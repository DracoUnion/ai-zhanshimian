# AI展示面大师 — 详细设计（前后端）

> 文档版本：V1.0 | 日期：2026年9月6日
>
> **依据**：配合 `doc/design.md`（概要设计）使用，细化到**建表 SQL、接口字段、组件拆分、并发/幂等方案**。
> 技术栈：FastAPI（Python 3.11+）+ React（TS）+ PostgreSQL + Redis + 对象存储。

---

## 一、计费模型（先定规则，再定表）

> 业务规则全部配置化（`config.py` + 后台可调），表结构不写死具体额度。

| 规则 | 取值 | 说明 |
|------|------|------|
| 免费试用 | 1 次（`users.trial_used`） | 注册即送，不可重复 |
| **69 元解锁包** | `WELCOME_CREDITS=69` 次 + `unlocked=true` | 买断功能 + 赠送额度；`unlocked=false` 的已试用用户被禁止继续生成 |
| 充值套餐 | `RECHARGE_PACKAGES={5000:50, 10000:100, 20000:200}` | 金额(分)→次数，1 元≈1 次，比例可配 |
| 消耗 | 每次成功生成扣 1 次/张（`quantity` 张则扣 `quantity`） | 失败退回，见状态机 |

**关键点**：`credits` 语义统一为「可用生成次数」。69 元赠的额度与充值额度同池，用完都从「充值」入口续。

---

## 二、数据库详细设计（PostgreSQL 15+，Alembic 管理）

### 2.1 users 用户

```sql
CREATE TABLE users (
  id              BIGSERIAL PRIMARY KEY,
  phone           VARCHAR(20)  NOT NULL,
  wechat_openid   VARCHAR(64),                    -- 小程序/微信登录预留
  nickname        VARCHAR(32),
  avatar_url      VARCHAR(512),
  unlocked        BOOLEAN      NOT NULL DEFAULT FALSE,  -- 是否已购买 69 解锁包
  credits         INT          NOT NULL DEFAULT 0,      -- 可用生成次数
  trial_used      BOOLEAN      NOT NULL DEFAULT FALSE,  -- 是否用过免费 1 次
  status          SMALLINT     NOT NULL DEFAULT 0,      -- 0正常 1冻结
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT chk_credits_ge_0 CHECK (credits >= 0),
  CONSTRAINT uk_users_phone UNIQUE (phone),
  CONSTRAINT uk_users_openid UNIQUE (wechat_openid)
);
```

### 2.2 generations 生成记录

```sql
CREATE TABLE generations (
  id             BIGSERIAL PRIMARY KEY,
  user_id        BIGINT       NOT NULL REFERENCES users(id),
  selfie_key     VARCHAR(512) NOT NULL,           -- OSS object_key 原图
  reference_key  VARCHAR(512),                    -- 参考图（可选）
  prompt         TEXT,
  template_id    BIGINT REFERENCES templates(id), -- 可空（自定义提示词模式）
  quantity       SMALLINT     NOT NULL DEFAULT 1 CHECK (quantity BETWEEN 1 AND 12),
  status         VARCHAR(16)  NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','processing','success','failed')),
  result_keys    JSONB,                           -- 产出 object_key 数组
  credit_cost    SMALLINT     NOT NULL DEFAULT 0, -- 本次扣费张数
  charged        BOOLEAN      NOT NULL DEFAULT FALSE, -- 是否已持有扣费
  fail_reason    VARCHAR(255),
  created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
  finished_at    TIMESTAMPTZ
);
CREATE INDEX idx_gen_user_created ON generations (user_id, created_at DESC);
CREATE INDEX idx_gen_status ON generations (status) WHERE status IN ('pending','processing');  -- worker 扫描
```

> **batch 原子性约定**：一次生成视为原子批次，任一输出失败整体置 `failed` 并退款，不做部分成功。

### 2.3 templates 风格模板库

