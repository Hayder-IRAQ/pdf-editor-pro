"""
PDF Editor Pro v3.0 - Modern Edition
Professional PDF Editor with:
- Modern dark theme UI
- Tooltips for all buttons
- Fast text editing
- Optimized image handling
- RTL language support

Author  : Hayder Odhafa (حيدر عذافة)
GitHub  : https://github.com/Hayder-IRAQ
Version : 3.0
License : MIT
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from PIL import Image, ImageTk
import os
import sys
import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.pdf_engine import PDFEngine
from core.languages import get_text, get_available_languages
from core.tools import Tool, DEFAULT_COLORS, FONT_SIZES, TOOL_TOOLTIPS
from core.fonts import FontManager


class ToolTip:
    """Modern tooltip class"""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.id = None

        widget.bind('<Enter>', self.schedule)
        widget.bind('<Leave>', self.hide)
        widget.bind('<ButtonPress>', self.hide)

    def schedule(self, event=None):
        self.hide()
        self.id = self.widget.after(self.delay, self.show)

    def show(self, event=None):
        if self.tip_window:
            return

        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        # Modern tooltip styling
        frame = tk.Frame(tw, bg="#333333", bd=1, relief="solid")
        frame.pack()

        label = tk.Label(
            frame, text=self.text, bg="#333333", fg="#ffffff",
            font=("Segoe UI", 9), padx=8, pady=4
        )
        label.pack()

        # Adjust position to center
        tw.update_idletasks()
        tw_width = tw.winfo_width()
        tw.wm_geometry(f"+{x - tw_width // 2}+{y}")

    def hide(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class ModernButton(tk.Button):
    """Modern styled button with hover effects"""

    def __init__(self, parent, **kwargs):
        self.tooltip_text = kwargs.pop('tooltip', None)
        self.bg_color = kwargs.pop('bg', '#3c3c3c')
        self.hover_color = kwargs.pop('hover_bg', '#505050')
        self.active_color = kwargs.pop('active_bg', '#4a9eff')

        super().__init__(
            parent,
            bg=self.bg_color,
            fg='white',
            activebackground=self.active_color,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            font=('Segoe UI', 10),
            **kwargs
        )

        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

        if self.tooltip_text:
            ToolTip(self, self.tooltip_text)

    def _on_enter(self, e):
        self['bg'] = self.hover_color

    def _on_leave(self, e):
        self['bg'] = self.bg_color


class PDFEditorApp:
    """Modern PDF Editor Application v3.0"""

    CANVAS_OFFSET = 20

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.geometry("1500x950")
        self.root.minsize(1200, 800)

        # Modern dark theme colors
        self.colors = {
            'bg_dark': '#1e1e1e',
            'bg_medium': '#252526',
            'bg_light': '#333333',
            'accent': '#4a9eff',
            'accent_hover': '#6bb3ff',
            'text': '#ffffff',
            'text_dim': '#aaaaaa',
            'border': '#404040',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336',
        }

        self.root.configure(bg=self.colors['bg_dark'])

        # Core engine
        self.engine = PDFEngine()

        # UI State
        self.current_page = 0
        self.zoom = 1.0
        self.current_tool = Tool.SELECT
        self.current_lang = "en"

        # Tool settings
        self.text_color = DEFAULT_COLORS["text"]
        self.highlight_color = DEFAULT_COLORS["highlight"]
        self.shape_color = DEFAULT_COLORS["shape"]
        self.font_size = 12
        self.font_name = "helv"
        self.line_width = 2

        # Selection state
        self.selected_text = None
        self.selected_image = None
        self.selected_layer = None

        # Drawing state
        self.drawing = False
        self.start_pos = None
        self.temp_points = []
        self.drag_start = None

        # Display images
        self.current_image = None
        self.thumbnail_images = []

        # Tooltips dictionary
        self.tooltips = {}

        # Build UI
        self._setup_styles()
        self._create_menu()
        self._create_toolbar()
        self._create_main_area()
        self._create_status_bar()
        self._bind_shortcuts()
        self._update_title()

    def t(self, key: str) -> str:
        return get_text(self.current_lang, key)

    def get_tooltip(self, tool: Tool) -> str:
        """Get tooltip text for a tool"""
        lang_tooltips = TOOL_TOOLTIPS.get(self.current_lang, TOOL_TOOLTIPS.get("en", {}))
        return lang_tooltips.get(tool, str(tool.value))

    def change_language(self, lang_code: str):
        self.current_lang = lang_code
        self._rebuild_menus()
        self._rebuild_toolbar()
        self._update_ui_texts()
        self._update_title()

    def _update_ui_texts(self):
        self.pages_label.config(text=self.t("pages"))
        self.props_label.config(text=self.t("properties"))
        self.status_label.config(text=self.t("ready"))
        self._update_tool_label()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Modern dark theme styles
        style.configure("Dark.TFrame", background=self.colors['bg_dark'])
        style.configure("Medium.TFrame", background=self.colors['bg_medium'])
        style.configure("Light.TFrame", background=self.colors['bg_light'])

        style.configure("Dark.TLabel",
            background=self.colors['bg_dark'],
            foreground=self.colors['text'],
            font=('Segoe UI', 10)
        )

        style.configure("Title.TLabel",
            background=self.colors['bg_medium'],
            foreground=self.colors['text'],
            font=('Segoe UI', 11, 'bold')
        )

        style.configure("Modern.TButton",
            background=self.colors['bg_light'],
            foreground=self.colors['text'],
            padding=(10, 5),
            font=('Segoe UI', 10)
        )
        style.map("Modern.TButton",
            background=[('active', self.colors['accent']), ('pressed', self.colors['accent_hover'])]
        )

        style.configure("Toolbar.TLabelframe",
            background=self.colors['bg_medium'],
            foreground=self.colors['text']
        )
        style.configure("Toolbar.TLabelframe.Label",
            background=self.colors['bg_medium'],
            foreground=self.colors['text_dim'],
            font=('Segoe UI', 9)
        )

        style.configure("TCombobox",
            fieldbackground=self.colors['bg_light'],
            background=self.colors['bg_light'],
            foreground=self.colors['text']
        )

        style.configure("TSpinbox",
            fieldbackground=self.colors['bg_light'],
            background=self.colors['bg_light'],
            foreground=self.colors['text']
        )

    def _update_title(self):
        title = self.t("app_title") + " v3.0"
        if self.engine.file_path:
            title += f" - {os.path.basename(self.engine.file_path)}"
            if self.engine.modified:
                title += " *"
        self.root.title(title)

    def _update_tool_label(self):
        tool_names = {
            Tool.SELECT: "select", Tool.TEXT: "text",
            Tool.HIGHLIGHT: "highlight", Tool.UNDERLINE: "underline",
            Tool.STRIKEOUT: "strikeout", Tool.RECTANGLE: "rectangle",
            Tool.CIRCLE: "circle", Tool.LINE: "line",
            Tool.ARROW: "arrow", Tool.FREEHAND: "freehand",
            Tool.IMAGE_SELECT: "select_image", Tool.IMAGE_MOVE: "move_image",
        }
        name = tool_names.get(self.current_tool, "select")
        self.tool_label.config(text=f"{self.t('tool')}: {self.t(name)}")

    def _create_menu(self):
        self.menubar = tk.Menu(self.root, bg=self.colors['bg_light'],
                               fg=self.colors['text'],
                               activebackground=self.colors['accent'],
                               activeforeground='white')
        self.root.config(menu=self.menubar)
        self._rebuild_menus()

    def _rebuild_menus(self):
        self.menubar.delete(0, tk.END)

        menu_config = {'bg': self.colors['bg_light'], 'fg': self.colors['text'],
                       'activebackground': self.colors['accent'], 'activeforeground': 'white'}

        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("file"), menu=file_menu)
        file_menu.add_command(label=self.t("open"), command=self.open_pdf, accelerator="Ctrl+O")
        file_menu.add_command(label=self.t("save"), command=self.save_pdf, accelerator="Ctrl+S")
        file_menu.add_command(label=self.t("save_as"), command=self.save_as_pdf)
        file_menu.add_separator()
        file_menu.add_command(label=self.t("export_images"), command=self.export_images)
        file_menu.add_command(label=self.t("extract_text"), command=self.extract_text)
        file_menu.add_separator()
        file_menu.add_command(label=self.t("exit"), command=self.on_closing)

        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("edit"), menu=edit_menu)
        edit_menu.add_command(label=self.t("undo"), command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label=self.t("redo"), command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label=self.t("find_replace"), command=self.find_replace, accelerator="Ctrl+H")

        # Page menu
        page_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("page"), menu=page_menu)
        page_menu.add_command(label=self.t("add_page"), command=self.add_page)
        page_menu.add_command(label=self.t("delete_page"), command=self.delete_page)
        page_menu.add_command(label=self.t("rotate_page"), command=self.rotate_page)
        page_menu.add_separator()
        page_menu.add_command(label=self.t("extract_pages"), command=self.extract_pages)
        page_menu.add_command(label=self.t("merge_pdf"), command=self.merge_pdfs)

        # Insert menu
        insert_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("insert"), menu=insert_menu)
        insert_menu.add_command(label=self.t("text"), command=lambda: self.set_tool(Tool.TEXT))
        insert_menu.add_command(label=self.t("image"), command=self.insert_image)
        insert_menu.add_separator()
        insert_menu.add_command(label=self.t("signature"), command=self.add_signature)
        insert_menu.add_command(label=self.t("stamp"), command=self.add_stamp)
        insert_menu.add_command(label=self.t("watermark"), command=self.add_watermark)

        # Image menu
        image_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("image_tools"), menu=image_menu)
        image_menu.add_command(label=self.t("select_image"), command=lambda: self.set_tool(Tool.IMAGE_SELECT))
        image_menu.add_command(label=self.t("move_image"), command=lambda: self.set_tool(Tool.IMAGE_MOVE))
        image_menu.add_separator()
        image_menu.add_command(label=self.t("resize_image"), command=self.resize_selected_image)
        image_menu.add_command(label=self.t("rotate_image"), command=self.rotate_selected_image)
        image_menu.add_command(label=self.t("scale_image"), command=self.scale_selected_image)
        image_menu.add_separator()
        image_menu.add_command(label=self.t("delete_image"), command=self.delete_selected_image)
        image_menu.add_command(label=self.t("replace_image"), command=self.replace_selected_image)
        image_menu.add_command(label=self.t("extract_image"), command=self.extract_selected_image)

        # View menu
        view_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("view"), menu=view_menu)
        view_menu.add_command(label=self.t("zoom_in"), command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label=self.t("zoom_out"), command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label=self.t("actual_size"), command=self.zoom_fit, accelerator="Ctrl+0")
        view_menu.add_separator()
        view_menu.add_command(label=self.t("memory_usage"), command=self.show_memory_stats)

        # Language menu
        lang_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("language"), menu=lang_menu)
        for code, name in get_available_languages().items():
            lang_menu.add_command(label=name, command=lambda c=code: self.change_language(c))

        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0, **menu_config)
        self.menubar.add_cascade(label=self.t("help"), menu=help_menu)
        help_menu.add_command(label=self.t("shortcuts"), command=self.show_shortcuts)
        help_menu.add_command(label=self.t("about"), command=self.show_about)

    def _create_toolbar(self):
        self.toolbar_frame = tk.Frame(self.root, bg=self.colors['bg_medium'], height=60)
        self.toolbar_frame.pack(fill="x", padx=5, pady=(5, 0))
        self.toolbar_frame.pack_propagate(False)
        self._rebuild_toolbar()

    def _create_tool_button(self, parent, text, command, tooltip_text):
        """Create a tool button with tooltip"""
        btn = ModernButton(parent, text=text, command=command,
                          tooltip=tooltip_text, width=3, height=1)
        btn.pack(side="left", padx=2, pady=2)
        return btn

    def _rebuild_toolbar(self):
        for widget in self.toolbar_frame.winfo_children():
            widget.destroy()

        # File tools
        file_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("file"),
                                   bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                   font=('Segoe UI', 9))
        file_frame.pack(side="left", padx=5, pady=5, fill="y")

        self._create_tool_button(file_frame, "📂", self.open_pdf, self.t("open") + " (Ctrl+O)")
        self._create_tool_button(file_frame, "💾", self.save_pdf, self.t("save") + " (Ctrl+S)")

        # Edit tools
        edit_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("edit"),
                                   bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                   font=('Segoe UI', 9))
        edit_frame.pack(side="left", padx=5, pady=5, fill="y")

        self._create_tool_button(edit_frame, "↩", self.undo, self.t("undo") + " (Ctrl+Z)")
        self._create_tool_button(edit_frame, "↪", self.redo, self.t("redo") + " (Ctrl+Y)")

        # Selection/Text tools
        tools_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("tools"),
                                    bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                    font=('Segoe UI', 9))
        tools_frame.pack(side="left", padx=5, pady=5, fill="y")

        tools = [
            (Tool.SELECT, "👆"), (Tool.TEXT, "T"),
            (Tool.HIGHLIGHT, "🖍"), (Tool.UNDERLINE, "U̲"), (Tool.STRIKEOUT, "S̶"),
        ]
        for tool, icon in tools:
            self._create_tool_button(tools_frame, icon,
                                    lambda t=tool: self.set_tool(t),
                                    self.get_tooltip(tool))

        # Drawing tools
        draw_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("shapes") if hasattr(self, 't') else "Shapes",
                                   bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                   font=('Segoe UI', 9))
        draw_frame.pack(side="left", padx=5, pady=5, fill="y")

        draw_tools = [
            (Tool.RECTANGLE, "▢"), (Tool.CIRCLE, "○"),
            (Tool.LINE, "╱"), (Tool.ARROW, "→"), (Tool.FREEHAND, "✏"),
        ]
        for tool, icon in draw_tools:
            self._create_tool_button(draw_frame, icon,
                                    lambda t=tool: self.set_tool(t),
                                    self.get_tooltip(tool))

        # Image tools
        img_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("images"),
                                  bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                  font=('Segoe UI', 9))
        img_frame.pack(side="left", padx=5, pady=5, fill="y")

        self._create_tool_button(img_frame, "🖼",
                                lambda: self.set_tool(Tool.IMAGE_SELECT),
                                self.get_tooltip(Tool.IMAGE_SELECT))
        self._create_tool_button(img_frame, "✋",
                                lambda: self.set_tool(Tool.IMAGE_MOVE),
                                self.get_tooltip(Tool.IMAGE_MOVE))

        # Font settings
        text_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("font"),
                                   bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                   font=('Segoe UI', 9))
        text_frame.pack(side="left", padx=5, pady=5, fill="y")

        fonts = FontManager.get_available_fonts()
        font_names = [f["name"] for f in fonts]
        self.font_var = tk.StringVar(value="Helvetica")
        font_combo = ttk.Combobox(text_frame, textvariable=self.font_var,
                                  values=font_names, width=10)
        font_combo.pack(side="left", padx=2, pady=2)
        font_combo.bind("<<ComboboxSelected>>", self._on_font_change)
        ToolTip(font_combo, self.t("font"))

        self.font_size_var = tk.StringVar(value="12")
        size_combo = ttk.Combobox(text_frame, textvariable=self.font_size_var,
                                  values=FONT_SIZES, width=4)
        size_combo.pack(side="left", padx=2, pady=2)
        ToolTip(size_combo, self.t("size"))

        self.text_color_btn = ModernButton(text_frame, text="  ", width=2,
                                           bg="black", command=self.choose_text_color,
                                           tooltip=self.t("text_color") if hasattr(self, 't') else "Text Color")
        self.text_color_btn.pack(side="left", padx=2, pady=2)

        # Colors
        color_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("color"),
                                    bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                    font=('Segoe UI', 9))
        color_frame.pack(side="left", padx=5, pady=5, fill="y")

        self.highlight_color_btn = ModernButton(color_frame, text="  ", width=2,
                                                bg="yellow", command=self.choose_highlight_color,
                                                tooltip=self.t("highlight_color") if hasattr(self, 't') else "Highlight Color")
        self.highlight_color_btn.pack(side="left", padx=2, pady=2)

        self.shape_color_btn = ModernButton(color_frame, text="  ", width=2,
                                            bg="red", command=self.choose_shape_color,
                                            tooltip=self.t("shape_color") if hasattr(self, 't') else "Shape Color")
        self.shape_color_btn.pack(side="left", padx=2, pady=2)

        self.line_width_var = tk.StringVar(value="2")
        width_spin = ttk.Spinbox(color_frame, from_=1, to=10, width=3,
                                 textvariable=self.line_width_var)
        width_spin.pack(side="left", padx=2, pady=2)
        ToolTip(width_spin, self.t("thickness"))

        # Zoom
        zoom_frame = tk.LabelFrame(self.toolbar_frame, text=self.t("view"),
                                   bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                   font=('Segoe UI', 9))
        zoom_frame.pack(side="left", padx=5, pady=5, fill="y")

        self._create_tool_button(zoom_frame, "−", self.zoom_out, self.t("zoom_out"))

        self.zoom_label = tk.Label(zoom_frame, text="100%", width=5,
                                   bg=self.colors['bg_medium'], fg=self.colors['text'],
                                   font=('Segoe UI', 10))
        self.zoom_label.pack(side="left", padx=5, pady=2)

        self._create_tool_button(zoom_frame, "+", self.zoom_in, self.t("zoom_in"))

    def _create_main_area(self):
        main_frame = tk.Frame(self.root, bg=self.colors['bg_dark'])
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Thumbnails panel
        self.thumbnails_frame = tk.Frame(main_frame, width=160, bg=self.colors['bg_medium'])
        self.thumbnails_frame.pack(side="left", fill="y", padx=(0, 5))
        self.thumbnails_frame.pack_propagate(False)

        self.pages_label = tk.Label(self.thumbnails_frame, text=self.t("pages"),
                                    bg=self.colors['bg_medium'], fg=self.colors['text'],
                                    font=('Segoe UI', 11, 'bold'))
        self.pages_label.pack(pady=10)

        self.thumbnails_canvas = tk.Canvas(self.thumbnails_frame, bg=self.colors['bg_light'],
                                          highlightthickness=0, width=150)
        thumbnails_scroll = ttk.Scrollbar(self.thumbnails_frame, orient="vertical",
                                         command=self.thumbnails_canvas.yview)
        self.thumbnails_inner = tk.Frame(self.thumbnails_canvas, bg=self.colors['bg_light'])

        self.thumbnails_canvas.configure(yscrollcommand=thumbnails_scroll.set)
        thumbnails_scroll.pack(side="right", fill="y")
        self.thumbnails_canvas.pack(side="left", fill="both", expand=True)
        self.thumbnails_canvas.create_window((0, 0), window=self.thumbnails_inner, anchor="nw")

        self.thumbnails_inner.bind("<Configure>",
            lambda e: self.thumbnails_canvas.configure(scrollregion=self.thumbnails_canvas.bbox("all")))

        # Main canvas
        view_frame = tk.Frame(main_frame, bg=self.colors['bg_dark'])
        view_frame.pack(side="left", fill="both", expand=True)

        self.canvas_frame = tk.Frame(view_frame, bg=self.colors['bg_dark'])
        self.canvas_frame.pack(fill="both", expand=True)

        self.h_scroll = ttk.Scrollbar(self.canvas_frame, orient="horizontal")
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient="vertical")

        self.canvas = tk.Canvas(self.canvas_frame, bg=self.colors['bg_light'],
                               xscrollcommand=self.h_scroll.set,
                               yscrollcommand=self.v_scroll.set,
                               highlightthickness=0)

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Canvas events
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)

        # Navigation
        nav_frame = tk.Frame(view_frame, bg=self.colors['bg_medium'], height=40)
        nav_frame.pack(fill="x", pady=(5, 0))

        nav_inner = tk.Frame(nav_frame, bg=self.colors['bg_medium'])
        nav_inner.pack(expand=True)

        self._create_tool_button(nav_inner, "◀◀", self.first_page, self.t("first_page") if hasattr(self, 't') else "First Page")
        self._create_tool_button(nav_inner, "◀", self.prev_page, self.t("prev_page") if hasattr(self, 't') else "Previous Page")

        self.page_entry = tk.Entry(nav_inner, width=5, justify="center",
                                   bg=self.colors['bg_light'], fg=self.colors['text'],
                                   insertbackground=self.colors['text'],
                                   font=('Segoe UI', 10))
        self.page_entry.pack(side="left", padx=5)
        self.page_entry.bind("<Return>", self._on_page_entry)

        self.page_label = tk.Label(nav_inner, text=f"{self.t('page_of')} 0",
                                   bg=self.colors['bg_medium'], fg=self.colors['text'],
                                   font=('Segoe UI', 10))
        self.page_label.pack(side="left", padx=5)

        self._create_tool_button(nav_inner, "▶", self.next_page, self.t("next_page") if hasattr(self, 't') else "Next Page")
        self._create_tool_button(nav_inner, "▶▶", self.last_page, self.t("last_page") if hasattr(self, 't') else "Last Page")

        # Properties panel
        self.properties_frame = tk.Frame(main_frame, width=200, bg=self.colors['bg_medium'])
        self.properties_frame.pack(side="right", fill="y", padx=(5, 0))
        self.properties_frame.pack_propagate(False)

        self.props_label = tk.Label(self.properties_frame, text=self.t("properties"),
                                    bg=self.colors['bg_medium'], fg=self.colors['text'],
                                    font=('Segoe UI', 11, 'bold'))
        self.props_label.pack(pady=10)

        layers_label = tk.Label(self.properties_frame, text="Layers",
                               bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                               font=('Segoe UI', 9))
        layers_label.pack(pady=(10, 5))

        self.layer_listbox = tk.Listbox(self.properties_frame, bg=self.colors['bg_light'],
                                        fg=self.colors['text'], selectbackground=self.colors['accent'],
                                        selectforeground='white', height=12,
                                        font=('Segoe UI', 9), highlightthickness=0)
        self.layer_listbox.pack(fill="x", padx=10)
        self.layer_listbox.bind("<<ListboxSelect>>", self._on_layer_select)

    def _create_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=self.colors['bg_medium'], height=30)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(self.status_bar, text=self.t("ready"),
                                     bg=self.colors['bg_medium'], fg=self.colors['text'],
                                     font=('Segoe UI', 9))
        self.status_label.pack(side="left", padx=10, pady=5)

        self.tool_label = tk.Label(self.status_bar,
                                   text=f"{self.t('tool')}: {self.t('select')}",
                                   bg=self.colors['bg_medium'], fg=self.colors['text'],
                                   font=('Segoe UI', 9))
        self.tool_label.pack(side="right", padx=10, pady=5)

        self.memory_label = tk.Label(self.status_bar, text="",
                                     bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                     font=('Segoe UI', 9))
        self.memory_label.pack(side="right", padx=10, pady=5)

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-s>", lambda e: self.save_pdf())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-h>", lambda e: self.find_replace())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.zoom_fit())
        self.root.bind("<Prior>", lambda e: self.prev_page())
        self.root.bind("<Next>", lambda e: self.next_page())
        self.root.bind("<Home>", lambda e: self.first_page())
        self.root.bind("<End>", lambda e: self.last_page())
        self.root.bind("<Delete>", lambda e: self.delete_selection())
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ============ File Operations ============

    def open_pdf(self):
        if self.engine.modified:
            if not messagebox.askyesno(self.t("confirm"), self.t("unsaved_changes")):
                return

        file_path = filedialog.askopenfilename(
            title=self.t("open"),
            filetypes=[("PDF files", "*.pdf")]
        )

        if file_path:
            try:
                self.engine.open(file_path)
                self.current_page = 0
                self._update_thumbnails()
                self._render_page()
                self._update_page_info()
                self._update_title()
                self._update_layer_list()
                self.status_label.config(text=self.t("file_opened"))
            except Exception as e:
                messagebox.showerror(self.t("error"), str(e))

    def save_pdf(self):
        if not self.engine.is_open():
            return

        if self.engine.file_path:
            try:
                self.engine.save()
                self._update_title()
                self.status_label.config(text=self.t("file_saved"))
            except Exception as e:
                messagebox.showerror(self.t("error"), str(e))
        else:
            self.save_as_pdf()

    def save_as_pdf(self):
        if not self.engine.is_open():
            return

        file_path = filedialog.asksaveasfilename(
            title=self.t("save_as"),
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )

        if file_path:
            try:
                self.engine.save(file_path)
                self._update_title()
                self.status_label.config(text=self.t("file_saved"))
            except Exception as e:
                messagebox.showerror(self.t("error"), str(e))

    def export_images(self):
        if not self.engine.is_open():
            return

        folder = filedialog.askdirectory(title=self.t("export_images"))
        if folder:
            count = self.engine.export_images(folder)
            messagebox.showinfo(self.t("success"), f"{count} {self.t('pages')}")

    def extract_text(self):
        if not self.engine.is_open():
            return

        file_path = filedialog.asksaveasfilename(
            title=self.t("extract_text"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )

        if file_path:
            if self.engine.extract_text(file_path):
                messagebox.showinfo(self.t("success"), self.t("file_saved"))

    # ============ Edit Operations ============

    def undo(self):
        if self.engine.undo():
            self._render_page()
            self._update_thumbnails()
            self._update_title()
            self.status_label.config(text=self.t("undo"))

    def redo(self):
        if self.engine.redo():
            self._render_page()
            self._update_thumbnails()
            self._update_title()
            self.status_label.config(text=self.t("redo"))

    def delete_selection(self):
        if self.selected_image:
            self.delete_selected_image()
        elif self.selected_layer:
            self.engine.layer_manager.remove_layer(self.selected_layer.id)
            self._render_page()
            self._update_layer_list()

    def find_replace(self):
        if not self.engine.is_open():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("find_replace"))
        dialog.geometry("450x220")
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=self.t("find"), bg=self.colors['bg_medium'],
                fg=self.colors['text'], font=('Segoe UI', 10)).pack(pady=(15, 5))
        find_entry = tk.Entry(dialog, width=45, bg=self.colors['bg_light'],
                             fg=self.colors['text'], insertbackground=self.colors['text'])
        find_entry.pack(pady=5)

        tk.Label(dialog, text=self.t("replace_with"), bg=self.colors['bg_medium'],
                fg=self.colors['text'], font=('Segoe UI', 10)).pack(pady=(10, 5))
        replace_entry = tk.Entry(dialog, width=45, bg=self.colors['bg_light'],
                                fg=self.colors['text'], insertbackground=self.colors['text'])
        replace_entry.pack(pady=5)

        def do_replace():
            find_text = find_entry.get()
            replace_text = replace_entry.get()
            if find_text:
                count = self.engine.find_and_replace(find_text, replace_text)
                if count > 0:
                    self._render_page()
                    self._update_thumbnails()
                    self._update_title()
                    messagebox.showinfo(self.t("success"), f"{count} {self.t('matches_replaced')}")
                else:
                    messagebox.showinfo(self.t("success"), self.t("no_match"))
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=20)
        ModernButton(btn_frame, text=self.t("replace_all"), command=do_replace,
                    tooltip="Replace all occurrences").pack(side="left", padx=10)
        ModernButton(btn_frame, text=self.t("cancel"), command=dialog.destroy,
                    tooltip="Cancel").pack(side="left", padx=10)

    # ============ Page Operations ============

    def add_page(self):
        if self.engine.is_open():
            self.engine.add_page()
            self._update_thumbnails()
            self.last_page()
            self._update_title()

    def delete_page(self):
        if not self.engine.is_open() or self.engine.get_page_count() <= 1:
            return

        if messagebox.askyesno(self.t("confirm"),
                              f"{self.t('delete_page')} {self.current_page + 1}?"):
            if self.engine.delete_page(self.current_page):
                if self.current_page >= self.engine.get_page_count():
                    self.current_page = self.engine.get_page_count() - 1
                self._update_thumbnails()
                self._render_page()
                self._update_page_info()
                self._update_title()

    def rotate_page(self):
        if self.engine.is_open():
            self.engine.rotate_page(self.current_page)
            self._render_page()
            self._update_thumbnails()
            self._update_title()

    def extract_pages(self):
        if not self.engine.is_open():
            return

        pages_str = simpledialog.askstring(
            self.t("extract_pages"),
            f"{self.t('total_pages')}: {self.engine.get_page_count()}\n{self.t('enter_page_range')}"
        )

        if pages_str:
            try:
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
                    if self.engine.extract_pages(pages, output_path):
                        messagebox.showinfo(self.t("success"), self.t("file_saved"))
            except Exception as e:
                messagebox.showerror(self.t("error"), str(e))

    def merge_pdfs(self):
        files = filedialog.askopenfilenames(
            title=self.t("merge_pdf"),
            filetypes=[("PDF files", "*.pdf")]
        )

        if files:
            output_path = filedialog.asksaveasfilename(
                title=self.t("save_as"),
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")]
            )

            if output_path:
                if self.engine.merge_pdfs(list(files), output_path):
                    messagebox.showinfo(self.t("success"), self.t("file_saved"))

    # ============ Insert Operations ============

    def insert_image(self):
        if not self.engine.is_open():
            return

        img_path = filedialog.askopenfilename(
            title=self.t("image"),
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )

        if img_path:
            self.engine.insert_image(self.current_page, img_path)
            self._render_page()
            self._update_title()

    def add_signature(self):
        if not self.engine.is_open():
            return

        sig_window = tk.Toplevel(self.root)
        sig_window.title(self.t("draw_signature"))
        sig_window.geometry("420x230")
        sig_window.configure(bg=self.colors['bg_medium'])
        sig_window.transient(self.root)

        canvas = tk.Canvas(sig_window, bg="white", width=400, height=160)
        canvas.pack(pady=10)

        points = []

        def draw(event):
            if points:
                canvas.create_line(points[-1][0], points[-1][1], event.x, event.y, width=2)
            points.append((event.x, event.y))

        def clear():
            canvas.delete("all")
            points.clear()

        def save_sig():
            if len(points) >= 2:
                page_h = self.engine.get_page_size(self.current_page)[1]
                scaled_points = [(p[0] + 100, page_h - 100 + p[1] * 0.5) for p in points]
                self.engine.add_freehand(self.current_page, scaled_points,
                                        color=(0, 0, 0.5), width=1.5)
                self._render_page()
                self._update_title()
            sig_window.destroy()

        canvas.bind("<B1-Motion>", draw)

        btn_frame = tk.Frame(sig_window, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=10)
        ModernButton(btn_frame, text=self.t("clear"), command=clear).pack(side="left", padx=5)
        ModernButton(btn_frame, text=self.t("insert_sig"), command=save_sig).pack(side="left", padx=5)

    def add_stamp(self):
        if not self.engine.is_open():
            return

        stamps = [
            self.t("draft"), self.t("confidential"), self.t("final"),
            self.t("rejected"), self.t("approved"), self.t("urgent")
        ]

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("choose_stamp"))
        dialog.geometry("220x350")
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)

        for stamp in stamps:
            ModernButton(dialog, text=stamp, width=20,
                        command=lambda s=stamp: self._insert_stamp(s, dialog)).pack(pady=8)

    def _insert_stamp(self, text, dialog):
        w, h = self.engine.get_page_size(self.current_page)
        self.engine.add_stamp(self.current_page, text, w / 3, h / 2,
                             color=(1, 0, 0), font_size=72, rotation=45)
        self._render_page()
        self._update_title()
        dialog.destroy()

    def add_watermark(self):
        if not self.engine.is_open():
            return

        text = simpledialog.askstring(self.t("watermark"), self.t("enter_watermark"))
        if text:
            self.engine.add_watermark(text)
            self._render_page()
            self._update_thumbnails()
            self._update_title()

    # ============ Image Operations ============

    def delete_selected_image(self):
        if self.selected_image and self.engine.is_open():
            if self.engine.delete_image(self.current_page, self.selected_image):
                self.selected_image = None
                self.canvas.delete("selection")
                self._render_page()
                self._update_title()
                self.status_label.config(text=self.t("image_deleted"))
        else:
            messagebox.showwarning(self.t("error"), self.t("select_image_first"))

    def replace_selected_image(self):
        if not self.selected_image:
            messagebox.showwarning(self.t("error"), self.t("select_image_first"))
            return

        new_path = filedialog.askopenfilename(
            title=self.t("image"),
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )

        if new_path:
            if self.engine.replace_image(self.current_page, self.selected_image, new_path):
                self.selected_image = None
                self.canvas.delete("selection")
                self._render_page()
                self._update_title()
                self.status_label.config(text=self.t("image_replaced"))

    def extract_selected_image(self):
        if not self.selected_image:
            messagebox.showwarning(self.t("error"), self.t("select_image_first"))
            return

        output_path = filedialog.asksaveasfilename(
            title=self.t("extract_image"),
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
        )

        if output_path:
            if self.engine.extract_image(self.selected_image, output_path):
                messagebox.showinfo(self.t("success"), self.t("file_saved"))

    def resize_selected_image(self):
        """Show dialog to resize selected image"""
        if not self.selected_image:
            messagebox.showwarning(self.t("error"), self.t("select_image_first"))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("resize_image"))
        dialog.geometry("350x250")
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()

        # Current size info
        current_w = self.selected_image.rect.width
        current_h = self.selected_image.rect.height

        tk.Label(dialog, text=f"Current: {current_w:.1f} x {current_h:.1f}",
                bg=self.colors['bg_medium'], fg=self.colors['text'],
                font=('Segoe UI', 10)).pack(pady=10)

        # Width
        frame_w = tk.Frame(dialog, bg=self.colors['bg_medium'])
        frame_w.pack(pady=5)
        tk.Label(frame_w, text="Width:", bg=self.colors['bg_medium'],
                fg=self.colors['text'], width=10).pack(side="left")
        width_var = tk.StringVar(value=str(int(current_w)))
        width_entry = tk.Entry(frame_w, textvariable=width_var, width=10,
                              bg=self.colors['bg_light'], fg=self.colors['text'])
        width_entry.pack(side="left", padx=5)

        # Height
        frame_h = tk.Frame(dialog, bg=self.colors['bg_medium'])
        frame_h.pack(pady=5)
        tk.Label(frame_h, text="Height:", bg=self.colors['bg_medium'],
                fg=self.colors['text'], width=10).pack(side="left")
        height_var = tk.StringVar(value=str(int(current_h)))
        height_entry = tk.Entry(frame_h, textvariable=height_var, width=10,
                               bg=self.colors['bg_light'], fg=self.colors['text'])
        height_entry.pack(side="left", padx=5)

        # Keep aspect ratio
        keep_ratio = tk.BooleanVar(value=True)
        tk.Checkbutton(dialog, text="Keep Aspect Ratio", variable=keep_ratio,
                      bg=self.colors['bg_medium'], fg=self.colors['text'],
                      selectcolor=self.colors['bg_dark']).pack(pady=10)

        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=20)

        def apply_resize():
            try:
                new_w = float(width_var.get())
                new_h = float(height_var.get())
                if new_w > 0 and new_h > 0:
                    if self.engine.resize_image(self.current_page, self.selected_image,
                                                new_w, new_h, keep_ratio.get()):
                        self.selected_image = None
                        self.canvas.delete("selection")
                        self._render_page()
                        self._update_title()
                        self.status_label.config(text="Image resized")
                        dialog.destroy()
                    else:
                        messagebox.showerror(self.t("error"), "Failed to resize image")
            except ValueError:
                messagebox.showerror(self.t("error"), "Invalid dimensions")

        tk.Button(btn_frame, text="✓ Apply", width=10, bg="#4CAF50", fg="white",
                 command=apply_resize).pack(side="left", padx=10)
        tk.Button(btn_frame, text="✗ Cancel", width=10, bg="#f44336", fg="white",
                 command=dialog.destroy).pack(side="left", padx=10)

    def scale_selected_image(self):
        """Show dialog to scale selected image by percentage"""
        if not self.selected_image:
            messagebox.showwarning(self.t("error"), self.t("select_image_first"))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("scale_image"))
        dialog.geometry("300x180")
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Scale Percentage:", bg=self.colors['bg_medium'],
                fg=self.colors['text'], font=('Segoe UI', 11)).pack(pady=15)

        # Scale options
        frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        frame.pack(pady=10)

        scale_var = tk.StringVar(value="100")
        scale_entry = tk.Entry(frame, textvariable=scale_var, width=8,
                              font=('Segoe UI', 12), justify='center',
                              bg=self.colors['bg_light'], fg=self.colors['text'])
        scale_entry.pack(side="left", padx=5)
        tk.Label(frame, text="%", bg=self.colors['bg_medium'],
                fg=self.colors['text'], font=('Segoe UI', 12)).pack(side="left")

        # Quick buttons
        quick_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        quick_frame.pack(pady=5)
        for val in ["50", "75", "100", "150", "200"]:
            tk.Button(quick_frame, text=f"{val}%", width=5,
                     bg=self.colors['bg_light'], fg=self.colors['text'],
                     command=lambda v=val: scale_var.set(v)).pack(side="left", padx=2)

        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=15)

        def apply_scale():
            try:
                scale = float(scale_var.get()) / 100.0
                if scale > 0:
                    if self.engine.scale_image(self.current_page, self.selected_image, scale):
                        self.selected_image = None
                        self.canvas.delete("selection")
                        self._render_page()
                        self._update_title()
                        self.status_label.config(text=f"Image scaled to {int(scale*100)}%")
                        dialog.destroy()
                    else:
                        messagebox.showerror(self.t("error"), "Failed to scale image")
            except ValueError:
                messagebox.showerror(self.t("error"), "Invalid scale value")

        tk.Button(btn_frame, text="✓ Apply", width=10, bg="#4CAF50", fg="white",
                 command=apply_scale).pack(side="left", padx=10)
        tk.Button(btn_frame, text="✗ Cancel", width=10, bg="#f44336", fg="white",
                 command=dialog.destroy).pack(side="left", padx=10)

    def rotate_selected_image(self):
        """Show dialog to rotate selected image"""
        if not self.selected_image:
            messagebox.showwarning(self.t("error"), self.t("select_image_first"))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("rotate_image"))
        dialog.geometry("300x150")
        dialog.configure(bg=self.colors['bg_medium'])
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Rotate Image:", bg=self.colors['bg_medium'],
                fg=self.colors['text'], font=('Segoe UI', 11)).pack(pady=15)

        # Rotation options
        frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        frame.pack(pady=10)

        def do_rotate(degrees):
            if self.engine.rotate_image(self.current_page, self.selected_image, degrees):
                self.selected_image = None
                self.canvas.delete("selection")
                self._render_page()
                self._update_title()
                self.status_label.config(text=f"Image rotated {degrees}°")
                dialog.destroy()
            else:
                messagebox.showerror(self.t("error"), "Failed to rotate image")

        tk.Button(frame, text="↺ 90°", width=8, font=('Segoe UI', 10),
                 bg=self.colors['bg_light'], fg=self.colors['text'],
                 command=lambda: do_rotate(90)).pack(side="left", padx=5)
        tk.Button(frame, text="180°", width=8, font=('Segoe UI', 10),
                 bg=self.colors['bg_light'], fg=self.colors['text'],
                 command=lambda: do_rotate(180)).pack(side="left", padx=5)
        tk.Button(frame, text="↻ 270°", width=8, font=('Segoe UI', 10),
                 bg=self.colors['bg_light'], fg=self.colors['text'],
                 command=lambda: do_rotate(270)).pack(side="left", padx=5)

        # Cancel
        tk.Button(dialog, text="Cancel", width=10, bg="#f44336", fg="white",
                 command=dialog.destroy).pack(pady=10)

    # ============ View Operations ============

    def _render_page(self):
        if not self.engine.is_open():
            return

        img = self.engine.render_page(self.current_page, self.zoom)
        if img:
            self.current_image = ImageTk.PhotoImage(img)

            self.canvas.delete("all")
            self.canvas.create_image(
                self.CANVAS_OFFSET + img.width / 2,
                self.CANVAS_OFFSET + img.height / 2,
                image=self.current_image, tags="page"
            )

            self.canvas.configure(scrollregion=(
                0, 0,
                img.width + self.CANVAS_OFFSET * 2,
                img.height + self.CANVAS_OFFSET * 2
            ))

            self._update_page_info()
            self._update_memory_label()

    def _update_thumbnails(self):
        for widget in self.thumbnails_inner.winfo_children():
            widget.destroy()

        if not self.engine.is_open():
            return

        self.thumbnail_images = []

        for i in range(self.engine.get_page_count()):
            frame = tk.Frame(self.thumbnails_inner, bg=self.colors['bg_light'])
            frame.pack(pady=5)

            img = self.engine.render_thumbnail(i)
            if img:
                photo = ImageTk.PhotoImage(img)
                self.thumbnail_images.append(photo)

                border_color = self.colors['accent'] if i == self.current_page else self.colors['bg_light']
                btn = tk.Button(frame, image=photo, relief="flat",
                               bg=border_color, activebackground=self.colors['accent'],
                               cursor='hand2',
                               command=lambda p=i: self._goto_page(p))
                btn.pack(padx=2, pady=2)
                ToolTip(btn, f"{self.t('page')} {i + 1}")

                label = tk.Label(frame, text=str(i + 1),
                               bg=self.colors['bg_light'], fg=self.colors['text'],
                               font=('Segoe UI', 9))
                label.pack()

    def _update_page_info(self):
        if self.engine.is_open():
            self.page_entry.delete(0, tk.END)
            self.page_entry.insert(0, str(self.current_page + 1))
            self.page_label.config(text=f"{self.t('page_of')} {self.engine.get_page_count()}")

    def _update_layer_list(self):
        self.layer_listbox.delete(0, tk.END)
        if self.engine.is_open():
            layers = self.engine.layer_manager.get_layers_for_page(self.current_page)
            for layer in layers:
                self.layer_listbox.insert(tk.END, f"{layer.layer_type.value}: {layer.id}")

    def _update_memory_label(self):
        stats = self.engine.get_memory_stats()
        cache_mb = stats["cache"]["page_cache"]["size_mb"]
        undo_kb = stats["undo_memory"] / 1024
        self.memory_label.config(text=f"Cache: {cache_mb:.1f}MB | Undo: {undo_kb:.0f}KB")

    def _goto_page(self, page_num: int):
        if self.engine.is_open() and 0 <= page_num < self.engine.get_page_count():
            self.current_page = page_num
            self._render_page()
            self._update_thumbnails()
            self._update_layer_list()

    def first_page(self):
        self._goto_page(0)

    def prev_page(self):
        self._goto_page(self.current_page - 1)

    def next_page(self):
        self._goto_page(self.current_page + 1)

    def last_page(self):
        if self.engine.is_open():
            self._goto_page(self.engine.get_page_count() - 1)

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

    # ============ Tool Operations ============

    def set_tool(self, tool: Tool):
        self.current_tool = tool
        self._update_tool_label()

        if tool not in [Tool.IMAGE_SELECT, Tool.IMAGE_MOVE]:
            self.selected_image = None
        if tool not in [Tool.SELECT, Tool.TEXT]:
            self.selected_text = None
        self.canvas.delete("selection")

    def _on_font_change(self, event):
        fonts = FontManager.get_available_fonts()
        for f in fonts:
            if f["name"] == self.font_var.get():
                self.font_name = f["id"]
                break

    def choose_text_color(self):
        color = colorchooser.askcolor(title=self.t("color"))
        if color[0]:
            self.text_color = tuple(c / 255 for c in color[0])
            self.text_color_btn.configure(bg=color[1])

    def choose_highlight_color(self):
        color = colorchooser.askcolor(title=self.t("color"))
        if color[0]:
            self.highlight_color = tuple(c / 255 for c in color[0])
            self.highlight_color_btn.configure(bg=color[1])

    def choose_shape_color(self):
        color = colorchooser.askcolor(title=self.t("color"))
        if color[0]:
            self.shape_color = tuple(c / 255 for c in color[0])
            self.shape_color_btn.configure(bg=color[1])

    # ============ Canvas Events ============

    def _canvas_to_pdf(self, canvas_x: float, canvas_y: float) -> tuple:
        return self.engine.canvas_to_pdf(
            canvas_x, canvas_y, self.zoom,
            (self.CANVAS_OFFSET, self.CANVAS_OFFSET)
        )

    def _pdf_to_canvas(self, pdf_x: float, pdf_y: float) -> tuple:
        return self.engine.pdf_to_canvas(
            pdf_x, pdf_y, self.zoom,
            (self.CANVAS_OFFSET, self.CANVAS_OFFSET)
        )

    def _on_canvas_click(self, event):
        if not self.engine.is_open():
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x, pdf_y = self._canvas_to_pdf(canvas_x, canvas_y)

        self.start_pos = (pdf_x, pdf_y)
        self.drawing = True

        if self.current_tool == Tool.TEXT:
            self._handle_text_click(pdf_x, pdf_y)
        elif self.current_tool == Tool.FREEHAND:
            self.temp_points = [(pdf_x, pdf_y)]
        elif self.current_tool == Tool.SELECT:
            self._handle_select_click(pdf_x, pdf_y)
        elif self.current_tool == Tool.IMAGE_SELECT:
            self._handle_image_select(pdf_x, pdf_y)
        elif self.current_tool == Tool.IMAGE_MOVE:
            if self.selected_image:
                self.drag_start = (pdf_x, pdf_y)

    def _on_canvas_drag(self, event):
        if not self.drawing or not self.engine.is_open():
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x, pdf_y = self._canvas_to_pdf(canvas_x, canvas_y)

        if self.current_tool == Tool.FREEHAND:
            self.temp_points.append((pdf_x, pdf_y))
            if len(self.temp_points) >= 2:
                p1 = self._pdf_to_canvas(*self.temp_points[-2])
                p2 = self._pdf_to_canvas(*self.temp_points[-1])
                self.canvas.create_line(
                    p1[0], p1[1], p2[0], p2[1],
                    fill=self._rgb_to_hex(self.shape_color),
                    width=int(self.line_width_var.get()),
                    tags="temp"
                )

    def _on_canvas_release(self, event):
        if not self.drawing or not self.engine.is_open():
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x, pdf_y = self._canvas_to_pdf(canvas_x, canvas_y)

        self.drawing = False

        if self.current_tool == Tool.RECTANGLE:
            rect = fitz.Rect(self.start_pos[0], self.start_pos[1], pdf_x, pdf_y)
            self.engine.add_rectangle(self.current_page, rect,
                                      self.shape_color, float(self.line_width_var.get()))
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.CIRCLE:
            rect = fitz.Rect(self.start_pos[0], self.start_pos[1], pdf_x, pdf_y)
            self.engine.add_circle(self.current_page, rect,
                                   self.shape_color, float(self.line_width_var.get()))
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.LINE:
            self.engine.add_line(self.current_page, self.start_pos, (pdf_x, pdf_y),
                                self.shape_color, float(self.line_width_var.get()))
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.ARROW:
            self.engine.add_line(self.current_page, self.start_pos, (pdf_x, pdf_y),
                                self.shape_color, float(self.line_width_var.get()))
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.FREEHAND and self.temp_points:
            self.engine.add_freehand(self.current_page, self.temp_points,
                                    self.shape_color, float(self.line_width_var.get()))
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.HIGHLIGHT:
            rect = fitz.Rect(self.start_pos[0], self.start_pos[1], pdf_x, pdf_y)
            self.engine.add_highlight(self.current_page, rect, self.highlight_color)
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.UNDERLINE:
            rect = fitz.Rect(self.start_pos[0], self.start_pos[1], pdf_x, pdf_y)
            self.engine.add_underline(self.current_page, rect)
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.STRIKEOUT:
            rect = fitz.Rect(self.start_pos[0], self.start_pos[1], pdf_x, pdf_y)
            self.engine.add_strikeout(self.current_page, rect)
            self._render_page()
            self._update_title()

        elif self.current_tool == Tool.IMAGE_MOVE and self.selected_image and self.drag_start:
            if self.engine.move_image(self.current_page, self.selected_image, pdf_x, pdf_y):
                self._render_page()
                self._update_title()
                self.status_label.config(text=self.t("image_moved"))
            self.drag_start = None

        self.temp_points = []
        self.canvas.delete("temp")
        self._update_layer_list()

    def _on_canvas_double_click(self, event):
        if not self.engine.is_open():
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x, pdf_y = self._canvas_to_pdf(canvas_x, canvas_y)

        # Try to find and edit text
        text_block = self.engine.find_text_at(self.current_page, pdf_x, pdf_y)
        if text_block:
            self._show_text_editor(text_block)
        else:
            # Check for image
            image = self.engine.find_image_at(self.current_page, pdf_x, pdf_y)
            if image:
                self.selected_image = image
                self._handle_image_select(pdf_x, pdf_y)
            else:
                # Add new text at click position
                self._add_new_text(pdf_x, pdf_y)

    def _on_canvas_right_click(self, event):
        """Handle right-click context menu"""
        if not self.engine.is_open():
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        pdf_x, pdf_y = self._canvas_to_pdf(canvas_x, canvas_y)

        # Check if clicking on an image
        image = self.engine.find_image_at(self.current_page, pdf_x, pdf_y)
        if image:
            self.selected_image = image
            self._handle_image_select(pdf_x, pdf_y)
            self._show_image_context_menu(event)
            return

        # Check if clicking on text
        text_block = self.engine.find_text_at(self.current_page, pdf_x, pdf_y)
        if text_block:
            self._show_text_context_menu(event, text_block)
            return

        # General context menu
        self._show_general_context_menu(event, pdf_x, pdf_y)

    def _show_image_context_menu(self, event):
        """Show context menu for images"""
        menu = tk.Menu(self.root, tearoff=0,
                      bg=self.colors['bg_medium'], fg=self.colors['text'])

        menu.add_command(label="📏 " + self.t("resize_image"),
                        command=self.resize_selected_image)
        menu.add_command(label="🔄 " + self.t("scale_image"),
                        command=self.scale_selected_image)
        menu.add_command(label="↻ " + self.t("rotate_image"),
                        command=self.rotate_selected_image)
        menu.add_separator()
        menu.add_command(label="🔀 " + self.t("move_image"),
                        command=lambda: self.set_tool(Tool.IMAGE_MOVE))
        menu.add_command(label="🔄 " + self.t("replace_image"),
                        command=self.replace_selected_image)
        menu.add_command(label="💾 " + self.t("extract_image"),
                        command=self.extract_selected_image)
        menu.add_separator()
        menu.add_command(label="🗑️ " + self.t("delete_image"),
                        command=self.delete_selected_image)

        menu.tk_popup(event.x_root, event.y_root)

    def _show_text_context_menu(self, event, text_block):
        """Show context menu for text"""
        menu = tk.Menu(self.root, tearoff=0,
                      bg=self.colors['bg_medium'], fg=self.colors['text'])

        menu.add_command(label="✏️ " + self.t("edit_text"),
                        command=lambda: self._show_text_editor(text_block))
        menu.add_separator()
        menu.add_command(label="🖍️ " + self.t("highlight"),
                        command=lambda: self._highlight_text(text_block))
        menu.add_command(label="__ " + self.t("underline"),
                        command=lambda: self._underline_text(text_block))
        menu.add_command(label="—— " + self.t("strikeout"),
                        command=lambda: self._strikeout_text(text_block))

        menu.tk_popup(event.x_root, event.y_root)

    def _show_general_context_menu(self, event, pdf_x, pdf_y):
        """Show general context menu"""
        menu = tk.Menu(self.root, tearoff=0,
                      bg=self.colors['bg_medium'], fg=self.colors['text'])

        menu.add_command(label="📝 " + self.t("new_text"),
                        command=lambda: self._add_new_text(pdf_x, pdf_y))
        menu.add_command(label="🖼️ " + self.t("insert") + " " + self.t("image"),
                        command=self.insert_image)
        menu.add_separator()
        menu.add_command(label="📋 " + self.t("paste"),
                        command=self.paste)

        menu.tk_popup(event.x_root, event.y_root)

    def _highlight_text(self, text_block):
        """Apply highlight to text block"""
        if self.engine.add_highlight(self.current_page, text_block.rect):
            self._render_page()
            self._update_title()

    def _underline_text(self, text_block):
        """Apply underline to text block"""
        if self.engine.add_underline(self.current_page, text_block.rect):
            self._render_page()
            self._update_title()

    def _strikeout_text(self, text_block):
        """Apply strikeout to text block"""
        if self.engine.add_strikeout(self.current_page, text_block.rect):
            self._render_page()
            self._update_title()

    def _on_mouse_wheel(self, event):
        if event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")

    def _on_layer_select(self, event):
        selection = self.layer_listbox.curselection()
        if selection:
            layers = self.engine.layer_manager.get_layers_for_page(self.current_page)
            if selection[0] < len(layers):
                self.selected_layer = layers[selection[0]]
                self.engine.layer_manager.select_layer(self.selected_layer)

    def _handle_text_click(self, x: float, y: float):
        text_block = self.engine.find_text_at(self.current_page, x, y)

        if text_block:
            # Show selection rectangle
            c1 = self._pdf_to_canvas(text_block.rect.x0, text_block.rect.y0)
            c2 = self._pdf_to_canvas(text_block.rect.x1, text_block.rect.y1)
            self.canvas.delete("selection")
            self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1],
                                        outline=self.colors['accent'], width=2,
                                        dash=(4, 4), tags="selection")
            self.selected_text = text_block
            self._show_text_editor(text_block)
        else:
            # No text found - add new text
            self._add_new_text(x, y)

    def _show_text_editor(self, block):
        editor = tk.Toplevel(self.root)
        editor.title(self.t("edit_text"))
        editor.geometry("600x450")
        editor.configure(bg=self.colors['bg_medium'])
        editor.transient(self.root)
        editor.grab_set()

        # Tools frame
        tools_frame = tk.Frame(editor, bg=self.colors['bg_medium'])
        tools_frame.pack(fill="x", padx=10, pady=10)

        # Font selection with multilingual support
        tk.Label(tools_frame, text=self.t("font") + ":", bg=self.colors['bg_medium'],
                fg=self.colors['text']).pack(side="left")

        # Extended font list with Arabic/Russian support
        font_options = [
            ("Helvetica", "helv"),
            ("Times", "tiro"),
            ("Courier", "cour"),
            ("Arabic (Noto)", "arabic"),
            ("Russian (Noto)", "russian"),
            ("CJK (Chinese/Japanese/Korean)", "cjk"),
        ]
        font_names = [f[0] for f in font_options]
        first_span = block.spans[0] if block.spans else None

        # Detect current font
        current_font = "Helvetica"
        if first_span:
            font_lower = first_span.font_name.lower()
            if "arab" in font_lower or "noto" in font_lower:
                current_font = "Arabic (Noto)"
            elif "cyr" in font_lower:
                current_font = "Russian (Noto)"

        font_var = tk.StringVar(value=current_font)
        font_combo = ttk.Combobox(tools_frame, textvariable=font_var,
                    values=font_names, width=20)
        font_combo.pack(side="left", padx=5)

        tk.Label(tools_frame, text=self.t("size") + ":", bg=self.colors['bg_medium'],
                fg=self.colors['text']).pack(side="left")
        size_var = tk.StringVar(value=str(int(first_span.font_size if first_span else 12)))
        ttk.Combobox(tools_frame, textvariable=size_var,
                    values=FONT_SIZES, width=4).pack(side="left", padx=5)

        color_btn = ModernButton(tools_frame, text=self.t("color"), width=8,
                                tooltip="Choose text color")
        color_btn.pack(side="left", padx=5)
        color_btn.color = first_span.color if first_span else (0, 0, 0)

        def choose_color():
            color = colorchooser.askcolor(title=self.t("color"))
            if color[0]:
                color_btn.color = tuple(c / 255 for c in color[0])
                color_btn.configure(bg=color[1])

        color_btn.configure(command=choose_color)

        # Text widget with RTL support
        text_frame = tk.Frame(editor, bg=self.colors['bg_medium'])
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Use a font that supports Arabic/Russian
        text_widget = tk.Text(text_frame, wrap="word", font=("Segoe UI", 12),
                             bg=self.colors['bg_light'], fg=self.colors['text'],
                             insertbackground=self.colors['text'])
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", block.text)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=scrollbar.set)

        # Info label
        info_label = tk.Label(editor, text="💡 " + self._get_font_info(),
                             bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                             font=('Segoe UI', 9))
        info_label.pack(pady=5)

        # Buttons frame
        btn_frame = tk.Frame(editor, bg=self.colors['bg_medium'])
        btn_frame.pack(pady=15, fill="x")

        def apply_changes():
            new_text = text_widget.get("1.0", "end-1c")
            new_size = float(size_var.get())
            new_color = color_btn.color

            # Get font ID based on selection
            font_id = "helv"
            selected_font = font_var.get()
            for name, fid in font_options:
                if name == selected_font:
                    font_id = fid
                    break

            result = self.engine.edit_text(self.current_page, block, new_text,
                                 new_size, new_color, font_id)

            if result:
                self._render_page()
                self._update_thumbnails()
                self._update_title()
                self.status_label.config(text=self.t("changes_applied"))
                editor.destroy()
            else:
                messagebox.showerror(self.t("error"), "Failed to edit text")

        def save_and_close():
            apply_changes()

        # Save button (prominent)
        save_btn = ModernButton(btn_frame, text=f"💾 {self.t('save')}", width=12,
                    command=save_and_close, tooltip="Save changes (Ctrl+S)")
        save_btn.pack(side="left", padx=20)
        save_btn.configure(bg=self.colors['success'])

        # Apply button
        ModernButton(btn_frame, text=f"✓ {self.t('apply')}", width=10,
                    command=apply_changes, tooltip="Apply changes").pack(side="left", padx=10)

        # Cancel button
        ModernButton(btn_frame, text=f"✗ {self.t('cancel')}", width=10,
                    command=editor.destroy, tooltip="Cancel").pack(side="right", padx=20)

        # Keyboard shortcuts
        editor.bind('<Control-s>', lambda e: save_and_close())
        editor.bind('<Escape>', lambda e: editor.destroy())

        # Focus on text widget
        text_widget.focus_set()

    def _get_font_info(self) -> str:
        """Get font info message based on language"""
        msgs = {
            "en": "For Arabic/Russian text, select the appropriate font",
            "ar": "للنص العربي، اختر خط Arabic (Noto)",
            "ru": "Для русского текста выберите шрифт Russian (Noto)"
        }
        return msgs.get(self.current_lang, msgs["en"])

    def _add_new_text(self, x: float, y: float):
        text = simpledialog.askstring(self.t("new_text"), self.t("enter_text"))
        if text:
            font_size = float(self.font_size_var.get())
            self.engine.add_text(self.current_page, x, y, text,
                                font_size, self.text_color, self.font_name)
            self._render_page()
            self._update_title()

    def _handle_select_click(self, x: float, y: float):
        block = self.engine.find_text_at(self.current_page, x, y)

        if block:
            self.selected_text = block
            c1 = self._pdf_to_canvas(block.rect.x0, block.rect.y0)
            c2 = self._pdf_to_canvas(block.rect.x1, block.rect.y1)
            self.canvas.delete("selection")
            self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1],
                                        outline=self.colors['accent'], width=2,
                                        dash=(4, 4), tags="selection")
            self.status_label.config(text=f"Selected: {block.text[:30]}..." if len(block.text) > 30 else f"Selected: {block.text}")
        else:
            self.selected_text = None
            self.canvas.delete("selection")
            self.status_label.config(text=self.t("ready"))

    def _handle_image_select(self, x: float, y: float):
        image = self.engine.find_image_at(self.current_page, x, y)

        if image:
            self.selected_image = image
            c1 = self._pdf_to_canvas(image.rect.x0, image.rect.y0)
            c2 = self._pdf_to_canvas(image.rect.x1, image.rect.y1)
            self.canvas.delete("selection")
            self.canvas.create_rectangle(c1[0], c1[1], c2[0], c2[1],
                                        outline=self.colors['success'], width=3, tags="selection")
            self.status_label.config(text=self.t("select_image"))
        else:
            self.selected_image = None
            self.canvas.delete("selection")
            images = self.engine.get_images(self.current_page)
            if not images:
                self.status_label.config(text=self.t("no_images"))

    def _rgb_to_hex(self, rgb):
        return "#{:02x}{:02x}{:02x}".format(
            int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    # ============ Help ============

    def show_shortcuts(self):
        shortcuts = """
