"""应用配置（pydantic-settings）。生产环境通过环境变量 / .env 覆盖。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI展示面大师"
    env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    # --- 数据库 / 缓存 ---
    database_url: str = "sqlite:///./zhanshi.db"      # 生产切换 postgresql+psycopg2://...
    redis_url: str | None = None                      # 为空时 KV 退化为进程内缓存（仅开发/单进程）
    auto_create_tables: bool = True                   # 开发便捷；生产用 alembic 迁移
    seed_demo_templates: bool = True

    # --- 对象存储 ---
    storage_provider: str = "local"                   # local | s3
    storage_local_dir: str = "./storage"
    upload_sign_ttl: int = 600                        # 上传地址有效秒数
    view_sign_ttl: int = 3600                         # 查看地址有效秒数
    s3_endpoint_url: str | None = None
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = ""

    # --- 短信 ---
    sms_provider: str = "mock"                        # mock | http
    sms_http_url: str = ""
    sms_http_token: str = ""

    # --- 支付 ---
    payment_mode: str = "mock"                        # mock | wechat
    wechat_appid: str = ""
    wechat_mchid: str = ""
    wechat_api_v3_key: str = ""
    wechat_private_key_path: str = ""                 # 商户私钥 apiclient_key.pem
    wechat_serial_no: str = ""
    wechat_notify_url: str = ""
    wechat_platform_cert_path: str = ""               # 平台证书（回调验签，可选）

    # --- AIGC 图生图 ---
    aigc_provider: str = "mock"                       # mock | http
    aigc_mock_delay: float = 1.5                      # 模拟生图耗时
    aigc_http_url: str = ""
    aigc_http_token: str = ""

    # --- 认证 ---
    jwt_secret: str = "dev-only-please-change-this-secret-0123456789abcdef"
    access_token_ttl: int = 900                       # 15 分钟
    refresh_token_ttl: int = 604800                   # 7 天
    sms_code_ttl: int = 300
    sms_cooldown: int = 60
    admin_key: str = "change-me-admin"

    # --- 业务规则（对应详细设计：计费模型） ---
    welcome_credits: int = 69                         # 69 解锁包赠送次数
    unlock_price: int = 6900                          # 69 元（单位：分）
    recharge_packages: dict[int, int] = {5000: 50, 10000: 100, 20000: 200}  # 金额(分):次数, 1元≈1次
    trial_quantity: int = 1
    max_quantity: int = 12
    max_selfie_size: int = 5 * 1024 * 1024
    max_reference_size: int = 8 * 1024 * 1024
    order_expire_hours: int = 2

    # --- 异步任务 ---
    celery_eager: bool = True                         # 开发直接内联执行；生产置 False 用真实 broker
    celery_broker_url: str = "memory://"
    celery_result_backend: str = "cache+memory://"

    @property
    def recharge_packages_list(self) -> list[dict]:
        return [{"amount": k, "credits": v} for k, v in sorted(self.recharge_packages.items())]


@lru_cache
def get_settings() -> Settings:
    return Settings()