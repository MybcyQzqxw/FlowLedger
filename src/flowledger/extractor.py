"""Screenshot -> Record: offline OCR (RapidOCR) plus layout-aware field parsing."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .excel_store import Record, parse_amount, parse_datetime


class ExtractError(Exception):
    """Raised when the screenshot cannot be turned into a valid record."""


@dataclass
class TextBox:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class ExtractResult:
    record: Record
    warnings: List[str]


# Label synonyms per field, matched on the left column of the screenshot.
LABELS: Dict[str, Tuple[str, ...]] = {
    "amount": ("收入金额", "转入金额", "入账金额", "到账金额", "交易金额"),
    "name": ("对方名称", "付款方名称", "付款人名称", "付款户名", "对方户名", "对方姓名", "付款人"),
    "account": ("对方账号", "对方账户", "付款方账号", "付款人账号", "付款账号", "付款账户"),
    "time": ("交易时间", "交易日期"),
    "type": ("交易类型", "业务类型"),
    "channel": ("交易渠道", "渠道"),
    "memo": ("附言", "摘要", "用途", "备注"),
}
FIELD_TITLES = {
    "amount": "收入金额",
    "name": "付款方名称",
    "account": "付款方账号",
    "time": "交易时间",
    "type": "交易类型",
    "channel": "交易渠道",
    "memo": "附言",
}
CONTINUATION_FIELDS = {"name", "type", "channel", "memo"}
_AMOUNT_RE = re.compile(r"[+＋-]?\s*(?:人民币|RMB|CNY|¥|￥)?\s*\d[\d,，.]*[.,]\d{2}")
_ACCOUNT_RE = re.compile(r"[\d*＊xX•●·]{4,}")
_SEPARATORS = re.compile(r"[:：;；,，|/\\\s]+")


def _normalize(text: str) -> str:
    return re.sub(r"[\s/／:：]+", "", text)


def _match_label(box: TextBox, width: float) -> Optional[Tuple[str, str]]:
    """Return (field, inline_value) when `box` is a field label in the left half."""
    if box.x0 > width * 0.45:
        return None
    norm = _normalize(box.text)
    for field, synonyms in LABELS.items():
        for syn in sorted(synonyms, key=len, reverse=True):
            if norm.startswith(syn):
                rest = norm[len(syn):]
                if field == "amount" or len(rest) <= 4:
                    return field, ""
                return field, rest
    return None


def _same_row(a: TextBox, b: TextBox) -> bool:
    overlap = min(a.y1, b.y1) - max(a.y0, b.y0)
    return overlap > 0.4 * min(a.height, b.height)


def meaningful_text(remark: str) -> str:
    """Drop digits and symbols from the remark, keeping the meaningful words."""
    segments = [re.sub(r"[\d_]|[^\w]", "", s) for s in _SEPARATORS.split(remark)]
    segments = [s for s in segments if s]
    with_cjk = [s for s in segments if re.search(r"[\u4e00-\u9fff]", s)]
    if with_cjk:
        return "".join(with_cjk)
    return "".join(s for s in segments if len(s) >= 2)


def _first_amount(text: str) -> Optional[float]:
    m = _AMOUNT_RE.search(text)
    return parse_amount(m.group(0)) if m else None


def _collect_value(label: TextBox, field: str, boxes: Sequence[TextBox], labels: Sequence[TextBox]) -> str:
    """Value text to the right of `label`, including wrapped continuation lines."""
    taken = [
        b for b in boxes
        if b is not label and b not in labels and _same_row(label, b) and b.x0 >= label.x1 - 5
    ]
    taken.sort(key=lambda b: b.x0)
    if not taken:
        return ""
    lines = [b.text for b in taken]
    if field in CONTINUATION_FIELDS:
        bottom = max(b.y1 for b in taken)
        line_h = sum(b.height for b in taken) / len(taken)
        below = sorted(
            (b for b in boxes if b is not label and b not in labels and b not in taken
             and b.x0 >= label.x1 - 5 and b.y0 >= bottom - 2),
            key=lambda b: b.y0,
        )
        for b in below:
            if b.y0 - bottom > 0.9 * line_h:
                break
            lines.append(b.text)
            bottom = max(bottom, b.y1)
    return "".join(lines).strip()


def parse_boxes(boxes: Sequence[TextBox], width: float) -> ExtractResult:
    """Turn OCR boxes of a bank 'income detail' screenshot into a Record."""
    labels: List[TextBox] = []
    label_field: Dict[int, Tuple[str, str]] = {}
    for b in boxes:
        hit = _match_label(b, width)
        if hit:
            labels.append(b)
            label_field[id(b)] = hit

    found: Dict[str, Tuple[TextBox, str]] = {}
    for b in sorted(labels, key=lambda b: b.y0):
        field, inline = label_field[id(b)]
        found.setdefault(field, (b, inline))

    full_text = "\n".join(b.text for b in boxes)
    if "amount" not in found and re.search(r"支出金额|转出金额|付款金额", full_text):
        raise ExtractError("该截图看起来是支出记录，不是进账记录")

    warnings: List[str] = []

    def value_of(field: str) -> str:
        if field not in found:
            return ""
        label, inline = found[field]
        value = _collect_value(label, field, boxes, labels)
        return value or inline

    # time
    time_value = None
    if "time" in found:
        time_value = parse_datetime(value_of("time"))
    if time_value is None:
        for b in sorted(boxes, key=lambda b: (b.y0, b.x0)):
            if b in labels or re.match(r"^[“\"']", b.text.strip()):
                continue
            time_value = parse_datetime(b.text)
            if time_value:
                warnings.append("未能直接定位“交易时间”，已使用截图中出现的第一个完整时间")
                break
    if time_value is None:
        raise ExtractError("未能识别交易时间")

    # amount
    amount: Optional[float] = None
    if "amount" in found:
        label, inline = found["amount"]
        row = [b for b in boxes if b is not label and _same_row(label, b) and b.x0 >= label.x1 - 5]
        for b in sorted(row, key=lambda b: b.x0):
            amount = _first_amount(b.text)
            if amount is not None:
                break
        if amount is None:
            below = sorted(
                (b for b in boxes if b not in labels and b.y0 >= label.y1 - 5 and b.y0 - label.y1 < 6 * label.height),
                key=lambda b: (b.y0, b.x0),
            )
            for b in below:
                amount = _first_amount(b.text)
                if amount is not None:
                    break
    if amount is None:
        numeric = [(b.height, b) for b in boxes if re.fullmatch(_AMOUNT_RE, b.text.strip())]
        if numeric:
            amount = parse_amount(max(numeric, key=lambda t: t[0])[1].text)
            warnings.append("未能直接定位“收入金额”，已使用截图中字号最大的金额")
    if amount is None:
        raise ExtractError("未能识别收入金额")

    # text fields
    name = value_of("name")
    account_text = value_of("account")
    accounts = _ACCOUNT_RE.findall(account_text.replace(" ", ""))
    account = max(accounts, key=len) if accounts else ""
    tx_type = value_of("type")
    channel = value_of("channel")
    remark = value_of("memo")

    for field, value in (("name", name), ("account", account), ("type", tx_type), ("channel", channel)):
        if not value:
            warnings.append(f"未识别到“{FIELD_TITLES[field]}”，该列将留空")
    if not remark:
        if "memo" in found:
            warnings.append("“附言”内容为空，备注与具体信息将留空")
        else:
            warnings.append("截图中没有“附言”，备注与具体信息留空")

    record = Record(
        time=time_value,
        payer_name=name,
        payer_account=account,
        tx_type=tx_type,
        channel=channel,
        detail=meaningful_text(remark),
        amount=amount,
        remark=remark,
    )
    return ExtractResult(record, warnings)


class OcrExtractor:
    """Lazily creates the OCR engine (model loading takes a few seconds)."""

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    def warm_up(self) -> None:
        self._get_engine()

    def extract(self, path: Path) -> ExtractResult:
        import numpy as np

        from .image_utils import load_rgb

        try:
            image = load_rgb(path)
        except Exception as exc:
            raise ExtractError(f"无法读取图片：{exc}")
        longest = max(image.size)
        if longest > 4000:
            scale = 4000 / longest
            image = image.resize((int(image.width * scale), int(image.height * scale)))
        array = np.asarray(image)[:, :, ::-1].copy()  # RGB -> BGR for OpenCV based OCR

        try:
            result, _ = self._get_engine()(array)
        except Exception as exc:
            raise ExtractError(f"OCR 识别失败：{exc}")
        if not result:
            raise ExtractError("未在图片中识别到任何文字")

        boxes = []
        for points, text, _score in result:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            boxes.append(TextBox(min(xs), min(ys), max(xs), max(ys), str(text).strip()))
        return parse_boxes([b for b in boxes if b.text], float(image.width))
