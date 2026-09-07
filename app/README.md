# 后端服务（FastAPI）

按 `doc/design.md`（概要设计）+ `doc/design-detail.md`（详细设计）实现。

## 快速开始（开发，零外部依赖）

```bash
# 1. 安装依赖
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # macOS/Linux: .venv/bin/pip

# 2. 启动（默认 SQLite + 全部 mock 适配器，可直接跑通全链路）
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

- 交互文档：http://127.0.0.1:8000/api/docs
- 健康检查：`GET /health`

### 本地全链路如何跑通（无需微信/短信/AIGC 真服务）

1. `POST /api/v1/auth/sms-code`（手机号）
2. `POST /api/v1/auth/dev-code` —— 读取 mock 验证码
3. `POST /api/v1/auth/phone-login` —— 拿 JWT
4. `POST /api/v1/uploads/presign` → 按返回的 `upload_url`（本地为 `/api/v1/uploads/local/...`）PUT 上传图片
5. `POST /api/v1/generations` → 免费试用生成 1 张（`CELERY_EAGER=true` 内联执行，直接返回结果）
6. `POST /api/v1/payments/recharge`（69 元解锁包）→ `POST /api/v1/payments/mock-confirm` 模拟微信到账
7. 再充 `5000` 分套餐 → mock-confirm → 余额到账 → 继续生成扣费

> 生产切换：见 `.env.example`——`DATABASE_URL` 指 PostgreSQL、`PAYMENT_MODE=wechat`、`AIGC_PROVIDER=http`、`STORAGE_PROVIDER=s3`、`CELERY_EAGER=false` + Redis broker。

## 测试

```bash
.venv/Scripts/python -m pytest app/tests -v
```

## 目录

```
app/
├── main.py            # FastAPI 入口（CORS、异常、静态挂载、路由注册）
├── config.py          # pydantic-settings 配置（含全部业务规则）
├── core/              # 错误码/统一响应/JWT/KV缓存
├── db/                # Engine/Session/Base
├── models/            # users/generations/templates/orders/balance_transactions/idempotency_keys
├── schemas/           # Pydantic v2 请求/响应
├── services/          # 存储/AIGC/短信适配器 + 计费账本 + 生成受理 + 支付/微信v3
├── tasks/             # Celery（生图 worker + 卡单兜底）
├── api/v1/            # 路由：auth/users/uploads/generations/templates/payments/admin
├── scripts/           # 演示模板种子
└── tests/             # 冒烟测试（mock 适配器跑通主链路）
```

## 关键设计落地对照

| 详细设计 | 实现 |
|----------|------|
| 计费模型 | `config.py: WELCOME_CREDITS / UNLOCK_PRICE / RECHARGE_PACKAGES` |
| 生成幂等/并发安全 | `services/generation.py: accept_generation`（Idempotency-Key + 行锁 + trial 原子抢占） |
| 支付回调幂等 | `services/payment.py: settle_paid_order`（行锁 + status 先判后置） |
| 失败自动退款 | `tasks/generation_tasks.py: _fail_and_refund` + `sweep_stuck_generations` |
| 图片私有化 | 私有对象存储 + 预签名直传/查看（local 为开发替代） |
| 微信支付 v3 | `services/wechat_pay_v3.py`（下单验签解密，mock 模式可先行联调） |