"""In-memory rate limiter mantiqi uchun unit testlar (11-bo'lim)."""

from __future__ import annotations

import pytest
from app.core.rate_limit import InMemoryRateLimiter

pytestmark = pytest.mark.asyncio


async def test_allows_up_to_max_then_blocks() -> None:
    limiter = InMemoryRateLimiter()

    assert await limiter.allow("key", 2, 60) is True
    assert await limiter.allow("key", 2, 60) is True
    # Uchinchi urinish limitdan oshadi.
    assert await limiter.allow("key", 2, 60) is False


async def test_keys_are_independent() -> None:
    limiter = InMemoryRateLimiter()

    assert await limiter.allow("a", 1, 60) is True
    assert await limiter.allow("a", 1, 60) is False
    # Boshqa kalit alohida hisoblanadi.
    assert await limiter.allow("b", 1, 60) is True


async def test_reset_clears_counts() -> None:
    limiter = InMemoryRateLimiter()

    await limiter.allow("key", 1, 60)
    assert await limiter.allow("key", 1, 60) is False
    limiter.reset()
    assert await limiter.allow("key", 1, 60) is True
