"""
Compress Tab - Two Panel Layout (Like Password Tab)

Left : ファイル選択（リスト + ボタン）
Right: 設定（圧縮レベル / 目標サイズ / 出力ファイル名 / 実行）
"""

from __future__ import annotations

import threading
import subprocess
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.config import Colors, Config
from src.components import ModernButton
from src.utils import find_gs, open_folder
from src.services.pdf_compress import compress_pdfs


def build_compress_tab(app):
    from src.ui.scrollable_frame import ScrollableFrame
    
    # スクロール可能なフレームを作成
    scroll_container = ScrollableFrame(app.tab_compress)
    scroll_container.pack(fill="both", expand=True)
    
    # 実際のコンテンツはscrollable_frameに配置
    temp_container = scroll_container.scrollable_frame
    
    # パディング用の外側フレーム
    container = tk.Frame(temp_container, bg=Colors.BG_MAIN)
    container.pack(fill="both", expand=True, padx=Config.PADDING_LARGE, pady=Config.PADDING_LARGE)

    # ===== Title =====
    title_frame = tk.Frame(container, bg=Colors.BG_MAIN)
    title_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        title_frame,
        text="🗜️PDF圧縮",
        font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left")
    tk.Label(
        title_frame,
        text="PDFの容量を小さくします（複数選択可）",
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(10, 0))

    # --------------------
    # state
    # --------------------
    app.compress_files: list[Path] = []
    app.compress_files_label = tk.StringVar(value="（未選択）")

    # --------------------
    # helpers
    # --------------------
    def get_compress_default_name(src: Path) -> str:
        return f"{src.stem}_圧縮済み.pdf"

    def get_compress_default_suffix() -> str:
        # UX重視：{name}前提
        return "{name}_圧縮済み.pdf"

    def _sync_hint():
        if not hasattr(app, "compress_hint_label"):
            return
        if app.compress_files:
            app.compress_hint_label.place_forget()
        else:
            app.compress_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    def update_suffix_placeholder():
        if not hasattr(app, "compress_suffix_entry"):
            return
        if app.compress_files:
            # 入力例がわかりやすい：元ファイル名入りの例
            placeholder = get_compress_default_name(app.compress_files[0])
        else:
            placeholder = "空欄:'元ファイル名'_圧縮済み.pdf"
        app.set_placeholder(app.compress_suffix_entry, placeholder)

    def _refresh_left_list():
        app.compress_listbox.delete(0, tk.END)
        for p in app.compress_files:
            app.compress_listbox.insert(tk.END, f"  📄 {p.name}")

        app.compress_files_label.set(
            f"{len(app.compress_files)} 個のPDFファイル" if app.compress_files else "（未選択）"
        )

        _sync_hint()

        if app.compress_files:
            app.update_pdf_info(app.compress_files[0])
        else:
            app.update_pdf_info(None)

        update_suffix_placeholder()

    def _add_files(paths: list[Path]):
        if not paths:
            return
        for p in paths:
            if p not in app.compress_files:
                app.compress_files.append(p)
        _refresh_left_list()
        app.status.set(f"{len(app.compress_files)} 個のPDFを選択しました。")

    def on_drop_compress(event):
        pdf_paths = app._iter_dnd_pdf_paths(event)
        if not pdf_paths:
            return
        _add_files(pdf_paths)

    def choose_files():
        paths = filedialog.askopenfilenames(
            title="圧縮するPDFを選択",
            filetypes=[("PDFファイル", "*.pdf")],
        )
        if not paths:
            return
        _add_files([Path(p) for p in paths])

    def remove_selected():
        sel = app.compress_listbox.curselection()
        if not sel:
            return
        for idx in reversed(sel):
            if idx < len(app.compress_files):
                del app.compress_files[idx]
        _refresh_left_list()
        app.status.set(f"残り {len(app.compress_files)} ファイル")

    def clear_files():
        app.compress_files = []
        _refresh_left_list()
        app.status.set("ファイルリストをクリアしました。")

    def on_compress_scale_release(_event=None):
        # ttk.Scale は float で来るので丸める
        try:
            val = float(app.compress_level.get())
        except Exception:
            val = 3.0
        val = round(val)
        val = max(1, min(5, val))
        app.compress_level.set(val)

    def run_compress():
        if not app.compress_files:
            messagebox.showwarning("警告", "圧縮するPDFを選んでください。")
            return

        # Ghostscript
        if not hasattr(app, "gs_path") or app.gs_path is None:
            app.gs_path = find_gs()

        if not app.gs_path:
            messagebox.showerror("エラー", "Ghostscript が見つかりません。圧縮を実行できません。")
            return

        # 目標サイズ
        target_mb: Optional[float] = None
        raw = app.target_size_mb.get().strip()
        if raw:
            try:
                v = float(raw)
                if v > 0:
                    target_mb = v
            except ValueError:
                messagebox.showwarning("警告", "目標サイズ(MB) は数値で入力してください。")
                return

        # 出力パターン
        pattern = app.get_entry_text(app.compress_suffix_entry).strip()

        sources: list[Path] = []
        out_paths: list[Path] = []
        report_skip: list[str] = []

        # 出力フォルダ（共通）
        dir_str = app.output_dir_var.get().strip()
        out_dir = Path(dir_str) if dir_str else None

        for src in app.compress_files:
            src = Path(src)

            if not pattern:
                out_name = get_compress_default_name(src)
            else:
                if "{name}" in pattern:
                    out_name = pattern.replace("{name}", src.stem)
                else:
                    out_name = pattern
                if not out_name.lower().endswith(".pdf"):
                    out_name += ".pdf"

            out_path = (out_dir / out_name) if out_dir else src.with_name(out_name)

            if not app.confirm_overwrite(out_path):
                report_skip.append(f"{src.name}: スキップ（既存ファイル有りのため）")
                continue

            sources.append(src)
            out_paths.append(out_path)

        if not sources:
            app.status.set("圧縮をキャンセルしました（すべてスキップ）")
            return

        app.progress_reset()
        app.set_actions_state(False)
        app.status.set("圧縮処理を開始しました...")

        gs_path = app.gs_path
        level = int(app.compress_level.get())
        total = len(sources)

        def progress_cb(percent: float, msg: str):
            def _u():
                app.progress_set(percent)
                app.status.set(msg)
            app.after(0, _u)

        def worker():
            try:
                results = compress_pdfs(
                    sources=sources,
                    out_paths=out_paths,
                    gs_path=gs_path,
                    level=level,
                    target_mb=target_mb,
                    progress_cb=progress_cb,
                )

            except subprocess.CalledProcessError as e:
                def _on_error():
                    messagebox.showerror("エラー", f"圧縮中にエラーが発生しました:\n{e}")
                    app.status.set("圧縮に失敗しました")
                    app.set_actions_state(True)
                    app.progress_reset()
                app.after(0, _on_error)
                return

            except Exception as e:
                def _on_error():
                    messagebox.showerror("エラー", f"圧縮中に予期しないエラーが発生しました:\n{e}")
                    app.status.set("圧縮に失敗しました")
                    app.set_actions_state(True)
                    app.progress_reset()
                app.after(0, _on_error)
                return

            def _on_success():
                app.progress_done()
                app.set_actions_state(True)

                lines = []
                if target_mb is not None:
                    lines.append(f"[目標サイズ: {target_mb:.2f}MB]")
                    lines.append("")

                if report_skip:
                    lines.append("スキップ:")
                    lines.extend(report_skip)
                    lines.append("")

                if results:
                    lines.append("圧縮結果:")
                    for r in results:
                        lines.append(
                            f"{r.src.name}: {r.orig_mb:.2f}MB → {r.new_mb:.2f}MB "
                            f"({r.reduced_percent:.1f}%削減 / {r.setting})"
                        )

                msg = "\n".join(lines) if lines else "圧縮が完了しました。"
                messagebox.showinfo("完了", msg)
                app.status.set(f"圧縮を完了しました: 成功 {len(results)} 件 / 対象 {total} 件")

                if app.open_after.get() and results:
                    open_folder(results[-1].out)

            app.after(0, _on_success)

        threading.Thread(target=worker, daemon=True).start()

    # --------------------
    # DnD (container only)
    # --------------------
    try:
        if hasattr(app, "dnd_available") and app.dnd_available:
            container.drop_target_register(app._dnd_token)
            container.dnd_bind("<<Drop>>", on_drop_compress)
    except:
        pass

    # ====================
    # Layout (Two Panel)
    # ====================
    main_container = ttk.Frame(container)
    main_container.pack(fill="both", expand=True, pady=(0, 5))

    left_panel = ttk.LabelFrame(main_container, text="📁 対象PDFファイル", padding=10)
    left_panel.pack(side="left", fill="both", expand=False)
    left_panel.pack_propagate(False)
    left_panel.configure(width=280)

    right_panel = ttk.LabelFrame(main_container, text="⚙️ 設定", padding=10)
    right_panel.pack(side="left", fill="both", expand=True, padx=(8, 0))

    # --------------------
    # Left panel
    # --------------------
    btn_frame = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    btn_frame.pack(fill="x", pady=(0, 5))

    btn_choose = ModernButton(btn_frame, text="📁 PDFを選択", command=choose_files, style="secondary")
    btn_choose.pack(side="left", padx=(0, 5))

    btn_del = ModernButton(btn_frame, text="🗑️ 削除", command=remove_selected, style="secondary")
    btn_del.pack(side="left", padx=5)

    btn_clear = ModernButton(btn_frame, text="🔄    クリア", command=clear_files, style="danger")
    btn_clear.pack(side="left")

    app.action_buttons.extend([btn_choose, btn_del, btn_clear])

    tk.Label(
        left_panel,
        textvariable=app.compress_files_label,
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    ).pack(anchor="w", pady=(5, 5))

    listbox_frame = tk.Frame(left_panel, bg=Colors.BG_MAIN)
    listbox_frame.pack(fill="both", expand=True)

    app.compress_listbox = tk.Listbox(
        listbox_frame,
        font=(Config.FONT_FAMILY, 10),
        selectmode=tk.EXTENDED,
        relief="solid",
        borderwidth=1,
        highlightthickness=0,
        bg="white",
    )
    app.compress_listbox.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=app.compress_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    app.compress_listbox.config(yscrollcommand=scrollbar.set)

    app.compress_hint_label = tk.Label(
        listbox_frame,
        text="💡 ファイルをドラッグ&ドロップで追加できます",
        font=(Config.FONT_FAMILY, 11),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    )
    app.compress_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    # --------------------
    # Right panel (Settings)
    # --------------------
    # ① 圧縮レベル
    level_frame = ttk.LabelFrame(right_panel, text="🎚️圧縮レベル", padding=8)
    level_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        level_frame,
        text="数字が小さいほど画質優先、大きいほどファイルサイズ優先",
        font=(Config.FONT_FAMILY, 9),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    ).pack(anchor="w", pady=(0, 6))

    app.compress_level = tk.IntVar(value=3)

    scale_label_frame = tk.Frame(level_frame, bg="white", height=20)
    scale_label_frame.pack(fill="x", pady=(0, 2))
    scale_label_frame.pack_propagate(False)

    for level, relx in {1: 0.005, 3: 0.5, 5: 0.995}.items():
        tk.Label(
            scale_label_frame,
            text=str(level),
            font=(Config.FONT_FAMILY, 10, "bold"),
            fg=Colors.TEXT_PRIMARY,
            bg="white",
        ).place(relx=relx, rely=0.5, anchor="center")

    app.compress_scale = ttk.Scale(
        level_frame,
        from_=1,
        to=5,
        orient="horizontal",
        variable=app.compress_level,
    )
    app.compress_scale.pack(fill="x", pady=(0, 6))
    app.compress_scale.bind("<ButtonRelease-1>", on_compress_scale_release)

    info_frame = tk.Frame(level_frame, bg="white")
    info_frame.pack(fill="x")
    tk.Label(
        info_frame, text="低圧縮（高画質）",
        font=(Config.FONT_FAMILY, 8),
        fg=Colors.TEXT_SECONDARY, bg="white"
    ).pack(side="left")
    tk.Label(
        info_frame, text="高圧縮（低画質）",
        font=(Config.FONT_FAMILY, 8),
        fg=Colors.TEXT_SECONDARY, bg="white"
    ).pack(side="right")

    # ② 目標サイズ
    size_frame = ttk.LabelFrame(right_panel, text="📌 目標サイズ（参考値）", padding=8)
    size_frame.pack(fill="x", pady=(0, 10))

    row = tk.Frame(size_frame, bg="white", height=40)
    row.pack(fill="x", pady=5)
    row.pack_propagate(False)

    tk.Label(row, text="目標サイズ:", font=(Config.FONT_FAMILY, 10, "bold"), bg="white").pack(
        side="left", padx=(0, 10), pady=8
    )

    app.target_size_mb = tk.StringVar(value="")
    app.target_size_entry = tk.Entry(
        row,
        font=(Config.FONT_FAMILY, 11),
        relief="solid",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
        borderwidth=1,
        width=10,
        textvariable=app.target_size_mb,
    )
    app.target_size_entry.pack(side="left", padx=(0, 10), pady=5)

    tk.Label(row, text="MB以下", font=(Config.FONT_FAMILY, 10), bg="white").pack(side="left", pady=8)

    tk.Label(
        size_frame,
        text=(
            "※ 目標サイズ(MB)は「このサイズ以下を目指す上限値」です。\n"
            "   PDFの内容により、指定した値に一致するとは限らず、"
            "   十分に小さくできない場合もあります。"
        ),
        font=(Config.FONT_FAMILY, 8),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
        justify="left",
    ).pack(anchor="w", pady=(6, 0))

    # 出力フォルダ
    from src.ui.tab_base import make_output_folder_row
    make_output_folder_row(right_panel, app=app)

    # ③ 出力ファイル名
    output_frame = tk.Frame(right_panel, bg=Colors.BG_MAIN)
    output_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        output_frame,
        text="📝 出力ファイル名:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN,
    ).pack(side="left", padx=(0, 10))

    app.compress_suffix_entry = tk.Entry(
        output_frame,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    app.compress_suffix_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))


    app.init_placeholder(app.compress_suffix_entry, get_compress_default_suffix())
    update_suffix_placeholder()

    # オプション
    from src.ui.tab_base import make_options_checkboxes
    make_options_checkboxes(right_panel, app=app)

    # ④ 実行
    btn_exec = ModernButton(
        right_panel,
        text="🚀 圧縮を実行",
        command=run_compress,
        style="primary",
    )
    btn_exec.pack(fill="x", pady=(10, 0))
    app.action_buttons.append(btn_exec)

    # appに関数をぶら下げ
    app.choose_compress_pdfs = choose_files
    app.clear_compress_pdfs = clear_files
    app.run_compress = run_compress
    app.update_compress_suffix_placeholder = update_suffix_placeholder

    _refresh_left_list()
