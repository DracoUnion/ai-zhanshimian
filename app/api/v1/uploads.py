"""上传：预签名直传 + 批量签名查看；本地模式提供内部 PUT 接口。"""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.core.response import ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.upload import PresignReq, SignViewReq, SignViewOut, UploadTargetOut
from app.services.storage import get_storage

router = APIRouter()
settings = get_settings()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
}


@router.post("/presign")
def presign(req: PresignReq, user: User = Depends(get_current_user)) -> dict:
    if req.content_type not in ALLOWED_CONTENT_TYPES:
        raise BizError(ErrCode.UPLOAD_INVALID, "仅支持 JPG/PNG/WebP/HEIC 图片")
    limit = settings.max_selfie_size if req.kind == "selfie" else settings.max_reference_size
    if req.size > limit:
        raise BizError(ErrCode.UPLOAD_INVALID, "图片过大，请压缩后上传")

    key = f"u/{user.id}/{uuid4().hex}.{_EXT[req.content_type]}"
    target = get_storage().presign_upload(key, req.content_type, req.size)
    view_url = get_storage().sign_view(key, settings.view_sign_ttl)
    return ok(
        UploadTargetOut(
            object_key=key,
            upload_url=target.url,
            view_url=view_url,
            expires_in=target.expires_in,
            method=target.method,
            headers=target.headers or {},
        ).model_dump()
    )


@router.post("/signview")
def signview(req: SignViewReq, user: User = Depends(get_current_user)) -> dict:
    store = get_storage()
    urls = {key: store.sign_view(key, settings.view_sign_ttl) for key in req.object_keys}
    return ok(SignViewOut(urls=urls).model_dump())


@router.put("/local/{object_key:path}")
async def local_upload(object_key: str, request: Request, user: User = Depends(get_current_user)) -> dict:
    """本地存储直传落盘（仅开发/单机；storage_provider=local 时使用）。"""
    if settings.storage_provider != "local":
        raise BizError(ErrCode.FORBIDDEN, "当前存储模式不支持该接口", status_code=403)
    body = await request.body()
    if not body:
        raise BizError(ErrCode.UPLOAD_INVALID, "空文件")
    get_storage().save_bytes(object_key, body)
    return ok({"object_key": object_key})