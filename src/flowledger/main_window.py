"""Main window: path pickers, drop area, action buttons and log console."""
from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from PySide6.QtCore import QEvent, QSettings, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    APP_NAME,
    DEFAULT_EXCEL_PATH,
    DEFAULT_TARGET_DIR,
    THUMBNAIL_SIZE,
    WINDOW_MIN_SIZE,
    WINDOW_TITLE,
)
from .image_utils import make_thumbnail, validate_image
from .widgets.console import ConsoleWidget
from .widgets.drop_area import DropArea
from .widgets.export_dialog import ExportDialog
from .widgets.path_picker import PathPicker
from .worker import UploadWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)
        self.setAcceptDrops(True)
        self._settings = QSettings(APP_NAME, APP_NAME, self)
        self._files: Dict[str, Path] = {}
        self._worker: Optional[UploadWorker] = None
        self._paste_dir: Optional[Path] = None  # holds images pasted as bitmaps (e.g. from WeChat)
        self._paste_count = 0

        self._build_ui()
        self._connect_signals()
        self._restore_settings()
        QApplication.instance().installEventFilter(self)
        self.console.info("就绪：请先指定 Excel 文件与截图存放目录，再添加截图并点击“上传”。")
        self.console.info("提示：点击拖放框可激活 Ctrl+V 粘贴微信等处复制的图片，再次点击取消。")

    # -- UI ----------------------------------------------------------------
    def _build_ui(self) -> None:
        self.excel_picker = PathPicker("file", "Excel 文件的绝对路径（可输入尚不存在的 .xlsx 新文件）", "选择文件…")
        self.dir_picker = PathPicker("dir", "截图存放目录的绝对路径", "选择目录…")
        self.drop_area = DropArea()

        self.upload_btn = QPushButton("上传")
        self.check_btn = QPushButton("检查")
        self.export_btn = QPushButton("导出")
        for btn in (self.upload_btn, self.check_btn, self.export_btn):
            btn.setMinimumHeight(34)
        self.upload_btn.setToolTip("识别截图并录入 Excel，同时将图片以“时间-金额”命名保存到截图目录")
        self.check_btn.setToolTip("用默认程序打开 Excel 文件")
        self.export_btn.setToolTip("将 Excel 文件导出到指定目录")

        self.console = ConsoleWidget()
        self.console.setMinimumHeight(150)

        excel_box = QGroupBox("Excel 文件")
        QVBoxLayout(excel_box).addWidget(self.excel_picker)
        dir_box = QGroupBox("截图存放目录")
        QVBoxLayout(dir_box).addWidget(self.dir_picker)
        drop_box = QGroupBox("待上传截图")
        QVBoxLayout(drop_box).addWidget(self.drop_area)
        console_box = QGroupBox("终端")
        QVBoxLayout(console_box).addWidget(self.console)

        buttons = QHBoxLayout()
        buttons.addWidget(self.upload_btn, 1)
        buttons.addWidget(self.check_btn, 1)
        buttons.addWidget(self.export_btn, 1)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(excel_box)
        layout.addWidget(dir_box)
        layout.addWidget(drop_box, 3)
        layout.addLayout(buttons)
        layout.addWidget(console_box, 2)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self.drop_area.add_files_requested.connect(self._on_add_files)
        self.drop_area.remove_item_requested.connect(self._on_remove_item)
        self.drop_area.paste_armed_changed.connect(self._on_paste_armed_changed)
        self.upload_btn.clicked.connect(self._on_upload)
        self.check_btn.clicked.connect(self._on_check)
        self.export_btn.clicked.connect(self._on_export)
        self.excel_picker.path_changed.connect(lambda p: self._settings.setValue("excel_path", p))
        self.dir_picker.path_changed.connect(lambda p: self._settings.setValue("target_dir", p))

    def _restore_settings(self) -> None:
        self.excel_picker.set_path(self._settings.value("excel_path", DEFAULT_EXCEL_PATH, str) or DEFAULT_EXCEL_PATH)
        self.dir_picker.set_path(self._settings.value("target_dir", DEFAULT_TARGET_DIR, str) or DEFAULT_TARGET_DIR)

    # -- adding / removing files -------------------------------------------------
    def _on_add_files(self, paths: List[str]) -> None:
        if self._worker is not None:
            self.console.warn("正在上传中，请等待完成后再添加截图")
            return
        existing = {os.path.normcase(str(p)) for p in self._files.values()}
        added = 0
        for raw in paths:
            path = Path(raw)
            ok, reason = validate_image(path)
            if not ok:
                self.console.warn(f"已拒绝 {path.name or raw}：{reason}")
                continue
            norm = os.path.normcase(str(path))
            if norm in existing:
                self.console.warn(f"已忽略 {path.name}：该文件已在列表中")
                continue
            existing.add(norm)
            item_id = uuid4().hex
            self._files[item_id] = path
            try:
                size_kb = path.stat().st_size / 1024
                subtitle = f"{path.parent}  ·  {size_kb:,.0f} KB"
            except OSError:
                subtitle = str(path.parent)
            self.drop_area.add_item(item_id, path.name, subtitle, make_thumbnail(path, THUMBNAIL_SIZE))
            added += 1
        if added:
            self.console.info(f"已添加 {added} 张截图，共 {len(self._files)} 张待上传")

    def _on_remove_item(self, item_id: str) -> None:
        if self._worker is not None:
            return
        path = self._files.pop(item_id, None)
        self.drop_area.remove_item(item_id)
        if path:
            self._discard_pasted(path)
            self.console.info(f"已移除 {path.name}")

    # -- Ctrl+V paste ----------------------------------------------------------------
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        # Paste is only active after the user clicked the drop box (it then shows highlighted).
        # Application-wide so it also works while a path box has focus; plain-text
        # clipboards still paste normally into text boxes.
        if (
            event.type() == QEvent.KeyPress
            and event.matches(QKeySequence.Paste)
            and self.drop_area.is_paste_armed()
            and QApplication.activeModalWidget() is None
            and self._is_own_focus()
        ):
            if self._clipboard_has_images():
                self._paste_from_clipboard()
                return True
            if not isinstance(QApplication.focusWidget(), QLineEdit):
                self.console.warn("剪贴板中没有图片或图片文件，请先在微信等处复制图片")
                return True
        return super().eventFilter(obj, event)

    def _on_paste_armed_changed(self, armed: bool) -> None:
        if armed:
            self.console.info("粘贴已激活：按 Ctrl+V 粘贴微信等处复制的图片（再次点击拖放框可取消）")
        else:
            self.console.info("粘贴已取消")

    def _is_own_focus(self) -> bool:
        widget = QApplication.focusWidget()
        return widget is not None and (widget is self or self.isAncestorOf(widget))

    @staticmethod
    def _clipboard_has_images() -> bool:
        mime = QGuiApplication.clipboard().mimeData()
        if mime is None:
            return False
        return mime.hasImage() or any(url.isLocalFile() for url in mime.urls())

    def _paste_from_clipboard(self) -> None:
        if self._worker is not None:
            self.console.warn("正在上传中，请等待完成后再粘贴")
            return
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        paths = [url.toLocalFile().replace("/", "\\") for url in mime.urls() if url.isLocalFile()]
        if not paths and mime.hasImage():
            image = clipboard.image()
            if image.isNull():
                self.console.warn("剪贴板中的图片无法读取")
                return
            try:
                if self._paste_dir is None:
                    self._paste_dir = Path(tempfile.mkdtemp(prefix="FlowLedger_paste_"))
                self._paste_count += 1
                name = f"粘贴图片_{datetime.now():%Y%m%d_%H%M%S}_{self._paste_count}.png"
                target = self._paste_dir / name
                if not image.save(str(target), "PNG"):
                    raise OSError("无法写入临时文件")
            except OSError as exc:
                self.console.error(f"粘贴失败：{exc}")
                return
            paths = [str(target)]
        self.console.info(f"检测到剪贴板中有 {len(paths)} 个图片/文件，正在添加…")
        self._on_add_files(paths)

    def _discard_pasted(self, path: Path) -> None:
        if self._paste_dir is not None and path.parent == self._paste_dir:
            path.unlink(missing_ok=True)

    # -- upload --------------------------------------------------------------------
    def _excel_path(self) -> Optional[Path]:
        text = self.excel_picker.path()
        if not text:
            self.console.error("请先指定 Excel 文件路径")
            return None
        path = Path(text)
        if path.suffix.lower() != ".xlsx":
            self.console.error("Excel 文件必须是 .xlsx 格式")
            return None
        return path

    def _on_upload(self) -> None:
        if self._worker is not None:
            return
        excel = self._excel_path()
        if excel is None:
            return
        target_text = self.dir_picker.path()
        if not target_text:
            self.console.error("请先指定截图存放目录")
            return
        target = Path(target_text)
        if target.exists() and not target.is_dir():
            self.console.error(f"截图存放位置不是目录：{target}")
            return
        if not excel.parent.is_dir():
            self.console.error(f"Excel 所在目录不存在：{excel.parent}")
            return
        if not self._files:
            self.console.warn("没有待上传的截图，请先添加截图")
            return
        if excel.exists() and target.exists() and excel.parent == target:
            self.console.warn("提示：Excel 文件与截图存放在同一目录")

        items = list(self._files.items())
        self._set_busy(True)
        self.console.info(f"开始上传，共 {len(items)} 张…")
        self._worker = UploadWorker(items, excel, target, self)
        self._worker.log.connect(self.console.log)
        self._worker.item_done.connect(self._on_item_done)
        self._worker.summary.connect(self._on_summary)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_item_done(self, item_id: str, status: str) -> None:
        # Recorded and duplicate items are handled; failures stay so they can be retried or removed.
        if status in ("added", "duplicate"):
            path = self._files.pop(item_id, None)
            self.drop_area.remove_item(item_id)
            if path:
                self._discard_pasted(path)

    def _on_summary(self, added: int, duplicate: int, failed: int) -> None:
        text = f"上传完成：成功 {added} 张，重复 {duplicate} 张，失败 {failed} 张"
        if failed or duplicate:
            self.console.warn(text)
        else:
            self.console.success(text)
        if failed:
            self.console.warn("失败的图片仍保留在列表中，可处理后重试或手动移除")

    def _on_worker_finished(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self.upload_btn.setEnabled(not busy)
        self.upload_btn.setText("上传中…" if busy else "上传")
        self.export_btn.setEnabled(not busy)
        self.drop_area.setEnabled(not busy)

    # -- check / export -----------------------------------------------------------------
    def _on_check(self) -> None:
        excel = self._excel_path()
        if excel is None:
            return
        if not excel.exists():
            self.console.warn(f"Excel 文件尚不存在：{excel}（上传第一张截图后会自动创建）")
            return
        try:
            os.startfile(str(excel))
            self.console.info(f"已打开 {excel}")
        except OSError as exc:
            self.console.error(f"无法打开 Excel 文件：{exc}")

    def _on_export(self) -> None:
        excel = self._excel_path()
        if excel is None:
            return
        if not excel.exists():
            self.console.error(f"Excel 文件不存在，无法导出：{excel}")
            return
        dialog = ExportDialog(self)
        if dialog.exec() != dialog.Accepted:
            self.console.info("已取消导出")
            return
        directory = Path(dialog.directory())
        if not dialog.directory() or not directory.is_dir():
            self.console.error(f"导出目录无效：{dialog.directory() or '(空)'}")
            return
        destination = directory / excel.name
        if destination.exists():
            if destination.resolve() == excel.resolve():
                self.console.warn("导出目录即 Excel 所在目录，无需导出")
                return
            answer = QMessageBox.question(
                self, "导出", f"{destination.name} 已存在于导出目录，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self.console.info("已取消导出")
                return
        try:
            shutil.copy2(excel, destination)
        except OSError as exc:
            self.console.error(f"导出失败：{exc}")
            return
        self.console.success(f"已导出到 {destination}")

    # -- drag & drop anywhere on the window -------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        paths = [url.toLocalFile().replace("/", "\\") for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self._on_add_files([p for p in paths if p])

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None:
            answer = QMessageBox.question(
                self, "退出", "正在上传中，退出可能导致部分截图未处理，确定退出吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self._worker.wait(30000)
        QApplication.instance().removeEventFilter(self)
        if self._paste_dir is not None:
            shutil.rmtree(self._paste_dir, ignore_errors=True)
        event.accept()
