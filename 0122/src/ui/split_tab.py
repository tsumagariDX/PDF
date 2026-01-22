from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from src.config import Colors, Config
from src.components import ModernButton
from src.components.page_views import PageSelectView
from src.services.pdf_split import split_pdf
from src.utils import open_folder


def build_split_tab(app):
    frame = app.tab_split

    # ===================== 内部ヘルパ =====================
    def get_split_default_name(mode: str, src: Path) -> str:
        suffix = "_抽出済み" if mode == "keep" else "_削除済み"
        return f"{src.stem}{suffix}.pdf"

    def update_split_output_placeholder():
        if not hasattr(app, "split_output_entry"):
            return
        if not getattr(app, "split_src_path", None):
            placeholder = "空欄:'元ファイル名'_抽出済み.pdf"
        else:
            placeholder = get_split_default_name(app.page_edit_mode.get(), app.split_src_path)
        app.set_placeholder(app.split_output_entry, placeholder)

    def clear_split_pdf():
        app.split_src_path = None
        app.split_src_label.set("(未選択)")

        if hasattr(app, "split_thumb_view"):
            try:
                app.split_thumb_view.clear()
            except Exception:
                pass

        app.update_pdf_info(None)
        update_split_output_placeholder()
        app.status.set("抽出／削除対象をクリアしました。")

    def load_split_pdf(path: Path, from_dnd: bool = False):
        app.split_src_path = path
        app.split_src_label.set(path.name)

        app.update_pdf_info(path)
        app.status.set(f"抽出／削除対象（D&D）: {path}" if from_dnd else f"抽出／削除対象: {path}")

        if hasattr(app, "split_thumb_view"):
            try:
                app.split_thumb_view.load_pdf(str(path))
            except Exception as e:
                messagebox.showerror("エラー", f"サムネイル作成に失敗しました:\n{e}")

        update_split_output_placeholder()

    def choose_split_pdf(file_path=None):
        if file_path is None:
            path = filedialog.askopenfilename(
                title="抽出／削除するPDFを選択",
                filetypes=[("PDFファイル", "*.pdf")],
            )
            if not path:
                return
            file_path = Path(path)
        load_split_pdf(file_path, from_dnd=False)

    def on_drop_split(event):
        pdf_paths = app._iter_dnd_pdf_paths(event)
        if not pdf_paths:
            return
        load_split_pdf(pdf_paths[0], from_dnd=True)

    def run_split():
        if not getattr(app, "split_src_path", None):
            messagebox.showwarning("警告", "抽出／削除するPDFを選択してください。")
            return

        src_path: Path = app.split_src_path

        dir_str = app.output_dir_var.get().strip()
        out_dir = Path(dir_str) if dir_str else src_path.parent

        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("エラー", f"出力フォルダの作成に失敗しました:\n{e}")
            return

        if hasattr(app, "page_range_entry"):
            text = app.get_entry_text(app.page_range_entry).strip()
        else:
            text = app.page_range_var.get().strip()
        mode = app.page_edit_mode.get()

        selected_indices = []
        if not text and hasattr(app, "split_thumb_view"):
            selected_indices = app.split_thumb_view.get_selected_indices()

        from pypdf import PdfReader
        try:
            reader = PdfReader(str(src_path))
            total_pages = len(reader.pages)
        except Exception as e:
            messagebox.showerror("エラー", f"PDFの読み込みに失敗しました:\n{e}")
            return

        if text:
            from src.services.pdf_split import parse_page_ranges
            try:
                target_indices = parse_page_ranges(text, total_pages)
            except ValueError as e:
                messagebox.showwarning("警告", str(e))
                return
        elif selected_indices:
            target_indices = selected_indices
        else:
            messagebox.showwarning("警告", "ページを指定してください。")
            return

        raw_name = app.get_entry_text(app.split_output_entry).strip()
        if not raw_name:
            raw_name = get_split_default_name(mode, src_path)
        if not raw_name.lower().endswith(".pdf"):
            raw_name += ".pdf"

        out_path = out_dir / raw_name

        if not app.confirm_overwrite(out_path):
            app.status.set(f"ページ{'抽出' if mode == 'keep' else '削除'}をキャンセルしました（既存ファイルあり）")
            return

        app.progress_reset()
        app.status.set("ページ抽出／削除中...")
        app.set_actions_state(False)

        try:
            result = split_pdf(src_path, out_path, mode, target_indices)
        except ValueError as e:
            messagebox.showwarning("警告", str(e))
            app.status.set("抽出／削除を中止しました")
            app.set_actions_state(True)
            app.progress_reset()
            return
        except Exception as e:
            messagebox.showerror("エラー", f"抽出／削除中にエラーが発生しました:\n{e}")
            app.status.set("抽出／削除に失敗しました")
            app.set_actions_state(True)
            app.progress_reset()
            return

        app.progress_done()
        app.set_actions_state(True)

        mode_jp = "抽出" if mode == "keep" else "削除"
        messagebox.showinfo(
            "完了",
            f"{mode_jp}を完了しました。\n"
            f"出力ファイル: {out_path}\n"
            f"元ページ数: {result.total_pages} / 残りページ数: {result.kept_pages}"
        )
        app.status.set(f"ページ{mode_jp}を完了しました: {out_path}")

        if app.open_after.get():
            open_folder(out_path)

    # ===================== UI（ここから） =====================
    container = tk.Frame(frame, bg=Colors.BG_MAIN)
    container.pack(fill="both", expand=True, padx=Config.PADDING_LARGE, pady=Config.PADDING_LARGE)

    # Title（他タブと統一）
    title_frame = tk.Frame(container, bg=Colors.BG_MAIN)
    title_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        title_frame,
        text="✂️ 抽出／削除",
        font=(Config.FONT_FAMILY, 16, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left")
    tk.Label(
        title_frame,
        text="指定したページを抽出または削除します",
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(10, 0))

    # DnD（containerに統一）
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            container.drop_target_register(app._dnd_token)
            container.dnd_bind("<<Drop>>", on_drop_split)
    except Exception:
        pass

    # ====================
    # 2カラム（左右逆転版）
    # 左：ページ選択/プレビュー（広く）
    # 右：設定（固定幅）
    # ====================
    main_container = ttk.Frame(container)
    main_container.pack(fill="both", expand=True, pady=(0, 5))

    left_panel = ttk.LabelFrame(main_container, text="📄 ページ選択 / プレビュー", padding=10)
    left_panel.pack(side="left", fill="both", expand=True)

    right_panel = ttk.LabelFrame(main_container, text="⚙️ 設定", padding=10)
    right_panel.pack(side="left", fill="y", expand=False, padx=(5, 0))
    right_panel.pack_propagate(False)
    right_panel.configure(width=360)

    # ---- 左（ページ選択/プレビュー） ----
    # 上部に小さな導線（任意）：ここからもPDF選択できるようにして迷いを減らす
    top_left_bar = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    top_left_bar.pack(fill="x", pady=(0, 8))

    ModernButton(
        top_left_bar,
        text="📁 PDFを選択",
        command=choose_split_pdf,
        style="secondary",
    ).pack(side="left", padx=(0, 6))

    ModernButton(
        top_left_bar,
        text="🔄     クリア",
        command=clear_split_pdf,
        style="danger",
    ).pack(side="left")

    # ヒント（D&D）
    hint_text = (
        "💡 PDFはドラッグ＆ドロップでも追加できます（このエリアにドロップ）"
        if getattr(app, "dnd_available", False)
        else "💡（このPCではドラッグ＆ドロップは未対応です）"
    )
    hint_row = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    hint_row.pack(fill="x", pady=(2, 6))
    tk.Label(
        hint_row,
        text=hint_text,
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
        font=(Config.FONT_FAMILY, 9),
    ).pack(anchor="w")

    app.split_thumb_view = PageSelectView(left_panel, thumb_height=100)
    app.split_thumb_view.pack(fill="both", expand=True)

    # DnD（左パネルにも）
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            left_panel.drop_target_register(app._dnd_token)
            left_panel.dnd_bind("<<Drop>>", on_drop_split)
    except Exception:
        pass

    # ---- 右（設定） ----
    app.split_src_path: Optional[Path] = None
    app.split_src_label = tk.StringVar(value="(未選択)")

    # 対象表示
    tk.Label(
        right_panel,
        text="対象PDF:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w")

    tk.Label(
        right_panel,
        textvariable=app.split_src_label,
        wraplength=320,
        font=(Config.FONT_FAMILY, 9),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(4, 10))

    # ページ指定
    tk.Label(
        right_panel,
        text="📄 ページ指定（入力優先）:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 5))

    app.page_range_var = tk.StringVar(value="")
    page_entry = tk.Entry(
        right_panel,
        textvariable=app.page_range_var,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    page_entry.pack(fill="x", pady=(0, 10))
    app.init_placeholder(page_entry, "例: 1,3,5-7（空欄ならサムネ選択）")
    app.page_range_entry = page_entry


    # 処理モード
    tk.Label(
        right_panel,
        text="⚙️ 処理モード:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 5))

    app.page_edit_mode = tk.StringVar(value="keep")

    ttk.Radiobutton(
        right_panel,
        text="抽出（指定ページだけ残す）",
        variable=app.page_edit_mode,
        value="keep",
        command=update_split_output_placeholder,
    ).pack(anchor="w")

    ttk.Radiobutton(
        right_panel,
        text="削除（指定ページを消す）",
        variable=app.page_edit_mode,
        value="delete",
        command=update_split_output_placeholder,
    ).pack(anchor="w", pady=(0, 10))

    # 出力フォルダ
    from src.ui.tab_base import make_output_folder_row
    make_output_folder_row(right_panel, app=app)

    # 出力ファイル名
    tk.Label(
        right_panel,
        text="📝 出力ファイル名:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 5))

    app.split_output_var = tk.StringVar(value="")
    app.split_output_entry = tk.Entry(
        right_panel,
        textvariable=app.split_output_var,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    app.split_output_entry.pack(fill="x", pady=(0, 10))

    app.init_placeholder(app.split_output_entry, "空欄:'元ファイル名'_抽出済み.pdf")
    update_split_output_placeholder()

    # オプション
    from src.ui.tab_base import make_options_checkboxes
    make_options_checkboxes(right_panel, app=app)

    # 実行ボタン（右カラムの下）
    execute_btn = ModernButton(
        right_panel,
        text="🚀 ページ抽出/削除を実行",
        command=run_split,
        style="primary",
    )
    execute_btn.pack(fill="x", pady=(10, 0))
    app.action_buttons.append(execute_btn)

    # appにぶら下げ
    app.update_split_output_placeholder = update_split_output_placeholder
    app.choose_split_pdf = choose_split_pdf
    app.clear_split_pdf = clear_split_pdf
    app.run_split = run_split
    app.get_split_default_name = get_split_default_name
