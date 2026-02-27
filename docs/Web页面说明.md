# Tatha Web 页面说明（认证订阅页 + 匹配体验）

> 说明当前 Web 页面的形式（单页 HTML vs Vue/Vite）及与 ServBay 的参考关系。

---

## 一、Vue 和 Vite 分别是什么

| 名词 | 含义 |
|------|------|
| **Vue** | 前端**框架**：用「组件」的方式写页面，数据与视图绑定，适合多页面、复杂交互（如登录表单、多步引导）。 |
| **Vite** | 前端**构建工具**：负责开发时热更新、打包压缩、产出可部署的 JS/CSS。常与 Vue 一起用（官方推荐 Vue 项目用 Vite）。 |
| **常见组合** | **Vite + Vue**：用 Vite 创建 Vue 项目，写 `.vue` 组件，运行 `npm run build` 得到静态文件，再由后端或 CDN 提供。ServBay 等现代站多为此类（打包后为带 hash 的 .js/.css）。 |

所以「Vue 开发」和「Vite」不是二选一，而是**一起用**：Vite 负责工程与构建，Vue 负责页面与组件。

---

## 二、当前 Tatha 的选型（参考 ServBay 的「形态」而非必上同款技术栈）

**目标**：认证订阅入口（三档 + CTA）+ 匹配体验页，**单页、静态或轻动态即可**（见《认证订阅与档位设计》）。

**当前实现**：

- **单文件 HTML**，不引入 Vue、不引入 Vite，无 Node/npm 依赖。
- **index.html**：认证订阅页，参考 [ServBay 定价页](https://www.servbay.com/zh-CN/pricing) 的布局（三档卡片、一句话价值主张、每档一个 CTA）；「免费注册/体验」链到 `demo.html`。
- **demo.html**：匹配体验页，调用 `/v1/jobs/match` 与 `/v1/ask`，与现有 V0 一致。
- API 启动后：访问 `http://127.0.0.1:8010/` 或 `http://127.0.0.1:8010/index.html` 进入订阅页，点击「免费注册/体验」进入 `demo.html`。

**这样选的原因**：

- 与「单页、静态或轻动态」的定位一致，上手快，无需学 Vue/Vite。
- 与现有 Tatha 一致：仅 Python + 单文件 HTML，由 FastAPI 同源提供，无 CORS、无构建步骤。
- **参考 ServBay** 的是**页面形态**（三档、CTA、简洁），不是必须用他们那套前端技术。

---

## 三、若后续要做成 Vue + Vite

当需要以下能力时，再考虑在 Tatha 下增加 **Vite + Vue** 前端工程（例如 `web/` 或 `frontend/`）：

- 多页面（订阅页、登录页、匹配体验页、个人中心）且希望组件复用。
- 登录态、路由、与后端鉴权接口的对接。
- 更复杂的交互（如月付/年付切换、表单校验、步骤引导）。

那时可：

1. 在 Tatha 下执行 `npm create vite@latest web -- --template vue`，在 `web/` 内用 Vue 3 + Vite。
2. 把当前 `index.html` / `demo.html` 的**内容与结构**迁移为 Vue 组件与路由。
3. 执行 `npm run build`，将 `dist/` 产物交给 FastAPI 的静态挂载或单独部署。

当前阶段**不必**上 Vue/Vite，现有单页 HTML 已满足「V0 + 认证订阅页」的交付与演示需求。

---

## 四、文件与访问路径

| 文件 | 说明 | 访问路径（API 启动后） |
|------|------|------------------------|
| **index.html** | 认证订阅入口（三档 + CTA） | `/` 或 `/index.html` |
| **demo.html** | 匹配体验（调用主仓 API） | `/demo.html` |

启动方式：`uv run uvicorn tatha.api.app:app --host 127.0.0.1 --port 8010`，浏览器打开 `http://127.0.0.1:8010/` 即可。
