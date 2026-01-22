"""
PDF Compression Service

Provides functionality to compress PDF files using Ghostscript.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, List

# Type aliases
ProgressCallback = Callable[[float, str], None]

# Ghostscript compression presets (from low to high compression)
COMPRESSION_PRESETS = ["/prepress", "/printer", "/default", "/ebook", "/screen"]

# Windows subprocess flag to hide console window
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass(frozen=True)
class CompressResult:
    """Result of a PDF compression operation."""
    src: Path
    out: Path
    orig_mb: float
    new_mb: float
    setting: str
    reduced_percent: float


class PDFCompressError(Exception):
    """Exception raised during PDF compression operations."""
    pass


def level_to_start_index(level: int) -> int:
    """
    Convert UI compression level (1-5) to preset start index.
    
    Args:
        level: Compression level from 1 (low compression, high quality)
               to 5 (high compression, low quality)
    
    Returns:
        Index into COMPRESSION_PRESETS array
        
    Examples:
        >>> level_to_start_index(1)  # Lowest compression
        0
        >>> level_to_start_index(5)  # Highest compression
        4
    """
    level = max(1, min(5, int(level)))  # Clamp to 1-5
    return level - 1


def compress_one_pdf(
    input_path: Path,
    output_path: Path,
    gs_path: str,
    pdf_settings: str,
) -> None:
    """
    Compress a PDF file using Ghostscript.
    
    Args:
        input_path: Input PDF file path
        output_path: Output PDF file path
        gs_path: Path to Ghostscript executable
        pdf_settings: Ghostscript PDF settings (e.g., "/screen")
        
    Raises:
        PDFCompressError: If compression fails
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build Ghostscript command
    cmd = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_settings}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={str(output_path)}",
        str(input_path),
    ]
    
    try:
        if os.name == "nt":
            # Windows: hide console window
            subprocess.run(cmd, check=True, creationflags=CREATE_NO_WINDOW)
        else:
            # Unix-like systems
            subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise PDFCompressError(
            f"Ghostscriptによる圧縮に失敗しました: {str(e)}"
        ) from e
    except FileNotFoundError as e:
        raise PDFCompressError(
            f"Ghostscriptが見つかりません: {gs_path}"
        ) from e


def compress_pdf_auto(
    src: Path,
    out_path: Path,
    gs_path: str,
    start_index: int = 0,
    target_mb: Optional[float] = None,
    presets: Optional[List[str]] = None,
) -> CompressResult:
    """
    Automatically compress a PDF, optionally targeting a specific file size.
    
    Args:
        src: Source PDF file path
        out_path: Output PDF file path
        gs_path: Path to Ghostscript executable
        start_index: Starting index in presets array
        target_mb: Target file size in MB (None for single compression)
        presets: List of Ghostscript presets (uses default if None)
        
    Returns:
        CompressResult containing compression details
        
    Raises:
        PDFCompressError: If compression fails
        FileNotFoundError: If source file doesn't exist
    """
    src = Path(src)
    out_path = Path(out_path)
    
    if presets is None:
        presets = COMPRESSION_PRESETS
    
    if not src.exists():
        raise FileNotFoundError(f"ソースファイルが見つかりません: {src}")
    
    # Get original file size
    orig_bytes = src.stat().st_size
    orig_mb = orig_bytes / (1024 * 1024)
    
    # Validate start index
    last_idx = len(presets) - 1
    cur_idx = max(0, min(start_index, last_idx))
    
    used_setting = presets[cur_idx]
    
    if target_mb is None:
        # Single compression with specified preset
        compress_one_pdf(src, out_path, gs_path, used_setting)
    else:
        # Iterative compression to reach target size
        while True:
            used_setting = presets[cur_idx]
            compress_one_pdf(src, out_path, gs_path, used_setting)
            
            new_bytes = out_path.stat().st_size
            new_mb = new_bytes / (1024 * 1024)
            
            # Check if target reached or no more presets
            if new_mb <= target_mb or cur_idx >= last_idx:
                break
            
            cur_idx += 1
    
    # Calculate final size and reduction
    new_bytes = out_path.stat().st_size
    new_mb = new_bytes / (1024 * 1024)
    
    if orig_bytes > 0:
        reduced_percent = (1 - new_bytes / orig_bytes) * 100
    else:
        reduced_percent = 0.0
    
    return CompressResult(
        src=src,
        out=out_path,
        orig_mb=orig_mb,
        new_mb=new_mb,
        setting=used_setting,
        reduced_percent=reduced_percent,
    )


def compress_pdfs(
    sources: List[Path],
    out_paths: List[Path],
    gs_path: str,
    level: int = 3,
    target_mb: Optional[float] = None,
    progress_cb: Optional[ProgressCallback] = None,
) -> List[CompressResult]:
    """
    Compress multiple PDF files.
    
    Args:
        sources: List of source PDF file paths
        out_paths: List of output PDF file paths (same length as sources)
        gs_path: Path to Ghostscript executable
        level: Compression level (1-5)
        target_mb: Target file size in MB (None for level-based compression)
        progress_cb: Optional callback receiving (percent, message)
        
    Returns:
        List of CompressResult for each file
        
    Raises:
        ValueError: If sources and out_paths lengths don't match
        PDFCompressError: If compression fails
    """
    if len(sources) != len(out_paths):
        raise ValueError("sources と out_paths の数が一致していません。")
    
    if not sources:
        return []
    
    presets = COMPRESSION_PRESETS
    
    # Determine starting preset index
    if target_mb is None:
        start_idx = level_to_start_index(level)
    else:
        start_idx = 0  # Start with lowest compression for target mode
    
    total = len(sources)
    results: List[CompressResult] = []
    
    for i, (src, out_path) in enumerate(zip(sources, out_paths), start=1):
        # Report progress: starting
        if progress_cb:
            percent = (i - 1) / total * 100
            progress_cb(percent, f"圧縮準備...（{i}/{total}）{src.name}")
        
        # Compress
        try:
            res = compress_pdf_auto(
                src=src,
                out_path=out_path,
                gs_path=gs_path,
                start_index=start_idx,
                target_mb=target_mb,
                presets=presets,
            )
            results.append(res)
        except Exception as e:
            # Log error but continue with other files
            if progress_cb:
                progress_cb((i - 1) / total * 100, f"エラー: {src.name}")
            raise
        
        # Report progress: completed
        if progress_cb:
            percent = i / total * 100
            progress_cb(percent, f"圧縮完了（{i}/{total}）{res.src.name}")
    
    return results
