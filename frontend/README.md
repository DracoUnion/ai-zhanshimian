# 前端服务（React）

按 `doc/design-detail.md` 第四章实现：Vite + React 18 + TS + TanStack Query + axios，移动优先（375px 起步）、黑金高级感视觉。

## 快速开始

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173（/api、/files 自动代理到后端 8000）
```

构建：

```bash
npm run build        # tsc 类型检查 + vite 打包到 dist/
```

## 页面与路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 落地页 | 卖点 + CTA |
| `/workspace` | 生成工作台 | 上传自拍(+参考图) → 选模板/提示词 → 张数（1/6/12）|
| `/result/:id` | 结果页 | 生成中轮询动画 → 成功画廊(保存)/失败重试 |
| `/pricing` | 定价页 | 69 解锁包 + 50/100/200 充值套餐 |
| `/account` | 我的 | 余额/解锁/试用状态、改名、充值、退出 |
| `/history` | 生成记录 | 分页历史 |

## 关键实现

- **登录/鉴权**：手机号验证码；axios 拦截器自动注入 Bearer；401 静默 refresh 一次后重试，失败广播登出；开发模式验证码自动填充（`/auth/dev-code`）。
- **生成防重复扣费**：提交时生成 `crypto.randomUUID()` 作为 `Idempotency-Key`（对应后端幂等）。
- **轮询**：生成 pending/processing 每 2s、订单 pending 每 2s；终态自动停止（TanStack Query `refetchInterval`）。
- **图片**：前端 canvas 压缩（≤1200px）→ 后端预签名直传（跨域 S3 自动不带 Bearer）→ 私有桶签名查看。
- **支付**：mock 模式自动「模拟到账」；`PAYMENT_MODE=wechat` 时按 `h5_url` 拉起收银台并轮询订单。
- **付费门槛**：未登录→登录弹窗；未解锁→69 解锁；余额不足→充值弹窗；支付成功回调后自动续传本次生成。

## 浏览器 E2E 冒烟

前置：后端 `:8000`、前端 `:5173` 均启动后：

```bash
python ../.venv/../../.venv/Scripts/python .smoke/run.py   # 或 cd 到项目根用 .venv 运行
```

覆盖：落地页 → 登录 → 上传自拍 → 选模板 → 生成 → 结果画廊 → 定价页，断言无控制台错误。

## 目录

```
frontend/src/
├── api/        axios 客户端(解包/刷新/幂等) + 各模块接口 + Query hooks
├── auth/       AuthContext（token/user/refresh）
├── modal/      ModalContext（登录/支付弹窗全局唤起）
├── components/ Layout / 上传 / 模板墙 / 提示词 / 张数 / 画廊 / 弹窗
├── pages/      落地 / 工作台 / 结果 / 定价 / 我的 / 历史
├── styles/     theme.css(设计令牌) + app.css(全部样式)
└── utils/      图片压缩 / 格式化
```

生产：Nginx 托管 `dist/` 静态资源，`/api` `proxy_pass` 到 FastAPI，`/files` 已并入后端静态；域名需 ICP 备案。