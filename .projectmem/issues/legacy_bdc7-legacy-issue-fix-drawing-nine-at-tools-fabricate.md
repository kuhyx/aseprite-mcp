# #legacy_bdc7 Legacy issue: fix(drawing): nine _at tools fabricated success on a missing cel

- 2026-08-15T13:18:06Z `issue`: Legacy issue: fix(drawing): nine _at tools fabricated success on a missing cel
- 2026-08-15T13:18:06Z `fix`: fix(drawing): nine _at tools fabricated success on a missing cel
- 2026-08-15T13:58:18Z `fix`: Root cause: nine _at tools (draw_pixels_at, draw_line_at, draw_rectangle_at, draw_circle_at, fill_area_at, draw_ellipse_at, draw_polygon, draw_path, apply_gradient_rect) guarded a missing cel inside app.transaction — same closure-exit bug. Fix: added REQUIRE_CEL snippet to core/lua.py and hoisted all nine guards above the transaction. [aseprite_mcp/tools/drawing.py]
