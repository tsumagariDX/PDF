"""
PDF Merging Service

Provides functionality to merge multiple PDF files into a single document.
"""

from pathlib import Path
from typing import Union, Callable, Optional, List

from pypdf import PdfReader, PdfWriter


PathLike = Union[str, Path]
ProgressCallback = Optional[Callable[[float], None]]


class PDFMergeError(Exception):
    """Exception raised during PDF merge operations."""
    pass


def merge_pdfs(
    inputs: List[PathLike],
    output: PathLike,
    progress_cb: ProgressCallback = None
) -> None:
    """
    Merge multiple PDF files into a single output file.
    
    Args:
        inputs: List of input PDF file paths
        output: Output PDF file path
        progress_cb: Optional callback function that receives progress (0-100)
        
    Raises:
        PDFMergeError: If merge operation fails
        FileNotFoundError: If any input file doesn't exist
        ValueError: If input list is empty or contains encrypted PDFs
        
    Examples:
        >>> merge_pdfs(['file1.pdf', 'file2.pdf'], 'merged.pdf')
        >>> # With progress callback
        >>> def on_progress(percent):
        ...     print(f"Progress: {percent}%")
        >>> merge_pdfs(inputs, output, progress_cb=on_progress)
    """
    # Convert all paths to Path objects
    input_paths = [Path(p) for p in inputs]
    output_path = Path(output)
    
    # Validate inputs
    if not input_paths:
        raise ValueError("結合するPDFが指定されていません。")
    
    # Check all files exist
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {path}")
        if not path.is_file():
            raise ValueError(f"ファイルではありません: {path}")
    
    try:
        writer = PdfWriter()
        total = len(input_paths)
        
        for i, path in enumerate(input_paths, start=1):
            try:
                reader = PdfReader(str(path))
                
                # Check for password protection
                if reader.is_encrypted:
                    raise ValueError(
                        f"パスワードが設定されているPDFは結合できません。\n"
                        f"対象ファイル: {path.name}"
                    )
                
                # Add all pages from this PDF
                for page in reader.pages:
                    writer.add_page(page)
                
                # Report progress
                if progress_cb is not None:
                    progress_cb((i / total) * 100)
                    
            except ValueError:
                # Re-raise ValueError (e.g., encrypted PDF)
                raise
            except Exception as e:
                raise PDFMergeError(
                    f"PDFの読み込みに失敗しました: {path.name}\n"
                    f"エラー: {str(e)}"
                ) from e
        
        # Write merged PDF
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as f:
            writer.write(f)
            
    except (ValueError, PDFMergeError, FileNotFoundError):
        # Re-raise known exceptions
        raise
    except Exception as e:
        raise PDFMergeError(f"PDF結合中にエラーが発生しました: {str(e)}") from e
