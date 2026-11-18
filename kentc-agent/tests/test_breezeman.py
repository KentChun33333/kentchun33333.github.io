import threading
import time

import pytest
from fastapi.testclient import TestClient

from kentc_agent.adapters.llm import ModelInfo, Reply
from kentc_agent.config import STATE_DIR, Settings
from kentc_breezeman.app import create_app
from kentc_breezeman.runtime import Runtime


class StreamingLLM:
    """Streams each scripted reply's text through on_delta; "WAIT" streams thinking until the run is stopped."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.streaming = threading.Event()

    def info(self, *, refresh=False):
        return ModelInfo("breezeman-test", 65536, False)

    def chat(self, messages, *, tools=None, max_tokens, effort=None, on_delta=None):
        reply = self.replies.pop(0)
        if reply == "WAIT":
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                on_delta("reasoning", ".")      # raises Aborted once stop is requested
                self.streaming.set()
                time.sleep(0.01)
            raise AssertionError("the run was never stopped")
        for word in reply.split(" "):
            on_delta("content", word + " ")
        return Reply(content=reply, finish="stop")


def client(tmp_path, llm):
    return TestClient(create_app(Runtime(tmp_path, Settings(), llm)))


def until(ws, kind):
    """Events up to the first of `kind`; any other run outcome first is a failure."""
    events = []
    while True:
        event = ws.receive_json()
        events.append(event)
        if event["type"] == kind:
            return events
        assert event["type"] not in ("done", "aborted", "compacted") and not (event["type"] == "error" and "run" in event), event



def test_uploads_stay_inside_the_workspace_and_never_overwrite(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / STATE_DIR).mkdir()
    with client(tmp_path, StreamingLLM()) as c:
        first = c.post("/api/upload", data={"folder": "docs"}, files=[("files", ("note.txt", b"one"))])
        second = c.post("/api/upload", data={"folder": "docs"}, files=[("files", ("../../note.txt", b"two"))])
        assert first.json()["saved"] == ["docs/note.txt"]
        assert second.json()["saved"] == ["docs/note (1).txt"]
        assert (tmp_path / "docs" / "note.txt").read_bytes() == b"one"
        for folder in ("..", STATE_DIR, f"docs/../{STATE_DIR}"):
            r = c.post("/api/upload", data={"folder": folder}, files=[("files", ("x.txt", b"x"))])
            assert r.status_code == 400, folder
        assert c.get("/api/file", params={"path": "../etc/passwd"}).status_code == 400
        assert [e["name"] for e in c.get("/api/tree").json()] == ["docs"]


def test_a_new_chat_is_a_fresh_main_agent_and_old_chats_resume(tmp_path):
    llm = StreamingLLM("first answer", "second answer")
    with client(tmp_path, llm) as c:
        a = c.post("/api/chats").json()["key"]
        with c.websocket_connect(f"/ws/{a}") as ws:
            assert ws.receive_json()["type"] == "hello"
            ws.send_json({"type": "chat", "text": "hello A", "attachments": []})
            events = until(ws, "done")
        assert events[0] == {**events[0], "type": "run_start", "text": "hello A"}
        assert "".join(e["text"] for e in events if e["type"] == "delta") == "first answer "
        assert events[-1]["answer"] == "first answer"

        b = c.post("/api/chats").json()["key"]
        assert b != a
        assert c.get(f"/api/chats/{b}/context").json()["messages"] == []
        with c.websocket_connect(f"/ws/{b}") as ws:
            ws.receive_json()
            ws.send_json({"type": "chat", "text": "hello B", "attachments": []})
            until(ws, "done")
        assert [m["content"] for m in c.get(f"/api/chats/{a}/transcript").json()] == ["hello A", "first answer"]
        assert [m["content"] for m in c.get(f"/api/chats/{b}/transcript").json()] == ["hello B", "second answer"]

    # a restarted server lists both and resumes A from its journal
    with client(tmp_path, StreamingLLM()) as c:
        listed = {e["key"]: e["title"] for e in c.get("/api/chats").json()}
        assert listed == {a: "hello A", b: "hello B"}
        context = c.get(f"/api/chats/{a}/context").json()
        assert [m["content"] for m in context["messages"]] == ["hello A", "first answer"]


def test_one_skill_per_chat_switches_cleanly_and_resumes(tmp_path):
    library = tmp_path / "lib"
    (library / "alpha").mkdir(parents=True)         # an asset folder beside a skill is not a skill
    (library / "alpha.md").write_text("---\ndescription: First skill.\n---\nALPHA RULES")
    (library / "beta.md").write_text("BETA RULES")
    systems = []

    class Recording(StreamingLLM):
        def chat(self, messages, **kw):
            systems.append(messages[0]["content"])
            return super().chat(messages, **kw)

    def app(llm):
        return TestClient(create_app(Runtime(tmp_path / "ws", Settings(), llm, library)))

    (tmp_path / "ws").mkdir()
    with app(Recording("one", "two", "WAIT")) as c:
        assert c.get("/api/skills").json() == [{"name": "alpha", "description": "First skill."},
                                               {"name": "beta", "description": ""}]
        key = c.post("/api/chats").json()["key"]
        assert c.put(f"/api/chats/{key}/skill", json={"name": "alpha"}).json() == {"skill": "alpha"}
        with c.websocket_connect(f"/ws/{key}") as ws:
            assert ws.receive_json()["skill"] == "alpha"
            ws.send_json({"type": "chat", "text": "q1", "attachments": []})
            until(ws, "done")
            assert c.put(f"/api/chats/{key}/skill", json={"name": "beta"}).json() == {"skill": "beta"}
            ws.send_json({"type": "chat", "text": "q2", "attachments": []})
            until(ws, "done")
            ws.send_json({"type": "chat", "text": "q3", "attachments": []})
            until(ws, "run_start")
            deadline = time.monotonic() + 5
            while not c.get("/api/chats").json()[0].get("busy") and time.monotonic() < deadline:
                time.sleep(0.01)
            assert c.put(f"/api/chats/{key}/skill", json={"name": None}).status_code == 409   # not while running
            ws.send_json({"type": "stop"})
            until(ws, "aborted")
        assert c.put(f"/api/chats/{key}/skill", json={"name": "../alpha"}).status_code == 400
        assert "ALPHA RULES" in systems[0] and "BETA RULES" not in systems[0]
        assert "BETA RULES" in systems[1] and "ALPHA RULES" not in systems[1]          # replaced, not stacked
        assert [m["content"] for m in c.get(f"/api/chats/{key}/transcript").json()][:4] == ["q1", "one", "q2", "two"]

    with app(StreamingLLM()) as c:                     # a restarted server resumes the chat with its skill
        context = c.get(f"/api/chats/{key}/context").json()
        assert context["skill"] == "beta" and "BETA RULES" in context["system"]
        assert c.put(f"/api/chats/{key}/skill", json={"name": None}).json() == {"skill": None}
        assert "BETA RULES" not in c.get(f"/api/chats/{key}/context").json()["system"]


def test_stop_ends_the_run_and_the_chat_stays_usable(tmp_path):
    llm = StreamingLLM("WAIT", "after stop")
    with client(tmp_path, llm) as c:
        key = c.post("/api/chats").json()["key"]
        with c.websocket_connect(f"/ws/{key}") as ws:
            ws.receive_json()
            ws.send_json({"type": "chat", "text": "think forever", "attachments": []})
            assert llm.streaming.wait(5)
            ws.send_json({"type": "chat", "text": "too early", "attachments": []})
            ws.send_json({"type": "stop"})
            events = until(ws, "aborted")
            assert any(e["type"] == "error" and "already running" in e["message"] for e in events)
            ws.send_json({"type": "chat", "text": "continue", "attachments": []})
            assert until(ws, "done")[-1]["answer"] == "after stop"
        roles = [m["role"] for m in c.get(f"/api/chats/{key}/transcript").json()]
        assert roles == ["user", "user", "assistant"]


@pytest.mark.parametrize("path", ["../outside.txt", f"{STATE_DIR}/sessions/x.jsonl", "missing.txt"])
def test_attachments_must_be_workspace_files(tmp_path, path):
    with client(tmp_path, StreamingLLM()) as c:
        key = c.post("/api/chats").json()["key"]
        with c.websocket_connect(f"/ws/{key}") as ws:
            ws.receive_json()
            ws.send_json({"type": "chat", "text": "read it", "attachments": [path]})
            event = ws.receive_json()
            assert event["type"] == "error" and "run" not in event


def test_raw_file_endpoint_serves_sandboxed_html(tmp_path):
    (tmp_path / "report.html").write_text("<h1>Hello</h1>", encoding="utf-8")
    (tmp_path / STATE_DIR).mkdir()
    (tmp_path / STATE_DIR / "secret.html").write_text("secret", encoding="utf-8")
    with client(tmp_path, StreamingLLM()) as c:
        r = c.get("/api/file/raw", params={"path": "report.html"})
        assert r.status_code == 200
        assert r.text == "<h1>Hello</h1>"
        assert r.headers["content-type"].startswith("text/html")
        assert r.headers["content-security-policy"] == "sandbox allow-scripts"
        assert c.get("/api/file/raw", params={"path": "../etc/passwd"}).status_code == 400
        assert c.get("/api/file/raw", params={"path": f"{STATE_DIR}/secret.html"}).status_code == 400


def test_task_manager_creates_folders_and_persists(tmp_path):
    with client(tmp_path, StreamingLLM()) as c:
        t1 = c.post("/api/tasks", json={"name": "Q3 KYC Review"}).json()
        assert t1["folder"] == "tasks/q3-kyc-review"
        assert (tmp_path / "tasks" / "q3-kyc-review").is_dir()
        assert t1["status"] == "open"
        assert t1["chat_key"]

        # duplicate name gets a distinct folder
        t2 = c.post("/api/tasks", json={"name": "Q3 KYC Review"}).json()
        assert t2["folder"] == "tasks/q3-kyc-review-2"
        assert (tmp_path / "tasks" / "q3-kyc-review-2").is_dir()
        assert t2["chat_key"] != t1["chat_key"]

        # custom folder inside workspace works; escaping workspace or STATE_DIR is rejected
        t3 = c.post("/api/tasks", json={"name": "Custom", "folder": "cases/alpha"}).json()
        assert t3["folder"] == "cases/alpha"
        assert (tmp_path / "cases" / "alpha").is_dir()
        for bad in ("../escape", STATE_DIR, "."):
            assert c.post("/api/tasks", json={"name": "Bad", "folder": bad}).status_code == 400

        # update status & delete (folder stays on disk)
        updated = c.patch(f"/api/tasks/{t1['id']}", json={"status": "done"}).json()
        assert updated["status"] == "done"
        assert c.patch(f"/api/tasks/{t1['id']}", json={"status": "invalid"}).status_code == 400
        assert c.delete(f"/api/tasks/{t2['id']}").json() == {"ok": True}
        assert (tmp_path / "tasks" / "q3-kyc-review-2").is_dir()

    # persists across server restart
    with client(tmp_path, StreamingLLM()) as c:
        listed = {t["id"]: t for t in c.get("/api/tasks").json()}
        assert set(listed) == {t1["id"], t3["id"]}
        assert listed[t1["id"]]["status"] == "done"


def test_task_has_isolated_workspace_for_files_and_agent(tmp_path):
    (tmp_path / "root-only.txt").write_text("root", encoding="utf-8")
    with client(tmp_path, StreamingLLM("ok", "after restart")) as c:
        task = c.post("/api/tasks", json={"name": "Isolated"}).json()
        tid = task["id"]
        # upload into the task's workspace
        up = c.post("/api/upload", data={"folder": "", "task": tid}, files=[("files", ("brief.txt", b"hello task"))])
        assert up.json()["saved"] == ["brief.txt"]
        assert (tmp_path / "tasks" / "isolated" / "brief.txt").read_bytes() == b"hello task"

        # tree & preview with task=<id> only see the task workspace, not root-only.txt
        assert [e["name"] for e in c.get("/api/tree", params={"task": tid}).json()] == ["brief.txt"]
        assert c.get("/api/file", params={"path": "brief.txt", "task": tid}).json()["text"] == "hello task"
        assert c.get("/api/file", params={"path": "root-only.txt", "task": tid}).status_code == 400

        # task chat runs with its workspace set to the task folder and accepts task-relative attachments
        with c.websocket_connect(f"/ws/{task['chat_key']}") as ws:
            ws.receive_json()
            ws.send_json({"type": "chat", "text": "read brief", "attachments": ["brief.txt"]})
            assert until(ws, "done")[-1]["answer"] == "ok"

    # after restart, resuming the task chat still uses the task workspace
    with client(tmp_path, StreamingLLM("after restart")) as c:
        with c.websocket_connect(f"/ws/{task['chat_key']}") as ws:
            ws.receive_json()
            ws.send_json({"type": "chat", "text": "again", "attachments": ["brief.txt"]})
            assert until(ws, "done")[-1]["answer"] == "after restart"


def test_task_scheduler_validates_and_triggers_due_runs(tmp_path):
    rt = Runtime(tmp_path, Settings(), StreamingLLM("scheduled reply"))
    with TestClient(create_app(rt)) as c:
        task = c.post("/api/tasks", json={"name": "Daily Watch"}).json()
        tid = task["id"]

        # validation
        assert c.patch(f"/api/tasks/{tid}", json={"schedule": {"enabled": True, "interval_min": 5, "prompt": ""}}).status_code == 400
        assert c.patch(f"/api/tasks/{tid}", json={"schedule": {"enabled": True, "interval_min": 0, "prompt": "hi"}}).status_code == 400

        # enable schedule
        updated = c.patch(
            f"/api/tasks/{tid}",
            json={"schedule": {"enabled": True, "interval_min": 10, "prompt": "check updates"}},
        ).json()
        sched = updated["schedule"]
        assert updated["status"] == "active"
        assert sched["enabled"] is True
        assert sched["interval_min"] == 10
        assert sched["prompt"] == "check updates"
        assert isinstance(sched["next_run"], float)

        # not due yet
        assert rt.tick_schedules(now=sched["next_run"] - 1) == []

        # due -> triggers the task's chat
        with c.websocket_connect(f"/ws/{task['chat_key']}") as ws:
            ws.receive_json()
            assert rt.tick_schedules(now=sched["next_run"] + 1) == [tid]
            assert until(ws, "done")[-1]["answer"] == "scheduled reply"

        assert [m["content"] for m in c.get(f"/api/chats/{task['chat_key']}/transcript").json()] == [
            "check updates",
            "scheduled reply",
        ]


def test_overdue_tasks_stagger_by_5_minutes(tmp_path):
    rt = Runtime(tmp_path, Settings(), StreamingLLM("first", "second"))
    with TestClient(create_app(rt)) as c:
        t1 = c.post("/api/tasks", json={"name": "Task One"}).json()
        t2 = c.post("/api/tasks", json={"name": "Task Two"}).json()
        r1 = c.patch(f"/api/tasks/{t1['id']}", json={"schedule": {"enabled": True, "interval_min": 60, "prompt": "p1"}}).json()
        r2 = c.patch(f"/api/tasks/{t2['id']}", json={"schedule": {"enabled": True, "interval_min": 60, "prompt": "p2"}}).json()
        # jump past both next_runs so both are overdue
        now = max(r1["schedule"]["next_run"], r2["schedule"]["next_run"]) + 10
        with c.websocket_connect(f"/ws/{t1['chat_key']}") as ws1:
            ws1.receive_json()
            assert rt.tick_schedules(now=now) == [t1["id"]]
            assert until(ws1, "done")[-1]["answer"] == "first"

        # t2 should be queued 5 minutes (300s) later
        tasks = {t["id"]: t for t in c.get("/api/tasks").json()}
        assert tasks[t2["id"]]["schedule"]["next_run"] == now + 300
        assert rt.tick_schedules(now=now + 299) == []

        with c.websocket_connect(f"/ws/{t2['chat_key']}") as ws2:
            ws2.receive_json()
            assert rt.tick_schedules(now=now + 300) == [t2["id"]]
            assert until(ws2, "done")[-1]["answer"] == "second"


def test_task_scheduler_applies_selected_skill(tmp_path):
    lib = tmp_path / "skills"
    lib.mkdir()
    (lib / "digest.md").write_text("---\ndescription: Daily digest.\n---\nDIGEST RULES", encoding="utf-8")
    systems = []

    class Recording(StreamingLLM):
        def chat(self, messages, **kw):
            systems.append(messages[0]["content"])
            return super().chat(messages, **kw)

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    rt = Runtime(ws_dir, Settings(), Recording("done with skill"), lib)
    with TestClient(create_app(rt)) as c:
        task = c.post("/api/tasks", json={"name": "Digest"}).json()
        tid = task["id"]
        assert c.patch(
            f"/api/tasks/{tid}",
            json={"schedule": {"enabled": True, "interval_min": 15, "prompt": "run", "skill": "missing"}},
        ).status_code == 400
        r = c.patch(
            f"/api/tasks/{tid}",
            json={"schedule": {"enabled": True, "interval_min": 15, "prompt": "run", "skill": "digest"}},
        ).json()
        assert r["schedule"]["skill"] == "digest"
        with c.websocket_connect(f"/ws/{task['chat_key']}") as ws:
            ws.receive_json()
            assert rt.tick_schedules(now=r["schedule"]["next_run"] + 1) == [tid]
            assert until(ws, "done")[-1]["answer"] == "done with skill"
        assert "DIGEST RULES" in systems[-1]
        assert c.get(f"/api/chats/{task['chat_key']}/context").json()["skill"] == "digest"
