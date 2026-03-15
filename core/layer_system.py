"""
Layer System for PDF Editor Pro
Manages shapes, annotations, and drawings as separate layers
Allows editing, moving, and deleting individual elements
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import uuid
import fitz
import math
import time


class LayerType(Enum):
    """Types of layers"""
    SHAPE = "shape"
    ANNOTATION = "annotation"
    TEXT = "text"
    IMAGE = "image"
    FREEHAND = "freehand"
    STAMP = "stamp"
    SIGNATURE = "signature"


class ShapeType(Enum):
    """Types of shapes"""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    LINE = "line"
    ARROW = "arrow"
    FREEHAND = "freehand"


@dataclass
class Layer:
    """Base layer class"""
    id: str
    layer_type: LayerType
    page_num: int
    visible: bool = True
    locked: bool = False
    z_index: int = 0
    created_at: float = 0
    modified_at: float = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = time.time()
        self.modified_at = self.created_at


@dataclass
class ShapeLayer(Layer):
    """Layer for shapes (rectangle, circle, line, etc.)"""
    shape_type: ShapeType = ShapeType.RECTANGLE
    rect: fitz.Rect = None
    points: List[Tuple[float, float]] = field(default_factory=list)
    color: Tuple[float, float, float] = (1, 0, 0)
    fill_color: Optional[Tuple[float, float, float]] = None
    stroke_width: float = 2
    opacity: float = 1.0

    def __post_init__(self):
        super().__post_init__()
        self.layer_type = LayerType.SHAPE

    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside shape"""
        if self.rect:
            return self.rect.contains(fitz.Point(x, y))
        elif self.points:
            threshold = self.stroke_width + 5
            for i in range(1, len(self.points)):
                p1 = self.points[i - 1]
                p2 = self.points[i]
                dist = self._point_to_line_distance(x, y, p1[0], p1[1], p2[0], p2[1])
                if dist < threshold:
                    return True
        return False

    def _point_to_line_distance(self, px, py, x1, y1, x2, y2) -> float:
        """Calculate distance from point to line segment"""
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

    def get_bounds(self) -> fitz.Rect:
        """Get bounding rectangle"""
        if self.rect:
            return self.rect
        elif self.points:
            xs = [p[0] for p in self.points]
            ys = [p[1] for p in self.points]
            return fitz.Rect(min(xs), min(ys), max(xs), max(ys))
        return fitz.Rect(0, 0, 0, 0)

    def move(self, dx: float, dy: float):
        """Move shape by offset"""
        if self.rect:
            self.rect = fitz.Rect(
                self.rect.x0 + dx, self.rect.y0 + dy,
                self.rect.x1 + dx, self.rect.y1 + dy
            )
        if self.points:
            self.points = [(p[0] + dx, p[1] + dy) for p in self.points]
        self.modified_at = time.time()

    def resize(self, new_rect: fitz.Rect):
        """Resize shape"""
        if self.rect:
            self.rect = new_rect
        self.modified_at = time.time()

    def render(self, page: fitz.Page):
        """Render shape to PDF page"""
        if not self.visible:
            return

        shape = page.new_shape()

        if self.shape_type == ShapeType.RECTANGLE:
            if self.rect:
                shape.draw_rect(self.rect)
        elif self.shape_type == ShapeType.CIRCLE:
            if self.rect:
                shape.draw_oval(self.rect)
        elif self.shape_type == ShapeType.LINE:
            if len(self.points) >= 2:
                shape.draw_line(fitz.Point(self.points[0]), fitz.Point(self.points[1]))
        elif self.shape_type == ShapeType.ARROW:
            if len(self.points) >= 2:
                shape.draw_line(fitz.Point(self.points[0]), fitz.Point(self.points[1]))
                # Draw arrow head
                p1, p2 = self.points[0], self.points[1]
                angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
                arrow_len = 15
                arrow_angle = math.pi / 6

                head1 = (
                    p2[0] - arrow_len * math.cos(angle - arrow_angle),
                    p2[1] - arrow_len * math.sin(angle - arrow_angle)
                )
                head2 = (
                    p2[0] - arrow_len * math.cos(angle + arrow_angle),
                    p2[1] - arrow_len * math.sin(angle + arrow_angle)
                )
                shape.draw_line(fitz.Point(p2), fitz.Point(head1))
                shape.draw_line(fitz.Point(p2), fitz.Point(head2))

        elif self.shape_type == ShapeType.FREEHAND:
            for i in range(1, len(self.points)):
                shape.draw_line(
                    fitz.Point(self.points[i - 1]),
                    fitz.Point(self.points[i])
                )

        shape.finish(
            color=self.color,
            fill=self.fill_color,
            width=self.stroke_width,
            stroke_opacity=self.opacity,
            fill_opacity=self.opacity
        )
        shape.commit()


