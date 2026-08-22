"""Smoke test - verifies omnixys-outbox can be imported."""

from __future__ import annotations

import importlib
from importlib.metadata import version as pkg_version

import outbox
from outbox import (
    OutboxMessage,
    OutboxMessageModel,
    OutboxMessageStatus,
    OutboxProcessor,
    OutboxPublisher,
    OutboxRepository,
)


def test_package_importable() -> None:
    mod = importlib.import_module("outbox")
    assert hasattr(mod, "__version__")
    assert mod.__version__ == pkg_version("omnixys-outbox")


def test_submodules_available() -> None:
    assert outbox.model is not None
    assert outbox.orm is not None
    assert outbox.processor is not None
    assert outbox.repository is not None


def test_public_exports() -> None:
    assert OutboxMessage is not None
    assert OutboxMessageModel is not None
    assert OutboxMessageStatus is not None
    assert OutboxProcessor is not None
    assert OutboxPublisher is not None
    assert OutboxRepository is not None
