from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings

logger = logging.getLogger("audio_analysis_system.rate_limit")


@dataclass
class LimitResult:
    allowed: bool
    retry_after_seconds: int


class RateLimiter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._memory: dict[str, tuple[int, float]] = {}
        self._redis: Any | None = None
        if settings.redis_url:
            try:
                from redis import Redis

                self._redis = Redis.from_url(settings.redis_url, socket_connect_timeout=0.3, socket_timeout=0.3)
                self._redis.ping()
            except Exception as exc:  # pragma: no cover - depends on local Redis availability
                logger.warning("Redis rate limiter unavailable, falling back to in-memory limiter: %s", exc)
                self._redis = None

    def check(self, key: str, limit: int, window_seconds: int) -> LimitResult:
        if limit <= 0:
            return LimitResult(allowed=True, retry_after_seconds=0)
        if self._redis is not None:
            return self._check_redis(key, limit, window_seconds)
        return self._check_memory(key, limit, window_seconds)

    def ping_redis(self) -> bool:
        if not self.settings.redis_url:
            return True
        if self._redis is None:
            return False
        try:
            return bool(self._redis.ping())
        except Exception:
            return False

    def _check_redis(self, key: str, limit: int, window_seconds: int) -> LimitResult:
        redis_client = self._redis
        if redis_client is None:
            return self._check_memory(key, limit, window_seconds)
        bucket = f"rate:{key}:{int(time.time() // window_seconds)}"
        count = int(redis_client.incr(bucket))
        if count == 1:
            redis_client.expire(bucket, window_seconds)
        if count > limit:
            ttl = redis_client.ttl(bucket)
            return LimitResult(allowed=False, retry_after_seconds=max(1, int(ttl)))
        return LimitResult(allowed=True, retry_after_seconds=0)

    def _check_memory(self, key: str, limit: int, window_seconds: int) -> LimitResult:
        now = time.monotonic()
        count, reset_at = self._memory.get(key, (0, now + window_seconds))
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds
        count += 1
        self._memory[key] = (count, reset_at)
        if count > limit:
            return LimitResult(allowed=False, retry_after_seconds=max(1, int(reset_at - now)))
        return LimitResult(allowed=True, retry_after_seconds=0)
