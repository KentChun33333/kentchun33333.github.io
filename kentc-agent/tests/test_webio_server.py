import threading
import time

import pytest
from fastapi.testclient import TestClient

from kentc_agent.adapters.llm import ModelInfo, Reply
from kentc_agent.config import Settings
from kent_webio.profiles import ProfileCatalog
from kent_webio.runtime import WebIO
from kent_webio.server import create_app
from kent_webio.tasks import Tasks


class SlowModel:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def info(self, **kwargs):
        return ModelInfo("test-model", 24000, False)

    def chat(self, messages, **kwargs):
        self.started.set()
        self.release.wait(timeout=5)
        return Reply(content="Done", finish="stop")


@pytest.fixture
def client_env(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    profiles = tmp_path / "profiles"
    (profiles / "personas").mkdir(parents=True)
    (profiles / "workflows").mkdir()
    (profiles / "workflows" / "bad.yaml").write_text("name: Bad\nsteps:\n  - id: s1\n    tools: [bash]\n    prompt: hi\n")
    model = SlowModel()
    web = WebIO(workspace, Settings(trace=False), model)
    app = create_app(web, profile_root=profiles)
    client = TestClient(app, base_url="http://localhost")
    return client, web, model, profiles


def test_file_crud_rename_delete_and_origin_check(client_env):
    client, web, _, _ = client_env

    # Origin mismatch on mutating methods is rejected
    assert client.post("/api/folders", json={"path": "docs"}, headers={"Origin": "http://evil.example"}).status_code == 403
    assert client.delete("/api/files?path=docs", headers={"Origin": "http://evil.example"}).status_code == 403

    # Create folder, upload file, list, rename, delete
    assert client.post("/api/folders", json={"path": "docs"}).status_code == 201
    assert client.put("/api/files?path=docs/report.html", content=b"<h1>Hi</h1>").status_code == 201

    listing = client.get("/api/files?path=docs").json()
    assert [entry["name"] for entry in listing["entries"]] == ["report.html"]

    # Preview includes sandbox CSP and valid origin
    preview = client.get("/preview/docs/report.html")
    assert preview.status_code == 200
    assert "sandbox allow-scripts" in preview.headers["content-security-policy"]
    assert "http://localhost/preview/" in preview.headers["content-security-policy"]

    # Rename file
    assert client.post("/api/files/rename", json={"source": "docs/report.html", "destination": "docs/final.html"}).status_code == 200
    assert (web.workspace / "docs" / "final.html").is_file()

    # Cannot move folder into itself
    assert client.post("/api/files/rename", json={"source": "docs", "destination": "docs/sub"}).status_code == 400

    # Non-empty folder requires recursive=true
    assert client.delete("/api/files?path=docs").status_code == 409
    assert client.delete("/api/files?path=docs&recursive=true").status_code == 200
    assert not (web.workspace / "docs").exists()

    # Path traversal is rejected
    assert client.delete("/api/files?path=../outside").status_code == 400


def test_closed_task_blocks_mutations_until_reopened(client_env):
    client, _, model, _ = client_env
    model.release.set()

    task = client.post("/api/tasks", json={"title": "Audit"}).json()
    tid = task["id"]

    assert client.post(f"/api/tasks/status?task={tid}", json={"closed": True}).status_code == 200

    assert client.post(f"/api/chat?task={tid}", json={"text": "hello", "files": []}).status_code == 409
    assert client.post(f"/api/folders?task={tid}", json={"path": "sub"}).status_code == 409
    assert client.put(f"/api/files?task={tid}&path=a.txt", content=b"x").status_code == 409
    assert client.delete(f"/api/files?task={tid}&path=a.txt").status_code == 409
    assert client.post(f"/api/files/rename?task={tid}", json={"source": "a.txt", "destination": "b.txt"}).status_code == 409
    assert client.post(f"/api/compact?task={tid}").status_code == 409

    # Reopening allows mutations again
    assert client.post(f"/api/tasks/status?task={tid}", json={"closed": False}).status_code == 200
    assert client.post(f"/api/folders?task={tid}", json={"path": "sub"}).status_code == 201


def test_cancel_running_chat(client_env):
    client, web, model, _ = client_env

    # Nothing running -> 409
    assert client.post("/api/cancel").status_code == 409

    assert client.post("/api/chat", json={"text": "hello", "files": []}).status_code == 202
    assert model.started.wait(timeout=3)

    assert client.post("/api/cancel").status_code == 200
    model.release.set()

    with web.condition:
        assert web.condition.wait_for(lambda: not web.view["busy"], timeout=5)
    assert web.view["run_state"] == "interrupted"
    assert web.view["notice"] == "Stopped by user."


def test_failed_task_creation_cleans_up_directory(client_env):
    _, web, _, profiles = client_env
    catalog = ProfileCatalog(profiles)
    # Force an invalid workflow into catalog to test create() cleanup
    from kentc_agent.workflow import load
    catalog.workflows["bad"] = load(profiles / "workflows" / "bad.yaml")
    store = Tasks(web, catalog)

    with pytest.raises(ValueError):
        store.create("Broken", "", [], "bad")

    tasks_dir = web.root / "tasks"
    assert not tasks_dir.exists() or list(tasks_dir.iterdir()) == []
