"""
LlamaIndex：连接私有数据与大模型，文档读取 → 索引构建 → 查询接口。

索引与向量数据仅存于配置的本地目录（见 TATHA_INDEX_STORAGE），不提交仓库，
适用于简历等个人信息隐私保护。

Embedding 与 LLM 均支持统一切换：
- TATHA_EMBED_MODEL=local（默认）：本地 HuggingFace，无需 API Key，适配仅配置 DeepSeek 的场景。
- TATHA_EMBED_MODEL=openai：使用 OpenAI embedding（需 OPENAI_API_KEY）。
- RAG 回答使用的 LLM 由 TATHA_DEFAULT_MODEL + LiteLLM 统一（如 deepseek/deepseek-chat）。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# 在首次导入时即设置 LlamaIndex Settings，避免后续任何代码触发「default」embed（OpenAI）导致 401
def _ensure_llamaindex_settings() -> None:
    """统一设置 LlamaIndex 的 embed 与 LLM，与 TATHA 配置一致（LiteLLM/DeepSeek 切换）。"""
    from llama_index.core import Settings
    from tatha.core.config import get_default_model, embed_model_type
    # Embedding：local = HuggingFace 多语言小模型（384 维），无需 API Key
    if embed_model_type() == "local":
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        _local_embed_model = os.getenv("TATHA_EMBED_LOCAL_MODEL") or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        Settings.embed_model = HuggingFaceEmbedding(model_name=_local_embed_model)
    # RAG 回答用的 LLM：LiteLLM，与 TATHA_DEFAULT_MODEL 一致（如 deepseek/deepseek-chat）
    from llama_index.llms.litellm import LiteLLM
    Settings.llm = LiteLLM(model=get_default_model())


# 导入 retrieval 时立即执行一次，确保后续 build/load/query 都用 Tatha 配置
_ensure_llamaindex_settings()

from llama_index.core import (
    Document,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.vector_stores.faiss import FaissVectorStore


def _embed_dim() -> int:
    """向量维度，需与 embedding 模型一致。local 默认 384，openai 默认 1536。"""
    dim_env = os.getenv("TATHA_EMBED_DIM")
    if dim_env:
        return int(dim_env)
    from tatha.core.config import embed_model_type
    return 384 if embed_model_type() == "local" else 1536


def _get_persist_dir(namespace: str, storage_root: Path | None = None) -> Path:
    """每个命名空间（如 resume、poetry）单独目录，便于隔离与权限。"""
    from tatha.core.config import get_index_storage_root
    root = storage_root or get_index_storage_root()
    path = root / namespace
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_index_from_dir(
    directory: str | Path,
    namespace: str = "docs",
    storage_root: Path | None = None,
    **reader_kwargs: Any,
) -> VectorStoreIndex:
    """
    从目录读取所有文档并构建 FAISS 向量索引，持久化到本地。
    directory: 文档目录（支持 Markdown、PDF 等，由 SimpleDirectoryReader 解析）。
    namespace: 索引命名空间，用于子目录与多租户隔离（如 resume、poetry）。
    """
    from llama_index.core import SimpleDirectoryReader

    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise FileNotFoundError(f"目录不存在或非目录: {dir_path}")

    docs = SimpleDirectoryReader(input_dir=str(dir_path), **reader_kwargs).load_data()
    return build_index_from_documents(docs, namespace=namespace, storage_root=storage_root)


def build_index_from_documents(
    documents: list[Document],
    namespace: str = "docs",
    storage_root: Path | None = None,
) -> VectorStoreIndex:
    """
    从内存中的文档列表构建 FAISS 向量索引并持久化。
    适用于已将上传文件转为 Markdown 后不落盘原文、仅建索引的场景（隐私友好）。
    向量维度由 TATHA_EMBED_DIM 控制，默认 1536（OpenAI embedding）。
    """
    if not documents:
        raise ValueError("documents 不能为空")

    import faiss
    persist_dir = _get_persist_dir(namespace, storage_root)
    dim = _embed_dim()
    faiss_index = faiss.IndexFlatL2(dim)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,
    )
    index.storage_context.persist(persist_dir=str(persist_dir))
    return index


def load_index(
    namespace: str,
    storage_root: Path | None = None,
) -> VectorStoreIndex:
    """从本地加载已持久化的索引。"""
    persist_dir = _get_persist_dir(namespace, storage_root)
    if not persist_dir.exists():
        raise FileNotFoundError(f"索引目录不存在: {persist_dir}，请先构建索引")

    vector_store = FaissVectorStore.from_persist_dir(str(persist_dir))
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
        persist_dir=str(persist_dir),
    )
    return load_index_from_storage(storage_context)


def get_query_engine(
    namespace: str,
    storage_root: Path | None = None,
    **engine_kwargs: Any,
) -> Any:
    """
    获取 RAG 查询引擎：对私有索引发起自然语言查询，返回基于检索结果的回答。
    示例：engine.query("总结文档的核心观点")
    """
    index = load_index(namespace=namespace, storage_root=storage_root)
    return index.as_query_engine(**engine_kwargs)


def get_retriever(
    namespace: str,
    storage_root: Path | None = None,
    similarity_top_k: int = 4,
    **kwargs: Any,
) -> Any:
    """仅做检索、不做生成的 Retriever，供自定义 RAG 流程使用。"""
    index = load_index(namespace=namespace, storage_root=storage_root)
    return index.as_retriever(similarity_top_k=similarity_top_k, **kwargs)
