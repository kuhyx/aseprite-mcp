---
name: seamless-tilesets
description: Draw seamless 32x32 (or 16x16) terrain tilesets in Aseprite via the `aseprite` MCP server — grass, dirt, stone, sand, water, plus transition tiles and 4-frame animated water. Use when asked for a tileset, terrain tiles, a tilemap, ground textures, "tiles that repeat without seams", or to fix tiles that show a visible grid when repeated. Contains a fixed ordered procedure and the deterministic gates that catch the failures which look fine in a single tile and only appear when tiled.
---

# Seamless terrain tilesets

**Status: solved.** A 5-tile base set + 3 transitions + a 4-frame water loop
was built and accepted in one session. Follow the order; the gates below are
not optional, because every one of them caught a defect that visual inspection
had already passed.

Tiles are, per `PIXEL_ART_FEASIBILITY.md`, the #2 easiest subject for an LLM:
no human prior, silhouette-free, and — crucially — the one hard constraint
(seamlessness) is **machine-checkable**. That is what makes them winnable.

> **Draw the tiles through the MCP, not with the example script.**
> `references/example_tileset.py` builds tiles with PIL: it fills via
> `Image.new`, stamps every pixel with `putpixel`, and never calls
> `Image.open`. That is the path the user banned after the item-icon audit
> (see `skills/item-icons/SKILL.md`), so treat it as a **record of the cluster
> placements** — the coordinate tables are still the valuable part — to be
> redrawn with `draw_pixels_at` / `draw_rectangle_at`. The hook does not block
> it by name, but `putpixel` hits its hard-deny branch.
> `references/tiletool.py` is unaffected — it *reads* exported PNGs to score
> seams, which is post-processing and stays allowed.
>
> The "solved" status above was recorded before that rule existed; the seam and
> quadrant metrics still hold, but the tiles behind it were not verified as
> MCP-drawn.
>
> **Resolved:** the set was redrawn through the MCP and the `.aseprite` sources
> are tracked in `examples/tileset/`. What was *not* solved was getting the art
> in front of the user — see step 10.

## The one-paragraph version

Fill the tile with a base colour. Stamp small, hand-placed clusters of a
shadow tone and a light tone, with coordinates chosen so **each quadrant
carries the same visual weight** and **several clusters straddle the tile
edge** (writes wrap modulo 32). Never place a big high-contrast feature. Check
with the seam metric and the quadrant-weight metric, then render a 3x3 repeat
and *look at it*. Transitions are made by compositing one finished tile over
another along a hand-authored irregular depth profile — never drawn fresh.

---

## Step-by-step

### 1. Pick three tones per material, from one palette

`apply_palette_preset(filename, "dawnbringer32")`, then take **shadow / base /
light** for each material. Three is enough; more reads as noise at this size.

Verified DB32 triples that work:

| Material | shadow | base | light |
|---|---|---|---|
| grass | `#4B692F` | `#6ABE30` | `#99E550` |
| dirt | `#45283C` | `#663931` | `#8F563B` |
| stone | `#323C39` | `#696A6A` | `#9BADB7` |
| sand | `#8A6F30` | `#D9A066` | `#EEC39A` |
| water | `#306082` | `#5B6EE1` | `#639BFF` |

**Do not use a saturated navy (`#3F3F74`) as stone mortar.** It reads as blue
plastic. `#323C39` (dark slate) is the neutral that works — this was a real
rejection.

### 2. Author clusters, do not sample noise

Define 4–6 small cluster *shapes* by hand (a 3px blade, a 5px tuft, a 2x2
pebble, a 4px ripple), then a hand-picked list of `(x, y)` positions for each
tone. Writes wrap with `% SIZE`, so a cluster placed at x=30 continues at x=0
and the seam is defeated **by construction**.

Two rules govern the position list, and both come from Slynyrd:

- **Even visual weight.** "If any area of the tile has a visual dominance the
  pattern will become too obvious." Spread positions so all four quadrants get
  a similar count. Measured target: quadrant luminance ratio **< 1.18**.
- **Straddle the edges deliberately.** Include clusters at x or y near 0 and
  near 31. Features contained neatly inside the tile *advertise* the grid;
  features crossing it hide the grid.

Also: avoid touching key clusters together (they clump into irregular blobs
and read as noise) — corner-to-corner contact is fine.

### 3. Vary cluster length, or you get corduroy

A single repeated ripple shape produces faint regular diagonal rows. Alternate
between 2–3 different lengths, indexed off the position
(`shapes[(x + y) % 3]`). This measurably improved the seam score (sand
h=1.54 → 1.19) *and* removed a visible artifact.

### 4. Run the gates — with a calibrated threshold

```
python tiletool.py grass.png dirt.png ...
```

Two metrics:

- **Seam energy** — mean colour difference across the wrap boundary, divided
  by the mean difference between adjacent interior columns/rows. A ratio near
  1 means the seam is statistically indistinguishable from the interior.
- **Quadrant weight** — max/min mean luminance across the four quadrants.

> **CALIBRATE THE THRESHOLD AGAINST CONTROLS. Do not guess it.**
>
> This is the mistake worth avoiding most. A guessed threshold of 1.35 flagged
> all five tiles as seamed, and they were fine. Generating two controls settled
> it in one command:
>
> - a wrapping sinusoid (provably seamless) scores **h≈1.6**
> - a hard half/half split (provably seamed) scores **h≈31**
>
> So anything under ~4 is texture variation, not a seam. The tiles scored
> 1.1–2.1. **The threshold was wrong, not the art.** When a metric disagrees
> with your eyes, calibrate it before you touch the art.

### 5. Render a 3x3 repeat and READ it

