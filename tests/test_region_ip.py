"""
region.py 中 _country_from_ip_api 及相关路径的 mock 测试。

所有网络调用均通过 unittest.mock 拦截，保证：
- 无需真实网络
- 覆盖成功/失败/超时/格式错误等边界情况
- 验证 IP 解析优先级链（CDN 头 > 环境变量 > ip-api）
"""
import io
import json
import os
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tatha.api.app import app
from tatha.api.region import (
    _country_from_ip_api,
    _is_private_ip,
    get_client_ip,
    get_country,
    get_pricing,
    get_region_response,
)

client = TestClient(app)


# ──────────────────────────────────────────────
# 辅助：构造伪 FastAPI Request
# ──────────────────────────────────────────────

def _make_request(headers: dict | None = None, client_host: str = "1.2.3.4", query_params: dict | None = None):
    """构造一个最小化 mock Request，仅实现 region.py 所需属性。"""
    req = MagicMock()
    h = headers or {}
    req.headers = MagicMock()
    req.headers.get = lambda key, default=None: h.get(key, default)
    req.client = MagicMock()
    req.client.host = client_host
    qp = query_params or {}
    req.query_params = MagicMock()
    req.query_params.get = lambda key, default=None: qp.get(key, default)
    return req


# ──────────────────────────────────────────────
# 1. _is_private_ip
# ──────────────────────────────────────────────

class TestIsPrivateIp:
    @pytest.mark.parametrize("ip", [
        "127.0.0.1", "192.168.1.1", "10.0.0.1", "::1", "fe80::1", ""
    ])
    def test_private(self, ip):
        assert _is_private_ip(ip) is True

    @pytest.mark.parametrize("ip", [
        "8.8.8.8", "114.114.114.114", "203.0.113.1"
    ])
    def test_public(self, ip):
        assert _is_private_ip(ip) is False


# ──────────────────────────────────────────────
# 2. get_client_ip — IP 提取优先级
# ──────────────────────────────────────────────

class TestGetClientIp:
    def test_x_forwarded_for_takes_precedence(self):
        req = _make_request(headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"})
        assert get_client_ip(req) == "203.0.113.1"

    def test_x_real_ip_second(self):
        req = _make_request(headers={"X-Real-IP": "203.0.113.2"})
        assert get_client_ip(req) == "203.0.113.2"

    def test_client_host_fallback(self):
        req = _make_request(client_host="203.0.113.3")
        assert get_client_ip(req) == "203.0.113.3"

    def test_no_client_returns_loopback(self):
        req = _make_request()
        req.client = None
        assert get_client_ip(req) == "127.0.0.1"


# ──────────────────────────────────────────────
# 3. _country_from_ip_api — 核心 mock 测试
# ──────────────────────────────────────────────

def _mock_urlopen(country_code: str, status: int = 200):
    """构造 urlopen 的 context manager mock，返回给定国家码。"""
    body = json.dumps({"countryCode": country_code}).encode()
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestCountryFromIpApi:
    def test_private_ip_returns_none(self):
        assert _country_from_ip_api("127.0.0.1") is None
        assert _country_from_ip_api("192.168.0.1") is None

    def test_success_returns_country_code(self):
        resp = _mock_urlopen("CN")
        with patch("urllib.request.urlopen", return_value=resp):
            result = _country_from_ip_api("114.114.114.114")
        assert result == "CN"

    def test_success_intl(self):
        resp = _mock_urlopen("JP")
        with patch("urllib.request.urlopen", return_value=resp):
            result = _country_from_ip_api("203.0.113.1")
        assert result == "JP"

    def test_non_200_status_returns_none(self):
        resp = _mock_urlopen("CN", status=429)
        with patch("urllib.request.urlopen", return_value=resp):
            result = _country_from_ip_api("114.114.114.114")
        assert result is None

    def test_empty_country_code_returns_none(self):
        body = json.dumps({"countryCode": ""}).encode()
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = body
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            result = _country_from_ip_api("114.114.114.114")
        assert result is None

    def test_network_timeout_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=OSError("timed out")):
            result = _country_from_ip_api("114.114.114.114")
        assert result is None

    def test_url_error_returns_none(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("connection refused")):
            result = _country_from_ip_api("114.114.114.114")
        assert result is None

    def test_invalid_json_returns_none(self):
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b"not-json"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=resp):
            result = _country_from_ip_api("114.114.114.114")
        assert result is None

    def test_correct_url_called(self):
        """验证调用的 URL 格式符合 ip-api.com 规范。"""
        resp = _mock_urlopen("US")
        with patch("urllib.request.urlopen", return_value=resp), \
             patch("urllib.request.Request") as mock_req_cls:
            mock_req_cls.return_value = MagicMock()
            _country_from_ip_api("8.8.8.8")
        args, _ = mock_req_cls.call_args
        assert "ip-api.com" in args[0]
        assert "8.8.8.8" in args[0]


# ──────────────────────────────────────────────
# 4. get_country — 优先级链
# ──────────────────────────────────────────────

