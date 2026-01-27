"""Scrollable Frame Helper for Tabs"""

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    """スクロール可能なフレーム"""
    
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Canvasとスクロールバーを作成
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#ffffff", borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")
        
        # スクロール可能なフレームをCanvasに配置
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._update_scrollregion()
        )
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Canvas幅をフレーム幅に合わせる
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # レイアウト
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # マウスホイールでのスクロール
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.scrollable_frame)
        
        # 初期化後にスクロール領域を更新
        self.after(100, self._update_scrollregion)
    
    def _update_scrollregion(self):
        """スクロール領域を更新"""
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Canvasのサイズが変わったら、内部フレームの幅も調整"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def _bind_mousewheel(self, widget):
        """マウスホイールでのスクロールを有効化"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        widget.bind('<Enter>', _bind_to_mousewheel)
        widget.bind('<Leave>', _unbind_from_mousewheel)