The metrics are a filter, never a verdict. Tile 3x3, upscale 4x, and look. A
grid seam, a dominant anchor feature, or corduroy banding are all obvious here
and invisible in a single tile.

### 6. Transitions — subtract, never redraw

Composite a finished top tile over a finished bottom tile along a
**hand-authored per-column depth profile** (a list of 32 ints). Both textures
keep their own identity because every pixel comes from a real tile.

- Make the profile **irregular** (values wandering ±2 px). A smooth or
  constant profile reads as a ruled line.
- Optionally add a 1px **fringe** at the boundary: dark soil under grass, pale
  foam at a waterline. This is what sells the join.
- The profile must itself wrap — start and end values should be close.

### 7. Gate transitions differently — they are SUPPOSED to differ vertically

A transition tile legitimately looks different top vs bottom, so the vertical
seam metric and quadrant weight will scream (measured v≈7–8.7, weight≈2.0).
**That is correct, not a bug.** For a transition, check:

- the **horizontal** wrap (must still be < 4), and
- the **vertical join** to its neighbours: stack `top / transition / bottom`
  and measure the two internal row boundaries against the interior baseline.
  Measured 0.20–0.89, i.e. below baseline. Anything under ~4 is clean.

Make the gate shape-aware rather than loosening it globally.

### 8. Animated water — the shift must divide the tile

Draw N frames where the ripple clusters are offset by a shift. **The shifts
must span a whole cycle**, or the wrap from the last frame to the first is a
different-sized step and the loop pops.

- Shifts `(0, 2, 4, 6)` on a 32px tile → wrap has to jump back 6px.
  Measured: interior steps 5.3, wrap step 8.24. **Visible pop.**
- Shifts `(0, 8, 16, 24)` → wrap is one more 8px step.
  Measured: all four steps **8.19, ratio exactly 1.00.** Perfect loop.

Moving the shadow ripples one way and the light crests the *other* way reads as
flow rather than the whole texture sliding sideways.

Then: `set_frame_duration_all(180)`, `set_tag("flow", 1, 4)`,
`export_tag(..., "water_flow.gif", scale)`.

`export_tag` takes `scale` — **one call gives you the scaled animated GIF.** Do
not export frames and stitch them with ImageMagick; a later session did that,
having checked `export_sprite` (which genuinely has no `scale`) and generalised
from it. See `skills/pixel-animation/SKILL.md` step 5.

### 9. Verify the exported GIF, not the source frames

Re-open the GIF, diff consecutive frames **including the wrap**, and assert
every step changed. See the animation trap below — this is not paranoia.

**Coalesce before diffing**: `magick out.gif -coalesce /tmp/scratch/coal_%d.png`.
GIF delta-optimization stores later frames cropped to the changed region
(`256x232+0+8`), so diffing raw frames compares different-sized canvases and
proves nothing. This step is why "verify the exported GIF" can be followed to
the letter and still miss.

### 10. Show the tiles — sources alone are not a deliverable

Full procedure in `references/showcase.md`. A session finished this
tileset, committed only the `.aseprite` files, and the user's next question was
"where can I see those?" — the answer was nowhere.

---

## Traps that will actually bite

- **`audit_animation` reports "clean" on an animation with four identical
  frames.** It checks cels and overlaps, not motion. A static "animation"
  passes it. Always diff the exported frames yourself and **fail closed** when
  any adjacent pair is identical (wrap included).
- **A tool returning success is not evidence.** Probe with
  `get_composite_rect` or re-open the export.
- **Prefer the `_at` tool variants.** The non-`_at` siblings silently drop
  out-of-bounds pixels while reporting success.
- **`import_image_as_layer` lives in `export`, not `layers`.** Likewise
  `outline_cel` is in `fx`, `validate_scene` is in `quality`. Grep before
  assuming a module.
- **`add_frame` takes only a filename** (no index) — use
  `animation.add_frames(filename, count)` to add several.
- **Don't gate transition tiles with the base-tile thresholds** (see step 7).
- If a metric and your eyes disagree, **calibrate the metric** (step 4).

## Verification checklist

| Check | How | Catches |
|---|---|---|
| Seam energy | `tiletool.py`, threshold from controls | Hard edges at the wrap |
| Quadrant weight | ratio < 1.18 | A dominant feature that anchors the grid |
| 3x3 repeat | render, upscale, **Read the PNG** | Corduroy, anchors, anything judgement-based |
| Transition join | stack top/mid/bottom, diff boundary rows | Butt-joints between terrains |
| Loop closure | diff GIF frames incl. wrap; ratio ≈ 1.0 | Popping animations |
| Motion present | every adjacent pair differs | Static "animations" |

## Known limits — say these out loud rather than implying coverage

- Directional (top-to-bottom) transitions do **not** make a corner set. With
  only `grass_dirt`-style tiles, vertical junctions between two terrains are
  hard butt-joints. A **16-tile Wang** or **47-tile blob** set is what fixes
  that; a third terrain pushes the count into the hundreds.
  (Ref: Boris the Brave, "Classification of Tilesets".)
- Three terrains in one blob set is where this stops being cheap.

## Sources

- Slynyrd Pixelblog 20 & 43 (top-down tiles) — even visual weight, edge
  straddling, cluster discipline, transitions by subtraction
- Boris the Brave, "Classification of Tilesets" — 16-tile Wang vs 47-blob
- Wolthera, "Animating Water Tiles part 1: Edges" — 4-frame shift technique
- `PIXEL_ART_FEASIBILITY.md` §5 — why tilesets rank #2 and are machine-checkable
- `tofix.md` — remaining known issues (fabricated success and the non-`_at`
  bounds drops were fixed on 2026-08-15)
