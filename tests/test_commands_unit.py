"""Unit tests for the AsepriteCommand subprocess boundary (core/commands.py).

Unlike the rest of tests/, these mock subprocess.run instead of shelling
out to a real Aseprite binary. That's the only way to drive the
CalledProcessError / non-zero-exit paths: a real, working Aseprite install
can't be forced to fail on demand. Everything else in this repo stays
integration-style against the real binary (see tests/conftest.py); this
file is deliberately the one exception, scoped to the subprocess seam.
"""

import contextlib
import subprocess as sp
from pathlib import Path
from unittest.mock import patch

import pytest

from aseprite_mcp.core.colors import parse_hex_color
from aseprite_mcp.core.commands import AsepriteCommand, lua_escape, reject_traversal


def test_lua_escape_backslash_and_quote() -> None:
    assert lua_escape('a\\b"c') == 'a\\\\b\\"c'


def test_lua_escape_newline_cr_nul() -> None:
    assert lua_escape("a\nb\rc\0d") == "a\\nb\\rc\\0d"


def test_lua_escape_plain_string_unchanged() -> None:
    assert lua_escape("plain") == "plain"


def test_reject_traversal_flags_dotdot_component() -> None:
    assert reject_traversal("../etc/passwd") == (
        "Invalid filename: parent directory traversal not allowed"
    )


def test_reject_traversal_flags_dotdot_that_would_normalize_away() -> None:
    # The check runs on the RAW components, so a mid-path ".." is rejected
    # even though os.path.normpath would collapse it to "bar.aseprite".
    # Normalizing first made the guard depend on whether the traversal
    # happened to cancel out, which is not a security property.
    assert reject_traversal("foo/../bar.aseprite") == (
        "Invalid filename: parent directory traversal not allowed"
    )


def test_reject_traversal_allows_dotdot_inside_a_filename() -> None:
    # Only a whole ".." path COMPONENT is traversal. A filename that merely
    # contains ".." is legitimate and must still pass -- this is why the
    # check splits on separators instead of doing a substring search.
    assert reject_traversal("foo..bar.aseprite") is None
    assert reject_traversal("dir/foo..bar.aseprite") is None
    assert reject_traversal("..leading.aseprite") is None
    assert reject_traversal("trailing...aseprite") is None


def test_reject_traversal_flags_dotdot_that_survives_normalization() -> None:
    assert reject_traversal("foo/../../bar.aseprite") == (
        "Invalid filename: parent directory traversal not allowed"
    )


def test_reject_traversal_allows_dotdot_substring_in_filename() -> None:
    # `foo..bar.aseprite` has no real ".." *component*, must not false-positive.
    assert reject_traversal("foo..bar.aseprite") is None


def test_reject_traversal_allows_normal_path() -> None:
    assert reject_traversal("/tmp/ase-pytest/sprite.aseprite") is None


def test_run_command_success() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "ok output"
        success, output = AsepriteCommand.run_command(["--version"])
    assert success is True
    assert output == "ok output"


def test_run_command_uses_aseprite_path_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASEPRITE_PATH", "/custom/aseprite")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        AsepriteCommand.run_command(["--batch"])
    called_cmd = mock_run.call_args[0][0]
    assert called_cmd[0] == "/custom/aseprite"


def test_run_command_defaults_to_bare_aseprite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASEPRITE_PATH", raising=False)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        AsepriteCommand.run_command(["--batch"])
    called_cmd = mock_run.call_args[0][0]
    assert called_cmd[0] == "aseprite"


def test_run_command_failure_returns_stderr() -> None:

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = sp.CalledProcessError(
            1, ["aseprite"], stderr="boom: something broke"
        )
        success, output = AsepriteCommand.run_command(["--batch"])
    assert success is False
    assert output == "boom: something broke"


def test_execute_lua_script_without_filename() -> None:
    with patch.object(AsepriteCommand, "run_command") as mock_run:
        mock_run.return_value = (True, "printed")
        success, output = AsepriteCommand.execute_lua_script("print('hi')")
    assert success is True
    assert output == "printed"
    args = mock_run.call_args[0][0]
    assert args[0] == "--batch"
    assert "--script" in args


