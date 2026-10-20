"""Terminal rendering of agent events (stderr for progress; the main answer streams to stdout)."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .ports import Events

SUB_AGENTS = ("document", "subagent", "web", "web-screen")


def fmt_tokens(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


class ConsoleUI(Events):
    def __init__(self, *, show_reasoning: bool = True, stream_content: bool = True,
                 out: TextIO = sys.stdout, err: TextIO = sys.stderr) -> None:
        self.show_reasoning = show_reasoning
        self.stream_content = stream_content
        self.out, self.err = out, err
        self.color = err.isatty()
        self.mode: str | None = None          # what the last streamed text was: "reasoning" | "content"
        self.tokens = 0
        self.window = 0

    def _c(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def _break(self) -> None:
        if self.mode is not None:
            (self.out if self.mode == "content" and self.stream_content else self.err).write("\n")
            self.mode = None

    def _line(self, text: str) -> None:
        self._break()
        self.err.write(text + "\n")
        self.err.flush()

    # ------------------------------------------------------------------ Events
    def delta(self, agent: str, kind: str, text: str) -> None:
        if agent in SUB_AGENTS or kind == "tool":
            return
        if kind == "reasoning" and not self.show_reasoning:
            return
        if kind == "content" and not self.stream_content:
            return
        if self.mode != kind:
            self._break()
            if kind == "reasoning":
                self.err.write(self._c("2;3", "thinking: "))
            self.mode = kind
        if kind == "reasoning":
            self.err.write(self._c("2;3", text))
            self.err.flush()
        else:
            self.out.write(text)
            self.out.flush()

    def tool_start(self, agent: str, name: str, args: dict[str, Any]) -> None:
        shown = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)[:80]}" for k, v in args.items()
                          if k not in ("content", "new_text", "old_text"))
        prefix = "  ↳ " if agent in SUB_AGENTS else ""
        tag = f"[{agent}] " if agent != "main" else ""
        self._line(prefix + self._c("36", f"● {tag}{name}") + self._c("2", f"({shown})"))

    def tool_end(self, agent: str, name: str, result: str, error: bool) -> None:
        lines = result.strip().splitlines() or [""]
        head = lines[0][:140] + (f"  (+{len(lines) - 1} lines)" if len(lines) > 1 else "")
        prefix = "    " if agent in SUB_AGENTS else "  "
        self._line(prefix + (self._c("31", "⎿ " + head) if error else self._c("2", "⎿ " + head)))

    def compaction(self, agent: str, before: int, after: int) -> None:
        self._line(self._c("1;33", f"◆ [{agent}] context compacted: {fmt_tokens(before)} → {fmt_tokens(after)} tokens"))

    def big_result(self, agent: str, tool: str, args: Any, routed: dict[str, Any], shown: int) -> None:
        target = ""
        if isinstance(args, dict):
            target = str(args.get("path") or args.get("command") or args.get("pattern") or "")
            target = target if len(target) <= 60 else target[:57] + "..."
        why = {"turn": "turn over big_turn_tokens", "file": "big file (over big_result_tokens)"}.get(
            routed.get("rule"), "result over big_result_tokens")
        prefix = "    " if agent in SUB_AGENTS else "  "
        self._line(prefix + self._c("1;35", f"▣ stored {tool}({target}): {fmt_tokens(routed['tokens'])} → "
                                            f"{fmt_tokens(shown)} tokens")
                   + self._c("35", f" · {why} · digest by {routed['by']}") + self._c("2", f" · {routed['folder']}"))

    def status(self, agent: str, text: str) -> None:
        self._line(self._c("2", f"· [{agent}] {text}"))

    def turn_end(self, agent: str, tokens: int, window: int) -> None:
        if agent not in SUB_AGENTS:
            self.tokens, self.window = tokens, window

    # ------------------------------------------------------------------ helpers
    def meter(self) -> str:
        if not self.window:
            return ""
        pct = 100 * self.tokens / self.window
        return f"context {fmt_tokens(self.tokens)}/{fmt_tokens(self.window)} ({pct:.0f}%)"

    def finish(self) -> None:
        self._break()
        self.out.flush()

    def ask(self, step: str, message: str, options: list[str] | None, default: str | None) -> str:
        """A workflow human gate on the terminal: numbered options or free text; Enter takes the default."""
        self._break()
        self.err.write("\n" + self._c("1;35", f"━━ human review · {step} ━━") + "\n" + message.rstrip() + "\n")
        if options:
            for i, o in enumerate(options, 1):
                self.err.write(f"  {i}) {o}" + (self._c("2", "  (default)") if o == default else "") + "\n")
        self.err.flush()
        while True:
            answer = read_line("answer › ").strip()
            if not answer and default is not None:
                return str(default)
            if options and answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1]
            if answer and (not options or any(answer.lower() == o.lower() for o in options)):
                return answer
            self.err.write(f"choose 1-{len(options)}\n" if options else "an answer is needed\n")


def read_line(prompt: str) -> str:
    """input(), with the terminal in normal line mode while it waits. A terminal left in raw mode by another program
    (Enter echoed as ^M, carriage return not turned into a newline) would otherwise never end the line."""
    try:
        import termios
        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
    except (ImportError, OSError, ValueError):            # not a terminal (or no termios, e.g. Windows)
        return input(prompt)
    line = list(saved)
    line[0] |= termios.ICRNL                              # Enter (\r) ends the line
    line[3] |= termios.ICANON | termios.ECHO              # line editing, typed text visible
    termios.tcsetattr(fd, termios.TCSANOW, line)
    try:
        return input(prompt)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, saved)
