"""Shared fixtures for the end-to-end tool tests.

These tests run each MCP tool against a real Aseprite (ASEPRITE_PATH),
so they are smoke/integration tests, not unit tests. Tests within a
file form a sequence on a module-scoped sprite; files are independent.

Scratch files live under a fixed /tmp path (not pytest's tmp_path) so
they resolve identically inside the Docker-wrapped Aseprite, which only
mounts /tmp and /var/folders.
"""

import asyncio
import shutil
import sys
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import aseprite_mcp.tools  # noqa: F401  (registers all tools)
from aseprite_mcp.tools import canvas, drawing

BASE = "/tmp/ase-pytest"


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    """Execute an async tool call from a sync test."""
    return asyncio.run(coro)


def ok[T](result: T) -> T:
    """Assert a tool call did not return an error message."""
    assert not str(result).startswith(
        ("Failed", "ERROR", "Invalid", "Script failed")
    ), result
    return result


@pytest.fixture(scope="session", autouse=True)
def base_dir() -> str:
    shutil.rmtree(BASE, ignore_errors=True)
    Path(BASE).mkdir(parents=True, exist_ok=True)
    return BASE


@pytest.fixture(scope="module")
def sprite(request: pytest.FixtureRequest) -> str:
    """Create a fresh 32x32 sprite per test module with a painted 'body' layer."""
    name = request.module.__name__.removeprefix("tests.").removeprefix("test_")
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(32, 32, path)))
    ok(run(canvas.add_layer(path, "body")))
    ok(
        run(
            drawing.draw_rectangle_at(
                path, "body", 1, 8, 8, 16, 16, "#D04648", fill=True
            )
        )
    )
    return path
