"""
V1 配额：按 user_id + tier + 日 计数，与《认证订阅与档位设计》一致。

存储：未配置 REDIS_URL 时用进程内内存（单机）；配置后可用 Redis 键 quota:{user_id}:{resource}:{date}。
"""
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Literal

from .auth import Tier

# 资源名，与 API 对应
RESOURCE_JOB_MATCH = "job_match"
RESOURCE_ASK = "ask"
RESOURCE_RESUME_PARSE = "resume_parse"
RESOURCE_RAG = "rag"

# 各档位每日上限（与认证订阅与档位设计一致）；pro 用大数表示「高/不限」
QUOTA_LIMITS: dict[Tier, dict[str, int]] = {
    "free": {
        RESOURCE_JOB_MATCH: 3,
        RESOURCE_ASK: 1,
        RESOURCE_RESUME_PARSE: 1,
        RESOURCE_RAG: 0,
    },
    "basic": {
        RESOURCE_JOB_MATCH: 20,
        RESOURCE_ASK: 15,
        RESOURCE_RESUME_PARSE: 5,
        RESOURCE_RAG: 10,
    },
    "pro": {
        RESOURCE_JOB_MATCH: 9999,
        RESOURCE_ASK: 9999,
        RESOURCE_RESUME_PARSE: 9999,
        RESOURCE_RAG: 9999,
    },
}

# 各档位 job_match 单次 top_n 上限
TOP_N_LIMIT: dict[Tier, int] = {
    "free": 3,
    "basic": 5,
    "pro": 20,
}


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# 进程内计数：key -> count
_memory: dict[str, int] = {}
_lock = Lock()


def _storage_key(user_id: str, resource: str) -> str:
    return f"quota:{user_id}:{resource}:{_today_key()}"


def get_remaining(user_id: str, tier: Tier, resource: str) -> int:
    """当前剩余配额（今日已用数量与上限的差）。"""
    limit = QUOTA_LIMITS.get(tier, QUOTA_LIMITS["free"]).get(resource, 0)
    key = _storage_key(user_id, resource)
    with _lock:
        used = _memory.get(key, 0)
    return max(0, limit - used)


def consume(user_id: str, tier: Tier, resource: str) -> bool:
    """
    扣减 1 次配额；若已超限则不扣减并返回 False。
    返回 True 表示扣减成功，可继续执行业务。
    """
    limit = QUOTA_LIMITS.get(tier, QUOTA_LIMITS["free"]).get(resource, 0)
    key = _storage_key(user_id, resource)
    with _lock:
        used = _memory.get(key, 0)
        if used >= limit:
            return False
        _memory[key] = used + 1
    return True


def clamp_top_n(tier: Tier, requested: int) -> int:
    """按档位限制 top_n，返回允许的最大值。"""
    max_n = TOP_N_LIMIT.get(tier, TOP_N_LIMIT["free"])
    return min(max(requested, 1), max_n)
