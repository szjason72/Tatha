# Changelog

## [0.2.0] - 2025-03-01

### V1 交付（Web 闭环 / 认证 / 档位 / 支付）

- **阶段 3**：`GET /v1/region` 按请求 IP 返回地区与定价；订阅页按地区展示 CNY/USD；Playwright E2E `test_subscription_region.py`、`test_region_api.py`
- **阶段 4**：鉴权中间件（量子认证 stub）、配额扣减；401/403/429 错误码；`test_quota.py`
- **阶段 5/6**：认证订阅与登录、简历与匹配闭环；`auth.html` 登录/注册；E2E `test_auth_and_demo.py`（2 用例待 jobfirst-claw 联调后启用）
- **阶段 7**：托管支付开箱用（Lemon Squeezy）；`POST /v1/orders/checkout`、`/v1/webhooks/payment`、`/v1/webhooks/stub-upgrade`；stub 链路可本地验收；`test_phase7.py`
- **文档**：`docs/API契约_V1.md` 覆盖 14 个端点与错误码；`docs/V1_阶段7_托管支付开箱用.md`、`docs/V1_region与订阅页测试.md`

对应《开发收敛与可交付路线图》V1 阶段 3～7 落地。

---

## [0.1.0] - 2025-02-19

### V0 交付（最小可演示）

- **端到端链路**：简历上传 → 解析与向量化 → 职位匹配 API → 匹配结果展示
- **单入口 API**：`POST /v1/ask`、`POST /v1/jobs/match`，健康检查 `/health`
- **Web 演示**：订阅首屏 `index.html`、登录/注册页 `auth.html`、匹配体验 `demo.html`
- **验收**：按 `docs/V0演示清单.md` 与 `scripts/verify_v0_demo.py` 可复现

对应《开发收敛与可交付路线图》V0 验收完成。
