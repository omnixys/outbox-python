"""Behaviour tests for the outbox domain model."""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

from outbox import OutboxMessage, OutboxMessageStatus


def test_status_values() -> None:
    assert OutboxMessageStatus.PENDING == "pending"
    assert OutboxMessageStatus.PROCESSING == "processing"
    assert OutboxMessageStatus.PROCESSED == "processed"
    assert OutboxMessageStatus.FAILED == "failed"


def test_message_defaults() -> None:
    msg = OutboxMessage()

    assert isinstance(msg.id, UUID)
    assert isinstance(msg.aggregate_id, UUID)
    assert msg.aggregate_type == ""
    assert msg.event_type == ""
    assert msg.topic == ""
    assert msg.payload == {}
    assert msg.status is OutboxMessageStatus.PENDING
    assert msg.retry_count == 0
    assert msg.error_message is None
    assert msg.processed_at is None
    assert msg.correlation_id is None
    assert msg.created_at.tzinfo is UTC


def test_message_accepts_values() -> None:
    msg = OutboxMessage(
        aggregate_type="account",
        aggregate_id=UUID("00000000-0000-0000-0000-000000000001"),
        event_type="account.created",
        topic="omnixys.account.events",
        payload={"id": "abc"},
        correlation_id="corr-1",
    )

    assert msg.aggregate_type == "account"
    assert msg.event_type == "account.created"
    assert msg.topic == "omnixys.account.events"
    assert msg.payload == {"id": "abc"}
    assert msg.correlation_id == "corr-1"


def test_message_defaults_generate_unique_ids() -> None:
    assert OutboxMessage().id != OutboxMessage().id
