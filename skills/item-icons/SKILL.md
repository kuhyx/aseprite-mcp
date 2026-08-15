---
name: item-icons
description: Draw 16x16 RPG item/inventory icons (potion, sword, shield, key, coin, gem, ring, scroll, bomb, food, book) in Aseprite via the `aseprite` MCP server. Use when asked for item icons, inventory icons, loot/pickup sprites, an icon set, or to fix icons that read as the wrong object ("looks like a gun / a tongue / an eye / a dagger"). Contains the measured construction data, the deterministic gates, and an honest hit-rate — this subject is NOT solved.
---

# 16x16 item icons

**Status: partially solved. Measured hit rate 6 of 12 (50%) on first pass, and
only 6 of 12 after a second redraw round.** `PIXEL_ART_FEASIBILITY.md` ranks
item icons the *easiest* subject for an LLM. That ranking is defensible — a
set is statistically robust, and a rejected icon is one icon, not a rejected
deliverable — but "easiest" is not "solved". Do not promise 12 good icons.

## The actual scoreboard (be honest about this)

Human verdicts across two rounds, one artist, one 12-icon set:

| Verdict | Icons | What they have in common |
|---|---|---|
| **Passed** | key, scroll, book, bone, gem, bomb | Distinctive silhouette; no strong human prior for "correct" proportions |
| **Failed** | potion, sword, shield, coin, ring, meat | Either a *familiar object with known proportions*, or a **plain geometric primitive** |

The pattern that predicts failure is **not** difficulty of drawing. It is:

1. **Objects everyone can picture precisely.** A sword's blade/hilt ratio, a
   flask's shoulders, a ham's shape — viewers have a specific mental image and
   a small error budget, the same "human prior" effect the feasibility doc
   identifies for faces. Bones and scrolls have no canonical proportions.
