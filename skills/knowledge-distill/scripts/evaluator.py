#!/usr/bin/env python3
"""
Evaluator: IQ-Style Multi-Dimensional Assessment Engine for knowledge-distill.

Evaluates:
1. Structure reasoning (causal chain, stacking flow, state transitions)
2. Output duplication (n-gram similarity & duplicate phrase detection)
3. Quality vs output size (compression ratio & information density)
4. Reasoning depth (mechanisms, failure modes, trade-offs, critical paths)
5. Evidence boundaries (explicit tags: IMPLEMENTED, INFERENCE, RECOMMENDATION, etc.)
6. Evidence invalidation (falsification tests and boundary triggers)
7. Practical transfer (actionable contracts, scorecards, and workflows)

Outputs structured IQ Training Evaluation markdown report.
"""

import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class DimensionScore:
    name: str
    score: int  # 1 to 5
    rationale: str
    evidence: List[str] = field(default_factory=list)


class KnowledgeEvaluator:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.dimensions: List[DimensionScore] = []
        self.knowledge_texts: Dict[str, str] = {}
        self.analysis_texts: Dict[str, str] = {}
        self.cooked_texts: Dict[str, str] = {}
        self._load_corpus()

    def _load_corpus(self):
        """Loads text files from the standard folders."""
        for subdir, target_dict in [
            ("knowledge", self.knowledge_texts),
            ("analysis", self.analysis_texts),
            ("data-cooked", self.cooked_texts),
        ]:
            d = self.project_dir / subdir
            if d.is_dir():
                for p in d.glob("**/*.md"):
                    rel = str(p.relative_to(self.project_dir))
                    target_dict[rel] = p.read_text(encoding="utf-8", errors="ignore")

    def run_evaluation(self) -> List[DimensionScore]:
        """Calculates scores across all 7 IQ dimensions."""
        self.dimensions = [
            self._eval_structure_reasoning(),
            self._eval_output_duplication(),
            self._eval_quality_vs_size(),
            self._eval_reasoning_depth(),
            self._eval_evidence_boundaries(),
            self._eval_evidence_invalidation(),
            self._eval_practical_transfer(),
        ]
        return self.dimensions

    def _eval_structure_reasoning(self) -> DimensionScore:
        score = 1
        evidence = []
        all_text = " ".join(self.knowledge_texts.values()) + " " + " ".join(self.analysis_texts.values())

        # Check for stacking flow diagram pattern
        if re.search(r"\[Input.*?\]\s*-->\s*\[.*?\]\s*-->\s*\[Output.*?\]", all_text, re.IGNORECASE) or \
           re.search(r"==+\s+==+\s+==+", all_text):
            score += 2
            evidence.append("Contains structured input -> module -> output data contract layout.")

        # Check for sequence / stage tables
        if "sequence of stages" in all_text.lower() or "runtime workflow" in all_text.lower() or "step #" in all_text.lower():
            score += 1
            evidence.append("Contains explicit stage sequences or runtime execution order.")

        # Check for state transition or lifecycle logic
        if re.search(r"\b(lifecycle|transition|state machine|flow analysis)\b", all_text, re.IGNORECASE):
            score += 1
            evidence.append("Models explicit state transitions or operational lifecycles.")

        score = min(5, max(1, score))
        return DimensionScore(
            name="Structure Reasoning",
            score=score,
            rationale=f"Structure exhibits level {score}/5 causal mapping and contract structuring.",
            evidence=evidence
        )

    def _eval_output_duplication(self) -> DimensionScore:
        evidence = []
        if not self.knowledge_texts:
            return DimensionScore("Output Duplication", 1, "No knowledge artifacts found.", ["Missing knowledge files"])

        # Extract 5-gram phrases to detect copy-paste repetition across knowledge files
        def get_ngrams(text: str, n: int = 5) -> List[str]:
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text)]
            return [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]

        all_ngrams: List[str] = []
        file_ngrams: Dict[str, Set[str]] = {}
        for fname, txt in self.knowledge_texts.items():
            ng = set(get_ngrams(txt, 5))
            file_ngrams[fname] = ng
            all_ngrams.extend(ng)

        counts = Counter(all_ngrams)
        duplicated_ngrams = [ng for ng, cnt in counts.items() if cnt > 1]
        
        # Calculate duplication ratio
        total_unique = len(counts)
        dup_ratio = (len(duplicated_ngrams) / max(1, total_unique)) * 100

        if dup_ratio < 5.0:
            score = 5
            rationale = "Minimal redundancy across knowledge files; single canonical explanations well preserved."
        elif dup_ratio < 15.0:
            score = 4
            rationale = "Low cross-file repetition with clear cross-referencing."
        elif dup_ratio < 30.0:
            score = 3
            rationale = "Moderate phrase repetition detected across knowledge documents."
        else:
            score = 2
            rationale = "High duplication rate across files. Consolidate into canonical definitions."

        evidence.append(f"Cross-document n-gram duplication ratio: {dup_ratio:.1f}%")
        return DimensionScore(
            name="Output Duplication",
            score=score,
            rationale=rationale,
            evidence=evidence
        )

    def _eval_quality_vs_size(self) -> DimensionScore:
        cooked_len = sum(len(t.split()) for t in self.cooked_texts.values())
        knowledge_len = sum(len(t.split()) for t in self.knowledge_texts.values())
        analysis_len = sum(len(t.split()) for t in self.analysis_texts.values())

        evidence = [
            f"Cooked words: {cooked_len}, Analysis words: {analysis_len}, Knowledge words: {knowledge_len}"
        ]

        if knowledge_len == 0:
            return DimensionScore("Quality vs Output Size", 1, "Knowledge output is empty.", evidence)

        # Good distillation compresses raw/cooked into tight, high-signal knowledge (e.g. 10% to 50% ratio)
        compression_ratio = knowledge_len / max(1, cooked_len)
        evidence.append(f"Knowledge-to-Cooked Word Ratio: {compression_ratio:.2f}")

        if 0.05 <= compression_ratio <= 0.6:
            score = 5
            rationale = "High information density and effective distillation compression."
        elif compression_ratio < 0.05:
            score = 3
            rationale = "Output might be overly brief or omitting important nuances."
        else:
            score = 4 if compression_ratio <= 1.0 else 2
            rationale = "Output size is relatively large compared to inputs; review for compression opportunities."

        return DimensionScore(
            name="Quality vs Output Size",
            score=score,
            rationale=rationale,
            evidence=evidence
        )

    def _eval_reasoning_depth(self) -> DimensionScore:
        score = 1
        evidence = []
        all_text = " ".join(self.knowledge_texts.values()) + " " + " ".join(self.analysis_texts.values())
        lower_text = all_text.lower()

        depth_markers = [
            ("failure mode / edge case", r"\b(failure mode|soft decline|hard decline|idempotency|error handling|spof|bottleneck)\b"),
            ("causal mechanisms", r"\b(because|leads to|results in|critical path|single point of failure)\b"),
            ("trade-offs & constraints", r"\b(trade-off|constraint|limit|lease|timeout|sla|boundary)\b"),
            ("concrete values & error codes", r"\b(err_[a-z0-9_]+|http \d{3}|409|500|\b\d+ (minutes|seconds|ms)\b)"),
        ]

        for label, pattern in depth_markers:
            matches = re.findall(pattern, lower_text)
            if matches:
                score += 1
                evidence.append(f"Identified {label} ({len(matches)} occurrences)")

        score = min(5, max(1, score))
        return DimensionScore(
            name="Reasoning Depth",
            score=score,
            rationale=f"Analysis exposes causal depth, failure modes, and operational constraints ({score}/5).",
            evidence=evidence
        )

    def _eval_evidence_boundaries(self) -> DimensionScore:
        score = 2
        evidence = []
        all_text = " ".join(self.knowledge_texts.values()) + " " + " ".join(self.analysis_texts.values())

        # Check source ID citations
        citations = re.findall(r"\b(source-\d+)\b", all_text)
        if len(citations) >= 5:
            score += 1
            evidence.append(f"Strong citation backing ({len(citations)} source citations)")

        # Check explicit boundary labeling
        boundary_tags = ["IMPLEMENTED", "DOCUMENTED", "INFERENCE", "RECOMMENDATION", "OPEN QUESTION", "OUT OF SCOPE"]
        found_tags = [tag for tag in boundary_tags if tag in all_text]
        if found_tags:
            score += 1
            evidence.append(f"Includes explicit boundary tags: {', '.join(found_tags)}")

        # Check boundary section
        if "boundaries" in all_text.lower() or "constraints" in all_text.lower():
            score += 1
            evidence.append("Includes dedicated system boundaries & constraints section")

        score = min(5, max(1, score))
        return DimensionScore(
            name="Evidence Boundaries",
            score=score,
            rationale=f"Boundary discrimination and provenance tracing rated {score}/5.",
            evidence=evidence
        )

    def _eval_evidence_invalidation(self) -> DimensionScore:
        score = 1
        evidence = []
        all_text = " ".join(self.knowledge_texts.values()) + " " + " ".join(self.analysis_texts.values())
        lower_text = all_text.lower()

        invalidation_patterns = [
            ("invalidation condition", r"\b(invalidat|falsif|weakened if|nullified)\b"),
            ("timeout / expiration triggers", r"\b(expire|lease|refund|after \d+ (minutes|seconds))\b"),
            ("boundary tests", r"\b(boundary check|test condition|assumptions)\b"),
        ]

        for label, pattern in invalidation_patterns:
            if re.search(pattern, lower_text):
                score += 1
                evidence.append(f"Found {label} markers.")

        if "invalidation" in lower_text:
            score += 1

        score = min(5, max(1, score))
        return DimensionScore(
            name="Evidence of Invalidation",
            score=score,
            rationale=f"Falsification and invalidation criteria rating: {score}/5.",
            evidence=evidence
        )

    def _eval_practical_transfer(self) -> DimensionScore:
        score = 1
        evidence = []
        all_text = " ".join(self.knowledge_texts.values())

        # Check for workflow guide or scorecard
        if "workflow" in all_text.lower() or "reference guide" in all_text.lower():
            score += 1
            evidence.append("Provides concrete operational workflow guide.")

        # Check for code/schema/endpoint reference
        if re.search(r"(`(post|get|put|delete)\s+/[^`]+`|`x-[a-z-]+`)", all_text, re.IGNORECASE):
            score += 1
            evidence.append("Specifies exact API endpoints / headers / signatures.")

        # Check for concrete decision rules
        if "gate" in all_text.lower() or "policy" in all_text.lower() or "decision logic" in all_text.lower():
            score += 1
            evidence.append("Exposes explicit decision gates and error policies.")

        # Check for read order / orientation
        if (self.project_dir / "knowledge" / "read-order.md").is_file() or "read-order" in all_text.lower() or "big-picture" in all_text.lower():
            score += 1
            evidence.append("Provides orientation / read-order for fast onboarding.")

        score = min(5, max(1, score))
        return DimensionScore(
            name="Practical Transfer",
            score=score,
            rationale=f"Transferability and developer readiness rated {score}/5.",
            evidence=evidence
        )

    def generate_iq_report(self) -> str:
        """Produces the formal IQ-Style review markdown report."""
        if not self.dimensions:
            self.run_evaluation()

        avg_score = sum(d.score for d in self.dimensions) / len(self.dimensions)

        lines = [
            f"# IQ-Style Review Evaluation: `{self.project_dir.name}`",
            "",
            "## 1. Working-Memory Scratchpad",
            f"- **Target Project**: `{self.project_dir.name}`",
            f"- **Overall IQ Composite Score**: **{avg_score:.2f} / 5.0**",
            f"- **Files Evaluated**: {len(self.knowledge_texts)} knowledge, {len(self.analysis_texts)} analysis, {len(self.cooked_texts)} cooked files.",
            "",
            "## 2. Independent Dimension Assessment",
            "",
            "| Dimension | Score | Assessment & Findings |",
            "|---|:---:|---|",
        ]

        for d in self.dimensions:
            score_bar = "★" * d.score + "☆" * (5 - d.score)
            lines.append(f"| **{d.name}** | {score_bar} ({d.score}/5) | {d.rationale} |")

        lines.append("")
        lines.append("## 3. Detailed Evidence Breakdown")
        for d in self.dimensions:
            lines.append(f"### {d.name} ({d.score}/5)")
            if d.evidence:
                for ev in d.evidence:
                    lines.append(f"- {ev}")
            else:
                lines.append("- No specific signals detected.")
            lines.append("")

        lines.append("## 4. Synthesis & Recommendations")
        weakest = [d for d in self.dimensions if d.score <= 3]
        if weakest:
            lines.append("To elevate output quality, focus on these lower-scoring areas:")
            for w in weakest:
                lines.append(f"- **{w.name}**: {w.rationale}")
        else:
            lines.append("All dimensions meet or exceed target threshold (4+/5). The distillation payload is well-grounded and compressed.")

        return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 evaluator.py <project_directory> [--write]")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    if not project_dir.exists():
        print(f"Error: Directory not found: {project_dir}")
        sys.exit(1)

    write_to_file = "--write" in sys.argv
    evaluator = KnowledgeEvaluator(project_dir)
    evaluator.run_evaluation()
    report = evaluator.generate_iq_report()

    print(report)

    if write_to_file:
        out_path = project_dir / "analysis" / "iq-training-evaluation.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[Evaluator] Wrote evaluation report to: {out_path}")


if __name__ == "__main__":
    main()
