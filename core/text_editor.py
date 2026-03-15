"""
Advanced Text Editor for PDF Editor Pro v3.0
REAL text editing like Adobe Acrobat
"""

import fitz
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class TextDirection(Enum):
    LTR = "ltr"
    RTL = "rtl"


@dataclass
class TextSpan:
    """Individual text span with properties"""
    text: str
    rect: fitz.Rect
    font_name: str
    font_size: float
    color: Tuple[float, float, float]
    flags: int = 0
    origin: Tuple[float, float] = (0, 0)
    baseline: float = 0

    def is_bold(self) -> bool:
        return bool(self.flags & 2 ** 4)

    def is_italic(self) -> bool:
        return bool(self.flags & 2 ** 1)


@dataclass
class TextLine:
    """A line of text containing multiple spans"""
    spans: List[TextSpan]
    rect: fitz.Rect
    direction: TextDirection = TextDirection.LTR

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)

    def get_span_at(self, x: float) -> Optional[TextSpan]:
        for span in self.spans:
            if span.rect.x0 <= x <= span.rect.x1:
                return span
        return None


@dataclass
class TextBlock:
    """A block of text containing multiple lines"""
    lines: List[TextLine]
    rect: fitz.Rect
    page_num: int = 0

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def spans(self) -> List[TextSpan]:
        result = []
        for line in self.lines:
            result.extend(line.spans)
        return result

    def get_span_at(self, x: float, y: float) -> Optional[TextSpan]:
        for line in self.lines:
            if line.rect.y0 <= y <= line.rect.y1:
                return line.get_span_at(x)
        return None


class TextAnalyzer:
    """Analyzes PDF text structure at span level"""

    @staticmethod
    def detect_direction(text: str) -> TextDirection:
        if not text:
            return TextDirection.LTR
        rtl_count = 0
        ltr_count = 0
        for char in text:
            code = ord(char)
            if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F:
                rtl_count += 1
            elif 0x0590 <= code <= 0x05FF:
                rtl_count += 1
            elif 0x0041 <= code <= 0x007A or 0x0400 <= code <= 0x04FF:
                ltr_count += 1
        return TextDirection.RTL if rtl_count > ltr_count else TextDirection.LTR

    @staticmethod
    def get_text_blocks(page: fitz.Page) -> List[TextBlock]:
        """Extract text blocks with span-level detail"""
        blocks = []

        try:
            text_dict = page.get_text("dict")

            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue

                block_bbox = block.get("bbox", [0, 0, 0, 0])
                block_rect = fitz.Rect(block_bbox)
                lines = []

                for line in block.get("lines", []):
                    line_bbox = line.get("bbox", [0, 0, 0, 0])
                    line_rect = fitz.Rect(line_bbox)
                    spans = []

                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if not span_text:
                            continue

                        span_bbox = span.get("bbox", [0, 0, 0, 0])
                        span_rect = fitz.Rect(span_bbox)
                        origin = span.get("origin", (span_rect.x0, span_rect.y1))

                        color_int = span.get("color", 0)
                        if isinstance(color_int, int):
                            color = (
                                ((color_int >> 16) & 0xFF) / 255,
                                ((color_int >> 8) & 0xFF) / 255,
                                (color_int & 0xFF) / 255
                            )
                        else:
                            color = (0, 0, 0)

                        text_span = TextSpan(
                            text=span_text,
                            rect=span_rect,
                            font_name=span.get("font", "helv"),
                            font_size=span.get("size", 11),
                            color=color,
                            flags=span.get("flags", 0),
                            origin=origin,
                            baseline=origin[1] if origin else span_rect.y1
                        )
                        spans.append(text_span)

                    if spans:
                        direction = TextAnalyzer.detect_direction("".join(s.text for s in spans))
                        lines.append(TextLine(spans=spans, rect=line_rect, direction=direction))

                if lines:
                    blocks.append(TextBlock(lines=lines, rect=block_rect, page_num=page.number))

        except Exception as e:
            print(f"Error analyzing text: {e}")

        return blocks

    @staticmethod
    def find_span_at(page: fitz.Page, x: float, y: float) -> Optional[TextSpan]:
        """Find span at coordinates with tolerance"""
        blocks = TextAnalyzer.get_text_blocks(page)
        point = fitz.Point(x, y)
        tolerance = 5

        for block in blocks:
            expanded_block = fitz.Rect(
                block.rect.x0 - tolerance,
                block.rect.y0 - tolerance,
                block.rect.x1 + tolerance,
                block.rect.y1 + tolerance
            )
            if expanded_block.contains(point):
                result = block.get_span_at(x, y)
                if result:
                    return result
                if block.spans:
                    return block.spans[0]
        return None

    @staticmethod
    def find_block_at(page: fitz.Page, x: float, y: float) -> Optional[TextBlock]:
        """Find text block at coordinates with tolerance"""
        blocks = TextAnalyzer.get_text_blocks(page)
        point = fitz.Point(x, y)

        # First try exact match
        for block in blocks:
            if block.rect.contains(point):
                return block

        # Try with expanded tolerance
        tolerance = 10
        for block in blocks:
            expanded = fitz.Rect(
                block.rect.x0 - tolerance,
                block.rect.y0 - tolerance,
                block.rect.x1 + tolerance,
                block.rect.y1 + tolerance
            )
            if expanded.contains(point):
                return block

        return None

    @staticmethod
    def search_text(page: fitz.Page, search_text: str) -> List[fitz.Rect]:
        return page.search_for(search_text)


