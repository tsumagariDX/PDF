from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from PIL import ImageTk
import pypdfium2 as pdfium

from src.config import Colors


class PageSelectView(ttk.Frame):
    """
    抽出／削除タブ用：
    PDF のページサムネイルを縦に並べて表示し、
    クリック（Ctrl+クリックで複数）でページ選択できるビュー。
    並び替え・回転はしないが、右側に拡大プレビューを表示する。
    """

    def __init__(self, master, thumb_height=120, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.thumb_height = thumb_height

        self.doc = None
        self.images: list[ImageTk.PhotoImage] = []
        self.page_items = []
        self.selected_indices: set[int] = set()

        self.current_page_index: Optional[int] = None
        self.preview_image = None

        # PanedWindowで左右を分割（リサイズ可能）
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True)

        # 左：サムネイル＋スクロール
        left = ttk.Frame(self.paned)
        self.paned.add(left, weight=0)  # weightを0にして固定的に

        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(left, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(
            left,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.inner = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_configure)

        self.canvas.bind(
            "<Enter>",
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel),
        )
        self.canvas.bind(
            "<Leave>",
            lambda e: self.canvas.unbind_all("<MouseWheel>"),
        )

        # 右：拡大プレビュー（スクロール可能）
        right = ttk.Frame(self.paned)
        self.paned.add(right, weight=1)  # プレビューが残りを使う

        ttk.Label(right, text="拡大プレビュー").pack(anchor="w", padx=5, pady=2)
        
        # プレビュー用のCanvas+Scrollbar
        preview_container = tk.Frame(right)
        preview_container.pack(fill="both", expand=True)
        
        self.preview_canvas = tk.Canvas(preview_container, bg=Colors.BG_MAIN, highlightthickness=0)
        preview_vscroll = ttk.Scrollbar(preview_container, orient="vertical", command=self.preview_canvas.yview)
        preview_hscroll = ttk.Scrollbar(preview_container, orient="horizontal", command=self.preview_canvas.xview)
        
        self.preview_canvas.configure(yscrollcommand=preview_vscroll.set, xscrollcommand=preview_hscroll.set)
        
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        preview_vscroll.grid(row=0, column=1, sticky="ns")
        preview_hscroll.grid(row=1, column=0, sticky="ew")
        
        preview_container.grid_rowconfigure(0, weight=1)
        preview_container.grid_columnconfigure(0, weight=1)
        
        # プレビューラベルをCanvas内に配置
        self.preview_label = ttk.Label(self.preview_canvas, anchor="nw", background=Colors.BG_MAIN)
        self.preview_window = self.preview_canvas.create_window((0, 0), window=self.preview_label, anchor="nw")
        
        # プレビューラベルのサイズ変更時にスクロール領域を更新
        self.preview_label.bind("<Configure>", self._update_preview_scroll_region)
        
        # 初期位置を設定（左側を350pxに）
        self._sash_position_set = False
        self.paned.bind("<Configure>", self._on_paned_configure)
    
    def _on_paned_configure(self, event=None):
        """PanedWindowのサイズ変更時に初期位置を設定"""
        if not self._sash_position_set and self.paned.winfo_width() > 1:
            try:
                self.paned.sashpos(0, 350)
                self._sash_position_set = True
            except Exception:
                pass
    
    def _update_preview_scroll_region(self, event=None):
        """プレビューのスクロール領域を更新"""
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))

    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if hasattr(self, "canvas_window"):
            self.canvas.itemconfigure(self.canvas_window, width=self.canvas.winfo_width())

    def _on_mousewheel(self, event):
        delta = int(-event.delta / 120)
        self.canvas.yview_scroll(delta, "units")

    def clear(self):
        for item in self.page_items:
            item["frame"].destroy()
        self.page_items.clear()
        self.images.clear()
        self.selected_indices.clear()
        self.current_page_index = None

        if self.doc is not None:
            self.doc.close()
            self.doc = None

        self.preview_label.configure(image="")
        self.preview_image = None

    def _render_page_image(self, page_index: int, max_width: int, max_height: int) -> ImageTk.PhotoImage:
        page = self.doc[page_index]
        w_pt, h_pt = page.get_size()

        if w_pt == 0 or h_pt == 0:
            scale = 1.0
        else:
            scale_w = max_width / w_pt
            scale_h = max_height / h_pt
            scale = min(scale_w, scale_h)

        if scale <= 0:
            scale = 0.1
        if scale > 3.0:
            scale = 3.0

        pil_image = page.render(scale=scale).to_pil()
        return ImageTk.PhotoImage(pil_image)

    def load_pdf(self, pdf_path: str):
        self.clear()
        self.doc = pdfium.PdfDocument(pdf_path)
        n_pages = len(self.doc)

        for i in range(n_pages):
            page = self.doc[i]
            w_pt, h_pt = page.get_size()
            scale = self.thumb_height / h_pt if h_pt else 1.0
            if scale <= 0:
                scale = 0.1
            if scale > 3.0:
                scale = 3.0

            pil_image = page.render(scale=scale).to_pil()
            img = ImageTk.PhotoImage(pil_image)
            self.images.append(img)

            frame = tk.Frame(
                self.inner,
                bg="#FFFFFF",
                bd=1,
                relief="solid",
            )
            frame.pack(pady=2, padx=2, anchor="w")  # fill="x"を削除、anchor="w"で左寄せ

            lbl_img = ttk.Label(frame, image=img)
            lbl_img.pack(side="left", padx=2, pady=2)

            lbl_text = ttk.Label(frame, text=f"P.{i + 1}", font=("Yu Gothic UI", 9))
            lbl_text.pack(side="left", padx=2)

            for w in (frame, lbl_img, lbl_text):
                w.configure(cursor="hand2")
                w.bind("<Button-1>", self._on_click)

            self.page_items.append({"frame": frame, "page_index": i, "img_label": lbl_img})

        if self.page_items:
            self.selected_indices = {0}
            self.current_page_index = 0
            self._update_styles()
            self._update_preview()

    def _on_click(self, event):
        idx = self._index_of(event.widget)
        if idx is None:
            return

        ctrl_pressed = (event.state & 0x0004) != 0

        if ctrl_pressed:
            if idx in self.selected_indices:
                self.selected_indices.remove(idx)
            else:
                self.selected_indices.add(idx)
        else:
            self.selected_indices = {idx}

        self.current_page_index = idx
        self._update_styles()
        self._update_preview()

    def _index_of(self, widget):
        w = widget
        while w is not None:
            for i, it in enumerate(self.page_items):
                if it["frame"] == w:
                    return i
            w = getattr(w, "master", None)
        return None

    def _update_styles(self):
        for i, it in enumerate(self.page_items):
            frame = it["frame"]
            if i in self.selected_indices:
                frame.configure(bg="#FFF3CD", bd=3)
            else:
                frame.configure(bg="#FFFFFF", bd=1)

    def _update_preview(self):
        if self.current_page_index is None or self.doc is None:
            return

        max_w = 800  # 元のサイズに戻す
        max_h = 500  # 元のサイズに戻す

        img = self._render_page_image(self.current_page_index, max_w, max_h)
        self.preview_image = img
        self.preview_label.configure(image=img)

    def get_selected_indices(self) -> list[int]:
        return sorted(self.selected_indices)


