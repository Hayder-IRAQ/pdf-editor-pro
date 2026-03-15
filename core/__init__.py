"""Core module for PDF Editor Pro v3.0 - Modern Edition"""

from core.pdf_engine import PDFEngine, ImageInfo
from core.languages import LANGUAGES, get_text, get_available_languages
from core.tools import Tool, DEFAULT_COLORS, FONT_SIZES, LINE_WIDTHS, ZOOM_LEVELS
from core.undo_manager import (
    UndoManager, ImageResizeCommand, ImageMoveCommand,
    ImageDeleteCommand, ImageInsertCommand
)
from core.cache_system import PageCache, AutoSaveManager
from core.layer_system import LayerManager, ShapeLayer, AnnotationLayer, TextLayer, ShapeType
from core.text_editor import TextAnalyzer, TextEditor, TextBlock, TextSpan
from core.fonts import FontManager, get_fonts_for_language, detect_script, get_font_for_text

__all__ = [
    'PDFEngine', 'ImageInfo',
    'LANGUAGES', 'get_text', 'get_available_languages',
    'Tool', 'DEFAULT_COLORS', 'FONT_SIZES', 'LINE_WIDTHS', 'ZOOM_LEVELS',
    'UndoManager', 'PageCache', 'AutoSaveManager',
    'ImageResizeCommand', 'ImageMoveCommand', 'ImageDeleteCommand', 'ImageInsertCommand',
    'LayerManager', 'ShapeLayer', 'AnnotationLayer', 'TextLayer', 'ShapeType',
    'TextAnalyzer', 'TextEditor', 'TextBlock', 'TextSpan',
    'FontManager', 'get_fonts_for_language', 'detect_script', 'get_font_for_text'
]