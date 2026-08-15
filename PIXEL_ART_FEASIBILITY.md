# What this MCP can draw well — a feasibility analysis

**Question this answers:** given the tools in this server, what is the *easiest*
pixel art for an LLM to create — where "easiest" means highest chance the result
genuinely looks good, then most useful in a real project?

**Short answer:** a **16×16 item/icon set**, drawn from a preset palette, with a
seamless **32×32 tileset** as the close second. Both beat characters, and both
beat portraits by a wide margin. The reasoning is in §2; it is not about canvas
size.

This document is analysis only — no art was produced in the session that wrote
it. It sits alongside [`tofix.md`](tofix.md) as the other
"what we learned the hard way" doc. (`BUGS_FOUND.md` was folded into
`tofix.md` on 2026-08-15 once its entries were fixed.)

---

## 1. What the server actually gives you

104+ tools across 17 categories (full tables in [`README.md`](README.md)).
Everything compiles down to Lua executed by `aseprite --batch --script`; the
vendored [`docs/api-reference/`](docs/api-reference/) is the spec for what is
ultimately possible.

For *planning art*, eight groups matter:

| Group | What it buys you | Representative tools |
|---|---|---|
| **Drawing** | Shapes and per-pixel control | `draw_rectangle_at`, `draw_ellipse_at`, `draw_line_at`, `draw_polygon`, `fill_area_at`, `draw_pixels_at` |
| **Palette** | Cohesion without inventing hex | `apply_palette_preset`, `generate_color_ramp`, `quantize_to_palette` |
| **Layers** | Separable parts, independent edits | `add_layer`, `reorder_layer`, `merge_layer_down` |
| **Animation** (24) | Motion without redrawing frames | `propagate_cels`, `tween_cel_positions_eased`, `oscillate_cel_positions`, `set_tag` |
| **Effects** | Readability and shading | `outline_cel`, `apply_dither_gradient`, `adjust_hsl` |
| **Inspection / readback** | **Seeing what you actually drew** | `get_color_stats`, `get_composite_rect`, `get_pixel_color` |
| **Quality** | Deterministic gates | `validate_scene`, `audit_animation`, `animation_sanitize` |
| **Export** | Deliverables | `export_frame` (integer upscale), `export_tag`, `export_spritesheet` |

Plus `run_lua_script` as an escape hatch for anything uncovered.

**The readback group is the strategically important one.** It is what separates
this server from "an LLM emitting pixel coordinates blind". Without
`get_color_stats` and `get_composite_rect` there is no way to know a drawing
call did anything. Several tools used to report success while doing nothing at
all; that class was fixed on 2026-08-15 (see `tofix.md`), but reading back what
you drew is still the only proof the art is what you intended.

### Available palette presets

Verified in `aseprite_mcp/tools/palette.py`:

`gameboy` · `monochrome` · `grayscale_4` · `cga` · `pico8` · `c64` ·
`dawnbringer16` · `dawnbringer32`

These are all **retro console palettes**. That is a genuine limitation for
character skin tones — the anime skill states flatly that none of them have
usable anime skin, and that `generate_color_ramp` "overshoots at the dark end
for skin". For **items, tiles, props and UI**, however, they are close to ideal:
`dawnbringer16`/`dawnbringer32` were designed for exactly this kind of small
object art, and using a fixed preset removes the single biggest source of the
"flat and monotone" failure — hand-picked colors that don't relate to each other.

---

## 2. The central thesis: what actually predicts success

### It is not canvas size

The tempting explanation for "sprites good, avatars bad" is resolution. The
repo's own skill rules this out:

> **Resolution is not the problem.** Downscaling the 128px reference to 64px
> still looks good, so 64px is sufficient for a competent portrait. Blaming
> canvas size is a wrong diagnosis.

Two things actually predict whether an LLM's pixel art lands.

### Predictor 1 — judgement asymmetry (the human prior)

