# #legacy_92d4 Legacy issue: fix(export,drawing): validate frame index and circle radius

- 2026-08-15T13:26:04Z `issue`: Legacy issue: fix(export,drawing): validate frame index and circle radius
- 2026-08-15T13:26:04Z `fix`: fix(export,drawing): validate frame index and circle radius
- 2026-08-15T13:58:27Z `fix`: Root cause: Aseprite silently clamps an out-of-range --frame-range, exits 0, and writes a fully transparent PNG — so export_frame reported "Frame 999 exported" for a 1-frame sprite. Fix: validate the frame index up front (as export_tag already did). Also added the missing radius>0 guard to draw_circle/draw_circle_at. [aseprite_mcp/tools/export.py]
