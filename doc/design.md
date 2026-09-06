# AI展示面大师 — 概要设计（前后端）

> 文档版本：V1.0 | 日期：2026年9月6日
>
> **依据**：本文档基于 `doc/prd.md`（V2.0）编写，技术栈为 **FastAPI（Python）+ React（TypeScript）**。
> 目标是与 PRD 对齐的 **V2.0 自助短链路**：用户进入网站即可免费试用，低客单全程自助，无需加个人微信。

---

## 一、设计总则

| # | 原则 | 落地要求 |
|---|------|----------|
| 1 | **极简路径优先** | 「注册 → 免费试用 → 生成 → 付费」主链路控制在最短路径，非核心功能一律后置 |
| 2 | **按次计费，成本与收入绑定** | 用户余额（次数）即配额，每次生成扣 1 次；`余额 - 成本` 始终为正，杜绝算力超支 |
| 3 | **生成异步化** | AI 生图耗时长，全部走异步任务 + 前端轮询，不阻塞支付/页面主链路 |
| 4 | **前后端分离** | React SPA（静态部署） + FastAPI（纯 API），后续小程序直接复用同一套 API |
| 5 | **费用先验证后扣** | 生成成功才扣费，失败退回，降低「AI 抽卡」带来的退款/差评风险 |

---

## 二、系统架构

```
┌──────────────────────────────┐
│  移动浏览器 / 电脑浏览器        │
│  React SPA (Vite 构建静态资源) │
└──────────────┬───────────────┘
               │ HTTPS
┌──────────────▼───────────────┐
│  Nginx（静态资源 + 反向代理）    │
└──────────────┬───────────────┘
               │ /api/*
┌──────────────▼───────────────┐
│  FastAPI 应用                 │
│  auth / generation / billing │
└───┬──────────┬──────────┬────┘
    │          │          │
┌───▼───┐ ┌────▼────┐ ┌───▼────────────┐
│PostgreSQL│ │ Redis   │ │ 对象存储 OSS/COS │
│ 业务数据   │ │队列/缓存/限流│ │ 原图+生成图    │
└────────┘ └─────────┘ └────────────────┘
    ▲                    ▲
    │                    │
┌───┴─────────┐   ┌──────┴─────────────┐
│ 微信支付API   │   │ 第三方AIGC图生图API   │
│ 收款 + 回调   │   │ (可插拔适配器，初期接   │
└─────────────┘   │  成熟平台，不自研模型)  │
                  └────────────────────┘
```

**选型理由**
- **PostgreSQL**：关系型，事务能力强，天然适合「余额扣减 + 流水」这类强一致性场景。
- **Redis**：三用——生成任务队列源、短信验证码缓存、限流计数器。
- **异步任务**：Celery（worker 独立进程）承担 AI 生图长任务；MVP 阶段不引入它也可用 FastAPI BackgroundTasks 顶替，但生产建议 Celery，避免长任务占死 Web 进程。
- **对象存储私有读 + 临时签名 URL**：用户照片敏感，不做公开可读桶。

---

## 三、模块划分

### 3.1 后端（FastAPI）模块

```
backend/
├── app/
│   ├── main.py              # 应用入口，挂载路由、CORS、异常处理
│   ├── config.py            # pydantic-settings 环境配置（含第三方密钥）
│   ├── core/
│   │   ├── security.py      # JWT 签发/校验、密码与短信验证码逻辑
│   │   └── deps.py          # 依赖注入：当前用户、DB session、限流
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py      # 手机号登录（P0）
│   │   │   ├── users.py     # 用户信息/余额（P0）
│   │   │   ├── uploads.py   # 预签名直传（P0）
│   │   │   ├── generations.py # 生成任务（P0）
│   │   │   ├── templates.py # 风格模板库（P1）
│   │   │   ├── billing.py   # 充值订单 + 微信回调（P0）
│   │   │   ├── content.py   # 文案自动生成（P2，预留）
│   │   │   └── admin.py     # 老用户权益补发/后台（P0，API Key 保护）
│   │   └── errors.py        # 统一错误码约定
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/
│   │   ├── aigc.py          # 第三方AIGC适配器（可插拔，核心）
│   │   ├── storage.py       # OSS/COS 封装 + 预签名
│   │   ├── billing.py       # 余额扣减/增加，事务流水
│   │   ├── payment.py       # 微信支付下单/验签/幂等
│   │   └── notify.py        # 短信（P0 手机号登录）/ 小程序订阅等
│   └── tasks/               # Celery 任务定义（生图编排、轮询回调）
└── alembic/                 # 数据库迁移
```

