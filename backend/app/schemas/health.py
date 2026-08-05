"""Health endpoint javob sxemalari."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """`/health` javobi — servis tiriklik holati."""

    status: Literal["ok"] = "ok"
    app: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """`/health/ready` javobi — bog'liq servislar (DB) tayyorligi."""

    status: Literal["ready", "degraded"]
    database: Literal["ok", "error"]
