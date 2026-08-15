# #legacy_f974 Legacy issue: fix(canvas): create_canvas reported success for a file it never wrote

- 2026-08-15T13:45:53Z `issue`: Legacy issue: fix(canvas): create_canvas reported success for a file it never wrote
- 2026-08-15T13:45:53Z `fix`: fix(canvas): create_canvas reported success for a file it never wrote
- 2026-08-15T13:58:48Z `fix`: Root cause: Sprite:saveAs() fails silently into an unwritable directory — the script still reached print("OK"), so create_canvas reported creating a file that does not exist. (BUGS_FOUND.md's claim that saveAs "writes the file anyway" was wrong; the file is absent.) Fix: confirm the file exists before reporting success, as export_sprite already does. [aseprite_mcp/tools/canvas.py]
