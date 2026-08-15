# #legacy_5a98 Legacy issue: fix(fonts): dark-rule glyphs with a side bearing rendered as blanks

- 2026-08-15T13:32:34Z `issue`: Legacy issue: fix(fonts): dark-rule glyphs with a side bearing rendered as blanks
- 2026-08-15T13:32:34Z `fix`: fix(fonts): dark-rule glyphs with a side bearing rendered as blanks
- 2026-08-15T13:58:37Z `fix`: Root cause: _read_cell's dark-mode box scan inferred a 2-D extent from a single line — box_w probed only row `oy`, box_h only column `ox`. A glyph whose ink misses the cell's leftmost column or top row read as background there, so the box collapsed to zero and range(0) wrote no ink, rendering the glyph blank. [aseprite_mcp/core/fonts.py]
