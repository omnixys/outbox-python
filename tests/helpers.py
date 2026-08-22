"""Shared fakes and helpers for outbox tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.dialects import postgresql

from outbox import OutboxMessage, OutboxMessageModel


def sql(stmt: object) -> str:
    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def make_model(**overrides: object) -> OutboxMessageModel:
    model = OutboxMessageModel(
        id=uuid.uuid4(),
        aggregate_type="account",
        aggregate_id=uuid.uuid4(),
        event_type="account.created",
        topic="omnixys.account.events",
        payload={"id": "abc"},
        status="pending",
        retry_count=0,
        error_message=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        processed_at=None,
        correlation_id="corr-1",
    )
    for name, value in overrides.items():
        setattr(model, name, value)
    return model


class FakeResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[object]:
        return self._rows


class FakeAsyncSession:
    def __init__(self, rows: list[object] | None = None) -> None:
        self.rows: list[object] = rows if rows is not None else []
        self.statements: list[object] = []
        self.added: list[object] = []
        self.flush_count = 0

    async def execute(self, stmt: object) -> FakeResult:
        self.statements.append(stmt)
        return FakeResult(self.rows)

    def add(self, model: object) -> None:
        self.added.append(model)

    async def flush(self) -> None:
        self.flush_count += 1


class FakeRepository:
    def __init__(self, messages: list[OutboxMessage]) -> None:
        self.messages = messages
        self.processed: list[UUID] = []
        self.failed: list[tuple[UUID, str]] = []

    async def claim_batch(self, *, limit: int = 100, max_retries: int = 5) -> list[OutboxMessage]:
        return self.messages

    async def mark_processed(self, message_id: UUID) -> None:
        self.processed.append(message_id)

    async def mark_failed(self, message_id: UUID, error_message: str) -> None:
        self.failed.append((message_id, error_message))


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def publish_raw(
        self,
        topic: str,
        value: bytes,
        key: str | None = None,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        self.calls.append({"topic": topic, "value": value, "key": key, "headers": headers})


class FailingPublisher(FakePublisher):
    async def publish_raw(
        self,
        topic: str,
        value: bytes,
        key: str | None = None,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        raise RuntimeError("broker down")
