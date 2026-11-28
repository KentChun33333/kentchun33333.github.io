"""Async HTTP client for the locally hosted PaddleOCR microservice."""

from __future__ import annotations

import base64
import logging
from typing import Dict, List, Tuple

import httpx

from solutions import ConfigNode

logger = logging.getLogger(__name__)


class PaddleOCRClient:
    """Calls local PaddleOCR HTTP endpoints (/health, /ocr, /ocr/batch)."""

    def __init__(self, cfg: ConfigNode) -> None:
        self.cfg = cfg
        self.base_url = cfg.base_url.rstrip("/")

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    async def ocr_image(self, image_bytes: bytes, filename: str = "page.jpg", timeout: float | None = None) -> str:
        eff_timeout = timeout if timeout is not None else self.cfg.timeout_sec
        async with httpx.AsyncClient(timeout=eff_timeout) as client:
            resp = await client.post(
                f"{self.base_url}/ocr",
                files={"file": (filename, image_bytes, "image/jpeg")},
            )
            resp.raise_for_status()
            return resp.json().get("text", "")

    async def ocr_batch(
        self,
        items: List[Tuple[str, bytes]],
        timeout: float | None = None,
        chunk_size: int = 8,
    ) -> Dict[str, str]:
        """Batch-OCR multiple JPEG pages in bounded HTTP chunks."""
        if not items:
            return {}

        eff_timeout = timeout if timeout is not None else max(self.cfg.timeout_sec, 30.0)
        texts: Dict[str, str] = {}

        async with httpx.AsyncClient(timeout=eff_timeout) as client:
            for start in range(0, len(items), chunk_size):
                batch = items[start : start + chunk_size]
                payload = {
                    "images": [
                        {"id": item_id, "image_b64": base64.b64encode(raw).decode("ascii")}
                        for item_id, raw in batch
                    ]
                }
                resp = await client.post(f"{self.base_url}/ocr/batch", json=payload)
                resp.raise_for_status()
                data = resp.json()
                for res in data.get("results", []):
                    if res.get("error"):
                        logger.warning("PaddleOCR batch item %s error: %s", res["id"], res["error"])
                    texts[res["id"]] = res.get("text", "")
        return texts
