# projectmem - aseprite-mcp

_Last updated: 2026-08-15_

## Project purpose
A Python MCP server that gives AI assistants full control over Aseprite for
creating pixel art and animated sprites — 104 tools across 17 categories.
Tools are deliberately higher-level than raw primitives (shading ramps with
hue shifting, ordered dithering, outlines, palette presets with quantization,
onion-skin renders, frame diffing) so an LLM can produce *good* pixel art and
check its own work, not just push pixels.

## Recent issues
- [DONE] #legacy_f974 Legacy issue: fix(canvas): create_canvas reported success for a file it never wrote -> Root cause: Sprite:saveAs() fails silently into an unwritable directory — the script still reached print("OK"), so create_canvas reported creating a file that does not exist. (BUGS_FOUND.md's claim that saveAs "writes the file anyway" was wrong; the file is absent.) Fix: confirm the file exists before reporting success, as export_sprite already does. [aseprite_mcp/tools/canvas.py] (fixed)
- [DONE] #legacy_f796 Legacy issue: docs: record the 22 vendored-script ruff errors in tofix.md -> docs: record the 22 vendored-script ruff errors in tofix.md (fixed)
- [DONE] #legacy_f076 Legacy issue: fix: restore the full-resolution filmstrip that Read downscaled in place -> fix: restore the full-resolution filmstrip that Read downscaled in place (fixed)
- [DONE] #legacy_c6d8 Legacy issue: fix(canvas): set_layer fabricated success on a missing layer -> Root cause: set_layer's not-found `return` sat INSIDE app.transaction, which exits only the closure — execution fell through to saveAs + print("OK"), reporting success and rewriting the file. Fix: hoist the guard above the transaction. [aseprite_mcp/tools/canvas.py] (fixed)
- [DONE] #legacy_bdc7 Legacy issue: fix(drawing): nine _at tools fabricated success on a missing cel -> Root cause: nine _at tools (draw_pixels_at, draw_line_at, draw_rectangle_at, draw_circle_at, fill_area_at, draw_ellipse_at, draw_polygon, draw_path, apply_gradient_rect) guarded a missing cel inside app.transaction — same closure-exit bug. Fix: added REQUIRE_CEL snippet to core/lua.py and hoisted all nine guards above the transaction. [aseprite_mcp/tools/drawing.py] (fixed)
- [DONE] #legacy_b083 Legacy issue: fix(animation): four tools fabricated success inside app.transaction -> Root cause: set_cel_position, create_cel, copy_cel, copy_frame all guarded with `return` inside app.transaction — same closure-exit bug, so all four fabricated success while rewriting the file. Fix: hoist all four guards above the transaction; also validate set_cel_position's source_frame_index. [aseprite_mcp/tools/animation.py] (fixed)
- [DONE] #legacy_9e72 Legacy issue: fix(commands): reject_traversal normalized the path before checking it -> Root cause (security): reject_traversal called os.path.normpath() BEFORE checking for "..", collapsing "foo/../bar.aseprite" to "bar.aseprite" — so a mid-path ".." was accepted while a leading "../" was rejected. The guard depended on whether traversal cancelled out. Fix: check raw path components; whole-component ".." match still avoids false-positives on names like "foo..bar.aseprite". [aseprite_mcp/core/commands.py] (fixed)
- [DONE] #legacy_92d4 Legacy issue: fix(export,drawing): validate frame index and circle radius -> Root cause: Aseprite silently clamps an out-of-range --frame-range, exits 0, and writes a fully transparent PNG — so export_frame reported "Frame 999 exported" for a 1-frame sprite. Fix: validate the frame index up front (as export_tag already did). Also added the missing radius>0 guard to draw_circle/draw_circle_at. [aseprite_mcp/tools/export.py] (fixed)
- [DONE] #legacy_909a Legacy issue: fix(export): stop the frame-rename fallback clobbering unrelated files -> Root cause (destructive): export_frame's "Aseprite may append the frame number" fallback globbed "<stem>*<suffix>" and renamed the first match onto the requested path — for hero.png that also matched heroine.png / hero_backup.png, silently destroying an unrelated user file. Fix: match digit-suffixed siblings only. Also collapsed export_sprite's identical gif/else branches and generate_color_ramp's unreachable steps>1 branch. [aseprite_mcp/tools/export.py] (fixed)
- [DONE] #legacy_6fb9 Legacy issue: docs: correct two claims the growth fix made false -> docs: correct two claims the growth fix made false (fixed)
- [DONE] #legacy_5f45 Legacy issue: fix: add a distinct-frame gate, closing an A,B,A,B hole -> fix: add a distinct-frame gate, closing an A,B,A,B hole (fixed)
- [DONE] #legacy_5a98 Legacy issue: fix(fonts): dark-rule glyphs with a side bearing rendered as blanks -> Root cause: _read_cell's dark-mode box scan inferred a 2-D extent from a single line — box_w probed only row `oy`, box_h only column `ox`. A glyph whose ink misses the cell's leftmost column or top row read as background there, so the box collapsed to zero and range(0) wrote no ink, rendering the glyph blank. [aseprite_mcp/core/fonts.py] (fixed)
- [DONE] #legacy_4119 Legacy issue: fix(drawing): draw_pixels and draw_line silently dropped out-of-cel art -> Root cause: a cel is only as large as its content bbox, so img:putPixel() outside it is a silent no-op — draw_pixels and draw_line dropped out-of-cel art while reporting success. Fix: extracted GROW_CEL snippet into core/lua.py; draw_line widens the bbox by floor(thickness/2). NOT a bug in draw_rectangle/fill_area/draw_circle: they dispatch app.useTool, which grows the cel itself (pinned by regression test). [aseprite_mcp/core/lua.py] (fixed)
- [DONE] #legacy_08ff Legacy issue: fix: render every README image at native width so the pixel art stays crisp -> fix: render every README image at native width so the pixel art stays crisp (fixed)
- [OPEN] #0002 Open, low priority: export_frame's frame-numbered sibling fallback still exists (now narrowed to digit-suffixed matches only after it was found clobbering unrelated files). The path only runs when the expected output file is absent. [aseprite_mcp/tools/export.py] (open)
- [OPEN] #0001 Open by nature: pixel_read.py's four `if not success:` process-failure guards are structurally unreachable — Aseprite exits 0 even on a corrupt file, so the script's own "ERROR:No active sprite" line is what catches it. Covered only by mocking execute_lua_script directly. Kept deliberately rather than deleting real error handling. Do not "fix" by removing them. [aseprite_mcp/tools/pixel_read.py] (open)

