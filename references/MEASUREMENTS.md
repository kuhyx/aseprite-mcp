# 16x16 RPG Inventory Icons — Measured Pixel Construction Data

**Everything below is MEASURED**, not invented. Every ASCII grid was produced
programmatically by `measure.py` (in this directory) reading the actual PNG
pixels via PIL. No grid in this file was drawn by hand or inferred.

Reproduce any grid with:

```
cd <this dir>
python3 -W ignore measure.py roguelike-items/roguelikeitems_1.png RL <cx>,<cy>
```

### What is measured vs. what is interpreted

- **Measured (trust these):** every ASCII grid; every bbox, margin, color
  count, hex value, and black-pixel percentage — all produced by code.
  **Additionally code-verified by a second pass:** the gem ramp, potion
  per-row spans, sword blade stroke and guard row, key bow-hole size, ring
  hole size, round-shield run-lengths, heater taper, and the
  silhouette-outline test. Those checks caught and corrected **four** by-eye
  errors of mine, which is why they are flagged explicitly.
- **NOT independently re-measured — by-eye readings of the grids above,
  treat with caution** (my by-eye error rate in this doc ran ~4 in 6):
  potion cork height and neck wall widths; scroll roll heights and the skew
  x-values; bone shaft width and knob sizes; book vertex positions, page-wedge
  thickness, gold-trim placement and bookmark size; the coin highlight pixel
  count/percentage. The grids themselves are exact — **if any of these matter,
  count them off the grid rather than trusting my sentence.**
- **Interpreted (my reading of the measurements):** part *names* ("this is the
  cork", "this is the crossguard"), the material/lighting rationale, and the
  10 summary rules at the bottom. These are inferences from the grids —
  reasonable, but they are my labels, not the artist's.
- **Not present:** the bomb. Stated plainly, no grid invented.

---

## Sources & Licenses

### PRIMARY (the 12-subject grids come from this one sheet)

**Roguelike/RPG Items** by **Joe Williamson** (Twitter @JoeCreates)
- <https://opengameart.org/content/roguelikerpg-items>
- File: `roguelike-items/roguelikeitems_1.png` — 208x240 px = **13 x 15 cells of 16x16**
- **License: OGA lists BOTH "CC-BY-SA 3.0" and "CC0".** The sheet itself has
  "Creative Commons Attribution-ShareAlike" *rendered into the bottom of the
  image*. **Treat it as CC-BY-SA 3.0** — the stricter of the two, and the one
  the author baked into the art. Do not assume CC0.
- Attribution line: `Roguelike/RPG Items by Joe Williamson (CC-BY-SA 3.0, CC0) — https://opengameart.org/content/roguelikerpg-items`

### SECONDARY — used for the cross-validation section

**16x16 Assorted RPG Icons** by **Shade** — **CC0** (single license, clean)
- <https://opengameart.org/content/16x16-assorted-rpg-icons>
- `assorted-rpg-icons/16x16 Assorted RPG Icons/{weapons,potions,consumables,chests,books,armours}.png`
- **3 icons measured** (sword, potion, book) as an independent-artist control.
  See "CROSS-VALIDATION" below. **This is the clean-CC0 source** — if license
  purity matters to you, prefer these grids over the Williamson ones.

### TERTIARY (inspected for the bomb, nothing measured)

**Tiny Dungeon** by **Kenney** — **CC0 1.0** (confirmed in the pack's own
`License.txt`)
- <https://kenney.nl/assets/tiny-dungeon>
- `kenney_tiny-dungeon.zip` → `kenney/Tilemap/tilemap_packed.png` (12x11 cells)
- Downloaded and viewed in full solely to settle the bomb question. No bomb.

> **Usage note (yours):** you stated you are measuring proportions/conventions
> for original art, not copying pixels. That is not a derivative work in any
> meaningful sense — but the CC-BY-SA status above is recorded as asked.

---

## Coverage: what I actually found

| Subject | Found | Cell (col,row) | Notes |
|---|---|---|---|
| potion | YES | (8,4), (9,4) | full flask row 4-5 |
| sword | YES | (0,8), (0,7), (1,7) | diagonal, hilt bottom-left |
| shield | YES | (6,11) round, (9,11) heater | both measured |
| key | YES | (11,3) | horizontal |
| coin | YES | (8,3) pile, (0,4) stack | **no single flat coin in set** |
| gem | YES | (3,3) red, (0,3) pink | cut-gem cluster |
| ring | YES | (6,2) gold, (10,2) silver band | |
| scroll | YES | (9,3) | |
| **bomb** | **NO** | — | **not present in either set. No grid given. Not fabricated.** |
| meat | YES | (10,3) | raw meat cut |
| bone | YES | (11,11) | |
| book | YES | (7,12) green, (8,12) red | closed, 3/4 angle |

**11 of 12 measured. Bomb is absent — see the "Bomb" section for what I can
and cannot say.**

---

## Cross-cutting conventions (measured across all 12 grids)

These are the numbers that tutorials don't give you.

> **Scope warning:** this section is measured across 15 cells of **one
> artist's one sheet**, and several of those are variants of the same object.
> It is n=1 on *style*. The **CROSS-VALIDATION** section near the end tests
> each of these against a second artist and marks which ones are genuinely
> universal versus Williamson's personal taste. **Read that table before
> treating any number here as a law.**

### Margins — the object does NOT sit inside a safe border

| Icon | bbox (x0,y0,x1,y1) | w x h | margins L/T/R/B |
|---|---|---|---|
| ring | (2,2,14,14) | 13x13 | 2/2/1/1 |
| key | (0,4,15,11) | 16x8 | 0/4/0/4 |
| sword | (0,0,15,15) | 16x16 | 0/0/0/0 |
| potion | (2,0,14,15) | 13x16 | 2/0/1/0 |
| round shield | (1,0,15,14) | 15x15 | 1/0/0/1 |
| scroll | (0,1,15,14) | 16x14 | 0/1/0/1 |
| meat | (0,2,14,14) | 15x13 | 0/2/1/1 |
| bone | (3,3,12,13) | 10x11 | 3/3/3/2 |
| book | (0,0,15,15) | 16x16 | 0/0/0/0 |
| gem (red) | (1,2,14,14) | 14x13 | 1/2/1/1 |
| coin pile | (0,4,15,12) | 16x9 | 0/4/0/3 |

**Key finding:** margins are **0-2 px, driven by the object's own silhouette,
not by a uniform border.** Long-axis items (sword, key, book, scroll) go
**edge to edge, 0 margin** on their long axis. The only icon with a real
all-round margin is the bone (3/3/3/2) — because it is a small object, not
because of a rule. There is no "1px safe area" convention here. Fill the cell.

### Color count

Measured unique opaque colors (including the black outline):

```
bone          4     coin stack    4     key           5     meat          5
coin pile     5     gem (red)     6     silver band   6     ring          7
sword         7     potion        9     scroll        9     round shield 10
book         13
```

**In Williamson's set, 4-9 is the normal band and 13 the ceiling** (the book,
which carries two materials + a bookmark + gold trim). A typical item is
**1 black + 3-5 shades of one hue + 1-2 accent colors.**

