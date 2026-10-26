"""测试环境：临时数据目录 + mock 适配器（在导入 app 前设置环境变量）。"""
from __future__ import annotations

import os
import shutil
import tempfile

_tmp = tempfile.mkdtemp(prefix="zhanshi_app_test_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "test.db").replace("\\", "/")
os.environ["STORAGE_LOCAL_DIR"] = os.path.join(_tmp, "storage")
os.environ["AIGC_PROVIDER"] = "mock"
os.environ["AIGC_MOCK_DELAY"] = "0"
os.environ["SEED_DEMO_TEMPLATES"] = "true"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture()
def fresh_db():
    """重建全部表 + 种子模板 + 本机账户（每个测试独立、可重复）。"""
    from db import base as _base
    from db import register_models
    from db.session import engine, init_db
    from scripts.seed_templates import seed_templates
    from services.local_user import ensure_local_user

    register_models()
    _base.Base.metadata.drop_all(engine)
    init_db()
    seed_templates()
    ensure_local_user()

    # 清空存储目录，避免上个测试的图片残留
    storage_dir = os.environ.get("STORAGE_LOCAL_DIR", "")
    if storage_dir:
        shutil.rmtree(storage_dir, ignore_errors=True)
        os.makedirs(storage_dir, exist_ok=True)
    yield


@pytest.fixture()
def sync_generation():
    """生图任务改为手动同步调用（AUTO_RUN=False），保证测试确定性。"""
    from tasks import generation_exec

    generation_exec.AUTO_RUN = False
    yield
    generation_exec.AUTO_RUN = True