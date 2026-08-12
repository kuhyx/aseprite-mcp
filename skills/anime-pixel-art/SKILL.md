---
name: anime-pixel-art
description: Draw anime/chibi character sprites and portraits in Aseprite via the `aseprite` MCP server. Use when asked to draw or make a character sprite, chibi, pixel portrait, game character, NPC, or anime face/hair — or to fix pixel art that "looks wrong" (reads as old, crying, alien, wearing a hood/helmet, or flat and monotone). Contains a fixed step-by-step sprite procedure that reliably produces a usable 32x32 character.
---

# Anime / chibi pixel art in Aseprite

## Rule 0: SEARCH THE WEB FIRST. Every time. No exceptions.

**Before drawing anything, and again before fixing anything, run a web search.**
This is mandatory, not advisory. kuhy made it a standing requirement because it
is what actually worked: in the session that produced this skill, essentially
every genuine fix came from a search result, and essentially every failure came
from me reasoning about pixels unaided.

Two triggers, both compulsory:

1. **"Draw X"** → search for how X is drawn in pixel art *before the first
   pixel*. Query the specific subject, not generalities: `pixel art
   <subject> tutorial proportions`, `how to draw <feature> pixel art`.
2. **"That's wrong / fix Y"** → search for that *specific defect* before
   touching the file. Search kuhy's own words — they are describing a known
   named failure mode more often than not.

Evidence this pays:
- "she looks old / eyebags" → a search found that a flat horizontal lower lid
  is *literally the standard way to draw a tired eye*. Unguessable.
- "nacho / guitar pick head" → "a rounded cranium, a narrower jaw, and a
  defined chin" — three parts, not one curve. That single line fixed it after
  three failed rounds of tuning.
- "hair looks monotone" → pillow shading is a named beginner error.
- "the bun looks like a tumor" → hair must *flow into* the tie with converging
  tension lines and a dark shadow under the base.

**For PORTRAITS and anything anatomical, text is not enough — fetch reference
IMAGES.** Four portraits failed in a row while I read prose about proportions
and translated it to pixels myself. One look at real portrait art explained
every failure at once, and none of the causes were proportional.

**OpenGameArt is the reference source.** It is genuinely good for this:

```
oga_search(query="anime portrait pixel", art_type="2d")
oga_search(query="character portrait face bust", art_type="2d", licence="cc0")
oga_submission(path=...)   # ALWAYS confirm licence — OGA's filter is unreliable
oga_download(path=..., dest="portrait-refs")
```

Then **Read the PNG** (scale it up with PIL if small). Already downloaded and
credited in a local `opengameart-downloads/portrait-refs/` directory:
- Portraits 01 128x128 by alexwh (CC-BY 4.0)
- Nekomimi girl portrait by Cawfeecrow (CC0)

Per kuhy's standing rule, every asset gets a credit entry in the same edit that
adds the file — `oga_download` writes CREDITS.md automatically.

Also: verify tutorial claims against the actual MCP tool list. A Gemini-written
guide that started this work cited a "legendary frame-by-frame" article that
contains no pixel counts, and invented MCP tool names wholesale.

**Draw with the MCP tools.** `draw_rectangle_at`, `draw_line_at`,
`draw_ellipse_at`, `draw_circle_at`, `draw_polygon`, `draw_pixels_at`,
`fill_area_at`, `erase_region`, `outline_cel`. Do NOT generate the image in a
script and bulk-push it — that is compiling, not drawing, and kuhy has asked
for MCP directly. `draw_pixels_at` is the detail brush (a specular, a mouth,
strand separation), not a delivery mechanism.

Start from `references/sprite-recipe.md` — it is a literal ordered procedure
for a 32x32 character that has produced an approved result. Deviate only for
what makes the character distinct (silhouette, colours, props).

## Non-negotiables

**Silhouette first.** If the silhouette is not readable, no shading fixes it.
Squint test: if you cannot tell what it is, simplify.

**2-3 colours per material, 6-12 total.** More colours at small sizes create
noise, not detail. Each colour must be distinguishable when squinting — two
medium blues read as one.

**Never pillow-shade.** Shading inward from the outline all the way around is
the single most common tell of amateur pixel art. Light comes from ONE
direction (top-left by convention): the opposite side gets shadow, and the
sheen band is asymmetric. A symmetric highlight reads as a headband, not light.

**No 1px protrusions.** Arms and legs at 1px thickness look like wires. 2px
minimum, 3px preferred at 32x32.