### 3.2 前端（React）页面与路由

| 路由 | 页面 | 说明 | 优先级 |
|------|------|------|--------|
| `/` | 落地页 | 卖点、案例图、CTA「免费生成一张」 | P0 |
| `/workspace` | 生成工作台 | 上传自拍 + 参考图 + 选模板/输入提示词 | P0 |
| `/result/:id` | 结果页 | 生成中（轮询动画）→ 成功画廊 → 「继续生成/保存」 | P0 |
| `/pricing` | 付费页 | 69 元解锁 + 50 元充值套餐 | P0 |
| `/pay/result` | 支付结果 | 订单状态、余额变更反馈 | P0 |
| `/account` | 我的 | 余额、历史记录、充值、权益 | P0 |
| `/history` | 历史记录 | 历史生成列表（已归档） | P1 |
| `/export` | 多端导出 | Soul/抖音/小红书/朋友圈尺寸适配 | P2 |

- **移动优先**：目标用户基本在手机浏览器使用，所有页面按 375px 起步做响应式。
- **视觉质感优先**：不引入重型 UI 框架，以自定义样式 + 图片画廊为核心表达「高级感展示面」，避免「工具站」廉价感。

**前端关键依赖建议**
- 构建：Vite + React 18 + TypeScript
- 服务端状态：TanStack Query（轮询/缓存/失效重取天然合适）
- 路由：react-router v6
- 大图压缩：客户端上传前用 canvas 压缩自拍与参考图（手机原图常有 10MB+）

---

## 四、数据模型（核心表）

### users 用户
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint PK | |
| phone | varchar(20) | 登录手机号，唯一（可空，兼容微信登录） |
| wechat_openid | varchar(64) | 小程序预留 |
| nickname / avatar_url | varchar | 展示信息 |
| credits | int | 剩余可用次数（1次≈1元，50元=50次） |
| trial_used | bool | 是否用过免费体验（1次） |
| status | int | 正常/冻结 |
| created_at / updated_at | timestamptz | |

### generations 生成记录
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint PK | |
| user_id | bigint FK | |
| selfie_url / reference_url | varchar | 原图 object_key |
| prompt | text | 用户提示词 |
| template_id | bigint FK, null | 关联模板（可空） |
| quantity | int | 本次生成张数（默认1，预留6/12） |
| status | enum | pending / processing / success / failed |
| result_urls | jsonb | 生成结果 object_key 列表 |
| credit_cost | int | 本次扣费次数 |
| charged | bool | 是否已扣费 |
| fail_reason | varchar | 失败原因（用于提示与日志） |
| created_at / finished_at | timestamptz | |

### templates 风格模板库（P1）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint PK | |
| name / cover_url | varchar | 咖啡厅、海边、健身房、城市街景… |
| prompt_template | text | 模板对应的提示词 |
| category / sort / enabled | | 分类、排序、上下架 |

### orders 充值订单
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint PK | |
| user_id | bigint FK | |
| order_no | varchar(32) 唯一 | 商户订单号 |
| amount | int | 金额（分） |
| status | enum | pending / paid / closed / refunded |
| pay_method | varchar | wechat_h5 / wechat_native |
| out_trade_no | varchar(64) | 微信侧单号 |
| paid_at | timestamptz | |

### balance_transactions 余额流水（账本）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | bigint PK | |
| user_id | bigint FK | |
| amount | int | 变动次数（正=充值/发放，负=消费） |
| type | enum | recharge / consume / refund / gift |
| ref_id | bigint | 关联业务单（订单/生成记录） |
| remark | varchar | 文案备注 |
| created_at | timestamptz | |

