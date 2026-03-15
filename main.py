"""
PDF Editor Pro - محرر PDF احترافي
برنامج متقدم لتحرير ملفات PDF مع واجهة رسومية
يدعم: تحرير النصوص، إضافة/حذف نصوص، الصور، التعليقات، الأشكال، والمزيد

Author  : Hayder Odhafa (حيدر عذافة)
GitHub  : https://github.com/Hayder-IRAQ
Version : 1.0
License : MIT
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog, font
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io
import os
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import copy


class Tool(Enum):
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


@dataclass
class TextBlock:
    """كتلة نصية قابلة للتحرير"""
    rect: fitz.Rect
    text: str
    font_name: str = "helv"
    font_size: float = 11
    color: Tuple[float, float, float] = (0, 0, 0)
    page_num: int = 0
    original_spans: List[Dict] = field(default_factory=list)


@dataclass
class Annotation:
    """تعليق توضيحي"""
    type: str
    rect: fitz.Rect
    color: Tuple[float, float, float]
    content: str = ""
    points: List[Tuple[float, float]] = field(default_factory=list)
    page_num: int = 0


class UndoManager:
    """مدير التراجع والإعادة"""
    def __init__(self, max_history: int = 50):
        self.history: List[bytes] = []
        self.future: List[bytes] = []
        self.max_history = max_history

    def save_state(self, doc: fitz.Document):
        if len(self.history) >= self.max_history:
            self.history.pop(0)
        self.history.append(doc.tobytes())
        self.future.clear()

    def undo(self, current_doc: fitz.Document) -> Optional[fitz.Document]:
        if not self.history:
            return None
        self.future.append(current_doc.tobytes())
        state = self.history.pop()
        return fitz.open(stream=state, filetype="pdf")

    def redo(self, current_doc: fitz.Document) -> Optional[fitz.Document]:
        if not self.future:
            return None
        self.history.append(current_doc.tobytes())
        state = self.future.pop()
        return fitz.open(stream=state, filetype="pdf")

    def can_undo(self) -> bool:
        return len(self.history) > 0

    def can_redo(self) -> bool:
        return len(self.future) > 0


class PDFEditorPro:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor Pro - محرر PDF احترافي")
        self.root.geometry("1400x900")
        self.root.configure(bg="#2b2b2b")

        # المتغيرات الأساسية
        self.doc: Optional[fitz.Document] = None
        self.current_page = 0
        self.zoom = 1.0
        self.current_tool = Tool.SELECT
        self.file_path = None
        self.modified = False

        # إعدادات الأدوات
        self.text_color = (0, 0, 0)
        self.highlight_color = (1, 1, 0)
        self.shape_color = (1, 0, 0)
        self.font_size = 12
        self.font_name = "helv"
        self.line_width = 2

        # التحرير
        self.text_blocks: List[TextBlock] = []
        self.annotations: List[Annotation] = []
        self.selected_block: Optional[TextBlock] = None
        self.temp_points: List[Tuple[float, float]] = []
        self.drawing = False
        self.start_pos = None

        # مدير التراجع
        self.undo_manager = UndoManager()

        # الحافظة
        self.clipboard_content = None

        # بناء الواجهة
        self._setup_styles()
        self._create_menu()
        self._create_toolbar()
        self._create_main_area()
        self._create_status_bar()
        self._bind_shortcuts()

    def _setup_styles(self):
        """إعداد أنماط الواجهة"""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Dark.TFrame", background="#2b2b2b")
        style.configure("Dark.TLabel", background="#2b2b2b", foreground="white")
        style.configure("Toolbar.TButton", padding=5)
        style.configure("Tool.TButton", padding=8, width=8)
        style.configure("Active.TButton", background="#4a9eff")

    def _create_menu(self):
        """إنشاء شريط القوائم"""
        menubar = tk.Menu(self.root, bg="#3c3c3c", fg="white")
        self.root.config(menu=menubar)

        # قائمة ملف
        file_menu = tk.Menu(menubar, tearoff=0, bg="#3c3c3c", fg="white")
        menubar.add_cascade(label="ملف", menu=file_menu)
        file_menu.add_command(label="فتح PDF", command=self.open_pdf, accelerator="Ctrl+O")
        file_menu.add_command(label="حفظ", command=self.save_pdf, accelerator="Ctrl+S")
        file_menu.add_command(label="حفظ باسم", command=self.save_as_pdf, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="تصدير كصور", command=self.export_images)
        file_menu.add_command(label="استخراج النص", command=self.extract_text)
        file_menu.add_separator()
        file_menu.add_command(label="خروج", command=self.on_closing)

        # قائمة تحرير
        edit_menu = tk.Menu(menubar, tearoff=0, bg="#3c3c3c", fg="white")
        menubar.add_cascade(label="تحرير", menu=edit_menu)
        edit_menu.add_command(label="تراجع", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="إعادة", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="نسخ", command=self.copy_selection, accelerator="Ctrl+C")
        edit_menu.add_command(label="لصق", command=self.paste_content, accelerator="Ctrl+V")
        edit_menu.add_command(label="حذف", command=self.delete_selection, accelerator="Del")
        edit_menu.add_separator()
        edit_menu.add_command(label="بحث واستبدال", command=self.find_replace, accelerator="Ctrl+H")

        # قائمة صفحة
        page_menu = tk.Menu(menubar, tearoff=0, bg="#3c3c3c", fg="white")
        menubar.add_cascade(label="صفحة", menu=page_menu)
        page_menu.add_command(label="إضافة صفحة", command=self.add_page)
        page_menu.add_command(label="حذف صفحة", command=self.delete_page)
        page_menu.add_command(label="تدوير الصفحة", command=self.rotate_page)
        page_menu.add_separator()
        page_menu.add_command(label="استخراج صفحات", command=self.extract_pages)
        page_menu.add_command(label="دمج PDF", command=self.merge_pdfs)

        # قائمة إدراج
        insert_menu = tk.Menu(menubar, tearoff=0, bg="#3c3c3c", fg="white")
        menubar.add_cascade(label="إدراج", menu=insert_menu)
        insert_menu.add_command(label="نص", command=lambda: self.set_tool(Tool.TEXT))
        insert_menu.add_command(label="صورة", command=self.insert_image)
        insert_menu.add_command(label="تعليق", command=lambda: self.set_tool(Tool.COMMENT))
        insert_menu.add_command(label="رابط", command=lambda: self.set_tool(Tool.LINK))
        insert_menu.add_separator()
        insert_menu.add_command(label="توقيع", command=self.add_signature)
        insert_menu.add_command(label="ختم", command=self.add_stamp)
        insert_menu.add_command(label="علامة مائية", command=self.add_watermark)

        # قائمة عرض
        view_menu = tk.Menu(menubar, tearoff=0, bg="#3c3c3c", fg="white")
        menubar.add_cascade(label="عرض", menu=view_menu)
        view_menu.add_command(label="تكبير", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="تصغير", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="حجم فعلي", command=self.zoom_fit, accelerator="Ctrl+0")

        # قائمة مساعدة
        help_menu = tk.Menu(menubar, tearoff=0, bg="#3c3c3c", fg="white")
        menubar.add_cascade(label="مساعدة", menu=help_menu)
        help_menu.add_command(label="اختصارات لوحة المفاتيح", command=self.show_shortcuts)
        help_menu.add_command(label="حول البرنامج", command=self.show_about)

    def _create_toolbar(self):
        """إنشاء شريط الأدوات"""
        toolbar_frame = ttk.Frame(self.root, style="Dark.TFrame")
        toolbar_frame.pack(fill="x", padx=5, pady=5)

        # أدوات الملف
        file_frame = ttk.LabelFrame(toolbar_frame, text="ملف")
        file_frame.pack(side="left", padx=5)

        ttk.Button(file_frame, text="📂 فتح", command=self.open_pdf).pack(side="left", padx=2)
        ttk.Button(file_frame, text="💾 حفظ", command=self.save_pdf).pack(side="left", padx=2)

        # أدوات التحرير
        edit_frame = ttk.LabelFrame(toolbar_frame, text="تحرير")
        edit_frame.pack(side="left", padx=5)

        self.undo_btn = ttk.Button(edit_frame, text="↩️", command=self.undo, width=3)
        self.undo_btn.pack(side="left", padx=2)
        self.redo_btn = ttk.Button(edit_frame, text="↪️", command=self.redo, width=3)
        self.redo_btn.pack(side="left", padx=2)

        # أدوات التحديد والنص
        tools_frame = ttk.LabelFrame(toolbar_frame, text="أدوات")
        tools_frame.pack(side="left", padx=5)

        self.tool_buttons = {}
        tools = [
            (Tool.SELECT, "👆", "تحديد"),
            (Tool.TEXT, "T", "نص"),
            (Tool.HIGHLIGHT, "🖍️", "تظليل"),
            (Tool.UNDERLINE, "U̲", "تسطير"),
            (Tool.STRIKEOUT, "S̶", "شطب"),
        ]

        for tool, icon, tooltip in tools:
            btn = ttk.Button(tools_frame, text=icon, width=3,
                           command=lambda t=tool: self.set_tool(t))
            btn.pack(side="left", padx=2)
            self.tool_buttons[tool] = btn

        # أدوات الرسم
        draw_frame = ttk.LabelFrame(toolbar_frame, text="رسم")
        draw_frame.pack(side="left", padx=5)

        draw_tools = [
            (Tool.RECTANGLE, "▢", "مستطيل"),
            (Tool.CIRCLE, "○", "دائرة"),
            (Tool.LINE, "╱", "خط"),
            (Tool.ARROW, "→", "سهم"),
            (Tool.FREEHAND, "✏️", "رسم حر"),
            (Tool.ERASER, "🧹", "ممحاة"),
        ]

        for tool, icon, tooltip in draw_tools:
            btn = ttk.Button(draw_frame, text=icon, width=3,
                           command=lambda t=tool: self.set_tool(t))
            btn.pack(side="left", padx=2)
            self.tool_buttons[tool] = btn

        # إعدادات النص
        text_frame = ttk.LabelFrame(toolbar_frame, text="نص")
        text_frame.pack(side="left", padx=5)

        # حجم الخط
        ttk.Label(text_frame, text="حجم:").pack(side="left")
        self.font_size_var = tk.StringVar(value="12")
        font_combo = ttk.Combobox(text_frame, textvariable=self.font_size_var, width=4,
                                  values=["8", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48", "72"])
        font_combo.pack(side="left", padx=2)
        font_combo.bind("<<ComboboxSelected>>", self._on_font_size_change)

        # لون النص
        self.text_color_btn = tk.Button(text_frame, text="  ", bg="black", width=2,
                                        command=self.choose_text_color)
        self.text_color_btn.pack(side="left", padx=5)

        # الألوان
        color_frame = ttk.LabelFrame(toolbar_frame, text="ألوان")
        color_frame.pack(side="left", padx=5)

        ttk.Label(color_frame, text="تظليل:").pack(side="left")
        self.highlight_color_btn = tk.Button(color_frame, text="  ", bg="yellow", width=2,
                                             command=self.choose_highlight_color)
        self.highlight_color_btn.pack(side="left", padx=2)

        ttk.Label(color_frame, text="شكل:").pack(side="left")
        self.shape_color_btn = tk.Button(color_frame, text="  ", bg="red", width=2,
                                         command=self.choose_shape_color)
        self.shape_color_btn.pack(side="left", padx=2)

        # سمك الخط
        ttk.Label(color_frame, text="سمك:").pack(side="left")
        self.line_width_var = tk.StringVar(value="2")
        width_spin = ttk.Spinbox(color_frame, from_=1, to=10, width=3,
                                textvariable=self.line_width_var)
        width_spin.pack(side="left", padx=2)

        # التكبير
        zoom_frame = ttk.LabelFrame(toolbar_frame, text="عرض")
        zoom_frame.pack(side="left", padx=5)

        ttk.Button(zoom_frame, text="−", width=2, command=self.zoom_out).pack(side="left")
        self.zoom_label = ttk.Label(zoom_frame, text="100%", width=5)
        self.zoom_label.pack(side="left", padx=5)
        ttk.Button(zoom_frame, text="+", width=2, command=self.zoom_in).pack(side="left")

    def _create_main_area(self):
        """إنشاء المنطقة الرئيسية"""
        main_frame = ttk.Frame(self.root, style="Dark.TFrame")
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # لوحة الصفحات المصغرة (يسار)
        self.thumbnails_frame = ttk.Frame(main_frame, width=150)
        self.thumbnails_frame.pack(side="left", fill="y", padx=(0, 5))
        self.thumbnails_frame.pack_propagate(False)

        ttk.Label(self.thumbnails_frame, text="الصفحات", style="Dark.TLabel").pack(pady=5)

        self.thumbnails_canvas = tk.Canvas(self.thumbnails_frame, bg="#3c3c3c",
                                          highlightthickness=0, width=140)
        thumbnails_scroll = ttk.Scrollbar(self.thumbnails_frame, orient="vertical",
                                         command=self.thumbnails_canvas.yview)
        self.thumbnails_inner = ttk.Frame(self.thumbnails_canvas)

        self.thumbnails_canvas.configure(yscrollcommand=thumbnails_scroll.set)
        thumbnails_scroll.pack(side="right", fill="y")
        self.thumbnails_canvas.pack(side="left", fill="both", expand=True)
        self.thumbnails_canvas.create_window((0, 0), window=self.thumbnails_inner, anchor="nw")

        self.thumbnails_inner.bind("<Configure>",
            lambda e: self.thumbnails_canvas.configure(scrollregion=self.thumbnails_canvas.bbox("all")))

        # منطقة العرض الرئيسية
        view_frame = ttk.Frame(main_frame)
        view_frame.pack(side="left", fill="both", expand=True)

        # Canvas للعرض مع شريط التمرير
        self.canvas_frame = ttk.Frame(view_frame)
        self.canvas_frame.pack(fill="both", expand=True)

        self.h_scroll = ttk.Scrollbar(self.canvas_frame, orient="horizontal")
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient="vertical")

        self.canvas = tk.Canvas(self.canvas_frame, bg="#404040",
                               xscrollcommand=self.h_scroll.set,
                               yscrollcommand=self.v_scroll.set,
                               highlightthickness=0)

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # ربط الأحداث
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)

        # شريط التنقل
        nav_frame = ttk.Frame(view_frame)
        nav_frame.pack(fill="x", pady=5)

        ttk.Button(nav_frame, text="◀◀", command=self.first_page, width=4).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="◀", command=self.prev_page, width=3).pack(side="left", padx=2)

        self.page_entry = ttk.Entry(nav_frame, width=5, justify="center")
        self.page_entry.pack(side="left", padx=5)
        self.page_entry.bind("<Return>", self._on_page_entry)

        self.page_label = ttk.Label(nav_frame, text="/ 0")
        self.page_label.pack(side="left")

        ttk.Button(nav_frame, text="▶", command=self.next_page, width=3).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="▶▶", command=self.last_page, width=4).pack(side="left", padx=2)

        # لوحة الخصائص (يمين)
        self.properties_frame = ttk.Frame(main_frame, width=200)
        self.properties_frame.pack(side="right", fill="y", padx=(5, 0))
        self.properties_frame.pack_propagate(False)

        ttk.Label(self.properties_frame, text="الخصائص", style="Dark.TLabel").pack(pady=5)

        # محتوى لوحة الخصائص
        self.props_content = ttk.Frame(self.properties_frame)
        self.props_content.pack(fill="both", expand=True, padx=5)

    def _create_status_bar(self):
        """إنشاء شريط الحالة"""
        self.status_bar = ttk.Frame(self.root, style="Dark.TFrame")
        self.status_bar.pack(fill="x", side="bottom")

        self.status_label = ttk.Label(self.status_bar, text="جاهز", style="Dark.TLabel")
        self.status_label.pack(side="left", padx=10)

        self.tool_label = ttk.Label(self.status_bar, text="أداة: تحديد", style="Dark.TLabel")
        self.tool_label.pack(side="right", padx=10)

        self.pos_label = ttk.Label(self.status_bar, text="", style="Dark.TLabel")
        self.pos_label.pack(side="right", padx=10)

    def _bind_shortcuts(self):
        """ربط اختصارات لوحة المفاتيح"""
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-s>", lambda e: self.save_pdf())
        self.root.bind("<Control-S>", lambda e: self.save_as_pdf())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-c>", lambda e: self.copy_selection())
        self.root.bind("<Control-v>", lambda e: self.paste_content())
        self.root.bind("<Delete>", lambda e: self.delete_selection())
        self.root.bind("<Control-h>", lambda e: self.find_replace())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.zoom_fit())
        self.root.bind("<Prior>", lambda e: self.prev_page())
        self.root.bind("<Next>", lambda e: self.next_page())
        self.root.bind("<Home>", lambda e: self.first_page())
        self.root.bind("<End>", lambda e: self.last_page())
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # =============== وظائف الملف ===============

    def open_pdf(self):
        """فتح ملف PDF"""
        if self.modified:
            if not messagebox.askyesno("تأكيد", "هناك تغييرات غير محفوظة. هل تريد المتابعة؟"):
                return

        file_path = filedialog.askopenfilename(
            title="اختر ملف PDF",
            filetypes=[("PDF files", "*.pdf")]
        )

        if file_path:
            try:
                self.doc = fitz.open(file_path)
                self.file_path = file_path
                self.current_page = 0
                self.modified = False
                self.undo_manager = UndoManager()

                self._update_thumbnails()
                self._render_page()
                self._update_page_info()
                self.status_label.config(text=f"تم فتح: {os.path.basename(file_path)}")
                self.root.title(f"PDF Editor Pro - {os.path.basename(file_path)}")

            except Exception as e:
                messagebox.showerror("خطأ", f"فشل في فتح الملف:\n{str(e)}")

    def save_pdf(self):
        """حفظ الملف"""
        if not self.doc:
            return

        if self.file_path:
            try:
                # حفظ في ملف مؤقت أولاً
                temp_path = self.file_path + ".tmp"
                self.doc.save(temp_path)
                self.doc.close()

                # استبدال الملف الأصلي
                os.replace(temp_path, self.file_path)
                self.doc = fitz.open(self.file_path)

                self.modified = False
                self.status_label.config(text="تم الحفظ بنجاح")
            except Exception as e:
                messagebox.showerror("خطأ", f"فشل في الحفظ:\n{str(e)}")
        else:
            self.save_as_pdf()

    def save_as_pdf(self):
        """حفظ باسم جديد"""
        if not self.doc:
            return

        file_path = filedialog.asksaveasfilename(
            title="حفظ باسم",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )

        if file_path:
            try:
                self.doc.save(file_path)
                self.file_path = file_path
                self.modified = False
                self.status_label.config(text=f"تم الحفظ: {os.path.basename(file_path)}")
                self.root.title(f"PDF Editor Pro - {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("خطأ", f"فشل في الحفظ:\n{str(e)}")

    def export_images(self):
        """تصدير الصفحات كصور"""
        if not self.doc:
            messagebox.showwarning("تنبيه", "لا يوجد ملف مفتوح")
            return

        folder = filedialog.askdirectory(title="اختر مجلد للتصدير")
        if not folder:
            return

        try:
            for i, page in enumerate(self.doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = os.path.join(folder, f"page_{i+1}.png")
                pix.save(img_path)

            messagebox.showinfo("نجاح", f"تم تصدير {len(self.doc)} صفحة")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def extract_text(self):
        """استخراج النص من PDF"""
        if not self.doc:
            messagebox.showwarning("تنبيه", "لا يوجد ملف مفتوح")
            return

        file_path = filedialog.asksaveasfilename(
            title="حفظ النص",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )

        if file_path:
            try:
                text = ""
                for page in self.doc:
                    text += page.get_text() + "\n\n"

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)

                messagebox.showinfo("نجاح", "تم استخراج النص بنجاح")
            except Exception as e:
                messagebox.showerror("خطأ", str(e))

    # =============== وظائف التحرير ===============

    def undo(self):
        """تراجع"""
        if self.doc and self.undo_manager.can_undo():
            new_doc = self.undo_manager.undo(self.doc)
            if new_doc:
                self.doc.close()
                self.doc = new_doc
                self._render_page()
                self._update_thumbnails()

    def redo(self):
        """إعادة"""
        if self.doc and self.undo_manager.can_redo():
            new_doc = self.undo_manager.redo(self.doc)
            if new_doc:
                self.doc.close()
                self.doc = new_doc
                self._render_page()
                self._update_thumbnails()

    def copy_selection(self):
        """نسخ المحدد"""
        if self.selected_block:
            self.clipboard_content = {
                "type": "text",
                "text": self.selected_block.text,
                "font_size": self.selected_block.font_size,
                "color": self.selected_block.color
            }
            self.status_label.config(text="تم النسخ")

    def paste_content(self):
        """لصق المحتوى"""
        if self.clipboard_content and self.doc:
            self.set_tool(Tool.TEXT)
            self.status_label.config(text="انقر لتحديد موقع اللصق")

    def delete_selection(self):
        """حذف المحدد"""
        if self.selected_block and self.doc:
            self._save_state()
            page = self.doc[self.current_page]

            # إنشاء مستطيل أبيض لتغطية النص
            rect = self.selected_block.rect
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

            self.selected_block = None
            self._render_page()
            self.modified = True

    def find_replace(self):
        """بحث واستبدال"""
        if not self.doc:
            messagebox.showwarning("تنبيه", "لا يوجد ملف مفتوح")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("بحث واستبدال")
        dialog.geometry("400x200")
        dialog.transient(self.root)

        ttk.Label(dialog, text="بحث عن:").pack(pady=5)
        find_entry = ttk.Entry(dialog, width=40)
        find_entry.pack(pady=5)

        ttk.Label(dialog, text="استبدال بـ:").pack(pady=5)
        replace_entry = ttk.Entry(dialog, width=40)
        replace_entry.pack(pady=5)

        def do_replace():
            find_text = find_entry.get()
            replace_text = replace_entry.get()

            if not find_text:
                return

            self._save_state()
            count = 0

            for page_num, page in enumerate(self.doc):
                text_instances = page.search_for(find_text)

                for inst in text_instances:
                    # تغطية النص القديم
                    page.draw_rect(inst, color=(1, 1, 1), fill=(1, 1, 1))

                    # إضافة النص الجديد
                    page.insert_text(
                        (inst.x0, inst.y1),
                        replace_text,
                        fontsize=11,
                        color=(0, 0, 0)
                    )
                    count += 1

            if count > 0:
                self._render_page()
                self._update_thumbnails()
                self.modified = True
                messagebox.showinfo("نجاح", f"تم استبدال {count} مطابقة")
            else:
                messagebox.showinfo("نتيجة", "لم يتم العثور على النص")

            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="استبدال الكل", command=do_replace).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="إلغاء", command=dialog.destroy).pack(side="left", padx=10)

    # =============== وظائف الصفحة ===============

    def add_page(self):
        """إضافة صفحة جديدة"""
        if not self.doc:
            messagebox.showwarning("تنبيه", "لا يوجد ملف مفتوح")
            return

        self._save_state()

        # إضافة صفحة بنفس حجم الصفحة الأولى
        first_page = self.doc[0]
        rect = first_page.rect
        self.doc.insert_page(-1, width=rect.width, height=rect.height)

        self._update_thumbnails()
        self.last_page()
        self.modified = True

    def delete_page(self):
        """حذف الصفحة الحالية"""
        if not self.doc or len(self.doc) <= 1:
            messagebox.showwarning("تنبيه", "لا يمكن حذف الصفحة الوحيدة")
            return

        if messagebox.askyesno("تأكيد", f"هل تريد حذف الصفحة {self.current_page + 1}؟"):
            self._save_state()
            self.doc.delete_page(self.current_page)

            if self.current_page >= len(self.doc):
                self.current_page = len(self.doc) - 1

            self._update_thumbnails()
            self._render_page()
            self._update_page_info()
            self.modified = True

    def rotate_page(self):
        """تدوير الصفحة"""
        if not self.doc:
            return

        self._save_state()
        page = self.doc[self.current_page]
        page.set_rotation((page.rotation + 90) % 360)

        self._render_page()
        self._update_thumbnails()
        self.modified = True

    def extract_pages(self):
        """استخراج صفحات محددة"""
        if not self.doc:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("استخراج صفحات")
        dialog.geometry("300x150")

        ttk.Label(dialog, text=f"إجمالي الصفحات: {len(self.doc)}").pack(pady=5)
        ttk.Label(dialog, text="أدخل أرقام الصفحات (مثال: 1,3,5-8):").pack(pady=5)

        entry = ttk.Entry(dialog, width=30)
        entry.pack(pady=5)

        def do_extract():
            try:
                pages_str = entry.get()
                pages = []

                for part in pages_str.split(","):
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        pages.extend(range(start - 1, end))
                    else:
                        pages.append(int(part.strip()) - 1)

                output_path = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf")]
                )

                if output_path:
                    new_doc = fitz.open()
                    for p in pages:
                        if 0 <= p < len(self.doc):
                            new_doc.insert_pdf(self.doc, from_page=p, to_page=p)
                    new_doc.save(output_path)
                    new_doc.close()
                    messagebox.showinfo("نجاح", "تم استخراج الصفحات بنجاح")
                    dialog.destroy()

            except Exception as e:
                messagebox.showerror("خطأ", str(e))

        ttk.Button(dialog, text="استخراج", command=do_extract).pack(pady=10)

    def merge_pdfs(self):
        """دمج ملفات PDF"""
        files = filedialog.askopenfilenames(
            title="اختر ملفات PDF للدمج",
            filetypes=[("PDF files", "*.pdf")]
        )

        if not files:
            return

        output_path = filedialog.asksaveasfilename(
            title="حفظ الملف المدمج",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )

        if output_path:
            try:
                merged = fitz.open()
                for pdf_file in files:
                    doc = fitz.open(pdf_file)
                    merged.insert_pdf(doc)
                    doc.close()

                merged.save(output_path)
                merged.close()
                messagebox.showinfo("نجاح", "تم دمج الملفات بنجاح")

            except Exception as e:
                messagebox.showerror("خطأ", str(e))

    # =============== وظائف الإدراج ===============

    def insert_image(self):
        """إدراج صورة"""
        if not self.doc:
            messagebox.showwarning("تنبيه", "لا يوجد ملف مفتوح")
            return

        img_path = filedialog.askopenfilename(
            title="اختر صورة",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )

        if img_path:
            self._save_state()
            page = self.doc[self.current_page]

            # إدراج الصورة في منتصف الصفحة
            rect = page.rect
            img_rect = fitz.Rect(rect.width/4, rect.height/4,
                                rect.width*3/4, rect.height*3/4)

            page.insert_image(img_rect, filename=img_path)

            self._render_page()
            self.modified = True
            self.status_label.config(text="تم إدراج الصورة")

    def add_signature(self):
        """إضافة توقيع"""
        if not self.doc:
            return

        # نافذة رسم التوقيع
        sig_window = tk.Toplevel(self.root)
        sig_window.title("ارسم توقيعك")
        sig_window.geometry("400x200")

        canvas = tk.Canvas(sig_window, bg="white", width=380, height=150)
        canvas.pack(pady=10)

        points = []

        def draw(event):
            x, y = event.x, event.y
            if points:
                canvas.create_line(points[-1][0], points[-1][1], x, y, width=2)
            points.append((x, y))

        def clear():
            canvas.delete("all")
            points.clear()

        def save_sig():
            if not points:
                return

            self._save_state()
            page = self.doc[self.current_page]

            # رسم التوقيع على الصفحة
            shape = page.new_shape()
            for i in range(1, len(points)):
                shape.draw_line(
                    fitz.Point(points[i-1][0] + 100, page.rect.height - 100 + points[i-1][1]),
                    fitz.Point(points[i][0] + 100, page.rect.height - 100 + points[i][1])
                )
            shape.finish(color=(0, 0, 0.5), width=1.5)
            shape.commit()

            self._render_page()
            self.modified = True
            sig_window.destroy()

        canvas.bind("<B1-Motion>", draw)

        btn_frame = ttk.Frame(sig_window)
        btn_frame.pack()
        ttk.Button(btn_frame, text="مسح", command=clear).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="إدراج", command=save_sig).pack(side="left", padx=5)

    def add_stamp(self):
        """إضافة ختم"""
        if not self.doc:
            return

        stamps = ["مسودة", "سري", "نهائي", "مرفوض", "موافق", "عاجل"]

        dialog = tk.Toplevel(self.root)
        dialog.title("اختر ختم")
        dialog.geometry("200x300")

        for stamp in stamps:
            ttk.Button(dialog, text=stamp,
                      command=lambda s=stamp: self._insert_stamp(s, dialog)).pack(pady=5)

    def _insert_stamp(self, text, dialog):
        """إدراج الختم"""
        self._save_state()
        page = self.doc[self.current_page]

        # إضافة الختم كنص كبير مائل
        rect = page.rect
        page.insert_text(
            (rect.width/3, rect.height/2),
            text,
            fontsize=72,
            color=(1, 0, 0),
            rotate=45
        )

        self._render_page()
        self.modified = True
        dialog.destroy()

    def add_watermark(self):
        """إضافة علامة مائية"""
        if not self.doc:
            return

        text = simpledialog.askstring("علامة مائية", "أدخل نص العلامة المائية:")
        if not text:
            return

        self._save_state()

        for page in self.doc:
            rect = page.rect
            # إضافة نص شفاف مائل
            page.insert_text(
                (rect.width/4, rect.height/2),
                text,
                fontsize=60,
                color=(0.8, 0.8, 0.8),
                rotate=45
            )

        self._render_page()
        self._update_thumbnails()
        self.modified = True
        self.status_label.config(text="تم إضافة العلامة المائية")

    # =============== وظائف العرض ===============

    def _render_page(self):
        """عرض الصفحة الحالية"""
        if not self.doc:
            return

        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom * 1.5, self.zoom * 1.5)
        pix = page.get_pixmap(matrix=mat)

        # تحويل إلى صورة PIL
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.current_image = ImageTk.PhotoImage(img)

        # عرض على Canvas
        self.canvas.delete("all")
        self.canvas.create_image(pix.width/2 + 20, pix.height/2 + 20,
                                image=self.current_image, tags="page")

        # تحديث منطقة التمرير
        self.canvas.configure(scrollregion=(0, 0, pix.width + 40, pix.height + 40))

        # تحديث معلومات الصفحة
        self._update_page_info()

    def _update_thumbnails(self):
        """تحديث الصور المصغرة"""
        # مسح الصور القديمة
        for widget in self.thumbnails_inner.winfo_children():
            widget.destroy()

        if not self.doc:
            return

        self.thumbnail_images = []

        for i, page in enumerate(self.doc):
            frame = ttk.Frame(self.thumbnails_inner)
            frame.pack(pady=5)

            # إنشاء صورة مصغرة
            pix = page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)
            self.thumbnail_images.append(photo)

            # زر الصورة المصغرة
            btn = tk.Button(frame, image=photo, relief="raised" if i == self.current_page else "flat",
                           command=lambda p=i: self._goto_page(p))
            btn.pack()

            ttk.Label(frame, text=str(i + 1)).pack()

    def _update_page_info(self):
        """تحديث معلومات الصفحة"""
        if self.doc:
            self.page_entry.delete(0, tk.END)
            self.page_entry.insert(0, str(self.current_page + 1))
            self.page_label.config(text=f"/ {len(self.doc)}")

    def _goto_page(self, page_num):
        """الانتقال إلى صفحة محددة"""
        if self.doc and 0 <= page_num < len(self.doc):
            self.current_page = page_num
            self._render_page()
            self._update_thumbnails()

    def first_page(self):
        self._goto_page(0)

    def prev_page(self):
        self._goto_page(self.current_page - 1)

    def next_page(self):
        self._goto_page(self.current_page + 1)

    def last_page(self):
        if self.doc:
            self._goto_page(len(self.doc) - 1)

    def _on_page_entry(self, event):
        try:
            page = int(self.page_entry.get()) - 1
            self._goto_page(page)
        except ValueError:
            pass

    def zoom_in(self):
        self.zoom = min(self.zoom * 1.2, 5.0)
        self.zoom_label.config(text=f"{int(self.zoom * 100)}%")
        self._render_page()

    def zoom_out(self):
        self.zoom = max(self.zoom / 1.2, 0.2)
        self.zoom_label.config(text=f"{int(self.zoom * 100)}%")
        self._render_page()

    def zoom_fit(self):
        self.zoom = 1.0
        self.zoom_label.config(text="100%")
        self._render_page()

    # =============== معالجة الأحداث ===============

    def set_tool(self, tool: Tool):
        """تعيين الأداة الحالية"""
        self.current_tool = tool
        self.tool_label.config(text=f"أداة: {tool.value}")

        # تحديث مظهر الأزرار
        for t, btn in self.tool_buttons.items():
            if t == tool:
                btn.state(['pressed'])
            else:
                btn.state(['!pressed'])

    def _on_canvas_click(self, event):
        """معالجة النقر على Canvas"""
        if not self.doc:
            return

        # تحويل إحداثيات الشاشة إلى إحداثيات PDF
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # حساب الإحداثيات على الصفحة
        scale = self.zoom * 1.5
        pdf_x = (canvas_x - 20) / scale
        pdf_y = (canvas_y - 20) / scale

        self.start_pos = (pdf_x, pdf_y)
        self.drawing = True

        if self.current_tool == Tool.TEXT:
            self._start_text_edit(pdf_x, pdf_y)
        elif self.current_tool == Tool.FREEHAND:
            self.temp_points = [(pdf_x, pdf_y)]
        elif self.current_tool == Tool.SELECT:
            self._try_select_text(pdf_x, pdf_y)

    def _on_canvas_drag(self, event):
        """معالجة السحب على Canvas"""
        if not self.drawing or not self.doc:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        scale = self.zoom * 1.5
        pdf_x = (canvas_x - 20) / scale
        pdf_y = (canvas_y - 20) / scale

        if self.current_tool == Tool.FREEHAND:
            self.temp_points.append((pdf_x, pdf_y))
            # رسم مؤقت على Canvas
            if len(self.temp_points) >= 2:
                p1 = self.temp_points[-2]
                p2 = self.temp_points[-1]
                self.canvas.create_line(
                    p1[0] * scale + 20, p1[1] * scale + 20,
                    p2[0] * scale + 20, p2[1] * scale + 20,
                    fill=self._rgb_to_hex(self.shape_color),
                    width=int(self.line_width_var.get()),
                    tags="temp"
                )

    def _on_canvas_release(self, event):
        """معالجة إفلات الزر"""
        if not self.drawing or not self.doc:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        scale = self.zoom * 1.5
        pdf_x = (canvas_x - 20) / scale
        pdf_y = (canvas_y - 20) / scale

        self.drawing = False

        if self.current_tool in [Tool.RECTANGLE, Tool.CIRCLE, Tool.LINE, Tool.ARROW]:
            self._draw_shape(self.start_pos, (pdf_x, pdf_y))
        elif self.current_tool == Tool.FREEHAND and self.temp_points:
            self._draw_freehand()
        elif self.current_tool == Tool.HIGHLIGHT:
            self._add_highlight(self.start_pos, (pdf_x, pdf_y))
        elif self.current_tool == Tool.UNDERLINE:
            self._add_underline(self.start_pos, (pdf_x, pdf_y))
        elif self.current_tool == Tool.STRIKEOUT:
            self._add_strikeout(self.start_pos, (pdf_x, pdf_y))

        self.temp_points = []
        self.canvas.delete("temp")

    def _on_canvas_double_click(self, event):
        """معالجة النقر المزدوج"""
        if not self.doc:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        scale = self.zoom * 1.5
        pdf_x = (canvas_x - 20) / scale
        pdf_y = (canvas_y - 20) / scale

        # محاولة تحديد كتلة نصية للتحرير
        self._start_text_edit(pdf_x, pdf_y)

    def _on_mouse_wheel(self, event):
        """معالجة عجلة الماوس"""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    # =============== وظائف الرسم والتحرير ===============

    def _save_state(self):
        """حفظ الحالة للتراجع"""
        if self.doc:
            self.undo_manager.save_state(self.doc)

    def _start_text_edit(self, x, y):
        """بدء تحرير النص"""
        page = self.doc[self.current_page]

        # البحث عن النص في الموقع
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # نص
                bbox = block.get("bbox", [0, 0, 0, 0])
                rect = fitz.Rect(bbox)

                if rect.contains(fitz.Point(x, y)):
                    # وجدنا كتلة نصية
                    self._show_text_editor(block, rect)
                    return

        # إذا لم نجد نصاً، نضيف نصاً جديداً
        self._add_new_text(x, y)

    def _show_text_editor(self, block, rect):
        """عرض محرر النص"""
        # استخراج النص الحالي
        text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "")
            text += "\n"

        # نافذة التحرير
        editor = tk.Toplevel(self.root)
        editor.title("تحرير النص")
        editor.geometry("500x300")

        # إطار الأدوات
        tools_frame = ttk.Frame(editor)
        tools_frame.pack(fill="x", padx=5, pady=5)

        # حجم الخط
        ttk.Label(tools_frame, text="الحجم:").pack(side="left")
        size_var = tk.StringVar(value=str(int(self.font_size)))
        size_combo = ttk.Combobox(tools_frame, textvariable=size_var, width=4,
                                  values=["8", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32"])
        size_combo.pack(side="left", padx=5)

        # لون النص
        color_btn = tk.Button(tools_frame, text="اللون", width=6,
                             command=lambda: self._choose_edit_color(color_btn))
        color_btn.pack(side="left", padx=5)
        color_btn.color = self.text_color

        # منطقة النص
        text_widget = tk.Text(editor, wrap="word", font=("Arial", 12))
        text_widget.pack(fill="both", expand=True, padx=5, pady=5)
        text_widget.insert("1.0", text.strip())

        def apply_changes():
            new_text = text_widget.get("1.0", "end-1c")
            new_size = float(size_var.get())
            new_color = color_btn.color

            self._save_state()
            page = self.doc[self.current_page]

            # تغطية النص القديم
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

            # إضافة النص الجديد
            text_point = fitz.Point(rect.x0, rect.y0 + new_size)
            page.insert_text(
                text_point,
                new_text,
                fontsize=new_size,
                color=new_color
            )

            self._render_page()
            self.modified = True
            editor.destroy()

        btn_frame = ttk.Frame(editor)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="تطبيق", command=apply_changes).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="إلغاء", command=editor.destroy).pack(side="left", padx=10)

    def _choose_edit_color(self, btn):
        """اختيار لون للتحرير"""
        color = colorchooser.askcolor(title="اختر لون النص")
        if color[0]:
            btn.color = tuple(c/255 for c in color[0])
            btn.configure(bg=color[1])

    def _add_new_text(self, x, y):
        """إضافة نص جديد"""
        text = simpledialog.askstring("نص جديد", "أدخل النص:")
        if not text:
            return

        self._save_state()
        page = self.doc[self.current_page]

        page.insert_text(
            fitz.Point(x, y),
            text,
            fontsize=float(self.font_size_var.get()),
            color=self.text_color
        )

        self._render_page()
        self.modified = True

    def _try_select_text(self, x, y):
        """محاولة تحديد نص"""
        page = self.doc[self.current_page]
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                bbox = block.get("bbox", [0, 0, 0, 0])
                rect = fitz.Rect(bbox)

                if rect.contains(fitz.Point(x, y)):
                    self.selected_block = TextBlock(
                        rect=rect,
                        text="".join(span.get("text", "")
                                   for line in block.get("lines", [])
                                   for span in line.get("spans", [])),
                        page_num=self.current_page
                    )

                    # رسم إطار التحديد
                    scale = self.zoom * 1.5
                    self.canvas.delete("selection")
                    self.canvas.create_rectangle(
                        rect.x0 * scale + 20, rect.y0 * scale + 20,
                        rect.x1 * scale + 20, rect.y1 * scale + 20,
                        outline="blue", width=2, tags="selection"
                    )
                    return

        self.selected_block = None
        self.canvas.delete("selection")

    def _draw_shape(self, start, end):
        """رسم شكل"""
        self._save_state()
        page = self.doc[self.current_page]
        shape = page.new_shape()

        rect = fitz.Rect(start[0], start[1], end[0], end[1])
        width = float(self.line_width_var.get())

        if self.current_tool == Tool.RECTANGLE:
            shape.draw_rect(rect)
        elif self.current_tool == Tool.CIRCLE:
            shape.draw_oval(rect)
        elif self.current_tool == Tool.LINE:
            shape.draw_line(fitz.Point(start), fitz.Point(end))
        elif self.current_tool == Tool.ARROW:
            shape.draw_line(fitz.Point(start), fitz.Point(end))
            # رسم رأس السهم
            import math
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            arrow_len = 15
            arrow_angle = math.pi / 6

            p1 = fitz.Point(
                end[0] - arrow_len * math.cos(angle - arrow_angle),
                end[1] - arrow_len * math.sin(angle - arrow_angle)
            )
            p2 = fitz.Point(
                end[0] - arrow_len * math.cos(angle + arrow_angle),
                end[1] - arrow_len * math.sin(angle + arrow_angle)
            )
            shape.draw_line(fitz.Point(end), p1)
            shape.draw_line(fitz.Point(end), p2)

        shape.finish(color=self.shape_color, width=width)
        shape.commit()

        self._render_page()
        self.modified = True

    def _draw_freehand(self):
        """رسم حر"""
        if len(self.temp_points) < 2:
            return

        self._save_state()
        page = self.doc[self.current_page]
        shape = page.new_shape()

        for i in range(1, len(self.temp_points)):
            shape.draw_line(
                fitz.Point(self.temp_points[i-1]),
                fitz.Point(self.temp_points[i])
            )

        shape.finish(color=self.shape_color, width=float(self.line_width_var.get()))
        shape.commit()

        self._render_page()
        self.modified = True

    def _add_highlight(self, start, end):
        """إضافة تظليل"""
        self._save_state()
        page = self.doc[self.current_page]

        rect = fitz.Rect(start[0], start[1], end[0], end[1])
        annot = page.add_highlight_annot(rect)
        annot.set_colors(stroke=self.highlight_color)
        annot.update()

        self._render_page()
        self.modified = True

    def _add_underline(self, start, end):
        """إضافة تسطير"""
        self._save_state()
        page = self.doc[self.current_page]

        rect = fitz.Rect(start[0], start[1], end[0], end[1])
        annot = page.add_underline_annot(rect)
        annot.update()

        self._render_page()
        self.modified = True

    def _add_strikeout(self, start, end):
        """إضافة شطب"""
        self._save_state()
        page = self.doc[self.current_page]

        rect = fitz.Rect(start[0], start[1], end[0], end[1])
        annot = page.add_strikeout_annot(rect)
        annot.update()

        self._render_page()
        self.modified = True

    # =============== وظائف مساعدة ===============

    def _rgb_to_hex(self, rgb):
        """تحويل RGB إلى Hex"""
        return "#{:02x}{:02x}{:02x}".format(
            int(rgb[0] * 255),
            int(rgb[1] * 255),
            int(rgb[2] * 255)
        )

    def _on_font_size_change(self, event):
        """تغيير حجم الخط"""
        try:
            self.font_size = float(self.font_size_var.get())
        except ValueError:
            pass

    def choose_text_color(self):
        """اختيار لون النص"""
        color = colorchooser.askcolor(title="اختر لون النص")
        if color[0]:
            self.text_color = tuple(c/255 for c in color[0])
            self.text_color_btn.configure(bg=color[1])

    def choose_highlight_color(self):
        """اختيار لون التظليل"""
        color = colorchooser.askcolor(title="اختر لون التظليل")
        if color[0]:
            self.highlight_color = tuple(c/255 for c in color[0])
            self.highlight_color_btn.configure(bg=color[1])

    def choose_shape_color(self):
        """اختيار لون الشكل"""
        color = colorchooser.askcolor(title="اختر لون الشكل")
        if color[0]:
            self.shape_color = tuple(c/255 for c in color[0])
            self.shape_color_btn.configure(bg=color[1])

    def show_shortcuts(self):
        """عرض اختصارات لوحة المفاتيح"""
        shortcuts = """
