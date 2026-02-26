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

### 四类能力落地：Haystack / tiktoken / FAISS / Pydantic Evals

| 能力 | 落地位置 | 用法简述 |
|------|----------|----------|
| **tiktoken** | `tatha.core.tokens` | `count_tokens(text, model_name)` 请求前算 token 数；`estimate_input_cost(text, ..., price_per_1k_input)` 估算美元成本，避免超长 Prompt 暴雷。 |
| **FAISS** | `tatha.retrieval.llama_index_rag` | 通过 LlamaIndex 的 `FaissVectorStore` 做向量索引与检索，`build_index_from_documents` / `get_query_engine`；本地毫秒级相似度搜索，适合简历/诗词等私有数据。 |
| **Haystack** | `tatha.retrieval.haystack_pipeline` | `build_query_pipeline(template=...)` 组装 PromptBuilder + OpenAIGenerator；`run_query_pipeline(query)` 跑「问题→回答」流水线。可扩展为 Retriever + Reranker + Generator 或对接 Qdrant/Elasticsearch。 |
| **Pydantic Evals** | `tatha.evals` + `scripts/run_document_evals.py` | `resume_extract_dataset()` / `poetry_extract_dataset()` / `credit_extract_dataset()` 预设 Case；`uv run python scripts/run_document_evals.py [--dataset all|resume|poetry|credit]` 跑回归，改提示词后验证不退化。 |

### LiteLLM 统一多平台模型调用

不同厂商 API 标准各异，LiteLLM 将接口统一后，**换模型只需改一个字符串**，无需三套请求与错误处理：

- **环境**：任选其一配置 key 即可（`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`DEEPSEEK_API_KEY`），LiteLLM 自动读取。
- **默认模型**：`.env` 中 `TATHA_DEFAULT_MODEL`，例如 `openai/gpt-4o`、`deepseek/deepseek-chat`、`anthropic/claude-3-5-sonnet`。
- **代码**：`tatha.core.llm` 提供：
  - `ask_ai(prompt, model=None)`：单轮问答，返回回复正文；不传 `model` 用默认。
  - `completion(model=None, messages=..., **kwargs)`：多轮或带 system 的完整调用，返回 LiteLLM response。

中央大脑的意图解析、Marvin 提取等均通过该统一入口使用模型，对比 GPT / Claude / DeepSeek 效果时只需改配置或传入不同 `model`。

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
        ├── jobs/           # 职位匹配流水线（职位源 + LLM 打分）
        ├── evals/          # Pydantic Evals 回归用例
        └── api/             # HTTP 入口（供助理 Tool 调用）
```

---

## 单入口与中央大脑

内部虽有解析、匹配、诗人 RAG、征信、MBTI 等多类能力与端口，**对用户/助理只暴露一个入口**：用户只提需求，由**中央大脑**解析意图并分发到对应内部处理端口，再统一返回。助理侧只需调用**单一 API**（如 `POST /v1/ask`），无需关心内部端口与路径。详见 [docs/架构_单入口与中央大脑.md](docs/架构_单入口与中央大脑.md)。

### PydanticAI：文档解读的数据边界

为避免 AI 在返回结构化数据时夹带「好的，这是你要的 JSON」等导致解析崩溃的文本，我们使用 **PydanticAI** 的 `result_type` 定义数据边界，把 AI 调用变成类型安全的函数调用。

- **模型**：`ResumeAnalysis`、`PoetryAnalysis`、`CreditAnalysis`（见 `tatha.agents.schemas`），与简历/诗词/征信字段一一对应。
- **智能体**：`tatha.agents.document_agents` 中为每种文档类型配置了 PydanticAI Agent（`result_type` + system_prompt），模型通过 **LiteLLM**（`pydantic-ai-litellm`）统一切换，与 `TATHA_DEFAULT_MODEL` 一致。
- **使用**：`run_resume_analysis(text)`、`run_poetry_analysis(text)`、`run_credit_analysis(text)` 或统一入口 `run_document_analysis(document_type, text)`，返回类型化结果（如 `output.data.summary`）。
- **后端切换**：`TATHA_DOCUMENT_ANALYSIS_BACKEND=pydantic_ai`（默认）使用上述 PydanticAI 边界；设为 `marvin` 时改用由 JSON schema 动态生成的 Marvin 提取器。

中央大脑与 `POST /v1/documents/convert` 的解读逻辑均走该配置，默认使用 PydanticAI 边界。

### 从 JSON 生产 Marvin 提取/分类函数