> **But see CROSS-VALIDATION below: this ceiling is NOT universal.** Shade
> draws the same subjects at the same size using **7 (sword), 15 (book) and
> 19 (potion)** colors. Treat color count as a style budget you choose and
> hold consistent, not as a limit imposed by the 16x16 size.

### Outlining — this is the single most important convention

**Every icon has a FULL, PURE-BLACK (`#000000`) outline.** Not selective, not
colored, not dark-hue. Black `#000000` appears in the palette of all 13
measured cells.

Black as a share of the icon's opaque pixels:

```
key          59%    sword        51%    bone         51%    potion       50%
ring         46%    coin pile    33%    coin stack   32%    scroll       30%
meat         28%    gem          25%    book         24%    round shield 23%
```

**Reading:** thin/linear items are ~50-60% black (outline dominates the mass);
chunky/round items are ~23-33%. Budget roughly **a quarter of a chunky icon
and half of a thin icon as outline.**

The outline is **1px and closed** — it fully encircles the silhouette, and it
also runs *internally* to separate distinct parts (e.g. the key's bit teeth,
the book's cover vs pages, the sword's guard vs blade). Internal black is used
as a **separator between materials**, which is why the black share is so high.

---

## POTION — cell (8,4), also (9,4)

```
......#####.....
......#ox=#.....
.....#**=*@#....
.....#*@*@@#....
......#*#@#.....
......#*#@#.....
.....#*##@#.....
....#*##@#@#....
...#*+##@@#@#...
..#&%++++++#@#..
..#&&&%%#####@#.
..#&&&&&&&###@#.
..#%%%%%%%##@#..
...#%%%%%###@#..
....#####@@@#...
.....#######....
palette: #=#000000  @=#99b1b5  %=#7d7660  &=#b4ae9c  *=#dee6e7
         +=#4c4c4c  ==#787b37  o=#929643  x=#b0b559
```

Same shape, purple liquid, at (9,4):

```
......#####.....
......#sax#.....
.....#==x=@#....
.....#=@=@@#....
......#=#@#.....
......#=#@#.....
.....#=##@#.....
....#=##@#@#....
...#=o++@@&@#...
..#*%oooooo&@#..
..#***%%&&+&+@#.
..#*******&&+@#.
..#%%%%%%%+&@#..
...#%%%%%&++@#..
....#&++&@@@#...
.....#######....
palette: #=#000000  @=#99b1b5  %=#7d7660  &=#4f0160  *=#b4ae9c
         +=#601271  ==#dee6e7  o=#732584  x=#787b37  s=#929643  a=#b0b559
```

**Measured potion geometry** (the flask is drawn on a diagonal/3-4 view, which
is why left and right edges differ):

Measured span per row (code-verified):

```
row  0:  5 px (x6-10)   cork cap        row  8: 10 px (x3-12)  shoulder
row  1:  5 px (x6-10)   cork            row  9: 12 px (x2-13)  shoulder
row  2:  7 px (x5-11)   cork flare      row 10: 13 px (x2-14)  body (widest)
row  3:  7 px (x5-11)   cork flare      row 11: 13 px (x2-14)  body (widest)
row  4:  5 px (x6-10)   neck            row 12: 12 px (x2-13)  body
row  5:  5 px (x6-10)   neck            row 13: 11 px (x3-13)  body
row  6:  6 px (x5-10)   neck            row 14:  9 px (x4-12)  base
row  7:  8 px (x4-11)   neck->shoulder  row 15:  7 px (x5-11)  base
```

- **Total bbox: x 2-14, y 0-15 — 13 wide x 16 tall. Uses the FULL vertical cell.**
- **Cork:** rows 0-3, x 5-11. Cork body (the `o`/`x`/`=` olive pixels + white
  highlight) occupies **rows 1-3 → cork height = 3px**, sitting on top of a
  black cap line at row 0.
