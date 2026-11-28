"""
Cell-only multi-sheet Excel parser (no embedded images) for local Qwen3.8 extraction.

Handles both clean 1-table-per-sheet workbooks AND messy real-world personal sheets
containing multiple stacked or side-by-side tables (e.g., Investments + Insurance + Bank
on a single worksheet) via 2D connected-region table segmentation.
"""

from __future__ import annotations

import datetime
import io
from collections import deque
from typing import Any, List, Tuple

import openpyxl
from openpyxl.utils import get_column_letter

from solutions import ConfigNode
from solutions.models import PageUnit


def _format_cell(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, datetime.datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, datetime.date):
        return val.isoformat()
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val))
        return f"{val:.6g}" if abs(val) < 0.01 else f"{val:,.4f}".rstrip("0").rstrip(".")
    text = str(val).replace("\n", " ").replace("\r", " ").strip()
    return " ".join(text.split())


def _find_table_regions(grid: List[List[str]]) -> List[Tuple[int, int, int, int]]:
    """
    Segment a 2D sheet grid into distinct rectangular table/note regions
    separated by blank rows and/or blank columns (4-connected components -> bounding boxes,
    merging overlapping bounding boxes cleanly).

    Returns list of (r_min, r_max, c_min, c_max) sorted top-to-bottom, left-to-right.
    """
    n_rows = len(grid)
    if n_rows == 0:
        return []
    n_cols = max((len(r) for r in grid), default=0)
    if n_cols == 0:
        return []

    visited = [[False] * n_cols for _ in range(n_rows)]
    boxes: List[List[int]] = []

    def _has_val(r: int, c: int) -> bool:
        return c < len(grid[r]) and grid[r][c] != ""

    for r in range(n_rows):
        for c in range(len(grid[r])):
            if visited[r][c] or not _has_val(r, c):
                continue
            q = deque([(r, c)])
            visited[r][c] = True
            r_min = r_max = r
            c_min = c_max = c

            while q:
                cr, cc = q.popleft()
                r_min = min(r_min, cr)
                r_max = max(r_max, cr)
                c_min = min(c_min, cc)
                c_max = max(c_max, cc)
                # 4-directional adjacency (also bridge a single blank cell inside a table row/col
                # only if directly adjacent via neighbors; pure blank row or pure blank col splits cleanly)
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < n_rows and 0 <= nc < n_cols and not visited[nr][nc] and _has_val(nr, nc):
                        visited[nr][nc] = True
                        q.append((nr, nc))

            boxes.append([r_min, r_max, c_min, c_max])

    # Merge bounding boxes that overlap or directly touch (e.g. a table with sparse empty interior cells)
    changed = True
    while changed:
        changed = False
        merged: List[List[int]] = []
        used = [False] * len(boxes)
        for i in range(len(boxes)):
            if used[i]:
                continue
            r0, r1, c0, c1 = boxes[i]
            used[i] = True
            for j in range(i + 1, len(boxes)):
                if used[j]:
                    continue
                ar0, ar1, ac0, ac1 = boxes[j]
                # Overlap or touch horizontally/vertically (requires >=1 full blank row or col to stay separate)
                row_touch = not (ar1 < r0 or ar0 > r1)
                col_touch = not (ac1 < c0 or ac0 > c1)
                row_adj = not (ar1 + 1 < r0 or ar0 - 1 > r1)
                col_adj = not (ac1 + 1 < c0 or ac0 - 1 > c1)
                if (row_touch and col_adj) or (col_touch and row_adj):
                    r0, r1 = min(r0, ar0), max(r1, ar1)
                    c0, c1 = min(c0, ac0), max(c1, ac1)
                    used[j] = True
                    changed = True
            merged.append([r0, r1, c0, c1])
        boxes = merged

    # Sort reading order: top-to-bottom, then left-to-right
    boxes.sort(key=lambda b: (b[0], b[2]))
    return [(b[0], b[1], b[2], b[3]) for b in boxes]


