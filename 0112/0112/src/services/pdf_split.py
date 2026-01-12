"""
PDF Page Extraction and Deletion Service

Provides functionality to extract specific pages or delete pages from PDFs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from pypdf import PdfReader, PdfWriter


@dataclass(frozen=True)
class SplitResult:
    """Result of a PDF split operation."""
    total_pages: int
    kept_pages: int
    output_path: Path


class PDFSplitError(Exception):
    """Exception raised during PDF split operations."""
    pass


def parse_page_ranges(text: str, total_pages: int) -> List[int]:
    """
    Parse page range specification into list of 0-based page indices.
    
    Args:
        text: Page specification (e.g., "1,3,5-7")
        total_pages: Total number of pages in PDF
        
    Returns:
        Sorted list of 0-based page indices
        
    Raises:
        ValueError: If page specification is invalid
        
    Examples:
        >>> parse_page_ranges("1,3,5-7", 10)
        [0, 2, 4, 5, 6]
        >>> parse_page_ranges("1-3,5", 10)
        [0, 1, 2, 4]
    """
    if total_pages <= 0:
        return []
    
    text = (text or "").strip()
    if not text:
        return []
    
    result_set: set[int] = set()
    parts = [p.strip() for p in text.split(",") if p.strip()]
    
    for part in parts:
        if "-" in part:
            # Range specification (e.g., "3-7")
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str.strip())
                end = int(end_str.strip())
            except ValueError as e:
                raise ValueError(f"範囲指定が不正です: {part}") from e
            
            if start < 1 or end < 1:
                raise ValueError(f"ページ番号は1以上である必要があります: {part}")
            if start > end:
                raise ValueError(f"範囲の開始が終了より大きくなっています: {part}")
            if end > total_pages:
                raise ValueError(
                    f"ページ番号 {end} は総ページ数 {total_pages} を超えています。"
                )
            
            # Add all pages in range (convert to 0-based)
            for page_num in range(start, end + 1):
                result_set.add(page_num - 1)
        else:
            # Single page specification
            try:
                page_num = int(part)
            except ValueError as e:
                raise ValueError(f"ページ番号が不正です: {part}") from e
            
            if page_num < 1:
                raise ValueError(f"ページ番号は1以上である必要があります: {page_num}")
            if page_num > total_pages:
                raise ValueError(
                    f"ページ番号 {page_num} は総ページ数 {total_pages} を超えています。"
                )
            
            result_set.add(page_num - 1)
    
    return sorted(result_set)


def split_pdf(
    src_path: Path,
    out_path: Path,
    mode: str,
    target_indices_0based: List[int],
) -> SplitResult:
    """
    Extract or delete specific pages from a PDF.
    
    Args:
        src_path: Source PDF file path
        out_path: Output PDF file path
        mode: "keep" to extract pages, "delete" to remove pages
        target_indices_0based: List of 0-based page indices
        
    Returns:
        SplitResult containing operation details
        
    Raises:
        PDFSplitError: If split operation fails
        ValueError: If input parameters are invalid
        
    Examples:
        >>> # Extract pages 1, 3, 5
        >>> result = split_pdf(src, out, "keep", [0, 2, 4])
        >>> # Delete pages 2, 4
        >>> result = split_pdf(src, out, "delete", [1, 3])
    """
    src_path = Path(src_path)
    out_path = Path(out_path)
    
    # Validate mode
    if mode not in ("keep", "delete"):
        raise ValueError(f"mode は 'keep' または 'delete' である必要があります: {mode}")
    
    try:
        reader = PdfReader(str(src_path))
        
        # Check for password protection
        if reader.is_encrypted:
            raise ValueError(
                "このPDFにはパスワードが設定されているため、抽出／削除できません。"
            )
        
        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDFにページが含まれていません。")
        
        # Validate target indices
        if not target_indices_0based:
            raise ValueError("対象ページが指定されていません。")
        
        for idx in target_indices_0based:
            if idx < 0 or idx >= total_pages:
                raise ValueError(
                    f"ページindex {idx + 1} が範囲外です "
                    f"(有効範囲: 1-{total_pages})"
                )
        
        # Determine pages to keep
        if mode == "keep":
            pages_to_keep = sorted(set(target_indices_0based))
        else:  # mode == "delete"
            pages_to_delete = set(target_indices_0based)
            pages_to_keep = [
                i for i in range(total_pages)
                if i not in pages_to_delete
            ]
        
        if not pages_to_keep:
            raise ValueError("結果として残るページがありません。")
        
        # Create output PDF
        writer = PdfWriter()
        for idx in pages_to_keep:
            writer.add_page(reader.pages[idx])
        
        # Write output file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            writer.write(f)
        
        return SplitResult(
            total_pages=total_pages,
            kept_pages=len(pages_to_keep),
            output_path=out_path
        )
        
    except ValueError:
        # Re-raise ValueError (validation errors)
        raise
    except Exception as e:
        raise PDFSplitError(
            f"PDF抽出／削除中にエラーが発生しました: {str(e)}"
        ) from e
