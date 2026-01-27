"""
Modern PDF Utility Application - FIXED VERSION

Key fixes:
1. Window size enlarged to 1200x850 (prevents content cutoff)
2. Minimum size set to 1000x700
3. All tabs support DnD
4. Form field restriction works correctly

+ UI tweak:
- Add spacing between tabs (tab margins)
- Keep even tab widths WITHOUT overwriting padding each resize
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
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

        # Window
        self.title(Config.WINDOW_TITLE)
        self.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")

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

        # Notebook resize debounce (prevents heavy style reconfigure on every pixel)
        self._tab_resize_after_id: Optional[str] = None

        # Build UI
        self.widgets()

        # Minimum window size
        self.update_idletasks()
        self.minsize(Config.MIN_WIDTH, Config.MIN_HEIGHT)

        self.update_pdf_info(None)

    def _configure_style(self):
        """Configure modern ttk styles"""
        style = ttk.Style()

        # ---- Font stabilization (IME / DPI) ----
        # Some Windows IME compositions can temporarily render with a larger font.
        # To prevent this, we explicitly configure Tk named fonts and ttk widget fonts.
        try:
            base_size = int(getattr(Config, "FONT_SIZE_NORMAL", 10))
            family = getattr(Config, "FONT_FAMILY", "Yu Gothic UI")

            named = [
                "TkDefaultFont",
                "TkTextFont",
                "TkFixedFont",
                "TkMenuFont",
                "TkHeadingFont",
                "TkCaptionFont",
                "TkSmallCaptionFont",
                "TkIconFont",
                "TkTooltipFont",
            ]
            for n in named:
                try:
                    f = tkfont.nametofont(n)
                    f.configure(family=family, size=base_size)
                except Exception:
                    pass

            # Fallback for any non-ttk widgets that don't set font explicitly
            self.option_add("*Font", (family, base_size))
        except Exception:
            pass

        # NOTE:
        # - On Windows default themes, tabmargins may not reflect well.
        # - If you want guaranteed visuals, uncomment the next line.
        # style.theme_use("clam")

        # ---- Notebook spacing (tab gaps) ----
        # tabmargins = [left, top, right, bottom]
        style.configure(
            "TNotebook",
            background=Colors.BG_MAIN,
            borderwidth=0,
            tabmargins=[0, 0, 0, 0],  # ★ tab-to-tab gaps
        )

        # Base tab padding (keep constant; do NOT override in _distribute_tabs)
        style.configure(
            "TNotebook.Tab",
            padding=(12, 8),
            font=(Config.FONT_FAMILY, 10, "bold"),
        )

        # Ensure ttk widgets keep a consistent font (prevents IME size jumps)
        try:
            base_size = int(getattr(Config, "FONT_SIZE_NORMAL", 10))
            family = getattr(Config, "FONT_FAMILY", "Yu Gothic UI")
            style.configure("TLabel", font=(family, base_size))
            style.configure("TButton", font=(family, base_size))
            style.configure("TEntry", font=(family, base_size))
            style.configure("TCombobox", font=(family, base_size))
            style.configure("TCheckbutton", font=(family, base_size))
            style.configure("TRadiobutton", font=(family, base_size))
        except Exception:
            pass

        # Color mapping
        style.map(
            "TNotebook.Tab",
            background=[("selected", Colors.TAB_SELECTED_BG), ("!selected", Colors.TAB_NORMAL_BG)],
            foreground=[("selected", Colors.TAB_SELECTED_FG), ("!selected", Colors.TAB_NORMAL_FG)],
        )

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
        menubar.add_cascade(label="コマンド", menu=file_menu)
        file_menu.add_command(label="終了", command=self.quit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="表示", menu=view_menu)
        view_menu.add_command(label="🏠 メニュー画面に戻る", command=self.show_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._show_about)

    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "バージョン情報\n",
            "らくらくPDF ver.1.0",
        )

    def dnd_register(self, widget, handler):
        """Register widget for DnD"""
        if not self.dnd_available or not self._dnd_token:
            return
        try:
            widget.drop_target_register(self._dnd_token)
            widget.dnd_bind("<<Drop>>", handler)
        except Exception:
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
        except Exception:
            self.info_size.set("不明")

        try:
            reader = PdfReader(str(path))
            self.info_pages.set(f"{len(reader.pages)} ページ")
        except Exception:
            self.info_pages.set("不明")

    # UI Layout
    def widgets(self):
        self.action_buttons = []
        self.configure(bg=Colors.BG_MAIN)

        # Header
        header = tk.Frame(self, bg=Colors.PRIMARY, height=30)
        header.pack(fill="both", side="top", expand=False, pady=(0, 0))
        header.configure(height=50)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="📄 らくらくPDF",
            font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),
            fg="white",
            bg=Colors.PRIMARY,
        ).pack(side="left", padx=20, pady=0)
        tk.Label(
            header,
            text="便利なPDF処理ツール",
            font=(Config.FONT_FAMILY, 8),
            fg="white",
            bg=Colors.PRIMARY,
        ).pack(side="left", padx=(0, 20))

        # Notebook
        self.nb = ttk.Notebook(self)

        # Create tabs
        self.tab_merge = ttk.Frame(self.nb)
        self.tab_split = ttk.Frame(self.nb)
        self.tab_reorder = ttk.Frame(self.nb)
        self.tab_compress = ttk.Frame(self.nb)
        self.tab_convert = ttk.Frame(self.nb)
        self.tab_password = ttk.Frame(self.nb)

        self.nb.add(self.tab_merge, text="📑 結合")
        self.nb.add(self.tab_split, text="✂ 抽出/削除")
        self.nb.add(self.tab_reorder, text="🔄 並び替え")
        self.nb.add(self.tab_compress, text="🗜️ 圧縮")
        self.nb.add(self.tab_convert, text="📝 変換")
        self.nb.add(self.tab_password, text="🔒 パスワード")

        # Build tab contents
        from src.ui.merge_tab import build_merge_tab
        from src.ui.split_tab import build_split_tab
        from src.ui.reorder_tab import build_reorder_tab
        from src.ui.compress_tab import build_compress_tab
        from src.ui.convert_tab import build_convert_tab
        from src.ui.password_tab import build_password_tab
        from src.ui.menu_screen import build_menu_screen

        build_merge_tab(self)
        build_split_tab(self)
        build_reorder_tab(self)
        build_compress_tab(self)
        build_convert_tab(self)
        build_password_tab(self)
        
        # メニュー画面を構築
        self.menu_screen = build_menu_screen(self)
        
        # 各タブに「メニューに戻る」ボタンを追加（メニューバーに移動したためコメントアウト）
        # self._add_back_buttons()

        # PDF info panel
        self.info_frame = ttk.LabelFrame(self, text="📊 選択中PDFの情報", padding=5)
        info_grid = ttk.Frame(self.info_frame)
        info_grid.pack(fill="x")

        for label_text, var in [
            ("📄 ファイル名:", self.info_name),
            ("📑 ページ数:", self.info_pages),
            ("💾 サイズ:", self.info_size),
            ("📍 場所:", self.info_path),
        ]:
            row = ttk.Frame(info_grid)
            row.pack(fill="x", pady=0)
            ttk.Label(row, text=label_text, width=12).pack(side="left")
            ttk.Label(row, textvariable=var, foreground=Colors.TEXT_SECONDARY).pack(side="left", padx=3)

        # Status bar
        self.status_frame = tk.Frame(self, bg=Colors.BG_ACCENT, pady=5, padx=15)
        ttk.Label(self.status_frame, textvariable=self.status, font=(Config.FONT_FAMILY, 9)).pack(side="left", padx=5)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            self.status_frame, variable=self.progress_var, maximum=100, mode="determinate", length=300
        )
        self.progress.pack(side="right", padx=5)

        # 初期表示はメニュー画面
        self.show_menu()
    
    def _add_back_buttons(self):
        """各タブに「メニューに戻る」ボタンを追加"""
        from src.components import ModernButton
        
        tabs = [
            self.tab_merge,
            self.tab_split,
            self.tab_reorder,
            self.tab_compress,
            self.tab_convert,
            self.tab_password,
        ]
        
        for tab in tabs:
            # 各タブの最上部にボタンフレームを挿入
            back_frame = tk.Frame(tab, bg=Colors.BG_MAIN, height=50)
            back_frame.pack(side="top", fill="x", padx=20, pady=(10, 0))
            back_frame.pack_propagate(False)
            
            back_btn = ModernButton(
                back_frame,
                text="◀ メニューに戻る",
                command=self.show_menu,
                style="secondary",
            )
            back_btn.pack(side="left", pady=10)
    
    def show_menu(self):
        """メニュー画面を表示"""
        # 既存の要素を非表示（状態の正規化）
        try:
            self.nb.unbind("<Configure>")
        except Exception:
            pass

        for w in (self.nb, self.info_frame):
            try:
                w.pack_forget()
            except Exception:
                pass
        
        # メニュー画面を表示
        self.menu_screen.pack(fill="both", expand=True)
        self.status_frame.pack(fill="x", side="bottom")
        
        # ステータスをリセット
        self.status.set("準備完了")
        self.progress_reset()
    
    def show_feature(self, feature_name: str):
        """機能画面を表示"""
        # メニュー画面を非表示（状態の正規化）
        try:
            self.menu_screen.pack_forget()
        except Exception:
            pass
        
        # タブとステータスバーを表示
        self.show_main_ui(initial_tab=feature_name)

    def show_main_ui(self, initial_tab: Optional[str] = None):
        """メインUI（タブ画面）を表示。メニュー↔タブ遷移時の表示状態を正規化する。"""

        # ---- 表示状態の正規化 ----
        # menu_screen が残っていると、環境によってはレイアウトが崩れることがある。
        try:
            self.menu_screen.pack_forget()
        except Exception:
            pass

        # Notebook のリサイズイベントは都度 bind すると過剰に走るため、明示的に unbind してから bind し直す
        try:
            self.nb.unbind("<Configure>")
        except Exception:
            pass

        # bottom
        self.status_frame.pack(fill="x", side="bottom")
        self.info_frame.pack(fill="x", side="bottom", padx=15, pady=5)

        # tabs
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        # Bind resize event to evenly distribute tabs
        self.nb.bind("<Configure>", self._on_notebook_resize)

        # Initial tab distribution
        self.after(100, self._distribute_tabs)

        if initial_tab:
            tab_map = {
                "merge": self.tab_merge,
                "split": self.tab_split,
                "reorder": self.tab_reorder,
                "compress": self.tab_compress,
                "convert": self.tab_convert,
                "password": self.tab_password,
            }
            if initial_tab in tab_map:
                self.nb.select(tab_map[initial_tab])

    def _on_notebook_resize(self, event=None):
        """Handle notebook resize to redistribute tabs"""
        if not (event and event.widget == self.nb):
            return

        # Debounce: リサイズ中に毎ピクセル再計算すると重い/チラつくため、短時間にまとめて実行
        try:
            if self._tab_resize_after_id:
                self.after_cancel(self._tab_resize_after_id)
        except Exception:
            pass

        self._tab_resize_after_id = self.after(120, self._distribute_tabs)

    def _distribute_tabs(self):
        """Distribute tabs evenly across notebook width (WITHOUT overwriting padding)."""
        try:
            nb_width = self.nb.winfo_width()
            if nb_width <= 1:
                return

            num_tabs = self.nb.index("end")
            if num_tabs == 0:
                return

            # Calculate tab width; keep a sensible minimum
            tab_width = max(90, nb_width // num_tabs)

            # Update only width; keep padding from _configure_style
            style = ttk.Style()
            style.configure("TNotebook.Tab", width=tab_width)

        except Exception:
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
            except Exception:
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
