"""Background upload pipeline: OCR -> dedupe -> copy screenshot -> write Excel."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import QThread, Signal

from .excel_store import ExcelError, ExcelStore, Record
from .extractor import ExtractError, OcrExtractor
from .image_utils import save_as_jpg


def target_name(record: Record) -> str:
    """`时间-金额.jpg` file name, e.g. 20260930_101630-3286.45.jpg"""
    stamp = record.time.strftime("%Y%m%d_%H%M%S") if isinstance(record.time, datetime) else "unknown"
    return f"{stamp}-{record.amount:.2f}.jpg"


def unique_path(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    n = 2
    while (directory / f"{stem}_{n}{suffix}").exists():
        n += 1
    return directory / f"{stem}_{n}{suffix}"


class UploadWorker(QThread):
    log = Signal(str, str)  # level, message
    item_done = Signal(str, str)  # item id, status: added | duplicate | failed
    summary = Signal(int, int, int)  # added, duplicate, failed

    def __init__(self, items: List[Tuple[str, Path]], excel_path: Path, target_dir: Path, parent=None):
        super().__init__(parent)
        self._items = items
        self._store = ExcelStore(excel_path)
        self._target_dir = target_dir
        self._extractor = OcrExtractor()

    def run(self) -> None:
        added = duplicate = failed = 0
        try:
            self._store.check_writable()
        except ExcelError as exc:
            self.log.emit("error", str(exc))
            self.summary.emit(0, 0, len(self._items))
            for item_id, _ in self._items:
                self.item_done.emit(item_id, "failed")
            return

        self.log.emit("info", "正在加载 OCR 模型…")
        try:
            self._extractor.warm_up()
        except Exception as exc:
            self.log.emit("error", f"OCR 模型加载失败：{exc}")
            self.summary.emit(0, 0, len(self._items))
            for item_id, _ in self._items:
                self.item_done.emit(item_id, "failed")
            return

        total = len(self._items)
        for index, (item_id, path) in enumerate(self._items, start=1):
            prefix = f"[{index}/{total}] {path.name}"
            self.log.emit("info", f"{prefix}：开始识别…")
            status = self._process(prefix, path)
            self.item_done.emit(item_id, status)
            if status == "added":
                added += 1
            elif status == "duplicate":
                duplicate += 1
            else:
                failed += 1
        self.summary.emit(added, duplicate, failed)

    def _process(self, prefix: str, path: Path) -> str:
        try:
            result = self._extractor.extract(path)
        except ExtractError as exc:
            self.log.emit("error", f"{prefix}：{exc}，已跳过")
            return "failed"
        except Exception as exc:  # never let one image kill the whole batch
            self.log.emit("error", f"{prefix}：识别出现异常：{exc}")
            return "failed"

        record = result.record
        for warning in result.warnings:
            self.log.emit("warn", f"{prefix}：{warning}")

        copied = None
        try:
            dup_row = self._store.find_duplicate(record)
            if dup_row is not None:
                when = record.time.strftime("%Y-%m-%d %H:%M:%S")
                self.log.emit(
                    "warn",
                    f"{prefix}：重复！与表格第 {dup_row} 行相同（{when}，{record.amount:,.2f}），未录入，图片未上传",
                )
                return "duplicate"

            self._target_dir.mkdir(parents=True, exist_ok=True)
            copied = unique_path(self._target_dir, target_name(record))
            save_as_jpg(path, copied)
            row_no = self._store.add(record)
            if row_no is None:
                copied.unlink(missing_ok=True)
                self.log.emit("warn", f"{prefix}：重复！与表格中已有记录相同，未录入，图片未上传")
                return "duplicate"
        except ExcelError as exc:
            if copied is not None:
                copied.unlink(missing_ok=True)
            self.log.emit("error", f"{prefix}：{exc}；图片未上传")
            return "failed"
        except (OSError, ValueError) as exc:
            if copied is not None:
                copied.unlink(missing_ok=True)
            self.log.emit("error", f"{prefix}：保存图片失败：{exc}")
            return "failed"

        when = record.time.strftime("%Y-%m-%d %H:%M:%S")
        self.log.emit(
            "success",
            f"{prefix}：已录入第 {row_no} 行（{when}，{record.payer_name or '—'}，+{record.amount:,.2f}），图片已保存为 {copied.name}",
        )
        return "added"
