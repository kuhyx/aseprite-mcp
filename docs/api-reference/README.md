# Aseprite Lua API reference (vendored)

Vendored from https://github.com/aseprite/api — the official Lua scripting API
docs that back https://www.aseprite.org/api/.

**This is the entire surface this MCP server is built on.** Every tool compiles
down to Lua executed by `aseprite --batch --script`, so the API reference is the
spec. Consult it BEFORE writing or fixing a tool.

## Why vendored instead of a RAG database

Measured: **27,309 words across 115 markdown files (~40k tokens, 1.2 MB).**

That is small enough to `grep` directly and to read a whole page on demand. A
RAG pipeline (chunking, embeddings, a vector store, a retrieval MCP) would add
a build step, an index to keep in sync and a similarity-search failure mode, in
exchange for solving a problem this corpus does not have. Reach for RAG when a
corpus is too big to grep — this one is not.

Compare: the ArchWiki RAG in `~/wiki-kb` exists because that corpus is
thousands of pages. 115 files is a `grep -rn`.

## How to use it

```bash
# Find a method
grep -rn "putPixel" docs/api-reference/api/

# Read a class
cat docs/api-reference/api/cel.md

# Check what changed between Aseprite versions
grep -n "1.3" docs/api-reference/Changes.md
```

## What it does NOT cover

`https://www.aseprite.org/docs/` (the other URL) is **end-user GUI
documentation** — toolbars, shortcuts, preferences. It is not useful here; the
MCP never touches the GUI.

More importantly, the API reference **documents intent, not quirks**. It does
NOT mention that `Image:putPixel()` outside the cel's bounding box is silently
discarded — the bug fixed in `fix/draw-pixels-at-cel-bounds`, which was present
in upstream and every fork. Undocumented behaviour is found by TESTING, not by
reading. Use the docs to check a signature; use a probe
(`get_composite_rect`) to check what actually happened.

## Verified against this reference

- `Rectangle:union()` and `Rectangle:intersect()` exist with the semantics the
  cel-growth fix relies on (api/rectangle.md).
- The server uses no deprecated calls (`putImage`, `putSprite` are absent).
