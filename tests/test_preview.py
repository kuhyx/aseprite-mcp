"""Preview HTTP server (preview.py) tests.

No Aseprite dependency - just spawns `python -m http.server`, so these
run for real rather than mocking.
"""

import os
import socket
import time
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import run

from aseprite_mcp.tools import preview


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until(
    predicate: Callable[[], bool], timeout: float = 2.0, interval: float = 0.05
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def test_start_preview_server_missing_directory() -> None:
    result = run(preview.start_preview_server("/no/such/directory", 12345))
    assert "not found" in result


def test_start_and_stop_preview_server(tmp_path: Path) -> None:
    port = _free_port()
    directory = str(tmp_path)
    try:
        start_result = run(preview.start_preview_server(directory, port))
        assert "Preview server started" in start_result
        assert str(port) in start_result

        pid_file = preview._pid_path(port)
        assert _wait_until(lambda: Path(pid_file).exists())

        stop_result = run(preview.stop_preview_server(port))
        assert "Preview server stopped" in stop_result
        assert _wait_until(lambda: not Path(pid_file).exists())
    finally:
        # Best-effort cleanup in case an assertion failed mid-test.
        if Path(preview._pid_path(port)).exists():
            run(preview.stop_preview_server(port))


def test_start_preview_server_detects_already_running(tmp_path: Path) -> None:
    port = _free_port()
    directory = str(tmp_path)
    try:
        first = run(preview.start_preview_server(directory, port))
        assert "Preview server started" in first
        assert _wait_until(lambda: Path(preview._pid_path(port)).exists())

        second = run(preview.start_preview_server(directory, port))
        assert "may already be running" in second
    finally:
        run(preview.stop_preview_server(port))


def test_start_preview_server_recovers_stale_pid_file(tmp_path: Path) -> None:
    port = _free_port()
    directory = str(tmp_path)
    pid_file = preview._pid_path(port)
    # A PID astronomically unlikely to be a live process, simulating a
    # stale pid file left behind by a crashed/killed server.
    with Path(pid_file).open("w", encoding="utf-8") as f:
        f.write("999999")
    try:
        result = run(preview.start_preview_server(directory, port))
        assert "Preview server started" in result
    finally:
        if Path(preview._pid_path(port)).exists():
            run(preview.stop_preview_server(port))


def test_start_preview_server_recovers_corrupt_pid_file(tmp_path: Path) -> None:
    port = _free_port()
    directory = str(tmp_path)
    pid_file = preview._pid_path(port)
    with Path(pid_file).open("w", encoding="utf-8") as f:
        f.write("not-a-pid")
    try:
        result = run(preview.start_preview_server(directory, port))
        assert "Preview server started" in result
    finally:
        if Path(preview._pid_path(port)).exists():
            run(preview.stop_preview_server(port))


def test_stop_preview_server_no_pid_file() -> None:
    port = _free_port()
    result = run(preview.stop_preview_server(port))
    assert "No preview server PID found" in result


def test_pid_is_running_true_for_current_process() -> None:
    assert preview._pid_is_running(os.getpid()) is True


def test_pid_is_running_false_for_bogus_pid() -> None:
    assert preview._pid_is_running(999999) is False


# --- os.name == "nt" branches: exercised via monkeypatch, not a real ---
# --- Windows machine. subprocess.run/Popen calls are mocked so no real ---
# --- tasklist/taskkill process is invoked. ---


def test_pid_is_running_windows_branch_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preview.os, "name", "nt")
    with patch("aseprite_mcp.tools.preview.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "1234 Console"
        assert preview._pid_is_running(1234) is True
    called_args = mock_run.call_args[0][0]
    assert called_args[0] == "tasklist"


def test_pid_is_running_windows_branch_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preview.os, "name", "nt")
    with patch("aseprite_mcp.tools.preview.subprocess.run") as mock_run:
        mock_run.return_value.stdout = "INFO: No tasks running"
        assert preview._pid_is_running(1234) is False


def test_spawn_server_windows_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # os.name = "nt" makes pathlib pick WindowsPath at every later Path()
    # construction in this process, silently corrupting any real-path check
    # (confirmed directly: Path(existing_dir).is_dir() returns False, not an
    # exception). _spawn_server itself contains no pathlib, so it's tested
    # directly rather than through the full start_preview_server tool.
    monkeypatch.setattr(preview.os, "name", "nt")
    with patch("aseprite_mcp.tools.preview.subprocess.Popen") as mock_popen:
        mock_popen.return_value.pid = 4321
        preview._spawn_server(["x"], str(tmp_path))
    _, kwargs = mock_popen.call_args
    assert "creationflags" in kwargs


def test_kill_process_windows_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preview.os, "name", "nt")
    with patch("aseprite_mcp.tools.preview.subprocess.run") as mock_run:
        preview._kill_process(4321)
    called_args = mock_run.call_args[0][0]
    assert called_args[0] == "taskkill"
