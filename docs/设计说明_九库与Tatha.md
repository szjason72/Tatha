# 九库与 Tatha 设计说明

> 基于《9 个 Python 库把一个月的 AI 开发周期缩短到了 3 天》的思路，将 9 个库与 **Tatha**（JobFirst 收敛项目）的能力层一一对应，便于实现时按模块选库、减少重复代码与维护成本。  
> 本文档已按当前主仓**真实落地**的实现补充「落地位置」与「用法示例」。

---

## 一、库与 Tatha 能力映射

| 库 | 文章中的用途 | Tatha 中的用法 | 落地位置 |
|----|--------------|----------------|----------|
| **LiteLLM** | 统一 OpenAI / Claude / Llama 等调用，一套逻辑换模型 | 简历分析、匹配解释、诗词推荐、意图解析、文档解读等**统一走 LiteLLM**；`TATHA_DEFAULT_MODEL` 指定 `openai/gpt-4o` 或 `deepseek/deepseek-chat`，无需为每个厂商写请求与错误处理。 | `tatha.core.llm`、PydanticAI 通过 `pydantic-ai-litellm` 使用 |
| **MarkItDown** | Word / Excel / PDF → Markdown，减少解析与清洗 | **简历/文档上传**：`POST /v1/documents/convert` 内调 `stream_to_markdown()`，PDF/Word/Excel 转 Markdown 后再送 PydanticAI 或 Marvin 提取。 | `tatha.ingest.markitdown_convert`、`tatha.api.app` |
| **LlamaIndex** | 文档加载、索引、RAG 查询 | **简历与诗人/诗词**：`build_index_from_dir` / `build_index_from_documents` 建索引，`get_query_engine(namespace)` 做 RAG；支撑 `POST /v1/rag/query` 与诗人推荐。 | `tatha.retrieval.llama_index_rag` |
| **PydanticAI** | 类型安全智能体，强制返回 Pydantic 模型 | **解析与打分**：`ResumeAnalysis`、`PoetryAnalysis`、`CreditAnalysis`、`JobMatchScore` 等 schema；`run_resume_analysis(text)` / `run_credit_analysis(text)` 及职位匹配打分，输出直接反序列化。 | `tatha.agents.schemas`、`tatha.agents.document_agents`、`tatha.jobs.scoring` |
| **Marvin** | 用函数签名 + docstring 定义简单 AI 能力 | **可选后端**：`TATHA_DOCUMENT_ANALYSIS_BACKEND=marvin` 时，由 `config/extractors_schema.example.json` 动态生成提取/分类函数；意图分类等轻量任务也可用 Marvin。 | `tatha.ai.fn_from_schema`、中央大脑 `_document_analysis` 回退 |
| **Haystack** | 检索流水线（检索 → 排序 → 生成） | **可选流水线**：`build_query_pipeline(template=...)` 组装 PromptBuilder + OpenAIGenerator；`run_query_pipeline(query)` 跑「问题→回答」。可扩展为 Retriever + Reranker + Generator 或对接 Qdrant/Elasticsearch。 | `tatha.retrieval.haystack_pipeline`（懒加载导出） |
| **tiktoken** | Token 计数与成本预估 | **请求前算账**：`count_tokens(text, model_name)` 算 token 数；`estimate_input_cost(text, ..., price_per_1k_input)` 估算美元成本。无网络时回退为近似 `len(text)//2`，避免崩溃。 | `tatha.core.tokens` |
| **FAISS** | 高维向量相似度搜索 | **向量检索**：LlamaIndex 使用 `FaissVectorStore`，`build_index_from_documents` 内建 `faiss.IndexFlatL2(dim)`，索引持久化到 `.data/indices/<namespace>`；本地毫秒级检索，隐私与本地优先。 | `tatha.retrieval.llama_index_rag`（FaissVectorStore） |
| **Pydantic Evals** | 提示词回归测试 | **文档提取回归**：`resume_extract_dataset()` / `poetry_extract_dataset()` / `credit_extract_dataset()` 定义 Case；`uv run python scripts/run_document_evals.py [--dataset all|resume|poetry|credit]` 跑回归，改提示词或模型后验证不退化。 | `tatha.evals.datasets`、`scripts/run_document_evals.py` |

---

## 二、按链路的推荐用法

### 2.1 文档接入（简历 / 诗人诗词）

1. **MarkItDown**：上传文件（PDF/Word/Excel）→ `stream_to_markdown(io.BytesIO(content), filename=...)`（见 `tatha.ingest.markitdown_convert`）→ 得到 Markdown 文本。
2. **LlamaIndex**：`SimpleDirectoryReader` 或内存 `Document` 列表；`build_index_from_dir()` / `build_index_from_documents()` 建索引；`get_query_engine(namespace)` 或 `get_retriever()` 供 RAG 使用。诗词索引另见 `scripts/build_poetry_index.py`。
3. **FAISS**：LlamaIndex 默认使用 `FaissVectorStore`，检索由 FAISS 加速；向量维度由 `TATHA_EMBED_DIM` / `embed_model_type()` 决定（local 默认 384，openai 默认 1536）。

### 2.2 模型调用与结构化输出

