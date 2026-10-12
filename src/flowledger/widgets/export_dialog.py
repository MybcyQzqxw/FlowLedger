"""Dialog asking for the export directory (defaults to the desktop)."""
from __future__ import annotations

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


def desktop_path() -> str:
    path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
    return path.replace("/", "\\")


class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出 Excel")
        self.setMinimumWidth(520)

        self.edit = QLineEdit(desktop_path())
        browse = QPushButton("选择目录…")
        browse.clicked.connect(self._on_browse)

        row = QHBoxLayout()
        row.addWidget(self.edit, 1)
        row.addWidget(browse)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("请选择导出目录（默认为桌面）："))
        layout.addLayout(row)
        layout.addWidget(buttons)

    def directory(self) -> str:
        return self.edit.text().strip().strip('"')

    def _on_browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "选择导出目录", self.directory())
        if chosen:
            self.edit.setText(chosen.replace("/", "\\"))
