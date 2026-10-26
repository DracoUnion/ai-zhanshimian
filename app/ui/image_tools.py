"""图片工具：上传前 Pillow 压缩（对齐原前端 canvas 压缩，最大 1200x1700, q0.82）。"""
from __future__ import annotations

import io
import os

CONTENT_TYPE_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heic",
}


def content_type_for(path: str) -> str | None:
    return CONTENT_TYPE_BY_EXT.get(os.path.splitext(path)[1].lower())


def compress_image_bytes(path: str, max_w: int = 1200, max_h: int = 1700, quality: int = 82) -> tuple[bytes, str]:
    """读取并压缩为 JPEG 字节，返回 (bytes, content_type)。"""
    from PIL import Image

    from core.errors import BizError, ErrCode

    ct = content_type_for(path)
    if ct is None:
        raise BizError(ErrCode.UPLOAD_INVALID, "仅支持 JPG/PNG/WebP/HEIC 图片")
    try:
        img = Image.open(path)
        img = img.convert("RGB")
        img.thumbnail((max_w, max_h), Image.LANCZOS)
    except Exception:  # noqa: BLE001
        raise BizError(ErrCode.UPLOAD_INVALID, "图片读取失败，请换一张")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue(), "image/jpeg"