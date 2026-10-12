"""Small helpers for Chinese-labelled message boxes."""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox


def confirm(parent, title: str, text: str, ok_text: str = "确定", cancel_text: str = "取消") -> bool:
    """Ask a yes/no question with Chinese button labels. Defaults to the safe (cancel) answer."""
    box = QMessageBox(QMessageBox.Question, title, text, QMessageBox.NoButton, parent)
    ok = box.addButton(ok_text, QMessageBox.AcceptRole)
    cancel = box.addButton(cancel_text, QMessageBox.RejectRole)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    return box.clickedButton() is ok


def show_error(parent, title: str, text: str) -> None:
    box = QMessageBox(QMessageBox.Critical, title, text, QMessageBox.NoButton, parent)
    box.addButton("知道了", QMessageBox.AcceptRole)
    box.exec()
