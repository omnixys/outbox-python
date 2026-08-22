"""Behaviour tests for the dishka wiring."""

from __future__ import annotations

from dishka import Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncSession

from outbox import OutboxProcessor, OutboxPublisher, OutboxRepository
from outbox.container import OutboxProvider
from tests.helpers import FakeAsyncSession, FakePublisher


class OuterProvider(Provider):
    def __init__(self, session: AsyncSession, publisher: OutboxPublisher) -> None:
        super().__init__()
        self._session = session
        self._publisher = publisher

    @provide(scope=Scope.REQUEST)
    def session(self) -> AsyncSession:
        return self._session

    @provide(scope=Scope.REQUEST)
    def publisher(self) -> OutboxPublisher:
        return self._publisher


async def test_provider_wires_repository_and_processor() -> None:
    session = FakeAsyncSession()
    publisher = FakePublisher()

    container = make_async_container(
        OutboxProvider(),
        OuterProvider(session, publisher),
    )

    async with container(scope=Scope.REQUEST) as request_container:
        repository = await request_container.get(OutboxRepository)
        processor = await request_container.get(OutboxProcessor)

        assert isinstance(repository, OutboxRepository)
        assert isinstance(processor, OutboxProcessor)
        assert repository._session is session
        assert processor._publisher is publisher

    await container.close()
