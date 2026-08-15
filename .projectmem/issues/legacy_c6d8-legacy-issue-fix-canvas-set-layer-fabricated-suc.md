# #legacy_c6d8 Legacy issue: fix(canvas): set_layer fabricated success on a missing layer

- 2026-08-15T13:10:09Z `issue`: Legacy issue: fix(canvas): set_layer fabricated success on a missing layer
- 2026-08-15T13:10:09Z `fix`: fix(canvas): set_layer fabricated success on a missing layer
- 2026-08-15T13:58:07Z `fix`: Root cause: set_layer's not-found `return` sat INSIDE app.transaction, which exits only the closure — execution fell through to saveAs + print("OK"), reporting success and rewriting the file. Fix: hoist the guard above the transaction. [aseprite_mcp/tools/canvas.py]
