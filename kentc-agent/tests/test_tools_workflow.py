from __future__ import annotations

import pytest

from kentc_agent.adapters.documents import parse_pages
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS, ToolError

from .conftest import FakeLLM


def no_llm(messages, tools):
    raise AssertionError("no model call expected")


# ---------------------------------------------------------------------- edit / write boundaries
def test_edit_requires_unique_match_and_stays_in_workspace(make_ctx, tmp_path):
    ctx = make_ctx(FakeLLM(no_llm))
    f = tmp_path / "x.py"
    f.write_text("a = 1\nb = 1\n")
    edit = CORE_TOOLS["edit"].run
    with pytest.raises(ToolError, match="occurs 2 times"):
        edit(ctx, {"path": "x.py", "old_text": "= 1", "new_text": "= 2"})
    with pytest.raises(ToolError, match="not found"):
        edit(ctx, {"path": "x.py", "old_text": "c = 1", "new_text": ""})
    edit(ctx, {"path": "x.py", "old_text": "b = 1", "new_text": "b = 2"})
    assert f.read_text() == "a = 1\nb = 2\n"
    edit(ctx, {"path": "x.py", "old_text": "= ", "new_text": ":= ", "replace_all": True})
    assert f.read_text() == "a := 1\nb := 2\n"
    with pytest.raises(ToolError, match="outside the workspace"):
        CORE_TOOLS["write"].run(ctx, {"path": "../escape.txt", "content": "x"})
    assert not (tmp_path.parent / "escape.txt").exists()


def test_read_routes_big_files_and_pages_stay_within_budget(make_ctx, tmp_path):
    ctx = make_ctx(FakeLLM(no_llm), big_result_tokens=50)
    (tmp_path / "small.txt").write_text("\n".join(f"line {i}" for i in range(1, 6)))
    assert CORE_TOOLS["read"].run(ctx, {"path": "small.txt"}) == "\n".join(f"line {i}" for i in range(1, 6))
    (tmp_path / "big.txt").write_text("\n".join(f"line {i}" for i in range(1, 101)))
    out = CORE_TOOLS["read"].run(ctx, {"path": "big.txt"})
    assert out.startswith("[Big result: read(path=big.txt)") and "Full text: big.txt." in out
    page = CORE_TOOLS["read"].run(ctx, {"path": "big.txt", "offset": 21})
    body, note = page.split("\n\n[")
    assert body.startswith("line 21\n") and len(body) <= 50 * 4 and note.startswith("Showing lines 21-")


def test_bash_keeps_output_tail_and_reports_exit(make_ctx):
    ctx = make_ctx(FakeLLM(no_llm), tool_output_max_lines=5)
    out = CORE_TOOLS["bash"].run(ctx, {"command": "seq 1 50; exit 3"})
    assert "50" in out and "\n1\n" not in out and out.endswith("[exit code 3]")
    assert "Full output:" in out


# ---------------------------------------------------------------------- document chunking
def test_parse_pages():
    assert parse_pages("1-3,5,3", 10) == [1, 2, 3, 5]
    assert parse_pages(None, 3) == [1, 2, 3]
    assert parse_pages("8-20", 10) == [8, 9, 10]
    with pytest.raises(ToolError):
        parse_pages("20-30", 10)


def test_video_and_legacy_office_are_rejected_before_any_model_call(make_ctx, tmp_path):
    ctx = make_ctx(FakeLLM(no_llm))
    (tmp_path / "clip.mp4").write_bytes(b"\0\0\0 ftypisom")
    (tmp_path / "old.xls").write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(ToolError, match="video input is not supported"):
        CORE_TOOLS["read"].run(ctx, {"path": "clip.mp4"})
    with pytest.raises(ToolError, match=r"save it as \.xlsx"):
        CORE_TOOLS["read"].run(ctx, {"path": "old.xls"})


def test_session_log_never_stores_inline_images(tmp_path):
    path = tmp_path / "s.jsonl"
    s = Session(path)
    image = {"type": "image_url", "image_url": {"url": "data:image/png;base64," + "A" * 50_000}, "_tokens": 448}
    s.append({"role": "user", "content": [{"type": "text", "text": "page"}, image]})
    assert "base64" not in path.read_text() and path.stat().st_size < 1000
    assert s.messages[0]["content"][1] is image          # the live request still carries the image

