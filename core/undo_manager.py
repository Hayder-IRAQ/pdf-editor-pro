"""
Command-based Undo/Redo System v3.0
FIXED: Annotations quads error, Text editing issues
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Any, Optional, Dict, Tuple
from enum import Enum
import fitz
import time


class CommandType(Enum):
    TEXT_EDIT = "text_edit"
    TEXT_ADD = "text_add"
    TEXT_DELETE = "text_delete"
    IMAGE_INSERT = "image_insert"
    IMAGE_DELETE = "image_delete"
    IMAGE_MOVE = "image_move"
    ANNOTATION_ADD = "annotation_add"
    SHAPE_ADD = "shape_add"
    PAGE_ROTATE = "page_rotate"


class Command(ABC):
    def __init__(self, page_num: int):
        self.page_num = page_num
        self.timestamp = time.time()

    @abstractmethod
    def execute(self, doc: fitz.Document) -> bool:
        pass

    @abstractmethod
    def undo(self, doc: fitz.Document) -> bool:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass


@dataclass
class TextEditCommand(Command):
    """Command for editing text - with FULL multilingual support including RTL"""
    page_num: int
    rect: fitz.Rect
    old_text: str
    new_text: str
    old_font_size: float
    new_font_size: float
    old_color: Tuple[float, float, float]
    new_color: Tuple[float, float, float]
    font_name: str = "helv"

    def __post_init__(self):
        self.timestamp = time.time()

    def _has_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        for c in text:
            code = ord(c)
            if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F or 0xFB50 <= code <= 0xFDFF:
                return True
        return False

    def _needs_unicode_font(self, text: str) -> bool:
        """Check if text contains non-ASCII characters"""
        for c in text:
            code = ord(c)
            if code > 127:
                return True
        return False

    def _process_arabic(self, text: str) -> str:
        """Process Arabic text for correct display in PDF"""
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display

            # Reshape to connect Arabic letters
            reshaped = arabic_reshaper.reshape(text)
            # Apply bidi algorithm for correct RTL display
            return get_display(reshaped)
        except ImportError:
            # If libraries not available, return as-is
            return text
        except Exception:
            return text

    def _prepare_text(self, text: str) -> str:
        """Prepare text for PDF insertion"""
        if self._has_arabic(text):
            return self._process_arabic(text)
        return text

    def _insert_text_unicode(self, page, x: float, y: float, text: str,
                             fontsize: float, color: Tuple[float, float, float]) -> bool:
        """Insert text with Unicode support using TextWriter"""
        try:
            font = fitz.Font("cjk")

            # Process Arabic text if needed
            display_text = self._prepare_text(text)

            tw = fitz.TextWriter(page.rect)
            tw.append((x, y), display_text, fontsize=fontsize, font=font)
            tw.write_text(page, color=color)
            return True
        except Exception as e:
            print(f"Unicode text insert error: {e}")
            return False

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]

            expanded_rect = fitz.Rect(
                self.rect.x0 - 2, self.rect.y0 - 2,
                self.rect.x1 + 2, self.rect.y1 + 2
            )

            page.add_redact_annot(expanded_rect, fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            if self.new_text.strip():
                lines = self.new_text.split('\n')
                y = self.rect.y0 + self.new_font_size

                for line in lines:
                    if line.strip():
                        if self._needs_unicode_font(line):
                            self._insert_text_unicode(page, self.rect.x0, y, line,
                                                     self.new_font_size, self.new_color)
                        else:
                            try:
                                page.insert_text(
                                    fitz.Point(self.rect.x0, y),
                                    line,
                                    fontsize=self.new_font_size,
                                    fontname="helv",
                                    color=self.new_color
                                )
                            except:
                                self._insert_text_unicode(page, self.rect.x0, y, line,
                                                         self.new_font_size, self.new_color)
                    y += self.new_font_size * 1.3
            return True
        except Exception as e:
            print(f"TextEditCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]

            expanded_rect = fitz.Rect(
                self.rect.x0 - 2, self.rect.y0 - 2,
                self.rect.x1 + 2, self.rect.y1 + 2
            )
            page.add_redact_annot(expanded_rect, fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            if self.old_text.strip():
                lines = self.old_text.split('\n')
                y = self.rect.y0 + self.old_font_size

                for line in lines:
                    if line.strip():
                        if self._needs_unicode_font(line):
                            self._insert_text_unicode(page, self.rect.x0, y, line,
                                                     self.old_font_size, self.old_color)
                        else:
                            try:
                                page.insert_text(
                                    fitz.Point(self.rect.x0, y),
                                    line,
                                    fontsize=self.old_font_size,
                                    fontname="helv",
                                    color=self.old_color
                                )
                            except:
                                self._insert_text_unicode(page, self.rect.x0, y, line,
                                                         self.old_font_size, self.old_color)
                    y += self.old_font_size * 1.3
            return True
        except Exception as e:
            print(f"TextEditCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Edit text on page {self.page_num + 1}"


@dataclass
class TextAddCommand(Command):
    """Command for adding new text"""
    page_num: int
    x: float
    y: float
    text: str
    font_size: float
    color: Tuple[float, float, float]
    font_name: str = "helv"
    _rect: fitz.Rect = None

    def __post_init__(self):
        self.timestamp = time.time()

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            fontname = self.font_name if self.font_name in ["helv", "tiro", "cour"] else "helv"

            try:
                page.insert_text(
                    fitz.Point(self.x, self.y),
                    self.text,
                    fontsize=self.font_size,
                    fontname=fontname,
                    color=self.color
                )
            except Exception:
                page.insert_text(
                    fitz.Point(self.x, self.y),
                    self.text,
                    fontsize=self.font_size,
                    color=self.color
                )

            text_width = len(self.text) * self.font_size * 0.5
            self._rect = fitz.Rect(
                self.x - 2,
                self.y - self.font_size - 2,
                self.x + text_width + 2,
                self.y + 4
            )
            return True
        except Exception as e:
            print(f"TextAddCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            if self._rect:
                page = doc[self.page_num]
                page.add_redact_annot(self._rect, fill=(1, 1, 1))
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            return True
        except Exception as e:
            print(f"TextAddCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Add text on page {self.page_num + 1}"


@dataclass
class ImageInsertCommand(Command):
    page_num: int
    rect: fitz.Rect
    image_data: bytes
    _xref: int = None

    def __post_init__(self):
        self.timestamp = time.time()

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            page.insert_image(self.rect, stream=self.image_data)
            return True
        except Exception as e:
            print(f"ImageInsertCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            page.add_redact_annot(self.rect, fill=(1, 1, 1))
            page.apply_redactions()
            return True
        except Exception as e:
            print(f"ImageInsertCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Insert image on page {self.page_num + 1}"


@dataclass
class ImageDeleteCommand(Command):
    page_num: int
    rect: fitz.Rect
    image_data: bytes
    xref: int

    def __post_init__(self):
        self.timestamp = time.time()

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            page.add_redact_annot(self.rect, fill=(1, 1, 1))
            page.apply_redactions()
            return True
        except Exception as e:
            print(f"ImageDeleteCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            page.insert_image(self.rect, stream=self.image_data)
            return True
        except Exception as e:
            print(f"ImageDeleteCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Delete image on page {self.page_num + 1}"


@dataclass
class ImageMoveCommand(Command):
    """Command for moving image - using redaction to remove old image"""
    page_num: int
    old_rect: fitz.Rect
    new_rect: fitz.Rect
    image_data: bytes
    xref: int = None

    def __post_init__(self):
        self.timestamp = time.time()

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]

            # Use redaction to remove the image from old position
            annot = page.add_redact_annot(self.old_rect)
            annot.set_colors(fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

            # Clean up
            page.clean_contents()

            # Insert image at new position
            page.insert_image(self.new_rect, stream=self.image_data)

            return True
        except Exception as e:
            print(f"ImageMoveCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]

            # Remove from new position
            annot = page.add_redact_annot(self.new_rect)
            annot.set_colors(fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
            page.clean_contents()

            # Restore at old position
            page.insert_image(self.old_rect, stream=self.image_data)

            return True
        except Exception as e:
            print(f"ImageMoveCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Move image on page {self.page_num + 1}"


@dataclass
class ImageResizeCommand(Command):
    """Command for resizing image - using redaction to remove old image"""
    page_num: int
    old_rect: fitz.Rect
    new_rect: fitz.Rect
    image_data: bytes
    xref: int = None

    def __post_init__(self):
        self.timestamp = time.time()

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]

            # Remove old image
            annot = page.add_redact_annot(self.old_rect)
            annot.set_colors(fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
            page.clean_contents()

            # Insert image at new size
            page.insert_image(self.new_rect, stream=self.image_data)

            return True
        except Exception as e:
            print(f"ImageResizeCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]

            # Remove resized image
            annot = page.add_redact_annot(self.new_rect)
            annot.set_colors(fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
            page.clean_contents()

            # Restore original size
            page.insert_image(self.old_rect, stream=self.image_data)

            return True
        except Exception as e:
            print(f"ImageResizeCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Resize image on page {self.page_num + 1}"


@dataclass
class ShapeAddCommand(Command):
    page_num: int
    shape_type: str
    rect: fitz.Rect = None
    points: List[Tuple[float, float]] = None
    color: Tuple[float, float, float] = (1, 0, 0)
    width: float = 2

    def __post_init__(self):
        self.timestamp = time.time()
        if self.points is None:
            self.points = []

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            shape = page.new_shape()

            if self.shape_type == "rectangle" and self.rect:
                shape.draw_rect(self.rect)
            elif self.shape_type == "circle" and self.rect:
                shape.draw_oval(self.rect)
            elif self.shape_type == "line" and len(self.points) >= 2:
                shape.draw_line(fitz.Point(self.points[0]), fitz.Point(self.points[1]))
            elif self.shape_type == "freehand" and len(self.points) >= 2:
                for i in range(1, len(self.points)):
                    shape.draw_line(fitz.Point(self.points[i - 1]), fitz.Point(self.points[i]))

            shape.finish(color=self.color, width=self.width)
            shape.commit()
            return True
        except Exception as e:
            print(f"ShapeAddCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            if self.rect:
                expanded = fitz.Rect(
                    self.rect.x0 - self.width - 2,
                    self.rect.y0 - self.width - 2,
                    self.rect.x1 + self.width + 2,
                    self.rect.y1 + self.width + 2
                )
                page.add_redact_annot(expanded, fill=(1, 1, 1))
                page.apply_redactions()
            elif self.points:
                xs = [p[0] for p in self.points]
                ys = [p[1] for p in self.points]
                rect = fitz.Rect(
                    min(xs) - self.width - 2,
                    min(ys) - self.width - 2,
                    max(xs) + self.width + 2,
                    max(ys) + self.width + 2
                )
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
            return True
        except Exception as e:
            print(f"ShapeAddCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Add {self.shape_type} on page {self.page_num + 1}"


@dataclass
class AnnotationAddCommand(Command):
    """Command for adding annotations - FIXED quads error"""
    page_num: int
    annot_type: str
    rect: fitz.Rect
    color: Tuple[float, float, float] = (1, 1, 0)
    _annot_xref: int = None

    def __post_init__(self):
        self.timestamp = time.time()

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]

            # Normalize rect
            rect = self.rect.normalize()

            if rect.is_empty or rect.is_infinite:
                return False

            # Minimum size check
            if rect.width < 5 or rect.height < 5:
                return False

            # Use quad for proper annotation
            quad = rect.quad

            if self.annot_type == "highlight":
                annot = page.add_highlight_annot(quad)
                if annot:
                    annot.set_colors(stroke=self.color)
                    annot.update()
                    self._annot_xref = annot.xref
            elif self.annot_type == "underline":
                annot = page.add_underline_annot(quad)
                if annot:
                    annot.update()
                    self._annot_xref = annot.xref
            elif self.annot_type == "strikeout":
                annot = page.add_strikeout_annot(quad)
                if annot:
                    annot.update()
                    self._annot_xref = annot.xref
            else:
                return False

            return True
        except Exception as e:
            print(f"AnnotationAddCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            for annot in page.annots():
                if annot.xref == self._annot_xref:
                    page.delete_annot(annot)
                    return True
            return False
        except Exception as e:
            print(f"AnnotationAddCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Add {self.annot_type} on page {self.page_num + 1}"


@dataclass
class PageRotateCommand(Command):
    page_num: int
    degrees: int

    def __post_init__(self):
        self.timestamp = time.time()

    def execute(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            page.set_rotation((page.rotation + self.degrees) % 360)
            return True
        except Exception as e:
            print(f"PageRotateCommand execute error: {e}")
            return False

    def undo(self, doc: fitz.Document) -> bool:
        try:
            page = doc[self.page_num]
            page.set_rotation((page.rotation - self.degrees) % 360)
            return True
        except Exception as e:
            print(f"PageRotateCommand undo error: {e}")
            return False

    def get_description(self) -> str:
        return f"Rotate page {self.page_num + 1} by {self.degrees}°"


class UndoManager:
    def __init__(self, max_history: int = 100):
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_history = max_history

    def execute(self, command: Command, doc: fitz.Document) -> bool:
        if command.execute(doc):
            if len(self.undo_stack) >= self.max_history:
                self.undo_stack.pop(0)
            self.undo_stack.append(command)
            self.redo_stack.clear()
            return True
        return False

    def undo(self, doc: fitz.Document) -> bool:
        if not self.undo_stack:
            return False
        command = self.undo_stack.pop()
        if command.undo(doc):
            self.redo_stack.append(command)
            return True
        return False

    def redo(self, doc: fitz.Document) -> bool:
        if not self.redo_stack:
            return False
        command = self.redo_stack.pop()
        if command.execute(doc):
            self.undo_stack.append(command)
            return True
        return False

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def get_undo_description(self) -> str:
        return self.undo_stack[-1].get_description() if self.undo_stack else ""

    def get_redo_description(self) -> str:
        return self.redo_stack[-1].get_description() if self.redo_stack else ""

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()

    def get_memory_usage(self) -> int:
        total = 0
        for cmd in self.undo_stack + self.redo_stack:
            if hasattr(cmd, 'image_data') and cmd.image_data:
                total += len(cmd.image_data)
            else:
                total += 500
        return total