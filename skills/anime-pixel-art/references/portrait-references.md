# What real anime pixel portraits actually look like

**Studied from real CC0/CC-BY reference art, not from text tutorials.** Reading
proportion rules in prose and translating them to pixels myself produced four
failed portraits in a row ("nacho", "alien", "E.T."). Looking at actual
portrait art explained the failures in one pass. **Always fetch reference
IMAGES before drawing a portrait** — the OpenGameArt MCP (`oga_search`,
`oga_submission`, `oga_download`) has usable ones.

References used:
- Portraits 01 128x128 by alexwh (CC-BY 4.0) —
  https://opengameart.org/content/portraits-01-128x128
- Nekomimi girl portrait by Cawfeecrow (CC0) —
  https://opengameart.org/content/nekomimi-girl-portrait

## The eight structural findings

These are about STRUCTURE, not proportions. My proportions were correct by the
time I measured them and the result still looked alien, because all eight of
these were wrong.

1. **Never a flat, front-facing, mirrored face.** Every reference portrait is
   a slight three-quarter view with a head tilt. Perfect bilateral symmetry
   is itself the "E.T./alien" tell. Offset the features: one eye slightly
   larger/closer to the centre line, the nose off-axis, the hair parting
   asymmetric.

2. **No corners anywhere on the face.** The jaw is a smooth continuous curve
   narrowing to a soft point. Carving a jaw with `erase_region` rectangles
   leaves literal square steps — kuhy: *"those weird squarish chin - whats up
   with that"*. Build the face outline row by row with single-pixel width
   changes, or draw it with `draw_path`/small ellipses. Never rectangles.

3. **Hair is ~60% of the head silhouette; the face is small.** In the
   references the hair mass dominates: it rises above the crown, frames past
   the jaw on both sides, and often falls below the chin. My faces were a big
   skin sphere with a small cap perched on top — backwards.

4. **The head widens GRADUALLY.** Measured on the reference: 7px wide at the
   crown, reaching 91px only ~40 rows later. A filled circle reaches full
   width in a handful of rows and reads as a ball. Taper the top.

5. **Eyes are WIDE and SHALLOW, not tall blocks.** Roughly 2:1 width:height,
   with a heavy dark lash mass along the top edge, and the iris occupying most
   of the opening. Tall round eyes read as insectile.

6. **The mouth is tiny — 2-3px, often a single curved line.** No open dark
   hole. kuhy on an open mouth: *"makes her look stupid"*, and on a small one
   at the wrong scale: *"looks weird and is too small compared to eyes"*. The
   safe default is a small closed curve.

7. **No black outline around the FACE.** Face edges are defined by hair
   against skin, and by shading. Outline the outer silhouette only. A dark
   line around the jaw plus another around the collar is what produced the
   "glued on" neck.

8. **Skin uses very few values but strong hue variation.** The references use
   an almost flat mid-tone with a distinctly warmer/darker tone for the jaw
   and neck shadow — not a subtle 1-step darker.

## Three-quarter view — how to actually build it

Front-facing is not an acceptable default. kuhy: *"we already established that
three-quarter view is superior, we dont want front facing"*. Breaking symmetry
with slightly-unequal eyes is NOT a substitute for turning the head.

From the reference crop plus drawing references:

- **Shift the face centre line toward the direction of the turn.** Everything
  (nose, mouth, the gap between the eyes) moves with it. The far side of the
  face gets compressed.
- **The near eye is large and fully visible. The far eye is NARROWER** —
  roughly 2/3 the width — and sits hard against the face's silhouette edge,
  partly cut off by it. There is no cheek beyond the far eye.
- **Eye/nose/mouth lines follow the head tilt** — they are not horizontal.
- Eyes are **almond**, not rectangles: dark heavy upper lash, thin lower
  line, a rounded iris. A filled rectangle reads as a screen, not an eye.
- Bang tufts are **thin spikes of varying length**, 1-2px wide, not blocks.

## Neck: there is almost none

kuhy called the neck "way too long" and "attached in an awkward way" three
times across four portraits. The reference shows why: **the neck is barely
visible at all**. The chin sits close above the collar, hair falls in FRONT of
the shoulders on both sides, and what little neck shows is 2-4 rows in a
narrow gap. A 10-12px exposed neck column is the bug.

## Collar / clothing

The reference collar is built from **overlapping angled bands with visible
edge highlights** — a lapel line, a lighter trim line following it, the shirt
V beneath. Two flat dark polygons overlapping produce the shapeless navy blob
kuhy flagged. Give every garment piece its own edge line in a lighter value.

## Neck / shoulder junction

kuhy called it "glued" three times. In the references the neck is NOT a
rectangle butting into a collar:
- The neck is partially hidden by hair falling in front of the shoulders.
- The trapezius slopes from the jaw outward — there is no visible horizontal
  seam where neck meets torso.
- No outline row between neck and clothing.

Draw the shoulders first, then the neck OVER them, then hair over the neck.

## Practical order

1. Fetch and LOOK at 2+ reference portraits.
2. Hair silhouette first (it is most of the shape), not the face.
3. Face as a small soft shape inside it, built row by row.
4. Features, with deliberate asymmetry.
5. Outline the outer silhouette only.