- **Neck:** rows 4-7. The neck is the narrowest part: at rows 4-6 the glass is
  literally **1px of light glass (`*`) + 1px black + 1px right-side glass
  (`@`)** — i.e. an **interior neck width of 1px per wall, ~3px total
  including the black divider.** The neck reads as two parallel 1px strokes.
- **Shoulder/flare:** rows 7-9, spans 8 → 10 → 12 px. The **shoulder flares
  out at ~2px per row over 3 rows** — an abrupt cone, not a gentle curve.
- **Body:** rows 10-13, **max span 13px at rows 10-11**, tapering to 11px by
  row 13 → **body width 13px, body height ~4-5 rows.**
- **Widest:body-neck ratio = 13:5** (13px body vs the 5px neck), i.e. the body
  is about **2.6x the neck width.**
- **Liquid fill:** the `&` mid-tone fills rows 10-11 and `%` rows 11-13 — the
  liquid occupies the **bottom ~4 of the 6 body rows**, with a flat top edge
  at row 10, leaving ~2 rows of empty glass headroom.
- **Highlight:** `*` / `dee6e7` runs down the **left** neck wall (rows 2-8) as a
  continuous 1px vertical stroke — the glass highlight is a *line*, not a dot.

---

## SWORD — cell (0,8) (clean diagonal), (0,7) and (1,7) variants

Cleanest sword, pointing up-right, hilt bottom-left:

```
.............###
............#@%#
...........#@@&#
..........#@@&#.
.........#@@%#..
........#@@%#...
.......#@@%#....
......#@@%#.....
.....#@@%#......
....#@@&#.......
...#+@&#........
...#=+#.........
..#*##..........
##*#............
#*#.............
###.............
palette: #=#000000  @=#dcdbe6  %=#b7b5cc  &=#9c9aba  *=#606060  +=#886c0f  ==#caa217
```

With a crossguard + pommel, cell (0,7):

```
................
................
...........###..
..........#&@#..
.........#&@o#..
........#&*o#...
....#..#&*@#....
...#%##&*@#.....
....#%=*@#......
.....#%=#.......
....#=#%#.......
...#+#.#%#......
.##+#...#.......
.#+#............
..##............
................
palette: #=#000000  @=#b7b5cc  %=#caa217  &=#dcdbe6  *=#808080  +=#606060  ==#9c9aba
```

**Measured sword geometry (cell (0,8)):**

- **Orientation: 45-degree diagonal, tip at top-RIGHT (x13-15, y0), hilt at
  bottom-LEFT (x0-2, y13-15). Occupies the full 16x16 — bbox (0,0,15,15),
  0 margin on every side.** This is the universal trick: a sword is longer
  than 16px, so it is drawn on the diagonal to buy `16*sqrt(2)` ≈ 22px of
  length.
- **Blade stroke: exactly 5px wide measured horizontally, held constant for
  rows 2-10** (code-verified: every row from 2 to 10 has span=5). The row
  pattern is literally `#@@%#` — **black, light `dcdbe6`, light `dcdbe6`,
  mid `b7b5cc`, black**. So it is **3px of metal (2 light + 1 mid) between two
  1px black edges**, measured on the horizontal; perpendicular to the blade
  axis that is ~2px of metal. The **light/mid split *is* the entire blade
  shading model** — highlight on the upper-left face, shadow on the
  lower-right.
- **Blade length:** rows 0-10 along the diagonal → **11 rows of blade**
  (~15px of true diagonal length), with the tip taking rows 0-1 as it narrows
  from 3 to 4 to 5px.
- **Crossguard:** at **rows 11-12** (`#=+#` / `#*##`), where the span drops
  from 5 to 4 — i.e. the guard sits at **~72% of the way down the cell
  (y=11 of 16)**, leaving 3 rows for grip and pommel. It is rendered in gold
  (`caa217`/`886c0f`) against the silver blade. **In this compact variant the
  guard does NOT extend beyond the blade stroke** — it is signalled purely by
  the colour change to gold, not by width. (The (0,7) variant is the one with
  a protruding guard.)
- In the (0,7) variant the crossguard is at **rows 6-8** and extends
  perpendicular to the blade by ~3px each way, with the **pommel at rows
  12-14**. So across variants: **guard at 45-75% depth, pommel in the last
  2-3 rows.**
- **Grip/pommel:** rows 13-15, drawn in dark grey `606060` — the darkest value
  in the icon, so the hilt reads as a separate material from the blade.

---

## SHIELD — round (6,11) and heater (9,11)

### Round shield (6,11) — bbox (1,0,15,14), 15x15, 10 colors

```
......#####.....
....##@===@##...
...#@+%%+%%+@#..
..#@%*&&@%&*%@#.
..#=&*&*@*&*&=#.
.#=*&&o*+%o&&*=#
.#@%&*%x@+%*&%@#
.#=+@@+@+s+@@+=#
.#@%**%xsx%**%@#
.#@%&&o%+%o&&%@#
..#=&*&*@*&*&=#.
..#@%*&*@%&*%@#.
...#@+%%+%%+@#..
....##+@+@+##...
......#####.....
................
palette: #=#000000  @=#c0c0c0  %=#5e4022  &=#b07840  *=#885c31  +=#808080
         ==#e9e9e9  o=#c28d58  x=#606060  s=#292929
```

**This is the canonical 15px circle at this size — memorize the run lengths.**
Per row, the width of the *filled* span (including its black outline):

