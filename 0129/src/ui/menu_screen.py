"""
Menu Screen - アプリケーションのメイン機能選択画面
"""
import tkinter as tk
from tkinter import ttk
from src.config import Colors, Config


class MenuCard(tk.Frame):
    """メニューカード - ホバー効果付き"""
    
    def __init__(self, master, icon, title, description, command, **kwargs):
        self.card_width = kwargs.pop('width', 280)
        self.card_height = kwargs.pop('height', 220)

        super().__init__(master, bg=Colors.BG_MAIN, relief="flat", borderwidth=2, **kwargs)
        self.command = command
        self.default_bg = Colors.BG_MAIN
        self.hover_bg = Colors.BG_SECONDARY
        self.border_color = Colors.BORDER
        self.hover_border_color = Colors.PRIMARY_LIGHT

        
        # カード内レイアウト
        self.configure(
        width=self.card_width,
        height=self.card_height,
        highlightbackground=self.border_color,
        highlightthickness=2,
        cursor="hand2"
        )
        self.pack_propagate(False)  # 内容に応じてサイズが変わらないようにする
        
        # アイコン
        icon_label = tk.Label(
            self,
            text=icon,
            font=(Config.FONT_FAMILY, 42),
            bg=self.default_bg,
            fg=Colors.PRIMARY,
        )
        icon_label.pack(pady=(20, 10))
        
        # タイトル
        title_label = tk.Label(
            self,
            text=title,
            font=(Config.FONT_FAMILY, 20, "bold"),
            bg=self.default_bg,
            fg=Colors.TEXT_PRIMARY,
        )
        title_label.pack(pady=(0, 8))
        
        # 説明
        desc_label = tk.Label(
            self,
            text=description,
            font=(Config.FONT_FAMILY, 12),
            bg=self.default_bg,
            fg=Colors.TEXT_SECONDARY,
            wraplength=200,
            justify="center",
        )
        desc_label.pack(pady=(0, 20))
        
        # ホバー効果用のバインディング
        self._bind_hover_recursive(self)
        
    def _bind_hover_recursive(self, widget):
        """ウィジェットとその子要素すべてにホバーイベントをバインド"""
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<Button-1>", self._on_click)
        
        for child in widget.winfo_children():
            self._bind_hover_recursive(child)
    
    def _on_enter(self, event):
        """マウスがカードに入った時"""
        self.configure(bg=self.hover_bg, highlightbackground=self.hover_border_color)
        for widget in self._get_all_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=self.hover_bg)
    
    def _on_leave(self, event):
        """マウスがカードから出た時"""
        self.configure(bg=self.default_bg, highlightbackground=self.border_color)
        for widget in self._get_all_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=self.default_bg)
    
    def _on_click(self, event):
        """カードがクリックされた時"""
        if self.command:
            self.command()
    
    def _get_all_children(self):
        """すべての子ウィジェットを取得"""
        children = []
        for child in self.winfo_children():
            children.append(child)
            if hasattr(child, 'winfo_children'):
                children.extend(self._get_all_children_recursive(child))
        return children
    
    def _get_all_children_recursive(self, widget):
        """再帰的にすべての子ウィジェットを取得"""
        children = []
        for child in widget.winfo_children():
            children.append(child)
            if hasattr(child, 'winfo_children'):
                children.extend(self._get_all_children_recursive(child))
        return children
    

def build_menu_screen(app):
    """メニュー画面を構築"""
    from src.ui.scrollable_frame import ScrollableFrame
    
    # スクロール可能なメインコンテナ
    scroll_wrapper = ScrollableFrame(app)
    menu_container = scroll_wrapper.scrollable_frame
    
    # ヘッダーセクション
    header_frame = tk.Frame(menu_container, bg=Colors.BG_MAIN)
    header_frame.pack(pady=(20, 15))

    """
    # メインタイトル
    title_label = tk.Label(
        header_frame,
        text="📄 らくらくPDF",
        font=(Config.FONT_FAMILY, 28, "bold"),
        fg=Colors.PRIMARY,
        bg=Colors.BG_MAIN,
    )
    title_label.pack()
    """
    
    # サブタイトル
    subtitle_label = tk.Label(
        header_frame,
        text="使いたい機能を選択してください",
        font=(Config.FONT_FAMILY, 20),
        fg=Colors.TEXT_SECONDARY,
        bg=Colors.BG_MAIN,
    )
    subtitle_label.pack(pady=(10, 0))
    
    # カードグリッドコンテナ
    cards_frame = tk.Frame(menu_container, bg=Colors.BG_MAIN)
    cards_frame.pack(pady=10, padx=60)
    
    # 機能定義
    features = [
        {
            "icon": "📑",
            "title": "結合",
            "description": "複数のPDFファイルを\n1つに結合します",
            "tab": "merge"
        },
        {
            "icon": "     ✂️",
            "title": "抽出/削除",
            "description": "特定のページを抽出\nまたは削除します",
            "tab": "split"
        },
        {
            "icon": "🔄",
            "title": "並び替え",
            "description": "ページの順序を\n自由に変更します",
            "tab": "reorder"
        },
        {
            "icon": "     🗜️",
            "title": "圧縮",
            "description": "PDFファイルサイズを\n削減します",
            "tab": "compress"
        },
        {
            "icon": "📝",
            "title": "変換",
            "description": "PDFを他の形式に\n変換します",
            "tab": "convert"
        },
        {
            "icon": "🔒",
            "title": "パスワード",
            "description": "パスワードの設定や\n解除を行います",
            "tab": "password"
        },
    ]
    
    # 2列×3行のグリッドでカードを配置
    for i, feature in enumerate(features):
        row = i // 3
        col = i % 3
        
        card = MenuCard(
            cards_frame,
            icon=feature["icon"],
            title=feature["title"],
            description=feature["description"],
            command=lambda tab=feature["tab"]: app.show_feature(tab),
            width=224,
            height=280,
        )
        card.grid(row=row, column=col, padx=20, pady=25, sticky="nsew")
    
    # フッター
    footer_frame = tk.Frame(menu_container, bg=Colors.BG_MAIN)
    footer_frame.pack(side="bottom", pady=15)
    
    version_label = tk.Label(
        footer_frame,
        text="Version 1.0",
        font=(Config.FONT_FAMILY, 9),
        fg=Colors.TEXT_LIGHT,
        bg=Colors.BG_MAIN,
    )
    version_label.pack()
    
    return scroll_wrapper