class TextEditor:
    """
    Advanced text editor - REAL editing like Adobe Acrobat
    Uses proper redaction and reinsertion with exact formatting
    """

    def __init__(self, doc: fitz.Document):
        self.doc = doc

    def edit_text_block(self, page_num: int, block: TextBlock,
                        new_text: str, font_size: float = None,
                        color: Tuple[float, float, float] = None,
                        font_name: str = None) -> bool:
        """
        Edit a text block with multilingual support (Arabic, Russian, CJK)
        """
        if not self.doc or page_num >= len(self.doc):
            return False

        page = self.doc[page_num]

        try:
            # Get original formatting from first span
            first_span = block.spans[0] if block.spans else None
            original_font = first_span.font_name if first_span else "helv"
            original_size = first_span.font_size if first_span else 11
            original_color = first_span.color if first_span else (0, 0, 0)

            # Use provided values or originals
            use_size = font_size or original_size
            use_color = color or original_color
            requested_font = font_name or original_font

            # Get appropriate font for the text
            fontname, fontfile = self._get_font_for_text(new_text, requested_font)

            # Step 1: Create white rectangle to cover old text
            cover_rect = fitz.Rect(
                block.rect.x0 - 1,
                block.rect.y0 - 1,
                block.rect.x1 + 1,
                block.rect.y1 + 1
            )

            # Add redaction annotation
            redact = page.add_redact_annot(cover_rect)
            redact.set_colors(fill=(1, 1, 1))

            # Apply redaction
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            # Step 2: Insert new text at the original position
            if new_text.strip():
                x_start = block.rect.x0
                y_start = block.rect.y0 + use_size

                # Handle text direction
                direction = TextAnalyzer.detect_direction(new_text)

                lines = new_text.split('\n')
                line_height = use_size * 1.2

                for i, line in enumerate(lines):
                    if line:
                        y_pos = y_start + (i * line_height)

                        # Shape text for RTL if needed
                        display_line = self._shape_text(line, direction)

                        try:
                            if fontfile:
                                # Use fontfile for Arabic/Russian/CJK
                                page.insert_text(
                                    point=fitz.Point(x_start, y_pos),
                                    text=display_line,
                                    fontfile=fontfile,
                                    fontsize=use_size,
                                    color=use_color
                                )
                            elif fontname:
                                page.insert_text(
                                    point=fitz.Point(x_start, y_pos),
                                    text=display_line,
                                    fontname=fontname,
                                    fontsize=use_size,
                                    color=use_color
                                )
                            else:
                                page.insert_text(
                                    point=fitz.Point(x_start, y_pos),
                                    text=display_line,
                                    fontsize=use_size,
                                    color=use_color
                                )
                        except Exception as font_error:
                            print(f"Font error, using fallback: {font_error}")
                            # Fallback without specific font
                            page.insert_text(
                                point=fitz.Point(x_start, y_pos),
                                text=display_line,
                                fontsize=use_size,
                                color=use_color
                            )

            return True

        except Exception as e:
            print(f"Error editing text block: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _normalize_font(self, font_name: str) -> str:
        """Normalize font name to PyMuPDF compatible name"""
        font_map = {
            "helv": "helv",
            "Helvetica": "helv",
            "helvetica": "helv",
            "Arial": "helv",
            "arial": "helv",
            "tiro": "tiro",
            "Times-Roman": "tiro",
            "Times": "tiro",
            "times": "tiro",
            "cour": "cour",
            "Courier": "cour",
            "courier": "cour",
            # Multilingual fonts
            "arabic": "arabic",
            "Arabic (Noto)": "arabic",
            "russian": "russian",
            "Russian (Noto)": "russian",
            "cjk": "cjk",
            "CJK (Chinese/Japanese/Korean)": "cjk",
        }

        if font_name in font_map:
            return font_map[font_name]

        lower_name = font_name.lower()
        if "helvetica" in lower_name or "arial" in lower_name:
            return "helv"
        if "times" in lower_name:
            return "tiro"
        if "courier" in lower_name:
            return "cour"
        if "arab" in lower_name or "noto" in lower_name:
            return "arabic"
        if "cyr" in lower_name or "russian" in lower_name:
            return "russian"

        return "helv"

    def _get_font_for_text(self, text: str, requested_font: str = "helv"):
        """
        Get appropriate font based on text content and requested font.
        Returns (fontname, fontfile) tuple.
        For Arabic/Russian, we need to use fontfile parameter.
        """
        # Check if text contains Arabic characters
        has_arabic = any('\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F' for c in text)
        # Check if text contains Cyrillic (Russian) characters
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)

        # If user explicitly requested Arabic or Russian font
        if requested_font in ["arabic", "Arabic (Noto)"]:
            return None, "notos"  # Noto Sans Arabic
        if requested_font in ["russian", "Russian (Noto)"]:
            return None, "notos"  # Noto Sans (supports Cyrillic)
        if requested_font in ["cjk", "CJK (Chinese/Japanese/Korean)"]:
            return None, "notocjk"

        # Auto-detect based on text content
        if has_arabic:
            return None, "notos"
        if has_cyrillic:
            return None, "notos"

        # Standard fonts
        return self._normalize_font(requested_font), None

    def add_text(self, page_num: int, x: float, y: float, text: str,
                 font_name: str = "helv", font_size: float = 12,
                 color: Tuple[float, float, float] = (0, 0, 0)) -> bool:
        """Add new text at position with multilingual support"""
        if not self.doc or page_num >= len(self.doc):
            return False

        page = self.doc[page_num]
        try:
            # Get appropriate font
            fontname, fontfile = self._get_font_for_text(text, font_name)

            # Handle text direction
            direction = TextAnalyzer.detect_direction(text)
            display_text = self._shape_text(text, direction)

            if fontfile:
                # Use fontfile for Arabic/Russian/CJK
                page.insert_text(
                    fitz.Point(x, y),
                    display_text,
                    fontsize=font_size,
                    fontfile=fontfile,
                    color=color
                )
            elif fontname:
                # Use standard font
                page.insert_text(
                    fitz.Point(x, y),
                    display_text,
                    fontsize=font_size,
                    fontname=fontname,
                    color=color
                )
            else:
                # Fallback
                page.insert_text(
                    fitz.Point(x, y),
                    display_text,
                    fontsize=font_size,
                    color=color
                )
            return True
        except Exception as e:
            print(f"Error adding text: {e}")
            # Fallback without font specification
            try:
                page.insert_text(
                    fitz.Point(x, y),
                    text,
                    fontsize=font_size,
                    color=color
                )
                return True
            except:
                return False

    def find_and_replace(self, find_text: str, replace_text: str,
                         page_num: int = None) -> int:
        """Find and replace text across document or single page"""
        if not self.doc:
            return 0

        count = 0
        pages = [page_num] if page_num is not None else range(len(self.doc))

        for pn in pages:
            if pn >= len(self.doc):
                continue

            page = self.doc[pn]
            instances = page.search_for(find_text)

            for rect in instances:
                try:
                    font_size = rect.height * 0.8

                    expanded = fitz.Rect(
                        rect.x0 - 1, rect.y0 - 1,
                        rect.x1 + 1, rect.y1 + 1
                    )

                    redact = page.add_redact_annot(expanded)
                    redact.set_colors(fill=(1, 1, 1))
                    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

                    page.insert_text(
                        fitz.Point(rect.x0, rect.y1),
                        replace_text,
                        fontsize=font_size,
                        color=(0, 0, 0)
                    )

                    count += 1
                except Exception as e:
                    print(f"Error replacing text: {e}")
                    continue

        return count

    def _shape_text(self, text: str, direction: TextDirection) -> str:
        """Apply text shaping for RTL text"""
        if direction == TextDirection.LTR:
            return text
        try:
            from bidi.algorithm import get_display
            return get_display(text)
        except ImportError:
            return text

    def get_selection_text(self, page_num: int, rect: fitz.Rect) -> str:
        """Get text within a selection rectangle"""
        if not self.doc or page_num >= len(self.doc):
            return ""
        page = self.doc[page_num]
        try:
            return page.get_textbox(rect).strip()
        except:
            return ""

    def delete_text_block(self, page_num: int, block: TextBlock) -> bool:
        """Delete a text block completely"""
        if not self.doc or page_num >= len(self.doc):
            return False

        page = self.doc[page_num]
        try:
            cover_rect = fitz.Rect(
                block.rect.x0 - 1,
                block.rect.y0 - 1,
                block.rect.x1 + 1,
                block.rect.y1 + 1
            )

            redact = page.add_redact_annot(cover_rect)
            redact.set_colors(fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            return True
        except Exception as e:
            print(f"Error deleting text: {e}")
            return False
