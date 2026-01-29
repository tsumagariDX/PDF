from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.config import Colors, Config
from src.components import ModernButton
from src.components.page_views import PageThumbnailView
from src.services.pdf_reorder import reorder_pdf
from src.utils import open_folder


def build_reorder_tab(app):
    """
    Left : サムネイル一覧（DnD/回転/並び替え）
    Right: 操作（PDF選択/クリア/回転ボタン/出力名/実行）
    ※DnDは「左パネル/サムネ枠/全体」に登録
    """
    frame = app.tab_reorder

    # ===================== 内部ヘルパ =====================
    def update_reorder_output_placeholder():
        if not hasattr(app, "reorder_output_entry"):
            return

        if not getattr(app, "reorder_pdf_path", None):
            placeholder = "空欄:'元ファイル名'_並び替え済み.pdf"
        else:
            p = Path(app.reorder_pdf_path)
            placeholder = f"{p.stem}_並び替え済み.pdf"

        app.set_placeholder(app.reorder_output_entry, placeholder)

    def clear_reorder_pdf():
        app.reorder_pdf_path = None
        app.reorder_var.set("(未選択)")

        if hasattr(app, "reorder_thumb_view"):
            try:
                app.reorder_thumb_view.clear()
            except Exception:
                pass

        app.update_pdf_info(None)
        update_reorder_output_placeholder()
        app.status.set("並び替え対象をクリアしました。")

    def load_reorder_pdf(path: Path, from_dnd: bool = False):
        app.reorder_pdf_path = str(path)
        app.reorder_var.set(path.name)

        app.update_pdf_info(path)
        app.status.set(f"並び替え対象（D&D）: {path}" if from_dnd else f"並び替え対象: {path}")

        try:
            app.reorder_thumb_view.load_pdf(str(path))
        except Exception as e:
            messagebox.showerror("エラー", f"サムネイル作成中にエラーが発生しました:\n{e}")
            app.status.set("サムネイル作成に失敗しました")

        update_reorder_output_placeholder()

    def choose_reorder_pdf(file_path=None):
        if file_path is None:
            path = filedialog.askopenfilename(
                title="並び替えをするPDFを選択",
                filetypes=[("PDFファイル", "*.pdf")],
            )
            if not path:
                return
            file_path = Path(path)

        load_reorder_pdf(file_path, from_dnd=False)

    def on_drop_reorder(event):
        pdf_paths = app._iter_dnd_pdf_paths(event)
        if not pdf_paths:
            return
        load_reorder_pdf(pdf_paths[0], from_dnd=True)

    def run_reorder():
        if not getattr(app, "reorder_pdf_path", None):
            messagebox.showwarning("警告", "並び替え対象のPDFが選択されていません。")
            return

        in_path = Path(app.reorder_pdf_path)

        # 出力フォルダ
        dir_str = app.output_dir_var.get().strip()
        out_dir = Path(dir_str) if dir_str else in_path.parent

        # 出力ファイル名
        raw_name = app.get_entry_text(app.reorder_output_entry).strip()
        if not raw_name:
            raw_name = f"{in_path.stem}_並び替え済み.pdf"
        if not raw_name.lower().endswith(".pdf"):
            raw_name += ".pdf"

        out_path = out_dir / raw_name

        if not app.confirm_overwrite(out_path):
            app.status.set("並び替え/回転をキャンセルしました（既存ファイルあり）")
            return

        order = app.reorder_thumb_view.get_page_order()
        rotations = app.reorder_thumb_view.get_page_rotations()

        if not order:
            messagebox.showwarning("警告", "ページ情報が取得できません。")
            return

        app.progress_reset()
        app.status.set("ページ並び替え/回転中...")
        app.set_actions_state(False)

        def progress_cb(p):
            app.progress_set(p)

        try:
            reorder_pdf(
                src_path=in_path,
                out_path=out_path,
                order=order,
                rotations=rotations,
                progress_cb=progress_cb,
            )
        except ValueError as e:
            messagebox.showwarning("警告", str(e))
            app.status.set("並び替え/回転を中止しました")
            app.set_actions_state(True)
            app.progress_reset()
            return
        except Exception as e:
            messagebox.showerror("エラー", f"並び替え/回転中にエラーが発生しました:\n{e}")
            app.status.set("並び替え/回転に失敗しました")
            app.set_actions_state(True)
            app.progress_reset()
            return

        app.progress_done()
        app.set_actions_state(True)

        messagebox.showinfo("完了", f"並び替え・回転を完了しました:\n{out_path}")
        app.status.set(f"並び替え・回転を完了しました: {out_path}")

        if app.open_after.get():
            open_folder(out_path)

    # ===================== UI（ここから） =====================
    # タブ全体は固定（スクロールなし）
    container = tk.Frame(frame, bg=Colors.BG_MAIN)
    container.pack(fill="both", expand=True, padx=Config.PADDING_LARGE, pady=(Config.PADDING_LARGE, 0))

    # Title（統一）
    title_frame = tk.Frame(container, bg=Colors.BG_MAIN)
    title_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        title_frame,
        text="🔀 並び替え / 回転",
        font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left")

    tk.Label(
        title_frame,
        text="サムネイルのドラッグ&ドロップ、または右側のボタンでページを並び替え・回転できます",
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(10, 0))

    # 2カラム with Resizable Splitter（左=サムネ / 右=操作）
    main_container = ttk.PanedWindow(container, orient=tk.HORIZONTAL)
    main_container.pack(fill="both", expand=True, pady=(0, 5))

    # 左：サムネ領域（ScrollableFrame削除 - PageThumbnailView内部でスクロール）
    left_panel = ttk.LabelFrame(main_container, text="ページ並び替え（サムネイル）", padding=5)
    main_container.add(left_panel, weight=3)

    # 右：操作（スクロール可能）
    right_panel = ttk.LabelFrame(main_container, text="操作・設定", padding=5)
    main_container.add(right_panel, weight=1)

    # ---- 左パネルの内容（ScrollableFrame不要） ----
    left_content = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    left_content.pack(fill="both", expand=True)

    # ---- 右パネル内にスクロール追加 ----
    from src.ui.scrollable_frame import ScrollableFrame
    right_scroll = ScrollableFrame(right_panel)
    right_scroll.pack(fill="both", expand=True)
    right_content = right_scroll.scrollable_frame
    right_content.configure(bg=Colors.BG_MAIN)
    
    # appに保存
    app.reorder_right_scroll = right_scroll

    # ---- 左パネルの内容 ----
    # Splitタブと同じ配置：左上バーに「PDF選択/クリア」
    top_left_bar = tk.Frame(left_content, bg=Colors.BG_MAIN)
    top_left_bar.pack(fill="x", pady=(0, 8))

    ModernButton(
        top_left_bar,
        text="📁 PDFを選択",
        command=choose_reorder_pdf,
        style="secondary",
    ).pack(side="left", padx=(0, 6))

    ModernButton(
        top_left_bar,
        text="🔄     クリア",
        command=clear_reorder_pdf,
        style="danger",
    ).pack(side="left")

    # ヒント（D&D）
    hint_text = (
        "💡 PDFはドラッグ＆ドロップでも追加できます（このエリアにドロップ）"
        if getattr(app, "dnd_available", False)
        else "💡（このPCではドラッグ＆ドロップは未対応です）"
    )
    hint_row = tk.Frame(left_content, bg=Colors.BG_MAIN)
    hint_row.pack(fill="x", pady=(2, 6))
    tk.Label(
        hint_row,
        text=hint_text,
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
        font=(Config.FONT_FAMILY, 9),
    ).pack(anchor="w")

    # -------- 左パネル：サムネビュー --------
    app.reorder_thumb_view = PageThumbnailView(left_content, thumb_height=100)
    app.reorder_thumb_view.pack(fill="both", expand=True)

    # DnD（サムネ枠＋左パネル＋全体コンテナ）
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            # 全体（落としやすさ）
            container.drop_target_register(app._dnd_token)
            container.dnd_bind("<<Drop>>", on_drop_reorder)

            # 左パネル（ヒント文と挙動を一致）
            left_panel.drop_target_register(app._dnd_token)
            left_panel.dnd_bind("<<Drop>>", on_drop_reorder)

    except Exception:
        pass

    # -------- 右パネル：操作 --------

    app.reorder_var = tk.StringVar(value="(未選択)")

    tk.Label(
        right_content,
        text="対象PDF:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w")

    tk.Label(
        right_content,
        textvariable=app.reorder_var,
        wraplength=320,
        font=(Config.FONT_FAMILY, 9),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 10))

    # 並び替えボタン
    tk.Label(
        right_content,
        text="📑 ページ移動:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 5))
    
    move_frame = tk.Frame(right_content, bg=Colors.BG_MAIN)
    move_frame.pack(fill="x", pady=(0, 10))
    
    ModernButton(
        move_frame,
        text="⇈ 先頭",
        command=lambda: app.reorder_thumb_view.move_selected_to_top(),
        style="secondary",
    ).pack(side="left", padx=(0, 5))
    
    ModernButton(
        move_frame,
        text="▲ 上",
        command=lambda: app.reorder_thumb_view.move_selected_up(),
        style="secondary",
    ).pack(side="left", padx=(0, 5))
    
    ModernButton(
        move_frame,
        text="▼ 下",
        command=lambda: app.reorder_thumb_view.move_selected_down(),
        style="secondary",
    ).pack(side="left", padx=(0, 5))
    
    ModernButton(
        move_frame,
        text="⇊ 末尾",
        command=lambda: app.reorder_thumb_view.move_selected_to_bottom(),
        style="secondary",
    ).pack(side="left")

    tk.Label(
        right_content,
        text="🔄 選択ページを回転:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 5))

    rotate_frame = tk.Frame(right_content, bg=Colors.BG_MAIN)
    rotate_frame.pack(fill="x", pady=(0, 10))

    ModernButton(
        rotate_frame,
        text="⟲ 90°左",
        command=lambda: app.reorder_thumb_view.rotate_selected(-90),
        style="secondary",
    ).pack(side="left", padx=(0, 5))

    ModernButton(
        rotate_frame,
        text="⟳ 90°右",
        command=lambda: app.reorder_thumb_view.rotate_selected(90),
        style="secondary",
    ).pack(side="left")

    # 出力フォルダ
    from src.ui.tab_base import make_output_folder_row
    make_output_folder_row(right_content, app=app)

    tk.Label(
        right_content,
        text="📝 出力ファイル名:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 5))

    app.reorder_output_var = tk.StringVar(value="")
    app.reorder_output_entry = tk.Entry(
        right_content,
        textvariable=app.reorder_output_var,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    app.reorder_output_entry.pack(fill="x", pady=(0, 10))

    app.init_placeholder(app.reorder_output_entry, "空欄:'元ファイル名'_並び替え済み.pdf")
    update_reorder_output_placeholder()

    # オプション
    from src.ui.tab_base import make_options_checkboxes
    make_options_checkboxes(right_content, app=app)

    execute_btn = ModernButton(right_content, text="🚀 並び替え/回転を実行", command=run_reorder, style="primary")
    execute_btn.pack(fill="x", pady=(10, 0))
    app.action_buttons.append(execute_btn)

    # appにぶら下げ
    app.update_reorder_output_placeholder = update_reorder_output_placeholder
    app.choose_reorder_pdf = choose_reorder_pdf
    app.clear_reorder_pdf = clear_reorder_pdf
    app.run_reorder = run_reorder
