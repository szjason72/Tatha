# Tatha

**Tatha** 是 JobFirst 收敛项目名称，面向「人生成长的分身系统」：从求职之路开始，以个人 AI 助理（ZeroClaw + 主仓 API）为交付形态，提供求职能力与日常陪伴（诗人/诗词、情绪价值），并坚持个人隐私与本地优先。

本仓库为 **Tatha 主仓 Python 能力层**：简历解析、职位匹配、诗人/诗词 RAG、统一模型调用等，供 [ZeroClaw 助理](https://github.com/zeroclaw-labs/zeroclaw) 通过 HTTP Tool 调用。收敛与产品定义见 [JobFirst/docs/开发收敛与可交付路线图.md](../JobFirst/docs/开发收敛与可交付路线图.md)、[JobFirst 个人 AI 助理版（ZeroClaw 路线）](../JobFirst/docs/JobFirst个人AI助理版_ZeroClaw路线.md)。

---

## 技术选型：9 库缩短 AI 开发周期

为减少重复封装、统一多模型调用与文档解析、保证输出可校验并控制成本，本仓采用以下 9 个库覆盖「数据接入 → 模型调用 → 检索 → 评估」全链路：

| 库 | 用途 | 在 Tatha 中的角色 |
|----|------|------------------|
| **LiteLLM** | 统一多平台模型调用（OpenAI / Claude / 等） | 简历分析、匹配解释、诗词推荐等统一入口，换模型只改配置 |
| **MarkItDown** | 多格式文档 → Markdown | 用户上传的 PDF/Word/Excel 简历统一转 Markdown，再进解析与向量化 |
| **LlamaIndex** | 文档读取、索引构建、RAG 查询 | 简历与诗人/诗词文档的索引与检索，支撑匹配与陪伴侧 RAG |
| **PydanticAI** | 类型安全的智能体与结构化输出 | 解析结果、匹配解释、诗人推荐等返回固定 schema，避免「AI 多打一句话」导致解析崩溃 |
| **Marvin** | 将 AI 能力封装为函数 | 轻量分类、标签提取、情绪→诗词关键词等，最小侵入集成 |
| **Haystack** | 端到端检索流水线 | 可选：大规模语义检索、多组件流水线（检索+排序+生成） |
| **tiktoken** | Token 计数与成本预估 | 请求前算账，控制单次调用与月度成本 |
| **FAISS** | 高效向量相似度搜索 | 简历/职位/诗词向量检索，本地部署友好 |
| **Pydantic Evals** | 提示词回归测试 | 解析、匹配、推荐等 Prompt 的自动化回归，避免改一处带出多处问题 |

详见 [docs/设计说明_九库与Tatha.md](docs/设计说明_九库与Tatha.md)。

---

## 项目结构（概要）

```
Tatha/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
├── docs/
│   └── 设计说明_九库与Tatha.md
└── src/
    └── tatha/
        ├── __init__.py
        ├── core/           # 配置、LiteLLM 封装、tiktoken 预估
        ├── ingest/         # MarkItDown + LlamaIndex 文档接入
        ├── agents/         # PydanticAI / Marvin 分析与提取
        ├── retrieval/      # 向量索引与检索（LlamaIndex + FAISS）
        ├── evals/          # Pydantic Evals 回归用例
        └── api/             # HTTP 入口（供助理 Tool 调用）
```

---

## 单入口与中央大脑

内部虽有解析、匹配、诗人 RAG、征信、MBTI 等多类能力与端口，**对用户/助理只暴露一个入口**：用户只提需求，由**中央大脑**解析意图并分发到对应内部处理端口，再统一返回。助理侧只需调用**单一 API**（如 `POST /v1/ask`），无需关心内部端口与路径。详见 [docs/架构_单入口与中央大脑.md](docs/架构_单入口与中央大脑.md)。

---

## 快速开始

1. **环境**：Python 3.10+，建议使用虚拟环境或 [ServBay](https://www.servbay.com) 等一键环境。
2. **依赖**：`pip install -r requirements.txt` 或 `uv sync`（若用 pyproject.toml）。
3. **配置**：复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`（或所用模型）、数据库与向量库连接等。
4. **启动 API**（唯一对外端口，内部由中央大脑分发）：
   ```bash
   uv run uvicorn tatha.api.app:app --host 0.0.0.0 --port 8000
   ```
5. **健康检查**：`curl -s http://127.0.0.1:8000/health`；用户/助理请求统一发往 `POST /v1/ask`（中央大脑入口，待实现）。

---

## 与 JobFirst 主仓的关系

- **收敛期**：Tatha 可作为**新的主仓**，从零按「九库 + 单一入口」搭建，再逐步迁移或对接现有 JobFirst 主仓的 DB/向量库；也可在现有 JobFirst 主仓内**引入这 9 个库**，替换/收敛原有 AI 与解析逻辑。
- **交付形态**：以**助理侧**为主；本仓仅提供 API，前端仅作开发期直观感受用。见 [开发收敛与可交付路线图 §六](../JobFirst/docs/开发收敛与可交付路线图.md#六可选路线个人-ai-助理版zeroclaw)。