> At 32px, identity lives in hairstyle and garment silhouette and the face is a
> few pixels. At 128px **the face IS the artwork**, and faces are the hardest
> thing there is.

Humans have a lifetime of trained priors for faces and bodies, and a
sub-pixel-level error budget for them. A 1px shift in a lower lid produces
*"she looks like she is crying"*; a 1px-too-wide dark row under an eye produces
*"eyebags… she looks very old"*. These are real perceptual failures, not
nitpicks — and they are unforgiving because the viewer's reference is involuntary.

Nobody has an involuntary prior for what a potion bottle looks like. A key, a
coin, a gem, a grass tile: the viewer accepts a wide range as "correct". **The
error budget is enormous** — and that budget, not pixel count, is what an LLM is
spending.

### Predictor 2 — failure-mode class (fixed order vs free-form)

> **Almost every portrait failure was a TOOL/ORDERING bug, not a drawing
> judgement bug.**

This is the more actionable of the two. The documented portrait failures were
things like the fringe being erased by a later face-cut (4×), a mouth silently
dropped to cel bounds (4×), `outline_cel` run twice, and a concave
`draw_polygon` writing nothing while returning success. None of those are
aesthetic misjudgements — they are procedure bugs.

And the evidence for the fix is strong: the **sprite** recipe succeeds because
it is a fixed ordered procedure, and it *transferred cold* — the same 11 steps
produced an approved schoolgirl and then an "office lady" with only color, hair
and garment changes. The **portrait** guidance is a set of principles, so it
gets reinterpreted every attempt and the same ordering mistakes recur.

### The rule that falls out

> **Easiest = a subject with no strong human prior, that reads by silhouette,
> and whose construction can be written down as a fixed order.**

Item icons satisfy all three maximally. Portraits violate all three.

---

## 3. Ranked: easiest → hardest

| # | Subject | Why it lands / fails | Useful in a real project? |
|---|---|---|---|
| 1 | **Item / icon set** (16×16) | No human prior; symmetric or blocky; each icon independent, so one miss doesn't sink the set; trivially fixed order | ★★★ inventory, shop, loot UI |
| 2 | **Seamless tileset** (32×32) | No prior; but adds a hard *correctness* constraint (edges must match) — which is machine-checkable | ★★★ any tile-based game |
| 3 | **Props / environment objects** (barrel, chest, sign, tree) | No prior, silhouette-driven; slightly more shape judgement than icons | ★★★ set dressing |
| 4 | **UI elements** (frames, buttons, bars, 9-patch) | Geometric, ruler-driven; `create_slice`/`set_slice_center` support 9-patch directly | ★★★ every game |
| 5 | **Side-view creature** (slime, bat, blob) | Weak prior — invented creatures can't be "wrong"; avoid recognisable real animals | ★★ enemies |
| 6 | **Full character sprite** (32×32 chibi) | **Solved** but only via the fixed recipe — follow it literally or it degrades | ★★ player/NPC |
| 7 | **Detailed large sprite** (64×64+ character) | Face becomes legible → prior activates → error budget collapses | ★ |
| 8 | **Portrait / avatar** (bust, face-dominant) | **Unsolved.** 8+ attempts, all rejected | — |

On #8, the repo's own position is worth quoting rather than softening:

> **Portraits**: NOT solved. Eight-plus attempts across 32/64/128px, all
> rejected. Do not promise a good portrait.

That matches your experience exactly: anime sprites good, anime avatars bad.
The repo had already independently converged on it.

---

## 4. Recommendation A — 16×16 item/icon set (primary pick)

**The pitch:** 8–12 icons on `dawnbringer32`. This is the safest bet available,
for four compounding reasons:

1. **No human prior** — the error budget is the largest of any subject.
2. **A set is statistically robust.** Twelve independent icons means one weak
   result is a rejected icon, not a rejected deliverable. Every character
   attempt is all-or-nothing by comparison.
