# Prompt for a new session — icon & sprite animation

Copy everything below the line into a fresh Claude Code session started in
`~/aseprite-mcp`. It is written to be pasted as-is.

---

Animate pixel art with the `aseprite` MCP server. Read these first, in order —
they are in this repo and they encode mistakes that cost a full session each:

- `skills/item-icons/SKILL.md` — the icon procedure, the gates, and an honest
  6/12 hit rate. **Section "Gates" and section "Traps" are the load-bearing
  parts.**
- `skills/seamless-tilesets/SKILL.md` — §8/§9 cover animated tiles: why a
  4-frame shift must divide the tile evenly, and why you must verify the
  exported GIF rather than the source frames.
- `tofix.md` — the remaining known issues. The "fabricated success" class
  (tools reporting OK having done nothing) was fixed on 2026-08-15; those
  tools now return a hard error instead.
- `references/CREDITS.md` — licences for the vendored reference sheets. One set
  is CC-BY-SA (ShareAlike); the rest are CC0.

## What exists already

Six approved 16x16 icon *designs* live in
`skills/item-icons/references/passing-grids/`: **key, scroll, book, bone, gem,
bomb**. They are ASCII glyph grids — one character per pixel, with the
character→dawnbringer32 mapping documented in `references/gridtool.py`. Read
them as a **shape reference to redraw from**, not as art to load: see "Working
method" below. Six other icons (potion, sword, shield, coin, ring, meat) were
drawn and **rejected**; do not resurrect them without redrawing from scratch.

A working animation driver was built last session but lives only in a
scratchpad that has since been cleared. **You will need to rebuild it** — the
procedure below is what it did, and the traps section is why it ended up that
way.

## The task

Build a small library of **4-frame loops** for the six approved icons, plus
whatever the state of the art needs beyond that. Concretely:

1. **Idle bob** — 1px vertical shift.
2. **Specular sweep** — a glint travelling along a hand-authored path across
   the object's lit face.
3. At least one motion that is **not** either of those. Pick something the
   subject justifies (the bomb's fuse burning down and its spark flickering is
   the obvious candidate; a page-flutter on the book is another). This is the
   part that is genuinely open — the first two are solved.

Export each as a GIF at 8x, tagged, and present them as an animated contact
sheet plus per-frame strips.

## Non-negotiable gates (each caught a real bug)

Implement these as **code that fails closed**, not as things you remember to
check:

- **`audit_animation` reports "clean" on an animation whose four frames are
  IDENTICAL.** It checks cels and overlaps, not motion. Diff the *exported
  GIF's* frames yourself and fail when any adjacent pair is identical, wrap
  included. A previous "specular sweep" shipped completely static and passed
  every built-in check.
- **A 1px bob eats the 1px outline margin.** `outline_cel` writes into
  transparent neighbours, so a frame flush against the canvas loses its outline
  on that side. The static grid gate cannot see this — it only inspects the
  unshifted grid. Check margins on **every generated frame**. Confirmed real
  via `get_composite_rect` on a built sprite: raw body colour where the outline
  should be.
  - Consequence: only icons with **≥2px top and bottom margin** can bob
    symmetrically. Of the twelve originally drawn, five qualified. Either bob
    only into the side that has room, or trim a row when authoring.
- **A loop's wrap step must equal its interior steps.** Shifts of `(0,2,4,6)`
  on a 32px tile made the 4→1 wrap a 6px reverse jump: interior deltas 5.3,
  wrap delta 8.24, visible pop. Shifts of `(0,8,16,24)` gave all four steps at
  8.19, ratio exactly 1.00. **Measure the ratio; don't eyeball it.**
- **Success responses are not evidence.** Probe with `get_composite_rect` or
  re-open the export.

## Module locations (grep before assuming)

`outline_cel` → `fx`. `import_image_as_layer` → `export`. `validate_scene` →
`quality`. `add_frames(file, count)` → `animation` (note: `canvas.add_frame`
takes only a filename, no index).

## Working method

**Draw every pixel through the MCP.** Establish full-canvas cel bounds with a
transparent `draw_rectangle_at` first (`draw_pixels_at` drops pixels outside the
cel's current bounds), then build each frame with `draw_pixels_at` /
`draw_rectangle_at` / `draw_line_at`. Outline once per frame, last. Verify with
`get_composite_rect` — success responses are not evidence. To *see* a frame,
`export_sprite` and upscale the PNG with a NEAREST resize; that is display
scaling, not drawing.

**Do not author frames as ASCII `.grid` files and render them to PNG.** An
earlier version of this document recommended exactly that, and it is now
blocked: `~/.claude/hooks/pixelart_mcp_only_pretool.sh` denies `Write`/`Edit`
to `*.grid` and blocks `preview.py` / `circles.py` / `gridtool.py`. The rule
exists because an audit of session `ec51350e` found the six "approved" static
icons were made with **0 `draw_pixels_at` calls** — what was approved were
PIL-rendered previews of text files, and Aseprite drew none of it.

Consequence for the input art: the six grids under `passing-grids/` are a
*reference for shape*, not a delivery format. Read them to see what shape was
approved, then draw that shape with MCP calls. Scripts may still post-process
**exported** images (GIF frame-diffing, contact sheets, frame strips) — the
hook allows PIL that opens a real export, and the animation gates below depend
on it.

## How to judge

Your own review agreed with the human roughly half the time last session.
**Export, Read the GIF yourself, fix what you can see — then present and ask.**
Do not call your own output usable. Present after each meaningful change rather
than batching; on static icons, fixing two critiques at once repeatedly
inverted the first one.

## Scope note

Animation is *more* forgiving than static art — a 1px bob is convincing and
essentially cannot look anatomically wrong — so this should go better than the
static icon set did. If a motion misses twice, cut it rather than iterating a
third time.
