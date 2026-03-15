<div align="center">

# 📄 PDF Editor Pro v3.0 — Modern Edition

**Full-featured PDF editor with modern dark UI, layer system, command-based undo/redo, and 10-language support.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://python.org)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.23%2B-orange)](https://pymupdf.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-green)]()
[![GUI](https://img.shields.io/badge/GUI-Tkinter-lightblue)]()

</div>

---

## ✨ Features

### 🖊️ Text Editing
- Click any text to edit it directly
- Font selection with Arabic / Russian / CJK support
- Font size, color picker
- RTL (Right-to-Left) layout for Arabic

### 🎨 Drawing & Annotation
- Rectangle, Circle, Line, Arrow
- Freehand drawing
- Highlight, Underline, Strikeout

### 🖼️ Image Operations
- Insert images anywhere
- Select, move, resize, scale, rotate images
- Replace or extract images
- Right-click context menu for images

### 📑 Page Management
- Add, delete, rotate pages
- Extract specific pages to new PDF
- Merge multiple PDFs
- Thumbnail panel with click-to-navigate

### 🏗️ Architecture
| Feature | Details |
|---|---|
| **Layer System** | Every edit is a separate layer — selectable and deletable |
| **Command-based Undo/Redo** | Full history with 50 states |
| **LRU Page Cache** | Smart caching with lazy loading for fast rendering |
| **Auto-save** | Background auto-save protection |
| **Memory Monitor** | Live cache/memory statistics in status bar |

### 🌍 10 UI Languages
English · Arabic (RTL) · Russian · Chinese · Spanish · French · German · Japanese · Korean · Portuguese

---

## 🖥️ Screenshots

> _Coming soon_

---

## 🚀 Quick Start

### 1. Clone
```bash
git clone https://github.com/Hayder-IRAQ/pdf-editor-pro.git
cd pdf-editor-pro
```

### 2. Virtual environment (recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run
```bash
python main.py
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `PyMuPDF` | PDF rendering and editing engine |
| `Pillow` | Image processing for page display |
| `tkinter` | GUI framework *(built into Python)* |

```bash
pip install PyMuPDF Pillow
```

---

## 🗂️ Project Structure

```
pdf-editor-pro/
├── main.py              # Application entry point & UI
├── requirements.txt
├── LICENSE
├── README.md
└── core/
    ├── pdf_engine.py    # Core PDF operations (open, save, edit, render)
    ├── text_editor.py   # Advanced text analysis and editing
    ├── undo_manager.py  # Command-based undo/redo system
    ├── cache_system.py  # LRU page cache + auto-save manager
    ├── layer_system.py  # Layer management (shapes, annotations, text)
    ├── tools.py         # Tool enums, constants, default colors
    ├── fonts.py         # Font management (Latin, Arabic, Russian, CJK)
    ├── languages.py     # i18n strings for 10 languages
    └── image_block.py   # Image block dataclass
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open PDF |
| `Ctrl+S` | Save |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+H` | Find & Replace |
| `Ctrl++` | Zoom In |
| `Ctrl+-` | Zoom Out |
| `Ctrl+0` | Reset Zoom |
| `Page Up` | Previous Page |
| `Page Down` | Next Page |
| `Home` | First Page |
| `End` | Last Page |
| `Delete` | Delete Selection |
| `Double-click` | Edit text / select image |
| `Right-click` | Context menu |

---

## 🏗️ Architecture Overview

```
PDFEditorApp (main.py)
    │
    ├── PDFEngine (core/pdf_engine.py)
    │       ├── UndoManager      — command history
    │       ├── PageCache        — LRU rendering cache
    │       ├── LayerManager     — per-page layer tracking
    │       └── TextAnalyzer     — text block detection
    │
    └── UI Layer (main.py)
            ├── Toolbar          — tools, fonts, colors
            ├── Canvas           — page rendering + events
            ├── Thumbnails Panel — page navigation
            └── Properties Panel — layers listbox
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m "feat: describe your change"`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Hayder Odhafa / حيدر عذافة**
GitHub: [@Hayder-IRAQ](https://github.com/Hayder-IRAQ)

---

<div align="center">
Made with ❤️ using Python + PyMuPDF — PDF Editor Pro v3.0 © 2025 Hayder Odhafa
</div>
