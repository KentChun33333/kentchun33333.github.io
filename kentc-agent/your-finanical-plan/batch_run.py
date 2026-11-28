"""
Batch runner for financial document key-value extraction.

Strict concurrency guarantee:
  `--workers` accepts 1..4 and creates ONE global asyncio.Semaphore(workers) shared
  across all files and all chunked LLM calls, ensuring at most `workers` simultaneous
  in-flight calls to local Qwen3.8 at any moment.

Usage:
  .venv/bin/python batch_run.py --input-dir dataset --output-dir outputs --name "Kent Chiu" --workers 4
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

from solutions import load_config
from solutions.models import ExtractedRecord, deduplicate_and_number, records_to_csv
from solutions.pipeline import EXCEL_EXTS, IMAGE_EXTS, PDF_EXTS, process_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_run")

SUPPORTED_EXTS = PDF_EXTS | IMAGE_EXTS | EXCEL_EXTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch financial key-value extractor (local Qwen3.8 + PaddleOCR)."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("dataset"),
        help="Directory (or single file path) containing financial documents.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory to write per-document CSVs, combined CSV, and batch_summary.json.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="Client",
        help="Client name recorded in the CSV output.",
    )
    parser.add_argument(
        "--document-type",
        type=str,
        default=None,
        help="Optional document type hint (auto-detected per row if omitted).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Max concurrent Qwen3.8 LLM calls (allowed range: 1 to 4).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*",
        help="Optional filename glob filter inside --input-dir (e.g. '*.pdf').",
    )
    return parser.parse_args()


def collect_files(input_path: Path, pattern: str) -> List[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in SUPPORTED_EXTS else []
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    files = [
        p
        for p in sorted(input_path.glob(pattern))
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    ]
    return files


async def run_batch(
    files: List[Path],
    output_dir: Path,
    client_name: str,
    document_type: Optional[str],
    workers: int,
    config_path: Path,
) -> dict:
    cfg = load_config(config_path)
    if not (1 <= workers <= cfg.batch.max_workers):
        raise ValueError(f"--workers must be between 1 and {cfg.batch.max_workers}, got {workers}")

    # Offline batch runs may queue up to `workers` concurrent calls on a local LLM;
    # use the generous batch per-file timeout instead of the 50s sync API SLA.
    cfg.server.sla_timeout_sec = cfg.batch.per_file_timeout_sec
    cfg.llm.request_timeout_sec = cfg.batch.per_file_timeout_sec

    output_dir.mkdir(parents=True, exist_ok=True)

    # Global Qwen3.8 concurrency cap across ALL files and ALL chunks
    global_qwen_sem = asyncio.Semaphore(workers)
    # Cap simultaneous file-level tasks as well to bound RAM for large PDFs
    file_sem = asyncio.Semaphore(workers)

    t_start = time.monotonic()
    combined_records: List[ExtractedRecord] = []
    file_reports: List[dict] = []

    async def _process_one(path: Path) -> None:
        async with file_sem:
            logger.info("Start: %s", path.name)
            try:
                raw_bytes = path.read_bytes()
                result, csv_text = await process_document(
                    file_bytes=raw_bytes,
                    filename=path.name,
                    client_name=client_name,
                    cfg=cfg,
                    document_type=document_type,
                    llm_semaphore=global_qwen_sem,
                )
                out_csv = output_dir / f"{path.stem}.csv"
                out_csv.write_text(csv_text, encoding="utf-8")

                combined_records.extend(result.records)
                st = result.stats
                logger.info(
                    "Done : %s | kind=%s | units=%d (selected=%d) | ocr=%d | llm_calls=%d | rows=%d | %.2fs | sla=%s",
                    path.name,
                    st.file_kind,
                    st.total_pages_or_sheets,
                    len(st.selected_pages_or_sheets),
                    st.ocr_pages_count,
                    st.llm_calls_count,
                    st.records_extracted,
                    st.elapsed_sec,
                    "PASS" if st.within_sla else "OVER",
                )
                file_reports.append(
                    {
                        "file": path.name,
                        "status": "ok",
                        "csv_path": str(out_csv),
                        "detected_document_types": result.detected_document_types,
                        "stats": st.model_dump(),
                    }
                )
            except Exception as exc:
                logger.exception("Failed: %s", path.name)
                file_reports.append(
                    {
                        "file": path.name,
                        "status": "error",
                        "error": str(exc),
                    }
                )

    await asyncio.gather(*(_process_one(f) for f in files))

    # Write combined deduplicated CSV across the whole batch
    all_deduped = deduplicate_and_number(combined_records)
    combined_csv_path = output_dir / "combined_financial_plan.csv"
    combined_csv_path.write_text(records_to_csv(all_deduped, cfg.csv.columns), encoding="utf-8")

    total_elapsed = round(time.monotonic() - t_start, 3)
    summary = {
        "client_name": client_name,
        "workers": workers,
        "total_files": len(files),
        "succeeded": sum(1 for r in file_reports if r["status"] == "ok"),
        "failed": sum(1 for r in file_reports if r["status"] == "error"),
        "total_records": len(all_deduped),
        "total_elapsed_sec": total_elapsed,
        "combined_csv": str(combined_csv_path),
        "files": file_reports,
    }
    summary_path = output_dir / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Batch complete: %d/%d succeeded, %d total rows in %.2fs -> %s",
        summary["succeeded"],
        summary["total_files"],
        summary["total_records"],
        total_elapsed,
        combined_csv_path,
    )
    return summary


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    workers = args.workers if args.workers is not None else cfg.batch.default_workers
    if not (1 <= workers <= cfg.batch.max_workers):
        logger.error("--workers must be between 1 and %d (got %d).", cfg.batch.max_workers, workers)
        sys.exit(2)

    files = collect_files(args.input_dir, args.pattern)
    if not files:
        logger.error("No supported financial files found in %s (pattern=%s).", args.input_dir, args.pattern)
        sys.exit(1)

    asyncio.run(
        run_batch(
            files=files,
            output_dir=args.output_dir,
            client_name=args.name,
            document_type=args.document_type,
            workers=workers,
            config_path=args.config,
        )
    )


if __name__ == "__main__":
    main()
