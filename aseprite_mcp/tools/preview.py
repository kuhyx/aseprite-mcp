import asyncio
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.paths import path_exists, path_is_dir


def _pid_path(port: int) -> str:
    return str(Path(tempfile.gettempdir()) / f"aseprite_mcp_preview_{port}.pid")


def _pid_is_running(pid: int) -> bool:
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                check=False,
                capture_output=True,
                text=True,
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _read_pid_file(pid_file: str) -> int:
    with Path(pid_file).open(encoding="utf-8") as f:
        return int(f.read().strip())


def _write_pid_file(pid_file: str, pid: int) -> None:
    with Path(pid_file).open("w", encoding="utf-8") as f:
        f.write(str(pid))


def _spawn_server(args: list[str], directory: str) -> subprocess.Popen[bytes]:
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP/DETACHED_PROCESS only exist in the
        # subprocess module on Windows; getattr keeps this typecheckable
        # on Linux/macOS where the module lacks those attributes entirely.
        create_new_process_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        detached_process = getattr(subprocess, "DETACHED_PROCESS", 0)
        return subprocess.Popen(
            args,
            cwd=directory,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=create_new_process_group | detached_process,
        )
    return subprocess.Popen(
        args,
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _kill_process(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
    else:
        os.kill(pid, signal.SIGTERM)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def start_preview_server(
    directory: Annotated[str, Field(description="Directory to serve")],
    port: Annotated[int, Field(description="Port to bind (default 8000)")] = 8000,
) -> str:
    """Start a simple HTTP server to preview exported sprites.

    Spawns a new background process bound to the given port; use
    stop_preview_server to shut it down when finished.
    """
    if not await path_is_dir(directory):
        return f"Directory {directory} not found"

    pid_file = _pid_path(port)
    if await path_exists(pid_file):
        try:
            pid = await asyncio.to_thread(_read_pid_file, pid_file)
            if await asyncio.to_thread(_pid_is_running, pid):
                return f"Preview server may already be running on port {port}"
        except (OSError, ValueError):
            pass
        await asyncio.to_thread(Path(pid_file).unlink)

    args = [sys.executable, "-m", "http.server", str(port), "--directory", directory]
    proc = await asyncio.to_thread(_spawn_server, args, directory)
    await asyncio.to_thread(_write_pid_file, pid_file, proc.pid)

    return f"Preview server started: http://localhost:{port}/"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def stop_preview_server(
    port: Annotated[int, Field(description="Port to stop (default 8000)")] = 8000,
) -> str:
    """Stop the preview HTTP server for a given port.

    Kills the background process started by start_preview_server. Calling
    this again after the server is already stopped is a no-op.
    """
    pid_file = _pid_path(port)
    if not await path_exists(pid_file):
        return f"No preview server PID found for port {port}"

    pid = await asyncio.to_thread(_read_pid_file, pid_file)

    try:
        await asyncio.to_thread(_kill_process, pid)
    finally:
        await asyncio.to_thread(Path(pid_file).unlink)

    return f"Preview server stopped on port {port}"
