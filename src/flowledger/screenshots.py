"""Match Excel records to their archived screenshots and remove them together."""
from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QFile

from .excel_store import Record
from .worker import target_name


@dataclass
class ImagePlan:
    """What happens to screenshots when `deleted` records are removed."""

    to_trash: List[Path] = field(default_factory=list)  # found in the screenshot folder
    missing: List[str] = field(default_factory=list)  # expected file not present
    ambiguous: List[str] = field(default_factory=list)  # several records share one file name
    unmapped: int = 0  # record has no usable time/amount, so no file name can be derived


@dataclass
class ImageResult:
    trashed: List[str] = field(default_factory=list)
    failed: List[Tuple[str, str]] = field(default_factory=list)


def _mappable(rec: Record) -> bool:
    return isinstance(rec.time, datetime) and rec.amount is not None


def plan_image_deletions(
    original: Sequence[Record], remaining: Sequence[Record], target_dir: Optional[Path]
) -> ImagePlan:
    plan = ImagePlan()
    if target_dir is None or not target_dir.is_dir():
        return plan
    kept = {id(r) for r in remaining}
    deleted = [r for r in original if id(r) not in kept]
    # Records with identical time+amount share a base name (later uploads got "_2", "_3"...),
    # so which file belongs to which record is unknowable - never guess.
    name_counts = Counter(target_name(r) for r in original if _mappable(r))
    for rec in deleted:
        if not _mappable(rec):
            plan.unmapped += 1
            continue
        name = target_name(rec)
        if name_counts[name] > 1:
            plan.ambiguous.append(name)
            continue
        path = target_dir / name
        if path.is_file():
            plan.to_trash.append(path)
        else:
            plan.missing.append(name)
    return plan


def _move_to_trash(path: Path) -> None:
    result = QFile.moveToTrash(str(path))
    ok = result[0] if isinstance(result, tuple) else result
    if not ok:
        # e.g. network or removable drives have no recycle bin
        os.remove(path)


def trash_images(paths: Sequence[Path]) -> ImageResult:
    """Move files to the recycle bin (falls back to deleting where there is none)."""
    result = ImageResult()
    for path in paths:
        try:
            _move_to_trash(path)
            result.trashed.append(path.name)
        except OSError as exc:
            result.failed.append((path.name, str(exc)))
    return result