```
row  0:  5 px   (x6-10)
row  1:  9 px   (x4-12)
row  2: 11 px   (x3-13)
row  3: 13 px   (x2-14)
row  4: 13 px   (x2-14)
row  5: 15 px   (x1-15)
row  6: 15 px
row  7: 15 px   <- widest, vertical centre
row  8: 15 px
row  9: 15 px
row 10: 13 px   (x2-14)
row 11: 13 px
row 12: 11 px   (x3-13)
row 13:  9 px   (x4-12)
row 14:  5 px   (x6-10)
```

Half-run sequence from the pole: **5, 9, 11, 13, 13, 15, 15, 15, 15, 15, 13,
13, 11, 9, 5.** That is the circle formula for this size: the first row is a
5px cap, then it jumps by 4, then by 2, 2, then flat.

- The metal rim is a **1px `c0c0c0`/`e9e9e9` ring just inside the black
  outline**; the wood field is browns (`5e4022`..`c28d58`); the boss is the
  dark `292929`/`606060` cluster dead centre at (7-8, 7-8).
- **Symmetry: the shield is mirror-symmetric left/right about x=8**, and very
  nearly top/bottom about y=7.

### Heater shield (9,11) — bbox (1,0,14,15), 14x16

```
.##..........##.
.#@##......##@#.
.#@**######**@#.
.#@*&**%%&*&&@#.
.#@*&&@%%@&&&@#.
.#%***@%%@&**%#.
.#%++*@%%@*++%#.
.#%%++++++++%%#.
.#@@%%%++%%%@@#.
.#@*@@@%%@@@&@#.
..#@&&@%%@&&@#..
..#@@&@%%@&&@#..
...#@@@%%@&@#...
....#@@%%@@#....
.....##%%##.....
.......##.......
palette: #=#000000  @=#272f61  %=#5663ba  &=#384389  *=#4251a4  +=#858ecd
```

**Measured heater geometry** (code-verified spans):

```
rows 0-9 : 14 px (x1-14)   <- straight parallel sides, 10 rows
row 10   : 12 px (x2-13)
row 11   : 12 px (x2-13)
row 12   : 10 px (x3-12)
row 13   :  8 px (x4-11)
row 14   :  6 px (x5-10)
row 15   :  2 px (x7-8)    <- point
```

**The top 10 of 16 rows (62%) are a plain rectangle at full 14px width; the
taper is the bottom 6 rows (37%)**, shrinking 2px per row (with one repeat at
12px). The point is 2px wide, not 1. A vertical light stripe (`5663ba`) runs
the full height at x=7-8, and a horizontal band (`858ecd`) at rows 6-7 —
together a cross device.

---

## KEY — cell (11,3)

```
................
................
................
................
..###...........
.#**%#..........
#*@#@%##########
#%#.#@%%%**%*%%#
#@#.#@#####@@@##
#&@#@&#...#@#@#.
.#&&&#....#&#&#.
..###.....####..
................
................
................
................
palette: #=#000000  @=#caa217  %=#eac64a  &=#886c0f  *=#ffffaa
```

- **bbox (0,4,15,11) — 16 wide x 8 tall. Full width, vertically centered with
  4px of air above and below.** A key is a horizontal icon; it does not try to
  fill the square.
- **Bow (the ring/handle): x0-5, rows 4-10 → a 6-wide x 7-tall loop whose hole
  is exactly 1px wide and 2px tall** (code-verified: the only enclosed
  transparent pixels are (3,7) and (3,8)). **A 1x2 hole is enough to read as
  "ring" at this size** — that is the single most useful number here. The bow
  is the only round part and it is tiny.
- **Shaft: rows 6-8, x6-15 → 10px long, 3px tall** (a black top line, a
  gold core row, a black bottom line). Effective visible shaft = **1-2px of
  gold**.
- **Bit/teeth: two downward teeth at x10-11 and x12-13, rows 9-10** — each
  tooth is 1px wide with black on both sides, hanging 2 rows below the shaft.
- **Highlight `ffffaa` (the lightest value) is a 3px cluster on the upper-left
  of the bow only** — at (1,5),(2,5) and (1,6). One highlight, on the round
  part, up-left.

---

## COIN — pile (8,3) and stack (0,4)

**There is no single flat coin in this set.** Both coin representations are
*piles*. This is itself a finding: at 16x16 a lone circle reads as a ring or a
ball, so the convention is to draw **a heap with visible individual disc
edges**.

Gold pile (8,3) — bbox (0,4,15,12), 16x9, 5 colors:

```
................
................
................
................
....####........
...#&&&&###.....
..#&*****@%#....
..#@@&**@&%#....
.#&***&&@@@%##..
#&@&&@@&%%@@%%#.
#@@@@&@@@@&%%%%#
.##%@@%%%%%%###.
...#########....
................
................
................
palette: #=#000000  @=#f8c800  %=#d2a500  &=#fffc00  *=#ffffaa
```

Coin stack (0,4) — bbox (1,4,15,12), 15x9, only 4 colors:

```
................
................
................
................
.....##.##......
....#@@#@@@#....
...##@&&&&%@#...
..#%&%&%@@&@%##.
..#%@@&@@%@&@%%#
.#@&%%@&@%%&@@%#
.#%@%&&@%%@@%%#.
..###@%%##%%%#..
.....###..###...
palette: #=#000000  @=#604d0b  %=#542d23  &=#9c7130
```

- **Both are ~9px tall and sit in the LOWER half of the cell** (rows 4-12),
  with 4px of air above and 3 below — coins are heavy, so they sit low.
- **Individual discs are indicated by 1px black arcs *inside* the mass**, not
  by outlining each coin fully. Look at (0,4) rows 4-5: `##.##` then
  `#@@#@@@#` — a single black column at x7 separates two coins in the top row.
