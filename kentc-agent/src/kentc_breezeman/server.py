"""kentc-breezeman: chat web UI + the kentc_agent runtime in one process.

    kentc-breezeman --workspace ~/work                  # then open http://127.0.0.1:9001
    kentc-breezeman -w ~/work --effort low --persona personas/catty.md

Each chat is a fresh main agent with its own session journal in <workspace>/.kentc-agent/sessions/;
saved sessions can be resumed from the chat list. Model settings load like kentc-agent's
(~/.config/kentc-agent/config.yaml, <workspace>/.kentc-agent/config.yaml, KENTC_AGENT_*).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn

from kentc_agent.adapters.llm import LLMClient, LLMError
from kentc_agent.config import load_settings

from .app import create_app
from .runtime import Runtime

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="kentc-breezeman", description="Chat web UI over kentc-agent")
    ap.add_argument("-w", "--workspace", default=".", help="the agent's workspace (shown as the folder tree)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9001)
    ap.add_argument("--token", help="API token (default: $KENTC_BREEZEMAN_TOKEN); required when host is not loopback")
    ap.add_argument("--base-url", help="OpenAI-compatible server, e.g. http://127.0.0.1:8081/v1")
    ap.add_argument("--model", help="model id (default: server discovery)")
    ap.add_argument("--effort", choices=["none", "low", "medium", "high"], help="reasoning effort")
    ap.add_argument("--persona", help="persona file for every chat's main agent")
    ap.add_argument("--max-turns", type=int, help="model calls per prompt (0: no limit)")
    args = ap.parse_args(argv)

    token = args.token or os.environ.get("KENTC_BREEZEMAN_TOKEN", "")
    if args.host not in LOOPBACK and not token:
        sys.exit("refusing to bind a non-loopback host without --token or $KENTC_BREEZEMAN_TOKEN")

    ws = Path(args.workspace).expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)
    try:
        settings = load_settings(ws, {"base_url": args.base_url, "model": args.model,
                                      "reasoning_effort": args.effort, "persona_path": args.persona,
                                      "max_turns": args.max_turns})
        llm = LLMClient(settings)
    except (ValueError, LLMError) as e:
        sys.exit(f"configuration error: {e}")
    try:
        info = llm.info()
        model = f"model {info.id} · {info.context_window} context"
    except LLMError as e:
        model = f"model offline ({e}); chats fail until it is reachable"
    print(f"kentc-breezeman · {model} · workspace {ws} · http://{args.host}:{args.port}")
    uvicorn.run(create_app(Runtime(ws, settings, llm), token=token), host=args.host, port=args.port,
                log_level="warning")


if __name__ == "__main__":
    main()
