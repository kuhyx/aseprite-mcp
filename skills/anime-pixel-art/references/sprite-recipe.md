# 32x32 chibi character sprite — ordered procedure

Derived from the sprite kuhy accepted (`sprite_mcp_v5`). Follow the order.
The order matters: hair after face, outline exactly once at the very end.

Coordinates assume a 32x32 canvas, character centred on x=16.

## Layout (do not redesign this)

| Part | Rows | Notes |
|---|---|---|
| Head | y=3..16 | circle r=7 at (16,10); ~13px tall = 40% of sprite |
| Torso | y=17..22 | 10px wide at x=11..20 |
| Skirt/hips | y=23..26 | flares to x=8..23, hem line at y=26 |
| Legs | y=27..31 | two 3px legs at x=12..14 and x=17..19, GAP between |
| Shoes | y=30..31 | dark, 3px wide |
| Arms | y=18..24 | 2px wide, OUTSIDE the torso at x=9..10 and x=21..22 |

Head is 40% of height — inside the "third to half" rule.

## Steps

### 1. Setup
```
create_canvas 32x32
set_palette   (custom, see SKILL.md)
add_layer     "char"
```
One layer is enough at 32x32. Multi-layer costs more than it gives here.

### 2. Head
`draw_ellipse_at` centre (16,10) radius 7,7 filled skin base.

### 3. Torso
`draw_rectangle_at` x=11 y=17 w=10 h=6, in the shirt colour.

### 4. Skirt
`draw_polygon` filled, convex, e.g.
`[(11,23),(20,23),(23,26),(8,26)]`.
Then `draw_line_at` y=26 across the full skirt width in the DEEPEST cloth
tone — this is the hem, and it is what stops the legs looking glued on.
Add 2-3 vertical pleat lines in the shadow tone at y=24..25.

### 5. Legs, socks, shoes
Two `draw_rectangle_at` 3px wide with a **2px gap between them**. Socks in
the light tone y=27..29, shoes in the deepest tone y=30..31.

### 6. Arms and hands
`draw_rectangle_at` 2px wide, y=18..22, at x=9..10 and x=21..22 — outside the
torso block so they separate. Hands: 2x2 skin at y=23..24.

### 7. Face
- Eyes: two `draw_rectangle_at` 3w x 4h at y=10, at x=11 and x=18.
- Top row of each eye in the DARK iris tone (lid shadow).
- 1px white specular in the upper-inner corner of each.
- 1px light-iris pixel low-outer.
- Mouth: 2px in a dark red at y=15.
- Blush: 1px each side at y=13, in the blush tone.

NO lower-lid line. See the failure table.

### 8. Ribbon
2x2 at the collar (y=17..18, x=15..16): top row mid-red, bottom row dark red.
Small. A wide red block reads as lips.

### 9. Hair — LAST before outlining
This is where sprites live or die. Four tones minimum.

1. `draw_rectangle_at` x=9 y=3 w=14 h=6 in the hair BASE tone (the cap).
2. Round the top corners: erase (9,3),(10,3),(21,3),(22,3),(9,4),(22,4) to
   transparent.
3. **Shadow side**: repaint the right ~1/3 of the cap in the hair SHADOW tone,
   stepping diagonally so it follows the skull curve, not a straight vertical.
4. **Sheen band**: 5-8 pixels in the hair LIGHT tone on the upper LEFT only,
   angled along the curve. Never mirror it.
5. **Strand separation**: 4-6 single pixels of the shadow tone scattered
   through the base area, following the flow direction. This is what kills the
   "monotone" look.
6. **Fringe**: pixels at y=9 with GAPS (e.g. x=9,10,11 / 13,14 / 17,18 /
   20,21,22) so it reads as tufts, not a bar.
7. **Side locks**: down x=9 and x=22 from y=9 to y=12, tapering — final pixel
   in the deepest tone. They must STOP around y=12 (cheek level). Running them
   to the jaw produces the "hood".

### 10. Outline — ONCE
`outline_cel` with `#2C1E38`. Do not run it twice under any circumstances.

### 11. Verify
`export_frame` scale 10, **Read the PNG**, check the failure table, show kuhy.

## Accessories that stick OUT of the silhouette (bun, ponytail, hat, bag)

Draw them BEFORE `outline_cel` if you want them auto-outlined. If you add one
after outlining:

1. Establish the area with a **shape** call (`draw_rectangle_at`) — a bare
   `draw_pixels_at` outside the cel's current bounds is silently dropped.
2. Shape it and hand-place its outline pixels.
3. **Separate it from the mass behind it with a dark seam.** A bun drawn in
   the same base tone as the crown beside it is invisible even though every
   pixel is correct — verified with `get_composite_rect` while it looked
   absent. Adjacent same-colour shapes have no edge; one column of the
   deepest tone between them is what makes it read.
4. **Hair must flow INTO a bun/ponytail, or it reads as a growth.** kuhy's
   word for a bun that was merely adjacent to the crown: *"like a tumor"*.
   The fix is anatomical, not a shape tweak:
   - Converging strand pixels in the surrounding hair, angled TOWARD the tie
     point, so there is visible tension.
   - The deepest tone directly UNDER the bun base (where it meets the head) —
     this is the shadow that seats it.
   - Value gradient within the bun itself: lightest on the top-left, deepest
     at the bottom-right, same light source as everything else. A uniform
     ball is what makes it a lump.

## Adapting to a different character

Keep: the layout table, the hair procedure, one outline pass.
Change: colours, hair silhouette, garment shapes, props, accessories.

Hairstyle is the strongest identity signal at this size — vary the cap shape
and lock length before anything else. Garment silhouette (skirt vs trousers vs
coat) is second. Facial features barely differ between characters at 32x32;
do not try to carry identity there.