╔═══════════════════════════════════╗
║       Keyboard Shortcuts          ║
╠═══════════════════════════════════╣
║  Ctrl+O     Open PDF              ║
║  Ctrl+S     Save PDF              ║
║  Ctrl+Z     Undo                  ║
║  Ctrl+Y     Redo                  ║
║  Ctrl+H     Find & Replace        ║
║  Ctrl++     Zoom In               ║
║  Ctrl+-     Zoom Out              ║
║  Ctrl+0     Actual Size           ║
║  Page Up    Previous Page         ║
║  Page Down  Next Page             ║
║  Home       First Page            ║
║  End        Last Page             ║
║  Delete     Delete Selection      ║
╚═══════════════════════════════════╝
        """
        messagebox.showinfo(self.t("shortcuts"), shortcuts)

    def show_about(self):
        about = f"""
╔═══════════════════════════════════════╗
║     {self.t("app_title")} v3.0          ║
║         Modern Edition                 ║
╠═══════════════════════════════════════╣
║                                        ║
║  ✓ Modern Dark Theme UI                ║
║  ✓ Tooltips for All Buttons            ║
║  ✓ Fast Text Editing                   ║
║  ✓ Optimized Image Operations          ║
║  ✓ Command-based Undo/Redo             ║
║  ✓ Page Caching & Lazy Loading         ║
║  ✓ Layer System                        ║
║  ✓ RTL Language Support                ║
║  ✓ Auto-save Functionality             ║
║  ✓ Multi-language UI (10 languages)    ║
║                                        ║
║  Supported Languages:                  ║
║  EN, AR, RU, ZH, ES, FR, DE, JA, KO, PT║
║                                        ║
║  Powered by:                           ║
║  Python + PyMuPDF + Tkinter            ║
╚═══════════════════════════════════════╝
        """
        messagebox.showinfo(self.t("about"), about)

    def show_memory_stats(self):
        stats = self.engine.get_memory_stats()
        msg = f"""
╔═══════════════════════════════════╗
║       Memory Statistics           ║
╠═══════════════════════════════════╣
║  Page Cache:                      ║
║    Entries: {stats['cache']['page_cache']['entries']:<20}║
║    Size: {stats['cache']['page_cache']['size_mb']:.2f} MB{' '*14}║
║    Hit Rate: {stats['cache']['page_cache']['hit_rate']:.1%}{' '*13}║
║                                   ║
║  Thumbnail Cache:                 ║
║    Entries: {stats['cache']['thumbnail_cache']['entries']:<20}║
║    Size: {stats['cache']['thumbnail_cache']['size_mb']:.2f} MB{' '*14}║
║                                   ║
║  Undo Memory: {stats['undo_memory'] / 1024:.1f} KB{' '*12}║
╚═══════════════════════════════════╝
        """
        messagebox.showinfo(self.t("memory_usage"), msg)

    def on_closing(self):
        if self.engine.modified:
            result = messagebox.askyesnocancel(
                self.t("save_changes"),
                self.t("unsaved_changes")
            )
            if result is None:
                return
            elif result:
                self.save_pdf()

        self.engine.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = PDFEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()