文档类型不限于简历（resume），还包括诗词（poetry）、征信（credit）等。你只需提供**解析后的 JSON**（描述每种文档的字段或分类标签），即可自动生成 Marvin 风格的提取/分类函数，无需手写复杂 Prompt。

- **JSON 结构**：`config/extractors_schema.example.json`  
  - `document_types`：每种文档的 `description` + `fields`（name / type / description）→ 生成 `extract_<type>(text)`，返回结构化结果。  
  - `classifiers`：每个分类任务的 `description` + `labels` → 生成 `classify_<name>(text)`。
- **使用**：未配置 `TATHA_EXTRACTORS_SCHEMA` 时，默认加载 `config/extractors_schema.example.json`（若存在）。中央大脑在 `resume_upload` / `poetry` / `credit` 等意图下，若有对应提取器且用户消息带文本，会调用该提取函数并返回 `extracted` 字段。
- **代码**：`tatha.ai` 下的 `load_schema`、`load_and_produce`、`get_extractor`、`get_classifier`。

### 简历上传解析流程（MarkItDown + 提取）

多格式文档（PDF/Word/Excel）先统一转 Markdown，再按文档类型做结构化提取，形成**高效解析标准流水线**：

1. **上传**：`POST /v1/documents/convert`，表单字段 `file`（必填）、`document_type`（可选，默认 `resume`）。
2. **转换**：使用 **MarkItDown** 将文件转为 Markdown（保留标题与表格结构，便于后续处理）。
3. **提取**：默认使用 PydanticAI 类型安全边界（见上节）对 Markdown 做结构化解读；可配置为 Marvin（见「从 JSON 生产 Marvin」）。响应中返回 `extracted`。
4. **说明**：扫描件或复杂图片表格效果会有波动，主要处理文字层。

示例：`curl -X POST http://127.0.0.1:8010/v1/documents/convert -F "file=@resume.pdf" -F "document_type=resume"`。代码入口：`tatha.ingest.markitdown_convert`。

### 职位匹配流水线（job_match）

在 Tatha 内自建「抓职位 + 简历 vs 职位 LLM 打分 + 排序 Top-N」闭环，借鉴 Argus（职位源）与 DailyJobMatch（打分结构）。

- **职位源**：`mock`（默认，5 条示例职位，无需 API Key）或 `apify_linkedin`（需 `APIFY_API_KEY`，从 Apify LinkedIn Job Scraper 拉取）。配置 `TATHA_JOB_SOURCE`、可选 `TATHA_JOB_TOP_N`（默认 5）。
- **打分**：PydanticAI Agent 对「简历 + 职位描述」做多维度打分（`JobMatchScore`：overall、skills_overlap、experience_relevance 等），并纳入**钱多事少离家近**三维：salary_match（钱多）、location_match（离家近）、culture_workload_match（事少）；流水线会将职位「工作地点」拼入描述供模型参考。LiteLLM 统一切换模型。
- **触发**：`POST /v1/ask` 意图为 `job_match` 时需提供简历（`resume_text` 或 `context.resume_text`）；或直接 `POST /v1/jobs/match`，body `{"resume_text": "..."}`。
- **代码**：`tatha.jobs`（`sources`、`scoring`、`pipeline`）。

### Resume → Job → Company E2E 测试流程

业务流程：用户先找岗位（简历 → 职位匹配）→ 得到高分段岗位后，再关心**该公司**经营/征信，辅助是否投递。三阶段对应：

1. **Resume**：简历输入（文件经 MarkItDown 转 Markdown，或直接文本）。
2. **Job**：`run_job_match_pipeline(resume_text)` 或 `POST /v1/jobs/match`，得到带 `job.company` 的匹配列表。
3. **Company**：对匹配结果中的公司做征信解析（主体明确为该公司），`run_credit_analysis(...)` 或 `POST /v1/ask` 带征信意图与公司名。

- **本地脚本**（不依赖已启动 API）：`uv run python scripts/test_resume_job_company_flow.py [简历文件路径]`，默认用内置简历摘要，依次执行三阶段并断言。
- **HTTP 串联**（需先启动 API）：`./scripts/test_improvements.sh` 中 **§12** 用 `POST /v1/jobs/match` 得到首条匹配公司，再 `POST /v1/ask` 查该公司征信并校验 `intent=credit`、`extracted.entity_name`。

### LlamaIndex：私有数据接入与 RAG

数据源（尤其简历等个人信息）需隐私保护，索引与向量仅存于本地配置目录，不提交仓库。

