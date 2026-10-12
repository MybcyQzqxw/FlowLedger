"""Light-pink theme shared by the main window and its child dialogs."""

PINK_BG = "#fff7f9"
PINK_BORDER = "#ecc4d1"
PINK_BUTTON = "#e3a8ba"
PINK_BUTTON_HOVER = "#d88fa5"
PINK_BUTTON_PRESSED = "#cf7f98"
PINK_TEXT = "#5c2436"
PINK_TITLE = "#a24b68"

APP_STYLE = f"""
QMainWindow, QDialog {{
    background-color: {PINK_BG};
}}
QGroupBox {{
    border: 1px solid {PINK_BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 6px;
    background-color: #fffbfc;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    color: {PINK_TITLE};
    font-weight: bold;
}}
QLabel {{
    color: {PINK_TEXT};
}}
QLineEdit {{
    background-color: white;
    border: 1px solid {PINK_BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: {PINK_BUTTON};
    selection-color: {PINK_TEXT};
}}
QLineEdit:focus {{
    border: 1px solid {PINK_BUTTON_HOVER};
    background-color: #fffdfe;
}}
QPushButton {{
    background-color: {PINK_BUTTON};
    color: {PINK_TEXT};
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
}}
QPushButton:hover:!disabled {{
    background-color: {PINK_BUTTON_HOVER};
}}
QPushButton:pressed:!disabled {{
    background-color: {PINK_BUTTON_PRESSED};
}}
QPushButton:disabled {{
    background-color: #f2e2e7;
    color: #bda0a8;
}}
QPushButton#ActionButton {{
    font-weight: bold;
    padding: 8px 20px;
}}
"""

# Drop box states
DROP_IDLE = (
    "QListWidget { background-color: #fdf3f6; border: 1px dashed #d88fa5; border-radius: 4px; }"
    "QListWidget::item:selected { background-color: #f4d9e2; color: black; }"
)
DROP_HOVER = (
    "QListWidget { background-color: #fbe6ed; border: 2px dashed #d6457a; border-radius: 4px; }"
    "QListWidget::item:selected { background-color: #f4d9e2; color: black; }"
)
DROP_ARMED = (
    "QListWidget { background-color: #ffe3ec; border: 2px solid #c2255c; border-radius: 4px; }"
    "QListWidget::item:selected { background-color: #f4d9e2; color: black; }"
)
THUMB_BG = "#f3dee5"
PLACEHOLDER_COLOR = "#b98a97"
HINT_IDLE = "color: #a58a94;"
HINT_ARMED = "color: #c2255c; font-weight: bold;"
