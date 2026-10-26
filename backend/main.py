"""FastAPI 应用入口。

启动（开发）：
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.core.response import err_response, ok
from app.db.session import init_db
from app.scripts.seed_templates import seed_templates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        init_db()
        logger.info("数据库表已就绪")
    if settings.seed_demo_templates:
        seed_templates()
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI 展示面大师 — 面向社交软件用户的轻量级 AI 展示面工具",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials="*" not in settings.cors_origins,
)


@app.exception_handler(BizError)
async def biz_error_handler(_: Request, exc: BizError):
    return err_response(exc)


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error_handler(_: Request, exc):
    return JSONResponse(
        status_code=422,
        content={"code": ErrCode.PARAM_INVALID, "message": "参数校验失败", "data": _brief_errors(exc)},
    )


def _brief_errors(exc) -> list[dict]:
    try:
        return [
            {**e, "loc": [str(x) for x in e.get("loc", [])]}
            for e in exc.errors()
        ][:5]
    except Exception:  # noqa: BLE001
        return []


# 本地存储：查看签名 URL 静态服务（仅开发；生产走对象存储 + 预签名）
if settings.storage_provider == "local":
    Path(settings.storage_local_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=settings.storage_local_dir), name="files")


@app.get("/health")
def health() -> dict:
    return ok({"status": "ok", "env": settings.env, "payment_mode": settings.payment_mode})


from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix=settings.api_prefix)