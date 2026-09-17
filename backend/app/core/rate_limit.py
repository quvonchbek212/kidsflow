"""Rate limiting — login va setup endpointlarini himoyalash (11-bo'lim).

Ikki backend:
- `memory` — bitta process uchun (dev/test); sodda fixed-window.
- `redis` — bir nechta instans uchun (production), INCR + EXPIRE.

Kalit odatda mijoz IP manzili + endpoint scope'idan tuziladi.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any, Protocol

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.core.exceptions import TooManyRequestsError


class RateLimiter(Protocol):
    async def allow(self, key: str, max_hits: int, window_seconds: int) -> bool:
        """Urinishga ruxsat bo'lsa True, limit oshsa False qaytaradi."""
        ...


class InMemoryRateLimiter:
    """Process-lokal fixed-window limiter (dev/test)."""

    # Shuncha chaqiruvdan keyin bo'shab qolgan kalitlar tozalanadi — aks holda
    # har bir yangi IP lug'atda abadiy qolib, xotira sekin o'sardi.
    _SWEEP_EVERY = 1000

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}
        self._calls = 0

    def reset(self) -> None:
        self._hits.clear()
        self._calls = 0

    def _sweep(self, now: float, window_seconds: int) -> None:
        self._hits = {
            key: kept
            for key, stamps in self._hits.items()
            if (kept := [t for t in stamps if now - t < window_seconds])
        }

    async def allow(self, key: str, max_hits: int, window_seconds: int) -> bool:
        now = time.monotonic()
        self._calls += 1
        if self._calls % self._SWEEP_EVERY == 0:
            self._sweep(now, window_seconds)
        bucket = [t for t in self._hits.get(key, []) if now - t < window_seconds]
        if len(bucket) >= max_hits:
            self._hits[key] = bucket
            return False
        bucket.append(now)
        self._hits[key] = bucket
        return True


class RedisRateLimiter:
    """Redis INCR + EXPIRE asosidagi fixed-window limiter (production)."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Any | None = None

    async def _get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as redis_asyncio

            self._client = redis_asyncio.from_url(self._url)
        return self._client

    async def allow(self, key: str, max_hits: int, window_seconds: int) -> bool:
        client = await self._get_client()
        redis_key = f"ratelimit:{key}"
        # INCR va EXPIRE bitta tranzaksiyada. Ilgari ular alohida edi: jarayon
        # orasida uzilsa kalit muddatsiz qolib, IP butunlay bloklanardi.
        # `nx=True` — mavjud muddat har urinishda uzaytirilmaydi (fixed window).
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds, nx=True)
            count, _ = await pipe.execute()
        return int(count) <= max_hits


@lru_cache
def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    if settings.rate_limit_backend == "redis":
        return RedisRateLimiter(str(settings.redis_url))
    return InMemoryRateLimiter()


def _client_key(request: Request, scope: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{scope}:{host}"


async def _enforce(
    request: Request, scope: str, max_hits: int, window_seconds: int
) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    limiter = get_rate_limiter()
    allowed = await limiter.allow(_client_key(request, scope), max_hits, window_seconds)
    if not allowed:
        raise TooManyRequestsError()


def rate_limit_dependency(
    scope: str,
    max_getter: Callable[[Settings], int],
    window_getter: Callable[[Settings], int],
) -> Callable[..., Awaitable[None]]:
    """Berilgan scope uchun rate-limit dependency yaratadi."""

    async def _dependency(
        request: Request, settings: Settings = Depends(get_settings)
    ) -> None:
        await _enforce(request, scope, max_getter(settings), window_getter(settings))

    return _dependency


login_rate_limit = rate_limit_dependency(
    "login",
    lambda s: s.login_rate_limit_max,
    lambda s: s.login_rate_limit_window_seconds,
)

refresh_rate_limit = rate_limit_dependency(
    "refresh",
    lambda s: s.refresh_rate_limit_max,
    lambda s: s.refresh_rate_limit_window_seconds,
)

setup_rate_limit = rate_limit_dependency(
    "setup",
    lambda s: s.setup_rate_limit_max,
    lambda s: s.setup_rate_limit_window_seconds,
)
