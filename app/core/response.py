"""统一响应格式：{code, message, data}；code=0 成功。"""
from __future__ import annotations

from fastapi.responses import JSONResponse

from .errors import BizError


def ok(data=None) -> dict:
    return {"code": 0, "message": "ok", "data": data}


def err_response(exc: BizError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": exc.data},
    )