- **流程**：文档读取 → 索引构建（FAISS 向量库）→ 查询接口；LlamaIndex 提供完整链路，便于复杂文档与 RAG。
- **存储**：`TATHA_INDEX_STORAGE` 指定索引根目录（默认 `.data/indices`）；`.data/` 已加入 `.gitignore`，简历等敏感数据不会进入版本库。
- **命名空间**：按 `namespace` 隔离（如 `resume`、`poetry`），便于多类数据与多租户。
- **构建索引**：
  - `build_index_from_dir("./docs", namespace="resume")`：从目录读取所有文档并建索引；
  - `build_index_from_documents(docs, namespace="resume")`：从内存文档（如上传转 Markdown 后）建索引，可不落盘原文；
  - **诗词索引**：`uv run python scripts/build_poetry_index.py [--max-docs N]` 从本地 **poetry-knowledge-base** 项目（与 Tatha 同级目录）的 `poems/poems_annotated.json`（或 `poems_index.json`）构建 `namespace=poetry` 的索引；数据源默认 `../poetry-knowledge-base/poems/`，可通过 `TATHA_POETRY_INDEX_SOURCE` 指定 JSON 路径；`--max-docs 500` 可先建小索引做测试。
- **查询**：`get_query_engine(namespace="resume").query("总结文档的核心观点")`，或调用 `POST /v1/rag/query`，body `{"namespace": "resume", "query": "..."}`。
- **LLM 统一切换**：RAG 回答使用的 LLM 由 **LiteLLM** + `TATHA_DEFAULT_MODEL` 提供（如 `deepseek/deepseek-chat`），与意图解析、PydanticAI 一致。索引用的 **embedding** 单独配置：`TATHA_EMBED_MODEL=local`（默认，本地 HuggingFace，无需 API Key，适配仅配 DeepSeek）或 `openai`；`TATHA_EMBED_DIM` 需与所选 embed 一致（local 默认 384，openai 默认 1536）。代码入口：`tatha.retrieval`。

---

## 快速开始

**V0 验收**：按《开发收敛与可交付路线图》要求，新成员可按 [docs/V0演示清单.md](docs/V0演示清单.md) 从环境准备到「上传简历 → 调用匹配 API → 看到匹配结果」跑通端到端链路。**仅本仓即可独立交付测试**（无需其它仓库），见演示清单「独立交付测试说明」。

1. **环境**：Python 3.10+，建议使用虚拟环境或 [ServBay](https://www.servbay.com) 等一键环境。  
   **端口**：Tatha 默认使用 **8010**，避免与 ServBay 等占用 **8000** 的服务冲突；可在 `.env` 中设置 `TATHA_API_PORT`。
2. **依赖**：`pip install -r requirements.txt` 或 `uv sync`（若用 pyproject.toml）。
3. **配置**：复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`（或所用模型）、数据库与向量库连接等。
4. **启动 API**（唯一对外端口，内部由中央大脑分发）。默认用 **8010**，避免与 ServBay 等占用 8000 的服务冲突：
   ```bash
   uv run uvicorn tatha.api.app:app --host 127.0.0.1 --port 8010
   ```
5. **健康检查**：`curl -s http://127.0.0.1:8010/health`；用户/助理请求统一发往 `POST /v1/ask`。
6. **可选：用浏览器打开演示页体验匹配结果**。启动 API 后访问 **http://127.0.0.1:8010/demo.html**（或直接打开仓库根目录下的 `demo.html` 文件；若遇 CORS，请通过上述同源 URL 访问）。单文件 HTML，调用 `POST /v1/jobs/match` 与 `POST /v1/ask`，在页面中展示匹配结果，仅用于开发期直观感受。

---

## 与 JobFirst 主仓的关系

- **收敛期**：Tatha 可作为**新的主仓**，从零按「九库 + 单一入口」搭建，再逐步迁移或对接现有 JobFirst 主仓的 DB/向量库；也可在现有 JobFirst 主仓内**引入这 9 个库**，替换/收敛原有 AI 与解析逻辑。
- **交付形态**：以**助理侧**为主；本仓仅提供 API，前端仅作开发期直观感受用。见 [开发收敛与可交付路线图 §六](../JobFirst/docs/开发收敛与可交付路线图.md#六可选路线个人-ai-助理版zeroclaw)。
- **V0 之后**：V1/V2/V3 版本定义与开发计划见 [开发收敛与可交付路线图](../JobFirst/docs/开发收敛与可交付路线图.md) §三、§六、§七；本仓 [V0 演示清单](docs/V0演示清单.md) §六 有简要索引。
