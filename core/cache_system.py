"""
Cache System for PDF Editor Pro v3.0
Optimized caching with lazy loading and background rendering
"""

import threading
from typing import Dict, Optional, Tuple, List, Callable
from dataclasses import dataclass
from collections import OrderedDict
import time
import fitz
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor


@dataclass
class CacheEntry:
    """A cached item with metadata"""
    data: any
    timestamp: float
    size_bytes: int
    page_num: int
    zoom: float = 1.0


class LRUCache:
    """Least Recently Used Cache with size limit - Thread-safe"""

    def __init__(self, max_size_mb: int = 100):
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def _make_key(self, page_num: int, zoom: float, suffix: str = "") -> str:
        return f"{page_num}_{zoom:.2f}_{suffix}"

    def get(self, page_num: int, zoom: float, suffix: str = "") -> Optional[any]:
        key = self._make_key(page_num, zoom, suffix)
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key].data
            self.misses += 1
            return None

    def put(self, page_num: int, zoom: float, data: any, size_bytes: int, suffix: str = ""):
        key = self._make_key(page_num, zoom, suffix)
        with self.lock:
            if key in self.cache:
                self.current_size -= self.cache[key].size_bytes
                del self.cache[key]
            while self.current_size + size_bytes > self.max_size_bytes and self.cache:
                oldest_key, oldest_entry = self.cache.popitem(last=False)
                self.current_size -= oldest_entry.size_bytes
            self.cache[key] = CacheEntry(
                data=data, timestamp=time.time(), size_bytes=size_bytes,
                page_num=page_num, zoom=zoom
            )
            self.current_size += size_bytes

    def invalidate_page(self, page_num: int):
        with self.lock:
            keys_to_remove = [k for k, v in self.cache.items() if v.page_num == page_num]
            for key in keys_to_remove:
                self.current_size -= self.cache[key].size_bytes
                del self.cache[key]

    def invalidate_all(self):
        with self.lock:
            self.cache.clear()
            self.current_size = 0

    def get_stats(self) -> Dict:
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        return {
            "entries": len(self.cache),
            "size_mb": self.current_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "hits": self.hits, "misses": self.misses, "hit_rate": hit_rate
        }


class BackgroundRenderer:
    """Optimized background renderer using ThreadPoolExecutor"""

    def __init__(self, cache: LRUCache, max_workers: int = 4):
        self.cache = cache
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pending = set()
        self.lock = threading.Lock()
        self._doc = None

    def set_document(self, doc: fitz.Document):
        self._doc = doc

    def queue_render(self, page_num: int, zoom: float, callback: Callable = None):
        """Queue a page for background rendering"""
        if self._doc is None:
            return
        key = (page_num, zoom)
        with self.lock:
            if key in self.pending or self.cache.get(page_num, zoom) is not None:
                return
            self.pending.add(key)
        self.executor.submit(self._render_task, page_num, zoom, callback)

    def _render_task(self, page_num: int, zoom: float, callback: Callable):
        try:
            if self._doc and 0 <= page_num < len(self._doc):
                page = self._doc[page_num]
                mat = fitz.Matrix(zoom * 96 / 72, zoom * 96 / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                size_bytes = pix.width * pix.height * 3
                self.cache.put(page_num, zoom, img, size_bytes)
                if callback:
                    callback(page_num, zoom, img)
        except Exception as e:
            pass
        finally:
            with self.lock:
                self.pending.discard((page_num, zoom))

    def shutdown(self):
        self.executor.shutdown(wait=False)


class PageCache:
    """High-level page caching system - Optimized for speed"""

    def __init__(self, max_size_mb: int = 200):
        self.page_cache = LRUCache(max_size_mb=int(max_size_mb * 0.7))
        self.thumbnail_cache = LRUCache(max_size_mb=int(max_size_mb * 0.3))
        self.renderer = BackgroundRenderer(self.page_cache)
        self._doc: Optional[fitz.Document] = None

    def set_document(self, doc: fitz.Document):
        self._doc = doc
        self.renderer.set_document(doc)
        self.invalidate_all()

    def get_page_image(self, page_num: int, zoom: float) -> Optional[Image.Image]:
        cached = self.page_cache.get(page_num, zoom)
        if cached:
            return cached
        if self._doc and 0 <= page_num < len(self._doc):
            page = self._doc[page_num]
            mat = fitz.Matrix(zoom * 96 / 72, zoom * 96 / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            size_bytes = pix.width * pix.height * 3
            self.page_cache.put(page_num, zoom, img, size_bytes)
            return img
        return None

    def get_thumbnail(self, page_num: int, scale: float = 0.15) -> Optional[Image.Image]:
        cached = self.thumbnail_cache.get(page_num, scale, "thumb")
        if cached:
            return cached
        if self._doc and 0 <= page_num < len(self._doc):
            page = self._doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            size_bytes = pix.width * pix.height * 3
            self.thumbnail_cache.put(page_num, scale, img, size_bytes, "thumb")
            return img
        return None

    def prefetch_pages(self, current_page: int, zoom: float, count: int = 3):
        if not self._doc:
            return
        for i in range(1, count + 1):
            if current_page + i < len(self._doc):
                self.renderer.queue_render(current_page + i, zoom)
            if current_page - i >= 0:
                self.renderer.queue_render(current_page - i, zoom)

    def invalidate_page(self, page_num: int):
        self.page_cache.invalidate_page(page_num)
        self.thumbnail_cache.invalidate_page(page_num)

    def invalidate_all(self):
        self.page_cache.invalidate_all()
        self.thumbnail_cache.invalidate_all()

    def get_stats(self) -> Dict:
        return {
            "page_cache": self.page_cache.get_stats(),
            "thumbnail_cache": self.thumbnail_cache.get_stats()
        }

    def shutdown(self):
        self.renderer.shutdown()


class AutoSaveManager:
    """Auto-save functionality to prevent data loss"""

    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self.last_save_time = 0
        self.backup_path: Optional[str] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._doc: Optional[fitz.Document] = None
        self._save_callback: Optional[Callable] = None
        self.modified = False

    def start(self, doc: fitz.Document, backup_path: str, save_callback: Callable = None):
        self._doc = doc
        self.backup_path = backup_path
        self._save_callback = save_callback
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def mark_modified(self):
        self.modified = True

    def _worker(self):
        while self.running:
            time.sleep(1)
            if self.modified and self._doc and self.backup_path:
                current_time = time.time()
                if current_time - self.last_save_time >= self.interval:
                    try:
                        self._doc.save(self.backup_path)
                        self.last_save_time = current_time
                        self.modified = False
                        if self._save_callback:
                            self._save_callback(self.backup_path)
                    except Exception as e:
                        pass

    def recover(self) -> Optional[str]:
        if self.backup_path:
            import os
            if os.path.exists(self.backup_path):
                return self.backup_path
        return None

    def cleanup_backup(self):
        if self.backup_path:
            import os
            if os.path.exists(self.backup_path):
                try:
                    os.remove(self.backup_path)
                except:
                    pass