## Decisions
- Single tracker: tofix.md holds all genuinely-open issues; BUGS_FOUND.md was deleted 2026-08-15 because eight docs/skills cited it and asserted its already-fixed bugs as present-tense fact. tofix.md also keeps a "verified NOT bugs" section so a future reader does not "fix" working code. [tofix.md]

## Notes
- feat: animate the water tile, and add a shift gate for opaque tiles
- feat: track the exports as a permanent showcase, and show them in the README
- docs(skills): add pixel-animation, and teach all three to ship the art
- feat(skills): install skills deterministically instead of by hand
- style(skills): clear all 22 ruff errors in the vendored reference scripts
- style: drop the last two lint suppressions and green the format gate
- gotcha: in Aseprite Lua, a `return` inside app.transaction(function() ... end) exits ONLY the closure — execution falls through to spr:saveAs + print("OK"), so the tool reports success AND rewrites the file. Every guard must sit ABOVE the transaction. This exact bug was found in 14 tools across canvas/animation/drawing on 2026-08-15; use the REQUIRE_CEL snippet in core/lua.py. [aseprite_mcp/core/lua.py]
- gotcha: Aseprite exits 0 on failure — it clamps an out-of-range --frame-range and writes a transparent PNG, exits 0 on a corrupt file (only stderr "Error reading header"), and Sprite:saveAs() fails silently. Never treat exit status as success: validate inputs up front and confirm the output file exists afterwards. [aseprite_mcp/tools/export.py]
- gotcha: when testing that a failed call did NOT write, assert on file mtime, not bytes — saveAs on an unmutated sprite can rewrite byte-identical content, so a byte comparison passes even when the tool wrongly saved. [tests/]

## Key files
- `examples/tileset/water.aseprite`
- `skills/item-icons/references/animgates.py`
- `.gitignore`
- `README.md`
- `examples/icon-animation/bomb.png`
- `examples/icon-animation/bomb_x8.png`
- `examples/icon-animation/bone.png`
- `examples/icon-animation/bone_x8.png`
- `examples/icon-animation/book.png`
- `examples/icon-animation/book_x8.png`
- `examples/icon-animation/gem.png`
- `examples/icon-animation/gem_x8.png`
- `examples/icon-animation/key.png`
- `examples/icon-animation/key_x8.png`
- `examples/icon-animation/scroll.png`
- `examples/icon-animation/scroll_x8.png`
- `examples/tileset/dirt.png`
- `examples/tileset/dirt_x8.png`
- `examples/tileset/grass.png`
- `examples/tileset/grass_dirt.png`

## Open questions
- None logged yet.
