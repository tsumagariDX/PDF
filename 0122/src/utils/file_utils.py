"""
Utility functions for PDF Tool Application

This module provides helper functions for:
- Ghostscript path detection
- Drag and drop path parsing
- Cross-platform folder opening
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox
from typing import Optional, List


# Constants
GHOSTSCRIPT_WINDOWS_EXES = ["gswin64c.exe", "gswin32c.exe", "gs.exe"]
GHOSTSCRIPT_UNIX_EXES = ["gs"]
PROGRAM_FILES_PATHS = [
    r"C:\Program Files\gs",
    r"C:\Program Files (x86)\gs",
]


def find_gs() -> Optional[str]:
    """
    Find Ghostscript executable path.
    
    Search order:
    1. Executable's directory (for bundled Ghostscript)
    2. System PATH
    3. Program Files directories (Windows only)
    
    Returns:
        str: Path to Ghostscript executable, or None if not found
        
    Examples:
        >>> gs_path = find_gs()
        >>> if gs_path:
        ...     print(f"Found Ghostscript at: {gs_path}")
    """
    exe_dir = Path(sys.argv[0]).resolve().parent
    
    # 1. Check local ghostscript folder (for bundled distribution)
    local_candidates = [
        exe_dir / "ghostscript" / "bin" / exe_name
        for exe_name in GHOSTSCRIPT_WINDOWS_EXES
    ] + [
        exe_dir / "ghostscript" / exe_name
        for exe_name in GHOSTSCRIPT_WINDOWS_EXES
    ]
    
    for exe_path in local_candidates:
        if exe_path.exists() and exe_path.is_file():
            return str(exe_path)
    
    # 2. Search in system PATH
    search_names = GHOSTSCRIPT_WINDOWS_EXES if os.name == "nt" else GHOSTSCRIPT_UNIX_EXES
    for name in search_names:
        found_path = shutil.which(name)
        if found_path:
            return found_path
    
    # 3. Search in Program Files (Windows only)
    if os.name == "nt":
        for base_dir in PROGRAM_FILES_PATHS:
            base_path = Path(base_dir)
            if not base_path.exists():
                continue
            
            try:
                # Search in version directories
                for ver_dir in base_path.iterdir():
                    if not ver_dir.is_dir():
                        continue
                    
                    for exe_name in GHOSTSCRIPT_WINDOWS_EXES:
                        exe_path = ver_dir / "bin" / exe_name
                        if exe_path.exists() and exe_path.is_file():
                            return str(exe_path)
            except (PermissionError, OSError):
                # Skip directories that can't be accessed
                continue
    
    return None


def split_dnd_paths(raw: str) -> List[str]:
    """
    Parse drag-and-drop path string from tkinterdnd2.
    
    Handles paths with spaces enclosed in braces.
    
    Args:
        raw: Raw string from tkinterdnd2 (e.g., '{C:/a b.pdf} {C:/c.pdf}')
        
    Returns:
        List of individual file paths
        
    Examples:
        >>> paths = split_dnd_paths('{C:/a b.pdf} {C:/c.pdf}')
        >>> print(paths)
        ['C:/a b.pdf', 'C:/c.pdf']
    """
    if not raw:
        return []
    
    result: List[str] = []
    buffer = ""
    in_braces = False
    
    for char in raw:
        if char == "{":
            in_braces = True
            buffer = ""
        elif char == "}":
            in_braces = False
            if buffer:
                result.append(buffer)
                buffer = ""
        elif char == " " and not in_braces:
            if buffer:
                result.append(buffer)
                buffer = ""
        else:
            buffer += char
    
    # Don't forget remaining buffer
    if buffer:
        result.append(buffer)
    
    return result


def open_folder(path: Path) -> None:
    """
    Open a folder in the system's default file manager.
    
    If path is a file, opens its parent directory.
    If path is a directory, opens that directory.
    
    Args:
        path: Path to file or directory
        
    Raises:
        Does not raise exceptions; shows error message box on failure
    """
    if not path.exists():
        messagebox.showerror("エラー", f"パスが存在しません:\n{path}")
        return
    
    folder = path if path.is_dir() else path.parent
    
    try:
        if os.name == "nt":
            # Windows
            os.startfile(str(folder))
        elif sys.platform == "darwin":
            # macOS
            subprocess.run(["open", str(folder)], check=True)
        else:
            # Linux/Unix
            subprocess.run(["xdg-open", str(folder)], check=True)
    except Exception as e:
        messagebox.showerror("エラー", f"フォルダを開けませんでした:\n{e}")
