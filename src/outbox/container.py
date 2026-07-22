from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from outbox.processor import OutboxProcessor, OutboxPublisher
from outbox.repository import OutboxRepository


class OutboxProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def repository(self, session: AsyncSession) -> OutboxRepository:
        return OutboxRepository(session=session)

    @provide
    def processor(self, repository: OutboxRepository, publisher: OutboxPublisher) -> OutboxProcessor:
        return OutboxProcessor(repository=repository, publisher=publisher)
