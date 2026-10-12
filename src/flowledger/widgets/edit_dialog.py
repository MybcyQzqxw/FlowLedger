"""Dialog for reviewing the workbook content and deleting rows (with undo)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..constants import HEADERS
from ..excel_store import ExcelError, ExcelStore, Record
from ..screenshots import ImagePlan, ImageResult, plan_image_deletions, trash_images
from .dialogs import confirm, show_error

_ALIGN = (
    Qt.AlignCenter, Qt.AlignLeft | Qt.AlignVCenter, Qt.AlignCenter, Qt.AlignCenter,
    Qt.AlignCenter, Qt.AlignLeft | Qt.AlignVCenter, Qt.AlignRight | Qt.AlignVCenter,
    Qt.AlignLeft | Qt.AlignVCenter,
)
_CHECKED_BG = QBrush(QColor("#fbd3df"))
_NO_BG = QBrush()


class EditDialog(QDialog):
    """Works on an in-memory copy; nothing touches the Excel file until 保存."""

    def __init__(
        self, store: ExcelStore, records: List[Record], target_dir: Optional[Path] = None, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("删改记录")
        self.resize(1200, 640)
        self.setMinimumSize(820, 420)

        self._store = store
        self._target_dir = target_dir
        self._original: List[Record] = list(records)
        self._original_count = len(records)
        self._records: List[Record] = list(records)
        self._undo: List[List[Record]] = []  # snapshots taken before each delete
        self.image_plan = ImagePlan()  # filled in after a successful save
        self.image_result = ImageResult()

        self._build_ui()
        self._populate()
        self._update_state()

    # -- result info for the caller ------------------------------------------
    @property
    def deleted_count(self) -> int:
        return self._original_count - len(self._records)

    @property
    def remaining_count(self) -> int:
        return len(self._records)

    # -- UI ----------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.select_all = QCheckBox("全选")
        self.select_all.clicked.connect(self._on_select_all)
        self.count_label = QLabel()
        self.total_label = QLabel()
        self.total_label.setStyleSheet("color: #c0123c; font-size: 16px; font-weight: bold;")

        top = QHBoxLayout()
        top.addWidget(self.select_all)
        top.addSpacing(16)
        top.addWidget(self.count_label)
        top.addStretch(1)
        top.addWidget(self.total_label)

        self.table = QTableWidget(0, len(HEADERS) + 1)
        self.table.setHorizontalHeaderLabels([""] + list(HEADERS))
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setShowGrid(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(len(HEADERS), QHeaderView.Stretch)  # 备注 takes the slack
        header.setMinimumSectionSize(46)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellClicked.connect(self._on_cell_clicked)

        self.empty_label = QLabel("表格中暂无记录")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #b98a97; font-size: 14px;")

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("DangerButton")
        self.undo_btn = QPushButton("撤销")
        self.cancel_btn = QPushButton("取消")
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("PrimaryButton")
        for btn in (self.delete_btn, self.undo_btn, self.cancel_btn, self.save_btn):
            btn.setMinimumSize(96, 36)
            btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setToolTip("删除已勾选的行（快捷键 Delete）")
        self.undo_btn.setToolTip("撤销上一步删除（快捷键 Ctrl+Z）")
        self.cancel_btn.setToolTip("放弃本次修改并关闭")
        self.save_btn.setToolTip("把修改写入 Excel，并将对应截图移入回收站")
        self.delete_btn.clicked.connect(self._on_delete)
        self.undo_btn.clicked.connect(self._on_undo)
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._on_save)

        buttons = QHBoxLayout()
        buttons.addWidget(self.delete_btn)
        buttons.addWidget(self.undo_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.save_btn)

        hint = QLabel("勾选要删除的行（点击行任意位置即可勾选），再点“删除”；确认无误后点“保存”，才会写入 Excel 并把对应截图移入回收站。")
        hint.setStyleSheet("color: #a58a94;")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty_label)
        layout.addWidget(hint)
        layout.addLayout(buttons)

        QShortcut(QKeySequence.Delete, self, activated=self._on_delete)
        QShortcut(QKeySequence.Undo, self, activated=self._on_undo)

    # -- table content ---------------------------------------------------------------
    @staticmethod
    def _cell_text(rec: Record, col: int) -> str:
        value = rec.to_row()[col]
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if col == 6:
            return f"{value:,.2f}"
        return str(value)

    @staticmethod
    def _padded(text: str, col: int) -> str:
        # item padding is avoided in the stylesheet (it leaves gaps in row highlights),
        # so left/right aligned text gets its breathing room from spaces instead
        if col in (1, 5, 7):
            return f"  {text}" if text else text
        if col == 6:
            return f"{text}  " if text else text
        return text

    def _populate(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._records))
        for r, rec in enumerate(self._records):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check.setCheckState(Qt.Unchecked)
            self.table.setItem(r, 0, check)
            for c in range(len(HEADERS)):
                text = self._cell_text(rec, c)
                item = QTableWidgetItem(self._padded(text, c))
                item.setFlags(Qt.ItemIsEnabled)
                item.setTextAlignment(int(_ALIGN[c]))
                item.setToolTip(text)
                self.table.setItem(r, c + 1, item)
        self.table.blockSignals(False)
        self.table.setColumnWidth(0, 52)
        for c in range(1, len(HEADERS)):
            self.table.resizeColumnToContents(c)
            self.table.setColumnWidth(c, self.table.columnWidth(c) + 24)

    def _checked_rows(self) -> List[int]:
        return [
            r for r in range(self.table.rowCount())
            if self.table.item(r, 0).checkState() == Qt.Checked
        ]

    def _paint_rows(self) -> None:
        checked = set(self._checked_rows())
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            brush = _CHECKED_BG if r in checked else _NO_BG
            for c in range(self.table.columnCount()):
                self.table.item(r, c).setBackground(brush)
        self.table.blockSignals(False)

    def _update_state(self) -> None:
        total_rows = self.table.rowCount()
        checked = len(self._checked_rows())
        amount = sum(rec.amount or 0 for rec in self._records)
        self.count_label.setText(f"共 {total_rows} 条　已选 {checked} 条")
        self.total_label.setText(f"金额总计：{amount:,.2f}")
        self.select_all.setEnabled(total_rows > 0)
        self.select_all.blockSignals(True)
        if total_rows and checked == total_rows:
            self.select_all.setCheckState(Qt.Checked)
        elif checked:
            self.select_all.setCheckState(Qt.PartiallyChecked)
        else:
            self.select_all.setCheckState(Qt.Unchecked)
        self.select_all.blockSignals(False)
        self.empty_label.setVisible(total_rows == 0)
        self.table.setVisible(total_rows > 0)
        self.delete_btn.setEnabled(checked > 0)
        self.undo_btn.setEnabled(bool(self._undo))
        self.save_btn.setEnabled(bool(self._undo))
        self._paint_rows()

    # -- interactions --------------------------------------------------------------------
    def _on_select_all(self, checked: bool) -> None:
        state = Qt.Checked if checked else Qt.Unchecked
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setCheckState(state)
        self.table.blockSignals(False)
        self._update_state()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            self._update_state()

    def _on_cell_clicked(self, row: int, column: int) -> None:
        # the checkbox column toggles itself; any other cell of the row toggles it too
        if column != 0:
            check = self.table.item(row, 0)
            check.setCheckState(Qt.Unchecked if check.checkState() == Qt.Checked else Qt.Checked)

    def _on_delete(self) -> None:
        rows = set(self._checked_rows())
        if not rows:
            return
        self._undo.append(list(self._records))
        self._records = [rec for i, rec in enumerate(self._records) if i not in rows]
        self._populate()
        self._update_state()

    def _on_undo(self) -> None:
        if not self._undo:
            return
        self._records = self._undo.pop()
        self._populate()
        self._update_state()

    def _on_save(self) -> None:
        if not self._undo:
            return
        n = self.deleted_count
        plan = plan_image_deletions(self._original, self._records, self._target_dir)
        lines = [f"将从 Excel 中永久删除 {n} 条记录。"]
        if plan.to_trash:
            lines.append(f"同时把截图目录中对应的 {len(plan.to_trash)} 张图片移入回收站。")
        skipped = len(plan.missing) + len(plan.ambiguous) + plan.unmapped
        if skipped:
            lines.append(f"另有 {skipped} 条记录没有可自动删除的图片（图片不存在，或同一时间金额有多条记录无法确定对应关系），将跳过。")
        if not plan.to_trash and not skipped and self._target_dir is None:
            lines.append("未指定有效的截图目录，不会删除任何图片。")
        lines.append("确定保存吗？")
        if not confirm(self, "保存修改", "\n".join(lines), ok_text="确定保存", cancel_text="再看看"):
            return
        try:
            self._store.replace_all(self._records)
        except ExcelError as exc:
            show_error(self, "保存失败", f"{exc}\n\n修改尚未写入，图片也未删除，可处理后再次点击“保存”。")
            return
        # only after the workbook is safely written do the screenshots go
        self.image_plan = plan
        self.image_result = trash_images(plan.to_trash)
        self.accept()

    def reject(self) -> None:  # also reached via Esc and the window close button
        if self._undo and not confirm(
            self, "放弃修改", "有尚未保存的删除操作，确定放弃并关闭吗？",
            ok_text="放弃修改", cancel_text="继续编辑",
        ):
            return
        super().reject()