> 短信验证码放在 Redis（key=`sms:{phone}`，TTL 5 分钟），不落库。

---

## 五、API 设计（v1，统一前缀 `/api/v1`）

### 认证鉴权（P0）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/sms-code` | 发送验证码（限流：同手机号 60s/次） |
| POST | `/auth/phone-login` | 验证码登录/注册，返回 `access_token`（短时效）+ `refresh_token` |
| POST | `/auth/refresh` | 刷新 token |
| GET | `/users/me` | 当前用户（含余额、是否用过试用） |
| PATCH | `/users/me` | 更新昵称/头像 |

### 上传（P0）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/uploads/presign` | 返回 OSS 直传的 presigned URL 与 object_key（自拍/参考图，前端秒传，不经过后端中转） |

### 生成（P0）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generations` | 创建任务。参数：selfie_key、reference_key、prompt、template_id、quantity。**免费试用优先**：`trial_used=false` 时不扣费；否则校验 `credits>=quantity` 并预扣 |
| GET | `/generations/{id}` | 查询状态与结果（前端轮询） |
| GET | `/generations` | 我的历史记录（分页） |
| DELETE | `/generations/{id}` | 删除记录（软删） |

### 模板（P1）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/templates` | 启用的模板列表（含封面、提示词） |

### 计费与支付（P0）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/payments/recharge` | 创建充值订单（50 元起），返回微信支付参数 |
| POST | `/payments/wechat/notify` | **微信异步回调**（幂等处理，验签 + 金额校验 + `out_trade_no` 去重） |
| GET | `/payments/orders/{order_no}` | 查询订单状态（前端轮询） |

### 后台（P0，`X-Admin-Key` 保护）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/users/{id}/credits` | 老用户权益补发 / 手动加次数（写流水 type=gift） |

**统一约定**
- 响应包裹 `{ code, message, data }`，`code=0` 表示成功；错误码有语义（如 `BALANCE_INSUFFICIENT`、`SMS_TOO_FREQUENT`）。
- 鉴权：Bearer JWT（AccessToken 15min + RefreshToken 7d）。
- 分页：`page` / `page_size`。

---

## 六、关键业务流程

### 6.1 注册登录（手机号验证码）
```
输入手机号 → POST /auth/sms-code（Redis 记录+限流）
输入验证码 → POST /auth/phone-login
   ├─ 新用户：创建 users（trial_used=false, credits=0）
   └─ 老用户：直接返回 token
→ 前端存 token，进入落地页/工作台
```

### 6.2 AI 生成（异步，核心链路）

```
前端                        后端                      第三方AIGC
 │ 压缩上传图片 → presign 直传 OSS               │
 │ POST /generations                            │
 │    ├─ 校验：试用量 or 余额                     │
 │    ├─ 入库 status=pending，预扣（trial/credits）│
 │    └─ 投递 Celery 任务 ───────────────────────▶ 调用图生图API
 │            worker：status=processing ────────▶ 受理/轮询拿结果
 │ 轮询 GET /generations/{id}  ◀── 回写 success + result_urls
 │            （或 failed：退回预扣费用，记流水）
 │ 结果页展示画廊（临时签名URL加载）
```

**扣费策略（对应「AI 抽卡」风险）**：任务受理后预扣 → 成功即持有；失败退回到余额。免费体验的首次生成失败不消耗试用资格。

### 6.3 充值支付（微信支付）
```
POST /payments/recharge {amount: 5000}
  → 创建订单 order_no，状态 pending
  → 调微信统一下单，返回 H5/Native 支付参数
前端拉起收银台 → 用户付款
微信异步回调 POST /payments/wechat/notify
  → 验签 + 金额核对 + 幂等（out_trade_no 去重）
  → 更新订单 paid，users.credits += amount/100，写流水 type=recharge
前端轮询 GET /payments/orders/{order_no} → 展示余额
```

### 6.4 老用户权益补发（P0）
已付 69 元的老用户由运营在后台按手机号定位，`POST /admin/users/{id}/credits` 发放规定周期内的免费次数，落 `balance_transactions(type=gift)`，前端「我的」可见到账。

