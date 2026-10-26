"""v1 路由聚合。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, auth, billing, generations, templates, uploads, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(generations.router, prefix="/generations", tags=["generations"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(billing.router, prefix="/payments", tags=["payments"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])