# utils.py

from pathlib import Path
import shutil
import subprocess
import os
import sys
from tkinter import messagebox
from typing import Optional

def find_gs() -> str | None:
    """
    Ghostscript の実行ファイル(例: gswin64c.exe)を探してパスを返す。
    見つからなければ None。
    優先順位:
      1) exe と同じフォルダ内の ghostscript
      2) PATH 上
      3) Program Files 配下
    """

    # 1) exe と同じフォルダ内（Nuitka ビルド後もここ）
    # 例: app.exe と同じ階層に ghostscript フォルダを置く
    #   app.exe
    #   ghostscript/bin/gswin64c.exe
    exe_dir = Path(sys.argv[0]).resolve().parent

    local_candidates = [
        exe_dir / "ghostscript" / "bin" / "gswin64c.exe",
        exe_dir / "ghostscript" / "bin" / "gswin32c.exe",
        exe_dir / "ghostscript" / "gswin64c.exe",
        exe_dir / "ghostscript" / "gswin32c.exe",
    ]
    for exe in local_candidates:
        if exe.exists():
            return str(exe)

    # 2) PATH 上から探す（開発PC / Ghostscriptインストール済み環境向け）
    for name in ["gswin64c.exe", "gswin32c.exe", "gs"]:
        p = shutil.which(name)
        if p:
            return p

    # 3) Program Files 配下を探す（インストール版 Ghostscript 向け）
    candidates = [
        r"C:\Program Files\gs",
        r"C:\Program Files (x86)\gs",
    ]

    for base in candidates:
        base_path = Path(base)
        if not base_path.exists():
            continue

        for ver_dir in base_path.iterdir():
            # 例: C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe
            exe = ver_dir / "bin" / "gswin64c.exe"
            if exe.exists():
                return str(exe)

    # どこにもなければ諦める
    return None

def split_dnd_paths(raw: str) -> list[str]:
    """
    tkinterdnd2 から渡される文字列を
    個々のパス文字列に分解するユーティリティ。
    例: '{C:/a b.pdf} {C:/c.pdf}' -> ['C:/a b.pdf', 'C:/c.pdf']
    """
    result: list[str] = []
    buf = ""
    in_brace = False

    for ch in raw:
        if ch == "{":
            in_brace = True
            buf = ""
        elif ch == "}":
            in_brace = False
            if buf:
                result.append(buf)
                buf = ""
        elif ch == " " and not in_brace:
            if buf:
                result.append(buf)
                buf = ""
        else:
            buf += ch

    if buf:
        result.append(buf)

    return result


def open_folder(path: Path) -> None:
    """
    引数 path がファイルならその親フォルダ、
    フォルダならそれ自体を OS の標準ファイラで開く。
    """
    folder = path if path.is_dir() else path.parent

    try:
        if os.name == "nt":
            # Windows
            os.startfile(str(folder))
        elif sys.platform == "darwin":
            # macOS
            subprocess.run(["open", str(folder)], check=False)
        else:
            # Linux系
            subprocess.run(["xdg-open", str(folder)], check=False)
    except Exception as e:
        messagebox.showerror("エラー", f"フォルダを開けませんでした:\n{e}")
