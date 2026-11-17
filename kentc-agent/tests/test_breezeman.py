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
