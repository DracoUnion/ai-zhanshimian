"""对象存储适配器：local（开发） / s3（生产，S3 兼容协议，覆盖阿里云 OSS/COS）。

核心原则：私有桶 + 预签名直传 + 短时效签名查看（对应详细设计 3.3/7）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.core.errors import BizError, ErrCode

settings = get_settings()


@dataclass
class UploadTarget:
    method: str = "PUT"
    url: str = ""
    headers: dict | None = None
    expires_in: int = 600
    extra: dict = field(default_factory=dict)


class Storage:
    def presign_upload(self, object_key: str, content_type: str, size: int) -> UploadTarget:  # noqa: D102
        raise NotImplementedError

    def sign_view(self, object_key: str, expires: int) -> str:  # noqa: D102
        raise NotImplementedError

    def save_bytes(self, object_key: str, data: bytes) -> None:  # noqa: D102
        raise NotImplementedError

    def open_bytes(self, object_key: str) -> bytes:  # noqa: D102
        raise NotImplementedError

    def delete(self, object_key: str) -> None:  # noqa: D102
        raise NotImplementedError


class LocalStorage(Storage):
    """本地磁盘存储。上传走内部 PUT 接口，查看走 /files 静态挂载（仅开发）。"""

    def __init__(self, base_dir: str):
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, object_key: str) -> Path:
        p = (self.base / object_key).resolve()
        root = self.base
        if p.parts[: len(root.parts)] != root.parts:
            raise BizError(ErrCode.UPLOAD_INVALID, "非法文件路径")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def presign_upload(self, object_key, content_type, size):
        return UploadTarget(
            method="PUT",
            url=f"/api/v1/uploads/local/{object_key}",
            expires_in=settings.upload_sign_ttl,
        )

    def sign_view(self, object_key, expires=settings.view_sign_ttl):
        return f"/files/{object_key}"

    def save_bytes(self, object_key, data):
        self._path(object_key).write_bytes(data)

    def open_bytes(self, object_key):
        p = self._path(object_key)
        if not p.exists():
            raise BizError(ErrCode.UPLOAD_INVALID, "文件不存在或已过期")
        return p.read_bytes()

    def delete(self, object_key):
        p = self._path(object_key)
        if p.exists():
            p.unlink()


class S3Storage(Storage):
    """S3 兼容对象存储：预签名 PUT 直传 + 预签名 GET 查看。"""

    def __init__(self):
        _ensure_boto3()
        import boto3  # type: ignore

        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region or None,
        )

    def presign_upload(self, object_key, content_type, size):
        url = self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": object_key, "ContentType": content_type},
            ExpiresIn=settings.upload_sign_ttl,
        )
        return UploadTarget(method="PUT", url=url, headers={}, expires_in=settings.upload_sign_ttl)

    def sign_view(self, object_key, expires=settings.view_sign_ttl):
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expires,
        )

    def save_bytes(self, object_key, data):
        self.client.put_object(Bucket=self.bucket, Key=object_key, Body=data)

    def open_bytes(self, object_key):
        obj = self.client.get_object(Bucket=self.bucket, Key=object_key)
        return obj["Body"].read()

    def delete(self, object_key):
        self.client.delete_object(Bucket=self.bucket, Key=object_key)


def _ensure_boto3():
    try:
        import boto3  # noqa: F401
    except ImportError:
        raise RuntimeError("storage_provider=s3 需要安装 boto3，请执行 pip install boto3")


@lru_cache
def get_storage() -> Storage:
    if settings.storage_provider == "s3":
        return S3Storage()
    return LocalStorage(settings.storage_local_dir)