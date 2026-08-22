"""Behaviour tests for the outbox repository."""

from __future__ import annotations

import uuid

from outbox import OutboxMessage, OutboxMessageModel, OutboxMessageStatus, OutboxRepository
from tests.helpers import FakeAsyncSession, make_model, sql


async def test_add_event_adds_and_flushes() -> None:
    session = FakeAsyncSession()
    repository = OutboxRepository(session)
    aggregate_id = uuid.uuid4()

    await repository.add_event(
        aggregate_type="account",
        aggregate_id=aggregate_id,
        event_type="account.created",
        topic="omnixys.account.events",
        payload={"id": "abc"},
        correlation_id="corr-1",
    )

    assert len(session.added) == 1
    model = session.added[0]
    assert isinstance(model, OutboxMessageModel)
    assert model.aggregate_type == "account"
    assert model.aggregate_id == aggregate_id
    assert model.event_type == "account.created"
    assert model.topic == "omnixys.account.events"
    assert model.payload == {"id": "abc"}
    assert model.correlation_id == "corr-1"
    assert session.flush_count == 1


async def test_claim_batch_returns_empty_without_rows() -> None:
    repository = OutboxRepository(FakeAsyncSession(rows=[]))

    assert await repository.claim_batch() == []


async def test_claim_batch_selects_claimable_rows_in_order() -> None:
    session = FakeAsyncSession(rows=[make_model()])
    repository = OutboxRepository(session)

    await repository.claim_batch(limit=50, max_retries=3)

    select_sql = sql(session.statements[0])
    assert "FROM outbox_messages" in select_sql
    assert "status IN ('pending', 'failed')" in select_sql
    assert "retry_count < 3" in select_sql
    assert "ORDER BY outbox_messages.created_at ASC" in select_sql
    assert "LIMIT 50" in select_sql
    assert "FOR UPDATE" in select_sql
    assert "SKIP LOCKED" in select_sql


async def test_claim_batch_marks_claimed_rows_processing() -> None:
    session = FakeAsyncSession(rows=[make_model()])
    repository = OutboxRepository(session)

    await repository.claim_batch()

    update_sql = sql(session.statements[1])
    assert "UPDATE outbox_messages" in update_sql
    assert "status='processing'" in update_sql


async def test_claim_batch_maps_model_to_message() -> None:
    model = make_model(
        status="failed",
        retry_count=2,
        error_message="boom",
    )
    repository = OutboxRepository(FakeAsyncSession(rows=[model]))

    messages = await repository.claim_batch()

    assert len(messages) == 1
    message = messages[0]
    assert isinstance(message, OutboxMessage)
    assert message.id == model.id
    assert message.aggregate_type == model.aggregate_type
    assert message.aggregate_id == model.aggregate_id
    assert message.event_type == model.event_type
    assert message.topic == model.topic
    assert message.payload == model.payload
    assert message.status is OutboxMessageStatus.FAILED
    assert message.retry_count == model.retry_count
    assert message.error_message == "boom"
    assert message.correlation_id == model.correlation_id
    assert message.processed_at == model.processed_at


async def test_mark_processed_updates_status_and_processed_at() -> None:
    session = FakeAsyncSession()
    repository = OutboxRepository(session)
    message_id = uuid.uuid4()

    await repository.mark_processed(message_id)

    statement_sql = sql(session.statements[0])
    assert "UPDATE outbox_messages" in statement_sql
    assert f"id = '{message_id}'" in statement_sql
    assert "status='processed'" in statement_sql
    assert "error_message=NULL" in statement_sql
    assert "processed_at" in statement_sql


async def test_mark_failed_increments_retry_and_truncates_error() -> None:
    session = FakeAsyncSession()
    repository = OutboxRepository(session)

    await repository.mark_failed(uuid.uuid4(), "x" * 5000)

    statement_sql = sql(session.statements[0])
    assert "status='failed'" in statement_sql
    assert "error_message='" + "x" * 4000 + "'" in statement_sql
    assert "retry_count=(outbox_messages.retry_count + 1)" in statement_sql
    assert "processed_at=NULL" in statement_sql


async def test_count_pending_counts_claimable_rows() -> None:
    repository = OutboxRepository(FakeAsyncSession(rows=[1, 2, 3]))

    assert await repository.count_pending() == 3
