"""
PDF Engine v3.0 - Core PDF manipulation with all improvements
- Command-based Undo/Redo
- Optimized caching and lazy loading
- Layer system
- FIXED text editing
- RTL support
- Fast image operations
"""

import fitz
from PIL import Image
import io
import os
import tempfile
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass

from core.undo_manager import (
    UndoManager, TextEditCommand, TextAddCommand,
    ImageInsertCommand, ImageDeleteCommand, ImageMoveCommand, ImageResizeCommand,
    ShapeAddCommand, AnnotationAddCommand, PageRotateCommand
)
from core.cache_system import PageCache, AutoSaveManager
from core.layer_system import (
    LayerManager, ShapeLayer, AnnotationLayer, TextLayer,
    ShapeType, LayerType
)
from core.text_editor import TextAnalyzer, TextEditor, TextBlock, TextSpan


@dataclass
class ImageInfo:
    """Information about an image in PDF"""
    rect: fitz.Rect
    xref: int
    page_num: int
    width: int = 0
    height: int = 0


class PDFEngine:
    """Advanced PDF Engine v3.0 - Optimized for speed and reliability"""

    DISPLAY_DPI = 96
    PDF_DPI = 72
    BASE_SCALE = DISPLAY_DPI / PDF_DPI

    def __init__(self):
        self.doc: Optional[fitz.Document] = None
        self.file_path: Optional[str] = None
        self.modified = False
        self.undo_manager = UndoManager(max_history=100)
        self.cache = PageCache(max_size_mb=200)
        self.layer_manager = LayerManager()
        self.text_editor: Optional[TextEditor] = None
        self.auto_save = AutoSaveManager(interval_seconds=60)
        self._backup_path: Optional[str] = None

    def open(self, file_path: str) -> bool:
        try:
            self.close()
            backup = self._get_backup_path(file_path)
            self.doc = fitz.open(file_path)
            self.file_path = file_path
            self.modified = False
            self.cache.set_document(self.doc)
            self.text_editor = TextEditor(self.doc)
            self.undo_manager.clear()
            self.layer_manager.clear_all_layers()
            self._backup_path = self._get_backup_path(file_path)
            self.auto_save.start(self.doc, self._backup_path)
            return True
        except Exception as e:
            raise Exception(f"Failed to open PDF: {str(e)}")

    def save(self, file_path: Optional[str] = None) -> bool:
        if not self.doc:
            return False
        save_path = file_path or self.file_path
        if not save_path:
            raise Exception("No file path specified")
        try:
            self._commit_layers()
            if save_path == self.file_path:
                temp_path = save_path + ".tmp"
                self.doc.save(temp_path, garbage=4, deflate=True)
                self.doc.close()
                os.replace(temp_path, save_path)
                self.doc = fitz.open(save_path)
                self.cache.set_document(self.doc)
                self.text_editor = TextEditor(self.doc)
            else:
                self.doc.save(save_path, garbage=4, deflate=True)
                self.file_path = save_path
            self.modified = False
            self.auto_save.cleanup_backup()
            return True
        except Exception as e:
            raise Exception(f"Failed to save PDF: {str(e)}")

    def close(self):
        if self.doc:
            self.auto_save.stop()
            self.cache.shutdown()
            self.doc.close()
            self.doc = None
            self.file_path = None
            self.modified = False
            self.text_editor = None
            self.layer_manager.clear_all_layers()

    def is_open(self) -> bool:
        return self.doc is not None

    def get_page_count(self) -> int:
        return len(self.doc) if self.doc else 0

    def get_page(self, page_num: int):
        if self.doc and 0 <= page_num < len(self.doc):
            return self.doc[page_num]
        return None

    def _get_backup_path(self, file_path: str) -> str:
        return file_path + ".backup"

    def _commit_layers(self):
        if not self.doc:
            return
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            self.layer_manager.render_layers(page, page_num)

    def _mark_modified(self):
        self.modified = True
        self.auto_save.mark_modified()

    def get_scale(self, zoom: float) -> float:
        return self.BASE_SCALE * zoom

    def render_page(self, page_num: int, zoom: float = 1.0) -> Optional[Image.Image]:
        if not self.doc or page_num >= len(self.doc):
            return None
        cached = self.cache.get_page_image(page_num, zoom)
        if cached:
            self.cache.prefetch_pages(page_num, zoom)
            return cached
        page = self.doc[page_num]
        scale = self.get_scale(zoom)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.cache.prefetch_pages(page_num, zoom)
        return img

    def render_thumbnail(self, page_num: int, scale: float = 0.15) -> Optional[Image.Image]:
        return self.cache.get_thumbnail(page_num, scale)

    def invalidate_page(self, page_num: int):
        self.cache.invalidate_page(page_num)

    def canvas_to_pdf(self, canvas_x: float, canvas_y: float,
                      zoom: float, offset: Tuple[float, float] = (0, 0)) -> Tuple[float, float]:
        scale = self.get_scale(zoom)
        pdf_x = (canvas_x - offset[0]) / scale
        pdf_y = (canvas_y - offset[1]) / scale
        return pdf_x, pdf_y

    def pdf_to_canvas(self, pdf_x: float, pdf_y: float,
                      zoom: float, offset: Tuple[float, float] = (0, 0)) -> Tuple[float, float]:
        scale = self.get_scale(zoom)
        canvas_x = pdf_x * scale + offset[0]
        canvas_y = pdf_y * scale + offset[1]
        return canvas_x, canvas_y

    def undo(self) -> bool:
        if self.doc and self.undo_manager.can_undo():
            result = self.undo_manager.undo(self.doc)
            if result:
                self.cache.invalidate_all()
                return True
        return False

    def redo(self) -> bool:
        if self.doc and self.undo_manager.can_redo():
            result = self.undo_manager.redo(self.doc)
            if result:
                self.cache.invalidate_all()
                return True
        return False

    def can_undo(self) -> bool:
        return self.undo_manager.can_undo()

    def can_redo(self) -> bool:
        return self.undo_manager.can_redo()

    def get_text_blocks(self, page_num: int) -> List[TextBlock]:
        if not self.doc or page_num >= len(self.doc):
            return []
        page = self.doc[page_num]
        return TextAnalyzer.get_text_blocks(page)

    def find_text_at(self, page_num: int, x: float, y: float) -> Optional[TextBlock]:
        if not self.doc or page_num >= len(self.doc):
            return None
        page = self.doc[page_num]
        return TextAnalyzer.find_block_at(page, x, y)

    def find_span_at(self, page_num: int, x: float, y: float) -> Optional[TextSpan]:
        if not self.doc or page_num >= len(self.doc):
            return None
        page = self.doc[page_num]
        return TextAnalyzer.find_span_at(page, x, y)

    def edit_text(self, page_num: int, block: TextBlock, new_text: str,
                  font_size: float = None, color: Tuple[float, float, float] = None,
                  font_name: str = None) -> bool:
        if not self.doc or not self.text_editor:
            return False

        first_span = block.spans[0] if block.spans else None
        old_font_size = first_span.font_size if first_span else 11
        old_color = first_span.color if first_span else (0, 0, 0)

        cmd = TextEditCommand(
            page_num=page_num,
            rect=block.rect,
            old_text=block.text,
            new_text=new_text,
            old_font_size=old_font_size,
            new_font_size=font_size or old_font_size,
            old_color=old_color,
            new_color=color or old_color,
            font_name=font_name or (first_span.font_name if first_span else "helv")
        )

        if self.undo_manager.execute(cmd, self.doc):
            self.invalidate_page(page_num)
            self._mark_modified()
            return True
        return False

    def add_text(self, page_num: int, x: float, y: float, text: str,
                 font_size: float = 12, color: Tuple[float, float, float] = (0, 0, 0),
                 font_name: str = "helv") -> bool:
        if not self.doc:
            return False

        cmd = TextAddCommand(
            page_num=page_num, x=x, y=y, text=text,
            font_size=font_size, color=color, font_name=font_name
        )

        if self.undo_manager.execute(cmd, self.doc):
            self.invalidate_page(page_num)
            self._mark_modified()
            return True
        return False

    def find_and_replace(self, find_text: str, replace_text: str) -> int:
        if not self.text_editor:
            return 0
        count = self.text_editor.find_and_replace(find_text, replace_text)
        if count > 0:
            self.cache.invalidate_all()
            self._mark_modified()
        return count

    def get_images(self, page_num: int) -> List[ImageInfo]:
        if not self.doc or page_num >= len(self.doc):
            return []
        page = self.doc[page_num]
        images = []
        try:
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                for img_rect in page.get_image_rects(xref):
                    images.append(ImageInfo(
                        rect=img_rect, xref=xref, page_num=page_num,
                        width=img_info[2], height=img_info[3]
                    ))
        except Exception as e:
            pass
        return images

    def find_image_at(self, page_num: int, x: float, y: float) -> Optional[ImageInfo]:
        images = self.get_images(page_num)
        point = fitz.Point(x, y)
        for img in images:
            if img.rect.contains(point):
                return img
        return None

    def insert_image(self, page_num: int, image_path: str, rect: fitz.Rect = None) -> bool:
        if not self.doc or page_num >= len(self.doc):
            return False
        page = self.doc[page_num]
        if rect is None:
            page_rect = page.rect
            rect = fitz.Rect(
                page_rect.width / 4, page_rect.height / 4,
                page_rect.width * 3 / 4, page_rect.height * 3 / 4
            )
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            cmd = ImageInsertCommand(page_num=page_num, rect=rect, image_data=image_data)
            if self.undo_manager.execute(cmd, self.doc):
                self.invalidate_page(page_num)
                self._mark_modified()
                return True
        except Exception as e:
            pass
        return False

    def delete_image(self, page_num: int, image: ImageInfo) -> bool:
        if not self.doc or not image:
            return False
        try:
            base_image = self.doc.extract_image(image.xref)
            image_data = base_image["image"]
            cmd = ImageDeleteCommand(
                page_num=page_num, rect=image.rect,
                image_data=image_data, xref=image.xref
            )
            if self.undo_manager.execute(cmd, self.doc):
                self.invalidate_page(page_num)
                self._mark_modified()
                return True
        except Exception as e:
            pass
        return False

    def move_image(self, page_num: int, image: ImageInfo, new_x: float, new_y: float) -> bool:
        if not self.doc or not image:
            return False
        try:
            base_image = self.doc.extract_image(image.xref)
            image_data = base_image["image"]
            width = image.rect.width
            height = image.rect.height
            new_rect = fitz.Rect(new_x, new_y, new_x + width, new_y + height)
            cmd = ImageMoveCommand(
                page_num=page_num, old_rect=image.rect,
                new_rect=new_rect, image_data=image_data,
                xref=image.xref
            )
            if self.undo_manager.execute(cmd, self.doc):
                self.invalidate_page(page_num)
                self._mark_modified()
                return True
        except Exception as e:
            print(f"Error moving image: {e}")
        return False

    def replace_image(self, page_num: int, image: ImageInfo, new_image_path: str) -> bool:
        if not self.doc or not image:
            return False
        if self.delete_image(page_num, image):
            return self.insert_image(page_num, new_image_path, image.rect)
        return False

    def resize_image(self, page_num: int, image: ImageInfo, new_width: float, new_height: float,
                     keep_aspect_ratio: bool = True) -> bool:
        """Resize image to new dimensions"""
        if not self.doc or not image:
            return False
        try:
            # Calculate new dimensions
            if keep_aspect_ratio:
                # Calculate aspect ratio
                orig_ratio = image.rect.width / image.rect.height
                new_ratio = new_width / new_height

                if new_ratio > orig_ratio:
                    # Height is the limiting factor
                    new_width = new_height * orig_ratio
                else:
                    # Width is the limiting factor
                    new_height = new_width / orig_ratio

            # Get image data
            base_image = self.doc.extract_image(image.xref)
            image_data = base_image["image"]

            # Create new rect at same position with new size
            new_rect = fitz.Rect(
                image.rect.x0,
                image.rect.y0,
                image.rect.x0 + new_width,
                image.rect.y0 + new_height
            )

            cmd = ImageResizeCommand(
                page_num=page_num,
                old_rect=image.rect,
                new_rect=new_rect,
                image_data=image_data,
                xref=image.xref
            )

            if self.undo_manager.execute(cmd, self.doc):
                self.invalidate_page(page_num)
                self._mark_modified()
                return True
        except Exception as e:
            print(f"Error resizing image: {e}")
        return False

    def scale_image(self, page_num: int, image: ImageInfo, scale_factor: float) -> bool:
        """Scale image by a factor (e.g., 0.5 = 50%, 2.0 = 200%)"""
        if not self.doc or not image or scale_factor <= 0:
            return False

        new_width = image.rect.width * scale_factor
        new_height = image.rect.height * scale_factor
        return self.resize_image(page_num, image, new_width, new_height, keep_aspect_ratio=False)

    def crop_image(self, page_num: int, image: ImageInfo,
                   crop_rect: fitz.Rect) -> bool:
        """Crop image to specified rectangle (relative to image)"""
        if not self.doc or not image:
            return False
        try:
            from PIL import Image
            import io

            # Extract image
            base_image = self.doc.extract_image(image.xref)
            image_data = base_image["image"]

            # Load with PIL
            pil_img = Image.open(io.BytesIO(image_data))

            # Calculate crop coordinates (PDF coords to image coords)
            img_width, img_height = pil_img.size
            scale_x = img_width / image.rect.width
            scale_y = img_height / image.rect.height

            # Crop box in image coordinates
            left = int((crop_rect.x0 - image.rect.x0) * scale_x)
            top = int((crop_rect.y0 - image.rect.y0) * scale_y)
            right = int((crop_rect.x1 - image.rect.x0) * scale_x)
            bottom = int((crop_rect.y1 - image.rect.y0) * scale_y)

            # Ensure valid bounds
            left = max(0, min(left, img_width))
            top = max(0, min(top, img_height))
            right = max(left, min(right, img_width))
            bottom = max(top, min(bottom, img_height))

            # Crop
            cropped = pil_img.crop((left, top, right, bottom))

            # Save to bytes
            output = io.BytesIO()
            cropped.save(output, format='PNG')
            new_image_data = output.getvalue()

            # Delete old and insert new
            page = self.doc[page_num]

            # Remove old image
            expanded = fitz.Rect(
                image.rect.x0 - 1, image.rect.y0 - 1,
                image.rect.x1 + 1, image.rect.y1 + 1
            )
            page.add_redact_annot(expanded, fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

            # Insert cropped image at crop_rect position
            page.insert_image(crop_rect, stream=new_image_data)

            self.invalidate_page(page_num)
            self._mark_modified()
            return True

        except Exception as e:
            print(f"Error cropping image: {e}")
        return False

    def rotate_image(self, page_num: int, image: ImageInfo, degrees: int = 90) -> bool:
        """Rotate image by specified degrees (90, 180, 270)"""
        if not self.doc or not image:
            return False
        if degrees not in [90, 180, 270, -90, -180, -270]:
            return False
        try:
            from PIL import Image
            import io

            # Extract image
            base_image = self.doc.extract_image(image.xref)
            image_data = base_image["image"]

            # Load with PIL and rotate
            pil_img = Image.open(io.BytesIO(image_data))
            rotated = pil_img.rotate(-degrees, expand=True)  # PIL rotates counter-clockwise

            # Save to bytes
            output = io.BytesIO()
            rotated.save(output, format='PNG')
            new_image_data = output.getvalue()

            # Calculate new rect (swap width/height for 90/270)
            if degrees in [90, 270, -90, -270]:
                new_width = image.rect.height
                new_height = image.rect.width
            else:
                new_width = image.rect.width
                new_height = image.rect.height

            new_rect = fitz.Rect(
                image.rect.x0,
                image.rect.y0,
                image.rect.x0 + new_width,
                image.rect.y0 + new_height
            )

            # Remove old image
            page = self.doc[page_num]
            expanded = fitz.Rect(
                image.rect.x0 - 1, image.rect.y0 - 1,
                image.rect.x1 + 1, image.rect.y1 + 1
            )
            page.add_redact_annot(expanded, fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

            # Insert rotated image
            page.insert_image(new_rect, stream=new_image_data)

            self.invalidate_page(page_num)
            self._mark_modified()
            return True

        except Exception as e:
            print(f"Error rotating image: {e}")
        return False

    def extract_image(self, image: ImageInfo, output_path: str) -> bool:
        if not self.doc or not image:
            return False
        try:
            base_image = self.doc.extract_image(image.xref)
            image_data = base_image["image"]
            ext = base_image["ext"]
            if not output_path.endswith(f".{ext}"):
                output_path = f"{output_path}.{ext}"
            with open(output_path, "wb") as f:
                f.write(image_data)
            return True
        except Exception as e:
            return False

    def add_shape(self, page_num: int, shape_type: str, rect: fitz.Rect = None,
                  points: List[Tuple[float, float]] = None,
                  color: Tuple[float, float, float] = (1, 0, 0),
                  width: float = 2) -> str:
        if not self.doc:
            return None
        layer = ShapeLayer(
            id="", layer_type=LayerType.SHAPE, page_num=page_num,
            shape_type=ShapeType(shape_type), rect=rect,
            points=points or [], color=color, stroke_width=width
        )
        layer_id = self.layer_manager.add_layer(layer)
        cmd = ShapeAddCommand(
            page_num=page_num, shape_type=shape_type, rect=rect,
            points=points, color=color, width=width
        )
        self.undo_manager.execute(cmd, self.doc)
        self.invalidate_page(page_num)
        self._mark_modified()
        return layer_id

    def add_rectangle(self, page_num: int, rect: fitz.Rect,
                      color: Tuple[float, float, float] = (1, 0, 0), width: float = 2) -> str:
        return self.add_shape(page_num, "rectangle", rect=rect, color=color, width=width)

    def add_circle(self, page_num: int, rect: fitz.Rect,
                   color: Tuple[float, float, float] = (1, 0, 0), width: float = 2) -> str:
        return self.add_shape(page_num, "circle", rect=rect, color=color, width=width)

    def add_line(self, page_num: int, start: Tuple[float, float], end: Tuple[float, float],
                 color: Tuple[float, float, float] = (1, 0, 0), width: float = 2) -> str:
        return self.add_shape(page_num, "line", points=[start, end], color=color, width=width)

    def add_freehand(self, page_num: int, points: List[Tuple[float, float]],
                     color: Tuple[float, float, float] = (1, 0, 0), width: float = 2) -> str:
        return self.add_shape(page_num, "freehand", points=points, color=color, width=width)

    def add_highlight(self, page_num: int, rect: fitz.Rect,
                      color: Tuple[float, float, float] = (1, 1, 0)) -> bool:
        if not self.doc:
            return False
        cmd = AnnotationAddCommand(page_num=page_num, annot_type="highlight", rect=rect, color=color)
        if self.undo_manager.execute(cmd, self.doc):
            self.invalidate_page(page_num)
            self._mark_modified()
            return True
        return False

    def add_underline(self, page_num: int, rect: fitz.Rect) -> bool:
        if not self.doc:
            return False
        cmd = AnnotationAddCommand(page_num=page_num, annot_type="underline", rect=rect)
        if self.undo_manager.execute(cmd, self.doc):
            self.invalidate_page(page_num)
            self._mark_modified()
            return True
        return False

    def add_strikeout(self, page_num: int, rect: fitz.Rect) -> bool:
        if not self.doc:
            return False
        cmd = AnnotationAddCommand(page_num=page_num, annot_type="strikeout", rect=rect)
        if self.undo_manager.execute(cmd, self.doc):
            self.invalidate_page(page_num)
            self._mark_modified()
            return True
        return False

    def add_page(self, width: float = None, height: float = None, index: int = -1) -> bool:
        if not self.doc:
            return False
        if width is None or height is None:
            first_page = self.doc[0]
            rect = first_page.rect
            width = rect.width
            height = rect.height
        self.doc.insert_page(index, width=width, height=height)
        self._mark_modified()
        return True

    def delete_page(self, page_num: int) -> bool:
        if not self.doc or len(self.doc) <= 1:
            return False
        if 0 <= page_num < len(self.doc):
            self.doc.delete_page(page_num)
            self.layer_manager.clear_page_layers(page_num)
            self.cache.invalidate_all()
            self._mark_modified()
            return True
        return False

    def rotate_page(self, page_num: int, degrees: int = 90) -> bool:
        if not self.doc:
            return False
        cmd = PageRotateCommand(page_num=page_num, degrees=degrees)
        if self.undo_manager.execute(cmd, self.doc):
            self.invalidate_page(page_num)
            self._mark_modified()
            return True
        return False

    def extract_pages(self, page_nums: List[int], output_path: str) -> bool:
        if not self.doc:
            return False
        try:
            new_doc = fitz.open()
            for p in page_nums:
                if 0 <= p < len(self.doc):
                    new_doc.insert_pdf(self.doc, from_page=p, to_page=p)
            new_doc.save(output_path, garbage=4, deflate=True)
            new_doc.close()
            return True
        except:
            return False

    def merge_pdfs(self, pdf_paths: List[str], output_path: str) -> bool:
        try:
            merged = fitz.open()
            for pdf_path in pdf_paths:
                doc = fitz.open(pdf_path)
                merged.insert_pdf(doc)
                doc.close()
            merged.save(output_path, garbage=4, deflate=True)
            merged.close()
            return True
        except:
            return False

    def add_watermark(self, text: str, color: Tuple[float, float, float] = (0.8, 0.8, 0.8),
                      font_size: float = 60, rotation: float = 45) -> bool:
        if not self.doc:
            return False
        for page in self.doc:
            rect = page.rect
            page.insert_text(
                (rect.width / 4, rect.height / 2), text,
                fontsize=font_size, color=color, rotate=rotation
            )
        self.cache.invalidate_all()
        self._mark_modified()
        return True

    def add_stamp(self, page_num: int, text: str, x: float, y: float,
                  color: Tuple[float, float, float] = (1, 0, 0),
                  font_size: float = 72, rotation: float = 45) -> bool:
        if not self.doc or page_num >= len(self.doc):
            return False
        page = self.doc[page_num]
        page.insert_text((x, y), text, fontsize=font_size, color=color, rotate=rotation)
        self.invalidate_page(page_num)
        self._mark_modified()
        return True

    def export_images(self, output_dir: str, dpi: int = 150) -> int:
        if not self.doc:
            return 0
        scale = dpi / 72
        count = 0
        for i, page in enumerate(self.doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            img_path = os.path.join(output_dir, f"page_{i+1}.png")
            pix.save(img_path)
            count += 1
        return count

    def extract_text(self, output_path: str) -> bool:
        if not self.doc:
            return False
        try:
            text = ""
            for page in self.doc:
                text += page.get_text() + "\n\n"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except:
            return False

    def get_page_size(self, page_num: int) -> Tuple[float, float]:
        if self.doc and 0 <= page_num < len(self.doc):
            rect = self.doc[page_num].rect
            return rect.width, rect.height
        return 0, 0

    def get_memory_stats(self) -> Dict:
        return {
            "cache": self.cache.get_stats(),
            "undo_memory": self.undo_manager.get_memory_usage()
        }