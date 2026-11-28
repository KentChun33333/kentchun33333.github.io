"""
Image & media normalization (max 1024px constraint) and PDF page rasterization.

Supported raster & snapshot formats:
  - Standard: PNG, JPG/JPEG, WEBP, BMP, TIFF, GIF, AVIF
  - Apple HEIF/HEIC: decoded natively via pillow-heif
  - WebM clips/screenshots (.webm): extracts the sharpest representative frame via OpenCV
"""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None  # type: ignore[assignment]

_WEBM_EBML_MAGIC = b"\x1a\x45\xdf\xa3"


def _is_webm_payload(raw_bytes: bytes, filename: Optional[str] = None) -> bool:
    if raw_bytes.startswith(_WEBM_EBML_MAGIC):
        return True
    if filename and Path(filename).suffix.lower() == ".webm":
        return True
    return False


def _extract_webm_frame_to_pil(raw_bytes: bytes) -> Image.Image:
    """Extract the clearest non-blank frame from a .webm file using OpenCV."""
    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = Path(tmp.name)

        cap = cv2.VideoCapture(str(tmp_path))
        if not cap.isOpened():
            raise ValueError("Unable to open WebM stream for frame extraction.")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        sample_indices = (
            sorted({0, total_frames // 4, total_frames // 2, (3 * total_frames) // 4})
            if total_frames > 4
            else [0]
        )

        best_frame = None
        best_sharpness = -1.0

        for idx in sample_indices:
            if idx > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            # Prefer non-blank frames with crisp text edges
            if sharpness > best_sharpness:
                best_sharpness = sharpness
                best_frame = frame

        cap.release()
        if best_frame is None:
            raise ValueError("WebM file did not contain any decodable video frames.")

        rgb = cv2.cvtColor(best_frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def resize_image_to_max_dim(
    image: Image.Image,
    max_dimension: int = 1024,
) -> Tuple[Image.Image, Tuple[int, int], Tuple[int, int]]:
    """
    Downscale any image whose width or height exceeds `max_dimension` (default 1024px)
    while preserving aspect ratio. Never upscales smaller images.
    """
    image = ImageOps.exif_transpose(image)
    if getattr(image, "is_animated", False):
        image.seek(0)

    if image.mode not in ("RGB", "L"):
        rgba = image.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        image = bg
    elif image.mode == "L":
        image = image.convert("RGB")

    orig_w, orig_h = image.size
    longest = max(orig_w, orig_h)
    if longest > max_dimension:
        scale = max_dimension / float(longest)
        new_w = max(1, int(round(orig_w * scale)))
        new_h = max(1, int(round(orig_h * scale)))
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    return image, (orig_w, orig_h), image.size


def encode_pil_to_jpeg(image: Image.Image, quality: int = 85) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def normalize_image_bytes(
    raw_bytes: bytes,
    max_dimension: int = 1024,
    jpeg_quality: int = 85,
    filename: Optional[str] = None,
) -> Tuple[bytes, Tuple[int, int], Tuple[int, int]]:
    """
    Load raw image or WebM bytes (JPG, PNG, HEIC, HEIF, WEBP, WEBM, TIFF, BMP, GIF),
    clamp max(w, h) <= max_dimension, and encode as JPEG.
    """
    if _is_webm_payload(raw_bytes, filename=filename):
        img = _extract_webm_frame_to_pil(raw_bytes)
        resized, orig_size, new_size = resize_image_to_max_dim(img, max_dimension=max_dimension)
        jpeg_bytes = encode_pil_to_jpeg(resized, quality=jpeg_quality)
        return jpeg_bytes, orig_size, new_size

    with Image.open(io.BytesIO(raw_bytes)) as img:
        resized, orig_size, new_size = resize_image_to_max_dim(img, max_dimension=max_dimension)
        jpeg_bytes = encode_pil_to_jpeg(resized, quality=jpeg_quality)
    return jpeg_bytes, orig_size, new_size


def render_pdf_page_to_jpeg(
    page: pymupdf.Page,
    dpi: int = 150,
    max_dimension: int = 1024,
    jpeg_quality: int = 85,
) -> Tuple[bytes, Tuple[int, int], Tuple[int, int]]:
    """
    Render a PDF page via PyMuPDF directly bounded to `max_dimension` px on its
    longest side so huge PDFs (2048px+ pages) never waste RAM or VLM vision tokens.
    """
    rect = page.rect
    raw_w = max(1.0, rect.width * dpi / 72.0)
    raw_h = max(1.0, rect.height * dpi / 72.0)
    orig_pixel_size = (int(round(raw_w)), int(round(raw_h)))

    zoom = dpi / 72.0
    longest = max(raw_w, raw_h)
    if longest > max_dimension:
        zoom *= max_dimension / longest

    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    img, _, final_size = resize_image_to_max_dim(img, max_dimension=max_dimension)
    jpeg_bytes = encode_pil_to_jpeg(img, quality=jpeg_quality)
    return jpeg_bytes, orig_pixel_size, final_size


def bytes_to_data_url(jpeg_bytes: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"