2. **Plain primitives read as boring.** A circle with a rim was rejected as
   "very barebones"; a slab shield as "meh". Geometric correctness is not
   sufficient — an icon needs a *feature* (the bomb's fuse, the key's wards,
   the book's clasp) or it reads as a placeholder.

**Corollary: geometry gets you to "not wrong", not to "good."** Every fix
below moves an icon from *wrong* to *acceptable*. None of them made an icon
*good*. Budget accordingly and present early.

## Verbatim critiques worth memorising

These are the actual words used. Each names a failure mode that recurs:

- sword → **"looks more like a dagger"** (blade too short), then after the fix
  → **"looks like a gun"** (guard + grip formed an L below the blade axis)
- meat → **"very bad, looks more like a tongue"** (soft symmetric blob, no bone)
- coin → **"looks more like Eye of Sauron"** (centred mark inside a rim *is* an
  iris and pupil), then after the fix → **"very barebones"**
- bomb/potion → **"squashed"** (not actually round)
- shield/gem → **"weird triangle at the bottom"** (tapering to a 1px spike)
- ring → **"should be more circular"**
- potion (after fix) → **"too round"** (a flask is not a sphere)

Note how often fixing one complaint produced the opposite one. **Show the human
after each redraw; do not batch two fixes on one icon.**

---

## Construction data (measured, not recalled)

Measured from shipped CC0/CC-BY-SA sets — see `references/MEASUREMENTS.md` and
`references/SHAPE_RESEARCH.md` in this repo, with sources in `CREDITS.md`.

### Round objects

Use a **gated pixel circle**, not the ellipse tool and not an ellipse formula.

A circle reads as round when its row-run-length **deltas decrease
monotonically** (`2,2,2,0,0`). A stutter (`4,2,0,2`) puts a flat spot mid-arc
followed by a re-widening — a dent. Generate with a distance threshold and a
radius bias `eps` between 0.25 and 0.5, then assert the delta rule:

```
d=11  eps=0.00  5,7,9,11,11,11,11,11,9,7,5
d=12  eps=0.25  6,8,10,12,12,12,12,12,12,10,8,6
d=13  eps=0.25  7,9,11,13,13,13,13,13,13,13,11,9,7
```

> **Caveat, and it matters.** The strong form of this rule was *refuted* during
> research: a professional shipped sprite (Kyrise's `pearl_01a.png`) has
> run-lengths byte-identical to Aseprite's "stuttering" d=14 output and reads
> as convincingly round. Treat the delta rule as a **tie-breaker, not a gate**.
> Only d=12 had no shipped counterexample. If a circle looks wrong, suspect
> diameter and shading before you suspect the arithmetic.

### Terminations — never taper to 1px

Measured across shipped packs: **nothing ends in a 1px point.**

- **Gem** pavilion → **3px flat**, tapering at -2 per row
- **Shield** → **5px flat**, tapering at -1 per side per row (symmetric!)

A `...5,3,1` sequence is literally a triangle. This produced the "weird
triangle at the bottom" rejection on two icons at once.

### Sword — blade:guard:grip = 11:1:4 of 16 rows

- Blade ≈ **69% of total height**, drawn **diagonally** (buys ~14px of blade in
  a 16px box vs ~10px vertical). A vertical blade reads as a dagger.
- Tip is **2-4px**, not 1px.
- **Keep every element on the blade's diagonal axis.** A guard bar plus a grip
  hanging *below and left* of the blade is a pistol silhouette. This was a real
  rejection and the fix is compositional, not a matter of pixel counts.

### Coin — the face is BLANK

The shipped coin's face is completely blank, carried entirely by an offset
highlight. **A centred mark inside a circular rim is an iris and pupil** — that
is the Eye of Sauron failure, and it is structural, not stylistic.
But note the follow-up verdict: a blank rimmed disc was then called
**"barebones"**. A coin likely needs an off-centre feature that is *not*
concentric — a notch on the rim, an off-axis emblem, or a stacked second coin.
**This icon was never landed.**

### Ring — 2px band, 4x4 SQUARE hole

Measured 10w x 12h. The hole is deliberately **not** rounded — at that size
rounding it produces noise. (Delivered version used a round hole and was rated
only "okish".)

### Meat / food — wider than tall, and it needs a bone

All measured meat sprites are **1.2-1.6:1 wider than tall**. A tongue is taller
than wide, which is exactly the read a tall symmetric blob produces. Add a
**bone stub (3-5px)** and a fat rind along one edge. An *angled* bone reads as
anatomical; a *vertical* one reads as a lollipop stick.

### Palette and outline

- `apply_palette_preset("dawnbringer32")`. Verified working ramps: metal
  `#595652 #847E87 #9BADB7 #CBDBFC`, gold `#8A6F30 #DF7126 #FBF236`, wood
  `#45283C #663931 #8F563B #D9A066`.
- **Solid dark outline, one pass, last.** Every measured reference uses a full
  near-black outline (`#000000`-`#0a0a0a`), not selective outlining. It
  guarantees contrast against arbitrary inventory backgrounds — **verify this
  by rendering the set on a LIGHT background as well as a dark one.**
- Colour count: 4-9 typical. A claimed "4-9 ceiling" was retracted after a
  second artist was measured using 19 on one potion. Structure transfers
  between artists; specific values are per-artist style.

---

## Procedure

1. **Plan the icon against the construction data above** — silhouette, the
   readable feature that keeps it off the "barebones" list, and the palette
   ramp. Sketching a layout in scratch notes is fine; what follows is what
   makes it art.
2. Establish full-canvas cel bounds with a transparent `draw_rectangle_at`
   (`draw_pixels_at` drops pixels outside the cel's current bounds), then draw
   the icon with `draw_pixels_at` / `draw_rectangle_at` / `draw_line_at`.
3. **Probe with `get_composite_rect` as you go.** A success response is not
   evidence; several tools report OK having done nothing.
4. **`outline_cel` exactly once, last.**
5. Export at 8x, `Read` the PNG, and build a contact sheet on **both** a dark
   and a light background. Upscaling an export with a NEAREST resize is display
   scaling and is allowed; synthesising pixels in a script is not.
6. Apply the gates below to what Aseprite actually contains, read back through
   `get_composite_rect` — not to a text file you authored.
7. **Present to the human and ask.** Your own review is a filter, never a
   verdict — measured across this session, self-review agreed with the human
   roughly half the time.

> **Do not author icons as ASCII `.grid` files rendered to PNG.** Steps 1-3 of
> this skill used to say exactly that, and an audit of session `ec51350e` found
> the six "approved" icons below were produced with **0 `draw_pixels_at` calls**
> and 114 Bash/python invocations — what the human approved were PIL previews of
> text files, and Aseprite drew none of it. The path is now blocked by
> `~/.claude/hooks/pixelart_mcp_only_pretool.sh`, which denies writing `*.grid`
> and running `preview.py` / `circles.py` / `gridtool.py`. The grids kept under
> `references/passing-grids/` are a **shape reference to redraw from**, and the
> helper scripts are retained only as a record of how they were made.
>
> `references/checkgrid.py` is part of that record too. It gates `.grid` text
> files (it imports `gridtool` for the glyph map), so it cannot check a sprite
> and nothing in this procedure calls it. The hook does not block it by name —
> do not mistake a clean run of it for a gated icon.

## Gates (each one caught a real defect)

| Gate | Catches | How it failed for real |
|---|---|---|
| **Edge margin ≥1px on all four sides** | `outline_cel` writes into transparent neighbours; art flush to the canvas gets **no outline on that side** | 6 of 12 icons shipped with a clipped bottom outline. Confirmed with `get_composite_rect`: raw body colour at y=15 where `#222034` should be |
| **Colour census on the sprite** | Off-palette colours, and missing features — an absent colour is an absent thing | `get_color_stats(top=16)`; target 4-9 unique colours. Note this does **not** replace the old "undefined glyph" check — that failure cannot occur once there is no glyph layer |
| **Drawn bounds == intended bounds** | Pixels silently dropped outside the cel | No recorded incident; `draw_pixels_at` drops out-of-bounds pixels while reporting success, and the transparent `draw_rectangle_at` in step 2 exists to prevent it |
| **Frame margins on EVERY frame** | A 1px animation bob eats the 1px border and re-clips the outline | The static check could not see it — it only inspected the unshifted art |
| **Adjacent frames must differ** | Static "animations" | `audit_animation` reported a **four-identical-frame** animation as clean |

**A tool returning success is not evidence** (`BUGS_FOUND.md`). Probe with
`get_composite_rect` or re-open the export.

## Traps

- Prefer the `_at` tool variants; the non-`_at` siblings silently drop
  out-of-bounds pixels while reporting success.
- `outline_cel` is in `fx`, `import_image_as_layer` in `export`,
  `validate_scene` in `quality`. Grep before assuming a module.
- `add_frame` takes only a filename — use `animation.add_frames(file, count)`.
- Don't fix two critiques on one icon in one pass; you will invert the first
  one (dagger→gun, squashed→too round, eye→barebones all happened).

## When to stop

If an icon has been redrawn twice and still misses, **cut it from the set**
rather than iterating a third time. A 6-icon set that all reads well beats a
12-icon set where half are "meh" — and the human's time is the scarce resource,
not the drawing.
