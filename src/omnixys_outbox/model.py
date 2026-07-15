from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class OutboxMessageStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class OutboxMessage:
    id: UUID = field(default_factory=uuid4)
    aggregate_type: str = ""
    aggregate_id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: OutboxMessageStatus = OutboxMessageStatus.PENDING
    retry_count: int = 0
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None
    correlation_id: str | None = None
