---
name: pixel-animation
description: Animate pixel art in Aseprite via the `aseprite` MCP server — looping cycles (water flow, fire, shimmer), item bobs, and any multi-frame sprite — and export it as a scaled animated GIF or filmstrip. Use when asked to animate a sprite/tile/icon, make a loop or idle bob, add frames, build a spritesheet, or to fix an animation that "doesn't move", pops at the loop point, or lost its outline when it started moving. Contains the loop-closure maths and the deterministic gates that catch animations which look fine frame-by-frame.
---

# Animating pixel art

**Status: the gates are solved; the art is not.** Motion correctness here is
*machine-checkable* — a loop either closes or it doesn't — which is what makes
this winnable in a way character art isn't. Every gate below caught a real
defect that had already passed both a tool's own success report and a visual
check.

The two failure modes that matter, and neither is visible frame-by-frame:

1. **The animation doesn't animate.** Frames are identical; the GIF is a still.
2. **The loop pops.** The wrap from last frame back to first is a different-sized
   step than the interior steps, producing a visible hitch once per cycle.

---

## The one-paragraph version

Add frames with `add_frames` (plural). Offset the moving elements by shifts that
**evenly divide the cycle**, so the wrap step equals the interior steps. Set
duration with `set_frame_duration_all`, tag with `set_tag`, and export with
`export_tag(..., scale=8)` — **one call**, which gives a scaled animated GIF
directly. Then verify the *exported GIF*, not your source frames: coalesce it and
assert every adjacent pair differs, wrap included.

---

## Step-by-step

### 1. Add frames — `add_frames`, not `add_frame`

`add_frame(filename)` takes **only** a filename and adds one frame — no index,
no count. To add several use `add_frames(filename, count, duration_ms)`.

They also live in **different modules**: `add_frame` is in `canvas`,
`add_frames` is in `animation`. Grep before assuming.

Frame indices are **1-based** everywhere (`export_frame(frame_index=1)` is the
first frame).

### 2. Make the shifts divide the cycle

This is the whole loop-closure problem, and it is arithmetic, not taste.

For an N-frame cycle over a P-pixel period, frame *i* must be offset by
`i * P / N`. The wrap from frame N-1 back to frame 0 is then the same size step
as every interior one.

Measured on a 32px water tile:

| Shifts | Interior step | Wrap step | Result |
|---|---|---|---|
| `(0, 2, 4, 6)` | 5.3 | 8.24 | **Visible pop** — wrap must jump back 6px |
| `(0, 8, 16, 24)` | 8.19 | 8.19 | **Ratio exactly 1.00** — perfect loop |

`(0,2,4,6)` looks reasonable and is wrong: it only traverses 6 of the 32 pixels,
so the loop has to leap the remaining 26. If the period is the tile width, the
shifts must reach it.

**For a non-looping motion** (a bob, a slash) this doesn't apply — but then
ping-pong or hold the extremes deliberately, and say which you did.

### 3. Counter-move the layers for flow, not sliding

Moving every element the same direction reads as the whole texture sliding
sideways. Move shadow elements one way and highlight elements the *other* way
and it reads as flow. (Wolthera, "Animating Water Tiles".)

### 4. Duration and tag

`set_frame_duration_all(filename, 180)` then `set_tag(filename, "flow", 1, 4)`.
180ms is a good default for a 4-frame ambient loop; 80–120ms for action.

### 5. Export with `export_tag(scale=N)` — one call

```
export_tag(filename, "flow", "water_flow_x8.gif", scale=8)
```

**This is the whole job.** It produces the scaled, correctly-timed, looping
animated GIF in a single native call.

