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
    TEXT_PRIMARY = "#1e293b"      # 14.63:1 - 最高
    TEXT_SECONDARY = "#475569"    # より濃く（7.4:1 - AAA）
    TEXT_LIGHT = "#64748b"        # より濃く（4.76:1 - AA）
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
    WINDOW_TITLE = "📄 らくらくPDF"
    # 注: 以下のサイズは参考値。実際は画面サイズに応じて自動調整されます
    WINDOW_WIDTH = 900   # フォールバック値
    WINDOW_HEIGHT = 650  # フォールバック値
    MIN_WIDTH = 600      # 絶対最小幅（超小画面対応）
    MIN_HEIGHT = 420     # 絶対最小高さ（超小画面対応）
    FONT_FAMILY = "Yu Gothic UI"
    FONT_SIZE_TITLE = 15        # タイトル：見やすく
    FONT_SIZE_SUBTITLE = 10     # サブタイトル：読みやすく
    FONT_SIZE_NORMAL = 10       # 通常テキスト：日本語UIの標準サイズ
    FONT_SIZE_SMALL = 9         # 小さいテキスト：最小でも9pt
    INVALID_FILENAME_CHARS = '\\/:*?"<>|'
    SUPPORTED_PDF_EXT = [".pdf"]
    PADDING_LARGE = 16          # 少し余裕を持たせる
    PADDING_MEDIUM = 12
    PADDING_SMALL = 8
    THUMBNAIL_HEIGHT = 80
    PREVIEW_MIN_SIZE = 240