- **Highlight:** the brightest value (`ffffaa` / `fffc00`) forms a **diagonal
  band across the upper-left of the pile** (rows 5-8, drifting right), never a
  single dot. Highlight is ~10-15 px, i.e. **roughly 12% of the icon.**

---

## GEM — cell (3,3) red, (0,3) pink

Red cut gem (3,3) — bbox (1,2,14,14), 14x13, 6 colors:

```
................
................
...######.......
..#*&&%@+##.....
.#+&&%@+%&&#....
.#+%%%@+&&&%#...
.#%+&+*+&&%%%#..
.#%+&%%*%%%%@#..
.#%+%%%%*%%@@&#.
.#%*%%%%@***&@#.
.#*@*@%%@@&@@@#.
.#*@@&@@@&&@@@#.
.#*@@&&&&&&@@&#.
.#&&&@@@@@@&&#..
..###########...
................
palette: #=#000000  @=#800000  %=#ce0000  &=#e62e1a  *=#f08b80  +=#f5bab4
```

Pink gem (0,3) — bbox (1,2,14,14), 14x13, 7 colors:

```
................
................
.....@@@@@......
....@**+**@@....
...@*##&##**@...
..@+&#####*##@..
.@=&#####&&*&#@.
.@*#####&&#*&&@.
.@+##&&&###=&&@.
.@+&###&&&=%#&@.
.@#%%&##&+%%%#@.
..@##++++%%%%@..
..@%%%%%%+%%@...
...@@%%%%%#@....
.....@@@@@@.....
................
palette: #=#fa9898  @=#000000  %=#8d2b2b  &=#ad4b4b  *=#ffeeee
         +=#ffb4b4  ==#ffe2e2
```

**Measured gem geometry:**

- Both are **~14x13, roughly filling the cell** with 1-2px margins — gems are
  drawn BIG.
- The pink one (0,3) is the clean **faceted-round** pattern. Measured span per
  row (verified by code, not by eye):

```
row  2:  5 px  (x5-9)      row  9: 14 px  (x1-14)
row  3:  8 px  (x4-11)     row 10: 14 px  (x1-14)
row  4: 10 px  (x3-12)     row 11: 12 px  (x2-13)
row  5: 12 px  (x2-13)     row 12: 11 px  (x2-12)
row  6: 14 px  (x1-14)     row 13:  9 px  (x3-11)
row  7: 14 px  (x1-14)     row 14:  6 px  (x5-10)
row  8: 14 px  (x1-14)
```

  **Ramp: 5, 8, 10, 12, 14 — then 5 flat rows at 14, then back down.**
  Compare the shield's **5, 9, 11, 13, 13, 15 + 5 flat rows at 15**.
  The two differ in the middle (the gem opens by 3,2,2,2; the shield by
  4,2,2,0,2) but **both start with a 5px cap and both hold their maximum for
  exactly 5 rows.** The reusable recipe at this size is therefore:
  **a 5px polar cap, open by ~2px per row for 4 rows, then run flat for 5
  rows, then mirror.** The gem's descent is *not* a perfect mirror of its
  ascent (row 12 is 11px, breaking symmetry) — hand-drawn asymmetry is normal
  and evidently acceptable.
- **Faceting is done with 2-3 flat value bands, not gradients.** The upper
  third is the lightest (`f5bab4`/`ffeeee`), the middle is mid (`ce0000`), the
  bottom is darkest (`800000`) — hard-edged, no dithering.
- **Highlight: an asymmetric blob in the UPPER-LEFT, 3-6px**, at roughly
  (2-6, 3-5). On the red gem the `*`/`+` lightest pixels sit at x2-5, y3-6.
  **Never centred, never a single pixel — a small angular patch.**

---

## RING — cell (6,2) gold, (10,2) silver band

Gold ring (6,2) — bbox (2,2,14,14), 13x13, 7 colors:

```
................
................
.......#####....
.....##@@@@%#...
....#@@**@%%@#..
...#@**%###%@@#.
...#**&#...#%@#.
..#&*&#....#=%#.
..#&*#.....#+%#.
..#&&#.....#+%#.
..#@&#....#+@#..
...#&%####+=%#..
...#@@%=++=%#...
....##@@@%%#....
......#####.....
................
palette: #=#000000  @=#eac64a  %=#caa217  &=#f9e471  *=#fdf9ea
         +=#604d0b  ==#886c0f
```

Silver band, viewed edge-on (10,2) — bbox (0,4,15,12), 16x9, 6 colors:

```
................
................
................
................
.....######.....
..###%***&%###..
.#@%&######&%@#.
#@###......###@#
#@##........##@#
#@%&########&%@#
.#@%&*+**&&%@@#.
..##&+*%%%@@##..
....########....
................
................
................
palette: #=#000000  @=#8b8b8b  %=#afafaf  &=#cacaca  *=#e0e0e0  +=#eaeaea
```

**Measured ring geometry (the important one — this is how you draw an
annulus at 16px):**

- Ring (6,2) is a **13x13 tilted ellipse**, bbox (2,2)-(14,14).
- **The band is only 2px of metal thick** (plus black on both sides = 4px of
  stroke), e.g. row 8 is `..#&*#.....#+%#..` — left wall = black,`&`,`*`,black;
  right wall = black,`+`,`%`,black.
- **The hole is measured exactly as** (code-verified transparent runs enclosed
  by the band):

