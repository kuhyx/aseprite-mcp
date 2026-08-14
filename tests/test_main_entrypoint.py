"""Entrypoint (__main__.py) tests.

Patches mcp.run so no real stdio server starts, then invokes the module
under __name__ == "__main__" via runpy.
"""

import runpy
from unittest.mock import patch


def test_main_entrypoint_calls_mcp_run_stdio() -> None:
    with patch("aseprite_mcp.mcp.run") as mock_run:
        runpy.run_module("aseprite_mcp.__main__", run_name="__main__")
    mock_run.assert_called_once_with(transport="stdio")


def test_main_entrypoint_does_not_run_server_when_imported() -> None:
    with patch("aseprite_mcp.mcp.run") as mock_run:
        runpy.run_module("aseprite_mcp.__main__", run_name="not_main")
    mock_run.assert_not_called()
