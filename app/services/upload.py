"""上传服务（桌面端直传本地存储）：校验类型/大小 → 生成对象键 → 落盘。"""
from __future__ import annotations

from uuid import uuid4

from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.services.storage import get_storage

settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
}


class UploadService:
    """上传门面：UI 传入图片字节，直接保存在本机账户命名空间。"""

    def save_image(self, user_id: int, kind: str, data: bytes, content_type: str) -> dict:
        """保存一张图片，返回 {object_key, view_url}。"""
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise BizError(ErrCode.UPLOAD_INVALID, "仅支持 JPG/PNG/WebP/HEIC 图片")
        limit = settings.max_selfie_size if kind == "selfie" else settings.max_reference_size
        if len(data) > limit:
            raise BizError(ErrCode.UPLOAD_INVALID, "图片过大，请压缩后上传")
        if not data:
            raise BizError(ErrCode.UPLOAD_INVALID, "空文件")

        key = f"u/{user_id}/{uuid4().hex}.{_EXT.get(content_type, 'jpg')}"
        store = get_storage()
        store.save_bytes(key, data)
        return {"object_key": key, "view_url": store.sign_view(key, settings.view_sign_ttl)}

    def view(self, object_key: str) -> str:
        return get_storage().sign_view(object_key, settings.view_sign_ttl)


upload_service = UploadService()