"""Scrollable Frame Helper for Tabs"""

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    """スクロール可能なフレーム（スクロールバー常時表示）"""
    
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Canvasとスクロールバーを作成
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#ffffff", borderwidth=0)
        # スクロールバーを常に表示（autohide無効化）
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
        
        # レイアウト（スクロールバーを常に表示）
        self.scrollbar.pack(side="right", fill="y")  # 先に配置
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # マウスホイールでのスクロール（改善版）
        self._setup_mousewheel()
        
        # スクロール領域を複数回更新（確実に反映させる）
        # 初期表示時に複数回更新（合計15回）
        update_times = [10, 50, 100, 150, 200, 300, 400, 500, 700, 1000, 1500, 2000, 3000, 4000, 5000]
        for delay in update_times:
            self.after(delay, self._update_scrollregion)
    
    def _update_scrollregion(self):
        """スクロール領域を更新（完全に書き直し - より確実な方法）"""
        try:
            self.update_idletasks()
            
            # 方法1: 子ウィジェットを再帰的に走査して最大の高さを取得
            max_bottom = 0
            max_right = 0
            
            def get_widget_bottom(widget, offset_y=0, offset_x=0):
                nonlocal max_bottom, max_right
                try:
                    # ウィジェットの実際の位置を取得
                    widget.update_idletasks()
                    y = widget.winfo_y() + offset_y
                    x = widget.winfo_x() + offset_x
                    height = widget.winfo_height()
                    width = widget.winfo_width()
                    
                    # 最大値を更新
                    max_bottom = max(max_bottom, y + height)
                    max_right = max(max_right, x + width)
                    
                    # 子ウィジェットを再帰的に処理
                    for child in widget.winfo_children():
                        get_widget_bottom(child, y, x)
                except:
                    pass
            
            # scrollable_frameから開始
            get_widget_bottom(self.scrollable_frame)
            
            # 方法2: bboxも試す（バックアップ）
            bbox = self.canvas.bbox("all")
            bbox_height = 0
            bbox_width = 0
            if bbox:
                x1, y1, x2, y2 = bbox
                bbox_height = y2
                bbox_width = x2
            
            # 方法3: scrollable_frameの要求サイズ
            frame_height = self.scrollable_frame.winfo_reqheight()
            frame_width = self.scrollable_frame.winfo_reqwidth()
            
            # 3つの方法のうち最大値を採用（余白は最小限に）
            final_height = max(max_bottom, bbox_height, frame_height) + 10  # 100→10に変更
            final_width = max(max_right, bbox_width, frame_width) + 20
            
            # スクロール領域を設定
            self.canvas.configure(scrollregion=(0, 0, final_width, final_height))
            
            # デバッグ情報（必要に応じて）
            # print(f"Scroll region updated: width={final_width}, height={final_height}")
            # print(f"  max_bottom={max_bottom}, bbox_height={bbox_height}, frame_height={frame_height}")
            
        except Exception as e:
            # エラーが発生してもフォールバック
            try:
                self.update_idletasks()
                bbox = self.canvas.bbox("all")
                if bbox:
                    x1, y1, x2, y2 = bbox
                    self.canvas.configure(scrollregion=(0, 0, x2 + 50, y2 + 150))
            except:
                pass
    
    def _on_canvas_configure(self, event):
        """Canvasのサイズが変わったら、内部フレームの幅も調整"""
        try:
            # スクロールバーの幅を考慮
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_frame, width=canvas_width)
            # サイズ変更時にもスクロール領域を更新
            self.after(10, self._update_scrollregion)
            self.after(100, self._update_scrollregion)
        except:
            pass
    
    def _setup_mousewheel(self):
        """マウスホイールスクロールを設定（改善版）"""
        def _on_mousewheel(event):
            # スクロール可能な範囲があるかチェック
            try:
                yview = self.canvas.yview()
                # わずかでもスクロール可能ならスクロールする
                if yview[1] - yview[0] < 0.999:  # ほぼ全体が見えていても少しでもスクロール可能なら
                    # Windowsとmacの両方に対応
                    if event.delta:
                        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    elif event.num == 4:  # Linux: scroll up
                        self.canvas.yview_scroll(-1, "units")
                    elif event.num == 5:  # Linux: scroll down
                        self.canvas.yview_scroll(1, "units")
            except:
                pass
        
        # Canvas全体にマウスホイールをバインド（常時有効）
        self.canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows/Mac
        self.canvas.bind("<Button-4>", _on_mousewheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", _on_mousewheel)    # Linux scroll down
        
        # scrollable_frameにもバインド
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-5>", _on_mousewheel)
        
        # すべての子ウィジェットにもマウスホイールを伝播
        def _bind_to_children(widget):
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                widget.bind("<Button-4>", _on_mousewheel)
                widget.bind("<Button-5>", _on_mousewheel)
                for child in widget.winfo_children():
                    _bind_to_children(child)
            except:
                pass
        
        # 初期化後に子ウィジェットにバインド（複数回試行）
        self.after(100, lambda: _bind_to_children(self.scrollable_frame))
        self.after(300, lambda: _bind_to_children(self.scrollable_frame))
        self.after(600, lambda: _bind_to_children(self.scrollable_frame))
    
    def force_update(self):
        """外部から強制的にスクロール領域を更新"""
        # 即座に1回
        self._update_scrollregion()
        # 遅延して複数回（確実に更新）
        update_times = [10, 50, 100, 200, 500, 1000, 2000]
        for delay in update_times:
            self.after(delay, self._update_scrollregion)

