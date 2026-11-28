"""
Synchronous Financial Document Key-Value Extraction API (<50s SLA).

Endpoints:
  GET  /health        - Service & local dependency status (Qwen3.8 + PaddleOCR)
  POST /extract       - Upload (name, file, optional document_type) -> CSV (or JSON via ?format=json)
  POST /extract/json  - Same upload, always returns JSON payload including `csv`, `records`, `stats`

Run:
  .venv/bin/python app.py
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Literal, Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from solutions import load_config, load_extraction_schema
from solutions.ocr_client import PaddleOCRClient
from solutions.pipeline import process_document
from solutions.qwen_client import QwenClient, build_system_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("financial_plan_api")

cfg = load_config()
# Shared global semaphore capping simultaneous Qwen3.8 calls across requests
GLOBAL_LLM_SEMAPHORE = asyncio.Semaphore(cfg.llm.max_concurrent_calls)

app = FastAPI(
    title="your-finanical-plan Extraction API",
    description=(
        "Synchronous financial key-value extraction backend powered exclusively by local Qwen3.8 "
        "and self-hosted local PaddleOCR. Outputs standardized CSV within a 50-second SLA."
    ),
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict:
    qwen_status: dict = {"url": cfg.llm.base_url, "model": cfg.llm.model, "ok": False}
    ocr_status: dict = {"url": cfg.paddle_ocr.base_url, "ok": False}

    try:
        qwen_client = QwenClient(cfg.llm, semaphore=GLOBAL_LLM_SEMAPHORE)
        models = await qwen_client.health()
        qwen_status["ok"] = True
        qwen_status["loaded_models"] = [m.get("id") for m in models.get("data", [])]
    except Exception as exc:
        qwen_status["error"] = str(exc)

    try:
        ocr_client = PaddleOCRClient(cfg.paddle_ocr)
        ocr_info = await ocr_client.health()
        ocr_status["ok"] = True
        ocr_status["engine"] = ocr_info.get("engine")
    except Exception as exc:
        ocr_status["error"] = str(exc)

    return {
        "status": "ok" if (qwen_status["ok"] and ocr_status["ok"]) else "degraded",
        "sla_timeout_sec": cfg.server.sla_timeout_sec,
        "constraints": {
            "large_pdf_page_threshold": cfg.pdf.large_pdf_page_threshold,
            "pages_per_llm_call": cfg.llm.pages_per_call,
            "max_image_dimension": cfg.image.max_dimension,
            "max_concurrent_llm_calls": cfg.llm.max_concurrent_calls,
        },
        "dependencies": {
            "qwen3_8": qwen_status,
            "paddle_ocr": ocr_status,
        },
    }


async def _handle_extract(
    name: str,
    file: UploadFile,
    document_type: Optional[str],
):
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=422, detail="'name' must not be empty.")

    filename = file.filename or "uploaded_document"
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_bytes = cfg.server.max_upload_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {cfg.server.max_upload_mb} MB limit.",
        )

    doc_type_clean = document_type.strip() if document_type and document_type.strip() else None

    try:
        result, csv_text = await process_document(
            file_bytes=raw_bytes,
            filename=filename,
            client_name=clean_name,
            cfg=cfg,
            document_type=doc_type_clean,
            content_type=file.content_type,
            llm_semaphore=GLOBAL_LLM_SEMAPHORE,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Extraction failed for %s", filename)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc

    return result, csv_text


@app.get("/schema")
async def get_schema() -> dict:
    """Return the active YAML extraction schema (document types, keys, definitions, triage weights)."""
    return load_extraction_schema(cfg)


@app.get("/prompts")
async def get_compiled_prompts(
    document_type: Optional[str] = Query(
        default=None,
        description="Optional document_type hint to preview the prioritized system prompt",
    ),
) -> dict:
    """Preview the live compiled Qwen3.8 system prompt and all 4 per-solution prompt preambles."""
    schema = load_extraction_schema(cfg)
    return {
        "schema_file": cfg.extraction.schema_file,
        "document_type_hint": document_type,
        "system_prompt": build_system_prompt(schema, doc_type_hint=document_type),
        "solution_contexts": schema.get("prompt_settings", {}).get("solution_contexts", {}),
        "document_types": list((schema.get("document_types") or {}).keys()),
        "domain_glossary_terms": [g.get("term") for g in (schema.get("domain_glossary") or [])],
    }


@app.post("/extract")
async def extract_document(
    name: str = Form(..., description="Client or owner name"),
    file: UploadFile = File(..., description="Financial document (PDF, JPG/PNG/HEIC/WEBP/WEBM/TIFF, or XLSX)"),
    document_type: Optional[str] = Form(
        default=None,
        description="Optional hint: investment, funding, bank_statement, insurance, mixed (auto-detected if omitted)",
    ),
    output_format: Literal["csv", "json"] = Query(
        default="csv",
        alias="format",
        description="Return raw CSV (default) or JSON envelope containing records + csv + stats",
    ),
):
    result, csv_text = await _handle_extract(name=name, file=file, document_type=document_type)
    stats = result.stats

    headers = {
        "X-Elapsed-Sec": f"{stats.elapsed_sec:.3f}",
        "X-Within-SLA": str(stats.within_sla).lower(),
        "X-Partial-Due-To-SLA": str(stats.partial_due_to_sla).lower(),
        "X-Records-Count": str(stats.records_extracted),
        "X-Total-Units": str(stats.total_pages_or_sheets),
        "X-Large-PDF-Triage": str(stats.used_large_pdf_triage).lower(),
        "X-OCR-Pages": str(stats.ocr_pages_count),
        "X-LLM-Calls": str(stats.llm_calls_count),
        "X-Table-Tiers": ",".join(f"{k}:{v}" for k, v in sorted(stats.table_tiers.items())),
        "X-Detected-Types": ",".join(result.detected_document_types),
    }

    if output_format == "json":
        return JSONResponse(
            content={
                "result": result.model_dump(),
                "csv": csv_text,
            },
            headers=headers,
        )

    out_stem = Path(result.source_file).stem or "extracted"
    headers["Content-Disposition"] = f'attachment; filename="{out_stem}_extracted.csv"'
    return Response(content=csv_text, media_type="text/csv; charset=utf-8", headers=headers)


@app.post("/extract/json")
async def extract_document_json(
    name: str = Form(..., description="Client or owner name"),
    file: UploadFile = File(..., description="Financial document (PDF, JPG/PNG/HEIC/WEBP/WEBM/TIFF, or XLSX)"),
    document_type: Optional[str] = Form(default=None, description="Optional document type hint"),
):
    return await extract_document(
        name=name,
        file=file,
        document_type=document_type,
        output_format="json",
    )


def main() -> None:
    host = os.environ.get("API_HOST", cfg.server.host)
    port = int(os.environ.get("API_PORT", cfg.server.port))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