class PageThumbnailView(ttk.Frame):
    """
    1つのPDFのページサムネイルを表示して、
    上下DnDで並び替えできるビュー
    ＋ 複数ページ選択＆ページごとの回転状態を保持
    """

    def __init__(self, master, thumb_height=120, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.thumb_height = thumb_height

        self.images: list[ImageTk.PhotoImage] = []
        self.page_items = []
        self.dragging = None
        self.doc = None
        self.preview_image = None

        self.page_rotations: dict[int, int] = {}
        self.selected_pages: set[int] = set()
        self.current_page_index: Optional[int] = None

        self.insert_line_id: Optional[int] = None

        self.normal_bg = "#FFFFFF"
        self.selected_bg = "#FFF3CD"
        self.normal_bd = 1
        self.selected_bd = 4
        self.drag_ghost = None
        self.drag_ghost_img = None

        # PanedWindowで左右を分割（リサイズ可能）
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True)

        # 左カラム（サムネイル＋スクロールバー）
        left = ttk.Frame(self.paned)
        self.paned.add(left, weight=0)  # weightを0にして固定的に

        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(left, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(
            left,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.inner = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_configure)

        self.canvas.bind(
            "<Enter>",
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel),
        )
        self.canvas.bind(
            "<Leave>",
            lambda e: self.canvas.unbind_all("<MouseWheel>"),
        )

        # 右カラム（拡大プレビュー・スクロール可能）
        right = ttk.Frame(self.paned)
        self.paned.add(right, weight=1)  # プレビューが残りを使う

        ttk.Label(right, text="拡大プレビュー").pack(anchor="w", padx=5, pady=2)
        
        # プレビュー用のCanvas+Scrollbar
        preview_container = tk.Frame(right)
        preview_container.pack(fill="both", expand=True)
        
        self.preview_canvas = tk.Canvas(preview_container, bg=Colors.BG_MAIN, highlightthickness=0)
        preview_vscroll = ttk.Scrollbar(preview_container, orient="vertical", command=self.preview_canvas.yview)
        preview_hscroll = ttk.Scrollbar(preview_container, orient="horizontal", command=self.preview_canvas.xview)
        
        self.preview_canvas.configure(yscrollcommand=preview_vscroll.set, xscrollcommand=preview_hscroll.set)
        
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        preview_vscroll.grid(row=0, column=1, sticky="ns")
        preview_hscroll.grid(row=1, column=0, sticky="ew")
        
        preview_container.grid_rowconfigure(0, weight=1)
        preview_container.grid_columnconfigure(0, weight=1)
        
        # プレビューラベルをCanvas内に配置
        self.preview_label = ttk.Label(self.preview_canvas, anchor="nw", background=Colors.BG_MAIN)
        self.preview_window = self.preview_canvas.create_window((0, 0), window=self.preview_label, anchor="nw")
        
        # プレビューラベルのサイズ変更時にスクロール領域を更新
        self.preview_label.bind("<Configure>", self._update_preview_scroll_region_thumbnail)
        
        # 初期位置を設定（左側を350pxに）
        self._sash_position_set = False
        self.paned.bind("<Configure>", self._on_paned_configure_thumbnail)
    
    def _on_paned_configure_thumbnail(self, event=None):
        """PanedWindowのサイズ変更時に初期位置を設定"""
        if not self._sash_position_set and self.paned.winfo_width() > 1:
            try:
                self.paned.sashpos(0, 350)
                self._sash_position_set = True
            except Exception:
                pass
    
    def _update_preview_scroll_region_thumbnail(self, event=None):
        """プレビューのスクロール領域を更新"""
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))

    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if hasattr(self, "canvas_window"):
            self.canvas.itemconfigure(self.canvas_window, width=self.canvas.winfo_width())

    def _on_mousewheel(self, event):
        delta = int(-event.delta / 120)
        self.canvas.yview_scroll(delta, "units")

    def _render_page_image(self, page_index: int, max_width: int, max_height: int) -> ImageTk.PhotoImage:
        page = self.doc[page_index]
        w_pt, h_pt = page.get_size()

        angle = self.page_rotations.get(page_index, 0) % 360
        if angle in (90, 270):
            page_w, page_h = h_pt, w_pt
        else:
            page_w, page_h = w_pt, h_pt

        if page_w == 0 or page_h == 0:
            scale = 1.0
        else:
            scale_w = max_width / page_w
            scale_h = max_height / page_h
            scale = min(scale_w, scale_h)

        if scale > 3.0:
            scale = 3.0
        if scale <= 0:
            scale = 0.1

        pil_image = page.render(scale=scale, rotation=angle).to_pil()
        return ImageTk.PhotoImage(pil_image)

    def load_pdf(self, pdf_path: str):
        self.clear()

        self.doc = pdfium.PdfDocument(pdf_path)
        n_pages = len(self.doc)

        self.page_rotations = {i: 0 for i in range(n_pages)}
        self.images = []
        self.page_items = []
        self.selected_pages = set()
        self.current_page_index = None

        thumb_max_width = 220

        for i in range(n_pages):
            img = self._render_page_image(i, max_width=thumb_max_width, max_height=self.thumb_height)
            self.images.append(img)

            frame = tk.Frame(
                self.inner,
                bg=self.normal_bg,
                bd=self.normal_bd,
                relief="solid",
            )
            frame.pack(pady=2, padx=2, anchor="w")  # fill="x"を削除、anchor="w"で左寄せ

            lbl_img = ttk.Label(frame, image=img)
            lbl_img.pack(side="left", padx=2, pady=2)

            lbl_text = ttk.Label(frame, text=f"P.{i + 1}", font=("Yu Gothic UI", 9))
            lbl_text.pack(side="left", padx=2)

            for w in (frame, lbl_img, lbl_text):
                w.configure(cursor="hand2")
                w.bind("<Button-1>", self._on_press)
                w.bind("<B1-Motion>", self._on_motion)
                w.bind("<ButtonRelease-1>", self._on_release)

            self.page_items.append({"frame": frame, "page_index": i, "img_label": lbl_img})

        if self.page_items:
            self._set_selected_page(0)
            self._update_preview()

    def clear(self):
        for item in self.page_items:
            item["frame"].destroy()
        self.page_items.clear()
        self.images.clear()
        self.dragging = None
        self.page_rotations.clear()
        self.selected_pages.clear()
        self.current_page_index = None

        self._hide_insert_indicator()

        if self.doc is not None:
            self.doc.close()
            self.doc = None

        self.preview_label.configure(image="")
        self.preview_image = None

    def _set_selected_page(self, page_index: int):
        self.selected_pages = {page_index}
        self.current_page_index = page_index
        self._update_selection_styles()

    def _update_selection_styles(self):
        for item in self.page_items:
            frame = item["frame"]
            if item["page_index"] in self.selected_pages:
                frame.configure(bg=self.selected_bg, bd=self.selected_bd)
            else:
                frame.configure(bg=self.normal_bg, bd=self.normal_bd)

    def _update_preview(self):
        if self.current_page_index is None or self.doc is None:
            return

        page_index = self.current_page_index

        max_w = 800  # 元のサイズに戻す
        max_h = 500  # 元のサイズに戻す

        img = self._render_page_image(page_index, max_width=max_w, max_height=max_h)
        self.preview_image = img
        self.preview_label.configure(image=img)

    def rotate_selected(self, delta_angle: int):
        if not self.selected_pages or self.doc is None:
            return

        thumb_max_width = 220

        for item in self.page_items:
            page_index = item["page_index"]
            if page_index not in self.selected_pages:
                continue

            current = self.page_rotations.get(page_index, 0)
            new_angle = (current + delta_angle) % 360
            self.page_rotations[page_index] = new_angle

            thumb_img = self._render_page_image(
                page_index,
                max_width=thumb_max_width,
                max_height=self.thumb_height,
            )
            self.images[page_index] = thumb_img

            lbl = item["img_label"]
            lbl.configure(image=thumb_img)
            lbl.image = thumb_img

        self._update_preview()

    def _hide_insert_indicator(self):
        if self.insert_line_id is not None:
            try:
                self.canvas.delete(self.insert_line_id)
            except Exception:
                pass
            self.insert_line_id = None

    def _show_insert_indicator_index(self, index: int):
        if not self.page_items:
            self._hide_insert_indicator()
            return

        if index <= 0:
            f = self.page_items[0]["frame"]
            y_root = f.winfo_rooty() - 2
        elif index >= len(self.page_items):
            f = self.page_items[-1]["frame"]
            y_root = f.winfo_rooty() + f.winfo_height() + 2
        else:
            f = self.page_items[index]["frame"]
            y_root = f.winfo_rooty() - 2

        canvas_y = self.canvas.canvasy(y_root - self.canvas.winfo_rooty())

        w = max(self.canvas.winfo_width(), 1)
        if self.insert_line_id is not None:
            try:
                self.canvas.delete(self.insert_line_id)
            except Exception:
                pass

        self.insert_line_id = self.canvas.create_line(
            0,
            canvas_y,
            w,
            canvas_y,
            width=3,
            fill="#0078D4",
        )

    def _on_press(self, event):
        idx = self._index_of(event.widget)
        if idx is None:
            return

        page_index = self.page_items[idx]["page_index"]
        ctrl_pressed = (event.state & 0x0004) != 0

        if ctrl_pressed:
            if page_index in self.selected_pages:
                self.selected_pages.remove(page_index)
                if self.current_page_index == page_index:
                    self.current_page_index = next(iter(self.selected_pages), None)
            else:
                self.selected_pages.add(page_index)
                self.current_page_index = page_index

            self._update_selection_styles()
            self._update_preview()
            return

        if page_index in self.selected_pages and self.selected_pages:
            self.current_page_index = page_index
        else:
            self._set_selected_page(page_index)

        self._update_selection_styles()
        self._update_preview()

        frame = self.page_items[idx]["frame"]
        self.dragging = (frame, idx)

        img = self.images[page_index]
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        lbl = tk.Label(ghost, image=img, bd=2, relief="solid")
        lbl.image = img
        lbl.pack()
        ghost.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        self.drag_ghost = ghost
        self.drag_ghost_img = img

    def _on_motion(self, event):
        if not self.dragging:
            return

        if self.drag_ghost is not None:
            self.drag_ghost.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        target_idx = self.nearest_index(event.y_root)
        if target_idx is None:
            self._hide_insert_indicator()
            return

        old_items = self.page_items
        sel_indices = [i for i, it in enumerate(old_items) if it["page_index"] in self.selected_pages]
        sel_indices.sort()

        insert_pos = 0

        if not sel_indices:
            widget, start_idx = self.dragging
            insert_pos = target_idx

            if target_idx == start_idx:
                self._show_insert_indicator_index(insert_pos)
                return

            item = self.page_items.pop(start_idx)
            if insert_pos > len(self.page_items):
                insert_pos = len(self.page_items)
            self.page_items.insert(insert_pos, item)

        else:
            if sel_indices[0] <= target_idx <= sel_indices[-1]:
                insert_pos = sel_indices[0]
                self._show_insert_indicator_index(insert_pos)
                return

            block_items = [old_items[i] for i in sel_indices]
            others = [item for i, item in enumerate(old_items) if i not in sel_indices]

            before_count = 0
            for j in range(len(old_items)):
                if j >= target_idx:
                    break
                if j not in sel_indices:
                    before_count += 1

            new_items = others[:before_count] + block_items + others[before_count:]
            self.page_items = new_items

            block_positions = [
                i for i, it in enumerate(self.page_items)
                if it["page_index"] in self.selected_pages
            ]
            insert_pos = block_positions[0] if block_positions else 0

        for it in self.page_items:
            it["frame"].pack_forget()
        for it in self.page_items:
            it["frame"].pack(pady=2, padx=2, anchor="w")  # fill="x"を削除、anchor="w"で左詰め

        self._refresh_labels()
        self._update_selection_styles()
        self._update_preview()

        self._show_insert_indicator_index(insert_pos)

    def _on_release(self, event):
        self.dragging = None
        if self.drag_ghost is not None:
            self.drag_ghost.destroy()
            self.drag_ghost = None
            self.drag_ghost_img = None

        self._hide_insert_indicator()

    def _index_of(self, widget):
        w = widget
        while w is not None:
            for i, it in enumerate(self.page_items):
                if it["frame"] == w:
                    return i
            w = getattr(w, "master", None)
        return None

    def nearest_index(self, screen_y):
        dists = []
        for i, it in enumerate(self.page_items):
            f = it["frame"]
            y = f.winfo_rooty()
            h = f.winfo_height()
            center_y = y + h / 2
            dists.append((abs(center_y - screen_y), i))
        if not dists:
            return None
        dists.sort()
        return dists[0][1]

    def _refresh_labels(self):
        for i, it in enumerate(self.page_items):
            for child in it["frame"].winfo_children():
                if isinstance(child, ttk.Label) and (str(child["text"]).startswith("ページ") or str(child["text"]).startswith("P.")):
                    child["text"] = f"P.{i + 1}"
                    break

    def get_page_order(self):
        return [it["page_index"] for it in self.page_items]

    def get_page_rotations(self) -> dict[int, int]:
        return dict(self.page_rotations)
    
    def move_selected_up(self):
        """選択中のページを1つ上に移動"""
        if not self.selected_pages or len(self.selected_pages) == 0:
            return
        
        # 選択中のページのインデックスを取得（表示順）
        selected_indices = []
        for i, item in enumerate(self.page_items):
            if item["page_index"] in self.selected_pages:
                selected_indices.append(i)
        
        # 一番上が選択されている場合は移動不可
        if 0 in selected_indices:
            return
        
        selected_indices.sort()
        
        # 上から順に移動
        for idx in selected_indices:
            self.page_items[idx], self.page_items[idx - 1] = self.page_items[idx - 1], self.page_items[idx]
        
        self._rebuild_display()
        self._refresh_labels()
        self._scroll_to_selected()  # 選択中のページまでスクロール
    
    def move_selected_down(self):
        """選択中のページを1つ下に移動"""
        if not self.selected_pages or len(self.selected_pages) == 0:
            return
        
        # 選択中のページのインデックスを取得（表示順）
        selected_indices = []
        for i, item in enumerate(self.page_items):
            if item["page_index"] in self.selected_pages:
                selected_indices.append(i)
        
        # 一番下が選択されている場合は移動不可
        if len(self.page_items) - 1 in selected_indices:
            return
        
        selected_indices.sort(reverse=True)
        
        # 下から順に移動
        for idx in selected_indices:
            self.page_items[idx], self.page_items[idx + 1] = self.page_items[idx + 1], self.page_items[idx]
        
        self._rebuild_display()
        self._refresh_labels()
        self._scroll_to_selected()  # 選択中のページまでスクロール
    
    def move_selected_to_top(self):
        """選択中のページを先頭に移動"""
        if not self.selected_pages or len(self.selected_pages) == 0:
            return
        
        # 選択中のページを抽出
        selected_items = []
        other_items = []
        
        for item in self.page_items:
            if item["page_index"] in self.selected_pages:
                selected_items.append(item)
            else:
                other_items.append(item)
        
        # 選択されたページを先頭に配置
        self.page_items = selected_items + other_items
        
        self._rebuild_display()
        self._refresh_labels()
        self._scroll_to_selected()  # 選択中のページまでスクロール
    
    def move_selected_to_bottom(self):
        """選択中のページを末尾に移動"""
        if not self.selected_pages or len(self.selected_pages) == 0:
            return
        
        # 選択中のページを抽出
        selected_items = []
        other_items = []
        
        for item in self.page_items:
            if item["page_index"] in self.selected_pages:
                selected_items.append(item)
            else:
                other_items.append(item)
        
        # 選択されたページを末尾に配置
        self.page_items = other_items + selected_items
        
        self._rebuild_display()
        self._refresh_labels()
        self._scroll_to_selected()  # 選択中のページまでスクロール
    
    def _rebuild_display(self):
        """ページアイテムの表示順を再構築"""
        # 全てのフレームをいったん削除
        for item in self.page_items:
            item["frame"].pack_forget()
        
        # 新しい順序で再配置
        for item in self.page_items:
            item["frame"].pack(pady=2, padx=2, anchor="w")
    
    def _scroll_to_selected(self):
        """選択中のページが見える位置までスクロール"""
        if not self.selected_pages:
            return
        
        # 選択中のページのフレームを探す
        selected_frame = None
        for item in self.page_items:
            if item["page_index"] in self.selected_pages:
                selected_frame = item["frame"]
                break
        
        if selected_frame is None:
            return
        
        # フレームが表示されるまで少し待つ
        self.after(10, lambda: self._do_scroll(selected_frame))
    
    def _do_scroll(self, frame):
        """実際にスクロールを実行"""
        try:
            # フレームの位置を取得
            frame.update_idletasks()
            
            # Canvasの表示領域を取得
            canvas_height = self.canvas.winfo_height()
            
            # フレームのY座標を取得（Canvas内での相対座標）
            frame_y = frame.winfo_y()
            frame_height = frame.winfo_height()
            
            # 全体の高さを取得
            bbox = self.canvas.bbox("all")
            if bbox:
                total_height = bbox[3] - bbox[1]
            else:
                return
            
            # 現在のスクロール位置を取得
            current_top = self.canvas.yview()[0] * total_height
            current_bottom = self.canvas.yview()[1] * total_height
            
            # フレームが見える位置にあるかチェック
            if frame_y < current_top:
                # フレームが上に隠れている場合
                scroll_to = frame_y / total_height
                self.canvas.yview_moveto(scroll_to)
            elif frame_y + frame_height > current_bottom:
                # フレームが下に隠れている場合
                scroll_to = (frame_y + frame_height - canvas_height) / total_height
                self.canvas.yview_moveto(max(0, scroll_to))
        except Exception:
            pass
