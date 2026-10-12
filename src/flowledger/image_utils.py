"""Image loading, validation and JPG conversion helpers (broad format support)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps, UnidentifiedImageError

try:  # HEIC/HEIF (common for phone screenshots)
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - depends on the installed wheel
    pillow_heif = None

Image.MAX_IMAGE_PIXELS = None

_COMMON_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".bmp", ".dib", ".gif", ".webp",
    ".tif", ".tiff", ".heic", ".heif", ".avif", ".jp2", ".j2k", ".ico", ".tga", ".ppm",
)
_JPEG_QUALITY = 95


def dialog_filter() -> str:
    """File-dialog filter built from the extensions this Pillow build can really open."""
    Image.init()
    known = {e.lower() for e in Image.registered_extensions()}
    patterns = " ".join(f"*{e}" for e in _COMMON_EXTENSIONS if e in known)
    return f"图片文件 ({patterns});;所有文件 (*.*)"


def validate_image(path: Path) -> Tuple[bool, Optional[str]]:
    """Return (ok, reason). Judged by file content, not by extension."""
    if not path.exists():
        return False, "文件不存在"
    if path.is_dir():
        return False, "这是一个文件夹，不是图片文件"
    try:
        with Image.open(path) as img:
            img.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, MemoryError):
        return False, f"不是有效的图片文件（{path.suffix or '无扩展名'}）"
    return True, None


def save_as_jpg(src: Path, dest: Path) -> None:
    """Write `src` to `dest` as JPEG. Plain upright JPEGs are copied bit-for-bit."""
    with Image.open(src) as img:
        upright = img.getexif().get(0x0112, 1) in (1, None)
        if img.format == "JPEG" and upright:
            shutil.copyfile(src, dest)
            return
    load_rgb(src).save(dest, "JPEG", quality=_JPEG_QUALITY, subsampling=0, optimize=True)



def load_rgb(path: Path) -> Image.Image:
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background
        return img.convert("RGB")


def make_thumbnail(path: Path, size: int):
    """Return a QPixmap thumbnail (null pixmap on failure)."""
    from PySide6.QtGui import QImage, QPixmap

    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((size * 2, size * 2))
            rgba = img.convert("RGBA")
            data = rgba.tobytes("raw", "RGBA")
            qimg = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg.copy())
    except Exception:
        return QPixmap()
