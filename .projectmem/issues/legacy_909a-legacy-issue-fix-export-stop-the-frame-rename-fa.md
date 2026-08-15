# #legacy_909a Legacy issue: fix(export): stop the frame-rename fallback clobbering unrelated files

- 2026-08-15T13:34:26Z `issue`: Legacy issue: fix(export): stop the frame-rename fallback clobbering unrelated files
- 2026-08-15T13:34:26Z `fix`: fix(export): stop the frame-rename fallback clobbering unrelated files
- 2026-08-15T13:58:43Z `fix`: Root cause (destructive): export_frame's "Aseprite may append the frame number" fallback globbed "<stem>*<suffix>" and renamed the first match onto the requested path — for hero.png that also matched heroine.png / hero_backup.png, silently destroying an unrelated user file. Fix: match digit-suffixed siblings only. Also collapsed export_sprite's identical gif/else branches and generate_color_ramp's unreachable steps>1 branch. [aseprite_mcp/tools/export.py]
