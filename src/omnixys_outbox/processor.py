from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from omnixys_outbox.model import OutboxMessage
    from omnixys_outbox.repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxPublisher(Protocol):
    async def publish_raw(
        self,
        topic: str,
        value: bytes,
        key: str | None = None,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None: ...


class OutboxProcessor:
    def __init__(self, repository: OutboxRepository, publisher: OutboxPublisher) -> None:
        self._repository = repository
        self._publisher = publisher

    async def process_batch(
        self,
        *,
        limit: int = 100,
        max_retries: int = 5,
    ) -> int:
        messages = await self._repository.claim_batch(limit=limit, max_retries=max_retries)
        if not messages:
            return 0

        processed = 0
        for msg in messages:
            ok = await self._publish_message(msg)
            if ok:
                await self._repository.mark_processed(msg.id)
                processed += 1
            else:
                await self._repository.mark_failed(msg.id, "Publishing failed")

        return processed

    async def _publish_message(self, msg: OutboxMessage) -> bool:
        start = perf_counter()
        try:
            payload = json.dumps(msg.payload, default=str).encode("utf-8")
            headers: list[tuple[str, bytes]] = [
                ("x-event-type", msg.event_type.encode("utf-8")),
            ]
            if msg.correlation_id:
                headers.append(("x-correlation-id", msg.correlation_id.encode("utf-8")))
            await self._publisher.publish_raw(
                topic=msg.topic,
                value=payload,
                key=str(msg.aggregate_id),
                headers=headers,
            )
            duration = perf_counter() - start
            logger.debug("Published outbox message %s in %.3fs", msg.id, duration)
            return True
        except Exception:
            logger.exception("Failed to publish outbox message %s", msg.id)
            return False