3. **Icons are symmetric or gridded.** Bilateral symmetry can be produced by
   construction (`flip_layer`) rather than by judgement.
4. **No anatomy.** Every documented failure mode in this repo's critique log is
   anatomical or facial. None of them can occur on a key or a coin.

**Suggested set** (each mutually distinct in silhouette, which is the point):
potion, sword, shield, key, coin, gem, ring, scroll, bomb, meat, bone, book.

**Method:** one 16×16 sprite per icon (cleanest for iteration and for reuse),
or a single sheet with one layer per icon. `apply_palette_preset` first, then
silhouette with `draw_rectangle_at`/`draw_ellipse_at`, refine with
`draw_pixels_at`, `outline_cel` exactly once at the end.

**Animated extension** (only after the static set is approved): a 4-frame
specular sweep across the gem/potion, or a 4-frame idle bob via
`oscillate_cel_positions`, tagged with `set_tag` and exported with `export_tag`.
Icon animation is unusually forgiving — a 1px vertical bob is convincing and
essentially cannot look anatomically wrong.

---

## 5. Recommendation B — seamless 32×32 tileset

**More useful than the icons; slightly riskier.** Worth being explicit about the
tradeoff rather than pretending it is a tie.

A tileset wins on project usefulness — a grass/dirt/stone/water set is
immediately usable, and `create_tilemap_layer`/`set_tiles` support tilemaps
natively. But it adds a constraint icons don't have: **the edges must tile
seamlessly**. That is a correctness property, and getting it wrong produces a
visible grid seam that no amount of pretty interior pixels rescues.

**The mitigation is what makes this viable:** seamlessness is *machine-checkable*.
Read column 0 and column 31 with `get_composite_rect` and assert they are
compatible; same for rows. It becomes a deterministic gate, not a judgement call
— which puts it in the category of failure this repo already knows how to beat.

**Suggested set:** grass, dirt, stone, water, sand, plus 2–3 transition tiles.

**Animated extension:** 4-frame water or lava, shifting bright pixels through
the tile — the classic palette-cycle look, achievable by drawing 4 frames and
tagging them.

---

## 6. Traps that will actually bite

From the 2026-08-12 coverage pass (now folded into [`tofix.md`](tofix.md)) and
the anime skill's hard-won list. These
are current, unfixed server behaviours — plan around them.

- **Prefer the `_at` variants.** `draw_pixels_at` was fixed to grow the cel
  bbox; the non-`_at` siblings (`draw_pixels`, `draw_line`, `draw_rectangle`,
  `fill_area`, `draw_circle`) were **not**, and silently drop out-of-bounds
  pixels while reporting success.
- **"Fabricated success" is real.** A Lua `return` inside
  `app.transaction(function() … end)` exits only the closure, so the script
  falls through to save and print OK regardless. Several tools report success
  having done nothing — including `export_frame` on an out-of-range frame,
  which writes an empty PNG. **A success response is not evidence.**
- **`draw_polygon` with `fill=true` silently writes nothing on concave shapes**
  and returns success. Use convex pieces or stacked rectangles.
- **`draw_pixels_at` drops pixels outside the cel's current bounds.** To add a
  feature in a new area of a layer, lead with a `draw_rectangle_at` covering
  that area first. Described in the skill as *the* most frequently-hit trap.
- **Run `outline_cel` exactly once, last.** A second pass outlines the first
  outline, thickens edges, and traces interior dark lines as if they were
  silhouette edges.
- **Layer order is bottom-up** — `reorder_layer` position 1 is the bottom.
- **Don't bulk-push a script-generated image.** Generating the art in a script
  and pushing the buffer is, in kuhy's words, *"compiling, not drawing"* — and
  it was the actual defect behind the worst portrait failure, where the head
  came from an ellipse formula that no amount of parameter tuning could round.
  `draw_pixels_at` is a detail brush, not a delivery mechanism.

---

## 7. The verification loop to use

