# Reference art — credits and licences

Third-party pixel art, vendored here as **reference material** for measuring
construction conventions (proportions, outline style, colour counts, silhouette
patterns). It is not used in, linked by, or shipped as part of this server.

**Read this before reusing anything in `references/`.** The sets have different
licences, and one of them is ShareAlike.

---

## 1. Roguelike/RPG Items — Joe Williamson

- **Files:** `roguelike-items/roguelikeitems_1.png`
- **Author:** Joe Williamson (`https://opengameart.org/users/joecreates`)
- **Source:** https://opengameart.org/content/roguelikerpg-items
- **Licence: CC-BY-SA 3.0** — Attribution + **ShareAlike**

> Roguelike/RPG Items by Joe Williamson, licensed CC-BY-SA 3.0.
> https://opengameart.org/content/roguelikerpg-items

**⚠️ ShareAlike warning.** OpenGameArt's page lists both CC-BY-SA 3.0 and CC0,
but the artist baked the words "Attribution-ShareAlike" into the image itself,
so the **stricter reading is recorded here deliberately**. ShareAlike is viral:
derivative artwork must be released under a compatible licence. If you need
licence-clean references, use the Shade or Kenney sets below instead.

This is the sheet the ASCII grids in `MEASUREMENTS.md` were measured from.

## 2. 16x16 Assorted RPG Icons — Shade

- **Files:** `assorted-rpg-icons/{weapons,potions,books,chests,armours,consumables}.png`
- **Author:** Shade (`https://merchant-shade.itch.io/`)
- **Source:** https://merchant-shade.itch.io/16x16-mixed-rpg-icons
- **Licence: CC0 1.0** (public domain dedication) — no obligations

Used to cross-validate Williamson's conventions against a second artist. That
cross-check is what retracted the "4–9 colour ceiling" claim: Shade uses 19
colours on a single potion, so colour counts are per-artist style, not a rule.

## 3. Tiny Dungeon — Kenney

- **Files:** `kenney-tiny-dungeon/tilemap_packed.png`, `Preview.png`, `License.txt`
- **Author:** Kenney (https://kenney.nl)
- **Source:** https://kenney.nl/assets/tiny-dungeon
- **Licence: CC0 1.0** — free for personal, educational and commercial use;
  crediting Kenney is appreciated but not mandatory (see `License.txt`).

Only the packed tilemap and preview are vendored, not all 136 individual tiles.

## 4. Kyrise's Free 16x16 RPG Icon Pack

- **Files:** not vendored — measured during research, not committed.
- **Author:** Kyrise (`https://kyrise.itch.io/`)
- **Source:** https://kyrise.itch.io/kyrises-free-16x16-rpg-icon-pack
- **Licence:** free pack; attribution requested by the author.

Measured in `SHAPE_RESEARCH.md` for gem/shield/sword/coin/ring construction
(§3, §4, §5, §7). `pearl_01a.png` is the sprite that **refuted** the strong
form of the circle-delta rule: its run-lengths are byte-identical to
Aseprite's stuttering d=14 output and it still reads as round.

## 5. CC0 Food Icons

- **Files:** not vendored — measured during research, not committed.
- **Author:** AntumDeluge (compiler), OpenGameArt
- **Source:** https://opengameart.org/content/cc0-food-icons
- **Licence: CC0 1.0**

Measured for the meat/ham proportions in `SHAPE_RESEARCH.md` §6 — the source
of the "real meat sprites are wider than tall (1.2–1.6:1)" finding.

---

## What was actually taken from these

Nothing was copied pixel-for-pixel. The measurements extracted were
*conventions*: bounding-box margins, colour counts, outline colour and
thickness, run-length progressions on round shapes, and blade/hilt ratios.
`MEASUREMENTS.md` records those as ASCII grids with the source cell noted for
each, so any number in it can be re-derived from the sheets here.

Original art produced in this repo from those conventions is original work.
Because it is not a derivative of the Williamson sheet, the ShareAlike term is
not believed to reach it — but that judgement is the reason the stricter
licence reading is recorded above rather than the convenient one.

## Re-fetching

If you would rather not have these binaries in your clone, delete
`references/*/` and re-download:

```sh
# Williamson (CC-BY-SA 3.0)
# https://opengameart.org/content/roguelikerpg-items
# Shade (CC0)
# https://merchant-shade.itch.io/16x16-mixed-rpg-icons
# Kenney Tiny Dungeon (CC0)
curl -LO https://kenney.nl/media/pages/assets/tiny-dungeon/tiny-dungeon.zip
```
