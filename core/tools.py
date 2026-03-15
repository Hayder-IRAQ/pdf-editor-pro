"""
Tools, constants and data structures for PDF Editor Pro v3.0
"""

from enum import Enum


class Tool(Enum):
    """Available editing tools"""
    SELECT = "select"
    TEXT = "text"
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    LINE = "line"
    ARROW = "arrow"
    FREEHAND = "freehand"
    IMAGE = "image"
    ERASER = "eraser"
    COMMENT = "comment"
    LINK = "link"
    IMAGE_SELECT = "image_select"
    IMAGE_MOVE = "image_move"


# Default colors
DEFAULT_COLORS = {
    "text": (0, 0, 0),
    "highlight": (1, 1, 0),
    "shape": (1, 0, 0),
    "link": (0, 0, 1),
    "comment": (1, 0.8, 0),
}

# Font sizes
FONT_SIZES = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48", "72"]

# Line widths
LINE_WIDTHS = [1, 2, 3, 4, 5, 6, 8, 10]

# Zoom levels
ZOOM_LEVELS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0]

# Page sizes (in points, 72 points = 1 inch)
PAGE_SIZES = {
    "A4": (595, 842),
    "A3": (842, 1191),
    "A5": (420, 595),
    "Letter": (612, 792),
    "Legal": (612, 1008),
    "Tabloid": (792, 1224),
}

# Tooltip texts for tools (multilingual)
TOOL_TOOLTIPS = {
    "en": {
        Tool.SELECT: "Select and move elements",
        Tool.TEXT: "Add or edit text",
        Tool.HIGHLIGHT: "Highlight text",
        Tool.UNDERLINE: "Underline text",
        Tool.STRIKEOUT: "Strikeout text",
        Tool.RECTANGLE: "Draw rectangle",
        Tool.CIRCLE: "Draw circle/oval",
        Tool.LINE: "Draw line",
        Tool.ARROW: "Draw arrow",
        Tool.FREEHAND: "Freehand drawing",
        Tool.IMAGE_SELECT: "Select image",
        Tool.IMAGE_MOVE: "Move image",
    },
    "ar": {
        Tool.SELECT: "تحديد ونقل العناصر",
        Tool.TEXT: "إضافة أو تحرير النص",
        Tool.HIGHLIGHT: "تظليل النص",
        Tool.UNDERLINE: "وضع خط تحت النص",
        Tool.STRIKEOUT: "شطب النص",
        Tool.RECTANGLE: "رسم مستطيل",
        Tool.CIRCLE: "رسم دائرة/بيضاوي",
        Tool.LINE: "رسم خط",
        Tool.ARROW: "رسم سهم",
        Tool.FREEHAND: "رسم حر",
        Tool.IMAGE_SELECT: "تحديد صورة",
        Tool.IMAGE_MOVE: "نقل صورة",
    },
    "ru": {
        Tool.SELECT: "Выбор и перемещение",
        Tool.TEXT: "Добавить или редактировать текст",
        Tool.HIGHLIGHT: "Выделить текст",
        Tool.UNDERLINE: "Подчеркнуть текст",
        Tool.STRIKEOUT: "Зачеркнуть текст",
        Tool.RECTANGLE: "Нарисовать прямоугольник",
        Tool.CIRCLE: "Нарисовать круг/овал",
        Tool.LINE: "Нарисовать линию",
        Tool.ARROW: "Нарисовать стрелку",
        Tool.FREEHAND: "Свободное рисование",
        Tool.IMAGE_SELECT: "Выбрать изображение",
        Tool.IMAGE_MOVE: "Переместить изображение",
    },
}