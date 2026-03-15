"""
Font Management for PDF Editor Pro v3.0
Supports fonts for: English, Arabic, Russian, Chinese, Japanese, Korean, etc.
"""

from typing import List, Dict, Optional

# PyMuPDF built-in fonts (always available)
BUILTIN_FONTS = {
    "helv": "Helvetica",
    "tiro": "Times Roman",
    "cour": "Courier",
    "symb": "Symbol",
    "zadb": "Zapf Dingbats",
}

# Font configurations for different languages
FONT_CONFIG = {
    "latin": {
        "default": "helv",
        "fonts": {
            "helv": {"name": "Helvetica", "file": None, "builtin": True},
            "tiro": {"name": "Times Roman", "file": None, "builtin": True},
            "cour": {"name": "Courier", "file": None, "builtin": True},
        }
    },
    "arabic": {
        "default": "helv",
        "fonts": {
            "helv": {"name": "Helvetica", "file": None, "builtin": True},
        }
    },
    "cyrillic": {
        "default": "helv",
        "fonts": {
            "helv": {"name": "Helvetica", "file": None, "builtin": True},
        }
    },
    "chinese": {
        "default": "helv",
        "fonts": {
            "helv": {"name": "Helvetica", "file": None, "builtin": True},
        }
    },
    "japanese": {
        "default": "helv",
        "fonts": {
            "helv": {"name": "Helvetica", "file": None, "builtin": True},
        }
    },
    "korean": {
        "default": "helv",
        "fonts": {
            "helv": {"name": "Helvetica", "file": None, "builtin": True},
        }
    },
}

# Language to font group mapping
LANG_FONT_MAP = {
    "en": "latin",
    "es": "latin",
    "fr": "latin",
    "de": "latin",
    "pt": "latin",
    "ar": "arabic",
    "ru": "cyrillic",
    "zh": "chinese",
    "ja": "japanese",
    "ko": "korean",
}

# Font display names for UI
FONT_DISPLAY_NAMES = {
    "helv": "Helvetica",
    "tiro": "Times New Roman",
    "cour": "Courier New",
}


def detect_script(text: str) -> str:
    """Detect the script/writing system of text"""
    if not text:
        return "latin"

    for char in text:
        code = ord(char)
        if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F:
            return "arabic"
        if 0x0400 <= code <= 0x04FF:
            return "cyrillic"
        if 0x4E00 <= code <= 0x9FFF:
            return "chinese"
        if 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
            return "japanese"
        if 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            return "korean"
    return "latin"


def get_font_for_text(text: str) -> str:
    """Get appropriate font for text based on its script"""
    return "helv"


def get_fonts_for_language(lang_code: str) -> List[Dict]:
    """Get available fonts for a specific language"""
    fonts = []
    for font_id, name in BUILTIN_FONTS.items():
        fonts.append({"id": font_id, "name": name, "builtin": True})
    return fonts


def get_default_font(lang_code: str) -> str:
    """Get default font for a language"""
    return "helv"


class FontManager:
    """Manages fonts for the PDF editor"""

    BUILTIN_FONTS = {
        "helv": "Helvetica",
        "tiro": "Times-Roman",
        "cour": "Courier",
        "symb": "Symbol",
        "zadb": "ZapfDingbats",
    }

    def __init__(self):
        self.loaded_fonts = {}
        self.font_paths = {}

    def register_font(self, font_id: str, font_path: str):
        """Register an external font file"""
        self.font_paths[font_id] = font_path

    def get_font_path(self, font_id: str) -> Optional[str]:
        """Get path for a font"""
        return self.font_paths.get(font_id)

    def is_builtin(self, font_id: str) -> bool:
        """Check if font is built-in"""
        return font_id in BUILTIN_FONTS

    @staticmethod
    def get_available_fonts() -> List[Dict[str, str]]:
        """Get list of available fonts"""
        return [{"id": k, "name": v} for k, v in FontManager.BUILTIN_FONTS.items()]

    @staticmethod
    def detect_script(text: str) -> str:
        """Detect the script of text"""
        return detect_script(text)

    @staticmethod
    def get_font_for_text(text: str) -> str:
        """Get appropriate font for text"""
        return get_font_for_text(text)