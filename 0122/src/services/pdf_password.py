"""
PDF Password Protection Service - SIMPLIFIED

Removed: annotation restriction, form field restriction
Kept: copy restriction, print restriction
"""

from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions

class PDFPasswordError(Exception):
    pass

def set_pdf_password(src: Path, out_path: Path, owner_password: str,
                     forbid_copy: bool = True, forbid_print: bool = False,
                     require_open_password: bool = False) -> None:
    try:
        reader = PdfReader(str(src))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        perms = UserAccessPermissions(-1)
        
        # If viewing requires password, also forbid copy/print
        if require_open_password:
            forbid_copy = True
            forbid_print = True
        
        if forbid_copy:
            if hasattr(UserAccessPermissions, "EXTRACT"):
                perms &= ~UserAccessPermissions.EXTRACT
            if hasattr(UserAccessPermissions, "EXTRACT_TEXT_AND_GRAPHICS"):
                perms &= ~UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
        
        if forbid_print:
            if hasattr(UserAccessPermissions, "PRINT"):
                perms &= ~UserAccessPermissions.PRINT
            if hasattr(UserAccessPermissions, "PRINT_TO_REPRESENTATION"):
                perms &= ~UserAccessPermissions.PRINT_TO_REPRESENTATION
        
        user_pwd = owner_password if require_open_password else ""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        writer.encrypt(user_password=user_pwd, owner_password=owner_password, permissions_flag=perms)
        
        with out_path.open("wb") as f:
            writer.write(f)
    except Exception as e:
        raise PDFPasswordError(f"パスワード設定エラー: {str(e)}") from e

def remove_pdf_password(src: Path, out_path: Path, password: str) -> None:
    try:
        reader = PdfReader(str(src))
        if not reader.is_encrypted:
            raise ValueError("PDFにパスワードが設定されていません。")
        result = reader.decrypt(password)
        if result == 0:
            raise ValueError("パスワードが正しくありません。")
        
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            writer.write(f)
    except ValueError:
        raise
    except Exception as e:
        raise PDFPasswordError(f"パスワード解除エラー: {str(e)}") from e
