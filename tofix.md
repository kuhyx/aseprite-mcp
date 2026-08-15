# To fix

Known issues deliberately left for a later session. Nothing here blocks the
MCP server, the test suite, or the skills.

---

## 22 ruff errors in the vendored skill reference scripts

**Status:** open. **Found:** 2026-08-15. **Blocks:** nothing.

`uv run ruff check .` reports 22 errors, all in `skills/*/references/*.py`.
The server package (`aseprite_mcp/`), `tests/` and `scripts/` are clean, and
857 tests pass.

These **predate the session that recorded them** — all six files were last
touched on 2026-08-14 by `c668abf` and `2361966`; the recording session's
commits are all 2026-08-15. They were vendored in as a record of how the early
grid-based art was made, and were never linted.

### Reproduce

```bash
uv run ruff check . --output-format=concise
```

### The errors

| File | Count | Rules |
|---|---:|---|
| `skills/item-icons/references/checkgrid.py` | 7 | EXE001, PLC0415, C901, PLR0912, PLR2004 ×3 |
| `skills/seamless-tilesets/references/tiletool.py` | 6 | EXE001, PLC0415, PLR2004 ×4 |
| `skills/seamless-tilesets/references/example_tileset.py` | 3 | EXE001, D401 ×2 |
| `skills/item-icons/references/gridtool.py` | 3 | EXE001, PLR2004 ×2 |
| `skills/item-icons/references/circles.py` | 2 | EXE001, D401 |
| `skills/item-icons/references/preview.py` | 1 | EXE001 |

Grouped by rule:

- **EXE001** (6) — shebang present but the file is not executable. All six are
  `-rw-r--r--`. Either `chmod +x` them or drop the shebang; see the caveat
  below, because for some of these files "make it runnable" is the wrong
  direction.
- **PLR2004** (9) — magic values in comparisons. Real ones worth naming:
  `4.0` (the seam-energy threshold) and `1.18` (the quadrant-weight ceiling) in
  `tiletool.py`. Both are documented constants in `seamless-tilesets/SKILL.md`,
  so extracting them as named constants would make the code agree with the doc.
- **D401** (3) — docstring not in imperative mood.
- **PLC0415** (2) — import not at top level.
- **C901** + **PLR0912** (2) — `check` in `checkgrid.py` is too complex
  (14 > 10) with too many branches (13 > 12).

### Caveat — read before "fixing" these

These files are **not** all live code, and three are actively blocked:

- `~/.claude/hooks/pixelart_mcp_only_pretool.sh` denies running three of the
  `item-icons` helpers by name. They are kept as a **record** of how the
  banned ASCII-grid workflow worked, not as tooling to run. `checkgrid.py`
  gates `.grid` text files, so it cannot check a sprite and nothing in the
  skill's procedure calls it.
- `example_tileset.py` builds tiles with PIL (`putpixel`), which is the path
  banned after the item-icon audit. `seamless-tilesets/SKILL.md` keeps it only
  for its cluster-coordinate tables.
- `tiletool.py` is the exception: it *reads* exported PNGs to score seams,
  which is post-processing and stays allowed. It is genuinely used.

So the options, in the order worth considering:

1. **Fix `tiletool.py` properly** — it is live, and naming `4.0` / `1.18` is a
   real improvement that ties the code to the documented thresholds.
2. **Decide what the record-only files are for.** If they are documentation,
   `extend-exclude` on the reference dirs is more honest than making dead code
   lint-clean. If they should be deleted, the skills already carry the
   knowledge in prose.
3. Do **not** blanket-add `# noqa` — per `~/.claude/memories/code-quality.md`,
   suppressions need a decision first.
