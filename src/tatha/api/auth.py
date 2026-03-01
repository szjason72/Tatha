"""
V1 认证：从请求头取 token，调量子认证校验（或 stub），将 user_id、tier 注入请求上下文。

与 docs/量子认证接口约定_V1.md 一致；未配置 QUANTUM_AUTH_URL 时使用 stub（任意 token 视为 free 档）。
"""
import os
import re
from dataclasses import dataclass
from typing import Literal

from fastapi import Header, HTTPException

Tier = Literal["free", "basic", "pro"]


@dataclass
class AuthContext:
    """请求上下文中的用户身份与档位，供业务与配额使用。"""
    user_id: str
    tier: Tier


def get_bearer_token(authorization: str | None = Header(None, alias="Authorization")) -> str | None:
    """从请求头取出 Bearer token；无头或格式不对返回 None。"""
    if not authorization or not isinstance(authorization, str):
        return None
    auth = authorization.strip()
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    return token if token else None


def _verify_token_stub(token: str) -> AuthContext:
    """Stub：任意非空 token 视为 free 档，user_id 由 token 派生。"""
    safe = re.sub(r"[^a-zA-Z0-9\-]", "", token[:32]) or "anon"
    return AuthContext(user_id=f"stub-{safe}", tier="free")


def _verify_token_remote(token: str) -> AuthContext | None:
    """调用量子认证服务校验 token；失败或非 200 返回 None。"""
    url = os.environ.get("QUANTUM_AUTH_URL", "").strip()
    if not url:
        return None
    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode())
            user_id = data.get("user_id")
            tier_raw = (data.get("tier") or "free").lower()
            tier: Tier = "free" if tier_raw not in ("basic", "pro") else tier_raw
            if not user_id:
                return None
            return AuthContext(user_id=str(user_id), tier=tier)
    except Exception:
        return None


def verify_token(token: str) -> AuthContext | None:
    """校验 token：若配置 QUANTUM_AUTH_URL 则远程校验，否则 stub。"""
    ctx = _verify_token_remote(token)
    if ctx is not None:
        return ctx
    return _verify_token_stub(token)


def _apply_tier_override(ctx: AuthContext) -> AuthContext:
    """若本地有支付开通的档位覆盖，则覆盖认证返回的 tier（阶段 7）。"""
    from .tier_store import get_tier
    override = get_tier(ctx.user_id)
    if override:
        return AuthContext(user_id=ctx.user_id, tier=override)
    return ctx


def get_auth(authorization: str | None = Header(None, alias="Authorization")) -> AuthContext:
    """
    依赖项：从请求头取 token，校验后返回 AuthContext；无 token 或校验失败抛出 401。
    档位优先使用支付/订阅开通的本地覆盖（tier_store），再使用量子认证/stub 返回的 tier。
    """
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="missing or invalid authorization")
    ctx = verify_token(token)
    if ctx is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return _apply_tier_override(ctx)
