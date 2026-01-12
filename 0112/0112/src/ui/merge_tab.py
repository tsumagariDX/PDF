"""
Merge Tab - Two Column Layout (Left: files, Right: settings/execute) WITH DnD SUPPORT
"""

from __future__ import annotations

import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.config import Colors, Config
from src.components import ModernButton
from src.services.pdf_merge import merge_pdfs
from src.utils import open_folder


def build_merge_tab(app):
    """Build merge tab with DnD support (2-column layout)"""

    container = tk.Frame(app.tab_merge, bg=Colors.BG_MAIN)
    container.pack(fill="both", expand=True, padx=Config.PADDING_LARGE, pady=Config.PADDING_LARGE)

    # ===== Title =====
    title_frame = tk.Frame(container, bg=Colors.BG_MAIN)
    title_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        title_frame,
        text="📑    PDF結合",
        font=(Config.FONT_FAMILY, 16, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left")

    tk.Label(
        title_frame,
        text="複数のPDFファイルを1つに結合します",
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(10, 0))

    # ===== state =====
    if not hasattr(app, "pdf_paths") or app.pdf_paths is None:
        app.pdf_paths = []
    app.pdf_paths = list(app.pdf_paths)

    # ===== helpers =====
    def _sync_hint():
        if not hasattr(app, "merge_hint_label"):
            return
        if app.pdf_paths:
            app.merge_hint_label.place_forget()
        else:
            app.merge_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    def _refresh_merge_list(keep_selection: bool = True):
        # 選択維持（先頭のみでOK）
        selected = None
        if keep_selection:
            sel = app.merge_listbox.curselection()
            if sel:
                selected = sel[0]

        app.merge_listbox.delete(0, tk.END)
        for p in app.pdf_paths:
            app.merge_listbox.insert(tk.END, f"  📄 {Path(p).name}")

        _sync_hint()

        # 選択復元
        if selected is not None:
            new_idx = min(selected, max(app.merge_listbox.size() - 1, 0))
            if app.merge_listbox.size() > 0:
                app.merge_listbox.selection_set(new_idx)
                app.merge_listbox.see(new_idx)

        # PDF情報
        if app.pdf_paths:
            app.update_pdf_info(Path(app.pdf_paths[0]))
        else:
            app.update_pdf_info(None)

        app.status.set(f"{len(app.pdf_paths)} 個のPDFファイル" if app.pdf_paths else "（未選択）")

    def _add_files(paths: list[Path]):
        if not paths:
            return
        exist = {str(p) for p in app.pdf_paths}
        for p in paths:
            if str(p) not in exist:
                app.pdf_paths.append(p)
                exist.add(str(p))
        _refresh_merge_list(keep_selection=False)

    def on_drop_merge(event):
        # app._iter_dnd_pdf_paths がある前提（他タブと同じ）
        pdf_paths = app._iter_dnd_pdf_paths(event)
        if not pdf_paths:
            return
        _add_files(pdf_paths)

    def choose_files():
        files = filedialog.askopenfilenames(
            title="結合するPDFファイルを選択",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not files:
            return
        _add_files([Path(f) for f in files])

    def remove_selected():
        sel = app.merge_listbox.curselection()
        if not sel:
            return
        for idx in reversed(sel):
            if idx < len(app.pdf_paths):
                del app.pdf_paths[idx]
        _refresh_merge_list()

    def clear_all():
        if app.pdf_paths and messagebox.askyesno("確認", "リストをクリアしますか?"):
            app.pdf_paths.clear()
            _refresh_merge_list(keep_selection=False)
            app.status.set("クリアしました")

    def move_up():
        sel = app.merge_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        app.pdf_paths[idx - 1], app.pdf_paths[idx] = app.pdf_paths[idx], app.pdf_paths[idx - 1]
        _refresh_merge_list(keep_selection=False)
        app.merge_listbox.selection_set(idx - 1)
        app.merge_listbox.see(idx - 1)

    def move_down():
        sel = app.merge_listbox.curselection()
        if not sel or sel[0] >= len(app.pdf_paths) - 1:
            return
        idx = sel[0]
        app.pdf_paths[idx + 1], app.pdf_paths[idx] = app.pdf_paths[idx], app.pdf_paths[idx + 1]
        _refresh_merge_list(keep_selection=False)
        app.merge_listbox.selection_set(idx + 1)
        app.merge_listbox.see(idx + 1)

    def execute_merge():
        if len(app.pdf_paths) < 2:
            messagebox.showwarning("警告", "結合するPDFを2つ以上選択してください。")
            return

        filename = app.get_entry_text(app.merge_filename_entry).strip()
        if not filename:
            messagebox.showwarning("警告", "出力ファイル名を入力してください。")
            return

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        out_dir = app.output_dir_var.get().strip() or str(Path(app.pdf_paths[0]).parent)
        output_path = Path(out_dir) / filename

        if not app.confirm_overwrite(output_path):
            return

        def task():
            try:
                app.progress_reset()
                app.set_actions_state(False)
                app.status.set("PDF結合中...")

                merge_pdfs(app.pdf_paths, output_path, progress_cb=lambda p: app.progress_set(p))

                app.progress_done()
                app.status.set(f"✓ 結合完了: {output_path.name}")
                messagebox.showinfo("完了", f"PDFを結合しました。\n\n{output_path}")

                if app.open_after.get():
                    open_folder(output_path)

            except Exception as e:
                messagebox.showerror("エラー", f"結合に失敗しました:\n{str(e)}")
                app.status.set("エラーが発生しました")

            finally:
                app.set_actions_state(True)

        threading.Thread(target=task, daemon=True).start()

    # ===== DnD (container + left_panel only, no duplicates) =====
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            container.drop_target_register(app._dnd_token)
            container.dnd_bind("<<Drop>>", on_drop_merge)
    except Exception:
        pass

    # ====================
    # Two Column Layout
    # ====================
    main_container = ttk.Frame(container)
    main_container.pack(fill="both", expand=True, pady=(0, 5))

    # Left: file list (fixed-ish width)
    left_panel = ttk.LabelFrame(main_container, text="📁 結合するPDFファイル", padding=10)
    left_panel.pack(side="left", fill="both", expand=False)
    left_panel.pack_propagate(False)
    left_panel.configure(width=420)

    # Right: settings/execute
    right_panel = ttk.LabelFrame(main_container, text="⚙️ 設定", padding=10)
    right_panel.pack(side="left", fill="both", expand=True, padx=(5, 0))

    # ===== Left panel UI =====
    btn_row = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    btn_row.pack(fill="x", pady=(0, 6))

    btn_add = ModernButton(btn_row, text="➕ 追加", command=choose_files, style="secondary")
    btn_add.pack(side="left", padx=(0, 5))
    btn_del = ModernButton(btn_row, text="🗑️ 削除", command=remove_selected, style="secondary")
    btn_del.pack(side="left", padx=5)
    btn_clear = ModernButton(btn_row, text="🔄 クリア", command=clear_all, style="danger")
    btn_clear.pack(side="left", padx=5)

    app.action_buttons.extend([btn_add, btn_del, btn_clear])

    listbox_frame = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    listbox_frame.pack(fill="both", expand=True)

    # listbox area
    listbox_area = tk.Frame(listbox_frame, bg=Colors.BG_MAIN)
    listbox_area.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(listbox_area, orient="vertical")
    scrollbar.pack(side="right", fill="y")

    app.merge_listbox = tk.Listbox(
        listbox_area,
        font=(Config.FONT_FAMILY, 10),
        selectmode=tk.EXTENDED,
        yscrollcommand=scrollbar.set,
        bg="white",
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    app.merge_listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=app.merge_listbox.yview)

    app.merge_hint_label = tk.Label(
        listbox_area,
        text="💡 ファイルをドラッグ&ドロップで追加できます",
        font=(Config.FONT_FAMILY, 11),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    )
    app.merge_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    # move buttons (vertical) right of listbox
    move_col = tk.Frame(listbox_frame, bg=Colors.BG_MAIN)
    move_col.pack(side="left", fill="y", padx=(8, 0))

    tk.Frame(move_col, bg=Colors.BG_MAIN).pack(expand=True, fill="y")
    btn_up = ModernButton(move_col, text="⬆️", command=move_up, style="secondary")
    btn_up.pack(fill="x", pady=(0, 6))
    btn_down = ModernButton(move_col, text="⬇️", command=move_down, style="secondary")
    btn_down.pack(fill="x")
    tk.Frame(move_col, bg=Colors.BG_MAIN).pack(expand=True, fill="y")

    app.action_buttons.extend([btn_up, btn_down])

    # Left panel DnD（containerとは別に左でもOK）
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            left_panel.drop_target_register(app._dnd_token)
            left_panel.dnd_bind("<<Drop>>", on_drop_merge)
    except Exception:
        pass

    # ===== Right panel UI =====
    # 出力フォルダ
    from src.ui.tab_base import make_output_folder_row
    make_output_folder_row(right_panel, app=app)
    
    name_frame = tk.Frame(right_panel, bg=Colors.BG_MAIN)
    name_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        name_frame,
        text="📝 出力ファイル名:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w")

    app.merge_filename_entry = tk.Entry(
        name_frame,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    app.merge_filename_entry.pack(fill="x", pady=(6, 0))
    app.init_placeholder(app.merge_filename_entry, "merged.pdf")

    # オプション
    from src.ui.tab_base import make_options_checkboxes
    make_options_checkboxes(right_panel, app=app)

    execute_btn = ModernButton(right_panel, text="🚀 PDFを結合する", command=execute_merge, style="primary")
    execute_btn.pack(fill="x", pady=(10, 0))
    app.action_buttons.append(execute_btn)

    # 初期描画
    _refresh_merge_list(keep_selection=False)

    # appに関数をぶら下げ（他タブと揃える）
    app.merge_add_files = _add_files
    app.merge_clear_files = clear_all
    app.run_merge = execute_merge
