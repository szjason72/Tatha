# V1 主仓 API 契约

> 供前端与认证/配额中间件共用；与 [V1 阶段任务拆解](../../JobFirst/docs/V1阶段任务拆解.md) 阶段 1.1 对齐。V1 将在此契约上增加鉴权与配额，错误码 401/403/429 见阶段 4。

---

## 一、端点总览

| 方法 | 路径 | 说明 | V1 鉴权 |
|------|------|------|---------|
| GET | `/health` | 探活 | 否 |
| GET | `/`, `/index.html` | 认证订阅首屏 | 否 |
| GET | `/auth.html` | 登录/注册页 | 否 |
| GET | `/demo.html` | 匹配体验演示页 | 否 |
| GET | `/v1/region` | 按请求 IP 返回地区与定价（V1 新增） | 否 |
| POST | `/v1/auth/login` | 登录 | 否 |
| POST | `/v1/auth/register` | 注册 | 否 |
| POST | `/v1/ask` | 单入口中央大脑 | **是** |
| POST | `/v1/documents/convert` | 文档转 Markdown + 可选结构化提取 | **是** |
| POST | `/v1/jobs/match` | 职位匹配 | **是** |
| POST | `/v1/rag/query` | 私有索引 RAG 查询 | **是** |
| POST | `/v1/orders/checkout` | 创建托管支付结账（阶段 7） | **是** |
| POST | `/v1/webhooks/payment` | Lemon Squeezy 支付 Webhook | 否（签名校验） |
| POST | `/v1/webhooks/stub-upgrade` | 本地 stub 写档位（仅未完整配置支付时可用） | 否 |

---

## 二、请求/响应与错误码

### 2.1 探活

- **GET /health**
- 响应：`{"status":"ok","service":"tatha"}`

### 2.2 认证（当前为演示桩，V1 对接量子认证）

- **POST /v1/auth/login**  
  - Body: `{ "email": string, "password": string }`  
  - 响应：`{ "ok": true, "message": string, "token": string }`

- **POST /v1/auth/register**  
  - Body: `{ "email": string, "password": string }`（password 至少 6 位）  
  - 响应：`{ "ok": true, "message": string, "token": string }`

### 2.3 单入口

- **POST /v1/ask**  
  - Body: `{ "message": string, "context"?: object, "resume_text"?: string }`  
  - 响应：`{ "intent": string, "result": object, "suggestions": string[] }`  
  - V1：请求头需 `Authorization: Bearer <token>`；未带或无效返回 **401**；配额用尽返回 **429**。

### 2.4 文档转换

- **POST /v1/documents/convert**  
  - `multipart/form-data`：`file`（必填）、`document_type`（可选，默认 `resume`，取值 resume/poetry/credit）  
  - 响应：`{ "markdown": string, "document_type"?: string, "extracted"?: object, "error"?: string }`  
  - V1：需鉴权；配额按「简历解析」扣减，超限 **429**。

### 2.5 职位匹配

- **POST /v1/jobs/match**  
  - Body: `{ "resume_text": string, "top_n"?: number (1–20, 默认 5), "source"?: string }`  
  - 响应：`{ "matches": array, "total_evaluated": number, "message"?: string, "error"?: string }`  
  - V1：需鉴权；配额按档位（Free 3 次/日等）扣减，超限 **429**。

### 2.6 RAG 查询

- **POST /v1/rag/query**  
  - Body: `{ "namespace": string, "query": string }`  
  - 响应：`{ "answer": string, "namespace": string, "error"?: string }`  
  - V1：需鉴权；按档位开放与配额扣减，超限 **429**。

### 2.7 地区与定价（V1 新增）

- **GET /v1/region**  
  - 无 Body；根据请求 IP（或 `X-Forwarded-For` / `X-Real-IP`）返回地区与定价。  
  - 响应：`{ "country": string, "currency": string, "locale": string, "pricing": object }`  
  - 无需鉴权，供订阅页按地区展示价格与币种。

### 2.8 支付与档位（阶段 7，托管支付开箱用）

- **POST /v1/orders/checkout**  
  - 需鉴权。Body：`{ "tier": "basic" | "pro", "interval"?: "month" | "year", "return_url"?: string, "client_type"?: string }`  
  - 响应：`{ "checkout_url": string, "tier": string, "interval": string }`  
  - 未完整配置 Lemon Squeezy 时返回同源 stub URL（便于本地验收）；否则返回托管支付页 URL。  
  - 400：tier/interval 非法；502：支付平台调用失败。

- **POST /v1/webhooks/payment**  
  - 供 Lemon Squeezy 回调；请求体为平台 JSON，需校验 `X-Signature`（HMAC）。  
  - 校验失败返回 **401**；处理成功返回 200 与 `{ "ok": true, "tier"?: string, "user_id"?: string }`。

- **POST /v1/webhooks/stub-upgrade**  
  - 仅当**未**完整配置 Lemon Squeezy（缺 Store ID 或 Variant）时可用。  
  - Body：`{ "user_id": string, "tier": "basic" | "pro" }`  
  - 响应：`{ "ok": true, "tier": string, "user_id": string }`  
  - 完整配置支付后此接口返回 **404**。

---

## 三、V1 统一错误码与前端约定（阶段 4 落地）

| 状态码 | 含义 | 前端处理建议 |
|--------|------|--------------|
| **401** | 未认证或 token 无效 | 跳转登录/订阅页 |
| **403** | 无权限（如档位不足） | 提示升级档位 |
| **429** | 配额用尽 | 展示升级引导、不重复刷接口 |

**响应体约定**（便于前端区分并展示文案）：

- **401**：`detail` 为字符串，如 `"missing or invalid authorization"` 或 `"invalid or expired token"`。前端可统一跳转登录页。
- **403**：`detail` 可为字符串或对象；若为对象则含 `code`（如 `"tier_limit"`）、`message`。前端提示升级档位。
- **429**：`detail` 为对象：`{ "code": "quota_exceeded", "message": "当日配额已用尽，请升级后继续使用。" }`。前端展示 `message` 并引导升级，避免重复请求。

---

## 四、与现有代码的对应

- 请求/响应模型：`src/tatha/api/schemas.py`（AskRequest/AskResponse、JobMatchRequest/JobMatchResponse、DocumentConvertResponse、AuthLoginRequest/AuthRegisterRequest 等）。
- 路由与实现：`src/tatha/api/app.py`。
- V1 新增：`GET /v1/region`（阶段 3）；鉴权中间件与 401/403/429（阶段 2、4）；阶段 7 订单/Webhook 见 `src/tatha/api/orders.py`、`webhooks.py`。

文档版本：与 V1 阶段任务拆解阶段 1.1 对齐；阶段 7 已补全端点与契约。
