from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from outbox.model import OutboxMessage, OutboxMessageStatus
from outbox.orm import OutboxMessageModel

logger = logging.getLogger(__name__)

CLAIMABLE = (OutboxMessageStatus.PENDING, OutboxMessageStatus.FAILED)


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_event(
        self,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        topic: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        model = OutboxMessageModel(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            topic=topic,
            payload=payload,
            correlation_id=correlation_id,
        )
        self._session.add(model)
        await self._session.flush()

    async def claim_batch(self, limit: int = 100, max_retries: int = 5) -> list[OutboxMessage]:
        stmt = (
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.status.in_(CLAIMABLE),
                OutboxMessageModel.retry_count < max_retries,
            )
            .order_by(OutboxMessageModel.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        if not models:
            return []

        ids = [m.id for m in models]
        await self._session.execute(
            update(OutboxMessageModel)
            .where(OutboxMessageModel.id.in_(ids))
            .values(status=OutboxMessageStatus.PROCESSING)
        )
        await self._session.flush()

        return [self._to_message(m) for m in models]

    async def mark_processed(self, message_id: UUID) -> None:
        await self._session.execute(
            update(OutboxMessageModel)
            .where(OutboxMessageModel.id == message_id)
            .values(
                status=OutboxMessageStatus.PROCESSED,
                processed_at=datetime.now(UTC),
                error_message=None,
            ),
        )

    async def mark_failed(self, message_id: UUID, error_message: str) -> None:
        await self._session.execute(
            update(OutboxMessageModel)
            .where(OutboxMessageModel.id == message_id)
            .values(
                status=OutboxMessageStatus.FAILED,
                error_message=error_message[:4000],
                retry_count=OutboxMessageModel.retry_count + 1,
                processed_at=None,
            )
            .execution_options(synchronize_session=False),
        )

    async def count_pending(self) -> int:
        stmt = select(OutboxMessageModel.id).where(OutboxMessageModel.status.in_(CLAIMABLE))
        result = await self._session.execute(stmt)
        return len(result.all())

    @staticmethod
    def _to_message(model: OutboxMessageModel) -> OutboxMessage:
        return OutboxMessage(
            id=model.id,
            aggregate_type=model.aggregate_type,
            aggregate_id=model.aggregate_id,
            event_type=model.event_type,
            topic=model.topic,
            payload=model.payload,
            status=OutboxMessageStatus(model.status),
            retry_count=model.retry_count,
            error_message=model.error_message,
            created_at=model.created_at,
            processed_at=model.processed_at,
            correlation_id=model.correlation_id,
        )
