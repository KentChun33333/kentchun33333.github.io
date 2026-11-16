import pytest

from kentc_agent.adapters.llm import ModelInfo, Reply
from kentc_agent.config import Settings
from kentc_agent.workflow import WorkflowError
from kent_webio.profiles import ProfileCatalog
from kent_webio.runtime import WebIO
from kent_webio.tasks import Tasks


class Model:
    def info(self, **kwargs):
        return ModelInfo("task-test", 24000, False)

    def chat(self, messages, **kwargs):
        return Reply(content="<h1>Reviewed report</h1>", finish="stop")


@pytest.fixture
def task_store(tmp_path):
    root = tmp_path / "legacy"
    root.mkdir()
    profiles = tmp_path / "profiles"
    (profiles / "personas").mkdir(parents=True)
    (profiles / "personas" / "reviewer.md").write_text("Pinned reviewer instructions.")
    (profiles / "workflows").mkdir()
    (profiles / "workflows" / "review.yaml").write_text("""name: Review
steps:
  - id: decision
    ask: Review this case.
    options: [Approve, Return]
    default: Approve
  - id: report
    tools: []
    prompt: Create the approved HTML report.
    output: reports/result.html
""")
    legacy = WebIO(root, Settings(trace=False), Model())
    return Tasks(legacy, ProfileCatalog(profiles)), profiles


def finish(web):
    with web.condition:
        assert web.condition.wait_for(lambda: not web.view["busy"], timeout=5)
    with web.lock:
        pass
    assert not web.view["error"], web.view["error"]


def test_task_files_and_pinned_profiles_survive_reopen(task_store):
    store, profiles = task_store
    first = store.create("First task", "reviewer", [], "")
    second = store.create("Second task", "", [], "")
    one, two = store.get(first["id"]), store.get(second["id"])
    result, error = one.agent._tool("write", {"path": "report.html", "content": "<h1>First task</h1>"})
    assert not error, result
    assert not (two.workspace / "report.html").exists()
    _, error = two.agent._tool("read", {"path": str(one.workspace / "report.html")})
    assert error
    one.agent._tool("write", {"path": "AGENTS.md", "content": "Uploaded document instruction marker."})
    (profiles / "personas" / "reviewer.md").write_text("Changed persona marker.")
    reopened = Tasks(store.legacy, ProfileCatalog(profiles)).get(first["id"])
    assert "Pinned reviewer instructions." in reopened.agent.system
    assert "Changed persona marker." not in reopened.agent.system
    assert "Uploaded document instruction marker." not in reopened.agent.system
    assert reopened.workspace == one.workspace
    assert reopened.agent.session.id != two.agent.session.id
    assert store.set_closed(one, True)["status"] == "closed"
    assert Tasks(store.legacy, ProfileCatalog(profiles)).get(first["id"]).task["closed"]
    with pytest.raises(FileNotFoundError):
        store.get("../other-task")


def test_workflow_default_waits_for_explicit_review_after_restart(task_store):
    store, profiles = task_store
    task = store.create("Case review", "reviewer", [], "review")
    web = store.get(task["id"])
    assert web.start_workflow({}, None, None)
    finish(web)
    assert web.view["workflow"]["status"] == "waiting"
    assert not (web.workspace / "reports/result.html").exists()
    # The task retains the reviewed workflow definition when its source is edited.
    (profiles / "workflows" / "review.yaml").write_text("invalid: replacement")
    restarted = Tasks(store.legacy, ProfileCatalog(profiles))
    assert next(row for row in restarted.list() if row["id"] == task["id"])["status"] == "waiting"
    web = restarted.get(task["id"])
    with pytest.raises(WorkflowError):
        web.start_workflow({}, "old-step", "Approve")
    assert web.start_workflow({}, "decision", "Approve")
    finish(web)
    assert web.view["workflow"]["status"] == "done"
    assert (web.workspace / "reports/result.html").read_text() == "<h1>Reviewed report</h1>"
    assert web.messages[-1]["outputs"] == ["reports/result.html"]
    assert web.task_summary()["status"] == "open"
