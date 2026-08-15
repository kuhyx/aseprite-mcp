# #legacy_9e72 Legacy issue: fix(commands): reject_traversal normalized the path before checking it

- 2026-08-15T13:28:26Z `issue`: Legacy issue: fix(commands): reject_traversal normalized the path before checking it
- 2026-08-15T13:28:26Z `fix`: fix(commands): reject_traversal normalized the path before checking it
- 2026-08-15T13:58:32Z `fix`: Root cause (security): reject_traversal called os.path.normpath() BEFORE checking for "..", collapsing "foo/../bar.aseprite" to "bar.aseprite" — so a mid-path ".." was accepted while a leading "../" was rejected. The guard depended on whether traversal cancelled out. Fix: check raw path components; whole-component ".." match still avoids false-positives on names like "foo..bar.aseprite". [aseprite_mcp/core/commands.py]
