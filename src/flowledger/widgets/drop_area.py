"""Drag-and-drop image list with per-item delete controls."""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..constants import THUMBNAIL_SIZE
from ..image_utils import dialog_filter
from ..theme import (
    DROP_ARMED as _ARMED_STYLE,
    DROP_HOVER as _HOVER_STYLE,
    DROP_IDLE as _IDLE_STYLE,
    HINT_ARMED,
    HINT_IDLE,
    PLACEHOLDER_COLOR,
    THUMB_BG,
)

_ITEM_ID_ROLE = Qt.UserRole + 1


class _ImageRow(QWidget):
    """One row in the drop list: thumbnail + name + status + delete button."""

    delete_requested = Signal(str)

    def __init__(self, item_id: str, display_name: str, subtitle: str, thumbnail: QPixmap, parent=None):
        super().__init__(parent)
        self._item_id = item_id

        thumb_label = QLabel()
        thumb_label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setStyleSheet(f"background-color: {THUMB_BG}; border-radius: 3px;")
        if not thumbnail.isNull():
            thumb_label.setPixmap(
                thumbnail.scaled(THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        name_label = QLabel(display_name)
        name_label.setStyleSheet("font-weight: bold;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #888; font-size: 11px;")
        text_layout.addWidget(name_label)
        text_layout.addWidget(subtitle_label)

        delete_btn = QToolButton()
        delete_btn.setText("\u2715")
        delete_btn.setToolTip("移除该图片")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(
            "QToolButton { color: #d16969; border: none; font-weight: bold; }"
            "QToolButton:hover { color: #ff5555; }"
        )
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._item_id))
        self.delete_btn = delete_btn

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.addWidget(thumb_label)
        layout.addLayout(text_layout, 1)
        layout.addWidget(delete_btn)


class DropArea(QWidget):
    """Accepts images via drag-and-drop, a file browser, or manual paths."""

    add_files_requested = Signal(list)
    remove_item_requested = Signal(str)
    paste_armed_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._armed = False
        self._hover = False

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.setSpacing(2)
        self.list_widget.setStyleSheet(_IDLE_STYLE)
        self.list_widget.setAcceptDrops(False)

        self._placeholder = QLabel("将截图拖拽到此处（可多选，仅支持图片格式），或使用下方按钮添加\n点击此框可激活 Ctrl+V 粘贴")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(f"color: {PLACEHOLDER_COLOR};")
        self._placeholder.setWordWrap(True)

        self._paste_hint = QLabel("点击上方框可激活 Ctrl+V 粘贴")
        self._paste_hint.setStyleSheet(HINT_IDLE)

        # clicks inside the box (list, rows, placeholder) bubble up to the viewport
        self.list_widget.viewport().installEventFilter(self)

        # the hint sits centred inside the box itself
        inside = QVBoxLayout(self.list_widget.viewport())
        inside.setContentsMargins(12, 12, 12, 12)
        inside.addWidget(self._placeholder)

        browse_btn = QPushButton("浏览文件…")
        browse_btn.clicked.connect(self._on_browse)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("或输入图片文件路径，多个路径用分号分隔，回车添加")
        self.path_edit.returnPressed.connect(self._on_manual_add)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._on_manual_add)

        manual_row = QHBoxLayout()
        manual_row.addWidget(self.path_edit, 1)
        manual_row.addWidget(add_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self._paste_hint)
        layout.addWidget(browse_btn)
        layout.addLayout(manual_row)

        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._sync_placeholder()

    # -- public API ---------------------------------------------------
    def add_item(self, item_id: str, display_name: str, subtitle: str, thumbnail: QPixmap) -> None:
        row = _ImageRow(item_id, display_name, subtitle, thumbnail)
        row.delete_requested.connect(self.remove_item_requested)

        item = QListWidgetItem(self.list_widget)
        item.setData(_ITEM_ID_ROLE, item_id)
        item.setSizeHint(row.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, row)
        self._sync_placeholder()

    def remove_item(self, item_id: str) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(_ITEM_ID_ROLE) == item_id:
                self.list_widget.takeItem(i)
                break
        self._sync_placeholder()

    def clear(self) -> None:
        self.list_widget.clear()
        self._sync_placeholder()

    def count(self) -> int:
        return self.list_widget.count()

    def is_paste_armed(self) -> bool:
        return self._armed

    def set_paste_armed(self, armed: bool) -> None:
        if armed == self._armed:
            return
        self._armed = armed
        self._apply_style()
        if armed:
            self._paste_hint.setText("● 粘贴已激活：现在按 Ctrl+V 可粘贴截图（再次点击上方框取消）")
            self._paste_hint.setStyleSheet(HINT_ARMED)
        else:
            self._paste_hint.setText("点击上方框可激活 Ctrl+V 粘贴")
            self._paste_hint.setStyleSheet(HINT_IDLE)
        self.paste_armed_changed.emit(armed)

    # -- internals ------------------------------------------------------
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        # A left click anywhere inside the box toggles paste mode.
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.set_paste_armed(not self._armed)
        return super().eventFilter(obj, event)

    def _apply_style(self) -> None:
        if self._hover:
            style = _HOVER_STYLE
        elif self._armed:
            style = _ARMED_STYLE
        else:
            style = _IDLE_STYLE
        self.list_widget.setStyleSheet(style)

    def _sync_placeholder(self) -> None:
        self._placeholder.setVisible(self.list_widget.count() == 0)

    def _on_browse(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择截图",
            "",
            dialog_filter(),
        )
        if paths:
            self.add_files_requested.emit([p.replace("/", "\\") for p in paths])

    def _on_manual_add(self) -> None:
        text = self.path_edit.text().strip()
        if not text:
            return
        paths = [p.strip().strip('"') for p in text.replace("；", ";").split(";") if p.strip()]
        if paths:
            self.add_files_requested.emit(paths)
        self.path_edit.clear()

    # -- drag & drop ------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._hover = True
            self._apply_style()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self._apply_style()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._hover = False
        self._apply_style()
        paths = [url.toLocalFile().replace("/", "\\") for url in event.mimeData().urls() if url.isLocalFile()]
        paths = [p for p in paths if p]
        if paths:
            self.add_files_requested.emit(paths)
            event.acceptProposedAction()