The repo already has a working protocol. Restated as the procedure for the build
session:

**Rule 0 — search the web first.** Non-negotiable per the skill: *"essentially
every genuine fix came from a search result, and essentially every failure came
from me reasoning about pixels unaided."* Before the first pixel, look up
reference art for the specific subject. Verify any tutorial's tool names against
this server's actual tool list — a previous guide invented tool names wholesale.

**Then gate every phase, not just the end:**

| Check | Tool | Catches |
|---|---|---|
| Colour census | `get_color_stats(top=16)` | Missing features (an absent colour = an absent thing); palette drift. Target 6–12 unique colours |
| Region probe | `get_composite_rect(x,y,w,h)` | Silent write failures. **Probe before re-drawing — never re-draw in a different colour and hope** |
| Scene validation | `validate_scene(required_layers=[…])` | Missing layers/cels before you depend on them |
| Visual | `export_frame` at 8–10×, then **Read the PNG** | Everything judgement-based |
| Tiling (tileset only) | `get_composite_rect` on opposite edges | Seams |

**Then the two-stage judging both of us agreed on:**

1. **I judge first** — export, read the PNG, compare against fetched reference
   art, and iterate on anything I can see is wrong.
2. **Then kuhy judges.** Per the skill: *"Do not call your own output 'usable' —
   present it and ask."* My self-review has been measurably worse than kuhy's on
   every point of the critique log, so stage 1 is a filter, never a verdict.

---

## 8. Concrete spec for the build session

Nothing below needs re-litigating; it is the agreed scope.

**Deliverable 1 — icon set (static)**
- 12 icons, 16×16 each, one sprite per icon
- Palette: `apply_palette_preset("dawnbringer32")`
- Subjects: potion, sword, shield, key, coin, gem, ring, scroll, bomb, meat, bone, book
- One `outline_cel` pass per icon, last
- **Done when:** all 12 exported at 8×, each read and self-checked, ≥10 of 12
  approved by kuhy. Colour census shows 6–12 unique colours per icon.

**Deliverable 2 — icon animation (after 1 is approved)**
- Pick 2–3 approved icons, 4 frames each, `set_tag`, export with `export_tag`
- **Done when:** GIFs loop without a visible pop; `audit_animation` clean

**Deliverable 3 — tileset (static, then animated)**
- 5 base tiles + 2–3 transitions, 32×32, same palette
- **Done when:** edge-match probe passes on all four sides of every tile, and a
  3×3 repeat render shows no visible seam

**Where files go:** this repo holds markdown only. Generated `.aseprite`/`.png`
art goes to the session scratchpad, and anything worth keeping moves to
`~/testsAndMisc_binaries/` — the no-binaries-in-repo rule applies here as
everywhere.

---

## Appendix — sources

Everything above is grounded in files in this repo; no claim is from memory.

- [`README.md`](README.md) — tool tables, "Recommended Workflow for LLMs" (6 steps)
- [`tofix.md`](tofix.md) — what is still open. Fabricated success and the
  non-`_at` bounds drops were fixed on 2026-08-15
- [`skills/anime-pixel-art/SKILL.md`](skills/anime-pixel-art/SKILL.md) — honest status, MCP gotchas, canvas sizing
- [`skills/anime-pixel-art/references/critique-log.md`](skills/anime-pixel-art/references/critique-log.md) — verbatim human critiques
- [`skills/anime-pixel-art/references/verification-checks.md`](skills/anime-pixel-art/references/verification-checks.md) — the four deterministic checks
- [`skills/anime-pixel-art/references/sprite-recipe.md`](skills/anime-pixel-art/references/sprite-recipe.md) — the fixed 11-step procedure that works
- `aseprite_mcp/tools/palette.py` — `PALETTE_PRESETS` (the 8 presets)
- [`examples/swordsman/`](examples/swordsman/) — the one worked example: 32×32 still + 4-frame slash