```
row  6: 3 px (x8-10)     row  9: 5 px (x6-10)
row  7: 4 px (x7-10)     row 10: 4 px (x6-9)
row  8: 5 px (x6-10)
```

  **A 5px-wide, 5-row-tall hole inside a 13x13 ring — the hole is ~38% of the
  ring's diameter.** That is the thing that makes it read as a ring rather
  than a donut-shaped coin: **at 16px you must spend at least 4-5px on the
  hole**, even though it costs you the band's thickness.
- The ring is drawn **tilted in 3/4**, so the outline is an ellipse rotated
  ~30 degrees: the top-left arc (rows 3-6) is thicker/lighter and the
  bottom-right (rows 11-13) is darker (`604d0b`,`886c0f`).
- **Highlight: `fdf9ea` (lightest) sits on the UPPER-LEFT inner arc**, pixels
  at (8-9,4), (5-6,5), (4-5,6), (4,7), (4,8) — a **1-2px wide light stroke
  following the curve**, not a dot.
- The edge-on band (10,2) is the alternative: a **flat 16x9 ellipse with a
  6x2 hollow centre** (rows 7-8, x5-11 empty), giving an open O.

---

## SCROLL — cell (9,3)

```
................
...###......###.
..#o@=######=@o#
..#@@%&&&&&&&@@#
...#*%%++++%%x#.
....#@+*@@*++@#.
....#%**%***%*#.
....#*@@*@@@%%#.
...#*%&&%*%&%#..
...#%*@@&@*%*#..
..#@++*%%++@#...
.#&=&=+++=&=#...
#o@%&%&&=&%@o#..
#@@%######%@@#..
.###......###...
................
palette: #=#000000  @=#3f2c16  %=#c29541  &=#d9bc88  *=#93702f
         +=#6b4a25  ==#ecddc1  o=#805e4d  x=#705523
```

- **bbox (0,1,15,14) — 16 wide x 14 tall. Full width.**
- **Two rolled ends, top and bottom, each 3 rows tall** (rows 1-3 and 12-14),
  each drawn as a **dark `3f2c16` cylinder with light `ecddc1` end-caps at the
  extreme left and right x0-2 / x13-15.** The rolls stick out past the sheet.
- **The parchment sheet is rows 4-11, x3-13 — narrower than the rolls by ~2px
  each side.** That inset is what sells "rolled up".
- **The sheet is skewed:** its left edge marches right as you go down
  (x4 at row 4 → x3 at row 8 → x1 at row 11), giving a subtle parallelogram
  rather than a rectangle.
- **Writing is implied by scattered mid-value `93702f`/`c29541` pixels**, never
  by legible marks.

---

## MEAT — cell (10,3)

```
................
................
..@@@@@.........
.@&&###@@.......
@#&#&#&&&@......
@&######&&@@....
.@#&#%%###&#@@..
.@%&&#%*######@.
..@%#&#%**##%%@.
..@*%#&#%%*#%%@.
...@%#&##%%*@*@.
...@%##%##*@....
...@*%#%%#@.....
...@****%@......
....@@@@@.......
................
palette: #=#a62c1a  @=#000000  %=#842113  &=#e0503a  *=#63180e
```

- **bbox (0,2,14,14) — 15x13. Only 5 colors: black + 4 reds.**
- Shape is an **irregular blob** — deliberately asymmetric, wider at the top
  (rows 3-7 reach x0-x13) and tapering bottom-right. **No symmetry at all**;
  that irregularity is what makes it read as meat and not a gem.
- **Highlight `e0503a` (brightest red) forms a diagonal streak** through
  rows 3-7 on the left/upper area — again upper-left.
- Shadow `63180e` is used sparingly (bottom rows 9-13).
- The black outline here is **only 28% of pixels** — the lowest of the thin
  items — because the blob is solid.

---

## BONE — cell (11,11)

```
................
................
................
.........###....
........#&@%#...
.......#@%%@#...
......#&%@##....
......#@@#......
.......#&%#.....
....##.#@@#.....
...#&%#@&#......
...#@@&%@#......
....#%@##.......
.....##.........
................
................
palette: #=#000000  @=#b5754a  %=#c59372  &=#e4c4ad
```

- **bbox (3,3,12,13) — 10x11. The SMALLEST icon measured, with real margins
  (3/3/3/2).** Small objects are allowed to be small; they are not scaled up
  to fill the cell.
- **Only 4 colors** — black + 3 tans. The minimum viable palette.
- Structure: a **diagonal shaft 2px wide** running from upper-right (10,6) to
  lower-left (5,11), with a **knob at each end**: the top knob is a 4x3 blob
  at (8-11, 3-5) and the bottom knob is 4x3 at (3-6, 9-11). Classic dog-bone,
  drawn on the diagonal for the same length reason as the sword.
- Lightest value `e4c4ad` is one or two pixels per knob, upper-left of each.

---

## BOOK — cell (7,12) green, (8,12) red

```
.......@@@......
.....@@%%#@.....
...@@#%#%%#@....
.@@##%#%#%##@...
@###%#%######@..
@x#=########%#@.
@&=######%#####@
@&sx####%#%###*@
@&s&x#=##%##**+@
.@=&&=####**+oo@
..@&&sx#**+oob+@
...@&s&*+oob+@@.
....@=&*ab+@@...
.....@&*cc@@....
......@@@aa@....
.........@@.....
palette (green): @=#000000  #=#274f1c  %=#356a26  &=#1b3513  *=#0f1e0b
                 x=#3e7a2c  ==#9c6f00  s=#d2a500  +=#c29541
                 o=#ecddc1  b=#d9bc88  a=#aa0000  c=#ff0000
```

- **bbox (0,0,15,15) — fills the whole 16x16 cell, 0 margin.** 13 colors,
  the richest icon measured.
