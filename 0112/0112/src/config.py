"""Application Configuration - IMPROVED VERSION"""

class Colors:
    PRIMARY = "#2563eb"
    PRIMARY_DARK = "#1e40af"
    PRIMARY_LIGHT = "#60a5fa"
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    DANGER = "#ef4444"
    INFO = "#06b6d4"
    BG_MAIN = "#ffffff"
    BG_SECONDARY = "#f8fafc"
    BG_ACCENT = "#f1f5f9"
    TEXT_PRIMARY = "#1e293b"
    TEXT_SECONDARY = "#64748b"
    TEXT_LIGHT = "#94a3b8"
    BORDER = "#e2e8f0"
    BORDER_HOVER = "#cbd5e1"
    DND_HOVER = "#dbeafe"
    DND_ACTIVE = "#bfdbfe"
    
    # Improved tab colors
    TAB_SELECTED_BG = "#2563eb"
    TAB_SELECTED_FG = "#000000"
    TAB_NORMAL_BG = "#e2e8f0"
    TAB_NORMAL_FG = "#64748b"

class Config:
    WINDOW_TITLE = "📄 Modern PDF Utility"
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 950
    MIN_WIDTH = 1200
    MIN_HEIGHT = 850
    FONT_FAMILY = "Yu Gothic UI"
    FONT_SIZE_TITLE = 18
    FONT_SIZE_SUBTITLE = 10
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_SMALL = 9
    INVALID_FILENAME_CHARS = '\\/:*?"<>|'
    SUPPORTED_PDF_EXT = [".pdf"]
    PADDING_LARGE = 20
    PADDING_MEDIUM = 15
    PADDING_SMALL = 10
    THUMBNAIL_HEIGHT = 100
    PREVIEW_MIN_SIZE = 300
