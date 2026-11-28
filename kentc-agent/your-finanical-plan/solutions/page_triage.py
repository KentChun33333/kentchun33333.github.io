"""
Financial page triage & PaddleOCR-assisted selection for large PDFs (> 9 pages).

Goals:
  - Quickly separate high-value numeric/tabular financial pages (holdings, balances,
    policy schedules, cash/surrender value tables, funding commitments) from
    boilerplate legal clauses / T&C / blank pages.
  - Guarantee triage completes well inside the 50s SLA budget even on 60-100 page
    scanned insurance PDFs.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional, Tuple

import pymupdf

from solutions import ConfigNode, load_extraction_schema
from solutions.image_utils import render_pdf_page_to_jpeg
from solutions.models import DeadlineBudget, PageUnit
from solutions.ocr_client import PaddleOCRClient

logger = logging.getLogger(__name__)

# Monetary / numeric patterns
_CURRENCY_AMOUNT_RE = re.compile(
    r"(?:US\$|HK\$|SG\$|CA\$|AU\$|NT\$|RMB|CNY|USD|HKD|SGD|CAD|EUR|GBP|JPY|[\$€£¥])\s*[-+]?\d[\d,]*(?:\.\d+)?"
    r"|\b\d{1,3}(?:,\d{3})+(?:\.\d{1,4})?\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
_TICKER_RE = re.compile(r"\b[A-Z]{2,5}(?:\.[A-Z]{1,2})?\b")

# Domain keyword weights
_HIGH_VALUE_KEYWORDS: List[Tuple[str, float]] = [
    # Investment / Brokerage
    ("market value", 3.0),
    ("cost basis", 2.5),
    ("unrealized", 2.0),
    ("holdings", 2.5),
    ("portfolio summary", 3.5),
    ("account value", 3.5),
    ("asset allocation", 2.5),
    ("total value", 3.0),
    ("equities", 2.0),
    ("fixed income", 2.0),
    ("dividend", 2.0),
    ("ticker", 2.5),
    ("symbol", 1.8),
    ("cusip", 2.0),
    ("shares", 2.0),
    ("quantity", 1.8),
    ("nav", 1.8),
    # Funding / Private investment
    ("funding", 2.5),
    ("series a", 2.5),
    ("series b", 2.5),
    ("series c", 2.5),
    ("seed round", 2.5),
    ("valuation", 2.5),
    ("commitment", 2.5),
    ("capital call", 2.5),
    ("invested amount", 3.0),
    ("investment amount", 3.0),
    # Bank statement
    ("beginning balance", 3.5),
    ("ending balance", 3.5),
    ("opening balance", 3.5),
    ("closing balance", 3.5),
    ("account summary", 3.5),
    ("total deposits", 3.0),
    ("total withdrawals", 3.0),
    ("checking", 1.8),
    ("savings", 1.8),
    ("interest earned", 2.0),
    ("statement period", 2.0),
    # Insurance (crucial for 60-100 page policies!)
    ("policy schedule", 4.5),
    ("schedule of benefits", 4.5),
    ("benefit summary", 4.0),
    ("policy summary", 4.0),
    ("sum assured", 4.5),
    ("face amount", 4.0),
    ("death benefit", 3.5),
    ("annual premium", 4.5),
    ("modal premium", 3.5),
    ("total premium", 4.0),
    ("planned premium", 3.5),
    ("cash value", 4.0),
    ("surrender value", 4.0),
    ("guaranteed value", 3.5),
    ("non-guaranteed", 2.5),
    ("policy number", 3.0),
    ("policy date", 2.0),
    ("maturity date", 2.5),
    ("deductible", 2.5),
    ("coverage limit", 3.0),
    ("rider", 2.0),
    ("table of values", 4.5),
    ("illustration", 2.5),
]

_BOILERPLATE_PENALTIES: List[Tuple[str, float]] = [
    ("table of contents", -4.0),
    ("general provisions", -2.5),
    ("definitions", -2.0),
    ("governing law", -2.5),
    ("entire contract", -2.0),
    ("incontestability", -2.0),
    ("suicide exclusion", -2.0),
    ("misstatement of age", -2.0),
    ("privacy notice", -3.0),
    ("important disclosures", -2.5),
    ("terms and conditions", -2.5),
    ("this page intentionally left blank", -8.0),
    ("intentionally left blank", -8.0),
]


def _load_schema_keywords(schema: Optional[dict[str, Any]]) -> List[Tuple[str, float]]:
    """Read triage keyword weights + glossary aliases from extraction_schema.yaml."""
    if not schema:
        return _HIGH_VALUE_KEYWORDS
    merged: dict[str, float] = {}
    for spec in (schema.get("document_types") or {}).values():
        for kw, wt in (spec.get("triage_keywords") or {}).items():
            merged[str(kw).lower()] = max(merged.get(str(kw).lower(), 0.0), float(wt))
    for entry in schema.get("domain_glossary") or []:
        for alias in entry.get("aliases") or []:
            a = str(alias).strip().lower()
            if len(a) >= 3:
                merged[a] = max(merged.get(a, 0.0), 2.5)
    return list(merged.items()) if merged else _HIGH_VALUE_KEYWORDS


def score_financial_page(
    text: str,
    doc_type_hint: Optional[str] = None,
    keywords: Optional[List[Tuple[str, float]]] = None,
) -> Tuple[float, List[str]]:
    """
    Compute a transparent financial relevance score for a single page's text.
    Higher score = denser key numbers, financial tables, and summary headers.
    """
    if not text or len(text.strip()) < 15:
        return 0.0, []

    lower = text.lower()
    score = 0.0
    signals: List[str] = []

    # 1. Currency & comma-formatted numbers (capped so giant tx logs don't drown summaries)
    amounts = _CURRENCY_AMOUNT_RE.findall(text)
    if amounts:
        amount_pts = min(14.0, len(amounts) * 1.15)
        score += amount_pts
        signals.append(f"amounts:{len(amounts)}")

    # 2. Percentages (yields, rates, allocations, riders)
    pcts = _PERCENT_RE.findall(text)
    if pcts:
        score += min(4.0, len(pcts) * 0.6)
        signals.append(f"pct:{len(pcts)}")

    # 3. Domain keywords (driven dynamically from extraction_schema.yaml)
    kw_hits = 0
    for kw, weight in (keywords if keywords is not None else _HIGH_VALUE_KEYWORDS):
        if kw in lower:
            score += weight
            kw_hits += 1
            if len(signals) < 8:
                signals.append(kw)

    # Extra boost if user hinted a specific document type
    if doc_type_hint:
        hint = doc_type_hint.lower()
        if "insur" in hint and any(k in lower for k in ("premium", "sum assured", "face amount", "cash value", "surrender", "death benefit", "policy schedule")):
            score += 3.0
        elif "invest" in hint and any(k in lower for k in ("market value", "holdings", "shares", "cost basis", "portfolio", "ticker", "dividend")):
            score += 3.0
        elif "bank" in hint and any(k in lower for k in ("balance", "deposit", "withdrawal", "checking", "savings")):
            score += 3.0
        elif "fund" in hint and any(k in lower for k in ("funding", "valuation", "commitment", "series", "invested")):
            score += 3.0

    # 4. Tabular line bonus (lines containing multiple numbers or pipe separators)
    numeric_lines = 0
    for line in text.splitlines():
        if len(_CURRENCY_AMOUNT_RE.findall(line)) >= 2 or ("|" in line and any(c.isdigit() for c in line)):
            numeric_lines += 1
    if numeric_lines >= 3:
        score += min(6.0, numeric_lines * 0.5)
        signals.append(f"table_rows:{numeric_lines}")

    # 5. Boilerplate legal prose penalty when numeric density is very low
    for phrase, pen in _BOILERPLATE_PENALTIES:
        if phrase in lower:
            # Reduce penalty if page genuinely has rich numeric tables despite legal heading
            eff_pen = pen if len(amounts) < 6 else pen * 0.35
            score += eff_pen

    # Dense prose penalty: long text with almost no numbers is almost certainly legal T&C
    if len(text) > 1200 and len(amounts) <= 1 and kw_hits <= 1:
        score -= 3.0

    return round(max(0.0, score), 2), signals


def _priority_scan_order(indices: List[int]) -> List[int]:
    """
    Order scanned pages so schedules/summaries (front), value tables (back),
    and evenly distributed pages get OCR'd first if a 100-page scanned PDF approaches SLA.
    """
    if len(indices) <= 20:
        return indices
    ordered: List[int] = []
    seen: set[int] = set()

    def _add(i: int) -> None:
        if i not in seen:
            seen.add(i)
            ordered.append(i)

    # Front 10 pages (cover, policy schedule, summary)
    for i in indices[:10]:
        _add(i)
    # Last 8 pages (benefit/cash value/surrender tables, appendices)
    for i in indices[-8:]:
        _add(i)
    # Even stride across middle pages
    step = max(2, len(indices) // 16)
    for i in indices[::step]:
        _add(i)
    # Remaining pages in natural order
    for i in indices:
        _add(i)
    return ordered


def _clean_markdown_table(md: str) -> str:
    """Compact PyMuPDF Markdown tables so tokens stay lean and cell values stay on one row."""
    cleaned_lines: List[str] = []
    for ln in md.splitlines():
        ln = ln.replace("<br>", " ").replace("<br/>", " ").strip()
        if ln:
            cleaned_lines.append(" ".join(ln.split()))
    return "\n".join(cleaned_lines)


def _extract_table_aware_digital_page(page: pymupdf.Page) -> Tuple[str, str]:
    """
    Minimal table-aware extractor for digital PDF pages:
      - If ruled tables exist (`page.find_tables()`): column-locked Markdown tables + non-table text.
      - Otherwise: visual reading-order `page.get_text("text", sort=True)`.
    """
    valid_tables = []
    try:
        found = page.find_tables()
        valid_tables = [t for t in (found.tables or []) if t.row_count >= 2 and t.col_count >= 2]
    except Exception as exc:
        logger.debug("find_tables() fallback on page %s: %s", page.number + 1, exc)

    if valid_tables:
        table_rects = [pymupdf.Rect(t.bbox) for t in valid_tables]
        non_table_parts: List[str] = []
        blocks = sorted(page.get_text("blocks"), key=lambda b: (round(b[1] / 6.0), b[0]))
        for b in blocks:
            if b[6] != 0:
                continue
            cx, cy = (b[0] + b[2]) * 0.5, (b[1] + b[3]) * 0.5
            if any(r.contains(pymupdf.Point(cx, cy)) for r in table_rects):
                continue
            txt = (b[4] or "").strip()
            if txt:
                non_table_parts.append(txt)

        md_blocks = []
        for idx, tb in enumerate(valid_tables, start=1):
            md = _clean_markdown_table(tb.to_markdown())
            if md:
                md_blocks.append(f"[Table {idx} ({tb.row_count}x{tb.col_count})]\n{md}")

        sections = []
        if non_table_parts:
            sections.append("\n".join(non_table_parts))
        if md_blocks:
            sections.append("\n\n".join(md_blocks))
        return "\n\n".join(sections).strip(), "markdown_table"

    return (page.get_text("text", sort=True) or "").strip(), "sorted_text"


async def extract_and_triage_pdf_pages(
    pdf_bytes: bytes,
    cfg: ConfigNode,
    ocr_client: PaddleOCRClient,
    budget: DeadlineBudget,
    doc_type_hint: Optional[str] = None,
    schema: Optional[dict[str, Any]] = None,
) -> Tuple[List[PageUnit], int, bool, int, List[str]]:
    """
    Parse a PDF into PageUnits.

    Returns:
        (selected_units, total_pages, used_large_triage, ocr_pages_count, warnings)
    """
    warnings: List[str] = []
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        return [], 0, False, 0, ["PDF contains 0 pages"]

    is_large_pdf = total_pages > cfg.pdf.large_pdf_page_threshold
    pages: List[PageUnit] = []
    pages_needing_ocr: List[int] = []

    # Step 1: Fast PyMuPDF embedded text probe across all pages (~5-20ms even for 100 pages)
    for idx in range(total_pages):
        page = doc[idx]
        embedded_text = (page.get_text("text") or "").strip()
        unit = PageUnit(
            unit_id=f"page_{idx + 1}",
            page_number=idx + 1,
            section_or_sheet=f"Page {idx + 1}",
            text=embedded_text,
        )
        pages.append(unit)

        needs_ocr = len(embedded_text) < cfg.pdf.min_embedded_chars_per_page
        if is_large_pdf and cfg.pdf.force_paddle_ocr_for_large_pdf:
            needs_ocr = True
        if needs_ocr:
            pages_needing_ocr.append(idx)

    # Step 2: Run locally hosted PaddleOCR on scanned pages (clamped to <= 1024px)
    ocr_pages_count = 0
    if pages_needing_ocr:
        scan_order = _priority_scan_order(pages_needing_ocr)
        # Allocate at most 48% of remaining soft budget to OCR triage so Qwen3.8 always has time
        ocr_deadline_elapsed = budget.elapsed + min(24.0, budget.remaining_soft * 0.48)
        batch_size = max(4, cfg.paddle_ocr.batch_concurrency * 2)

        for start in range(0, len(scan_order), batch_size):
            if budget.elapsed >= ocr_deadline_elapsed:
                skipped = len(scan_order) - start
                warnings.append(
                    f"SLA guard stopped PaddleOCR triage after {ocr_pages_count} scanned pages "
                    f"({skipped} lower-priority pages skipped to preserve LLM extraction time)."
                )
                break

            batch_indices = scan_order[start : start + batch_size]
            batch_payload: List[Tuple[str, bytes]] = []
            for p_idx in batch_indices:
                jpeg_bytes, orig_sz, res_sz = render_pdf_page_to_jpeg(
                    doc[p_idx],
                    dpi=cfg.pdf.render_dpi,
                    max_dimension=min(cfg.image.max_dimension, cfg.pdf.triage_render_max_dim),
                    jpeg_quality=cfg.image.jpeg_quality,
                )
                pages[p_idx].image_jpeg_bytes = jpeg_bytes
                pages[p_idx].original_size = orig_sz
                pages[p_idx].resized_size = res_sz
                batch_payload.append((pages[p_idx].unit_id, jpeg_bytes))

            remaining_for_call = max(3.0, ocr_deadline_elapsed - budget.elapsed)
            try:
                ocr_map = await ocr_client.ocr_batch(
                    batch_payload,
                    timeout=min(cfg.paddle_ocr.timeout_sec, remaining_for_call + 2.0),
                    chunk_size=batch_size,
                )
                for p_idx in batch_indices:
                    uid = pages[p_idx].unit_id
                    ocr_text = (ocr_map.get(uid) or "").strip()
                    if ocr_text:
                        pages[p_idx].text = ocr_text
                    pages[p_idx].ocr_used = True
                    ocr_pages_count += 1
            except Exception as exc:
                warnings.append(f"PaddleOCR batch failed on pages {[i + 1 for i in batch_indices]}: {exc}")
                logger.warning("PaddleOCR batch failed: %s", exc)
                break

    # Step 3: Score all pages using YAML-configured keywords & select top-K if > 9 pages
    schema_keywords = _load_schema_keywords(schema or load_extraction_schema(cfg))
    for unit in pages:
        score, sigs = score_financial_page(unit.text, doc_type_hint=doc_type_hint, keywords=schema_keywords)
        unit.signal_score = score
        unit.matched_signals = sigs

    if is_large_pdf:
        # Select highest-signal pages up to max_selected_pages while preserving document order
        ranked = sorted(pages, key=lambda u: (-u.signal_score, u.page_number or 0))
        qualified = [u for u in ranked if u.signal_score >= cfg.pdf.min_page_signal_score]
        if not qualified:
            # Fallback: never return 0 pages on unusual documents; take top 3 non-empty pages
            qualified = [u for u in ranked if u.text.strip()][:3]
            warnings.append("No pages exceeded signal threshold; fell back to top non-empty pages.")

        selected = qualified[: cfg.pdf.max_selected_pages]
        selected.sort(key=lambda u: u.page_number or 0)
    else:
        # Small PDF (<= 9 pages): keep all non-empty pages
        selected = [u for u in pages if u.text.strip() or u.image_jpeg_bytes is not None]
        if not selected:
            selected = pages[: cfg.pdf.max_selected_pages]

    # Step 4: Table-aware Markdown extraction on selected digital pages (simple 2-path: digital Markdown vs scanned OCR)
    table_aware = bool(cfg.pdf.get("table_aware_extraction", True))

    for unit in selected:
        if unit.ocr_used:
            unit.parse_tier = "paddle_ocr"
        elif table_aware and unit.page_number is not None and budget.has_soft_budget(min_needed_sec=6.0):
            rich_text, tier = _extract_table_aware_digital_page(doc[unit.page_number - 1])
            if rich_text:
                unit.text = rich_text
            unit.parse_tier = tier
        else:
            unit.parse_tier = "sorted_text"

        if cfg.llm.prefer_vision_for_pdf and unit.image_jpeg_bytes is None and unit.page_number is not None:
            jpeg_bytes, orig_sz, res_sz = render_pdf_page_to_jpeg(
                doc[unit.page_number - 1],
                dpi=cfg.pdf.render_dpi,
                max_dimension=cfg.image.max_dimension,
                jpeg_quality=cfg.image.jpeg_quality,
            )
            unit.image_jpeg_bytes = jpeg_bytes
            unit.original_size = orig_sz
            unit.resized_size = res_sz

    doc.close()
    return selected, total_pages, is_large_pdf, ocr_pages_count, warnings