- Drawn as a **diamond/rhombus (3-4 top-down view of a closed book)**: the
  top vertex is at (7-9, 0), the left vertex at (0, 4-8), the right vertex at
  (15, 6-9), the bottom at (9-10, 15). Rotating the rectangle to a diamond is
  what buys the perceived size.
- **Cover** = the greens (`274f1c`/`356a26`/`3e7a2c`), occupying the upper-left
  ~2/3. **Page block** = the creams (`ecddc1`/`d9bc88`/`c29541`), a wedge along
  the lower-right edge, about **3-4px thick**.
- **Gold trim** (`d2a500`/`9c6f00`) is a **1px line along the left/spine edge**,
  rows 7-12 at x2-3.
- **Bookmark:** a **2px red tail** (`ff0000`/`aa0000`) at (8-10, 12-15),
  hanging off the bottom — the only saturated accent, and the thing that makes
  a green diamond read as a book.

---

## BOMB — NOT FOUND

**I did not find a bomb in either downloaded set, and I have not fabricated a
grid for it.**

**Three sources inspected, all negative:**

- **Williamson roguelike sheet** (13x15 = 195 cells) — viewed in full at 8x.
  Contents: rings/amulets, crowns, gems, gold, ore, ingots, tools, swords,
  axes, maces, helmets, armour, gloves, boots, staves, shields, bones, plants,
  books. **No bomb.**
- **Shade's 16x16 Assorted RPG Icons** — `consumables.png` viewed in full
  (both halves of its 44 columns: **all 748 cells are mugs/tankards/jars**);
  `weapons.png` viewed in full (**all 72 cells are swords**); `potions.png`,
  `books.png`, `armours.png`, `chests.png` are what their names say.
  **No bomb.**
- **Kenney "Tiny Dungeon" (CC0)** — downloaded from kenney.nl
  (`kenney_tiny-dungeon.zip`, License.txt confirms **CC0 1.0**), 12x11 packed
  tilemap viewed in full. Walls, floors, doors, barrels, chests, characters,
  swords, axes, potions, keys. **No bomb.**
- OGA searches for `bomb sprite item` (CC0) and `food meat bomb icons 16x16`
  returned only platformer/character sheets (Pirate Bomb, Bombman, Bomb
  Explosion Animation) — none is a 16x16 inventory icon.

**What I can say without measuring:** nothing reliable about a bomb's pixel
layout. If you want it, the honest next step is a targeted hunt (Kenney
1-Bit / Tiny Dungeon, or a Zelda-like item sheet). **What I would NOT do is
invent a grid.**

**However**, the conventions above transfer directly: from the ring you get
the annulus/sphere edge treatment; from the coin pile you get the 5→9→11→13
round ramp; from the key you get the "1px highlight cluster upper-left of the
round part" rule; a bomb is a filled version of the shield circle plus a
2px diagonal fuse in the style of the sword's 2px diagonal blade.

---

## CROSS-VALIDATION against a second artist (Shade, CC0)

**Everything above this point is ONE artist's ONE sheet (Joe Williamson).**
Several of those 13 cells are variants of the same object, so the "conventions"
were really n=1 on *style*. To test which rules are universal versus
Williamson's personal taste, here are three icons measured from **Shade's
16x16 Assorted RPG Icons (CC0)** — a completely independent artist.

### Shade sword — `weapons.png` cell (0,0)

```
................
.###............
.#**#...........
.#@&*#..........
..#@&*#.........
...#@&@#........
....#@&@#.......
.....#@&%#..##..
......#%&%##%#..
.......#%&%@#...
........#%*#....
........#@#+#...
.......#%#.#=#..
.......##...#+#.
.............##.
................
palette: #=#070707  @=#d29f58  %=#b07e41  &=#412d1c  *=#fbbd5d
         +=#7e4e26  ==#c07f3a
7 colors, bbox (1,1,14,14) = 14x14
```

### Shade potion — `potions.png` cell (0,0)

```
................
................
......####......
.....#s&&s#.....
....#%&&&&e#....
....#@c&&cb#....
....#@assab#....
....#%@@@=%#....
...#@xooohx%#...
...#=@@+++*%#...
...#=@@ddig%#...
...#%o*+++*%#...
...#%ox***xf#...
....#%@@==%#....
.....######.....
................
palette: #=#070707  @=#ffffff  %=#9e9e96  &=#ecb686  *=#565656
         +=#727272  ==#d2d2d2  o=#dcdcdc  x=#393939  s=#96523a
         a=#591d1d  b=#989898  c=#bd774f  d=#dfdfdf  e=#4c4c4c
         f=#5e5b4f  g=#9e9e96  h=#a5a5a5  i=#c1c1c1
19 colors, bbox (3,2,12,14) = 10x13
```

### Shade book — `books.png` cell (0,0)

```
................
...###########..
..#++o****o++#..
.#@+&@@@@@@&+#..
.#&o@x=ab=x@o#..
.#&*@%ae=b%@*#..
.#&*@%c==c%@*#..
.#&*@%b==a%@*#..
.#&o@x=ca=x@o#..
.#&+&@@@@@@&+#..
.#&++o****o++#..
.#@&&%%%%%%&&#..
.#&@dsssssss##..
..#xx%%%%%%x&#..
...###########..
................
palette: #=#0a0a0a  @=#29211e  %=#764829  &=#452e25  *=#a87644
         +=#f4bd64  ==#343434  o=#cf9b54  x=#5a392b  s=#e8d6ba
         a=#bbbbbb  b=#555555  c=#7d7d7d  d=#d7ad7c  e=#e8e8e8
15 colors, bbox (1,1,13,14) = 13x14
```

