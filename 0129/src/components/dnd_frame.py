"""Drag and Drop Frame"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Callable, List
from src.config import Colors, Config
from src.utils.file_utils import split_dnd_paths

try:
    from tkinterdnd2 import DND_FILES
    _DND_AVAILABLE = True
except:
    DND_FILES = None
    _DND_AVAILABLE = False

class DnDFrame(ttk.Frame):
    def __init__(self, master, on_drop: Callable[[List[Path]], None], 
                 file_types: List[str] = None, label_text: str = None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_drop = on_drop
        self.file_types = file_types or [".pdf"]
        
        if label_text is None:
            label_text = "📁 ファイルをドラッグ＆ドロップ\\nまたはクリックして選択"
        
        self.inner_frame = tk.Frame(self, bg=Colors.BG_ACCENT, highlightthickness=2,
                                   highlightbackground=Colors.BORDER, highlightcolor=Colors.PRIMARY)
        self.inner_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.dnd_label = tk.Label(self.inner_frame, text=label_text, font=(Config.FONT_FAMILY, 11),
                                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_ACCENT, cursor="hand2", pady=40)
        self.dnd_label.pack(fill="both", expand=True)
        
        self.dnd_label.bind("<Button-1>", lambda e: self._browse_files())
        self.inner_frame.bind("<Button-1>", lambda e: self._browse_files())
        self._setup_dnd()
    
    def _setup_dnd(self):
        if not _DND_AVAILABLE or DND_FILES is None:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.inner_frame.drop_target_register(DND_FILES)
            self.dnd_label.drop_target_register(DND_FILES)
            for widget in [self, self.inner_frame, self.dnd_label]:
                widget.dnd_bind("<<Drop>>", self._handle_drop)
                widget.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                widget.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        except:
            pass
    
    def _on_drag_enter(self, event):
        self.inner_frame.configure(bg=Colors.DND_HOVER, highlightbackground=Colors.PRIMARY)
        self.dnd_label.configure(bg=Colors.DND_HOVER)
    
    def _on_drag_leave(self, event):
        self.inner_frame.configure(bg=Colors.BG_ACCENT, highlightbackground=Colors.BORDER)
        self.dnd_label.configure(bg=Colors.BG_ACCENT)
    
    def _handle_drop(self, event):
        self._on_drag_leave(event)
        raw = getattr(event, "data", "")
        if not raw:
            return
        paths = split_dnd_paths(raw)
        valid_paths = [Path(p) for p in paths if Path(p).suffix.lower() in self.file_types]
        if valid_paths:
            self.on_drop(valid_paths)
        else:
            messagebox.showwarning("警告", f"有効なファイルが見つかりません。\\n対応形式: {', '.join(self.file_types)}")
    
    def _browse_files(self):
        filetypes = [(f"{ext.upper()} files", f"*{ext}") for ext in self.file_types]
        filetypes.append(("All files", "*.*"))
        files = filedialog.askopenfilenames(title="ファイルを選択", filetypes=filetypes)
        if files:
            self.on_drop([Path(f) for f in files])
    
    def update_label(self, text: str):
        self.dnd_label.configure(text=text)
