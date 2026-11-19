"""Tests for Folder-as-Studio-Agent integration in kentc-breezeman."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from kentc_agent.config import Settings
from kentc_breezeman.app import create_app
from kentc_breezeman.runtime import Runtime
from kentc_breezeman.studio import BLANK_APP_YAML


class _DummyLLM:
    def info(self, refresh: bool = False):
        class _Info:
            id = "dummy-model"
            context_window = 32768
        return _Info()


def _client(tmp_path: Path, token: str = "") -> TestClient:
    rt = Runtime(tmp_path, Settings(), _DummyLLM())
    return TestClient(create_app(rt, token=token))


def test_create_and_mount_studio_folder(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        tpls = client.get("/api/studios/templates")
        assert tpls.status_code == 200
        ids = {t["id"] for t in tpls.json()}
        assert {"ter", "rm", "blank"}.issubset(ids)

        created = client.post("/api/studios", json={"name": "TER KYC Batch", "template": "ter"})
        assert created.status_code == 200
        st = created.json()
        assert st["folder"] == "tasks/ter-kyc-batch"
        assert (tmp_path / "tasks/ter-kyc-batch/app.yaml").is_file()
        assert (tmp_path / "tasks/ter-kyc-batch/studio.yaml").is_file()

        listed = client.get("/api/studios").json()
        assert len(listed) == 1
        assert listed[0]["id"] == st["id"]
        assert listed[0]["cases"] == 0

        redir = client.get(f"/studios/{st['id']}", follow_redirects=False)
        assert redir.status_code == 307
        assert redir.headers["location"] == f"/studios/{st['id']}/"

        html = client.get(f"/studios/{st['id']}/")
        assert html.status_code == 200, html.text
        assert 'href="assets/css/app.css"' in html.text

        apps = client.get(f"/studios/{st['id']}/api/apps")
        assert apps.status_code == 200
        assert len(apps.json()) == 1

        # Create a case inside this Studio folder via its mounted Studio API
        case_res = client.post(
            f"/studios/{st['id']}/api/cases",
            data={
                "app": apps.json()[0]["name"],
                "case_id": "TER-2026-001",
                "fields": '{"cif":"CIF-1","start_date":"2026-07-01","lookback_date":"2026-04-01","trigger":"test"}',
                "lanes": ["context"],
            },
            files=[("files", ("trigger.txt", b"trigger email content", "text/plain"))],
        )
        assert case_res.status_code == 201, case_res.text
        assert client.get("/api/studios").json()[0]["cases"] == 1

        tree = client.get(f"/api/tree?task=studio:{st['id']}")
        assert tree.status_code == 200
        names = {e["name"] for e in tree.json()}
        assert {"app.yaml", "studio.yaml", "cases"}.issubset(names)


def test_autodiscover_plain_app_yaml_folder_and_token_guard(tmp_path: Path) -> None:
    custom = tmp_path / "custom-kyc"
    custom.mkdir()
    (custom / "app.yaml").write_text(BLANK_APP_YAML.format(title="Custom KYC"), encoding="utf-8")

    with _client(tmp_path, token="s3cr3t") as client:
        assert client.get("/api/studios").status_code == 401
        listed = client.get("/api/studios", headers={"x-api-token": "s3cr3t"})
        assert listed.status_code == 200
        studios = listed.json()
        assert len(studios) == 1
        sid = studios[0]["id"]
        assert studios[0]["name"] == "Custom KYC"

        assert client.get(f"/studios/{sid}/api/apps").status_code == 401
        ok = client.get(f"/studios/{sid}/api/apps", headers={"x-api-token": "s3cr3t"})
        assert ok.status_code == 200, ok.text
        assert ok.json()[0]["title"] == "Custom KYC"