def test_execute_lua_script_with_existing_filename(tmp_path: Path) -> None:
    sprite_path = tmp_path / "x.aseprite"
    sprite_path.write_bytes(b"")
    with patch.object(AsepriteCommand, "run_command") as mock_run:
        mock_run.return_value = (True, "")
        AsepriteCommand.execute_lua_script("print('hi')", filename=str(sprite_path))
    args = mock_run.call_args[0][0]
    assert str(sprite_path) in args


def test_execute_lua_script_with_nonexistent_filename_omits_it(
    tmp_path: Path,
) -> None:
    missing = str(tmp_path / "does-not-exist.aseprite")
    with patch.object(AsepriteCommand, "run_command") as mock_run:
        mock_run.return_value = (True, "")
        AsepriteCommand.execute_lua_script("print('hi')", filename=missing)
    args = mock_run.call_args[0][0]
    assert missing not in args


def test_execute_lua_script_cleans_up_temp_file_on_success() -> None:
    captured_path = {}

    def fake_run_command(args: list[str]) -> tuple[bool, str]:
        script_path = args[-1]
        captured_path["path"] = script_path
        assert Path(script_path).exists()
        return True, "ok"

    with patch.object(AsepriteCommand, "run_command", side_effect=fake_run_command):
        AsepriteCommand.execute_lua_script("print('hi')")
    assert not Path(captured_path["path"]).exists()


def test_execute_lua_script_cleans_up_temp_file_on_exception() -> None:

    captured_path = {}

    def raising_run_command(args: list[str]) -> tuple[bool, str]:
        captured_path["path"] = args[-1]
        msg = "simulated failure"
        raise RuntimeError(msg)

    with (
        patch.object(AsepriteCommand, "run_command", side_effect=raising_run_command),
        contextlib.suppress(RuntimeError),
    ):
        AsepriteCommand.execute_lua_script("print('hi')")
    assert not Path(captured_path["path"]).exists()


def test_execute_lua_script_checked_propagates_subprocess_failure() -> None:
    with patch.object(AsepriteCommand, "execute_lua_script") as mock_exec:
        mock_exec.return_value = (False, "subprocess died")
        success, output = AsepriteCommand.execute_lua_script_checked("print('hi')")
    assert success is False
    assert output == "subprocess died"


def test_execute_lua_script_checked_detects_error_line() -> None:
    with patch.object(AsepriteCommand, "execute_lua_script") as mock_exec:
        mock_exec.return_value = (True, "some output\nERROR:Layer not found\nmore")
        success, output = AsepriteCommand.execute_lua_script_checked("print('hi')")
    assert success is False
    assert output == "Layer not found"


def test_execute_lua_script_checked_returns_raw_output_when_no_error_line() -> None:
    with patch.object(AsepriteCommand, "execute_lua_script") as mock_exec:
        mock_exec.return_value = (True, "line one\nline two\nOK")
        success, output = AsepriteCommand.execute_lua_script_checked("print('hi')")
    assert success is True
    assert output == "line one\nline two\nOK"


# --- core/colors.py: parse_hex_color -----------------------------------


def test_parse_hex_color_rrggbb() -> None:
    assert parse_hex_color("#FF0000") == (255, 0, 0, 255)


def test_parse_hex_color_rrggbbaa() -> None:
    assert parse_hex_color("#FF000080") == (255, 0, 0, 0x80)


def test_parse_hex_color_short_rgb() -> None:
    assert parse_hex_color("#0F0") == (0, 255, 0, 255)


def test_parse_hex_color_short_rgba() -> None:
    assert parse_hex_color("#0F08") == (0, 255, 0, 0x88)


def test_parse_hex_color_without_hash() -> None:
    assert parse_hex_color("00FF00") == (0, 255, 0, 255)


def test_parse_hex_color_strips_whitespace() -> None:
    assert parse_hex_color("  #00FF00  ") == (0, 255, 0, 255)


def test_parse_hex_color_empty_string_is_none() -> None:
    assert parse_hex_color("") is None


def test_parse_hex_color_wrong_length_is_none() -> None:
    # 5 hex chars doesn't match any of the accepted lengths (3, 4, 6, 8).
    assert parse_hex_color("#FF000") is None


def test_parse_hex_color_non_hex_chars_is_none() -> None:
    assert parse_hex_color("#GGGGGG") is None
