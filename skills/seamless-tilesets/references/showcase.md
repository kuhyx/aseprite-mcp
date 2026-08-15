# Exporting, tracking and showing pixel art

> **Canonical copy:** `skills/pixel-animation/references/showcase.md` in the
> `aseprite-mcp` repo. The copies under `item-icons/` and `seamless-tilesets/`
> (and everything under `~/.claude/skills/`) are installed duplicates — edit the
> canonical one and re-run `scripts/install_skills.sh`, which re-copies and then
> diffs every copy to prove they match.

Shared by `item-icons`, `seamless-tilesets` and `pixel-animation`. Everything
here was learned by getting it wrong in a session whose art was already finished
— the drawing was done and the work was still invisible.

## The failure this exists to prevent

A session drew 6 icons and 8 tiles, verified them, and committed the
`.aseprite` sources. The user then asked **"where can I see those?"** and the
answer was *nowhere*: no PNG existed on disk, every export had been a scratchpad
temp file, and `.gitignore` blocked `*.png` outright. The art was real and
unviewable.

**Sources are not a deliverable.** A `.aseprite` file requires Aseprite
installed and running to see. If the user cannot look at the work in a browser
or a file manager, it is not delivered.

---

## THE TRAP: `Read` modifies image files in place

**`Read`-ing an image rewrites the file on disk at reduced resolution.** It is
not a viewer; it is a destructive downscale.

Mechanism, read from source rather than inferred: `~/.claude/settings.json`
registers `hooks/shrink_images_pretool.sh` as a **`PreToolUse` hook matching
`Read`**. It calls `~/.claude/scripts/shrink_screenshot.py`, which caps width at
`DEFAULT_MAX_WIDTH = 640`, resamples with `Image.LANCZOS`, and saves with
`resized.save(path)` — **the same path**. Any exported art wider than 640px is
silently downscaled the moment you look at it, and LANCZOS is precisely the
bilinear-family filter that destroys hard pixel edges.

This is a *good* hook — screenshots are billed by pixel area — that is simply
hostile to pixel-art assets. Work around it; don't disable it.

Proven, not assumed:

```
export_spritesheet(...)          -> 1024x256 on disk
cp sheet.png /scratch/probe.png
Read /scratch/probe.png          -> the COPY becomes 640x160
identify sheet.png               -> the ORIGINAL is still 1024x256
```

In this session that corrupted a **committed** asset: the filmstrip was Read
during inspection, silently became 640x160, and got committed and then labelled
"native width" in a README. The wrong number was even given a fabricated
explanation ("`export_spritesheet` packs content width") rather than being
distrusted — 1024x256 and 640x160 are both 4:1, which is exactly what a uniform
downscale looks like and nothing like a crop.

**Rules:**

- Never `Read` a file you are about to commit. `cp` it to the scratchpad and
  `Read` the copy.
- After inspecting anything, `identify` the real file before committing.
- If a dimension surprises you, **re-derive it** (`identify`, or parse the
  header) before writing an explanation for it. A number you cannot explain is
  a bug, not a fact to rationalise.

---

## Two exports per source

| File | Scale | Purpose |
|---|---|---|
| `key.png` | 1x | the real asset — what a game would load |
| `key_x8.png` | 8x nearest-neighbour | the viewing render — 16px art is invisible at 1:1 |

Name them distinctly. Both match `*.png` and land in the same directory; a
shared name silently overwrites the real asset.

Scale with the tool's own `scale` parameter (`export_frame`,
`export_spritesheet`, `export_tag` all take one) — that is nearest-neighbour and
preserves hard pixel edges. Upscaling an export with a NEAREST resize is display
scaling and allowed; synthesising pixels in a script is not.

## Track the exports

Sources alone leave the art unviewable, so commit both. In `.gitignore`:

```gitignore
# Exports are tracked as the permanent showcase. They are regenerable from the
# sources, but "regenerable" needs Aseprite installed and running.
!examples/icon-animation/*.png
!examples/tileset/*.png
!examples/tileset/*.gif
```

Blanket `*.png` / `*.gif` rules are **file** patterns, not directory patterns,
so a `!` re-include works here. Verify per file rather than trusting the rule:

```
git check-ignore -v <path>     # nonzero exit = NOT ignored = committable
```

If a rule's comment says exports stay ignored, **rewrite the comment** when the
policy changes. Do not bolt on an exception clause that contradicts the prose
above it.

## Render at native width or the art blurs

GitHub strips CSS, so `image-rendering: pixelated` is not available. Any
declared width that isn't the asset's native width forces a **bilinear
resample** and smears every hard pixel edge — blurry pixel art in the README of
a pixel-art project.

```html
<img src="examples/tileset/grass_x8.png" width="256">   <!-- asset IS 256px -->
```

Icons at 128px shown at `width="96"` (0.75x) and tiles at 256px shown at
`width="112"` (0.4375x) both shipped this defect. If a row of native-width
images overflows GitHub's ~830px column, **reflow the table** (two rows of
three, two per row) rather than shrinking the images.

Downscaling a *large* source (a 1536px sheet capped by the container) is far
less destructive than upscaling; it is acceptable where a wide filmstrip has no
alternative.

Check it mechanically — parse each `<img>` and compare declared width against
the file's real header. Do not eyeball it.

## Verify it actually renders

Local file existence is not visibility. After pushing:

```
curl -s -o /dev/null -w '%{http_code} %{size_download}' \
  https://raw.githubusercontent.com/<user>/<repo>/main/<path>
```

Expect `200 <bytes>` matching the committed size. A 404 means the showcase is
broken for everyone but you.

**And push.** A clean `git status` is not a delivered showcase — README `<img>`
tags only resolve for the user once the commit is on the remote. Check
`git log origin/main..HEAD` before claiming done.

## Checklist

| Check | Command | Catches |
|---|---|---|
| Exports exist | `ls` the target dirs | "sources only" — the whole failure above |
| Not gitignored | `git check-ignore -v` per file | Committing nothing; broken images on GitHub |
| Paths resolve | test every README `src` on disk | Typos, renames |
| Native width | parse `<img>`, compare to header | Bilinear blur |
| Real file intact | `identify` after any `Read` | The in-place downscale trap |
| Pushed | `git log origin/main..HEAD` | A showcase only you can see |
| Serves remotely | `curl` raw.githubusercontent | Broken images for everyone else |