### Which rules SURVIVED, and which were Williamson-only

| Rule | Verdict |
|---|---|
| **Full closed 1px outline on the silhouette** | **HOLDS.** Code-verified: all 38 silhouette-edge px of Shade's sword are a single uniform color. Universal. |
| **Outline is PURE `#000000`** | **FAILS — this was Williamson-specific.** Shade uses **near-black `#070707`** (sword, potion) and **`#0a0a0a`** (book). Restate the rule as *"one uniform near-black outline color, `#000000`–`#0a0a0a`"*, not literally pure black. |
| **Draw long items on the diagonal** | **HOLDS.** Shade's sword is also a 45-degree diagonal, tip upper-left, hilt lower-right (mirrored vs Williamson's). |
| **Sword blade = ~2px metal + 1px outline each side** | **HOLDS.** Shade's blade rows read `#@&*#` / `#@&@#` — same 3-metal-px-between-two-outline-px stroke. |
| **Blade uses a light/dark pair for the two faces** | **HOLDS.** Shade: `d29f58` light face + `412d1c` dark core + `fbbd5d` highlight edge. |
| **Crossguard low on the blade** | **HOLDS.** Shade's guard is at rows 7-9 (~50% depth) vs Williamson's row 11 (~72%). Range: **50-75% depth.** |
| **4-9 colors** | **FAILS as an upper bound.** Shade runs **7 (sword), 15 (book), 19 (potion)**. Williamson's 13-color book was not the ceiling. Restate: **a simple item needs only 4-7; a detailed one may use 15-19.** Color count is a style dial, not a constraint. |
| **Fill the cell / tiny margins** | **HOLDS, loosely.** Shade: sword 14x14, book 13x14, potion 10x13 — margins of 1-3px, slightly more generous than Williamson's 0-2px. |
| **No dithering, hard-edged value bands** | **HOLDS.** No dither pattern in any Shade grid. |
| **Highlight upper-left** | **HOLDS on the sword** (`fbbd5d` on the upper-left blade edge). **Shade's potion is front-lit/symmetric instead** — its bottle is bilaterally symmetric with a centred shine, because it is drawn front-on rather than 3/4. So: **upper-left holds for 3/4-view objects; front-on objects get a symmetric centred highlight.** |
| **Potion = 3/4 view, tall, fills 16 rows** | **FAILS.** Shade's potion is **front-on, bilaterally symmetric, 10x13 with margins** — a squat round flask, not Williamson's tall angled one. **Both are valid; this is a style choice, not a convention.** |

**Bottom line:** the *structural* rules (closed uniform outline, diagonal for
long items, 2px blade stroke, hard value bands, fill-ish the cell) are
**genuinely cross-artist**. The *specific values* (pure black vs near-black,
color count, 3/4 vs front-on projection, exact margins) are **per-artist
style** — pick one and be consistent rather than treating Williamson's numbers
as law.

---

## Summary of transferable rules (all derived from measurements above)

1. **Fill the cell.** Margins are 0-2px. Long items run edge-to-edge on their
   long axis. Only genuinely small objects (the bone) get a real margin.
2. **Draw long things on the diagonal** — sword, bone, key-teeth. The diagonal
   buys 22px of length inside a 16px box.
3. **Full closed 1px outline around the whole silhouette, in ONE uniform
   near-black.** Strictly code-verified: for all 15 Williamson icons, every
   silhouette-edge pixel is `#000000` (13 of 15 perfect; meat and coin-stack
   each have exactly **1** stray non-black edge pixel — artist slips, not
   technique). Shade independently uses `#070707`/`#0a0a0a`. **So: near-black
   in `#000000`–`#0a0a0a`, never selective, never hue-tinted.** Outline is
   23-33% of a chunky icon's pixels and 46-59% of a thin one's.
4. **Use black internally too**, to separate materials (blade/guard,
   cover/pages, shaft/teeth). This is why the black budget is so high.
5. **Color count is a style dial, not a constraint.** Williamson runs 4-13
   (typically outline + 3-5 shades of one hue + 1-2 accents); Shade runs 7-19
   on the same subjects at the same size. **4-7 is enough for a simple item;
   going to 15-19 is legitimate for a detailed one.** Pick a budget and hold
   it across the set — consistency matters more than the number.
6. **The round-form recipe at this size: a 5px polar cap, then open by ~2px
   per row for 4 rows, then hold the maximum flat for exactly 5 rows, then
   mirror.** Shield measures 5,9,11,13,13,15 + 5 flat rows at 15; gem measures
   5,8,10,12,14 + 5 flat rows at 14. **The "5px cap" and the "5 flat rows at
   max" are the two constants**; the opening increments vary by 1px between
   the two, and the descent need not perfectly mirror the ascent.
7. **Highlights go UPPER-LEFT, as strokes or small patches (2-6px), never a
   single centred dot.** True on ring, gem, key, meat, potion, coin, and on
   Shade's sword. **Exception found in cross-check:** objects drawn *front-on*
   rather than 3/4 (Shade's potion) are bilaterally symmetric with a **centred**
   shine instead. Light direction follows the projection you chose.
8. **Shading is 2-3 hard-edged value bands. No dithering, no gradients** in any
   measured icon.
9. **Heavy things sit low** (coins occupy rows 4-12, air above). Tall things
   (potion) use all 16 rows.
10. **One saturated accent per icon** to make the read (the book's red
    bookmark, the crown's ruby, the sword's gold guard against silver).