**Outline exactly once, at the end.** See the MCP gotchas below.

## Proportions (verified against references)

- **Chibi: 2-2.5 heads tall.** The head takes **a third to a half** of the
  total sprite height. This is not a compromise — big heads carry expression
  and read at small sizes. Do not "fix" a chibi by making it 3.5 heads; that
  makes it a small adult and loses the appeal.
- Realistic figures are a 6-head model (8 heads is too elongated for pixel art).
- Neck width: **1/2 to 2/3 of a head width**.
- Eyes sit on the vertical midline of the head, separated by ~1 eye width.

| Canvas | Use | Eye size |
|---|---|---|
| 16x16 | tiny sprite | 2x2 px |
| 32x32 | game sprite (chibi) | 3x4 px |
| 64x64 | portrait / bust | 7-9 px round |

## Honest status: sprites work, portraits do not

**Sprites**: the recipe in `references/sprite-recipe.md` is proven. It produced
an approved schoolgirl and then transferred cold to an "office lady" with only
colour/hair/garment changes. Follow it literally.

**Portraits**: NOT solved. Eight-plus attempts across 32/64/128px, all
rejected. Do not promise a good portrait. What was learned:

- **Resolution is not the problem.** Downscaling the 128px reference to 64px
  still looks good, so 64px is sufficient for a competent portrait. Blaming
  canvas size is a wrong diagnosis.
- **Almost every portrait failure was a TOOL/ORDERING bug, not a drawing
  judgement bug**: the fringe erased by the face-cut (4x), the mouth lost to
  cel bounds (4x), `outline_cel` run twice, concave `draw_polygon` silently
  failing. The sprite recipe succeeds because it is a fixed ordered procedure;
  the portrait guidance is principles that get reinterpreted each time, so the
  same ordering mistakes recur.
- **At 32px, identity lives in hairstyle and garment silhouette** and the face
  is a few pixels. At 128px the face IS the artwork, and faces are the hardest
  subject. That asymmetry — not pixel count — is why sprites land and
  portraits do not.
- **The hair should be much darker than the face, cover nearly all the
  forehead, and the face should be a small bright shape low in the frame.** A
  large pale dome up top is the "potato" failure kuhy names repeatedly.

If asked for a portrait: say plainly that this is unsolved, offer a sprite
instead, or expect several rounds of correction.

## Portraits: the six structural rules

Portraits fail on structure, not proportions. Full detail plus sources in
`references/portrait-references.md`; procedure in `references/portrait-recipe.md`.

1. **Never a flat mirrored front view** — slight three-quarter with a tilt.
   Perfect bilateral symmetry IS the "alien/E.T." tell.
2. **No corners on the face** — never carve a jaw with `erase_region`
   rectangles; that is the "squarish chin".
3. **Hair ≈ 60% of the head silhouette, face small** — draw hair first, fit
   the face inside. A skin ball with a cap on top is backwards.
4. **Eyes wide and shallow (~2:1)**, heavy lash mass on top. Tall round eyes
   read as insectile.
5. **Mouth 2-3px, usually a curve.** No open dark hole.
6. **No outline around the FACE** — hair against skin defines the edge. Jaw
   outline + collar outline = the "glued on" neck.

## Face failure modes

Each of these shipped and was caught by kuhy, not by me. They are symptom
names — match the complaint to the cause.

| Complaint | Cause | Fix |
|---|---|---|
| "she looks old", "eyebags" | full-width horizontal dark line under the eye — literally how a tired eye is drawn | no full-width lower lid; 2px lash tick at the OUTER corner only |
| "looks like she is crying" | lightest iris value on the bottom rim, pooling against that dark lid | iris dark at TOP (lid casts shadow), lightest band ABOVE the bottom row |
| "burka", "grandma hood" | hair enclosing the jaw | side locks STOP at cheek level; jaw and chin touch background |
| "purple minecraft helmet" | bang mass with a flat straight bottom edge and a rectangular top | carve pointed tufts of varying depth into the bottom; round the top corners |
| "nacho", "guitar pick", "alien" | head derived from ONE smooth curve (ellipse + taper) | cranium / cheeks / jaw as three parts — see below |
| "forehead too big" | bangs lifted too high off the brows | fringe should sit close above the eyes; forehead is a narrow band, not a dome |
| grey headband across the hair | highlight mirrored symmetrically | sheen only on the lit side |
| dashed line across forehead | bang cast-shadow computed independently of where hair actually is | derive shadow row from the lowest hair pixel per column |
| invisible brows | brows drawn in the hair colour | use a skin-shadow tone, clear of both fringe shadow and lash line |
| ribbon reads as lips | wide horizontal red block low on the chest | small bow AT THE COLLAR with a visible knot |
| "mouth makes her look stupid" | large open mouth, and/or too close to the chin | small closed or barely-open mouth, placed ~70% of eye-to-chin, never in the jaw shadow band |
| neck "glued on" with a thick black line | neck outline and collar outline stacking into a bar | let the neck meet the collar with ONE outline row, or none — do not outline both |

