"""
V1 阶段 3：GET /v1/region 接口契约测试。
保证返回结构、国内/境外定价与 query 覆盖不被改坏。
"""
import pytest
from fastapi.testclient import TestClient

from tatha.api.app import app

client = TestClient(app)


def test_region_response_shape():
    """响应必须包含 country、currency、locale、pricing。"""
    r = client.get("/v1/region")
    assert r.status_code == 200
    data = r.json()
    assert "country" in data
    assert "currency" in data
    assert "locale" in data
    assert "pricing" in data
    p = data["pricing"]
    assert "currency" in p
    assert "basic_monthly" in p
    assert "basic_yearly" in p
    assert "pro_monthly" in p
    assert "pro_yearly" in p


def test_region_country_cn_returns_cny():
    """?country=CN 返回人民币与国内定价。"""
    r = client.get("/v1/region?country=CN")
    assert r.status_code == 200
    data = r.json()
    assert data["country"] == "CN"
    assert data["currency"] == "CNY"
    assert data["locale"] == "zh-CN"
    assert data["pricing"]["currency"] == "CNY"
    assert data["pricing"]["basic_monthly"] == 99
    assert data["pricing"]["pro_monthly"] == 199


def test_region_intl_returns_usd():
    """?region=intl 返回美元与境外定价。"""
    r = client.get("/v1/region?region=intl")
    assert r.status_code == 200
    data = r.json()
    assert data["currency"] == "USD"
    assert data["pricing"]["currency"] == "USD"
    assert data["pricing"]["basic_monthly"] == 9.9
    assert data["pricing"]["pro_monthly"] == 19.9
