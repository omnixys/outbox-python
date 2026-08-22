"""Behaviour tests for the outbox ORM model."""

from __future__ import annotations

from outbox import OutboxMessageModel


def test_table_name() -> None:
    assert OutboxMessageModel.__tablename__ == "outbox_messages"


def test_table_columns() -> None:
    assert set(OutboxMessageModel.__table__.columns.keys()) == {
        "id",
        "aggregate_type",
        "aggregate_id",
        "event_type",
        "topic",
        "payload",
        "status",
        "retry_count",
        "error_message",
        "created_at",
        "processed_at",
        "correlation_id",
    }


def test_status_defaults() -> None:
    status = OutboxMessageModel.__table__.columns["status"]

    assert status.default.arg == "pending"
    assert status.server_default.arg == "pending"


def test_retry_count_defaults() -> None:
    retry_count = OutboxMessageModel.__table__.columns["retry_count"]

    assert retry_count.default.arg == 0
    assert retry_count.server_default.arg == "0"


def test_created_at_is_server_side_now() -> None:
    created_at = OutboxMessageModel.__table__.columns["created_at"]

    assert str(created_at.server_default.arg) == "now()"


def test_indexes_are_defined() -> None:
    index_columns = {
        index.name: [col.name for col in index.columns] for index in OutboxMessageModel.__table__.indexes
    }

    assert index_columns["ix_outbox_messages_status_created"] == ["status", "created_at"]
    assert index_columns["ix_outbox_messages_aggregate"] == ["aggregate_type", "aggregate_id"]
    assert index_columns["ix_outbox_messages_event_type"] == ["event_type"]
