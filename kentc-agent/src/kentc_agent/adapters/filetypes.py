"""File-type policy shared by the tools and the document loaders."""

from __future__ import annotations

from pathlib import Path

from ..errors import ToolError

DOCUMENT_SUFFIXES = {
    "pdf": {".pdf"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".avif", ".heic"},
    "docx": {".docx", ".docm"},
    "xlsx": {".xlsx", ".xlsm"},
    "pptx": {".pptx"},
    "email": {".eml", ".msg"},
    "csv": {".csv", ".tsv"},
    "html": {".html", ".htm"},
}
# read() hands these to documents.read_document (conversion, or the parsing sub-agent for PDFs/images/large files)
DOC_SUFFIXES = set().union(*DOCUMENT_SUFFIXES.values())
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mpg", ".mpeg", ".wmv", ".flv", ".3gp"}
LEGACY_OFFICE = {".doc": ".docx", ".xls": ".xlsx", ".ppt": ".pptx"}


def reject_unsupported(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        raise ToolError(f"{path.name}: video input is not supported")
    if suffix in LEGACY_OFFICE:
        raise ToolError(f"{path.name}: legacy Office format; save it as {LEGACY_OFFICE[suffix]} first")
