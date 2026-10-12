"""Path input row: editable absolute path on the left, browse button on the right."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget


class PathPicker(QWidget):
    """`mode` is "file" (Excel workbook, may not exist yet) or "dir"."""

    path_changed = Signal(str)

    def __init__(self, mode: str, placeholder: str, button_text: str, parent=None):
        super().__init__(parent)
        self._mode = mode

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)
        self.edit.editingFinished.connect(lambda: self.path_changed.emit(self.path()))

        browse = QPushButton(button_text)
        browse.clicked.connect(self._on_browse)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(browse)

    def path(self) -> str:
        return self.edit.text().strip().strip('"')

    def set_path(self, path: str) -> None:
        self.edit.setText(path)

    def _on_browse(self) -> None:
        current = self.path()
        if self._mode == "file":
            chosen, _ = QFileDialog.getSaveFileName(
                self,
                "选择 Excel 文件（可选择已有文件，或输入新文件名）",
                current,
                "Excel 工作簿 (*.xlsx)",
                options=QFileDialog.DontConfirmOverwrite,
            )
        else:
            chosen = QFileDialog.getExistingDirectory(self, "选择截图存放目录", current)
        if chosen:
            self.set_path(chosen.replace("/", "\\"))
            self.path_changed.emit(self.path())
