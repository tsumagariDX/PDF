"""
PDF Reordering and Rotation Service

Provides functionality to reorder pages and rotate them in PDFs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Callable

from pypdf import PdfReader, PdfWriter


@dataclass(frozen=True)
class ReorderResult:
    """Result of a PDF reorder operation."""
    total_pages: int
    output_path: Path


class PDFReorderError(Exception):
    """Exception raised during PDF reorder operations."""
    pass


def _rotate_page_compat(page, angle: int):
    """
    Rotate a PDF page, handling different pypdf versions.
    
    Args:
        page: PDF page object
        angle: Rotation angle in degrees (0, 90, 180, 270)
        
    Returns:
        Rotated page object
        
    Raises:
        ValueError: If rotation fails
    """
    if not angle or angle % 360 == 0:
        return page
    
    # Normalize angle to 0-359
    normalized_angle = angle % 360
    
    # Try modern API first (pypdf >= 3.0)
    if hasattr(page, "rotate"):
        try:
            page.rotate(normalized_angle)
            return page
        except Exception:
            pass
    
    # Try clockwise rotation (pypdf 2.x)
    if hasattr(page, "rotate_clockwise"):
        try:
            page = page.rotate_clockwise(normalized_angle)
            return page
        except Exception:
            pass
    
    # Try counter-clockwise rotation (older pypdf)
    if hasattr(page, "rotateCounterClockwise"):
        try:
            ccw_angle = (360 - normalized_angle) % 360
            page.rotateCounterClockwise(ccw_angle)
            return page
        except Exception:
            pass
    
    raise ValueError(f"ページ回転に失敗しました（angle={angle}）")


def reorder_pdf(
    src_path: Path,
    out_path: Path,
    order: List[int],
    rotations: Optional[Dict[int, int]] = None,
    progress_cb: Optional[Callable[[float], None]] = None,
) -> ReorderResult:
    """
    Reorder and optionally rotate pages in a PDF.
    
    Args:
        src_path: Source PDF file path
        out_path: Output PDF file path
        order: List of 0-based page indices in desired order
        rotations: Optional dict mapping page index to rotation angle
        progress_cb: Optional callback receiving progress (0-100)
        
    Returns:
        ReorderResult containing operation details
        
    Raises:
        PDFReorderError: If reorder operation fails
        ValueError: If input parameters are invalid
        
    Examples:
        >>> # Reverse page order
        >>> reorder_pdf(src, out, [2, 1, 0])
        >>> # Rotate specific pages
        >>> reorder_pdf(src, out, [0, 1, 2], rotations={1: 90})
    """
    src_path = Path(src_path)
    out_path = Path(out_path)
    rotations = rotations or {}
    
    try:
        reader = PdfReader(str(src_path))
        
        # Check for password protection
        if reader.is_encrypted:
            raise ValueError(
                "このPDFにはパスワードが設定されているため、"
                "並び替え／回転できません。"
            )
        
        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDFにページが含まれていません。")
        
        if not order:
            raise ValueError("ページ順(order)が空です。")
        
        # Validate page indices
        for idx in order:
            if idx < 0 or idx >= total_pages:
                raise ValueError(
                    f"order のページindex {idx + 1} が範囲外です "
                    f"(有効範囲: 1-{total_pages})"
                )
        
        writer = PdfWriter()
        total = len(order)
        
        for i, src_idx in enumerate(order, start=1):
            page = reader.pages[src_idx]
            
            # Apply rotation if specified
            angle = rotations.get(src_idx, 0) or 0
            if angle:
                page = _rotate_page_compat(page, angle)
            
            writer.add_page(page)
            
            # Report progress
            if progress_cb is not None:
                progress_cb((i / total) * 100)
        
        # Write output file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            writer.write(f)
        
        return ReorderResult(total_pages=total_pages, output_path=out_path)
        
    except ValueError:
        # Re-raise ValueError (validation errors)
        raise
    except Exception as e:
        raise PDFReorderError(
            f"PDF並び替え／回転中にエラーが発生しました: {str(e)}"
        ) from e
