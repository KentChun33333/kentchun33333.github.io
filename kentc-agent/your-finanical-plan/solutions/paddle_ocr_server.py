"""
Self-hosted local PaddleOCR HTTP microservice.

Hosts PaddleOCR models locally on http://127.0.0.1:8866 with three selectable engines:
  1. "rapidocr" (default): Official PaddleOCR PP-OCRv4/v5 models executed on ONNXRuntime.
     Fastest option on Apple Silicon CPU (~0.15-0.35s/page) for meeting the <50s SLA.
  2. "paddleocr": Native PaddlePaddle `paddleocr.PaddleOCR` Python package.
  3. "ollama_paddleocr": Local Ollama `MedAIBase/PaddleOCR-VL:0.9b` vision-OCR model.

Run directly:
    .venv/bin/python -m solutions.paddle_ocr_server
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, List, Optional

import httpx
import numpy as np
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

from solutions import ConfigNode, load_config
from solutions.image_utils import normalize_image_bytes

logger = logging.getLogger("paddle_ocr_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class OCRLine(BaseModel):
    text: str
    score: float = 1.0
    box: Optional[List[List[float]]] = None


class OCRResponse(BaseModel):
    text: str
    lines: List[OCRLine]
    engine: str
    width: int
    height: int
    elapsed_ms: float


class BatchImageItem(BaseModel):
    id: str
    image_b64: str


class BatchOCRRequest(BaseModel):
    images: List[BatchImageItem] = Field(default_factory=list)


class BatchOCRItemResponse(BaseModel):
    id: str
    text: str
    line_count: int
    elapsed_ms: float
    error: Optional[str] = None


class BatchOCRResponse(BaseModel):
    engine: str
    results: List[BatchOCRItemResponse]
    total_elapsed_ms: float


class LocalPaddleOCREngine:
    """Thread-safe wrapper around local PaddleOCR backends."""

    def __init__(self, cfg: ConfigNode) -> None:
        self.cfg = cfg
        self.engine_name = cfg.paddle_ocr.engine
        self.max_dim = cfg.image.max_dimension
        self._engine: Any = None
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max(2, cfg.paddle_ocr.batch_concurrency))

    def load(self) -> None:
        if self._engine is not None:
            return
        with self._lock:
            if self._engine is not None:
                return
            t0 = time.perf_counter()
            if self.engine_name == "rapidocr":
                from rapidocr import RapidOCR

                self._engine = RapidOCR()
                logger.info(
                    "Loaded PaddleOCR PP-OCR ONNX engine (RapidOCR) in %.2fs",
                    time.perf_counter() - t0,
                )
            elif self.engine_name == "paddleocr":
                from paddleocr import PaddleOCR

                self._engine = PaddleOCR(use_angle_cls=True, lang="ch")
                logger.info(
                    "Loaded native PaddleOCR engine in %.2fs",
                    time.perf_counter() - t0,
                )
            elif self.engine_name == "ollama_paddleocr":
                self._engine = "ollama"
                logger.info(
                    "Configured Ollama PaddleOCR-VL backend (%s @ %s)",
                    self.cfg.paddle_ocr.ollama_model,
                    self.cfg.paddle_ocr.ollama_base_url,
                )
            else:
                raise ValueError(f"Unsupported paddle_ocr.engine: {self.engine_name}")

    def _run_sync(self, raw_bytes: bytes, filename: Optional[str] = None) -> OCRResponse:
        self.load()
        t0 = time.perf_counter()
        jpeg_bytes, _, (w, h) = normalize_image_bytes(
            raw_bytes,
            max_dimension=self.max_dim,
            jpeg_quality=self.cfg.image.jpeg_quality,
            filename=filename,
        )

        if self.engine_name == "ollama_paddleocr":
            b64 = base64.b64encode(jpeg_bytes).decode("ascii")
            payload = {
                "model": self.cfg.paddle_ocr.ollama_model,
                "prompt": "OCR:",
                "images": [b64],
                "stream": False,
                "options": {"temperature": 0},
            }
            with httpx.Client(timeout=self.cfg.paddle_ocr.timeout_sec) as client:
                resp = client.post(f"{self.cfg.paddle_ocr.ollama_base_url}/api/generate", json=payload)
                resp.raise_for_status()
                text = (resp.json().get("response") or "").strip()
            lines = [OCRLine(text=ln, score=0.95) for ln in text.splitlines() if ln.strip()]
            return OCRResponse(
                text=text,
                lines=lines,
                engine="ollama_paddleocr",
                width=w,
                height=h,
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )

        img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
        np_img = np.array(img)
        lines: List[OCRLine] = []

        if self.engine_name == "rapidocr":
            # RapidOCR 3.x returns a RapidOCROutput object with .txts, .scores, .boxes
            res = self._engine(np_img)
            txts = getattr(res, "txts", None) or []
            scores = getattr(res, "scores", None) or []
            boxes = getattr(res, "boxes", None)
            if boxes is None:
                boxes = [None] * len(txts)

            # Sort lines top-to-bottom, left-to-right for natural financial table reading
            items = []
            for idx, txt in enumerate(txts):
                txt_str = str(txt).strip()
                if not txt_str:
                    continue
                score = float(scores[idx]) if idx < len(scores) else 1.0
                box = boxes[idx] if idx < len(boxes) else None
                y_key, x_key = float(idx * 20), 0.0
                box_list = None
                if box is not None:
                    box_arr = np.asarray(box, dtype=float)
                    box_list = box_arr.tolist()
                    y_key = float(np.mean(box_arr[:, 1]))
                    x_key = float(np.min(box_arr[:, 0]))
                items.append((y_key, x_key, txt_str, score, box_list))

            # Group text boxes on roughly the same horizontal row so tables stay aligned
            items.sort(key=lambda it: (round(it[0] / 14.0), it[1]))
            rows_text: List[str] = []
            current_row_bucket: Optional[int] = None
            current_row_parts: List[str] = []
            for y_key, _, txt_str, score, box_list in items:
                lines.append(OCRLine(text=txt_str, score=round(score, 4), box=box_list))
                bucket = round(y_key / 14.0)
                if current_row_bucket is None or bucket == current_row_bucket:
                    current_row_bucket = bucket
                    current_row_parts.append(txt_str)
                else:
                    rows_text.append(" | ".join(current_row_parts))
                    current_row_bucket = bucket
                    current_row_parts = [txt_str]
            if current_row_parts:
                rows_text.append(" | ".join(current_row_parts))
            full_text = "\n".join(rows_text)

        else:
            # Native PaddleOCR
            raw_res = self._engine.ocr(np_img)
            text_lines: List[str] = []
            if raw_res and raw_res[0]:
                for entry in raw_res[0]:
                    box, (txt_str, score) = entry[0], entry[1]
                    txt_clean = str(txt_str).strip()
                    if txt_clean:
                        lines.append(OCRLine(text=txt_clean, score=round(float(score), 4), box=box))
                        text_lines.append(txt_clean)
            full_text = "\n".join(text_lines)

        return OCRResponse(
            text=full_text,
            lines=lines,
            engine=self.engine_name,
            width=w,
            height=h,
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
        )

    async def recognize_bytes(self, raw_bytes: bytes, filename: Optional[str] = None) -> OCRResponse:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._run_sync, raw_bytes, filename)


_cfg = load_config()
_ocr_engine = LocalPaddleOCREngine(_cfg)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ocr_engine.load()
    yield


app = FastAPI(
    title="Local PaddleOCR Microservice",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "paddle-ocr",
        "engine": _ocr_engine.engine_name,
        "max_dimension": _ocr_engine.max_dim,
    }


@app.post("/ocr", response_model=OCRResponse)
async def ocr_single(file: UploadFile = File(...)) -> OCRResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    try:
        return await _ocr_engine.recognize_bytes(raw, filename=file.filename)
    except Exception as exc:
        logger.exception("OCR single failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc


@app.post("/ocr/batch", response_model=BatchOCRResponse)
async def ocr_batch(req: BatchOCRRequest) -> BatchOCRResponse:
    t0 = time.perf_counter()
    sem = asyncio.Semaphore(_cfg.paddle_ocr.batch_concurrency)

    async def _one(item: BatchImageItem) -> BatchOCRItemResponse:
        async with sem:
            t_item = time.perf_counter()
            try:
                raw = base64.b64decode(item.image_b64)
                res = await _ocr_engine.recognize_bytes(raw)
                return BatchOCRItemResponse(
                    id=item.id,
                    text=res.text,
                    line_count=len(res.lines),
                    elapsed_ms=res.elapsed_ms,
                )
            except Exception as exc:
                return BatchOCRItemResponse(
                    id=item.id,
                    text="",
                    line_count=0,
                    elapsed_ms=round((time.perf_counter() - t_item) * 1000.0, 2),
                    error=str(exc),
                )

    results = await asyncio.gather(*(_one(item) for item in req.images))
    return BatchOCRResponse(
        engine=_ocr_engine.engine_name,
        results=list(results),
        total_elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
    )


def main() -> None:
    host = os.environ.get("PADDLE_OCR_HOST", _cfg.paddle_ocr.host)
    port = int(os.environ.get("PADDLE_OCR_PORT", _cfg.paddle_ocr.port))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