@dataclass
class AnnotationLayer(Layer):
    """Layer for annotations (highlight, underline, strikeout)"""
    annot_type: str = "highlight"
    rect: fitz.Rect = None
    color: Tuple[float, float, float] = (1, 1, 0)
    opacity: float = 0.5
    _annot_xref: int = None

    def __post_init__(self):
        super().__post_init__()
        self.layer_type = LayerType.ANNOTATION

    def contains_point(self, x: float, y: float) -> bool:
        if self.rect:
            return self.rect.contains(fitz.Point(x, y))
        return False

    def get_bounds(self) -> fitz.Rect:
        return self.rect if self.rect else fitz.Rect(0, 0, 0, 0)

    def render(self, page: fitz.Page):
        """Render annotation to PDF page"""
        if not self.visible or not self.rect:
            return

        try:
            if self.annot_type == "highlight":
                annot = page.add_highlight_annot(self.rect)
                annot.set_colors(stroke=self.color)
            elif self.annot_type == "underline":
                annot = page.add_underline_annot(self.rect)
            elif self.annot_type == "strikeout":
                annot = page.add_strikeout_annot(self.rect)
            else:
                return

            annot.set_opacity(self.opacity)
            annot.update()
            self._annot_xref = annot.xref
        except Exception as e:
            print(f"Error rendering annotation: {e}")


@dataclass
class TextLayer(Layer):
    """Layer for text elements"""
    rect: fitz.Rect = None
    text: str = ""
    font_name: str = "helv"
    font_size: float = 12
    color: Tuple[float, float, float] = (0, 0, 0)
    alignment: str = "left"

    def __post_init__(self):
        super().__post_init__()
        self.layer_type = LayerType.TEXT

    def contains_point(self, x: float, y: float) -> bool:
        if self.rect:
            return self.rect.contains(fitz.Point(x, y))
        return False

    def get_bounds(self) -> fitz.Rect:
        return self.rect if self.rect else fitz.Rect(0, 0, 0, 0)

    def move(self, dx: float, dy: float):
        if self.rect:
            self.rect = fitz.Rect(
                self.rect.x0 + dx, self.rect.y0 + dy,
                self.rect.x1 + dx, self.rect.y1 + dy
            )
        self.modified_at = time.time()

    def render(self, page: fitz.Page):
        """Render text to PDF page"""
        if not self.visible or not self.text:
            return

        try:
            x = self.rect.x0 if self.rect else 100
            y = self.rect.y0 + self.font_size if self.rect else 100

            page.insert_text(
                fitz.Point(x, y),
                self.text,
                fontsize=self.font_size,
                fontname=self.font_name,
                color=self.color
            )
        except Exception as e:
            print(f"Error rendering text: {e}")


