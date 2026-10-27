"""kentc-agent: one simple main agent on any OpenAI-compatible LLM server (a local Strata by default).

    kentc-agent                                      chat in the current directory
    kentc-agent --workspace ~/cases/ter              chat with that folder as the workspace
    kentc-agent -w ~/cases/ter "summarize the evidence folder"         one prompt, print the answer
    kentc-agent -w ~/cases/ter --workflow ter-case-review -i case_id=TER-1 ...   run a YAML workflow
    kentc-agent -w ~/cases/ter --resume latest --answer next_step=Agree
    kentc-agent --list-workflows | --validate <workflow> | --info
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from kentc_agent.adapters.documents import attach_document
from kentc_agent.adapters.llm import LLMClient, LLMError
from kentc_agent.adapters.session import Session
from kentc_agent.adapters.tools import CORE_TOOLS, ToolContext, ToolError, resolve
from kentc_agent.adapters.web_research import web_search_tool
from kentc_agent.agent import Aborted, Agent, build_tools, new_session_path
from kentc_agent.config import STATE_DIR, load_settings
from kentc_agent.context.compaction import CompactionError
from kentc_agent.ui import ConsoleUI, fmt_tokens
from kentc_agent.workflow import Runner, WorkflowError, find_workflow, load, resolve_inputs, workflow_dirs

CHAT_HELP = """Commands:
  /attach <file> [question]  add a file to your next message (PDFs/images/large documents via the parsing sub-agent)
  /compact [focus]           summarize older history now
  /tokens                    context usage
  /new                       start a new session
  /tools                     list tools
  /quit                      exit (Ctrl-D)
