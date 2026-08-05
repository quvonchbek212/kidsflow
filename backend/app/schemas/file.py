"""Fayl sxemalari."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class FileResponse(BaseModel):
    id: uuid.UUID
    original_name: str
    content_type: str
    size_bytes: int
    scan_status: str
    created_at: datetime
