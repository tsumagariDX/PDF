from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from PIL import ImageTk
import pypdfium2 as pdfium


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

        # 左：サムネイル＋スクロール
        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=False)
        left.config(width=250)
        left.pack_propagate(False)

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

        # 右：拡大プレビュー
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(20, 0))

        ttk.Label(right, text="拡大プレビュー").pack(anchor="w")
        self.preview_label = ttk.Label(right)
        self.preview_label.pack(fill="both", expand=True)

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
            frame.pack(pady=3, padx=5, fill="x")

            lbl_img = ttk.Label(frame, image=img)
            lbl_img.pack(side="left", padx=5, pady=5)

            lbl_text = ttk.Label(frame, text=f"ページ {i + 1}")
            lbl_text.pack(side="left", padx=10)

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

        max_w = 650
        max_h = 320

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

        # 左カラム（サムネイル＋スクロールバー）
        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=False)
        left.config(width=250)
        left.pack_propagate(False)

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

        # 右カラム（拡大プレビュー）
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(20, 0))

        ttk.Label(right, text="拡大プレビュー").pack(anchor="w")
        self.preview_label = ttk.Label(right)
        self.preview_label.pack(fill="both", expand=True)

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
            frame.pack(pady=3, padx=5, fill="x")

            lbl_img = ttk.Label(frame, image=img)
            lbl_img.pack(side="left", padx=5, pady=5)

            lbl_text = ttk.Label(frame, text=f"ページ {i + 1}")
            lbl_text.pack(side="left", padx=10)

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

        max_w = 650
        max_h = 320

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
            it["frame"].pack(pady=3, padx=5, fill="x")

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
                if isinstance(child, ttk.Label) and str(child["text"]).startswith("ページ"):
                    child["text"] = f"ページ {i + 1}"
                    break

    def get_page_order(self):
        return [it["page_index"] for it in self.page_items]

    def get_page_rotations(self) -> dict[int, int]:
        return dict(self.page_rotations)
