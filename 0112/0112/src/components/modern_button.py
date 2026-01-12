"""Modern Button"""
import tkinter as tk
from src.config import Colors

class ModernButton(tk.Button):
    STYLES = {
        "primary": (Colors.PRIMARY, Colors.PRIMARY_DARK, "white"),
        "success": (Colors.SUCCESS, "#059669", "white"),
        "danger": (Colors.DANGER, "#dc2626", "white"),
        "secondary": (Colors.BG_ACCENT, Colors.BORDER_HOVER, Colors.TEXT_PRIMARY),
    }
    
    def __init__(self, master, text="", command=None, style="primary", **kwargs):
        bg, hover_bg, fg = self.STYLES.get(style, self.STYLES["primary"])
        super().__init__(master, text=text, command=command, bg=bg, fg=fg,
                        font=("Yu Gothic UI", 10, "bold"), relief="flat", padx=20, pady=10,
                        cursor="hand2", activebackground=hover_bg, activeforeground=fg,
                        borderwidth=0, **kwargs)
        self._default_bg = bg
        self._hover_bg = hover_bg
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, e):
        if self["state"] != "disabled":
            self.configure(bg=self._hover_bg)
    
    def _on_leave(self, e):
        if self["state"] != "disabled":
            self.configure(bg=self._default_bg)