### Head construction

Never one smooth curve. Three parts with visible transitions:

1. **Rounded cranium** — a circle; widens fast then holds.
2. **Cheeks** — width barely changes for several rows. This flat run is what
   makes it read round. Without it you get a diamond.
3. **Jaw + chin** — a distinct inward turn, then a SHORT chin. A higher,
   compact chin reads younger and rounder.

Sanity check: the widest half-width repeats for **4+ rows**. One-row peak =
pointed.

## MCP gotchas (all found the hard way)

- **`draw_polygon` with `fill=true` silently fails on concave shapes.** A
  zig-zag fringe as one polygon writes NOTHING and returns success. Use convex
  pieces or stacked rectangles. Verify with `get_composite_rect`.
- **Run `outline_cel` exactly ONCE per cel.** A second pass outlines the first
  outline: edges thicken, deliberate gaps fill in (a thigh gap vanished), and
  any dark line you drew inside the sprite (a skirt hem) gets traced as if it
  were a silhouette edge. To fix something after outlining, hand-place outline
  pixels or clear the cel and rebuild.
- **`draw_pixels_at` silently drops pixels outside the cel's current bounds**
  and still reports success. This is THE most frequently-hit trap in this
  workflow — it cost four separate failed attempts across two portraits (a
  mouth twice, a bun, a fringe). A cel only covers the bounding box of what
  has been drawn on it so far; anything beyond that is discarded silently.
  **Rule: to add a feature in a NEW area of a layer, always lead with a
  `draw_rectangle_at` covering that area, then refine with `draw_pixels_at`.**
  If something does not appear, do not re-draw it in a different colour and
  hope — read the region with `get_composite_rect` and confirm whether the
  pixels exist at all.
- **Never cut a face hole out of hair AFTER drawing the fringe.** The erase
  takes the fringe with it and you get a bald forehead. Either cut the hole
  first and draw the fringe after, or draw the fringe on a higher layer.
  Hit twice.
- **`outline_cel` expands the cel** and can cover regions erased on other
  layers. Outline LAST; re-check anything cut with `erase_region`.
- **Layer order is bottom-up**; `reorder_layer` position 1 is the bottom.
- **`generate_color_ramp` overshoots at the dark end for skin** — a ramp around
  `#F0C8A0` returned mustard `#EBBA45` as the darkest step. Hand-pick skin;
  the tool is fine for hair, cloth, eyes.
- **Built-in palette presets are all retro console palettes.** None have usable
  anime skin. Build a custom palette.

## Palette

Outline `#2C1E38` (dark purple — **never pure black**).

| Role | Deepest | Shadow | Base | Light |
|---|---|---|---|---|
| Skin | `#8C5A4A` | `#C98D6B` | `#F2C9A6` | `#FFE6D0` |
| Hair (plum) | `#26192C` | `#4A3959` | `#6A5C82` | `#8E89A2` |
| Navy cloth | `#171736` | `#303764` | `#4D5F8F` | `#768DAD` |
| Iris (teal) | `#1E4068` | — | `#3A7CA5` | `#74B1C4` |

Accents: blouse `#E8E8F0`, white `#FFFFFF`, red `#C43F5A` / `#7A2E42`,
blush `#E89A8C`.

Recolour freely per character — keep the 4-step structure and the value gaps.
Use `generate_color_ramp` for new hair/cloth colours.

## Verify before showing

1. `export_frame` at scale 8-10 and **Read the PNG**. A successful MCP call
   only proves pixels were written, not that they look right.
2. Check against the failure-mode table above by name.
3. **Show the human and let them judge.** Every entry in that table was caught
   by kuhy after I had already judged the image acceptable. Do not call your
   own output "usable" — present it and ask.

## References

- `references/sprite-recipe.md` — the ordered 32x32 procedure. Start here.
- `references/critique-log.md` — verbatim critiques, for matching symptoms.
