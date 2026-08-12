# 64x64 anime portrait — ordered procedure

Four portraits failed before this recipe existed ("nacho", "alien", "E.T.").
They failed on STRUCTURE, not proportions — by the fourth attempt the
measurements were correct and it still looked wrong. Read
`portrait-references.md` first; the six findings there are the actual content.

## Step 0 — FETCH REFERENCE IMAGES (mandatory)

OpenGameArt is the source. It is genuinely good for this and has usable
licences:

```
oga_search(query="anime portrait pixel", art_type="2d")
oga_search(query="character portrait face bust", art_type="2d", licence="cc0")
oga_submission(path=...)     # confirm the licence — OGA's filter is unreliable
oga_download(path=..., dest="portrait-refs")
```

Then **actually Read the PNG**, scaled up 2-4x with PIL if it is small.
Known-good, already credited in a local `opengameart-downloads/portrait-refs/` directory:
- Portraits 01 128x128 by alexwh (CC-BY 4.0)
- Nekomimi girl portrait by Cawfeecrow (CC0)

Reading prose about proportions is NOT a substitute. That is what produced
four alien faces.

## The six structural rules (from the references)

1. **Never a flat, mirrored, front-facing head.** Slight three-quarter with a
   tilt. Perfect bilateral symmetry IS the alien tell.
2. **No corners anywhere on the face.** Never carve a jaw with
   `erase_region` rectangles — that is exactly what produced the "squarish
   chin". Use overlapping ellipses or single-pixel row steps.
3. **Hair ≈ 60% of the head silhouette; the face is small.** Draw the hair
   mass FIRST and fit the face inside it. A big skin ball with a cap on top
   is backwards.
4. **Eyes wide and shallow, ~2:1 width:height.** Heavy dark lash mass along
   the top. Tall round eyes read as insectile.
5. **Mouth 2-3px, usually just a curve.** No open dark hole.
6. **No black outline around the FACE.** Face edges come from hair against
   skin. An outline round the jaw PLUS one round the collar is what made the
   neck look "glued on". Outline hair only.

## Step order — this order specifically

The order exists to prevent the erasure bug that killed three attempts: if you
cut the face opening out of the hair AFTER drawing the fringe, the erase takes
the fringe with it and you get a bald forehead. **Hit four times.**

1. `create_canvas` 64x64, `set_palette`, layers bottom-up:
   `body`, `skin`, `hair`, `features`.
2. **Body first.** Sloping shoulders (trapezius), so the neck can overlap
   them later and leave no seam.
3. **Face**, on `skin`: 2-3 overlapping filled ellipses — a cranium ellipse,
   a smaller one for the cheeks, a smaller one for the chin. Smooth curves,
   no rectangles. Keep it SMALL — hair will take most of the head.
4. **Neck**, also on `skin`, drawn OVER the shoulders. Hard skin-shadow band
   across its top (jaw cast shadow). No outline between neck and clothing.
5. **Hair mass**, on `hair`: crown ellipse larger than the face plus long
   side pieces framing PAST the jaw.
6. **Cut the face opening now** with `erase_region` — before any fringe
   exists.
7. **Fringe**, on `hair`, drawn AFTER the cut. Asymmetric tufts of varying
   depth; a side parting, never a symmetric bar.
8. **Sheen + strands**, lit side only.
9. **Features**, on `features`: eyes (wide/shallow), lash mass, speculars,
   brows, 2px nose, 2-3px mouth. Deliberate asymmetry.
10. `outline_cel` on **hair only**, once.
11. `export_frame` scale 8, **Read it**, check all six rules, show kuhy.

## Proportions (secondary — get the structure right first)

Eye line at 50% of head height. Head ≈ 5 eye-widths. Nose 1/3 and mouth 2/3 of
the eye-to-chin distance. These matter, but they are not what makes a portrait
read as human rather than alien — the six rules above are.

## MCP traps that bite hardest here

- `draw_pixels_at` silently drops pixels outside the cel's current bounds.
  Lead with a `draw_rectangle_at` in any new area. Verify with
  `get_composite_rect`, never by eye.
- `outline_cel` runs once per cel, ever.
- `draw_polygon` with `fill=true` fails silently on concave shapes.