class LayerManager:
    """Manages all layers for a document"""

    def __init__(self):
        self.layers: Dict[int, List[Layer]] = {}
        self.selected_layer: Optional[Layer] = None
        self._next_z_index = 0

    def add_layer(self, layer: Layer) -> str:
        """Add a layer and return its ID"""
        page_num = layer.page_num

        if page_num not in self.layers:
            self.layers[page_num] = []

        layer.z_index = self._next_z_index
        self._next_z_index += 1

        self.layers[page_num].append(layer)
        return layer.id

    def remove_layer(self, layer_id: str) -> bool:
        """Remove a layer by ID"""
        for page_num, page_layers in self.layers.items():
            for i, layer in enumerate(page_layers):
                if layer.id == layer_id:
                    page_layers.pop(i)
                    if self.selected_layer and self.selected_layer.id == layer_id:
                        self.selected_layer = None
                    return True
        return False

    def get_layer(self, layer_id: str) -> Optional[Layer]:
        """Get a layer by ID"""
        for page_layers in self.layers.values():
            for layer in page_layers:
                if layer.id == layer_id:
                    return layer
        return None

    def get_layers_for_page(self, page_num: int) -> List[Layer]:
        """Get all layers for a page, sorted by z-index"""
        if page_num not in self.layers:
            return []
        return sorted(self.layers[page_num], key=lambda l: l.z_index)

    def find_layer_at(self, page_num: int, x: float, y: float) -> Optional[Layer]:
        """Find topmost layer at coordinates"""
        layers = self.get_layers_for_page(page_num)

        for layer in reversed(layers):
            if layer.visible and not layer.locked:
                if hasattr(layer, 'contains_point') and layer.contains_point(x, y):
                    return layer

        return None

    def select_layer(self, layer: Optional[Layer]):
        """Select a layer"""
        self.selected_layer = layer

    def move_layer_up(self, layer_id: str):
        """Move layer up in z-order"""
        layer = self.get_layer(layer_id)
        if layer:
            layer.z_index += 1.5
            self._renumber_z_indices(layer.page_num)

    def move_layer_down(self, layer_id: str):
        """Move layer down in z-order"""
        layer = self.get_layer(layer_id)
        if layer:
            layer.z_index -= 1.5
            self._renumber_z_indices(layer.page_num)

    def _renumber_z_indices(self, page_num: int):
        """Renumber z-indices for a page"""
        if page_num in self.layers:
            sorted_layers = sorted(self.layers[page_num], key=lambda l: l.z_index)
            for i, layer in enumerate(sorted_layers):
                layer.z_index = i

    def render_layers(self, page: fitz.Page, page_num: int):
        """Render all visible layers to a page"""
        layers = self.get_layers_for_page(page_num)

        for layer in layers:
            if layer.visible and hasattr(layer, 'render'):
                layer.render(page)

    def clear_page_layers(self, page_num: int):
        """Clear all layers for a page"""
        if page_num in self.layers:
            self.layers[page_num].clear()

    def clear_all_layers(self):
        """Clear all layers"""
        self.layers.clear()
        self.selected_layer = None
        self._next_z_index = 0

    def to_dict(self) -> Dict:
        """Serialize layers to dictionary"""
        result = {}
        for page_num, page_layers in self.layers.items():
            result[page_num] = []
            for layer in page_layers:
                layer_dict = {
                    "id": layer.id,
                    "type": layer.layer_type.value,
                    "page_num": layer.page_num,
                    "visible": layer.visible,
                    "locked": layer.locked,
                    "z_index": layer.z_index
                }

                if isinstance(layer, ShapeLayer):
                    layer_dict["shape_type"] = layer.shape_type.value
                    if layer.rect:
                        layer_dict["rect"] = [layer.rect.x0, layer.rect.y0,
                                              layer.rect.x1, layer.rect.y1]
                    layer_dict["points"] = layer.points
                    layer_dict["color"] = layer.color
                    layer_dict["stroke_width"] = layer.stroke_width

                elif isinstance(layer, AnnotationLayer):
                    layer_dict["annot_type"] = layer.annot_type
                    if layer.rect:
                        layer_dict["rect"] = [layer.rect.x0, layer.rect.y0,
                                              layer.rect.x1, layer.rect.y1]
                    layer_dict["color"] = layer.color

                elif isinstance(layer, TextLayer):
                    if layer.rect:
                        layer_dict["rect"] = [layer.rect.x0, layer.rect.y0,
                                              layer.rect.x1, layer.rect.y1]
                    layer_dict["text"] = layer.text
                    layer_dict["font_name"] = layer.font_name
                    layer_dict["font_size"] = layer.font_size
                    layer_dict["color"] = layer.color

                result[page_num].append(layer_dict)

        return result

    def from_dict(self, data: Dict):
        """Load layers from dictionary"""
        self.clear_all_layers()

        for page_num_str, page_layers in data.items():
            page_num = int(page_num_str)

            for layer_dict in page_layers:
                layer_type = LayerType(layer_dict["type"])

                if layer_type == LayerType.SHAPE:
                    rect = None
                    if "rect" in layer_dict:
                        r = layer_dict["rect"]
                        rect = fitz.Rect(r[0], r[1], r[2], r[3])

                    layer = ShapeLayer(
                        id=layer_dict["id"],
                        layer_type=layer_type,
                        page_num=page_num,
                        visible=layer_dict.get("visible", True),
                        locked=layer_dict.get("locked", False),
                        z_index=layer_dict.get("z_index", 0),
                        shape_type=ShapeType(layer_dict["shape_type"]),
                        rect=rect,
                        points=layer_dict.get("points", []),
                        color=tuple(layer_dict.get("color", (1, 0, 0))),
                        stroke_width=layer_dict.get("stroke_width", 2)
                    )

                elif layer_type == LayerType.ANNOTATION:
                    rect = None
                    if "rect" in layer_dict:
                        r = layer_dict["rect"]
                        rect = fitz.Rect(r[0], r[1], r[2], r[3])

                    layer = AnnotationLayer(
                        id=layer_dict["id"],
                        layer_type=layer_type,
                        page_num=page_num,
                        visible=layer_dict.get("visible", True),
                        locked=layer_dict.get("locked", False),
                        z_index=layer_dict.get("z_index", 0),
                        annot_type=layer_dict.get("annot_type", "highlight"),
                        rect=rect,
                        color=tuple(layer_dict.get("color", (1, 1, 0)))
                    )

                elif layer_type == LayerType.TEXT:
                    rect = None
                    if "rect" in layer_dict:
                        r = layer_dict["rect"]
                        rect = fitz.Rect(r[0], r[1], r[2], r[3])

                    layer = TextLayer(
                        id=layer_dict["id"],
                        layer_type=layer_type,
                        page_num=page_num,
                        visible=layer_dict.get("visible", True),
                        locked=layer_dict.get("locked", False),
                        z_index=layer_dict.get("z_index", 0),
                        rect=rect,
                        text=layer_dict.get("text", ""),
                        font_name=layer_dict.get("font_name", "helv"),
                        font_size=layer_dict.get("font_size", 12),
                        color=tuple(layer_dict.get("color", (0, 0, 0)))
                    )
                else:
                    continue

                self.add_layer(layer)