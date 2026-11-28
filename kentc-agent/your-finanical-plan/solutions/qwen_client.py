"""
Async OpenAI-compatible client for local Qwen3.8 financial key-value extraction.

All document_type categories, key definitions, and per-solution prompt preambles are
compiled dynamically from `extraction_schema.yaml` (referenced in `config.yaml`).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, List, Optional

import httpx

from solutions import ConfigNode, load_extraction_schema
from solutions.image_utils import bytes_to_data_url
from solutions.models import (
    DeadlineBudget,
    ExtractedRecord,
    PageUnit,
    normalize_doc_type,
    parse_numeric_value,
)

logger = logging.getLogger(__name__)


def build_system_prompt(
    schema: dict[str, Any],
    doc_type_hint: Optional[str] = None,
) -> str:
    """Dynamically compile the Qwen3.8 system prompt from `extraction_schema.yaml`."""
    ps = schema.get("prompt_settings", {})
    doc_types: dict[str, Any] = schema.get("document_types", {})

    lines: List[str] = [
        ps.get("role_instruction", "You are a precision financial key-value extraction engine."),
        "",
        "Allowed `document_type` categories: " + " | ".join(doc_types.keys()),
        "",
        "Key Definitions by `document_type`:",
    ]

    hint_norm = normalize_doc_type(doc_type_hint) if doc_type_hint else None

    # Order hinted document_type first if provided, while keeping all types for mixed docs
    ordered_types = list(doc_types.keys())
    if hint_norm and hint_norm in ordered_types:
        ordered_types.remove(hint_norm)
        ordered_types.insert(0, hint_norm)

    for dtype in ordered_types:
        spec = doc_types.get(dtype) or {}
        rule = spec.get("extraction_rule", "")
        keys_map: dict[str, str] = spec.get("keys") or {}
        if hint_norm and dtype != hint_norm and len(keys_map) > 6:
            # Compact summary for non-primary categories to keep prompt tight and fast
            key_str = ", ".join(keys_map.keys())
            lines.append(f"- {dtype}: keys=[{key_str}] ({rule})")
        else:
            key_defs = "; ".join(f"{k} ({v})" for k, v in keys_map.items())
            lines.append(f"- {dtype}: {key_defs}")
            if rule:
                lines.append(f"  rule: {rule}")

    rules = ps.get("global_rules") or []
    if rules:
        lines.append("")
        lines.append("Rules:")
        for idx, r in enumerate(rules, start=1):
            lines.append(f"{idx}. {r}")

    if fmt := ps.get("output_format_instruction"):
        lines.append("")
        lines.append(fmt)
    if ex := ps.get("few_shot_example"):
        lines.append("Example:")
        lines.append(ex)

    return "\n".join(lines)


def match_glossary_terms(text: str, schema: dict[str, Any]) -> List[dict[str, Any]]:
    """
    On-demand glossary matcher: returns ONLY domain_glossary entries whose aliases
    actually appear in the chunk text (0 extra prompt tokens when not present).
    """
    glossary = schema.get("domain_glossary") or []
    if not glossary or not text:
        return []
    lower = f" {text.lower()} "
    matched: List[dict[str, Any]] = []
    for entry in glossary:
        aliases = entry.get("aliases") or [entry.get("term", "")]
        for alias in aliases:
            a = str(alias).strip().lower()
            if not a:
                continue
            # Short acronyms (<=4 chars) use word-boundary matching to avoid false positives
            if len(a) <= 4 and a.isalnum():
                if re.search(rf"\b{re.escape(a)}\b", lower):
                    matched.append(entry)
                    break
            elif a in lower:
                matched.append(entry)
                break
    return matched


def build_user_prompt(
    chunk: List[PageUnit],
    client_name: str,
    source_file: str,
    doc_type_hint: Optional[str],
    solution_mode: str,
    schema: dict[str, Any],
    use_vision: bool,
    max_chars_per_call: int,
) -> str:
    """Build the solution-specific user prompt payload for a 1..5 page/sheet chunk."""
    solution_contexts = schema.get("prompt_settings", {}).get("solution_contexts", {})
    mode_context = solution_contexts.get(solution_mode, "")

    hint_line = (
        f"Optional hint: document_type='{doc_type_hint}' (still tag mixed items accurately per row)."
        if doc_type_hint
        else "Auto-detect document_type per row (file may contain mixed document types)."
    )

    text_sections: List[str] = [
        f"Client: {client_name} | File: {source_file} | Pipeline: {solution_mode}",
        hint_line,
    ]
    if mode_context:
        text_sections.append(f"Context: {mode_context}")

    # Inject ONLY domain glossary definitions matched in this chunk (e.g., SRS, T-Bill, Private Fund, FCN, ILP)
    combined_chunk_text = "\n".join(u.text for u in chunk if u.text)
    matched_glossary = match_glossary_terms(combined_chunk_text, schema)
    if matched_glossary:
        text_sections.append("Matched Domain Term Definitions (follow these classifications strictly):")
        for g in matched_glossary:
            text_sections.append(f"- {g.get('term')}: {g.get('definition')}")

    text_sections.append('Extract key financial numbers from ALL sections below into compact JSON {"r":[[...]]}:')

    per_unit_char_cap = max(1500, max_chars_per_call // max(1, len(chunk)))
    for unit in chunk:
        header = f"\n### [{unit.section_or_sheet} | page={unit.page_number or 1}]"
        body = (unit.text or "").strip()
        if len(body) > per_unit_char_cap:
            body = body[:per_unit_char_cap] + "\n...[truncated]"
        text_sections.append(header)
        if body:
            text_sections.append(body)
        elif use_vision and unit.image_jpeg_bytes:
            text_sections.append("(See attached image.)")

    return "\n".join(text_sections)


def chunk_units_for_llm(
    units: List[PageUnit],
    pages_per_call: int,
    max_chars_per_call: int,
) -> List[List[PageUnit]]:
    """
    Group PageUnits into LLM-sized batches obeying BOTH:
      - At most `pages_per_call` (3-5) pages per single Qwen3.8 call
      - At most `max_chars_per_call` text characters per single Qwen3.8 call
    """
    chunks: List[List[PageUnit]] = []
    current: List[PageUnit] = []
    current_chars = 0

    for unit in units:
        unit_chars = len(unit.text)
        exceeds_pages = len(current) >= pages_per_call
        exceeds_chars = bool(current) and (current_chars + unit_chars > max_chars_per_call)

        if exceeds_pages or exceeds_chars:
            chunks.append(current)
            current = [unit]
            current_chars = unit_chars
        else:
            current.append(unit)
            current_chars += unit_chars

    if current:
        chunks.append(current)
    return chunks


def _row_array_to_dict(arr: list[Any]) -> Optional[dict[str, Any]]:
    """Convert compact 10-element row array into normalized dict."""
    if len(arr) < 6:
        return None
    return {
        "document_type": arr[0] if len(arr) > 0 else "other",
        "section_or_sheet": arr[1] if len(arr) > 1 else "",
        "page_number": arr[2] if len(arr) > 2 else None,
        "entity_or_ticker": arr[3] if len(arr) > 3 else "",
        "metric_key": arr[4] if len(arr) > 4 else "",
        "value_raw": arr[5] if len(arr) > 5 else "",
        "currency": arr[6] if len(arr) > 6 else "",
        "unit": arr[7] if len(arr) > 7 else "",
        "as_of_date": arr[8] if len(arr) > 8 else "",
        "notes": arr[9] if len(arr) > 9 else "",
        "confidence": 0.92,
    }


def _normalize_parsed_container(obj: Any) -> List[dict[str, Any]]:
    rows = None
    if isinstance(obj, dict):
        if isinstance(obj.get("r"), list):
            rows = obj["r"]
        elif isinstance(obj.get("records"), list):
            rows = obj["records"]
    elif isinstance(obj, list):
        rows = obj

    if not rows:
        return []

    out: List[dict[str, Any]] = []
    for item in rows:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, list):
            converted = _row_array_to_dict(item)
            if converted:
                out.append(converted)
    return out


def _extract_json_records(raw_text: str) -> List[dict[str, Any]]:
    """Parse compact array-of-arrays or dict JSON records, with truncation recovery."""
    if not raw_text:
        return []
    text = raw_text.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        parsed = json.loads(text)
        res = _normalize_parsed_container(parsed)
        if res:
            return res
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            res = _normalize_parsed_container(parsed)
            if res:
                return res
        except json.JSONDecodeError:
            pass

    recovered: List[dict[str, Any]] = []
    arr_pos = text.find("[")
    if arr_pos != -1:
        decoder = json.JSONDecoder()
        idx = arr_pos + 1
        n = len(text)
        while idx < n:
            while idx < n and text[idx] in " \t\r\n,":
                idx += 1
            if idx >= n or text[idx] == "]":
                break
            if text[idx] not in "[{":
                idx += 1
                continue
            try:
                elem, next_idx = decoder.raw_decode(text, idx)
                if isinstance(elem, dict) and ("metric_key" in elem or "value_raw" in elem):
                    recovered.append(elem)
                elif isinstance(elem, list):
                    converted = _row_array_to_dict(elem)
                    if converted:
                        recovered.append(converted)
                idx = next_idx
            except json.JSONDecodeError:
                break
    return recovered


class QwenClient:
    """Async client for local Qwen3.8 with concurrency semaphore & deadline awareness."""

    def __init__(
        self,
        cfg: ConfigNode,
        semaphore: Optional[asyncio.Semaphore] = None,
        schema: Optional[dict[str, Any]] = None,
    ) -> None:
        self.cfg = cfg
        self.base_url = cfg.base_url.rstrip("/")
        self.semaphore = semaphore or asyncio.Semaphore(cfg.max_concurrent_calls)
        self.schema = schema if schema is not None else load_extraction_schema()

    async def health(self) -> dict:
        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/models", headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def extract_chunk(
        self,
        chunk: List[PageUnit],
        client_name: str,
        source_file: str,
        doc_type_hint: Optional[str],
        use_vision: bool,
        budget: DeadlineBudget,
        solution_mode: str = "small_pdf",
    ) -> List[ExtractedRecord]:
        """Run one bounded Qwen3.8 call on a 1..5 page/sheet chunk."""
        if not budget.has_soft_budget(min_needed_sec=2.0):
            logger.warning("Skipping LLM chunk due to SLA soft deadline (elapsed=%.1fs)", budget.elapsed)
            return []

        system_prompt = build_system_prompt(self.schema, doc_type_hint=doc_type_hint)
        user_text = build_user_prompt(
            chunk=chunk,
            client_name=client_name,
            source_file=source_file,
            doc_type_hint=doc_type_hint,
            solution_mode=solution_mode,
            schema=self.schema,
            use_vision=use_vision,
            max_chars_per_call=self.cfg.max_chars_per_call,
        )

        if use_vision and any(u.image_jpeg_bytes for u in chunk):
            user_content: Any = [{"type": "text", "text": user_text}]
            for unit in chunk:
                if unit.image_jpeg_bytes:
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": bytes_to_data_url(unit.image_jpeg_bytes)},
                        }
                    )
        else:
            user_content = user_text

        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
            "chat_template_kwargs": {"enable_thinking": self.cfg.enable_thinking},
        }

        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }

        async with self.semaphore:
            if not budget.has_soft_budget(min_needed_sec=1.5):
                return []

            call_timeout = min(self.cfg.request_timeout_sec, max(3.0, budget.remaining_hard - 1.5))
            async with httpx.AsyncClient(timeout=call_timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        raw_items = _extract_json_records(content)

        default_page = chunk[0].page_number if chunk else 1
        default_section = chunk[0].section_or_sheet if chunk else ""

        records: List[ExtractedRecord] = []
        for item in raw_items:
            metric_key = str(item.get("metric_key") or "").strip()
            value_raw = str(item.get("value_raw") or "").strip()
            if not metric_key or not value_raw:
                continue

            page_num = item.get("page_number")
            try:
                page_num_int = int(page_num) if page_num not in (None, "") else default_page
            except (TypeError, ValueError):
                page_num_int = default_page

            conf_raw = item.get("confidence", 0.90)
            try:
                conf = max(0.0, min(1.0, float(conf_raw)))
            except (TypeError, ValueError):
                conf = 0.90

            records.append(
                ExtractedRecord(
                    client_name=client_name,
                    source_file=source_file,
                    document_type=normalize_doc_type(item.get("document_type") or doc_type_hint),
                    section_or_sheet=str(item.get("section_or_sheet") or default_section).strip(),
                    page_number=page_num_int,
                    entity_or_ticker=str(item.get("entity_or_ticker") or "").strip(),
                    metric_key=metric_key,
                    value_raw=value_raw,
                    value_numeric=parse_numeric_value(value_raw),
                    currency=str(item.get("currency") or "").strip().upper(),
                    unit=str(item.get("unit") or "").strip(),
                    as_of_date=str(item.get("as_of_date") or "").strip(),
                    confidence=round(conf, 3),
                    notes=str(item.get("notes") or "").strip(),
                )
            )

        return records
