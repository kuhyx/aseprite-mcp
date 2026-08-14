"""Lua escape hatch (script.py)."""

from unittest.mock import patch

from conftest import ok, run

from aseprite_mcp.tools import script


def test_run_lua_script_returns_printed_output(sprite: str) -> None:
    out = ok(
        run(
            script.run_lua_script(
                'local spr = app.activeSprite print("size=" .. spr.width .. "x" .. spr.height)',
                sprite,
            )
        )
    )
    assert "size=32x32" in out


def test_run_lua_script_rejects_empty() -> None:
    assert run(script.run_lua_script("  ")) == "Script cannot be empty"


def test_run_lua_script_rejects_missing_filename() -> None:
    result = run(script.run_lua_script("print('hi')", "/no/such/file.aseprite"))
    assert result == "File /no/such/file.aseprite not found"


def test_run_lua_script_reports_subprocess_failure() -> None:
    with patch(
        "aseprite_mcp.tools.script.AsepriteCommand.execute_lua_script"
    ) as mock_exec:
        mock_exec.return_value = (False, "aseprite crashed")
        result = run(script.run_lua_script("print('hi')"))
    assert result == "Script failed: aseprite crashed"


def test_run_lua_script_reports_no_output_printed() -> None:
    with patch(
        "aseprite_mcp.tools.script.AsepriteCommand.execute_lua_script"
    ) as mock_exec:
        mock_exec.return_value = (True, "   ")
        result = run(script.run_lua_script("-- no print"))
    assert result == "Script executed (no output printed)"