---

## 七、关键设计决策与理由

| 决策 | 选择 | 理由 |
|------|------|------|
| 计费模型 | 余额（次数）而非订阅 | 对齐 PRD「按次充值，约 1 元/次」，成本与收入直接绑定，无跑包风险 |
| 生成同步 or 异步 | 异步任务 + 前端轮询 | AI 生图耗时 30s~数分钟，异步避免接口超时、支撑批量生成 |
| 第三方 AIGC 接入 | 服务层适配器隔离，不散落调用点 | 初始接成熟平台快速验证，后续换模型/自研只改一处 |
| 图片传输 | 预签名直传 OSS，不经后端 | 大图不占服务器带宽；后端只持有 object_key |
| 图片安全 | OSS 私有桶 + 临时签名 URL（短时效） | 用户照片敏感，杜绝公开可枚举 |
| 费用结算 | 成功后扣费、失败退回 | 降低「抽卡」失败 → 退款 → 差评的负面链路 |
| 支付方式 | H5（手机浏览器）+ Native（PC 扫码） | 覆盖 Web 端主要场景；微信内 JSAPI 需认证服务号，V2.0 小程序阶段再引入 |
| 免费试用 | `users.trial_used` 一次性标记 | 对齐「先跑通一次再付费」，降低决策门槛 |
| 短信 | 手机验证码登录（Redis 缓存 + 限流） | 无需密码体系；后续小程序可用微信静默登录复用同一 user 表 |

---

## 八、非功能需求

- **性能**：生成接口 `P95 < 300ms`（不含第三方耗时）；前端首屏落地页静态化，图片懒加载。
- **安全**：JWT + HTTPS；上传类型/大小白名单；生成接口限流（如 10 次/分钟/用户）；后台 API Key 与主系统隔离。
- **合规/伦理**（对齐 PRD 八.3）：生成提示词与服务条款明确禁止伪造身份、冒充他人；后续引入生成内容审核（PG 后端可挂第三方内容安全 API，P2）。
- **可观测**：结构化日志（请求 ID 透传）；Sentry 采集错误；Celery 任务失败告警。
- **可移植**：所有第三方（AIGC/存储/短信/支付）均走适配器 + 环境变量配置，前端 API 地址走构建期注入，便于换环境。

---

## 九、部署架构

```
┌──────────┐   ┌─────────────────────────────┐   ┌───────────┐
│  CDN / Nginx │   │  ECS（国内，需备案域名+HTTPS） │   │  Celery worker│
│  React 静态  │──▶│  uvicorn/gunicorn ×N      │──▶│  (独立进程)   │
│  资源        │   │  FastAPI                 │   │  跑生图任务   │
└──────────┘   └─────┬────────┬──────────────┘   └─────┬─────┘
                    PostgreSQL │ Redis                 │
                    (RDS/自建)   │                       │
                                └──────────── 对象存储 ──┘
```

- 前端构建产物部署 Nginx，`/api/*` 反代至 FastAPI。
- 域名 + ICP 备案是前置条件（国内访问），微信支付与短信同样要求已验证域名/账号。
- 迁移 Alembic 管理；CI 走 lint + 单元测试 + 构建；生产多 worker + Celery 独立扩容。

---

## 十、迭代对齐（对应 PRD 九）

| 阶段 | 本期范围 | 里程碑验收口径 |
|------|----------|----------------|
| **V2.0 平台化（先行）** | 落地页、手机号登录、免费试用、生成工作台、结果页、69 元解锁 + 50 元充值、微信支付、我的/余额、老用户补发后台 | 全新用户**全程自助**完成「试用 1 次 → 充值 → 生成多轮」，无人工介入 |
| V2.5 模板丰富 | 风格模板库、一键生成多张、文案自动生成 | 模板可选、单次生成 6~12 张 |
| V3.0 规模化 | 多平台导出、内容审核、投放追踪 | 探索投放，API 化输出 |

---

*本文档为概要设计，细化到接口字段、建表 SQL、组件拆分的部分在详细设计阶段迭代补充（可对照 PRD 的「极简 + 自助」原则随时裁剪）。*