```sql
CREATE TABLE templates (
  id              BIGSERIAL PRIMARY KEY,
  name            VARCHAR(32)  NOT NULL,
  category        VARCHAR(32)  NOT NULL DEFAULT 'life',  -- life/sport/street/cafe…
  cover_key       VARCHAR(512),                          -- 封面图
  prompt_template TEXT         NOT NULL,
  prompt_tips     VARCHAR(255),                          -- 给用户的提示语
  sort            INT          NOT NULL DEFAULT 0,
  enabled         BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

### 2.4 orders 订单（解锁包 + 充值共用）

```sql
CREATE TABLE orders (
  id             BIGSERIAL PRIMARY KEY,
  user_id        BIGINT       NOT NULL REFERENCES users(id),
  order_no       VARCHAR(32)  NOT NULL,
  order_type     VARCHAR(16)  NOT NULL CHECK (order_type IN ('unlock','recharge')),
  amount         INT          NOT NULL CHECK (amount > 0), -- 单位：分
  credits        INT          NOT NULL,                    -- 本单到账次数（下单时快照，防比例变更）
  status         VARCHAR(16)  NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending','paid','closed','refunded')),
  pay_method     VARCHAR(16),                              -- wechat_h5 / wechat_native
  prepay_id      VARCHAR(64),
  out_trade_no   VARCHAR(64),
  notify_payload JSONB,                                    -- 回调原文（审计用）
  created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
  paid_at        TIMESTAMPTZ,
  CONSTRAINT uk_orders_no UNIQUE (order_no)
);
CREATE INDEX idx_orders_user_created ON orders (user_id, created_at DESC);
CREATE INDEX idx_orders_out_trade_no ON orders (out_trade_no) WHERE out_trade_no IS NOT NULL;
```

**`order_no` 生成规则**：`+{user_id:0>6}{yyyyMMddHHmmss}{6位随机}`，如 `10000012320260906120000456`。

### 2.5 balance_transactions 余额流水（唯一审计账本）

```sql
CREATE TABLE balance_transactions (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT       NOT NULL REFERENCES users(id),
  amount        INT          NOT NULL CHECK (amount <> 0),  -- 正=增 负=扣
  balance_after INT          NOT NULL,                      -- 变动后余额快照
  type          VARCHAR(16)  NOT NULL
                  CHECK (type IN ('recharge','consume','refund','gift','unlock')),
  ref_id        BIGINT,                                     -- 关联 orders.id / generations.id
  remark        VARCHAR(255),
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_bt_user_created ON balance_transactions (user_id, created_at DESC);
```

> **写流水原则**：`users.credits` 变更与 `balance_transactions` 插入必须同事务；`consume/refund/unlock` 全量记录，可对账。

### 2.6 Redis Key 约定

| Key | 内容 | TTL |
|-----|------|-----|
| `sms:{phone}` | 验证码 | 5 min |
| `sms_cooldown:{phone}` | 发送冷却 | 60 s |
| `rt:{user_id}` | refresh_token 黑名单（换绑/登出） | 7 d |
| `rl:gen:{user_id}` | 生成接口限流（10 次/min） | 60 s |

---

## 三、API 详细设计（统一前缀 `/api/v1`）

**通用约定**
- 响应包裹：`{ "code": 0, "message": "ok", "data": {...} }`；`code != 0` 时 `data` 为 `null`。
- 鉴权：`Authorization: Bearer <access_token>`（15 min）+ `POST /auth/refresh` 刷新（7 d）。
- 微信回调接口例外返回微信指定 XML；分页用 `page`/`page_size`。

**错误码表**

| 码 | 含义 | 调制时机 |
|----|------|----------|
| 1001 | 未登录/Token 无效 | 鉴权中间件 |
| 1002 | Token 过期 | 鉴权中间件 |
| 1101 | 短信发送过频 | 60s 冷却 |
| 1102 | 验证码错误/过期 | 登录 |
| 1201 | 余额不足 | 生成 |
| 1202 | 生成记录不存在或非本人 | 生成 |
| 1203 | 生成状态不允许该操作 | 生成 |
| 1204 | 上传类型/大小不合法 | 上传 |
| 1205 | quantity 超范围（1~12） | 生成 |
| 1206 | 未解锁，先购买 69 解锁包 | 生成 |
| 1301 | 订单不存在 | 订单 |
| 1302 | 订单状态非法 | 订单 |

### 3.1 认证 auth

**POST `/auth/sms-code`**
```
Body   { "phone": "13800138000" }          # 校验 ^1[3-9]\d{9}$
200    { "code":0, "data": { "cooldown": 60 } }        # 不返回验证码；测试环境配置 SMTP_DEBUG=true 时日志输出
Error  1101
```

**POST `/auth/phone-login`**
```
Body   { "phone": "...", "code": "123456" }
200    { "data": {
          "access_token": "...", "refresh_token": "...", "expires_in": 900,
          "user": { "id":1, "phone":"***0000", "nickname":null,
                    "unlocked":false, "credits":0, "trial_used":false } } }
Error  1102
```
> 逻辑：验证码通过 → 若无用户则创建（`trial_used=false`） → 签发双 Token。

**POST `/auth/refresh`**
```
Body   { "refresh_token": "..." }
200    { "data": { "access_token": "...", "expires_in": 900 } }
```

### 3.2 用户 users

**GET `/users/me`** → `data` 同登录返回的 `user` 对象。
**PATCH `/users/me`** → `Body { "nickname"?, "avatar_url"? }`，返回更新后 `user`。

### 3.3 上传 uploads（预签名直传）

**POST `/uploads/presign`**
```
Body   { "kind": "selfie"|"reference", "content_type": "image/jpeg", "size": 204800 }
200    { "data": {
          "object_key": "u/1/8f9e….jpg",     # 服务端生成，格式 u/{user_id}/{uuid}.{ext}
          "upload_url": "https://…/sig",     # 预签名 PUT 地址，10 min
          "view_url": "https://…/sig",       # 预签名 GET 地址，1 h
          "expires_in": 600 } }
Error  1204
```
校验：`content_type ∈ {jpeg,png,webp,heic}`；`size`：selfie ≤ 5MB、reference ≤ 8MB（前端已压缩）。

**POST `/uploads/signview`**
```
Body   { "object_keys": ["g/1/….jpg", "..."] }
200    { "data": { "urls": {"g/1/….jpg": "https://…sig", ...} } }   # 历史页懒签名
```

> 前端流程：压缩 → presign 拿地址 → `PUT upload_url` 直传 → 提交 object_key。桶配置 CORS 允许 PUT/GET。

### 3.4 生成 generations

**POST `/generations`**
```
Header  Idempotency-Key: <uuid>          # 前端每次提交生成一个新 key，防双击重复扣费
Body    { "selfie_key": "u/1/….jpg",
          "reference_key": "u/1/…"?,
          "template_id": 3?,             # template_id 与 prompt 二选一必填
          "prompt": "日系氛围感…"?,
          "quantity": 1 }                # 1~12，默认 1
200     { "data": { "generation_id": 1024, "status": "pending",
                    "credit_cost": 1, "trial_used": true, "balance": 68 } }
Error   1201 / 1205 / 1206 / 1204 / 1001
```

**GET `/generations/{id}`** → `data`：
```
{ "generation_id":1024, "status":"success", "quantity":4, "credit_cost":4,
  "selfie_url":"…sig", "reference_url":"…sig",
  "prompt":"…", "template": {"id":3,"name":"海边","cover_url":"…sig"},
  "results": [{"url":"…sig","width":800,"height":1067}, ...],   // 签名 URL，1h 内有效
  "fail_reason":null, "created_at":"...", "finished_at":"..." }
```

**GET `/generations?page=1&page_size=20`** → `{ "items":[...同上精简], "total": 42, "page": 1, "has_more": true }`

**DELETE `/generations/{id}`** → 软删标记（仅本人，`1202` 校验）。

### 3.5 模板 templates

**GET `/templates`**
```
200  { "data": { "items":[
        { "id":3, "name":"海边", "category":"life",
          "cover_url":"…sig", "prompt_template":"…", "prompt_tips":"…", "sort":1 } ] } }
```

### 3.6 计费支付 billing

**POST `/payments/recharge`**
```
Body   { "amount": 5000,            # 只允许 RECHARGE_PACKAGES 的 key（5000/10000/20000）
         "order_type": "recharge"|"unlock",   # unlock 时 amount 固定为 6900
         "pay_type": "h5"|"native" }          # 手机=h5，PC=native(扫码)
200    { "data": {
          "order_no": "10000000120260906…",
          "pay_params": { "h5_url": "https://wx.tenpay.com/…" }  # native 时返回 code_url
        } }
Error  1301（金额不在套餐）/ 1202（解锁包已购）
```

**POST `/payments/wechat/notify`**（**无统一包裹**，微信回调）
```
请求：Content-Type: application/xml，body 为微信 v3 密文 JSON（含 resource）
业务：验签 → AES-GCM 解密 → 幂等入账（见五.2）
应答：<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>
```

**GET `/payments/orders/{order_no}`**
```
200  { "data": { "order_no":"…", "order_type":"recharge", "status":"paid",
                 "amount":5000, "credits":50 } }
     # status=pending 时前端继续轮询（2s），paid 后刷新余额
```

### 3.7 后台 admin（`X-Admin-Key`，独立于用户 JWT）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/users/search?phone=` | 按手机号定位用户（老用户补发入口） |
| POST | `/admin/users/{id}/credits` | `Body { "credits": 30, "remark": "老用户权益补发" }` → 写流水 `type=gift`，返回新余额 |

---

## 四、前端详细设计（React + TS）

### 4.1 目录结构

```
frontend/src/
├── main.tsx / App.tsx
├── api/
│   ├── client.ts            # axios 实例：带 token、401 刷新重试、错误码→toast
│   ├── auth.ts / user.ts / generation.ts / upload.ts / payment.ts / template.ts
│   └── hooks/               # TanStack Query hooks（useTrial/useBalance/usePollGeneration…）
├── auth/
│   └── AuthContext.tsx      # token 存取(userStorage)、refresh、user 状态
├── utils/
│   ├── image.ts             # compressImage(file,{maxW:1200,maxH:1600,quality:.8}) → Blob
│   └── format.ts
├── components/
│   ├── UploadPanel/ (SelfieUploader / ReferenceUploader)
│   ├── TemplatePicker/
│   ├── PromptInput/ (预设 chips + 输入框 + 字数限制)
│   ├── QuantitySelector/
│   ├── ResultGallery/
│   ├── LoginModal/          # 手机号+验证码，60s 倒计时
│   └── PayModal/            # 选套餐 → 拉起微信收银台 → 轮询订单
└── pages/
    ├── LandingPage/  WorkspacePage/  ResultPage/
    ├── PricingPage/  AccountPage/    HistoryPage/
```

### 4.2 数据与状态

- **AuthContext**：`{ token, user, login(phone,code), logout }`；启动时 `GET /users/me` 恢复会话，401 时静默 refresh 一次。
- **TanStack Query hooks**（关键轮询）：
  - `usePollGeneration(id, status)` —— `status ∈ {pending,processing}` 时 `refetchInterval: 2000`，成功后停。
  - `usePollOrder(orderNo)` —— `pending` 时 2s 轮询，`paid` 后 `invalidateQueries(['me'])` 刷新余额。
- **生成提交**（防重复扣费的关键）：
  1. 前端生成 `crypto.randomUUID()` 作为 `Idempotency-Key`；
  2. `useCreateGeneration` mutation 提交；成功 → `router.push('/result/'+id)`；
  3. 按钮进入 5s 禁用态，双击不会重复请求。

### 4.3 关键组件 props

| 组件 | Props | 职责 |
|------|-------|------|
| SelfieUploader | `value: string\|null; onChange(key)` | 压缩→直传→回填 object_key；换图时提示「五官不变，仅优化穿搭/光线/环境」 |
| TemplatePicker | `value:number\|null; onPick(id)` | 模板卡片墙，选中高亮，显示 cover |
| PromptInput | `value, onChange` | 预设 chips（日系/商务/运动…）+ 单行输入，≤120 字 |
| QuantitySelector | `value, onChange(1\|6\|12)` | 1/6/12 档位卡片，标注「约 N 元 / 抽卡成功率更高」 |
| ResultGallery | `results, onSave, onRegenerate` | 九宫格画廊，长按/下载到相册，返回 69 元引导提示不遮挡 |
| LoginModal | `open, onClose` | 手机号校验、验证码倒计时、登录成功后关闭 |
| PayModal | `orderType:'unlock'\|'recharge', onPaid` | 套餐卡 → 下单 → 微信拉起 → 轮询 → 回调 `onPaid(balance)` |

### 4.4 页面状态机

```
WorkspacePage:
  idle → uploading(压缩/直传) → submitting(Idempotency-Key) → 路由跳 ResultPage
  （余额不足时未提交，先弹 PayModal）

ResultPage:
  status=pending/processing → 加载动画 + 提示「第 1 张约 30s~2min」
  status=success           → ResultGallery + 保存/重生成
  status=failed            → 错误卡片(fail_reason) + 「重新生成」(额度已退回) + 客服微信二维码(仅高客单深聊)
```

---

## 五、核心流程的并发与幂等

### 5.1 生成受理（防并发扣费/超额）

伪代码（同一 DB 事务）：

```python
def accept_generation(user, req, idem_key):
    # 1. Idempotency-Key 去重（防前端双击）
    with db.begin():
        if exists(idempotency_orders, key=idem_key): return existing
        user = lock_user(user.id)                      # SELECT … FOR UPDATE

        if not user.trial_used:
            # 免费试用：原子占位，杜绝并发占两次
            updated = db.execute(
                "UPDATE users SET trial_used=TRUE WHERE id=:id AND trial_used=FALSE …")
            if updated: credit_cost, charged = 0, False
            else: raise Insufficient  # 极端并发下走付费分支
        else:
            if not user.unlocked: raise FeatureLocked(1206)
            assert user.credits >= req.quantity         # 锁内已生效
            db.execute("UPDATE users SET credits=credits-:n …")
            insert balance_transactions(amount=-n, type='consume', …)
            credit_cost, charged = n, True

        gen = insert generations(status='pending', …)
        enqueue(gen.id)                                # Celery
        return gen
```

### 5.2 支付回调入账（验签 + 金额 + 幂等）

```python
def wechat_notify(payload, headers):
    if not verify_sign(headers): return fail()
    data = aes_gcm_decrypt(payload['resource'])
    order_no, out_trade_no, amount = data['out_trade_no'], data['transaction_id'], data['amount']['total']

    with db.begin():
        order = lock_order(order_no)                    # SELECT … FOR UPDATE
        if not order: return fail()                     # 未知单号，拒绝
        if order.status == 'paid':                      # 幂等：重复回调直接成功
            return SUCCESS
        if order.status != 'pending': return fail()
        if order.amount != amount:                      # 金额不符，拒绝并告警
            return fail()

        order.status, order.out_trade_no = 'paid', out_trade_no
        order.paid_at = now()

        user = lock_user(order.user_id)
        if order.order_type == 'recharge':
            user.credits += order.credits
            insert balance_transactions(type='recharge', amount=+credits, ref_id=order.id)
        elif order.order_type == 'unlock':
            user.unlocked = True
            user.credits += WELCOME_CREDITS
            insert balance_transactions(type='unlock', amount=+WELCOME_CREDITS, ref_id=order.id)
    return SUCCESS
```

> 幂等关键：全程 `order.status` 先判后置，锁内完成。重复回调/微信超时重发都不会重复加钱。

### 5.3 生成任务状态机

```
create ─▶ pending ──▶ processing ──▶ success（已扣费，结束）
            │              │
            │              └────▶ failed ─▶ 退款（charger 流程见下）
            └── 超时兜底：worker 扫描 pending>5min 置 failed
```

```python
# worker
def run_generation(gen_id):
    gen = lock_generation(gen_id)
    gen.status = 'processing'
    try:
        outputs = aigc_client.transform(  # 适配器：自拍+参考图+提示词 → N 张
            selfie=gen.selfie_key, ref=gen.reference_key,
            prompt=gen.prompt or template_prompt, n=gen.quantity,
            retry=3, backoff=expo)        # 第三方限流退避
        save_results(gen, outputs)        # 生成图入 OSS → result_keys
        gen.status, gen.finished_at = 'success', now()
    except AigcError as e:
        gen.status, gen.fail_reason, gen.finished_at = 'failed', str(e), now()
        refund(gen)                        # 见下

def refund(gen):
    if gen.charged:
        with db.begin():
            user = lock_user(gen.user_id)
            user.credits += gen.credit_cost
            insert balance_transactions(type='refund', amount=+gen.credit_cost, ref_id=gen.id)
            gen.charged = False
```

### 5.4 未解锁用户的防绕过

- 后端在每个生成受理点校验 `unlocked`；前端仅做引导展示，不承担安全边界。
- 69 解锁包「已购」由 `users.unlocked` 判定，重复下单 `1202 拒绝`，不重复赠送。

---

## 六、部署与关键配置

### 6.1 Nginx

```nginx
server {
    listen 443 ssl;
    root /var/www/dist;                     # React 构建产物
    location / { try_files $uri /index.html; }   # SPA fallback
    location /api/ { proxy_pass http://127.0.0.1:8000; proxy_set_header X-Request-Id $request_id; }
    client_max_body_size 20m;               # 直传走 OSS，后端基本不被追加大文件
}
```

### 6.2 环境变量（`config.py`）

```
DATABASE_URL, REDIS_URL, OSS_ENDPOINT/OSS_BUCKET/OSS_CREDENTIALS,
WECHAT_* (APP_ID, MCH_ID, API_V3_KEY, PRIVATE_KEY, NOTIFY_URL),
SMS_* (provider, keys), AIGC_* (provider, api_key, base_url),
WELCOME_CREDITS=69, RECHARGE_PACKAGES, JWT_SECRET, ADMIN_KEY
```

### 6.3 依赖清单（要点）

| 端 | 依赖 |
|----|------|
| 后端 | fastapi, uvicorn[standard], sqlalchemy 2, alembic, asyncpg, pydantic-settings, redis, celery, httpx, PyJWT, wechatpayv3, oss2(或cos-python-sdk) |
| 前端 | react18, react-router-dom6, @tanstack/react-query, axios, vite, typescript |

---

## 七、边界与异常清单（联调前核对）

| # | 场景 | 处理 |
|---|------|------|
| 1 | 微信回调重复/超时重发 | 5.2 幂等，`paid` 直接 SUCCESS |
| 2 | 用户双击生成 | 前端禁用 + `Idempotency-Key` 去重 |
| 3 | 并发两次试用 | `trial_used` 原子 UPDATE 抢占 |
| 4 | 余额恰好等于 quantity | `credits>=0` 约束 + 锁内扣减 |
| 5 | 第三方生图失败/超时 | worker 重试 3 次退避 → failed → 自动退款 |
| 6 | worker 崩溃挂起任务 | 定时扫描 pending>5min 置 failed 退款 |
| 7 | 订单未支付 | 2 小时未支付置 `closed`，前端不再轮询 |
| 8 | 金额不符回调 | 拒绝 + 告警，不写库 |
| 9 | 旧体验用户（无手机号）/数据迁移 | 手机号为主键，`wechat_openid` 可空，兼容逐步迁入 |
| 10 | 生成结果 URL 泄露 | 私有桶 + 1h 签名，超时前端重新 `signview` |
| 11 | 未成年/敏感内容 | 服务条款声明 + 展示面定位提示，P2 挂内容安全审核 |
| 12 | 手机号换绑 | 90 天内不可换绑（防试吃），`rt:` 清 refresh |

---

## 八、开发拆分建议（对应里程碑）

| 阶段 | 后端 | 前端 | 验收 |
|------|------|------|------|
| M0 骨架 | 工程、config、DB 迁移、错误码 | Vite 工程、axios、AuthContext | 空工程启动、lint 通过 |
| M1 闭环 | auth、users、uploads、generations、templates、demo AIGC 适配器 | 落地页、工作台、结果页、登录弹窗 | **免费试用跑通 1 张** |
| M2 收费 | billing、wechat 通知、admin 补发 | 价格页、PayModal、我的/余额、历史 | 试用→69 解锁→充值→多张生成，全程自助 |
| M3 增强 | quantity 多张、worker 重试/超时兜底 | 6/12 档位、结果画廊保存 | 批量生成 + 失败自动退款 |
| M4 预留 | 小程序 API 层（openid 登录）、文案生成（LLM 适配器）、多端导出规格 | 小程序端（后续新建） | V2.5/V3.0 特性 |

---

*本文档随开发推进补充字段级约束、SQL 迁移脚本与组件实现；涉及第三方（微信支付、短信、AIGC）的接入细节以对应平台文档为准。*