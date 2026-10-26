"""应用配置（pydantic-settings）。生产环境通过环境变量 / .env 覆盖。

桌面端约定：数据库 / 本地存储等运行时数据统一落在 `<项目根>/data/`
（已被 .gitignore 排除），默认相对路径均基于该目录解析。
单机模式：无用户系统 / 无后台管理，仅一条「本机账户」承载试用/解锁/余额。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI展示面大师"
    env: str = "dev"
    debug: bool = True

    # --- 数据库 ---
    database_url: str = f"sqlite:///{(DATA_DIR / 'zhanshi.db').as_posix()}"  # 生产切换 postgresql+psycopg2://...
    auto_create_tables: bool = True
    seed_demo_templates: bool = True

    # --- 对象存储 ---
    storage_provider: str = "local"                   # local | s3
    storage_local_dir: str = str(DATA_DIR / "storage")
    upload_sign_ttl: int = 600
    view_sign_ttl: int = 3600
    s3_endpoint_url: str | None = None
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = ""

    # --- AIGC 图生图 ---
    aigc_provider: str = "mock"                       # mock | http
    aigc_mock_delay: float = 1.5
    aigc_http_url: str = ""
    aigc_http_token: str = ""

    # --- 业务规则（单机本地：试用 1 次 → 69 解锁赠送 69 次；无充值/支付） ---
    welcome_credits: int = 69                         # 69 解锁包赠送次数
    trial_quantity: int = 1
    max_quantity: int = 12
    max_selfie_size: int = 5 * 1024 * 1024
    max_reference_size: int = 8 * 1024 * 1024

    # --- 后台任务线程池 ---
    generation_workers: int = 2                       # 生图后台线程数（替代原 Celery worker）
    sweep_stuck_minutes: int = 5

    def ensure_dirs(self) -> None:
        """确保数据库 / 存储等运行时目录存在。"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if self.storage_provider == "local":
            Path(self.storage_local_dir).mkdir(parents=True, exist_ok=True)
        """确保数据库 / 存储等运行时目录存在。"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if self.storage_provider == "local":
            Path(self.storage_local_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()