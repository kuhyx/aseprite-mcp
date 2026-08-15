# #legacy_b083 Legacy issue: fix(animation): four tools fabricated success inside app.transaction

- 2026-08-15T13:13:50Z `issue`: Legacy issue: fix(animation): four tools fabricated success inside app.transaction
- 2026-08-15T13:13:50Z `fix`: fix(animation): four tools fabricated success inside app.transaction
- 2026-08-15T13:58:13Z `fix`: Root cause: set_cel_position, create_cel, copy_cel, copy_frame all guarded with `return` inside app.transaction — same closure-exit bug, so all four fabricated success while rewriting the file. Fix: hoist all four guards above the transaction; also validate set_cel_position's source_frame_index. [aseprite_mcp/tools/animation.py]