1. **LiteLLM**：`tatha.core.llm` 提供 `completion()`、`ask_ai()`；意图解析、PydanticAI Agent 均通过 LiteLLM 统一，模型名来自 `get_default_model()`。
2. **PydanticAI**：文档解读用 `run_resume_analysis` / `run_poetry_analysis` / `run_credit_analysis` 或统一 `run_document_analysis(document_type, text)`；职位匹配打分用 `tatha.jobs.scoring` 内 Agent，返回 `JobMatchScore`。
3. **Marvin**：当 `TATHA_DOCUMENT_ANALYSIS_BACKEND=marvin` 时，`_document_analysis()` 回退到 `get_extractor(document_type)(text)`，由 JSON schema 动态生成。

### 2.3 检索与 RAG

1. **LlamaIndex**：主 RAG 框架，`tatha.retrieval` 提供 `get_query_engine(namespace)`、`get_retriever()`；embedding 与 LLM 由 `TATHA_EMBED_MODEL`、`TATHA_DEFAULT_MODEL` 统一。
2. **Haystack**（可选）：`from tatha.retrieval import build_query_pipeline, run_query_pipeline`；需要多组件（retriever + ranker + generator）或对接 Qdrant/Elasticsearch 时，在 `haystack_pipeline` 上扩展。
3. **FAISS**：已作为 LlamaIndex 的 vector store 使用，见 `llama_index_rag.build_index_from_documents` 中的 `FaissVectorStore(faiss_index=faiss.IndexFlatL2(dim))`。

### 2.4 成本与质量保障

1. **tiktoken**：调用 LLM 前对文本做 `count_tokens(text, model_name)`；可选 `estimate_input_cost(..., price_per_1k_input=0.002)` 记录预估成本。入口：`from tatha.core import count_tokens, estimate_input_cost`。
2. **Pydantic Evals**：为简历/诗词/征信解析定义 `tatha.evals.datasets` 中的 `Dataset`；运行 `scripts/run_document_evals.py`，需配置 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`。改 Prompt 或模型后跑一遍，保证关键 Case 不退化。

---

## 三、落地实现与代码位置速查

| 能力 | 模块/文件 | 典型用法 |
|------|-----------|----------|
| 配置与模型 | `tatha.core.config` | `get_default_model()`、`document_analysis_backend()`、`embed_model_type()` |
| LiteLLM 封装 | `tatha.core.llm` | `ask_ai(prompt)`、`completion(messages=...)` |
| **Token 计数** | `tatha.core.tokens` | `count_tokens(text)`、`estimate_input_cost(text, price_per_1k_input=...)` |
| 文档转 Markdown | `tatha.ingest.markitdown_convert` | `stream_to_markdown(stream, filename=...)` |
| 文档解读 schema | `tatha.agents.schemas` | `ResumeAnalysis`、`PoetryAnalysis`、`CreditAnalysis` |
| 文档解读 Agent | `tatha.agents.document_agents` | `run_resume_analysis(text)`、`run_credit_analysis(text)`、`run_document_analysis(type, text)` |
| 索引与 RAG（FAISS） | `tatha.retrieval.llama_index_rag` | `build_index_from_documents(docs, namespace)`、`get_query_engine(namespace)` |
| **Haystack 流水线** | `tatha.retrieval.haystack_pipeline` | `build_query_pipeline(template=...)`、`run_query_pipeline(query)` |
| **Pydantic Evals** | `tatha.evals.datasets`、`scripts/run_document_evals.py` | `resume_extract_dataset()`、`run_document_evals.py --dataset all` |
| 职位匹配 | `tatha.jobs` | `run_job_match_pipeline(resume_text, top_n)`、`POST /v1/jobs/match` |
| 中央大脑 | `tatha.api.central_brain` | `parse_intent(message)`、`dispatch(intent, request)`、`_document_analysis(type, text)` |
| HTTP 入口 | `tatha.api.app` | `POST /v1/ask`、`POST /v1/documents/convert`、`POST /v1/rag/query` |

---

## 四、与收敛文档的对应

- **主仓 API**：本仓对外暴露 REST（上传、解析、匹配、诗人/诗词 RAG、征信解析），对应《开发收敛与可交付路线图》中的「主仓」与《实现路径》中的能力层。
- **单一入口**：LiteLLM 统一模型调用；API 层仅一个 FastAPI 应用，`POST /v1/ask` 为单入口，中央大脑解析意图后分发到各能力端口，对应「主仓入口收敛」。
- **隐私与本地**：FAISS + 本地 HuggingFace embedding（`TATHA_EMBED_MODEL=local`）支持无外网 Key 的向量检索；索引存于 `TATHA_INDEX_STORAGE`（默认 `.data/indices`），不提交仓库，对应「诗人系统」「个人隐私」。
- **交付形态**：本仓仅提供 API，助理侧（ZeroClaw）通过 Tool 调用；前端仅作开发期直观感受，对应「形态取舍结论」。

以上设计已在主仓按 V0 落地（上传→解析→匹配→解释、诗人/诗词 RAG、征信解析、E2E Resume→Job→Company），并叠加 **tiktoken / Haystack / FAISS / Pydantic Evals** 四类能力的具体实现与脚本。
