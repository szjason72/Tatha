"""
V1 档位覆盖存储：支付/订阅开通后，将用户档位写入此处；鉴权时优先读取，未命中再使用量子认证返回的 tier。

支持内存存储（默认）与 Redis（配置 REDIS_URL 时）。键：tatha:tier:{user_id}，值：basic | pro。
"""
import os
from typing import Literal

TierOverride = Literal["basic", "pro"]

_MEMORY: dict[str, str] = {}


def _redis_key(user_id: str) -> str:
    return f"tatha:tier:{user_id}"


def get_tier(user_id: str) -> TierOverride | None:
    """获取本地覆盖的档位；无覆盖返回 None。"""
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url)
            val = r.get(_redis_key(user_id))
            if val and isinstance(val, bytes):
                val = val.decode()
            if val in ("basic", "pro"):
                return val
            return None
        except Exception:
            pass
    return _MEMORY.get(user_id)


def set_tier(user_id: str, tier: TierOverride) -> None:
    """写入档位覆盖（支付成功回调时调用）。"""
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url)
            r.set(_redis_key(user_id), tier)
            return
        except Exception:
            pass
    _MEMORY[user_id] = tier
