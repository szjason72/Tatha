# 九库与 Tatha 设计说明

> 基于《9 个 Python 库把一个月的 AI 开发周期缩短到了 3 天》的思路，将 9 个库与 **Tatha**（JobFirst 收敛项目）的能力层一一对应，便于实现时按模块选库、减少重复代码与维护成本。

---

## 一、库与 Tatha 能力映射

| 库 | 文章中的用途 | Tatha 中的用法 |
|----|--------------|----------------|
| **LiteLLM** | 统一 OpenAI / Claude / Llama 等调用，一套逻辑换模型 | 简历分析、匹配解释、诗词推荐、诗人-人格映射等**统一走 LiteLLM**；配置中指定 `model="gpt-4o"` 或 `model="claude-3-5-sonnet"`，无需为每个厂商写请求与错误处理。 |
| **MarkItDown** | Word / Excel / PDF → Markdown，减少解析与清洗 | **简历上传**：用户上传的 PDF/Word 简历先转 Markdown，再进 LlamaIndex 或直接送 PydanticAI 解析；避免手写正则、多格式分支。 |
| **LlamaIndex** | 文档加载、索引、RAG 查询 | **简历与诗人/诗词**：目录或 DB 中的文档自动加载并建向量索引；支撑「匹配解释时引用简历片段」「按情绪/关键词推荐诗词」等 RAG。 |
| **PydanticAI** | 类型安全智能体，强制返回 Pydantic 模型 | **解析结果、匹配解释、诗人推荐**：定义 `ResumeAnalysis`、`MatchExplanation`、`PoetRecommendation` 等 schema，AI 输出直接反序列化，避免「好的，这是你要的 JSON」导致解析失败。 |
| **Marvin** | 用函数签名 + docstring 定义简单 AI 能力 | **轻量任务**：从简历中提取标签、情绪→诗词关键词、意图分类（求职/陪伴）等，写成 `@marvin.fn` 函数即可，无需单独写 Prompt。 |
| **Haystack** | 检索流水线（检索 → 排序 → 生成） | **可选**：当需要多阶段检索（如先关键词再向量、再重排）或与 Haystack 生态的向量库/生成器集成时使用；与 LlamaIndex 二选一或组合（如 LlamaIndex 做索引、Haystack 做流水线）。 |
| **tiktoken** | Token 计数与成本预估 | **每次调用前**：对 Prompt 与历史做 token 计数，超长则截断或分块；**成本看板**：按模型单价估算单次与月度消耗，避免账单失控。 |
| **FAISS** | 高维向量相似度搜索 | **向量检索**：简历、职位、诗词的 embedding 存入 FAISS 索引；本地部署、毫秒级检索，与「隐私、本地优先」一致；可与 LlamaIndex 的向量存储后端结合。 |
| **Pydantic Evals** | 提示词回归测试 | **解析 / 匹配 / 推荐**等 Prompt 或 Agent：用 `Case` 与 `Dataset` 定义输入与期望输出，CI 或上线前跑 `evaluate`，防止改提示词引入回归。 |

---

## 二、按链路的推荐用法

### 2.1 文档接入（简历 / 诗人诗词）

1. **MarkItDown**：上传文件（PDF/Word/Excel）→ `MarkItDown().convert(path)` → 得到 Markdown 文本。
2. **LlamaIndex**：`SimpleDirectoryReader` 或自定义 Reader 读 Markdown/JSON（诗人诗词）；`VectorStoreIndex.from_documents()` 建索引；`as_query_engine()` 或 `as_retriever()` 供 RAG 使用。
3. **FAISS**：若 LlamaIndex 使用 FAISS 作为 vector store，则检索由 FAISS 加速；或单独用 FAISS 管理简历/职位向量。

### 2.2 模型调用与结构化输出

1. **LiteLLM**：所有 `completion()` 或流式调用统一走 `litellm.completion(model=..., messages=...)`，模型名从配置读取。
2. **PydanticAI**：需要**固定 schema** 的环节（解析结果、匹配解释、诗人推荐）用 `Agent(..., result_type=YourModel)`，保证返回可解析。
3. **Marvin**：简单分类、提取、生成列表（如标签、关键词）用 `@marvin.fn`，减少 Prompt 模板与解析逻辑。

### 2.3 检索与 RAG

1. **LlamaIndex**：主 RAG 框架，负责 load → index → query；可配置 embedding 模型与 vector store（如 FAISS）。
2. **Haystack**（可选）：若需要多组件流水线（retriever + ranker + generator），用 Haystack Pipeline 组装；否则 LlamaIndex 的 `as_query_engine()` 即可。
3. **FAISS**：作为向量存储与检索引擎，与 LlamaIndex 或 Haystack 集成。

### 2.4 成本与质量保障

1. **tiktoken**：在调用 LiteLLM/PydanticAI 前，对当前 messages 做 `encode` + `len`，超阈值则截断或拒绝，并记录预估 token 与成本。
2. **Pydantic Evals**：为「简历解析」「匹配解释」「诗词推荐」等定义 `Dataset`，在改 Prompt 或模型后跑回归，保证关键用例不退化。

---

## 三、与收敛文档的对应

- **主仓 API**：本仓对外暴露 REST（上传、解析、匹配、解释、诗人推荐），对应《开发收敛与可交付路线图》中的「主仓」与《实现路径》中的能力层。
- **单一入口**：LiteLLM 统一模型调用，避免多套 AI 入口；API 层只保留一个 FastAPI/Sanic 应用，对应「主仓入口收敛」。
- **隐私与本地**：FAISS 与可选本地 embedding 支持本地向量检索；诗人/诗词数据可只读挂载或 API 拉取，对应「诗人系统」「个人隐私」。
- **交付形态**：本仓仅提供 API，助理侧（ZeroClaw）通过 Tool 调用；前端仅作开发期直观感受，对应「形态取舍结论」。

以上设计在实现时可按 V0（上传→解析→匹配→解释）优先落地，再叠加诗人/诗词 RAG 与 Evals。
