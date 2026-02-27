# Changelog

## [0.1.0] - 2025-02-19

### V0 交付（最小可演示）

- **端到端链路**：简历上传 → 解析与向量化 → 职位匹配 API → 匹配结果展示
- **单入口 API**：`POST /v1/ask`、`POST /v1/jobs/match`，健康检查 `/health`
- **Web 演示**：订阅首屏 `index.html`、登录/注册页 `auth.html`、匹配体验 `demo.html`
- **验收**：按 `docs/V0演示清单.md` 与 `scripts/verify_v0_demo.py` 可复现

对应《开发收敛与可交付路线图》V0 验收完成。