def _render_region_lines(
    grid: List[List[str]],
    region: Tuple[int, int, int, int],
    sheet_name: str,
    block_idx: int,
    total_blocks: int,
) -> Tuple[str, List[str]]:
    r0, r1, c0, c1 = region
    coord_range = f"{get_column_letter(c0 + 1)}{r0 + 1}:{get_column_letter(c1 + 1)}{r1 + 1}"
    label = (
        f"[Sheet: {sheet_name} | Table {block_idx}/{total_blocks} ({coord_range})]"
        if total_blocks > 1
        else f"[Sheet: {sheet_name} ({coord_range})]"
    )

    rows_lines: List[str] = []
    for r in range(r0, r1 + 1):
        vals = [grid[r][c] if c < len(grid[r]) else "" for c in range(c0, c1 + 1)]
        if not any(vals):
            continue
        rows_lines.append(" | ".join(vals))
    return label, rows_lines


def parse_excel_to_units(
    excel_bytes: bytes,
    cfg: ConfigNode,
) -> Tuple[List[PageUnit], int, List[str]]:
    """
    Parse all sheets of an Excel workbook into chunked PageUnits (cells only, no images).
    Automatically separates stacked and side-by-side tables on the same sheet.
    """
    warnings: List[str] = []
    wb = openpyxl.load_workbook(
        io.BytesIO(excel_bytes),
        read_only=True,
        data_only=True,
    )

    sheet_names = wb.sheetnames
    total_sheets = len(sheet_names)
    units: List[PageUnit] = []
    max_chars = cfg.llm.max_chars_per_call

    for s_idx, sheet_name in enumerate(sheet_names, start=1):
        ws = wb[sheet_name]
        grid: List[List[str]] = []

        for row in ws.iter_rows(
            max_row=cfg.excel.max_rows_per_sheet,
            max_col=cfg.excel.max_cols_per_sheet,
            values_only=True,
        ):
            formatted = [_format_cell(c) for c in row]
            while formatted and formatted[-1] == "":
                formatted.pop()
            grid.append(formatted)

        # Trim trailing entirely empty rows
        while grid and not grid[-1]:
            grid.pop()

        if cfg.excel.skip_empty_sheets and not grid:
            continue

        regions = _find_table_regions(grid)
        if not regions:
            continue

        # Render each separated table/note block cleanly
        sheet_blocks: List[Tuple[str, List[str]]] = []
        for b_idx, reg in enumerate(regions, start=1):
            label, lines = _render_region_lines(grid, reg, sheet_name, b_idx, len(regions))
            if lines:
                sheet_blocks.append((label, lines))

        if not sheet_blocks:
            continue

        # Pack blocks of this sheet into <= max_chars PageUnits while keeping each block's own header intact
        buf_parts: List[str] = []
        buf_len = 0
        part_num = 1

        def _flush() -> None:
            nonlocal buf_parts, buf_len, part_num
            if not buf_parts:
                return
            sec_label = sheet_name if part_num == 1 else f"{sheet_name} (part {part_num})"
            units.append(
                PageUnit(
                    unit_id=f"sheet_{s_idx}_{sheet_name}_p{part_num}",
                    page_number=s_idx,
                    section_or_sheet=sec_label,
                    text="\n\n".join(buf_parts),
                    parse_tier="excel_multi_table" if len(sheet_blocks) > 1 else "excel_table",
                    signal_score=10.0,
                )
            )
            buf_parts = []
            buf_len = 0
            part_num += 1

        for label, lines in sheet_blocks:
            block_text = label + "\n" + "\n".join(lines)
            if len(block_text) <= max_chars:
                if buf_parts and buf_len + len(block_text) + 2 > max_chars:
                    _flush()
                buf_parts.append(block_text)
                buf_len += len(block_text) + 2
                continue

            # Very large single table: flush existing buffer and split row-wise repeating this block's own header
            _flush()
            header_row = lines[0]
            sub_lines = [label, header_row]
            sub_len = len(label) + len(header_row) + 2
            for ln in lines[1:]:
                if sub_len + len(ln) + 1 > max_chars and len(sub_lines) > 2:
                    buf_parts = ["\n".join(sub_lines)]
                    _flush()
                    sub_lines = [f"{label} (cont.)", header_row, ln]
                    sub_len = sum(len(x) + 1 for x in sub_lines)
                else:
                    sub_lines.append(ln)
                    sub_len += len(ln) + 1
            if len(sub_lines) > 2:
                buf_parts = ["\n".join(sub_lines)]
                _flush()

        _flush()

    wb.close()
    if not units:
        warnings.append("Excel workbook contained no non-empty data cells.")
    return units, total_sheets, warnings
