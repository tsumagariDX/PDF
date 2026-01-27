# src/ui/tab_base.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from src.config import Colors, Config


def make_tab_container(tab_frame) -> tk.Frame:
    """結合タブと同じ外枠（padding付き）"""
    container = tk.Frame(tab_frame, bg=Colors.BG_MAIN)
    container.pack(fill="both", expand=True, padx=Config.PADDING_LARGE, pady=Config.PADDING_LARGE)
    return container


def add_tab_title(container: tk.Frame, title: str, subtitle: str) -> None:
    title_frame = tk.Frame(container, bg=Colors.BG_MAIN)
    title_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        title_frame, text=title,
        font=(Config.FONT_FAMILY, Config.FONT_SIZE_TITLE, "bold"),
        fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN
    ).pack(side="left")

    tk.Label(
        title_frame, text=subtitle,
        font=(Config.FONT_FAMILY, 10),
        fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN
    ).pack(side="left", padx=(10, 0))


def make_two_column(container: tk.Frame, left_title: str, right_title: str, left_width: int = 400):
    """全タブ共通の2カラム枠を作る（左固定幅・右可変）"""
    main = ttk.Frame(container)
    main.pack(fill="both", expand=True)

    left_panel = ttk.LabelFrame(main, text=left_title, padding=10)
    left_panel.pack(side="left", fill="both", expand=False)
    left_panel.pack_propagate(False)
    left_panel.configure(width=left_width)

    right_panel = ttk.LabelFrame(main, text=right_title, padding=10)
    right_panel.pack(side="left", fill="both", expand=True, padx=(8, 0))

    return main, left_panel, right_panel


def make_listbox_with_hint(parent, *, app, var_name_listbox: str, var_name_hint: str, height: int = 6):
    """Listbox + scrollbar + hint overlay（merge/passwordと同じノリ）"""
    listbox_frame = tk.Frame(parent, bg=Colors.BG_MAIN)
    listbox_frame.pack(fill="both", expand=True, pady=(5, 0))

    lb = tk.Listbox(
        listbox_frame,
        font=(Config.FONT_FAMILY, 10),
        selectmode=tk.EXTENDED,
        height=height,
        relief="solid",
        borderwidth=1,
        highlightthickness=0,
        bg="white",
    )
    lb.pack(side="left", fill="both", expand=True)

    sb = ttk.Scrollbar(listbox_frame, orient="vertical", command=lb.yview)
    sb.pack(side="right", fill="y")
    lb.config(yscrollcommand=sb.set)

    hint = tk.Label(
        listbox_frame,
        text="💡 ファイルをドラッグ&ドロップで追加できます",
        font=(Config.FONT_FAMILY, 11),
        fg=Colors.TEXT_SECONDARY,
        bg="white",
    )
    hint.place(relx=0.5, rely=0.5, anchor="center")

    setattr(app, var_name_listbox, lb)
    setattr(app, var_name_hint, hint)
    return lb, hint, listbox_frame


def make_output_folder_row(parent, *, app):
    """出力フォルダ行（各タブで使用）"""
    from src.components import ModernButton
    
    row = tk.Frame(parent, bg=Colors.BG_MAIN)
    row.pack(fill="x", pady=(0, 10))
    
    tk.Label(
        row,
        text="📁 出力フォルダ:",
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY,
        bg=Colors.BG_MAIN
    ).pack(side="left", padx=(0, 10))
    
    entry = ttk.Entry(row, textvariable=app.output_dir_var, font=(Config.FONT_FAMILY, 10))
    entry.pack(side="left", fill="x", expand=True, padx=5)
    
    btn = ModernButton(row, text="参照", command=app.browse_output_dir, style="secondary")
    btn.pack(side="left", padx=(5, 0))
    
    return row


def make_options_checkboxes(parent, *, app):
    """オプションチェックボックス（各タブで使用）"""
    row = tk.Frame(parent, bg=Colors.BG_MAIN)
    row.pack(fill="x", pady=(10, 10))
    
    chk_open = ttk.Checkbutton(
        row,
        text="処理完了後に出力フォルダを開く",
        variable=app.open_after
    )
    chk_open.pack(anchor="w", pady=(0, 5))
    app.action_buttons.append(chk_open)
    
    chk_overwrite = ttk.Checkbutton(
        row,
        text="同名ファイルは確認せず全て上書き",
        variable=app.overwrite_all
    )
    chk_overwrite.pack(anchor="w")
    app.action_buttons.append(chk_overwrite)
    
    return row


def make_output_row(parent, *, label_text: str, app, entry_attr: str, placeholder: str):
    """出力名行（Entry + placeholder）"""
    row = tk.Frame(parent, bg=Colors.BG_MAIN)
    row.pack(fill="x", pady=(10, 0))

    tk.Label(
        row, text=label_text,
        font=(Config.FONT_FAMILY, 10, "bold"),
        fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN
    ).pack(side="left", padx=(0, 10))

    e = tk.Entry(
        row,
        font=(Config.FONT_FAMILY, 10),
        relief="flat",
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
    )
    e.pack(side="left", fill="x", expand=True)

    setattr(app, entry_attr, e)
    app.init_placeholder(e, placeholder)
    return e


def make_execute_button(parent, *, app, text: str, command, style: str = "primary"):
    """実行ボタン（必ず右側の最下段に置く想定）"""
    from src.components import ModernButton

    btn = ModernButton(parent, text=text, command=command, style=style)
    btn.pack(fill="x", pady=(12, 0))
    app.action_buttons.append(btn)
    return btn