class TestGetCountry:
    def test_cdn_header_takes_highest_priority(self):
        req = _make_request(headers={"CF-IPCountry": "JP"}, client_host="8.8.8.8")
        # 即使 ip-api 可调用，也不应被调用
        with patch("tatha.api.region._country_from_ip_api") as mock_api:
            result = get_country(req)
        assert result == "JP"
        mock_api.assert_not_called()

    def test_env_var_overrides_ip_api(self, monkeypatch):
        monkeypatch.setenv("TATHA_DEFAULT_REGION", "DE")
        req = _make_request(client_host="8.8.8.8")
        with patch("tatha.api.region._country_from_ip_api") as mock_api:
            result = get_country(req)
        assert result == "DE"
        mock_api.assert_not_called()

    def test_ip_api_called_when_no_cdn_and_no_env(self, monkeypatch):
        monkeypatch.delenv("TATHA_DEFAULT_REGION", raising=False)
        req = _make_request(client_host="114.114.114.114")
        resp = _mock_urlopen("CN")
        with patch("urllib.request.urlopen", return_value=resp):
            result = get_country(req)
        assert result == "CN"

    def test_fallback_to_us_when_all_fail(self, monkeypatch):
        monkeypatch.delenv("TATHA_DEFAULT_REGION", raising=False)
        req = _make_request(client_host="8.8.8.8")
        with patch("tatha.api.region._country_from_ip_api", return_value=None):
            result = get_country(req)
        assert result == "US"

    def test_fallback_to_env_when_ip_api_fails(self, monkeypatch):
        monkeypatch.setenv("TATHA_DEFAULT_REGION", "KR")
        req = _make_request(client_host="8.8.8.8")
        with patch("tatha.api.region._country_from_ip_api", return_value=None):
            result = get_country(req)
        assert result == "KR"

    def test_private_ip_skips_ip_api(self, monkeypatch):
        monkeypatch.delenv("TATHA_DEFAULT_REGION", raising=False)
        req = _make_request(client_host="127.0.0.1")
        with patch("tatha.api.region._country_from_ip_api") as mock_api:
            mock_api.return_value = None  # 私有 IP 内部会直接返回 None
            result = get_country(req)
        # 私有 IP 无法解析，最终 fallback 到 US
        assert result in ("US", "")


# ──────────────────────────────────────────────
# 5. GET /v1/region — HTTP 层 ip-api mock
# ──────────────────────────────────────────────

class TestRegionEndpointWithIpApi:
    def test_region_auto_detects_cn_via_ip_api(self, monkeypatch):
        """TestClient 请求来自 127.0.0.1（私有），注入 X-Forwarded-For 让 ip-api 被调用并返回 CN。"""
        monkeypatch.delenv("TATHA_DEFAULT_REGION", raising=False)
        resp = _mock_urlopen("CN")
        with patch("urllib.request.urlopen", return_value=resp):
            r = client.get(
                "/v1/region",
                headers={"X-Forwarded-For": "114.114.114.114"},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["country"] == "CN"
        assert data["currency"] == "CNY"

    def test_region_auto_detects_us_via_ip_api(self, monkeypatch):
        monkeypatch.delenv("TATHA_DEFAULT_REGION", raising=False)
        resp = _mock_urlopen("US")
        with patch("urllib.request.urlopen", return_value=resp):
            r = client.get(
                "/v1/region",
                headers={"X-Forwarded-For": "8.8.8.8"},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["country"] == "US"
        assert data["currency"] == "USD"

    def test_region_cdn_header_bypasses_ip_api(self, monkeypatch):
        """CDN 头直接决定国家，不应触发 ip-api 调用。"""
        monkeypatch.delenv("TATHA_DEFAULT_REGION", raising=False)
        with patch("tatha.api.region._country_from_ip_api") as mock_api:
            r = client.get(
                "/v1/region",
                headers={"CF-IPCountry": "SG"},
            )
        assert r.status_code == 200
        assert r.json()["country"] == "SG"
        mock_api.assert_not_called()

    def test_region_ip_api_timeout_graceful(self, monkeypatch):
        """ip-api 超时时优雅降级，返回默认地区（不崩溃）。"""
        monkeypatch.delenv("TATHA_DEFAULT_REGION", raising=False)
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            r = client.get(
                "/v1/region",
                headers={"X-Forwarded-For": "8.8.8.8"},
            )
        assert r.status_code == 200
        # 超时后回退到 US
        assert r.json()["country"] == "US"

    def test_region_env_var_override(self, monkeypatch):
        """TATHA_DEFAULT_REGION=CN 时不调用 ip-api，直接返回 CN。"""
        monkeypatch.setenv("TATHA_DEFAULT_REGION", "CN")
        with patch("tatha.api.region._country_from_ip_api") as mock_api:
            r = client.get("/v1/region")
        assert r.status_code == 200
        assert r.json()["country"] == "CN"
        mock_api.assert_not_called()
