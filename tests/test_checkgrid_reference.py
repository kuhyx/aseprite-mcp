"""Characterization tests for skills/item-icons/references/checkgrid.py.

Written BEFORE refactoring `check` (which exceeded ruff's C901/PLR0912
limits) so the split into helpers is provably behaviour-preserving: these
pin the exact problem strings, not a paraphrase.

checkgrid.py is a frozen record of the ASCII-grid workflow that the
pixelart hook now denies, so it has no other test coverage. It is excluded
from the aseprite_mcp coverage target, so importing it here does not affect
the 100% bar.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REFS = Path(__file__).parent.parent / "skills" / "item-icons" / "references"


def _load(name: str) -> ModuleType:
    """Import a reference script by path.

    These live outside any package, so a plain `import` would need a
    sys.path insert placed above it -- which is a module-level statement
    before an import, i.e. an E402 that could only be silenced. Loading by
    spec keeps the file suppression-free. checkgrid imports gridtool by
    name, so the module is registered in sys.modules as well.
    """
    spec = importlib.util.spec_from_file_location(name, _REFS / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gridtool = _load("gridtool")
checkgrid = _load("checkgrid")

# A 16x16 grid: 'o' body centred with a 2px margin all round, no problems
# beyond the INFO lines.
_CLEAN = "\n".join(
    [
        "." * 16,
        "." * 16,
        *[("." * 2) + ("o" * 12) + ("." * 2) for _ in range(12)],
        "." * 16,
        "." * 16,
    ]
)


def _write(tmp_path: Path, grid: str) -> Path:
    path = tmp_path / "g.grid"
    path.write_text(grid, encoding="utf-8")
    return path


def test_clean_grid_reports_only_info(tmp_path: Path) -> None:
    problems = checkgrid.check(_write(tmp_path, _CLEAN))
    assert problems == [
        "INFO bbox x=2..13 y=2..13 margins L2 R2 T2 B2",
        "INFO 1 unique colours: o",
        "INFO 144 opaque pixels (56% fill)",
    ]


def test_wrong_height_and_row_widths(tmp_path: Path) -> None:
    problems = checkgrid.check(_write(tmp_path, "ooo\noo\n"))
    assert "height 2 != 16" in problems
    assert "row 0 width 3 != 16" in problems
    assert "row 1 width 2 != 16" in problems


def test_edge_touching_is_fatal(tmp_path: Path) -> None:
    grid = "\n".join(["o" * 16 for _ in range(16)])
    problems = checkgrid.check(_write(tmp_path, grid))
    fatal = [p for p in problems if p.startswith("FATAL touches canvas edge")]
    assert len(fatal) == 1
    assert "left, right, top, bottom" in fatal[0]


def test_undefined_glyph_is_fatal(tmp_path: Path) -> None:
    grid = _CLEAN.replace("oooooooooooo", "ooooo!oooooo", 1)
    problems = checkgrid.check(_write(tmp_path, grid))
    assert any(p == "FATAL undefined glyphs: !" for p in problems)


def test_silhouette_drift_is_reported(tmp_path: Path) -> None:
    # Each row's ink shifts right, so the row centres span far more than 2px.
    rows = ["." * 16]
    rows.extend(("." * (1 + i)) + "o" + ("." * (14 - i)) for i in range(14))
    rows.append("." * 16)
    problems = checkgrid.check(_write(tmp_path, "\n".join(rows)))
    assert any(p.startswith("silhouette drifts:") for p in problems)


def test_uneven_left_right_margins(tmp_path: Path) -> None:
    rows = ["." * 16, "." * 16]
    rows += [("." * 1) + ("o" * 9) + ("." * 6) for _ in range(12)]
    rows += ["." * 16, "." * 16]
    problems = checkgrid.check(_write(tmp_path, "\n".join(rows)))
    assert any(p.startswith("L/R margins uneven:") for p in problems)


def test_off_centre_bbox_is_reported(tmp_path: Path) -> None:
    rows = ["." * 16, "." * 16]
    rows += [("." * 1) + ("o" * 5) + ("." * 10) for _ in range(12)]
    rows += ["." * 16, "." * 16]
    problems = checkgrid.check(_write(tmp_path, "\n".join(rows)))
    assert any(p.startswith("bbox x-centre") for p in problems)


def test_too_many_colours(tmp_path: Path) -> None:
    palette = "ABCDEGLPRSTVW"  # 13 known glyphs, one over the 12 limit
    rows = ["." * 16, "." * 16]
    # First row carries the 13th colour so the set exceeds 12.
    rows.append(("." * 2) + palette[12] * 12 + ("." * 2))
    rows.extend(("." * 2) + (palette[i] * 12) + ("." * 2) for i in range(11))
    rows.append(("." * 2) + palette[11] * 12 + ("." * 2))
    rows += ["." * 16, "." * 16]
    problems = checkgrid.check(_write(tmp_path, "\n".join(rows)))
    assert any("> 12 (noisy)" in p for p in problems)


def test_empty_grid_skips_geometry_checks(tmp_path: Path) -> None:
    grid = "\n".join(["." * 16 for _ in range(16)])
    problems = checkgrid.check(_write(tmp_path, grid))
    assert not any(p.startswith(("INFO bbox", "FATAL touches")) for p in problems)
    assert "INFO 0 unique colours: " in problems


def test_known_glyphs_matches_gridtool() -> None:
    assert checkgrid.known_glyphs() == set(gridtool.DB32)


def test_rows_of_strips_blank_edges() -> None:
    assert checkgrid.rows_of("\n\nab\ncd\n\n") == ["ab", "cd"]


def test_main_prints_each_path(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    path = _write(tmp_path, _CLEAN)
    argv = sys.argv
    try:
        sys.argv = ["checkgrid.py", str(path)]
        checkgrid.main()
    finally:
        sys.argv = argv
    out = capsys.readouterr().out
    assert "=== g.grid ===" in out
    assert "INFO bbox x=2..13 y=2..13 margins L2 R2 T2 B2" in out
