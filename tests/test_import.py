"""Smoke test - verifies omnixys-outbox can be imported."""

from __future__ import annotations

import importlib



def test_package_importable() -> None:
    mod = importlib.import_module("omnixys_outbox")
    assert hasattr(mod, "__version__")
    assert mod.__version__ == "1.0.0"


def test_public_api() -> None:
    from omnixys_outbox import orm, processor, repository

    assert orm is not None
    assert processor is not None
    assert repository is not None
