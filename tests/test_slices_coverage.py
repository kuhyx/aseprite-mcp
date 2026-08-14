"""Coverage gaps in slices.py.

Not hit by test_slices.py / test_slices_pipe.py: validation guards and
operations on a nonexistent slice.

Uses the module-scoped `sprite` fixture read-only-ish (creates its own named
slices distinct from "button"/"weird|name,x"/"ninepatch" used elsewhere) so
it does not depend on execution order against those other files.
"""

from pathlib import Path

from conftest import BASE, ok, run

from aseprite_mcp.tools import slices

CORRUPT = f"{BASE}/slices_corrupt.aseprite"


def _make_corrupt() -> str:
    Path(BASE).mkdir(parents=True, exist_ok=True)
    if not Path(CORRUPT).exists():
        with Path(CORRUPT).open("w") as f:
            f.write("this is not a real aseprite file")
    return CORRUPT


# --- create_slice ---


def test_create_slice_missing_file() -> None:
    result = run(slices.create_slice("/tmp/ase-pytest/nope.aseprite", "s", 0, 0, 4, 4))
    assert "not found" in result


def test_create_slice_bad_dims(sprite: str) -> None:
    result = run(slices.create_slice(sprite, "cov_slice_bad", 0, 0, 0, 4))
    assert "must be > 0" in result


def test_create_slice_empty_name(sprite: str) -> None:
    result = run(slices.create_slice(sprite, "", 0, 0, 4, 4))
    assert "cannot be empty" in result


# --- set_slice_center ---


def test_set_slice_center_missing_file() -> None:
    result = run(
        slices.set_slice_center("/tmp/ase-pytest/nope.aseprite", "s", 0, 0, 4, 4)
    )
    assert "not found" in result


def test_set_slice_center_bad_dims(sprite: str) -> None:
    ok(run(slices.create_slice(sprite, "cov_center_slice", 0, 0, 8, 8)))
    result = run(slices.set_slice_center(sprite, "cov_center_slice", 0, 0, 4, 0))
    assert "must be > 0" in result


def test_set_slice_center_nonexistent_slice(sprite: str) -> None:
    result = run(slices.set_slice_center(sprite, "NO_SUCH_SLICE", 0, 0, 4, 4))
    assert str(result).startswith(("Failed", "ERROR"))


# --- set_slice_pivot ---


def test_set_slice_pivot_missing_file() -> None:
    result = run(slices.set_slice_pivot("/tmp/ase-pytest/nope.aseprite", "s", 0, 0))
    assert "not found" in result


def test_set_slice_pivot_nonexistent_slice(sprite: str) -> None:
    result = run(slices.set_slice_pivot(sprite, "NO_SUCH_SLICE", 0, 0))
    assert str(result).startswith(("Failed", "ERROR"))


# --- list_slices ---


def test_list_slices_missing_file() -> None:
    result = run(slices.list_slices("/tmp/ase-pytest/nope.aseprite"))
    assert "not found" in result


def test_list_slices_corrupt_file() -> None:
    # A garbage file exists (passes os.path.exists) but Aseprite can't open
    # it as a sprite, so the script's own "ERROR:No active sprite" line
    # flips execute_lua_script_checked's success flag to False.
    result = run(slices.list_slices(_make_corrupt()))
    assert result == "Failed to list slices: No active sprite"


# --- delete_slice ---


def test_delete_slice_missing_file() -> None:
    result = run(slices.delete_slice("/tmp/ase-pytest/nope.aseprite", "s"))
    assert "not found" in result


def test_delete_slice_nonexistent_slice(sprite: str) -> None:
    result = run(slices.delete_slice(sprite, "NO_SUCH_SLICE"))
    assert str(result).startswith(("Failed", "ERROR"))
