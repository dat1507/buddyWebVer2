"""Tests for the backend package boundaries introduced by BE-002."""

from importlib import import_module
from types import ModuleType

import pytest


@pytest.mark.parametrize(
    "module_name",
    (
        "app.cli",
        "app.api",
        "app.core",
        "app.models",
        "app.schemas",
        "app.services",
    ),
)
def test_backend_package_is_importable(module_name: str) -> None:
    module = import_module(module_name)

    assert isinstance(module, ModuleType)
