from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.config import Colors, Config
from src.components import ModernButton
from src.utils import open_folder
from src.services.pdf_convert import convert_pdfs  # services側に用意する


def build_convert_tab(app):
    """
    app: PDFToolApp インスタンス
    app.tab_convert を組み立てる（Two Panel Layout）
    Left : ファイル選択（リスト + ボタン）
    Right: 設定（出力形式 / 出力ファイル名 / 実行）
    """

    container = tk.Frame(app.tab_convert, bg=Colors.BG_MAIN)
    container.pack(fill="both", expand=True, padx=Config.PADDING_LARGE, pady=Config.PADDING_LARGE)

    # ===== Title =====
    title_frame = tk.Frame(container, bg=Colors.BG_MAIN)
    title_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        title_frame,
        text="📝     PDF変換",
        font=(Config.FONT_FAMILY, 16, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left")

    tk.Label(
        title_frame,
        text="PDFを Word / Excel に変換します（複数選択可）",
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(10, 0))

    # ===== state =====
    app.convert_files: list[Path] = []
    app.convert_files_label = tk.StringVar(value="（未選択）")

    # ===== helpers =====
    def _sync_hint():
        if hasattr(app, "convert_hint_label"):
            if app.convert_files:
                app.convert_hint_label.place_forget()
            else:
                app.convert_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    def _maybe_update_name_placeholder():
        """
        入力中の文字を潰さないように、
        「エントリが空（またはプレースホルダ状態）」のときだけ更新する。
        """
        if not hasattr(app, "convert_name_pattern_entry"):
            return
        # app.get_entry_text が「プレースホルダなら空」を返す設計の前提
        current = app.get_entry_text(app.convert_name_pattern_entry).strip()
        if current == "":
            app.set_placeholder(app.convert_name_pattern_entry, "{name}")

    def _refresh_left_list():
        app.convert_listbox.delete(0, tk.END)
        for p in app.convert_files:
            app.convert_listbox.insert(tk.END, f"  📄 {p.name}")

        app.convert_files_label.set(
            f"{len(app.convert_files)} 個のPDFファイル" if app.convert_files else "（未選択）"
        )

        _sync_hint()

        if app.convert_files:
            app.update_pdf_info(app.convert_files[0])
        else:
            app.update_pdf_info(None)

        _maybe_update_name_placeholder()

    def _add_files(paths: list[Path]):
        if not paths:
            return
        for p in paths:
            if p not in app.convert_files:
                app.convert_files.append(p)
        _refresh_left_list()
        app.status.set(f"{len(app.convert_files)} 個のPDFを選択しました。")

    def on_drop_convert(event):
        pdf_paths = app._iter_dnd_pdf_paths(event)
        if not pdf_paths:
            return
        _add_files(pdf_paths)

    def choose_files():
        paths = filedialog.askopenfilenames(
            title="変換するPDFを選択",
            filetypes=[("PDFファイル", "*.pdf")],
        )
        if not paths:
            return
        _add_files([Path(p) for p in paths])

    def remove_selected():
        sel = app.convert_listbox.curselection()
        if not sel:
            return
        for idx in reversed(sel):
            if idx < len(app.convert_files):
                del app.convert_files[idx]
        _refresh_left_list()
        app.status.set(f"残り {len(app.convert_files)} ファイル")

    def clear_files():
        app.convert_files = []
        _refresh_left_list()
        app.status.set("ファイルリストをクリアしました。")

    def run_convert():
        if not app.convert_files:
            messagebox.showwarning("警告", "変換するPDFを選んでください。")
            return

        to_word = app.convert_to_word.get()
        to_excel = app.convert_to_excel.get()

        if not (to_word or to_excel):
            messagebox.showwarning("警告", "少なくとも1つは出力形式（Word / Excel）を選択してください。")
            return

        dir_str = app.output_dir_var.get().strip()
        out_dir = Path(dir_str) if dir_str else None

        # パターン（{name} = 元PDF名）
        pattern = app.get_entry_text(app.convert_name_pattern_entry).strip()
        if not pattern:
            pattern = "{name}"

        # tasks: (src, word_path, excel_path)
        tasks: list[tuple[Path, Optional[Path], Optional[Path]]] = []
        skipped = 0

        for src in app.convert_files:
            src = Path(src)
            base_dir = out_dir if out_dir else src.parent

            base_name = pattern.replace("{name}", src.stem) if "{name}" in pattern else pattern

            word_path = base_dir / f"{base_name}.docx" if to_word else None
            excel_path = base_dir / f"{base_name}.xlsx" if to_excel else None

            if word_path and not app.confirm_overwrite(word_path):
                word_path = None
            if excel_path and not app.confirm_overwrite(excel_path):
                excel_path = None

            if not word_path and not excel_path:
                skipped += 1
                continue

            tasks.append((src, word_path, excel_path))

        if not tasks:
            app.status.set("変換をキャンセルしました（すべてスキップ）")
            return

        app.progress_reset()
        app.status.set("PDF → Word/Excel 変換を開始しました...")
        app.set_actions_state(False)

        total = len(tasks)

        def progress_cb(percent: float, msg: str):
            def _u():
                app.progress_set(percent)
                app.status.set(msg)
            app.after(0, _u)

        def worker():
            try:
                success_count = convert_pdfs(tasks=tasks, progress_cb=progress_cb)

                def _finish():
                    app.progress_done()
                    app.set_actions_state(True)

                    msg_lines = ["PDF → Word/Excel の変換が完了しました。"]
                    msg_lines.append(f"成功: {success_count} 件 / 合計: {total} 件")
                    if skipped:
                        msg_lines.append(f"スキップ: {skipped} 件（上書き拒否など）")

                    failed = total - success_count
                    if failed > 0:
                        msg_lines.append(f"失敗: {failed} 件")

                    messagebox.showinfo("完了", "\n".join(msg_lines))
                    app.status.set(f"変換を完了しました: 成功 {success_count} 件")

                    if app.open_after.get() and success_count > 0:
                        # 代表1件目の出力へ
                        if tasks[0][1]:
                            open_folder(tasks[0][1])
                        elif tasks[0][2]:
                            open_folder(tasks[0][2])

                app.after(0, _finish)

            except Exception as e:
                def _error():
                    app.progress_done()
                    app.set_actions_state(True)
                    messagebox.showerror("エラー", f"変換中にエラーが発生しました:\n{e}")
                    app.status.set("変換に失敗しました")
                app.after(0, _error)

        threading.Thread(target=worker, daemon=True).start()

    # ===== DnD (container) =====
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            container.drop_target_register(app._dnd_token)
            container.dnd_bind("<<Drop>>", on_drop_convert)
    except:
        pass

    # ====================
    # Two Panel Layout
    # ====================
    main_container = ttk.Frame(container)
    main_container.pack(fill="both", expand=True, pady=(0, 5))

    # Left: files
    left_panel = ttk.LabelFrame(main_container, text="📁 対象PDFファイル", padding=10)
    left_panel.pack(side="left", fill="both", expand=False)
    left_panel.pack_propagate(False)
    left_panel.configure(width=400)

    # Right: settings
    right_panel = ttk.LabelFrame(main_container, text="⚙️ 設定", padding=10)
    right_panel.pack(side="left", fill="both", expand=True, padx=(5, 0))

    # ===== Left panel widgets =====
    btn_frame = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    btn_frame.pack(fill="x", pady=(0, 5))

    btn_choose = ModernButton(btn_frame, text="📁 PDFを選択", command=choose_files, style="secondary")
    btn_choose.pack(side="left", padx=(0, 5))

    btn_del = ModernButton(btn_frame, text="🗑️削除", command=remove_selected, style="secondary")
    btn_del.pack(side="left", padx=5)

    btn_clear = ModernButton(btn_frame, text="🔄     クリア", command=clear_files, style="danger")
    btn_clear.pack(side="left")

    app.action_buttons.extend([btn_choose, btn_del, btn_clear])

    tk.Label(
        left_panel,
        textvariable=app.convert_files_label,
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(5, 5))

    listbox_frame = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    listbox_frame.pack(fill="both", expand=True)

    app.convert_listbox = tk.Listbox(
        listbox_frame,
        font=(Config.FONT_FAMILY, 10),
        selectmode=tk.EXTENDED,
        relief="solid",
        borderwidth=1,
        highlightthickness=0,
        bg="white",
    )
    app.convert_listbox.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=app.convert_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    app.convert_listbox.config(yscrollcommand=scrollbar.set)

    app.convert_hint_label = tk.Label(
        listbox_frame,
        text="💡 ファイルをドラッグ&ドロップで追加できます",
        font=(Config.FONT_FAMILY, 11),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    )
    app.convert_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    # Left panel DnD（重複登録は避ける）
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            left_panel.drop_target_register(app._dnd_token)
            left_panel.dnd_bind("<<Drop>>", on_drop_convert)
    except:
        pass

    # ===== Right panel widgets =====
    # Output type
    type_frame = ttk.LabelFrame(right_panel, text="📦 出力形式", padding=8)
    type_frame.pack(fill="x", pady=(0, 10))

    app.convert_to_word = tk.BooleanVar(value=True)
    app.convert_to_excel = tk.BooleanVar(value=True)

    ttk.Checkbutton(type_frame, text="Word（.docx）に変換", variable=app.convert_to_word).pack(
        anchor="w", padx=5, pady=2
    )
    ttk.Checkbutton(
        type_frame, text="Excel（.xlsx）に変換（表は罫線付きで出力）", variable=app.convert_to_excel
    ).pack(anchor="w", padx=5, pady=2)

    # 出力フォルダ
    from src.ui.tab_base import make_output_folder_row
    make_output_folder_row(right_panel, app=app)

    # Output name pattern
    name_frame = tk.Frame(right_panel, bg=Colors.BG_MAIN)
    name_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        name_frame,
        text="📝 出力ファイル名:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(0, 10))

    app.convert_name_pattern_var = getattr(app, "convert_name_pattern_var", tk.StringVar(value=""))
    app.convert_name_pattern_entry = tk.Entry(
        name_frame,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
        textvariable=app.convert_name_pattern_var,
    )
    app.convert_name_pattern_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    tk.Label(
        name_frame,
        text="{name}が元ファイル名",
        font=(Config.FONT_FAMILY, 9),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left")

    app.init_placeholder(app.convert_name_pattern_entry, "{name}")

    # オプション
    from src.ui.tab_base import make_options_checkboxes
    make_options_checkboxes(right_panel, app=app)

    # Notes
    note = ttk.Label(
        right_panel,
        text=(
            "※ 画像だけのPDFは文字や表を抽出できない場合があります。\n"
            "※ Excel出力では表をセル分割し、罫線付きで出力します。"
        ),
        wraplength=520,
        justify="left",
    )
    note.pack(anchor="w", pady=(0, 10))

    # Execute
    btn_exec = ModernButton(right_panel, text="🚀 変換を実行", command=run_convert, style="primary")
    btn_exec.pack(fill="x", pady=(5, 0))
    app.action_buttons.append(btn_exec)

    # appに関数をぶら下げ
    app.choose_convert_pdfs = choose_files
    app.clear_convert_pdfs = clear_files
    app.run_convert = run_convert

    # 初期表示
    _refresh_left_list()
