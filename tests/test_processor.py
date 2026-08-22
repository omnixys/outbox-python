"""Behaviour tests for the outbox processor."""

from __future__ import annotations

import json
import uuid

from outbox import OutboxMessage, OutboxProcessor
from tests.helpers import FailingPublisher, FakePublisher, FakeRepository


def make_message(**overrides: object) -> OutboxMessage:
    values: dict[str, object] = {
        "aggregate_type": "account",
        "aggregate_id": uuid.uuid4(),
        "event_type": "account.created",
        "topic": "omnixys.account.events",
        "payload": {"id": "abc"},
        "correlation_id": "corr-1",
    }
    values.update(overrides)
    return OutboxMessage(**values)


async def test_process_batch_publishes_and_marks_processed() -> None:
    message = make_message()
    repository = FakeRepository([message])
    publisher = FakePublisher()
    processor = OutboxProcessor(repository, publisher)

    processed = await processor.process_batch()

    assert processed == 1
    assert len(publisher.calls) == 1
    call = publisher.calls[0]
    assert call["topic"] == "omnixys.account.events"
    assert json.loads(call["value"]) == {"id": "abc"}
    assert call["key"] == str(message.aggregate_id)
    headers = call["headers"]
    assert ("x-event-type", b"account.created") in headers
    assert ("x-correlation-id", b"corr-1") in headers
    assert repository.processed == [message.id]
    assert repository.failed == []


async def test_process_batch_omits_correlation_id_header_when_absent() -> None:
    message = make_message(correlation_id=None)
    publisher = FakePublisher()
    processor = OutboxProcessor(FakeRepository([message]), publisher)

    await processor.process_batch()

    assert publisher.calls[0]["headers"] == [("x-event-type", b"account.created")]


async def test_process_batch_returns_zero_without_messages() -> None:
    processor = OutboxProcessor(FakeRepository([]), FakePublisher())

    assert await processor.process_batch() == 0


async def test_process_batch_marks_failed_on_publish_error() -> None:
    message = make_message()
    repository = FakeRepository([message])
    processor = OutboxProcessor(repository, FailingPublisher())

    processed = await processor.process_batch()

    assert processed == 0
    assert repository.failed == [(message.id, "Publishing failed")]
    assert repository.processed == []


async def test_process_batch_continues_after_failure() -> None:
    first = make_message(event_type="first", correlation_id=None)
    second = make_message(event_type="second", correlation_id=None)
    repository = FakeRepository([first, second])
    processor = OutboxProcessor(repository, FailingPublisher())

    processed = await processor.process_batch()

    assert processed == 0
    assert repository.failed == [(first.id, "Publishing failed"), (second.id, "Publishing failed")]


async def test_publish_serializes_non_json_payload() -> None:
    message = make_message(payload={"user_id": uuid.uuid4()})
    publisher = FakePublisher()
    processor = OutboxProcessor(FakeRepository([message]), publisher)

    await processor.process_batch()

    parsed = json.loads(publisher.calls[0]["value"])
    assert parsed["user_id"] == str(message.payload["user_id"])
