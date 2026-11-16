"""Foreground context compression policy: v1 budgets, checkpoints and local topic notes."""
from __future__ import annotations

from ..adapters.llm import ContextOverflow
from ..context.compaction import CompactionError, find_cut, summarize


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
        """Learn observed prompt density, never estimating below chars/4."""
        if not actual or estimated < 300 or actual <= counted:
            return
        observed = min(3.0, (actual - counted) / estimated)
        self.density = observed if observed > self.density else max(1.0, 0.8 * self.density + 0.2 * observed)

    @property
    def summary_words(self) -> int:
        """About window/16 tokens (300 to 4000), so compression frees real room."""
        return max(300, min(4000, self.window // 16)) * 3 // 4

    def room(self) -> int:
        return self.window - self.context_tokens() - max(256, self.window // 20)

    def compact(self, focus: str | None = None, *, force: bool = False) -> bool:
        """Consolidate older history into topic notes and a short task checkpoint."""
        # Parsing workers have isolated, pre-budgeted evidence, not topic archives.
        if not self._foreground:
            return False
        before = self.context_tokens()
        if not force and before <= self.window - self.reserve:
            return False
        cut = find_cut(self.session.messages, int(self.keep_recent / self.density))
        if cut == 0 and force and len(self.session.messages) > 1:
            cut = max(i for i, message in enumerate(self.session.messages)
                      if message["role"] in ("user", "assistant"))
        if cut == 0:
            return False
        self.ctx.events.status(self.name, f"compacting context ({before} tokens)...")
        s = self.ctx.settings
        result = summarize(self.ctx.llm, self.session.messages[:cut], self.session.summary, window=self.window,
                           reserve_tokens=self.reserve, max_output_tokens=s.max_output_tokens,
                           effort=s.sub_effort, focus=focus, max_words=self.summary_words,
                           density=self.density, existing_topics=self.session.read_topics())
        # Session commits topic writes and the journal before releasing any history.
        self.session.compact(result, cut, before)
        after = self.context_tokens()
        self.ctx.events.compaction(self.name, before, after)
        if self._op is not None:
            self._op.input["compactions"].append({"before": before, "after": after, "summarized": True})
        return True

    def _try_compact(self, *, force: bool = False) -> None:
        """Report failed compression without throwing away uncommitted history."""
        try:
            self.compact(force=force)
        except (CompactionError, ContextOverflow, OSError, ValueError) as exc:
            self.ctx.events.status(self.name, f"compaction failed: {exc}")
            if self._op is not None:
                self._op.input["compactions"].append({"error": str(exc)})
