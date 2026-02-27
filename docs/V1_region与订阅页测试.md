# V1 阶段 3：地区与订阅页测试

> 按地区展示价格的接口与订阅页用 **pytest** 与 **Playwright** 固定，避免后续改 region/定价时踩坏。

---

## 一、接口契约测试（无需启动服务）

`GET /v1/region` 的响应结构、国内/境外定价与 query 覆盖由单元测试保证：

```bash
uv run pytest tests/test_region_api.py -v
```

- `test_region_response_shape`：响应含 `country`、`currency`、`locale`、`pricing` 及 pricing 内各档价格字段。
- `test_region_country_cn_returns_cny`：`?country=CN` 返回 CNY、basic_monthly=99、pro_monthly=199。
- `test_region_intl_returns_usd`：`?region=intl` 返回 USD、basic_monthly=9.9、pro_monthly=19.9。

---

## 二、订阅页 E2E（Playwright）

需先启动 API，再安装 Playwright 浏览器后运行：

```bash
# 终端 1：启动服务
uv run uvicorn tatha.api.app:app --host 127.0.0.1 --port 8010

# 终端 2：安装浏览器（首次）
uv run playwright install chromium

# 运行全部 E2E（依赖 8010 已启动）
uv run pytest tests/e2e/ -v
```

- 若 8010 未启动，E2E 会 **skip**（见 `tests/e2e/conftest.py`）。
- `test_subscription_page_has_pricing_cards`：订阅页存在三档卡片与 `data-region-price` 占位。
- `test_subscription_page_loads_region_prices`：页面加载后请求 `/v1/region`，Basic/Pro 月价由接口填充，币种为 ¥ 或 $。

---

## 三、阶段 5/6：认证与简历匹配 E2E（test_auth_and_demo.py）

同目录下 `tests/e2e/test_auth_and_demo.py` 覆盖：

| 用例 | 说明 |
|------|------|
| `test_demo_redirect_when_no_token` | 未登录访问 demo.html 应重定向到 index.html |
| `test_auth_page_has_login_and_register` | 登录页存在登录/注册 tab 与表单 |
| `test_auth_can_switch_to_register` | 登录页可切换到注册面板 |
| `test_login_success_redirects_to_demo` | 登录成功后跳转到 demo 使用页 |
| `test_demo_with_token_shows_tabs` | 带 token 访问 demo 应展示简历、职位匹配、/v1/ask 三个 tab |
| `test_match_flow_shows_result_or_quota` | 带 token 点击匹配岗位，结果区出现职位卡片或 429 升级引导（最多等 60s） |

运行方式同上：先启动 API，再 `uv run pytest tests/e2e/ -v`。匹配用例会调用真实 `/v1/jobs/match`，耗时视 LLM 而定。

**暂缓用例（与 jobfirst-claw 联调后启用）**：`test_login_success_redirects_to_demo`、`test_match_flow_shows_result_or_quota` 已加 `@pytest.mark.skip`，原因分别为「登录跳转依赖前端 fetch 与 API 联调」与「匹配流程依赖 /v1/jobs/match 与 LLM/环境稳定」。待 jobfirst-claw 项目交付后联调联试时去掉 skip 即可。

---

## 四、订阅页按地区展示价格（实现说明）

`index.html` 在加载时请求 `GET /v1/region`，用返回的 `pricing` 与 `currency` 更新「基础版」「Pro 版」的月价与币种符号；免费版保持 ¥0。对应 DOM：`[data-region-price="basic_monthly"]`、`[data-region-price="pro_monthly"]`，内部分别有 `.currency-symbol` 与 `.price-value`。

---

*文档版本：含阶段 3 订阅页 E2E 与阶段 5/6 认证、简历匹配 E2E。*
