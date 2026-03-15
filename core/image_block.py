from dataclasses import dataclass
from typing import Tuple
import fitz

@dataclass
class ImageBlock:
    rect: fitz.Rect
    path: str
    page_num: int = 0