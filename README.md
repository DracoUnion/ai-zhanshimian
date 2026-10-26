# AI 展示面大师（PySide6 桌面客户端）

面向社交软件用户的 AI 展示面生成工具（单机本地版）。

原 FastAPI 后端 + React 前端已重构为 **PySide6 桌面程序**：移除 HTTP 层，
UI 直接调用服务层（`app/services`）。鉴于此为单机工具，**用户系统、后台管理、
充值/支付、生成次数限制均已彻底移除**：

- 无登录/注册：运行时自动建立一条「本机账户」（`services/local_user.py`）；
- **免费无限次生成**：无余额/解锁/试用概念，生成失败可无限重试；
- LLM/AIGC 调用统一走 `OpenAIClient`（`app/ai/openai_client.py`，源自
  `../BookerGptTool/BookerGptTool/openai.py` 裁剪而来），真实生图通过
  `OpenAIClient.call_tti` 对接任意 OpenAI 兼容底座，mock 模式离线占位。

## 快速开始

```bash
# 1. 安装依赖
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip

# 2. 启动（默认 SQLite + mock 生图 + 5 个演示模板）
.venv/Scripts/python -m app
```

- 运行时数据（数据库 / 生图存储）默认落在 `./data`（已 gitignore）；
- 生成在后台线程池执行（`app/tasks/generation_exec.py`），UI 不阻塞，
  结果页自动轮询至完成。`AIGC_MOCK_DELAY` 可调模拟耗时。

## 测试

```bash
.venv/Scripts/python -m pytest app/tests -v
```

服务层冒烟（免费生成/幂等/历史/校验）+ AIGC/OpenAIClient 接线（离线）+ UI 离屏启动冒烟。

## 目录

```
app/
├── main.py            # 入口：bootstrap + QApplication + MainWindow
├── bootstrap.py       # 建表 / 种子模板 / 本机账户 / 生图线程池
├── config.py          # pydantic-settings 配置（默认路径基于项目根 ./data）
├── core/              # 错误码 / 时间工具
├── db/                # Engine / Session（SQLite WAL + busy_timeout）
├── models/            # users/generations/templates/idempotency_keys
├── schemas/           # Pydantic v2 校验
├── ai/                # OpenAIClient（对话/视觉/文生图，所有 LLM 调用入口）
├── services/          # 业务门面(facade) + 生图/存储/AIGC 适配器
├── tasks/             # 生图线程池 + 卡单兜底
├── ui/                # PySide6：主窗口 / 页面 / 组件 / 主题
└── tests/             # 服务层 + AIGC 接线 + UI 冒烟
```

## 生产上真实 AIGC

`.env` 配 `AIGC_PROVIDER=openai` + `AIGC_HTTP_TOKEN`（API Key）+ `AIGC_MODEL`
（如 gpt-image-1），见 `.env.example`；所有生图经 `OpenAIClient.call_tti`。