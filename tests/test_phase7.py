"""
V1 阶段 7：托管支付开箱用 — 单测。

覆盖：tier_store、auth 档位覆盖、orders（checkout stub）、webhooks（stub-upgrade、payment 签名）。
"""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tatha.api.app import app
from tatha.api.auth import AuthContext, _apply_tier_override
from tatha.api.orders import create_checkout
from tatha.api.schemas import CheckoutRequest
from tatha.api.tier_store import get_tier, set_tier
from tatha.api.webhooks import handle_stub_upgrade

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer demo-token-phase7"}


# ----- tier_store -----


def test_tier_store_set_and_get():
    """内存存储：set_tier 后 get_tier 返回该档位。"""
    uid = "test-user-tier-store-1"
    set_tier(uid, "basic")
    assert get_tier(uid) == "basic"
    set_tier(uid, "pro")
    assert get_tier(uid) == "pro"


def test_tier_store_get_missing_returns_none():
    """未写入过的 user_id 返回 None。"""
    assert get_tier("nonexistent-user-xyz") is None


# ----- auth 档位覆盖 -----


def test_apply_tier_override_uses_store():
    """当 tier_store 有该用户覆盖时，返回覆盖的 tier。"""
    uid = "test-user-auth-override"
    set_tier(uid, "pro")
    ctx = AuthContext(user_id=uid, tier="free")
    out = _apply_tier_override(ctx)
    assert out.user_id == uid
    assert out.tier == "pro"


def test_apply_tier_override_no_store_unchanged():
    """当 tier_store 无覆盖时，返回原 ctx。"""
    ctx = AuthContext(user_id="no-override-user", tier="basic")
    out = _apply_tier_override(ctx)
    assert out.tier == "basic"


# ----- orders checkout -----


def test_checkout_requires_auth():
    """无 token 时返回 401。"""
    r = client.post(
        "/v1/orders/checkout",
        json={"tier": "basic", "interval": "month"},
    )
    assert r.status_code == 401


def test_checkout_invalid_tier_400(monkeypatch):
    """tier 非 basic/pro 返回 400。"""
    monkeypatch.setenv("LEMON_SQUEEZY_API_KEY", "")  # 确保走 stub 分支前先校验参数
    r = client.post(
        "/v1/orders/checkout",
        json={"tier": "invalid", "interval": "month"},
        headers=AUTH_HEADER,
    )
    assert r.status_code == 400
    assert "tier" in (r.json().get("detail") or "").lower()


def test_checkout_invalid_interval_400(monkeypatch):
    """interval 非 month/year 返回 400。"""
    r = client.post(
        "/v1/orders/checkout",
        json={"tier": "basic", "interval": "weekly"},
        headers=AUTH_HEADER,
    )
    assert r.status_code == 400
    assert "interval" in (r.json().get("detail") or "").lower()


def test_checkout_stub_returns_url(monkeypatch):
    """未完整配置 Lemon Squeezy 时返回 stub checkout_url（含 stub_checkout=1）。"""
    monkeypatch.setenv("LEMON_SQUEEZY_API_KEY", "")
    monkeypatch.setenv("LEMON_SQUEEZY_STORE_ID", "")
    r = client.post(
        "/v1/orders/checkout",
        json={"tier": "basic", "interval": "month"},
        headers=AUTH_HEADER,
    )
    assert r.status_code == 200
    data = r.json()
    assert "checkout_url" in data
    assert "stub_checkout=1" in data["checkout_url"]
    assert data.get("tier") == "basic"
    assert data.get("interval") == "month"


# ----- webhooks stub-upgrade -----


def test_stub_upgrade_success_when_not_configured(monkeypatch):
    """未完整配置支付时 stub-upgrade 返回 200 并写档位。"""
    monkeypatch.setenv("LEMON_SQUEEZY_API_KEY", "")
    monkeypatch.setenv("LEMON_SQUEEZY_STORE_ID", "")
    uid = "test-stub-upgrade-user"
    r = client.post(
        "/v1/webhooks/stub-upgrade",
        json={"user_id": uid, "tier": "pro"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("tier") == "pro"
    assert data.get("user_id") == uid
    assert get_tier(uid) == "pro"


def test_stub_upgrade_invalid_tier_400(monkeypatch):
    """tier 非 basic/pro 返回 400。"""
    monkeypatch.setenv("LEMON_SQUEEZY_API_KEY", "")
    r = client.post(
        "/v1/webhooks/stub-upgrade",
        json={"user_id": "u", "tier": "invalid"},
    )
    assert r.status_code == 400
    assert "tier" in (r.json().get("detail") or "").lower()


def test_stub_upgrade_404_when_fully_configured():
    """完整配置 Lemon Squeezy 时 stub-upgrade 返回 404（mock 已配置状态）。"""
    with patch("tatha.api.webhooks._is_real_checkout_configured", return_value=True):
        r = client.post(
            "/v1/webhooks/stub-upgrade",
            json={"user_id": "any", "tier": "basic"},
        )
    assert r.status_code == 404
    assert "stub" in (r.json().get("detail") or "").lower()


# ----- webhooks payment (signature) -----


def test_payment_webhook_401_without_signature():
    """无 X-Signature 时返回 401。"""
    r = client.post(
        "/v1/webhooks/payment",
        content=json.dumps({"meta": {"event_name": "order_created"}}),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 401


def test_payment_webhook_401_invalid_signature(monkeypatch):
    """错误签名返回 401。"""
    monkeypatch.setenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "test-secret")
    body = json.dumps({"meta": {"event_name": "order_created"}}).encode()
    r = client.post(
        "/v1/webhooks/payment",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": "wrong-signature-hex",
        },
    )
    assert r.status_code == 401
