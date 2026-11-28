"""Domain schemas, SLA deadline tracker, deduplication, and CSV serialization."""

from __future__ import annotations

import csv
import io
import re
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from pydantic import BaseModel, Field

VALID_DOC_TYPES = {
    "investment",
    "funding",
    "bank_statement",
    "insurance",
    "liability",
    "income_tax",
    "real_estate",
    "mixed",
    "other",
}


class ExtractedRecord(BaseModel):
    record_id: int = 0
    client_name: str = ""
    source_file: str = ""
    document_type: str = "other"
    section_or_sheet: str = ""
    page_number: Optional[int] = None
    entity_or_ticker: str = ""
    metric_key: str = ""
    value_raw: str = ""
    value_numeric: Optional[float] = None
    currency: str = ""
    unit: str = ""
    as_of_date: str = ""
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    notes: str = ""


class ProcessingStats(BaseModel):
    file_kind: str
    total_pages_or_sheets: int
    selected_pages_or_sheets: List[str] = Field(default_factory=list)
    used_large_pdf_triage: bool = False
    ocr_pages_count: int = 0
    llm_calls_count: int = 0
    records_extracted: int = 0
    table_tiers: dict[str, int] = Field(default_factory=dict)
    elapsed_sec: float = 0.0
    sla_timeout_sec: float = 50.0
    within_sla: bool = True
    partial_due_to_sla: bool = False
    warnings: List[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    client_name: str
    source_file: str
    requested_document_type: Optional[str] = None
    detected_document_types: List[str] = Field(default_factory=list)
    records: List[ExtractedRecord] = Field(default_factory=list)
    stats: ProcessingStats


@dataclass
class PageUnit:
    """Normalized page or sheet content ready for triage or LLM extraction."""

    unit_id: str
    page_number: Optional[int]
    section_or_sheet: str
    text: str = ""
    image_jpeg_bytes: Optional[bytes] = None
    original_size: Optional[tuple[int, int]] = None
    resized_size: Optional[tuple[int, int]] = None
    ocr_used: bool = False
    parse_tier: str = ""
    signal_score: float = 0.0
    matched_signals: List[str] = field(default_factory=list)


class DeadlineBudget:
    """Monotonic wall-clock tracker to enforce the <50s sync API SLA."""

    def __init__(self, hard_limit_sec: float = 50.0, soft_margin_sec: float = 4.0) -> None:
        self.start_time = time.monotonic()
        self.hard_limit_sec = hard_limit_sec
        self.soft_limit_sec = max(5.0, hard_limit_sec - soft_margin_sec)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    @property
    def remaining_hard(self) -> float:
        return max(0.0, self.hard_limit_sec - self.elapsed)

    @property
    def remaining_soft(self) -> float:
        return max(0.0, self.soft_limit_sec - self.elapsed)

    def has_soft_budget(self, min_needed_sec: float = 1.5) -> bool:
        return self.remaining_soft >= min_needed_sec


_NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def parse_numeric_value(value_raw: Any) -> Optional[float]:
    """Best-effort conversion of formatted financial strings to float."""
    if value_raw is None:
        return None
    if isinstance(value_raw, (int, float)) and not isinstance(value_raw, bool):
        return float(value_raw)
    text = str(value_raw).strip()
    if not text:
        return None

    # Accounting negative format: (1,234.56) or ($1,234.56) or -$4,923.16 -> negative
    negative = False
    if (text.startswith("(") and text.endswith(")")) or re.match(r"^\s*-\s*(?:[A-Za-z]{0,3}[\$€£¥]|US\$|HK\$|SG\$|CA\$)", text):
        negative = True
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()
    elif text.startswith("-"):
        negative = True

    # Detect shorthand suffixes like 1.5M / 250K / 2.3B
    multiplier = 1.0
    lower = text.lower()
    if re.search(r"\d\s*b(?:n|illion)?\b", lower):
        multiplier = 1e9
    elif re.search(r"\d\s*m(?:n|illion)?\b", lower):
        multiplier = 1e6
    elif re.search(r"\d\s*k\b", lower):
        multiplier = 1e3

    match = _NUM_RE.search(text)
    if not match:
        return None
    try:
        num = float(match.group(0).replace(",", "")) * multiplier
        return -abs(num) if negative else num
    except ValueError:
        return None


def normalize_doc_type(doc_type: Optional[str]) -> str:
    if not doc_type:
        return "other"
    cleaned = doc_type.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "bank": "bank_statement",
        "checking": "bank_statement",
        "savings": "bank_statement",
        "brokerage": "investment",
        "portfolio": "investment",
        "equity": "investment",
        "stock": "investment",
        "stocks": "investment",
        "fund": "funding",
        "funds": "funding",
        "fundings": "funding",
        "venture": "funding",
        "life_insurance": "insurance",
        "policy": "insurance",
        "loan": "liability",
        "mortgage": "liability",
        "debt": "liability",
        "tax": "income_tax",
    }
    cleaned = aliases.get(cleaned, cleaned)
    return cleaned if cleaned in VALID_DOC_TYPES else "other"


def deduplicate_and_number(records: List[ExtractedRecord]) -> List[ExtractedRecord]:
    """Deduplicate identical key-value items across overlapping chunks and assign IDs."""
    seen: set[tuple] = set()
    unique: List[ExtractedRecord] = []
    for rec in records:
        key = (
            rec.source_file.strip().lower(),
            rec.document_type.strip().lower(),
            rec.section_or_sheet.strip().lower(),
            rec.page_number,
            rec.entity_or_ticker.strip().upper(),
            rec.metric_key.strip().lower(),
            rec.value_raw.strip(),
            rec.currency.strip().upper(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(rec)

    for idx, rec in enumerate(unique, start=1):
        rec.record_id = idx
    return unique


def records_to_csv(records: List[ExtractedRecord], columns: List[str]) -> str:
    """Serialize extracted financial records to RFC 4180 CSV text."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for rec in records:
        row = rec.model_dump()
        for k, v in list(row.items()):
            if v is None:
                row[k] = ""
        writer.writerow(row)
    return buf.getvalue()
