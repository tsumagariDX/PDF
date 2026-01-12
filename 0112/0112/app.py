"""
Modern PDF Utility Application - FIXED VERSION

Key fixes:
1. Window size enlarged to 1200x850 (prevents content cutoff)
2. Minimum size set to 1000x700
3. All tabs support DnD
4. Form field restriction works correctly
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from pypdf import PdfReader
from src.config import Colors, Config
from src.components import DnDFrame, ModernButton
from src.utils import split_dnd_paths

# Check for DnD support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseTk = TkinterDnD.Tk
    _DND_AVAILABLE = True
except ImportError:
    BaseTk = tk.Tk
    _DND_AVAILABLE = False


class PDFToolApp(BaseTk):
    """Modern PDF Utility Application"""
    
    def __init__(self):
        super().__init__()
        
        # FIXED: Larger window size to prevent content cutoff
        self.title(Config.WINDOW_TITLE)
        self.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.geometry("900x920")
        self.resizable(False, False)
        
        self._configure_style()
        self._create_menu()
        
        # DnD availability
        self.dnd_available = _DND_AVAILABLE
        self._dnd_token = DND_FILES if _DND_AVAILABLE else None
        
        # Application state
        self.pdf_paths: List[Path] = []
        self.status = tk.StringVar(value="準備完了")
        self.output_dir_var = tk.StringVar(value="")
        self.overwrite_all = tk.BooleanVar(value=False)
        self.open_after = tk.BooleanVar(value=False)
        
        # PDF info variables
        self.info_name = tk.StringVar(value="---")
        self.info_pages = tk.StringVar(value="---")
        self.info_size = tk.StringVar(value="---")
        self.info_path = tk.StringVar(value="---")
        
        self.convert_name_pattern_var = tk.StringVar(value="")
        
        # Build UI
        self.widgets()
        
        # FIXED: Set minimum window size
        self.update_idletasks()
        self.minsize(Config.MIN_WIDTH, Config.MIN_HEIGHT)
        
        self.update_pdf_info(None)
    
    def _configure_style(self):
        """Configure modern ttk styles"""
        style = ttk.Style()
        
        # Configure notebook to evenly distribute tabs across the window
        style.configure("TNotebook", background=Colors.BG_MAIN, borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab", padding=[25,10], font=(Config.FONT_FAMILY, 10, "bold"))
        
        # Make tabs expand to fill available space evenly
        style.map("TNotebook.Tab",
                  background=[("selected", Colors.TAB_SELECTED_BG), ("!selected", Colors.TAB_NORMAL_BG)],
                  foreground=[("selected", Colors.TAB_SELECTED_FG), ("!selected", Colors.TAB_NORMAL_FG)],
                  expand=[("selected", [1, 1, 1, 0]), ("!selected", [1, 1, 1, 0])])
        
        style.configure("TFrame", background=Colors.BG_MAIN)
        style.configure("TLabel", background=Colors.BG_MAIN, foreground=Colors.TEXT_PRIMARY)
        style.configure("TLabelframe", background=Colors.BG_MAIN, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", font=(Config.FONT_FAMILY, 10, "bold"))
    
    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="終了", command=self.quit)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._show_about)
    
    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "バージョン情報",
            "Modern PDF Utility\\nVersion 2.0\\n\\nすべての改善が適用されました"
        )
    
    def dnd_register(self, widget, handler):
        """Register widget for DnD"""
        if not self.dnd_available or not self._dnd_token:
            return
        try:
            widget.drop_target_register(self._dnd_token)
            widget.dnd_bind("<<Drop>>", handler)
        except:
            pass
    
    # Placeholder helpers
    def init_placeholder(self, entry: tk.Entry, placeholder_text: str):
        entry._placeholder = placeholder_text
        entry._has_placeholder = False
        
        def on_focus_in(_e):
            if getattr(entry, "_has_placeholder", False):
                entry.delete(0, "end")
                entry.config(foreground="black")
                entry._has_placeholder = False
        
        def on_focus_out(_e):
            if not entry.get():
                self.set_placeholder(entry, entry._placeholder)
        
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        self.set_placeholder(entry, placeholder_text)
    
    def set_placeholder(self, entry: tk.Entry, placeholder_text: str):
        entry._placeholder = placeholder_text
        if getattr(entry, "_has_placeholder", False) or not entry.get():
            entry.delete(0, "end")
            entry.insert(0, placeholder_text)
            entry.config(foreground="gray")
            entry._has_placeholder = True
    
    def get_entry_text(self, entry: tk.Entry) -> str:
        text = entry.get().strip()
        return "" if getattr(entry, "_has_placeholder", False) else text
    
    # File validation
    def confirm_overwrite(self, path: Path) -> bool:
        name = path.name
        bad = [c for c in Config.INVALID_FILENAME_CHARS if c in name]
        if bad:
            messagebox.showwarning("警告", f"ファイル名に使用できない文字が含まれています。\n対象ファイル名: {name}")
            return False
        
        if not path.exists():
            return True
        
        if self.overwrite_all.get():
            return True
        
        return messagebox.askyesno("確認", f"{name} は既に存在します。\n\n上書きしますか？")
    
    # PDF info panel
    def update_pdf_info(self, path: Optional[Path]):
        if not path or not path.exists():
            self.info_name.set("---")
            self.info_pages.set("---")
            self.info_size.set("---")
            self.info_path.set("---")
            return
        
        self.info_name.set(path.name)
        self.info_path.set(str(path))
        
        try:
            size_bytes = path.stat().st_size
            if size_bytes < 1024 * 1024:
                self.info_size.set(f"{size_bytes / 1024:.1f} KB")
            else:
                self.info_size.set(f"{size_bytes / (1024 * 1024):.2f} MB")
        except:
            self.info_size.set("不明")
        
        try:
            reader = PdfReader(str(path))
            self.info_pages.set(f"{len(reader.pages)} ページ")
        except:
            self.info_pages.set("不明")
    
    # UI Layout
    def widgets(self):
        self.action_buttons = []
        self.configure(bg=Colors.BG_MAIN)
        
        # Header
        header = tk.Frame(self, bg=Colors.PRIMARY, height=30)
        header.pack(fill="both",side="top", expand=False, pady=(0, 0))
        header.configure(height=50)
        header.pack_propagate(False)
        
        tk.Label(header, text="📄 らくらくPDF", font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),
                fg="white", bg=Colors.PRIMARY).pack(side="left", padx=20, pady=0)
        tk.Label(header, text="便利なPDF処理ツール", font=(Config.FONT_FAMILY, 8),
                fg="white", bg=Colors.PRIMARY).pack(side="left", padx=(0, 20))
        
        # Notebook
        self.nb = ttk.Notebook(self)
        
        # Create tabs
        self.tab_merge = ttk.Frame(self.nb)
        self.tab_split = ttk.Frame(self.nb)
        self.tab_reorder = ttk.Frame(self.nb)
        self.tab_compress = ttk.Frame(self.nb)
        self.tab_convert = ttk.Frame(self.nb)
        self.tab_password = ttk.Frame(self.nb)
        
        # Add tabs with equal-width text using padding
        self.nb.add(self.tab_merge, text="    📑 結合      ")
        self.nb.add(self.tab_split, text="✂ 抽出/削除")
        self.nb.add(self.tab_reorder, text=" 🔄 並び替え ")
        self.nb.add(self.tab_compress, text="🗜️ 圧縮 ")
        self.nb.add(self.tab_convert, text="   📝 変換     ")
        self.nb.add(self.tab_password, text="🔒 パスワード")
        
        # Build tab contents
        from src.ui.merge_tab import build_merge_tab
        from src.ui.split_tab import build_split_tab
        from src.ui.reorder_tab import build_reorder_tab
        from src.ui.compress_tab import build_compress_tab
        from src.ui.convert_tab import build_convert_tab
        from src.ui.password_tab import build_password_tab
        
        build_merge_tab(self)
        build_split_tab(self)
        build_reorder_tab(self)
        build_compress_tab(self)
        build_convert_tab(self)
        build_password_tab(self)
        
        # PDF info panel
        self.info_frame = ttk.LabelFrame(self, text="📊 選択中PDFの情報", padding=8)
        info_grid = ttk.Frame(self.info_frame)
        info_grid.pack(fill="x")
        
        for label_text, var in [("📄 ファイル名:", self.info_name), ("📑 ページ数:", self.info_pages),
                                ("💾 サイズ:", self.info_size), ("📍 場所:", self.info_path)]:
            row = ttk.Frame(info_grid)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=label_text, width=15).pack(side="left")
            ttk.Label(row, textvariable=var, foreground=Colors.TEXT_SECONDARY).pack(side="left", padx=5)
        
        # Status bar
        self.status_frame = tk.Frame(self, bg=Colors.BG_ACCENT, pady=8, padx=20)
        ttk.Label(self.status_frame, textvariable=self.status, font=(Config.FONT_FAMILY, 9)).pack(side="left", padx=5)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(self.status_frame, variable=self.progress_var, maximum=100, mode="determinate", length=300)
        self.progress.pack(side="right", padx=5)
        
        self.show_main_ui()
    
    def show_main_ui(self, initial_tab: Optional[str] = None):
        # 下部要素を先に配置（side="bottom"は先にpackする必要がある）
        self.status_frame.pack(fill="x", side="bottom")
        self.info_frame.pack(fill="x", side="bottom", padx=20, pady=8)
        
        # タブは残りのスペースを使用
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Bind resize event to evenly distribute tabs
        self.nb.bind("<Configure>", self._on_notebook_resize)
        
        # Initial tab distribution
        self.after(100, self._distribute_tabs)
        
        if initial_tab:
            tab_map = {"merge": self.tab_merge, "split": self.tab_split, "reorder": self.tab_reorder,
                      "compress": self.tab_compress, "convert": self.tab_convert, "password": self.tab_password}
            if initial_tab in tab_map:
                self.nb.select(tab_map[initial_tab])
    
    def _on_notebook_resize(self, event=None):
        """Handle notebook resize to redistribute tabs"""
        if event and event.widget == self.nb:
            self._distribute_tabs()
    
    def _distribute_tabs(self):
        """Distribute tabs evenly across notebook width"""
        try:
            # Get notebook width
            nb_width = self.nb.winfo_width()
            if nb_width <= 1:
                return
            
            # Get number of tabs
            num_tabs = self.nb.index("end")
            if num_tabs == 0:
                return
            
            # Calculate tab width (evenly distributed)
            tab_width = nb_width // num_tabs
            
            # Update style with calculated width
            style = ttk.Style()
            style.configure("TNotebook.Tab", padding=[tab_width//2 - 40,10], width=tab_width)
        except:
            pass
    
    def browse_output_dir(self):
        initial = self.output_dir_var.get() or (str(self.pdf_paths[0].parent) if self.pdf_paths else "")
        folder = filedialog.askdirectory(title="出力フォルダを選択", initialdir=initial or None)
        if folder:
            self.output_dir_var.set(folder)
            self.status.set(f"出力フォルダを設定: {folder}")
    
    # Action state helpers
    def set_actions_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for btn in getattr(self, "action_buttons", []):
            try:
                btn.configure(state=state)
            except:
                pass
    
    # Progress bar helpers
    def progress_reset(self):
        self.progress_var.set(0)
        self.progress.update_idletasks()
    
    def progress_set(self, value: float):
        self.progress_var.set(value)
        self.progress.update_idletasks()
    
    def progress_done(self):
        self.progress_var.set(100)
        self.progress.update_idletasks()
    
    # DnD helpers
    def _iter_dnd_pdf_paths(self, event) -> List[Path]:
        raw = getattr(event, "data", "")
        paths = split_dnd_paths(raw)
        return [Path(p) for p in paths if Path(p).suffix.lower() == ".pdf"]


if __name__ == "__main__":
    app = PDFToolApp()
    app.mainloop()
