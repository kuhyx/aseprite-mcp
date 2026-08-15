# #legacy_4119 Legacy issue: fix(drawing): draw_pixels and draw_line silently dropped out-of-cel art

- 2026-08-15T13:22:56Z `issue`: Legacy issue: fix(drawing): draw_pixels and draw_line silently dropped out-of-cel art
- 2026-08-15T13:22:56Z `fix`: fix(drawing): draw_pixels and draw_line silently dropped out-of-cel art
- 2026-08-15T13:58:23Z `fix`: Root cause: a cel is only as large as its content bbox, so img:putPixel() outside it is a silent no-op — draw_pixels and draw_line dropped out-of-cel art while reporting success. Fix: extracted GROW_CEL snippet into core/lua.py; draw_line widens the bbox by floor(thickness/2). NOT a bug in draw_rectangle/fill_area/draw_circle: they dispatch app.useTool, which grows the cel itself (pinned by regression test). [aseprite_mcp/core/lua.py]
