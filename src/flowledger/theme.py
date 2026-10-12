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
QPushButton#BigButton {{
    background-color: #d6819c;
    color: white;
    font-size: 18px;
    font-weight: bold;
    padding: 8px 20px;
}}
QPushButton#BigButton:hover:!disabled {{
    background-color: #c96b89;
}}
QPushButton#BigButton:pressed:!disabled {{
    background-color: #b95a78;
}}
QPushButton#BigButton:disabled {{
    background-color: #ecd3db;
    color: #fbf3f6;
}}
QPushButton#SmallButton {{
    background-color: #f6d9e2;
    color: {PINK_TEXT};
    font-weight: bold;
    padding: 6px 12px;
}}
QPushButton#SmallButton:hover:!disabled {{
    background-color: #efc3d2;
}}
QPushButton#SmallButton:pressed:!disabled {{
    background-color: #e8b2c5;
}}
QPushButton#SmallButton:disabled {{
    background-color: #f7ebef;
    color: #c9b3ba;
}}
QPushButton#DangerButton {{
    background-color: #d6819c;
    color: white;
    font-weight: bold;
}}
QPushButton#DangerButton:hover:!disabled {{
    background-color: #c0395f;
}}
QPushButton#DangerButton:disabled {{
    background-color: #ecd3db;
    color: #fbf3f6;
}}
QPushButton#PrimaryButton {{
    font-weight: bold;
}}
QCheckBox {{
    color: {PINK_TEXT};
    spacing: 8px;
}}
QCheckBox::indicator, QTableView::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {PINK_BUTTON_HOVER};
    border-radius: 3px;
    background-color: white;
}}
QCheckBox::indicator:checked, QTableView::indicator:checked {{
    background-color: #c2255c;
    border: 1px solid #c2255c;
}}
QCheckBox::indicator:indeterminate {{
    background-color: #efb3c6;
}}
QTableWidget {{
    background-color: white;
    alternate-background-color: #fff3f7;
    gridline-color: #f3dbe3;
    border: 1px solid {PINK_BORDER};
    border-radius: 4px;
    color: {PINK_TEXT};
}}
QTableWidget::item {{
    padding: 0px;
}}
QHeaderView::section {{
    background-color: {PINK_BUTTON};
    color: {PINK_TEXT};
    font-weight: bold;
    padding: 7px 6px;
    border: none;
    border-right: 1px solid #f3dbe3;
}}
QTableCornerButton::section {{
    background-color: {PINK_BUTTON};
    border: none;
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
