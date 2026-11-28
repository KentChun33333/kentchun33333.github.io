"""
Unified extraction pipeline orchestrating PDF, Image, and Excel financial documents
within the 50-second synchronous API SLA.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from solutions import ConfigNode, load_extraction_schema
from solutions.excel_parser import parse_excel_to_units
from solutions.image_utils import normalize_image_bytes
from solutions.models import (
    DeadlineBudget,
    ExtractedRecord,
    ExtractionResult,
    PageUnit,
    ProcessingStats,
    deduplicate_and_number,
    records_to_csv,
)
from solutions.ocr_client import PaddleOCRClient
from solutions.page_triage import extract_and_triage_pdf_pages
from solutions.qwen_client import QwenClient, chunk_units_for_llm

logger = logging.getLogger(__name__)

PDF_EXTS = {".pdf"}
IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".heic",
    ".heif",
    ".webm",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
    ".avif",
}
EXCEL_EXTS = {".xlsx", ".xlsm"}


def detect_file_kind(filename: str, content_type: Optional[str] = None) -> str:
    ext = Path(filename).suffix.lower()
    ct = (content_type or "").lower()
    if ext in PDF_EXTS or "pdf" in ct:
        return "pdf"
    if ext in EXCEL_EXTS or "spreadsheet" in ct or "excel" in ct:
        return "excel"
    if ext in IMAGE_EXTS or ct.startswith("image/") or ct == "video/webm":
        return "image"
    raise ValueError(
        f"Unsupported file format '{ext or content_type}'. "
        "Supported: PDF, Images/WebM (JPG, PNG, HEIC, HEIF, WEBP, WEBM, TIFF, BMP, GIF, AVIF), XLSX/XLSM Excel."
    )


async def process_document(
    file_bytes: bytes,
    filename: str,
    client_name: str,
    cfg: ConfigNode,
    document_type: Optional[str] = None,
    content_type: Optional[str] = None,
    llm_semaphore: Optional[asyncio.Semaphore] = None,
) -> Tuple[ExtractionResult, str]:
    """
    End-to-end financial key-value extraction for one document.

    Returns:
        (ExtractionResult, csv_text)
    """
    budget = DeadlineBudget(
        hard_limit_sec=cfg.server.sla_timeout_sec,
        soft_margin_sec=cfg.server.soft_deadline_margin_sec,
    )

    file_kind = detect_file_kind(filename, content_type=content_type)
    schema = load_extraction_schema(cfg)
    ocr_client = PaddleOCRClient(cfg.paddle_ocr)
    qwen_client = QwenClient(cfg.llm, semaphore=llm_semaphore, schema=schema)

    units: List[PageUnit] = []
    total_units = 0
    used_large_triage = False
    ocr_pages_count = 0
    warnings: List[str] = []
    use_vision = False
    solution_mode = "small_pdf"

    if file_kind == "pdf":
        units, total_units, used_large_triage, ocr_pages_count, pdf_warnings = (
            await extract_and_triage_pdf_pages(
                pdf_bytes=file_bytes,
                cfg=cfg,
                ocr_client=ocr_client,
                budget=budget,
                doc_type_hint=document_type,
                schema=schema,
            )
        )
        warnings.extend(pdf_warnings)
        use_vision = cfg.llm.prefer_vision_for_pdf
        solution_mode = "large_pdf_triage" if used_large_triage else "small_pdf"

    elif file_kind == "excel":
        # Excel: cell-only, multi-sheet, no embedded images -> local Qwen3.8 only
        units, total_units, xl_warnings = parse_excel_to_units(file_bytes, cfg)
        warnings.extend(xl_warnings)
        use_vision = False
        solution_mode = "excel"

    elif file_kind == "image":
        solution_mode = "image_media"
        # Image / WebM: clamp max(w, h) <= 1024px -> PaddleOCR text + optional Qwen3.8 vision
        jpeg_bytes, orig_sz, resized_sz = normalize_image_bytes(
            file_bytes,
            max_dimension=cfg.image.max_dimension,
            jpeg_quality=cfg.image.jpeg_quality,
            filename=filename,
        )
        ocr_text = ""
        try:
            ocr_text = await ocr_client.ocr_image(
                jpeg_bytes,
                filename=f"{Path(filename).stem}.jpg",
                timeout=min(cfg.paddle_ocr.timeout_sec, max(4.0, budget.remaining_soft * 0.4)),
            )
            ocr_pages_count = 1
        except Exception as exc:
            warnings.append(f"PaddleOCR unavailable for image ({exc}); falling back to Qwen3.8 vision.")
            logger.warning("PaddleOCR image OCR failed: %s", exc)

        units = [
            PageUnit(
                unit_id="image_1",
                page_number=1,
                section_or_sheet="Image",
                text=ocr_text,
                image_jpeg_bytes=jpeg_bytes,
                original_size=orig_sz,
                resized_size=resized_sz,
                ocr_used=bool(ocr_text),
                signal_score=10.0,
            )
        ]
        total_units = 1
        use_vision = cfg.llm.vision_for_images or not bool(ocr_text)

    # Chunk units strictly respecting pages_per_call (3-5) and max_chars_per_call
    chunks = chunk_units_for_llm(
        units,
        pages_per_call=cfg.llm.pages_per_call,
        max_chars_per_call=cfg.llm.max_chars_per_call,
    )

    all_records: List[ExtractedRecord] = []
    partial_due_to_sla = False
    llm_calls_count = 0

    async def _run_chunk(chunk_idx: int, chunk: List[PageUnit]) -> List[ExtractedRecord]:
        nonlocal llm_calls_count, partial_due_to_sla
        if not budget.has_soft_budget(min_needed_sec=2.0):
            partial_due_to_sla = True
            return []
        llm_calls_count += 1
        try:
            return await qwen_client.extract_chunk(
                chunk=chunk,
                client_name=client_name,
                source_file=filename,
                doc_type_hint=document_type,
                use_vision=use_vision,
                budget=budget,
                solution_mode=solution_mode,
            )
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            warnings.append(f"LLM chunk {chunk_idx + 1}/{len(chunks)} error: {err_msg}")
            logger.warning("LLM chunk %d failed for %s: %s", chunk_idx + 1, filename, err_msg)
            return []

    if chunks:
        # Execute chunks concurrently under the shared semaphore + hard SLA wait_for guard
        tasks = [asyncio.create_task(_run_chunk(i, ch)) for i, ch in enumerate(chunks)]
        wait_limit = max(2.0, budget.remaining_hard - 1.0)
        done, pending = await asyncio.wait(tasks, timeout=wait_limit)

        for t in done:
            try:
                all_records.extend(t.result())
            except Exception as exc:
                warnings.append(f"Chunk task exception: {exc}")

        if pending:
            partial_due_to_sla = True
            warnings.append(
                f"SLA deadline reached ({cfg.server.sla_timeout_sec}s): cancelled {len(pending)} pending LLM chunk(s) "
                "and returned extracted records gathered so far."
            )
            for p in pending:
                p.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

    deduped = deduplicate_and_number(all_records)
    detected_types = sorted({r.document_type for r in deduped if r.document_type})
    elapsed = round(budget.elapsed, 3)

    tier_counts: dict[str, int] = {}
    for u in units:
        if u.parse_tier:
            tier_counts[u.parse_tier] = tier_counts.get(u.parse_tier, 0) + 1

    stats = ProcessingStats(
        file_kind=file_kind,
        total_pages_or_sheets=total_units,
        selected_pages_or_sheets=[u.section_or_sheet for u in units],
        used_large_pdf_triage=used_large_triage,
        ocr_pages_count=ocr_pages_count,
        llm_calls_count=llm_calls_count,
        records_extracted=len(deduped),
        table_tiers=tier_counts,
        elapsed_sec=elapsed,
        sla_timeout_sec=cfg.server.sla_timeout_sec,
        within_sla=elapsed <= cfg.server.sla_timeout_sec,
        partial_due_to_sla=partial_due_to_sla,
        warnings=warnings,
    )

    result = ExtractionResult(
        client_name=client_name,
        source_file=filename,
        requested_document_type=document_type,
        detected_document_types=detected_types,
        records=deduped,
        stats=stats,
    )
    csv_text = records_to_csv(deduped, cfg.csv.columns)
    return result, csv_text
