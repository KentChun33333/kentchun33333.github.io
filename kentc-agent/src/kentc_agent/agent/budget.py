"""Context budget policy: token estimates, compaction triggers, and reply room."""

from __future__ import annotations

from ..adapters.llm import ContextOverflow
from ..context.compaction import CompactionError, find_cut, shrink_tool_results, summarize


class BudgetMixin:
    """Mixed into Agent; expects ctx, session, name, density and _op."""

    @property
    def window(self) -> int:
        return self.ctx.llm.info().context_window

    @property
    def reserve(self) -> int:
        return min(self.ctx.settings.reserve_tokens, self.window // 4)

    @property
    def keep_recent(self) -> int:
        return min(self.ctx.settings.keep_recent_tokens, self.window // 3)

    def context_tokens(self) -> int:
        return self.session.context_tokens(self.fixed_tokens, self.density)

    def _calibrate(self, counted: int, estimated: int, actual: int | None) -> None:
        """Learn how dense this session's text really is: the server's prompt size against the estimate of the same
        request. A denser reading is taken at once, a lighter one slowly; never below chars/4."""
        if not actual or estimated < 300 or actual <= counted:
            return
        observed = min(3.0, (actual - counted) / estimated)
        self.density = observed if observed > self.density else max(1.0, 0.8 * self.density + 0.2 * observed)

    @property
    def summary_words(self) -> int:
        """The longest compaction summary: about window/16 tokens (300 to 4000), so a compaction frees real room."""
        return max(300, min(4000, self.window // 16)) * 3 // 4

    def room(self) -> int:
        """Tokens left for the reply. The safety margin covers the estimate of the newest messages (chars/4 runs
        low for paths, JSON and code), so prompt + max_tokens stays under the server's limit."""
        return self.window - self.context_tokens() - max(256, self.window // 20)

    def compact(self, focus: str | None = None, *, force: bool = False) -> bool:
        """Summarize old history if the context is over budget (or always with `force`). -> compacted?"""
        before = self.context_tokens()
        if not force and before <= self.window - self.reserve:
            return False
        s = self.ctx.settings
        cut = find_cut(self.session.messages, int(self.keep_recent / self.density))
        if cut == 0 and force and len(self.session.messages) > 1:
            cut = max(i for i, m in enumerate(self.session.messages) if m["role"] in ("user", "assistant"))
        if cut > 0:
            self.ctx.events.status(self.name, f"compacting context ({before} tokens)...")
            summary = summarize(self.ctx.llm, self.session.messages[:cut], self.session.summary, window=self.window,
                                reserve_tokens=self.reserve, max_output_tokens=s.max_output_tokens,
                                effort=s.sub_effort, focus=focus, max_words=self.summary_words,
                                density=self.density)
            self.session.compact(summary, cut, before)
        if self.context_tokens() > self.window - self.reserve:
            shrink_tool_results(self.session.messages, self.keep_recent // 4)
        after = self.context_tokens()
        self.ctx.events.compaction(self.name, before, after)
        if self._op is not None:
            self._op.input["compactions"].append({"before": before, "after": after, "summarized": cut > 0})
        return cut > 0

    def _try_compact(self, *, force: bool = False) -> None:
        """Compaction that never ends the run: a failed summary is reported, and when room is needed anyway
        (`force`) old tool results are shortened instead."""
        try:
            self.compact(force=force)
            return
        except (CompactionError, ContextOverflow) as e:
            self.ctx.events.status(self.name, f"compaction failed: {e}")
            if self._op is not None:
                self._op.input["compactions"].append({"error": str(e)})
        if force:
            n = shrink_tool_results(self.session.messages, max(200, self.keep_recent // 4))
            if n:
                self.ctx.events.status(self.name, f"shortened {n} older tool result(s) instead")
