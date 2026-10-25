"""Agentic Studio: web front end (web/) + FastAPI backend serving the apps of config/studio.yaml.

    kentc-studio --workspace ~/studio --effort low        # then open http://127.0.0.1:8090

The apps live in config/apps/<name>/app.yaml (agents declared inline, apps.py) and draw on the skills in skills/; the API
in api/app.py, the case/job service in service/cases.py and the dispatcher in jobs/queue.py.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn

from .api import create_app
from .service.cases import CaseService

ROOT = Path(__file__).resolve().parents[2]
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main() -> None:
    ap = argparse.ArgumentParser(prog="kentc-studio", description="Agentic Studio (web UI + API over kentc-agent)")
    ap.add_argument("-w", "--workspace", default=".", help="studio folder: cases live in <workspace>/cases/")
    ap.add_argument("--config", help="studio configuration (default: <workspace>/studio.yaml, else the bundled "
                                     "config/studio.yaml)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--token", help="API token (default: $KENTC_STUDIO_TOKEN); required when host is not loopback")
    ap.add_argument("--effort", choices=["none", "low", "medium", "high"], help="reasoning effort for local agents")
    args = ap.parse_args()

    token = args.token or os.environ.get("KENTC_STUDIO_TOKEN", "")
    if args.host not in LOOPBACK and not token:
        sys.exit("refusing to bind a non-loopback host without --token or $KENTC_STUDIO_TOKEN")

    ws = Path(args.workspace).expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)
    config = Path(args.config).resolve() if args.config else \
        ws / "studio.yaml" if (ws / "studio.yaml").is_file() else ROOT / "config" / "studio.yaml"
    studio = CaseService(ws, config, args.effort)
    print(f"Agentic Studio · apps {', '.join(a.title for a in studio.config.apps.values())} · workspace {ws} · "
          f"config {config} · http://{args.host}:{args.port}")
    uvicorn.run(create_app(studio, token=token), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
