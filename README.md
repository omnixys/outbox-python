# omnixys-outbox

Transactional outbox for Omnixys services: reliably persist domain events in
the same transaction as your aggregates, then publish them to Kafka
(transactionally-safe, exactly-once-at-least-once) without losing events when
the broker or process fails.

## Installation

```bash
pip install omnixys-outbox
```

## Features

- **OutboxMessageModel** — SQLAlchemy ORM model (`outbox_messages` table) with
  `JSONB` payload, status/retry columns, and indexes for claiming and tracing.
- **OutboxRepository** — `add_event()`, `claim_batch()` (skips locked rows,
  marks claimed rows `processing`), `mark_processed()`, `mark_failed()`,
  `count_pending()`.
- **OutboxProcessor** — claims a batch, publishes each message through an
  `OutboxPublisher`, and marks it processed or failed accordingly.
- **OutboxPublisher** — a `Protocol` (`publish_raw`) so any Kafka/HTTP publisher
  can be plugged in.
- **Dishka wiring** — `OutboxProvider` provides a request-scoped repository and
  processor.

## Quick start

Persist the event inside your business transaction:

```python
from outbox import OutboxRepository

async def create_account(session, repository: OutboxRepository, account, request_id) -> None:
    await repository.add_event(
        aggregate_type="account",
        aggregate_id=account.id,
        event_type="account.created",
        topic="omnixys.account.events",
        payload={"id": str(account.id), "email": account.email},
        correlation_id=request_id,
    )
    await session.commit()  # event and aggregate are committed atomically
```

Publish pending events with a background worker:

```python
from outbox import OutboxProcessor

async def worker_loop(processor: OutboxProcessor) -> None:
    while True:
        processed = await processor.process_batch(limit=100, max_retries=5)
        await asyncio.sleep(0.1 if processed else 1)
```

`process_batch` claims up to `limit` messages with
`retry_count < max_retries`, publishes each, and returns how many were
processed successfully.

## Publish protocol

Any object with an `async publish_raw` method can act as the publisher:

```python
from outbox import OutboxPublisher

class KafkaPublisher(OutboxPublisher):
    async def publish_raw(
        self,
        topic: str,
        value: bytes,
        key: str | None = None,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        ...
```

The processor publishes `json.dumps(payload, default=str).encode("utf-8")`
with `key=str(aggregate_id)` and headers `x-event-type` (and
`x-correlation-id` when present). Failed publishes do not raise: the message is
marked `failed` and its `retry_count` incremented so the next claim can retry
it.

## Repository

```python
from outbox import OutboxRepository

# claim a batch for processing (SELECT ... FOR UPDATE SKIP LOCKED)
messages = await repository.claim_batch(limit=100, max_retries=5)

# update after the processor publishes
await repository.mark_processed(message.id)
# or
await repository.mark_failed(message.id, "Publishing failed")

pending = await repository.count_pending()
```

`claim_batch` only selects rows with status `pending`/`failed` and
`retry_count < max_retries`, ordered by `created_at` ascending. Claimed rows
are set to `processing`; failed messages keep their error message (truncated to
4000 chars) and a bumped `retry_count`.

## Statuses

`OutboxMessageStatus` is a `StrEnum`:

| Value | Meaning |
| --- | --- |
| `pending` | persisted, not yet claimed |
| `processing` | claimed, being published |
| `processed` | published successfully |
| `failed` | publish failed, eligible for retry |

## Dependency injection

```python
from dishka import Provider, Scope, make_async_container
from outbox import OutboxProcessor, OutboxPublisher, OutboxRepository
from outbox.container import OutboxProvider

class OuterProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def session(self) -> AsyncSession:
        ...

    @provide(scope=Scope.REQUEST)
    def publisher(self) -> OutboxPublisher:
        return KafkaPublisher(...)

container = make_async_container(OutboxProvider(), OuterProvider(...))

async with container(scope=Scope.REQUEST) as request:
    repository = await request.get(OutboxRepository)
    processor = await request.get(OutboxProcessor)
```

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy src/
```

## License

GPL-3.0-or-later
