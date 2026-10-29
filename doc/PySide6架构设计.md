# ai-zhanshimian 架构设计

> AI 展示面大师（PySide6 桌面客户端）。本文件描述架构对齐后的当前代码结构（2026-10-30），
> 补充 `doc/design.md`、`doc/design-detail.md`、`doc/prd.md` 中未覆盖的架构层。

## 1. 项目简介

面向"AI 展示面"生成的桌面工作台：本机账户（免费无限次，无登录/支付/余额）、模板选择、上传自拍照/
参考图、图生图（mock 或 OpenAI 底座）、生成历史。单机模式，数据库 + 本地存储。

变更历史：`6b1c2fc` 新增零 Qt 架构层（common + 通用 TaskManager），`bootstrap()` 返回
`AppContext`，`main.py` 退出时关闭任务池。

## 2. 技术栈与依赖（`requirements.txt`）

| 项 | 值 |
|---|---|
| Qt 绑定 | PySide6 ≥ 6.6 |
| DB/ORM | SQLAlchemy ≥ 2（SQLite `data/zhanshi.db`，WAL） |
| 数据校验 | pydantic ≥ 2.6 + pydantic-settings ≥ 2.2 |
| 图像 | Pillow ≥ 10 |
| LLM | openai ≥ 1.30,<2（AI 图生图/文生图） |
| 存储 | 本地 `data/storage`（可选 S3） |
| 测试 | pytest ≥ 8（services / AIGC / UI smoke / 架构层） |

## 3. 目录结构

```text
ai-zhanshimian/app/
├─ __main__.py / main.py       # 入口：bootstrap() → QApplication → MainWindow
├─ bootstrap.py                # bootstrap() → build_context()：EventHub + TaskManager → AppContext
├─ data/                       # 运行时 SQLite + storage（gitignored）
├─ common/                     # ★ 零 Qt（本次新增）
│  ├─ events.py                # EventHub
│  ├─ context.py               # AppContext
│  └─ __init__.py
├─ tasks/                      # ★ 零 Qt
│  ├─ task.py                  # Task/TaskState/TaskManager + TaskCancelled（通用，本次新增）
│  ├─ generation_exec.py       # 生图专用线程池（retry/backoff/sweep_stuck）
│  └─ __init__.py
├─ services/                   # ★ 零 Qt 业务层
│  ├─ facade.py                # UI 门面（模块级函数：state/templates/upload/create_generation/...）
│  ├─ generation.py / storage.py / upload.py / local_user.py / aigc.py
│  └─ __init__.py
├─ ai/openai_client.py         # LLM 客户端（零 Qt）
├─ db/                         # base.py + session.py（SQLAlchemy 2.0 + WAL/session_scope；create_all）
├─ models/ schemas/            # ORM + Pydantic DTO（generation/template/user/upload/idempotency）
├─ core/                       # errors.py / timeutil.py（零 Qt）
├─ ui/                         # ★ 唯一 PySide6
│  ├─ main_window.py           # 顶栏/侧栏 + QStackedWidget + 页面栈（home/workspace/result/history/account）
│  ├─ worker.py                # QThreadPool + QRunnable + Poller（Qt 后台辅助）
│  ├─ context.py               # UI 回调上下文（window/toast/navigate）
│  ├─ theme.py / toast.py / widgets.py / components/ / pages/ / image.py / image_tools.py / template_picker.py
│  └─ __init__.py
├─ scripts/seed_templates.py
└─ tests/                      # conftest + test_services + test_aigc + test_ui_smoke + test_arch
```

## 4. 架构分层与依赖方向

```text
ui/ (唯一 PySide6；worker.py QThreadPool/Poller)
 └─ services/facade.py  (模块级门面函数)
     ├─ db/models/schemas（SQLAlchemy + Pydantic）
     ├─ ai/openai_client（LLM）
     └─ services（generation/storage/upload/local_user/aigc）
         └─ common/（EventHub / AppContext）+ tasks/（任务层）
```

## 5. 关键流程

```text
python -m app
→ bootstrap()
   ├─ settings.ensure_dirs()          # data/ storage/
   ├─ init_db()（create_all）
   ├─ seed_templates() + ensure_local_user()
   ├─ configure_pool(generation_workers)   # 生图线程池
   └─ build_context() 返回 AppContext
→ QApplication + apply_theme → MainWindow() → app.exec()
→ ctx.tasks.shutdown(wait=False)
```

生图：UI 受理（`facade.create_generation`）→ `tasks/generation_exec.submit_generation(gen_id)`
→ ThreadPoolExecutor 后台执行（pending→processing→success/failed，任务内重试退避）→
UI 经 `Poller(QTimer)` 轮询或 `worker.py` 收结果。`sweep_stuck_generations()` 兜底超时卡单。

## 6. 线程模型

| 线程 | 职责 |
|---|---|
| Qt 主线程 | 窗口 / 页面 / 短查询（直查 SQLite） |
| QThreadPool（QRunnable） | UI 发起的后台服务调用（worker.py） |
| 生图线程池（ThreadPoolExecutor） | AIGC 图生图（generation_exec，默认 2 线程） |
| TaskManager 池（零 Qt） | 通用后台任务（AppContext.tasks，为 UI 桥预留） |

## 7. 配置管理

- `.env` / 环境变量 ← `pydantic-settings`（`config.py`：app_name、database_url、storage、
  aigc_provider/model、max_quantity、generation_workers、sweep_stuck_minutes 等）。
- 业务数据：SQLite（`data/zhanshi.db`）+ 本地/ S3 对象存储。
- 无 QSettings 桌面偏好（`ui/` 未拆分 settings_store，可后续补）。

## 8. 测试

```bash
# 从 app/ 目录（pytest 需能 import core/db 等裸模块）
cd app && ../.venv/Scripts/python.exe -m pytest tests -q   # 18 passed
# 含 offscreen UI smoke（test_ui_smoke）+ 架构层（test_arch）
# QT_QPA_PLATFORM=offscreen
```

## 9. 与参考架构的差距（后续 TODO）

- `services/facade.py` 是模块级函数而非类式 `ServiceFacade`（组合域服务）——可包一层类。
- 无 Alembic（`init_db/create_all` 建表）；`db/seed.py` 未独立（种子在 `scripts/`）。
- 通用 `TaskManager`（AppContext.tasks）与生图专用池（generation_exec）并存，尚未统一到
  `ui/worker.py` 的 QtTaskBridge（业务后台 + Qt pool 目前两套执行体系）。
- 无 QSettings 偏好存储（`ui/settings_store.py`）。