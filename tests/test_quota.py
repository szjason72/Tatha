"""
V1 阶段 4：配额扣减与 429 行为。
"""
import pytest
from fastapi.testclient import TestClient

from tatha.api.app import app

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer demo-token-quota-test"}


def test_job_match_429_after_free_limit():
    """Free 档每日 3 次匹配，第 4 次应返回 429。"""
    payload = {"resume_text": "test resume", "top_n": 2}
    for _ in range(3):
        r = client.post("/v1/jobs/match", json=payload, headers=AUTH_HEADER)
        assert r.status_code == 200
    r4 = client.post("/v1/jobs/match", json=payload, headers=AUTH_HEADER)
    assert r4.status_code == 429
    data = r4.json()
    assert data.get("detail", {}).get("code") == "quota_exceeded"
    assert "配额" in (data.get("detail", {}).get("message") or "")
