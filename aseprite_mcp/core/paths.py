"""Async-safe filesystem checks for tool entry points.

Every MCP tool is declared ``async def`` because the SDK requires it, but the
work underneath (a stat, a subprocess, a file read) is ordinary synchronous
I/O with no real concurrency to protect. ``asyncio.to_thread`` keeps these
checks off the event loop without inventing a fake async filesystem layer.
"""

import asyncio
from pathlib import Path


async def path_exists(path: str) -> bool:
    """Check whether `path` exists (file or directory)."""
    return await asyncio.to_thread(lambda: Path(path).exists())


async def path_is_dir(path: str) -> bool:
    """Check whether `path` exists and is a directory."""
    return await asyncio.to_thread(lambda: Path(path).is_dir())
