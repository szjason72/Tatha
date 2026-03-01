"""
/v1/rag/query 接口测试。

所有测试均 mock get_query_engine，保证无需预构建 FAISS 索引、无需 LLM key 即可运行。

覆盖：
- 401 无鉴权
- Free 档 RAG 配额为 0，首次即返回 429
- Basic 档正常查询 → 200 + answer 结构
- 索引不存在（FileNotFoundError）→ 200 + error 含「索引不存在」
- 未知异常 → 200 + error 字段非空
- namespace 透传到响应
- 连续查询耗尽 basic 配额后返回 429
"""
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tatha.api.app import app
from tatha.api.quota import _memory as quota_memory

client = TestClient(app)

FREE_AUTH = {"Authorization": "Bearer demo-token-rag-free"}
BASIC_AUTH = {"Authorization": "Bearer demo-token-rag-basic"}
PRO_AUTH = {"Authorization": "Bearer demo-token-rag-pro"}

RAG_PAYLOAD = {"namespace": "poetry", "query": "推荐一首送别主题的古诗"}


def _fake_engine(answer: str = "举头望明月，低头思故乡。——李白《静夜思》"):
    """返回一个行为正常的 mock query engine。"""
    engine = MagicMock()
    engine.query.return_value = answer
    return engine


def _basic_ctx():
    """将 basic token 映射到 basic 档（通过 tier_store 覆盖）。"""
    from tatha.api.tier_store import set_tier
    set_tier("stub-demo-token-rag-basic", "basic")


def _pro_ctx():
    from tatha.api.tier_store import set_tier
    set_tier("stub-demo-token-rag-pro", "pro")


# ──────────────────────────────────────────────
# 鉴权
# ──────────────────────────────────────────────

def test_rag_query_no_token_401():
    r = client.post("/v1/rag/query", json=RAG_PAYLOAD)
    assert r.status_code == 401


def test_rag_query_invalid_token_401():
    r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers={"Authorization": "Bearer "})
    assert r.status_code == 401


# ──────────────────────────────────────────────
# 配额：Free 档 RAG 上限为 0
# ──────────────────────────────────────────────

def test_rag_query_free_tier_quota_zero():
    """Free 档 RAG 配额为 0，首次请求即返回 429。"""
    r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=FREE_AUTH)
    assert r.status_code == 429
    detail = r.json().get("detail", {})
    assert detail.get("code") == "quota_exceeded"
    assert "配额" in (detail.get("message") or "")


# ──────────────────────────────────────────────
# 正常查询 — Basic 档
# ──────────────────────────────────────────────

def test_rag_query_basic_returns_answer():
    _basic_ctx()
    engine = _fake_engine("举头望明月，低头思故乡。")
    with patch("tatha.retrieval.get_query_engine", return_value=engine):
        r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=BASIC_AUTH)
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "namespace" in data
    assert data["namespace"] == "poetry"
    assert "举头望明月" in data["answer"]
    assert data.get("error") is None


def test_rag_query_namespace_passthrough():
    _basic_ctx()
    engine = _fake_engine("结果")
    with patch("tatha.retrieval.get_query_engine", return_value=engine) as mock_get:
        r = client.post("/v1/rag/query", json={"namespace": "resume", "query": "联系方式"}, headers=BASIC_AUTH)
    assert r.status_code == 200
    # namespace 透传：get_query_engine 应以 namespace="resume" 调用
    mock_get.assert_called_once_with(namespace="resume")
    assert r.json()["namespace"] == "resume"


# ──────────────────────────────────────────────
# 错误处理
# ──────────────────────────────────────────────

def test_rag_query_index_not_found():
    """索引文件不存在时返回 200，error 字段含「索引不存在」。"""
    _basic_ctx()
    with patch("tatha.retrieval.get_query_engine", side_effect=FileNotFoundError("no index")):
        r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=BASIC_AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == ""
    assert data["error"] is not None
    assert "索引不存在" in data["error"]


def test_rag_query_generic_exception():
    """引擎抛出未知异常时返回 200，error 字段非空。"""
    _basic_ctx()
    with patch("tatha.retrieval.get_query_engine", side_effect=RuntimeError("faiss crash")):
        r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=BASIC_AUTH)
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == ""
    assert "faiss crash" in (data.get("error") or "")


def test_rag_query_engine_query_raises():
    """get_query_engine 正常但 engine.query() 抛异常时同样优雅降级。"""
    _basic_ctx()
    engine = MagicMock()
    engine.query.side_effect = ValueError("embedding error")
    with patch("tatha.retrieval.get_query_engine", return_value=engine):
        r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=BASIC_AUTH)
    assert r.status_code == 200
    data = r.json()
    assert "embedding error" in (data.get("error") or "")


# ──────────────────────────────────────────────
# 配额耗尽 — Basic 档 10 次后 429
# ──────────────────────────────────────────────

def test_rag_query_basic_quota_exhausted():
    """Basic 档 RAG 每日 10 次，第 11 次应返回 429。"""
    from tatha.api.tier_store import set_tier
    # 用独立 token 避免污染其他用例
    token = "demo-token-rag-basic-quota"
    user_id = "stub-demo-token-rag-basic-quota"
    set_tier(user_id, "basic")
    headers = {"Authorization": f"Bearer {token}"}
    engine = _fake_engine("答案")

    with patch("tatha.retrieval.get_query_engine", return_value=engine):
        for i in range(10):
            r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=headers)
            assert r.status_code == 200, f"第 {i+1} 次应成功，实际: {r.status_code}"

        r11 = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=headers)
    assert r11.status_code == 429
    assert r11.json().get("detail", {}).get("code") == "quota_exceeded"


# ──────────────────────────────────────────────
# Pro 档 — 不受配额限制
# ──────────────────────────────────────────────

def test_rag_query_pro_no_quota_limit():
    """Pro 档 RAG 配额 9999，多次请求均应 200。"""
    _pro_ctx()
    engine = _fake_engine("pro 答案")
    with patch("tatha.retrieval.get_query_engine", return_value=engine):
        for _ in range(5):
            r = client.post("/v1/rag/query", json=RAG_PAYLOAD, headers=PRO_AUTH)
            assert r.status_code == 200
