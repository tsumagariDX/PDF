"""
Password Tab - Two Modes

Mode A: 閲覧制限モード（パスワード必須）
Mode B: コピー・印刷制限モード（パスワード設定）
"""

from __future__ import annotations

import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.config import Colors, Config
from src.components import ModernButton
from src.services.pdf_password import set_pdf_password, remove_pdf_password
from src.utils import open_folder


def build_password_tab(app):
    """Build password tab with two separate modes"""
    # タブ全体は固定（スクロールしない）
    container = tk.Frame(app.tab_password, bg=Colors.BG_MAIN)
    container.pack(fill="both", expand=True, padx=Config.PADDING_LARGE, pady=(Config.PADDING_LARGE, 0))

    # ===== Title =====
    title_frame = tk.Frame(container, bg=Colors.BG_MAIN)
    title_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        title_frame,
        text="🔒    パスワード保護",
        font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left")

    tk.Label(
        title_frame,
        text="PDFにパスワードを設定/解除します（複数選択可）",
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(10, 0))

    # ===== state =====
    app.password_files = []
    app.password_files_label = tk.StringVar(value="（未選択）")

    # ===== helpers =====
    def _sync_hint():
        if not hasattr(app, "password_hint_label"):
            return
        if app.password_files:
            app.password_hint_label.place_forget()
        else:
            app.password_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    def _refresh_left_list():
        app.password_listbox.delete(0, tk.END)
        for p in app.password_files:
            app.password_listbox.insert(tk.END, f"  📄 {p.name}")

        app.password_files_label.set(f"{len(app.password_files)} 個のPDFファイル" if app.password_files else "（未選択）")
        _sync_hint()

        if app.password_files:
            app.update_pdf_info(app.password_files[0])
            app.status.set(f"{len(app.password_files)} 個のPDFを選択しました。")
        else:
            app.update_pdf_info(None)
            app.status.set("（未選択）")

    def _add_files(paths: list[Path]):
        if not paths:
            return
        exist = {str(p) for p in app.password_files}
        for p in paths:
            if str(p) not in exist:
                app.password_files.append(p)
                exist.add(str(p))
        _refresh_left_list()

    def on_drop_password(event):
        pdf_paths = app._iter_dnd_pdf_paths(event)
        if not pdf_paths:
            return
        _add_files(pdf_paths)

    def choose_files():
        paths = filedialog.askopenfilenames(
            title="PDFを選択",
            filetypes=[("PDFファイル", "*.pdf")],
        )
        if not paths:
            return
        _add_files([Path(p) for p in paths])

    def remove_selected():
        sel = app.password_listbox.curselection()
        if not sel:
            return
        for idx in reversed(sel):
            if idx < len(app.password_files):
                del app.password_files[idx]
        _refresh_left_list()

    def clear_files():
        app.password_files = []
        _refresh_left_list()
        app.status.set("ファイルリストをクリアしました。")

    # 右側表示切替
    def _toggle_operation_mode():
        if app.password_operation_mode.get() == "set":
            app.password_set_container.pack(fill="x", pady=(0, 10), after=app.password_operation_frame)
            app.password_remove_container.pack_forget()
        else:
            app.password_remove_container.pack(fill="x", pady=(0, 10), after=app.password_operation_frame)
            app.password_set_container.pack_forget()

    def _toggle_protection_mode():
        if app.password_protection_mode.get() == "view":
            app.mode_a_frame.pack(fill="x", pady=(0, 5))
            app.mode_b_frame.pack_forget()
        else:
            app.mode_b_frame.pack(fill="x", pady=(0, 5))
            app.mode_a_frame.pack_forget()

    # ===== execute =====
    def execute_password():
        if not app.password_files:
            messagebox.showwarning("警告", "PDFファイルを選択してください。")
            return

        op = app.password_operation_mode.get()
        if op == "set":
            _execute_set()
        else:
            _execute_remove()

    def _build_out_path(src_file: Path, pattern: str, out_dir: Path | None) -> Path:
        name = pattern.replace("{name}", src_file.stem) if "{name}" in pattern else pattern
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return (out_dir / name) if out_dir else (src_file.parent / name)

    def _execute_set():
        mode = app.password_protection_mode.get()

        if mode == "view":
            password = app.password_view_entry.get().strip()
            if not password:
                messagebox.showwarning("警告", "パスワードを入力してください。")
                return
            require_open_password = True
            forbid_copy = False
            forbid_print = False
        else:
            password = app.password_restrict_entry.get().strip()
            if not password:
                messagebox.showwarning("警告", "パスワードを入力してください。")
                return
            if not (app.forbid_copy.get() or app.forbid_print.get()):
                messagebox.showwarning("警告", "少なくとも1つの制限を選択してください。")
                return
            require_open_password = False
            forbid_copy = app.forbid_copy.get()
            forbid_print = app.forbid_print.get()

        pattern = app.get_entry_text(app.password_filename_entry).strip()
        if not pattern:
            pattern = "{name}_ロック済み.pdf"

        dir_str = app.output_dir_var.get().strip()
        out_dir = Path(dir_str) if dir_str else None

        def worker():
            success = 0
            failed = []

            for i, src_file in enumerate(app.password_files):
                try:
                    out_path = _build_out_path(src_file, pattern, out_dir)

                    if not app.confirm_overwrite(out_path):
                        failed.append(f"{src_file.name} (スキップ)")
                        continue

                    set_pdf_password(
                        src=src_file,
                        out_path=out_path,
                        owner_password=password,
                        forbid_copy=forbid_copy,
                        forbid_print=forbid_print,
                        require_open_password=require_open_password,
                    )

                    success += 1
                    progress = int((i + 1) / len(app.password_files) * 100)
                    app.after(0, lambda p=progress: app.progress_set(p))

                except Exception as e:
                    failed.append(f"{src_file.name}: {str(e)}")

            def _finish():
                app.progress_done()
                app.set_actions_state(True)

                if success > 0:
                    mode_name = "閲覧制限" if mode == "view" else "コピー・印刷制限"
                    msg = f"パスワード設定（{mode_name}）が完了しました。\n成功: {success} 件"
                    if failed:
                        msg += f"\n失敗/スキップ: {len(failed)} 件"
                    messagebox.showinfo("完了", msg)
                    app.status.set(f"パスワード設定完了: {success} 件")

                    if app.open_after.get():
                        # out_dirが指定されていればフォルダ、未指定なら最後の出力ファイル
                        if out_dir:
                            open_folder(out_dir)
                        else:
                            # 代表で最後の出力
                            last_out = _build_out_path(app.password_files[-1], pattern, None)
                            open_folder(last_out)
                else:
                    messagebox.showerror("エラー", "すべてのファイルの処理に失敗しました。")
                    app.status.set("パスワード設定に失敗しました")

            app.after(0, _finish)

        app.progress_reset()
        app.status.set("パスワード設定中...")
        app.set_actions_state(False)
        threading.Thread(target=worker, daemon=True).start()

    def _execute_remove():
        password = app.password_remove_entry.get().strip()
        if not password:
            messagebox.showwarning("警告", "パスワードを入力してください。")
            return

        pattern = app.get_entry_text(app.password_filename_entry).strip()
        if not pattern:
            pattern = "{name}_解除済み.pdf"

        dir_str = app.output_dir_var.get().strip()
        out_dir = Path(dir_str) if dir_str else None

        def worker():
            success = 0
            failed = []

            for i, src_file in enumerate(app.password_files):
                try:
                    out_path = _build_out_path(src_file, pattern, out_dir)

                    if not app.confirm_overwrite(out_path):
                        failed.append(f"{src_file.name} (スキップ)")
                        continue

                    remove_pdf_password(
                        src=src_file,
                        out_path=out_path,
                        password=password,
                    )

                    success += 1
                    progress = int((i + 1) / len(app.password_files) * 100)
                    app.after(0, lambda p=progress: app.progress_set(p))

                except Exception as e:
                    failed.append(f"{src_file.name}: {str(e)}")

            def _finish():
                app.progress_done()
                app.set_actions_state(True)

                if success > 0:
                    msg = f"パスワード解除が完了しました。\n成功: {success} 件"
                    if failed:
                        msg += f"\n失敗/スキップ: {len(failed)} 件"
                    messagebox.showinfo("完了", msg)
                    app.status.set(f"パスワード解除完了: {success} 件")

                    if app.open_after.get():
                        if out_dir:
                            open_folder(out_dir)
                        else:
                            last_out = _build_out_path(app.password_files[-1], pattern, None)
                            open_folder(last_out)
                else:
                    messagebox.showerror("エラー", "すべてのファイルの処理に失敗しました。")
                    app.status.set("パスワード解除に失敗しました")

            app.after(0, _finish)

        app.progress_reset()
        app.status.set("パスワード解除中...")
        app.set_actions_state(False)
        threading.Thread(target=worker, daemon=True).start()

    # ===== DnD (container + left_panel) =====
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            container.drop_target_register(app._dnd_token)
            container.dnd_bind("<<Drop>>", on_drop_password)
    except Exception:
        pass

    # ===========================
    # Two Column Layout with Resizable Splitter
    # ===========================
    main_container = ttk.PanedWindow(container, orient=tk.HORIZONTAL)
    main_container.pack(fill="both", expand=True, pady=(0, 5))

    # Left: files
    left_panel = ttk.LabelFrame(main_container, text="📁 対象PDFファイル", padding=10)
    main_container.add(left_panel, weight=1)

    # Right: settings/execute
    right_panel = ttk.LabelFrame(main_container, text="⚙️ 設定", padding=10)
    main_container.add(right_panel, weight=1)
    
    # 右パネル内にScrollableFrameを追加
    from src.ui.scrollable_frame import ScrollableFrame
    right_scroll = ScrollableFrame(right_panel)
    right_scroll.pack(fill="both", expand=True)
    right_content = right_scroll.scrollable_frame

    # ---------------------------
    # Left panel contents
    # ---------------------------
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
        textvariable=app.password_files_label,
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(5, 5))

    listbox_frame = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    listbox_frame.pack(fill="both", expand=True)

    app.password_listbox = tk.Listbox(
        listbox_frame,
        font=(Config.FONT_FAMILY, 10),
        selectmode=tk.EXTENDED,
        relief="solid",
        borderwidth=1,
        highlightthickness=0,
        bg="white",
    )
    app.password_listbox.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=app.password_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    app.password_listbox.config(yscrollcommand=scrollbar.set)
    
    # マウスホイールでのスクロールを有効化
    def _on_mousewheel(event):
        app.password_listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
    app.password_listbox.bind("<MouseWheel>", _on_mousewheel)
    app.password_listbox.bind("<Button-4>", lambda e: app.password_listbox.yview_scroll(-1, "units"))
    app.password_listbox.bind("<Button-5>", lambda e: app.password_listbox.yview_scroll(1, "units"))

    app.password_hint_label = tk.Label(
        listbox_frame,
        text="💡 ファイルをドラッグ&ドロップで追加できます",
        font=(Config.FONT_FAMILY, 11),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    )
    app.password_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            left_panel.drop_target_register(app._dnd_token)
            left_panel.dnd_bind("<<Drop>>", on_drop_password)
    except Exception:
        pass

    # ---------------------------
    # Right panel contents
    #   上: 設定（スクロール不要想定）
    #   下: 「出力パターン」→「実行」を最下部固定
    # ---------------------------

    # Operation mode (set/remove)
    app.password_operation_mode = tk.StringVar(value="set")

    app.password_operation_frame = tk.Frame(right_content, bg=Colors.BG_MAIN)
    app.password_operation_frame.pack(fill="x", pady=(0, 10))

    tk.Radiobutton(
        app.password_operation_frame,
        text="🔐 パスワードを設定",
        variable=app.password_operation_mode,
        value="set",
        font=(Config.FONT_FAMILY, 11, "bold"),
        bg=Colors.BG_MAIN,
        activebackground=Colors.BG_MAIN,
        command=_toggle_operation_mode,
    ).pack(side="left", padx=(0, 20))

    tk.Radiobutton(
        app.password_operation_frame,
        text="🔓 パスワードを解除",
        variable=app.password_operation_mode,
        value="remove",
        font=(Config.FONT_FAMILY, 11, "bold"),
        bg=Colors.BG_MAIN,
        activebackground=Colors.BG_MAIN,
        command=_toggle_operation_mode,
    ).pack(side="left")

    # ===== SET MODE container =====
    app.password_set_container = tk.Frame(right_content, bg=Colors.BG_MAIN)

    # Protection mode selection
    app.password_protection_mode = tk.StringVar(value="restrict")

    tk.Label(
        app.password_set_container,
        text="保護モードを選択:",
        font=(Config.FONT_FAMILY, 11, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(0, 5))

    mode_buttons_frame = tk.Frame(app.password_set_container, bg=Colors.BG_MAIN)
    mode_buttons_frame.pack(fill="x", pady=(0, 8))

    tk.Radiobutton(
        mode_buttons_frame,
        text="モードA: 閲覧制限",
        variable=app.password_protection_mode,
        value="view",
        font=(Config.FONT_FAMILY, 10, "bold"),
        bg=Colors.BG_MAIN,
        activebackground=Colors.BG_MAIN,
        command=_toggle_protection_mode,
    ).pack(side="left", padx=(0, 30))

    tk.Radiobutton(
        mode_buttons_frame,
        text="モードB: コピー・印刷制限",
        variable=app.password_protection_mode,
        value="restrict",
        font=(Config.FONT_FAMILY, 10, "bold"),
        bg=Colors.BG_MAIN,
        activebackground=Colors.BG_MAIN,
        command=_toggle_protection_mode,
    ).pack(side="left")

    # ---- Mode A ----
    app.mode_a_frame = ttk.LabelFrame(app.password_set_container, text="📖 モードA: 閲覧制限", padding=8)

    tk.Label(
        app.mode_a_frame,
        text="PDFを開くにはパスワードが必要になります",
        font=(Config.FONT_FAMILY, 9),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    ).pack(anchor="w", pady=(0, 5))

    pwd_a_frame = tk.Frame(app.mode_a_frame, bg="white", height=40)
    pwd_a_frame.pack(fill="x", pady=5)
    pwd_a_frame.pack_propagate(False)

    tk.Label(
        pwd_a_frame,
        text="パスワード:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        bg="white",
    ).pack(side="left", padx=(0, 10), pady=8)

    app.password_view_entry = tk.Entry(
        pwd_a_frame,
        font=(Config.FONT_FAMILY, 11),
        show="●",
        relief="solid",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
        borderwidth=1,
    )
    app.password_view_entry.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=5)

    # ---- Mode B ----
    app.mode_b_frame = ttk.LabelFrame(app.password_set_container, text="🔒 モードB: コピー・印刷制限", padding=8)

    tk.Label(
        app.mode_b_frame,
        text="PDFは自由に開けますが、コピー・印刷が制限されます",
        font=(Config.FONT_FAMILY, 9),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    ).pack(anchor="w", pady=(0, 5))

    pwd_b_frame = tk.Frame(app.mode_b_frame, bg="white", height=40)
    pwd_b_frame.pack(fill="x", pady=5)
    pwd_b_frame.pack_propagate(False)

    tk.Label(
        pwd_b_frame,
        text="パスワード:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        bg="white",
    ).pack(side="left", padx=(0, 10), pady=8)

    app.password_restrict_entry = tk.Entry(
        pwd_b_frame,
        font=(Config.FONT_FAMILY, 11),
        show="●",
        relief="solid",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
        borderwidth=1,
    )
    app.password_restrict_entry.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=5)

    app.forbid_copy = tk.BooleanVar(value=True)
    app.forbid_print = tk.BooleanVar(value=False)

    restrict_row = tk.Frame(app.mode_b_frame, bg="white")
    restrict_row.pack(anchor="w", pady=(10, 5), padx=10)

    tk.Label(
        restrict_row,
        text="制限する項目:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        bg="white",
    ).pack(side="left", padx=(0, 10))

    for var, text in [(app.forbid_copy, "📋 コピー禁止"), (app.forbid_print, "🖨️ 印刷禁止")]:
        tk.Checkbutton(
            restrict_row,
            text=text,
            variable=var,
            font=(Config.FONT_FAMILY, 9),
            bg="white",
            activebackground="white",
        ).pack(side="left", padx=(0, 15))

    tk.Label(
        restrict_row,
        text="※ 少なくとも1つの制限を選択してください",
        font=(Config.FONT_FAMILY, 8),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    ).pack(side="left", padx=(0, 0))

    # ===== REMOVE MODE container =====
    app.password_remove_container = tk.Frame(right_content, bg=Colors.BG_MAIN)

    remove_frame = ttk.LabelFrame(app.password_remove_container, text="🔓 パスワード解除", padding=8)
    remove_frame.pack(fill="x")

    pwd_remove_frame = tk.Frame(remove_frame, bg="white", height=40)
    pwd_remove_frame.pack(fill="x", pady=5)
    pwd_remove_frame.pack_propagate(False)

    tk.Label(
        pwd_remove_frame,
        text="現在のパスワード:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        bg="white",
    ).pack(side="left", padx=(0, 10), pady=8)

    app.password_remove_entry = tk.Entry(
        pwd_remove_frame,
        font=(Config.FONT_FAMILY, 11),
        show="●",
        relief="solid",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
        borderwidth=1,
    )
    app.password_remove_entry.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=5)

    # ===== Bottom: output pattern THEN execute (あなたの希望) =====
    # 出力フォルダ
    from src.ui.tab_base import make_output_folder_row
    make_output_folder_row(right_content, app=app)
    
    output_frame = tk.Frame(right_content, bg=Colors.BG_MAIN)
    output_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        output_frame,
        text="📝 出力ファイル名:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w",pady=(0, 0))

    row = tk.Frame(output_frame, bg=Colors.BG_MAIN)
    row.pack(fill="x", pady=(6, 0))

    app.password_filename_entry = tk.Entry(
        row,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    app.password_filename_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

    app.init_placeholder(app.password_filename_entry, "空欄:'元ファイル名'_ロック済み/解除済み.pdf")

    # オプション
    from src.ui.tab_base import make_options_checkboxes
    make_options_checkboxes(right_content, app=app)

    app.password_execute_btn = ModernButton(
        right_content,
        text="🚀 パスワード設定/解除を実行",
        command=execute_password,
        style="primary",
    )
    app.password_execute_btn.pack(fill="x", pady=(10, 0))
    app.action_buttons.append(app.password_execute_btn)

    # ===== initial view =====
    _toggle_operation_mode()
    _toggle_protection_mode()
    _refresh_left_list()


# 互換用（外部から呼ぶ想定があるなら残す）
# ここでは build_password_tab 内にロジックを閉じたため不要だが、
# 既存コードが呼んでいる場合に備えて「何もしない」関数を残すならここで定義してもOK。
