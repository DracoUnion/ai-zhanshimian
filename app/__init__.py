"""AI展示面大师 — PySide6 桌面客户端。

架构：去掉 HTTP 层后，UI（`app.ui`）直接调用服务层（`app.services`），
数据模型 / 配置 / 后台任务层从原 FastAPI 后端迁移而来（见 doc/design*.md）。

入口：`python -m app` 或 `python -m app.main`。
"""
from __future__ import annotations

__version__ = "0.1.0"