> **Do not assemble the GIF from frame exports.** This session did exactly that
> — exported four frames with `export_frame(scale=8)` and stitched them with
> ImageMagick `convert -delay 18` — on the belief that no export tool took a
> scale. That belief came from checking `export_sprite`, which indeed has **no**
> `scale` parameter, and generalising from it. `export_tag` has taken `scale`
> the entire time. The assembled GIF was later verified byte-equivalent in
> dimensions and frame delays to the native one: identical 256x256, identical
> 18cs delays. The detour produced nothing but risk.
>
> **Check the specific tool's signature before concluding a capability is
> missing.** Which export tools take `scale`:
>
> | Tool | `scale`? | Use for |
> |---|---|---|
> | `export_tag` | **yes** | scaled animated GIF (or PNG sequence) |
> | `export_frame` | **yes** | one frame, scaled — visual feedback while drawing |
> | `export_spritesheet` | **yes** | filmstrip / sheet, scaled |
> | `export_sprite` | **no** | 1x export, any format |

### 6. Verify the exported GIF — and coalesce it first

The gate that matters, as an actual command:

```
magick out.gif -coalesce /tmp/scratch/coal_%d.png
# then pairwise-diff every coal_*.png, INCLUDING last-vs-first
compare -metric AE coal_0.png coal_1.png null:
```

**Coalescing is not optional.** GIF delta-optimization stores later frames
cropped to the changed region — a 4-frame 256x256 GIF really reports
`256x256+0+0`, then `256x232+0+8` three times. Diffing those raw frames compares
different-sized canvases and tells you nothing about what a viewer sees.

Fail closed: if *any* adjacent pair reads 0 differing pixels, the animation is
static at that step. Do not report success.

---

## Gates

| Gate | Threshold | Catches | How it failed for real |
|---|---|---|---|
| **Adjacent frames differ** | every pair, wrap included | Static "animations" | `audit_animation` reported a **four-identical-frame** animation as clean — it checks cels and overlaps, not motion |
| **Loop closure** | wrap step / interior step ≈ 1.0 | Popping loops | `(0,2,4,6)` shifts measured 8.24 vs 5.3; a deliberately-broken control scored 13.0 |
| **Diff the COALESCED GIF** | — | A diff that silently proves nothing | Optimized frames are cropped (`+0+8`); raw comparison is meaningless |
| **Frame margins on EVERY frame** | ≥1px all sides, all frames | A 1px bob eats the border and re-clips the outline | A static margin check passes — it only inspects the unshifted art |
| **Distinct-frame gate must be pairwise** | all N×(N-1)/2 pairs | `A,B,A,B` | An adjacent-only check passes a 2-state flicker as a 4-frame animation |

`audit_animation` returning clean is **not** evidence of motion. A tool
returning success is not evidence of anything.

---

## Traps

- **`Read` on an image DOWNSCALES IT IN PLACE.** See `references/showcase.md`.
  This corrupted a committed filmstrip in this very session. Never `Read` a file
  you are about to commit — copy it to the scratchpad and Read the copy.
- **`outline_cel` grows the art 1px on each side**, so it eats the margin a bob
  needs. Draw 16x16 ink at y=3..12 to end with 2px margins after outlining.
- Prefer the `_at` tool variants; the non-`_at` siblings silently drop
  out-of-bounds pixels while reporting success.
- `outline_cel` is in `fx`, `import_image_as_layer` in `export`,
  `validate_scene` in `quality`. Grep before assuming a module.
- Equal pixel-difference counts across *all* frame pairs is expected for a
  uniform shift (every frame is the same pattern at a different offset) — it is
  not evidence of duplication. Zero is the failure, not equality.

## Related

- `skills/item-icons/SKILL.md` — the icons being bobbed; its margin gate
- `skills/seamless-tilesets/SKILL.md` — the tiles being animated; shift maths in context
- `references/showcase.md` — exporting, tracking and displaying the result

## Sources

- Wolthera, "Animating Water Tiles part 1: Edges" — the 4-frame shift technique
- `tofix.md` — remaining known issues (fabricated success and the non-`_at`
  bounds drops were fixed on 2026-08-15)
