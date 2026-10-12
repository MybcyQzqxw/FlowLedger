"""A simple read-only log console widget."""
from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtWidgets import QPlainTextEdit


class ConsoleWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)
        self.setStyleSheet(
            "QPlainTextEdit {"
            " background-color: #1e1e1e; color: #d4d4d4;"
            " font-family: Consolas, 'Courier New', monospace; font-size: 12px;"
            "}"
        )

    def _append(self, text: str, color: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.appendHtml(f'<span style="color:{color}">[{stamp}] {escape(text)}</span>')

    def info(self, text: str) -> None:
        self._append(text, "#d4d4d4")

    def success(self, text: str) -> None:
        self._append(text, "#6ac265")

    def warn(self, text: str) -> None:
        self._append(text, "#e5c07b")

    def error(self, text: str) -> None:
        self._append(text, "#e06c75")

    def log(self, level: str, text: str) -> None:
        getattr(self, level, self.info)(text)
