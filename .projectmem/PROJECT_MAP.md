# Project Map - aseprite-mcp

## Project purpose
A Python MCP server that gives AI assistants full control over Aseprite for
creating pixel art and animated sprites — 104 tools across 17 categories.
Tools are deliberately higher-level than raw primitives (shading ramps with
hue shifting, ordered dithering, outlines, palette presets with quantization,
onion-skin renders, frame diffing) so an LLM can produce *good* pixel art and
check its own work, not just push pixels.

## Stack
- Tags: docker, github-actions, httpx, pytest, python
- Key libraries: httpx, pillow, python-dotenv, typing_extensions
- Lint/type/test gate: ruff, mypy --strict, pytest (100% branch coverage)
- Detected from: pyproject.toml, requirements.txt, Dockerfile, docker-compose.yml, .github/workflows

## Structure
- `aseprite_mcp/` — the MCP server package
  - `aseprite_mcp/__main__.py` — entry point (`uv run -m aseprite_mcp`)
  - `aseprite_mcp/core/` — shared infrastructure, no MCP tools
    - `core/commands.py` — `AsepriteCommand`: runs Aseprite CLI + Lua scripts; owns `reject_traversal` path validation
    - `core/lua.py` — reusable Lua snippets injected into generated scripts (`REQUIRE_CEL`, `GROW_CEL`)
    - `core/fonts.py` — bitmap font cell reader used by `tools/text.py`
    - `core/colors.py` — color parsing/conversion helpers
    - `core/paths.py` — path resolution helpers
    - `core/native.py` — native Aseprite feature detection
  - `aseprite_mcp/tools/` — one module per tool category; each registers MCP tools
    - `tools/animation.py` (1942 L) — frames, cels, tags, tweening, onion skin
    - `tools/drawing.py` (1527 L) — pixels, lines, shapes, fills, gradients
    - `tools/quality.py` (1045 L) — dithering, ramps, outlines, quality passes
    - `tools/palette.py` — palettes, presets, quantization, color ramps
    - `tools/export.py` — sprite/frame/tag/spritesheet export
    - `tools/fx.py`, `tools/native_fx.py` — effects (scripted vs native)
    - `tools/text.py` — bitmap text rendering
    - `tools/tilemap.py`, `tools/slices.py`, `tools/layers.py`,
      `tools/selection.py`, `tools/transform.py`, `tools/canvas.py`
    - `tools/analysis.py`, `tools/pixel_read.py` — visual feedback: read pixels back, compare frames
    - `tools/preview.py` — preview server
    - `tools/scene.py` — scene validation
    - `tools/script.py` — raw Lua escape hatch (`run_lua_script`)
    - `tools/guide.py` — workflow guidance surfaced as a tool
- `tests/` — pytest suite, 100% branch coverage gate
- `skills/` — vendored Claude skills that drive this server (item-icons, pixel-animation, seamless-tilesets, anime-pixel-art)
- `examples/` — committed showcase art (swordsman, icon-animation, tilesets)
- `docs/`, `references/`, `scripts/`
- `tofix.md` — the single tracker of genuinely-open issues (BUGS_FOUND.md was deleted 2026-08-15)

## Relationships
- `aseprite_mcp/__main__.py` registers every module in `aseprite_mcp/tools/`
- every `tools/*.py` module calls `core/commands.py` to execute Lua against Aseprite
- `tools/drawing.py` and `tools/animation.py` inject snippets from `core/lua.py`
- `tools/text.py` reads glyph cells via `core/fonts.py`
- `skills/*/SKILL.md` drive the server through its MCP tools; they cite tool names directly, so renaming a tool breaks the skills
- `.github/workflows/ci.yml` runs the lint + type + coverage gate (tests need real Aseprite, self-hosted runner)