Ctrl-C stops the current run; the conversation stays usable."""


# ---------------------------------------------------------------------- arguments
def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="kentc-agent", description="Agent runtime for an OpenAI-compatible LLM server.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("prompt", nargs="*", help="run this one prompt and print the answer ('-' reads stdin); "
                                              "without it: interactive chat")
    ap.add_argument("-w", "--workspace", default=".", help="workspace folder (default: current directory)")

    g = ap.add_argument_group("model")
    g.add_argument("--provider", choices=["openai", "qwen38"], help="LLM transport (default: openai)")
    g.add_argument("--qwen-backend", choices=["coordinator", "litellm"],
                   help="preferred Qwen backend (default: coordinator; automatic fallback before streamed output)")
    g.add_argument("--qwen-context-window", type=int, help="verified context limit safe for both Qwen backends")
    g.add_argument("--qwen-vision", action=argparse.BooleanOptionalAction, default=None,
                   help="explicitly enable or disable Qwen image input (default: disabled)")
    g.add_argument("--verify-tls", action=argparse.BooleanOptionalAction, default=None,
                   help="verify server TLS certificates (default: enabled)")
    g.add_argument("--trust-env", action=argparse.BooleanOptionalAction, default=None,
                   help="honor environment proxy settings (default: enabled)")
    g.add_argument("--base-url", help="OpenAI-compatible LLM server URL: Strata, a LiteLLM proxy, vLLM "
                                      "(default http://127.0.0.1:8081/v1, a local Strata)")
    g.add_argument("--model", help="model id (default: the server's)")
    g.add_argument("--effort", choices=["none", "low", "medium", "high"], help="reasoning effort")
    g.add_argument("--max-turns", type=int, help="model calls per prompt (or per workflow step) before stopping; "
                   "0 = no limit")
    g.add_argument("--tokens-per-minute", type=int,
                   help="shared rolling token quota for all agents (default: 0, admission disabled)")
    g.add_argument("--rate-limit-max-wait", type=float,
                   help="maximum total rate-limit waiting seconds per call (default: 120)")
    g.add_argument("--quiet", action="store_true", help="hide the model's reasoning")

    g = ap.add_argument_group("chat / prompt")
    g.add_argument("--tools", help="comma-separated tool allowlist (default: all)")
    g.add_argument("-c", "--continue", dest="cont", action="store_true", help="continue the latest session")
    g.add_argument("--session", help="session file to continue or create")
    g.add_argument("--no-session", action="store_true", help="do not save the conversation")
    g.add_argument("-a", "--attach", action="append", default=[], help="file to add to the first message")
    g.add_argument("-s", "--instructions", help="extra system instructions (text or @file)")

    g = ap.add_argument_group("workflow")
    g.add_argument("--workflow", nargs="?", const="", metavar="NAME|PATH",
                   help=f"run a workflow (a path, or a name in {STATE_DIR}/workflows/, workflows/ or bundled)")
    g.add_argument("-i", "--input", action="append", default=[], metavar="KEY=VALUE", help="workflow input")
    g.add_argument("--answer", action="append", default=[], metavar="STEP=VALUE",
                   help="answer a human gate up front (needed when not in a terminal)")
    g.add_argument("--resume", metavar="RUN_DIR|latest", help="continue a workflow run at its first unfinished step "
                   "(-i KEY=VALUE overrides a saved input for the steps still to run)")
    g.add_argument("--validate", metavar="NAME|PATH", help="check a workflow and list its steps")
    g.add_argument("--list-workflows", action="store_true", help="list available workflows")
    g.add_argument("--info", action="store_true", help="show the model, context window and settings")
    return ap


def pairs(values: list[str], flag: str) -> dict[str, str]:
    out = {}
    for v in values:
        key, sep, value = v.partition("=")
        if not sep:
            raise SystemExit(f"{flag} {v!r}: expected KEY=VALUE")
        out[key.strip()] = value
    return out


# ---------------------------------------------------------------------- setup
def workspace(args: argparse.Namespace) -> Path:
    ws = Path(args.workspace).expanduser().resolve()
    if not ws.is_dir():
        raise SystemExit(f"workspace {ws} does not exist")
    return ws


def make_context(args: argparse.Namespace, ui: ConsoleUI) -> ToolContext:
    ws = workspace(args)
    settings = load_settings(ws, {"base_url": args.base_url, "model": args.model,
                                  "provider": args.provider, "qwen_backend": args.qwen_backend,
                                  "qwen_context_window": args.qwen_context_window, "qwen_vision": args.qwen_vision,
                                  "verify_tls": args.verify_tls, "trust_env": args.trust_env,
                                  "reasoning_effort": args.effort,
                                  "tokens_per_minute": args.tokens_per_minute,
                                  "rate_limit_max_wait": args.rate_limit_max_wait,
                                  "max_turns": args.max_turns, "show_reasoning": False if args.quiet else None})
    ui.show_reasoning = settings.show_reasoning
    return ToolContext(ws, settings, LLMClient(settings), ui)


def open_session(args: argparse.Namespace, ws: Path) -> Session:
    if args.no_session:
        return Session()
    if args.session:
        p = Path(args.session).expanduser()
        p = p if p.is_absolute() else ws / p
        return Session.load(p) if p.is_file() else Session(p)
    if args.cont:
        found = sorted((ws / STATE_DIR / "sessions").glob("*.jsonl"))
        if found:
            return Session.load(found[-1])
    return Session(new_session_path(ws))


def make_agent(args: argparse.Namespace, ctx: ToolContext, session: Session) -> Agent:
    """The chat / one-shot agent: the core tools plus screened web_search, since a human is in the loop here.
    Workflow steps and studio agents get only the core tools (web through `web:` steps)."""
    instructions = args.instructions or ""
    if instructions.startswith("@"):
        instructions = resolve(ctx, instructions[1:]).read_text(encoding="utf-8")
    tools = [t.strip() for t in args.tools.split(",") if t.strip()] if args.tools else None
    return Agent(ctx, tools=build_tools(tools, {**CORE_TOOLS, "web_search": web_search_tool()}), session=session,
                 instructions=instructions)


def attachment(ctx: ToolContext, path: str, question: str | None = None) -> str:
    """A file for the next message: text as is; documents through the same policy as the read tool."""
    return attach_document(ctx, resolve(ctx, path), question, label=path)


# ---------------------------------------------------------------------- modes
def run_prompt(args: argparse.Namespace) -> int:
    ui = ConsoleUI(stream_content=sys.stdout.isatty())
    ctx = make_context(args, ui)
    prompt = sys.stdin.read() if args.prompt == ["-"] else " ".join(args.prompt)
    agent = make_agent(args, ctx, open_session(args, ctx.workspace))
    answer = agent.run("\n\n".join([*(attachment(ctx, a) for a in args.attach), prompt]))
    ui.finish()
    if not ui.stream_content:
        print(answer)
    ui.status("main", ui.meter())
    return 0


def run_chat(args: argparse.Namespace) -> int:
    try:
        import readline
    except ImportError:          # Windows
        readline = None
    ui = ConsoleUI()
    ctx = make_context(args, ui)
    info = ctx.llm.info()
    session = open_session(args, ctx.workspace)
    agent = make_agent(args, ctx, session)
    history = ctx.state_dir / "history"
    if readline is not None:
        history.parent.mkdir(parents=True, exist_ok=True)
        try:
            readline.read_history_file(history)
        except OSError:
            pass
    pending = [attachment(ctx, a) for a in args.attach]
    print(f"kentc-agent · {info.id} · {fmt_tokens(info.context_window)} context · workspace {ctx.workspace}")
    if session.path:
        print(f"session {session.path}" + (f" (resumed, {len(session.messages)} messages)" if session.messages else ""))
    print("/help for commands, Ctrl-D to exit")
    while True:
        try:
            line = input("\n› ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue
        if readline is not None:
            readline.write_history_file(history)
        if not line:
            continue
        try:
            if line.startswith("/"):
                cmd, _, rest = line.partition(" ")
                if cmd in ("/quit", "/exit"):
                    break
                elif cmd == "/help":
                    print(CHAT_HELP)
                elif cmd == "/tokens":
                    print(f"context {fmt_tokens(agent.context_tokens())}/{fmt_tokens(agent.window)}; compacts above "
                          f"{fmt_tokens(agent.window - agent.reserve)}; {len(session.messages)} messages"
                          + ("; has a summary" if session.summary else ""))
                elif cmd == "/compact":
                    if not agent.compact(rest or None, force=True):
                        print("nothing to compact")
                elif cmd == "/new":
                    session = Session(None if args.no_session else new_session_path(ctx.workspace))
                    agent = make_agent(args, ctx, session)
                    print("new session" + (f": {session.path}" if session.path else ""))
                elif cmd == "/tools":
                    print("\n".join(f"{t.name}: {t.description}" for t in agent.tools.values()))
                elif cmd == "/attach":
                    path, _, question = rest.strip().partition(" ")
                    if not path:
                        print("usage: /attach <file> [question]")
                        continue
                    pending.append(attachment(ctx, path, question or None))
                    print(f"attached {path}; it goes with your next message")
                else:
                    print(f"unknown command {cmd}; /help")
                continue
            prompt = "\n\n".join([*pending, line])
            pending = []
            agent.run(prompt)
            ui.finish()
            ui.status("main", ui.meter())
        except Aborted:
            ui.finish()
            print("\n[stopped]")
        except (LLMError, ToolError, CompactionError, OSError, ValueError) as e:
            ui.finish()
            print(f"\nerror: {e}", file=sys.stderr)
    return 0


def run_workflow(args: argparse.Namespace) -> int:
    ui = ConsoleUI(stream_content=sys.stdout.isatty())
    ctx = make_context(args, ui)
    runs = ctx.state_dir / "runs"
    if args.resume:
        run_dir = max(runs.iterdir(), key=lambda p: p.stat().st_mtime) if args.resume == "latest" \
            else resolve(ctx, args.resume)
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        wf = load(Path(state["workflow"]))
        inputs: dict[str, Any] = state["inputs"]
        overrides = pairs(args.input, "--input")
        unknown = sorted(set(overrides) - set(wf.inputs))
        if unknown:
            raise SystemExit(f"unknown input(s): {', '.join(unknown)}; declared: {', '.join(wf.inputs) or '-'}")
        inputs = {**inputs, **overrides}           # fix an input and continue; finished steps keep their results
    else:
        if not args.workflow:
            raise SystemExit("--workflow needs a name or path (or use --resume)")
        wf = load(find_workflow(ctx.workspace, args.workflow))
        inputs = resolve_inputs(wf, pairs(args.input, "--input"))
        run_dir = runs / f"{time.strftime('%Y%m%d-%H%M%S')}-{wf.name}"
    ui.status("workflow", f"{wf.name}: {len(wf.steps)} steps → {run_dir}")
    state = Runner(wf, ctx, inputs, run_dir, answers=pairs(args.answer, "--answer"),
                   ask_user=ui.ask if sys.stdin.isatty() else None).run()
    ui.finish()
    last = wf.steps[-1]
    if not ui.stream_content or last.kind != "prompt":
        print(state["steps"][last.id].get("output", ""))
    ui.status("workflow", f"done; run state in {run_dir}")
    return 0


def validate(args: argparse.Namespace) -> int:
    wf = load(find_workflow(workspace(args), args.validate))
    print(f"{wf.name}: {len(wf.steps)} steps, valid")
    for st in wf.steps:
        tools = st.spec.get("tools", wf.tools) if st.kind == "prompt" else None
        if st.kind == "ask":
            detail = "human gate"
        elif st.kind == "web":
            mode = "plans its tasks" if str(st.spec["web"]).strip() == "plan" else \
                f"foreach {st.spec['foreach']}" if "foreach" in st.spec else "one task"
            detail = f"web agent ({mode}) -> {st.spec.get('output', 'research/')}" + \
                ("  [approve]" if st.spec.get("approve") else "")
        else:
            detail = f"tools: {(', '.join(tools) or 'none') if tools is not None else 'all'}"
        when = f"  when {st.spec['when']}" if "when" in st.spec else ""
        print(f"  {st.id:24} {detail}{when}")
    if wf.inputs:
        print("inputs: " + ", ".join(k + ("" if "default" in v else " (required)") for k, v in wf.inputs.items()))
    return 0


def list_workflows(args: argparse.Namespace) -> int:
    ws = workspace(args)
    seen: set[Path] = set()
    for d in workflow_dirs(ws):
        for f in sorted([*d.glob("*.yaml"), *d.glob("*.yml")]):
            if f.resolve() in seen:
                continue
            seen.add(f.resolve())
            where = f.relative_to(ws) if f.is_relative_to(ws) else f
            try:
                wf = load(f)
                print(f"{wf.name:22} {where}\n{'':22} {wf.description.strip().splitlines()[0] if wf.description else ''}")
            except WorkflowError as e:
                print(f"{f.stem:22} {where}  INVALID: {e}")
    return 0


def show_info(args: argparse.Namespace) -> int:
    ctx = make_context(args, ConsoleUI())
    info, s = ctx.llm.info(), ctx.settings
    print(f"server          {ctx.llm.base}")
    print(f"model           {info.id}  (images: {'yes' if info.vision else 'no'})")
    print(f"context window  {info.context_window}  (compact above "
          f"{info.context_window - min(s.reserve_tokens, info.context_window // 4)})")
    print(f"workspace       {ctx.workspace}")
    print(f"tools           {', '.join(t.name for t in build_tools(None))}")
    for k, v in vars(s).items():
        if k not in ("base_url", "api_key"):
            print(f"  {k:28} {v}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.info:
            return show_info(args)
        if args.list_workflows:
            return list_workflows(args)
        if args.validate:
            return validate(args)
        if args.workflow is not None or args.resume:
            return run_workflow(args)
        if args.prompt:
            return run_prompt(args)
        return run_chat(args)
    except Aborted:
        print("\n[stopped]", file=sys.stderr)
        return 130
    except (LLMError, WorkflowError, ToolError, CompactionError, ValueError) as e:
        print(f"\nerror: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
