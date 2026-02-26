#!/usr/bin/env python3
"""构建 resume 命名空间的 FAISS 索引。默认 TATHA_EMBED_MODEL=local（无需 API Key）；RAG LLM 用 TATHA_DEFAULT_MODEL（如 DeepSeek）。"""
# 必须先导入 tatha.retrieval，以在 LlamaIndex 使用默认 Settings 前注入 embed_model=local 与 LiteLLM
from tatha.retrieval import build_index_from_documents
from llama_index.core import Document

docs = [Document(text="李四，硕士清华大学，技能 Java 与架构设计，5 年大厂后端。")]
build_index_from_documents(docs, namespace="resume")
print("索引已构建到 .data/indices/resume")
