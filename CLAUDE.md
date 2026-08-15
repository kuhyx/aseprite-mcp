# CLAUDE.md

A Python MCP server giving AI assistants control over Aseprite: 104 tools for
drawing and animating pixel art. Tools are higher-level than primitives so an
LLM can produce good art and verify its own work.

## Commands

```bash
uv run -m aseprite_mcp              # run the server
uv run ruff check .                 # lint
uv run ruff format --check .        # format gate
uv run mypy --strict aseprite_mcp/  # types
uv run pytest --cov --cov-branch --cov-report=term-missing   # 100% branch gate
```

All four must pass; CI (`.github/workflows/ci.yml`) runs exactly these. The
test job needs a real Aseprite binary and runs on a self-hosted runner.

## Architecture

Every `aseprite_mcp/tools/*.py` module registers MCP tools and executes work by
generating a Lua script and running it through `core/commands.py`. Shared Lua
fragments live in `core/lua.py`. See `.projectmem/PROJECT_MAP.md` for the full
path index.

## Hard-won constraints — read before touching tool code

These are the defect *classes* fixed on 2026-08-15. They are easy to
reintroduce because the broken version looks correct and reports success.

1. **A guard must sit ABOVE `app.transaction`, never inside it.** A `return`
   inside `app.transaction(function() ... end)` exits only the closure.
   Execution then falls through to `spr:saveAs(...)` + `print("OK")`, so the
   tool reports work it never did *and still rewrites the file*. This bug was
   found 14 separate times (`set_layer`, four animation tools, nine `_at`
   drawing tools). Use the `REQUIRE_CEL` snippet in `core/lua.py`.

2. **Cels do not auto-grow for `img:putPixel()`.** A cel is only as large as
   its content's bounding box; a `putPixel` outside that box is a silent no-op.
   Use the `GROW_CEL` snippet. Note this does *not* apply to tools dispatching
   `app.useTool` with sprite-global points (`draw_rectangle`, `fill_area`,
   `draw_circle`) — those grow the cel themselves, and a regression test pins
   that, so switching them to `putPixel` will fail loudly.

3. **Aseprite exits 0 on failure.** It silently clamps an out-of-range
   `--frame-range` and writes a transparent PNG; it exits 0 on a corrupt file.
   Never treat exit status as success — validate inputs up front and confirm
   the output file exists afterwards, as `export_sprite` and `create_canvas` do.

4. **`Sprite:saveAs()` can fail silently.** Confirm the file exists before
   reporting success.

5. **Do not normalize a path before checking it for traversal.**
   `os.path.normpath()` collapses `foo/../bar` to `bar`, so a mid-path `..`
   slipped through while a leading `../` was caught. `reject_traversal` in
   `core/commands.py` checks raw components; keep it that way.

6. **Renaming fallbacks must not glob loosely.** `export_frame`'s
   `<stem>*<suffix>` fallback also matched `heroine.png` for a `hero.png`
   export and renamed an unrelated user file onto it. Match digit-suffixed
   siblings only.

`tofix.md` is the single tracker of genuinely-open issues. `BUGS_FOUND.md` was
deleted on 2026-08-15 — several docs still described its fixed bugs as
present-tense fact, which was actively misleading. Do not resurrect it.

## Conventions

- Tool names are API: `skills/*/SKILL.md` cite them directly, so renaming a
  tool breaks the vendored skills.
- No lint suppressions (`# noqa`, `# type: ignore`) — fix the underlying issue.
- Verify behavior against real Aseprite, not just mocks. Assert on file mtime
  when testing that a failed call did *not* write, since `saveAs` on an
  unmutated sprite can rewrite byte-identical content.

<!-- >>> projectmem bridge >>> -->
## projectmem (MANDATORY)

This project uses projectmem for persistent memory + workflow rules.

SESSION START — call these three MCP tools, in this order, BEFORE
answering ANY question about this project:

  1. `get_instructions()` — loads the project's mandatory workflow
     rules. Without this you will not know how to log work
     correctly, when to use `add_note` vs `add_decision`, or how
     the event log is structured.
  2. `get_summary()` — loads project content. Do NOT answer from
     conversation history or by re-reading package.json / README /
     source files.
  3. `get_project_map()` — loads structural layout when relevant.

BEFORE modifying ANY file:
  - Call `precheck_file(path)` — check failure history first.

DURING work — use MCP write tools, NEVER edit `.projectmem/`
files directly via filesystem write:
  - On a bug discovery → `log_issue(summary, location)`.
  - After each fix attempt → `record_attempt(summary, outcome)`.
  - After confirmation → `record_fix(summary)`.
  - On a design choice → `add_decision(summary)`.
  - On a gotcha / setup detail → `add_note(summary)`.

Editing `.projectmem/summary.md` or `.projectmem/PROJECT_MAP.md`
directly bypasses event logging and breaks audit replay. The
summary file regenerates from `events.jsonl` automatically — write
via the MCP tools and the summary will follow.

Do not re-scan source files when MCP tools can give you the same
answer in ~500 tokens instead of ~5000. This is not optional.
<!-- <<< projectmem bridge <<< -->
