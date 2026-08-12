# Bugs found while writing tests for 100% coverage (2026-08-12)

Found while writing/reviewing ~730 new tests across the coverage-gap pass.
None of these are fixed — documented and asserted as current behavior in
the test suite, per the coverage task's scope (write tests, don't change
behavior). Each entry names the test that captures/reproduces it.

## Fabricated success ("reports OK, does nothing")

The shared root cause: a Lua `return` inside `app.transaction(function() ... end)`
only exits the transaction closure, not the whole script — execution falls
through to `spr:saveAs(...)` + `print("OK")` regardless.

- **`canvas.set_layer(create_if_missing=False)`** on a missing layer name —
  reports `"Active layer set to 'X'"` though no layer was activated.
  `tests/test_canvas_coverage.py::test_set_layer_missing_without_create_flag`
- **`animation.copy_frame`** with an out-of-range `target_frame` — reports
  success, no-ops. `tests/test_animation_coverage.py` (noted in agent report,
  search for "fabricated-success" comments)
- **`animation.set_cel_position(create_if_missing=False)`** with no existing
  cel — same shape.
- **`animation.copy_cel`** with a missing source cel — same shape.
- **`animation.create_cel`** when a cel already exists — same shape.
- **`export.export_frame(filename, 999, ...)`** (frame index past the last
  frame) — does NOT error. `--frame-range` silently clamps/no-ops, CLI
  exits 0, tool writes a transparent/empty PNG and reports
  `"Frame 999 exported to ..."`.
  `tests/test_export_coverage.py::test_export_frame_out_of_range_frame_fabricates_success`
- **`drawing._at` tools with `create_if_missing=False`** on a layer/frame
  with no existing cel — hits `if not cel then return end` inside the Lua
  transaction, still prints `"OK"`.

## Missing bounds/growth guard on non-`_at` drawing tools

`draw_pixels_at` was fixed (commit `8281129`) to grow the cel's bounding box
so a `putPixel` outside it isn't silently discarded. The **sibling
non-`_at` tools never got the same fix**: `draw_pixels`, `draw_line`,
`draw_rectangle`, `fill_area`, `draw_circle` (all target `app.activeCel` /
`spr.layers[1]`) can silently drop pixels drawn outside the active cel's
current bounds while still reporting success. Same failure class as the bug
`8281129` fixed, just in 5 more functions.

## No radius/dimension validation on some draw tools

`draw_circle`/`draw_circle_at` never validate `radius` (no `<= 0` guard),
unlike `draw_rectangle` (checks width/height) and `draw_ellipse_at` (checks
radius_x/radius_y). `radius=0` silently produces a degenerate circle instead
of a clear error.

## `core/commands.py::reject_traversal` — normpath runs before the check

`os.path.normpath()` collapses `foo/../bar.aseprite` to `bar.aseprite`
**before** the `".." in parts` check ever runs. So a mid-path `..` that
cancels out during normalization is NOT rejected — only traversal that
survives normalization (e.g. a leading `../`) is caught. Verified directly;
`tests/test_commands_unit.py::test_reject_traversal_allows_dotdot_that_normalizes_away`
documents this. Same root cause independently found in
`scene.copy_layers_between_sprites` and `analysis.render_onion_skin`'s
output-path guard (the check runs after `os.path.exists`, and for absolute
paths pointing at an existing file the guard is effectively dead).

## `core/fonts.py` — dark-ink-rule glyph-dropping bug

`BitmapFont._read_cell()` with `ink_rule="dark"`: the box-height scan only
probes column `ox` (the cell's leftmost pixel) via
`is_background(ox, oy + box_h)` to find where the background resumes
vertically. If a glyph's ink doesn't touch the leftmost column of its cell
(e.g. left-side bearing), `box_h` comes out `0` and a visibly-inked cell
rasterises to **zero ink** — the glyph silently disappears.
`tests/test_fonts_unit.py::test_dark_ink_rule_blank_leftmost_column_yields_empty_box`

Also (same file): `BitmapFont.__init__` reads `cell_w`/`cell_h`/`ascent`
outside the `try/except (OSError, KeyError)` that wraps sheet loading, so a
`font.json` sheet missing one of those keys raises a bare `KeyError`
instead of the module's own `FontError` — inconsistent with the missing
`"file"` key case, which IS caught.

## Dead / unreachable code (not bugs, but noted)

- `export.py::export_sprite`'s `if format == "gif": ... else: ...` branches
  build byte-identical `args` and call `run_command` identically — the
  branch has no actual behavioral difference.
- `palette.py::generate_color_ramp`'s `t = ... if steps > 1 else 0` ternary
  has a permanently unreachable `else 0` arm since validation already
  rejects `steps < 2` earlier in the function.
- `export.py::export_frame`'s "rename frame-numbered sibling" fallback
  (lines ~130-138) is not reachable through the real Aseprite CLI as
  documented — verified directly that `--frame-range` writes to the exact
  requested filename even for frame 2+ of a multi-frame sprite, no numbered
  sibling produced. Covered via mock instead of a real repro.

## Environment-dependent guards (structurally hard to test without mocking)

- `pixel_read.py`'s four `if not success:` branches (process-level
  subprocess failure) are unreachable via a real corrupt/garbage
  `.aseprite` file — Aseprite exits 0 even on a bad file (prints "Error
  reading header" to stderr) and the script's own `"ERROR:No active
  sprite"` line catches it instead. Covered via mocking
  `AsepriteCommand.execute_lua_script` directly.
- `canvas.create_canvas` writing into a `chmod 555` directory it doesn't
  own write permission on: verified empirically that Aseprite's
  `Sprite:saveAs()` still succeeds (writes the file) even into a
  directory whose permission bits should deny it, and even auto-creates
  missing parent directories. Not confirmed why (possibly Aseprite
  ignoring/swallowing the OS-level permission error and reporting success
  regardless) — flagged for awareness, not chased further this session.