اختصارات لوحة المفاتيح:

Ctrl+O     فتح ملف
Ctrl+S     حفظ
Ctrl+Z     تراجع
Ctrl+Y     إعادة
Ctrl+C     نسخ
Ctrl+V     لصق
Delete     حذف
Ctrl+H     بحث واستبدال
Ctrl++     تكبير
Ctrl+-     تصغير
Ctrl+0     حجم فعلي
Page Up    الصفحة السابقة
Page Down  الصفحة التالية
Home       الصفحة الأولى
End        الصفحة الأخيرة
        """
        messagebox.showinfo("اختصارات لوحة المفاتيح", shortcuts)

    def show_about(self):
        """عرض معلومات البرنامج"""
        about = """
PDF Editor Pro
محرر PDF احترافي

الإصدار: 1.0

الميزات:
• تحرير النصوص
• إضافة وحذف النصوص
• رسم الأشكال
• التظليل والتسطير
• إدراج الصور
• دمج وتقسيم الملفات
• التوقيعات والأختام
• العلامات المائية

تم التطوير باستخدام:
Python + PyMuPDF + Tkinter
        """
        messagebox.showinfo("حول البرنامج", about)

    def on_closing(self):
        """معالجة الإغلاق"""
        if self.modified:
            result = messagebox.askyesnocancel(
                "حفظ التغييرات",
                "هناك تغييرات غير محفوظة. هل تريد الحفظ؟"
            )
            if result is None:  # إلغاء
                return
            elif result:  # نعم
                self.save_pdf()

        if self.doc:
            self.doc.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFEditorPro(root)
    root.mainloop()