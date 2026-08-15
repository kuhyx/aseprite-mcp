# To fix

Known issues deliberately left for a later session. Nothing here blocks the
MCP server, the test suite, or the skills.

`BUGS_FOUND.md` used to sit beside this file, holding bugs found during the
2026-08-12 coverage pass and asserted as *current behaviour* because that
task's scope was "write tests, don't change behavior". Every entry in it has
now been fixed (2026-08-15) except the two findings below, which are not
defects. It has been deleted.

---

## Four unreachable process-failure guards in `pixel_read.py`

**Status:** open by nature. **Found:** 2026-08-12. **Blocks:** nothing.

`pixel_read.py`'s four `if not success:` branches handle a process-level
subprocess failure that a real corrupt `.aseprite` file does not produce:
Aseprite exits 0 even on a bad file (printing "Error reading header" to
stderr), and the script's own `"ERROR:No active sprite"` line is what
actually catches it.

They are covered by mocking `AsepriteCommand.execute_lua_script` directly.
That is the honest option — the alternative is deleting real error handling
because this platform's Aseprite build happens not to exit non-zero.

## `export_frame`'s frame-numbered sibling fallback

**Status:** open, low priority. **Found:** 2026-08-12. **Blocks:** nothing.

`export.py::export_frame` keeps a fallback that adopts a `<stem><n>.png`
sibling when the exact requested filename was not produced. Verified directly
that the real Aseprite CLI writes to the exact filename even for frame 2+ of a
multi-frame sprite, so this path is unreachable here and is covered by a mock.

It is kept because the behaviour is undocumented and may differ on another
platform or Aseprite version. Its glob was tightened on 2026-08-15 to match
digit suffixes only — it previously matched `heroine.png` for an export to
`hero.png` and would have renamed that unrelated file over the output path.

## `set_cel_position` was restructured, not just re-guarded

**Status:** informational. **Blocks:** nothing.

The 2026-08-15 fabricated-success pass hoisted 15 guards out of
`app.transaction` closures. Fourteen were pure moves. `set_cel_position` is
the exception: its `source_frame` defaulting had to move above the
transaction as well so the guard could see it, and the transaction now
re-reads `target_layer:cel(frame)`. Behaviour is unchanged and covered, but
do not assume the diff is a straight lift when reading that function.

---

## Verified NOT bugs (do not re-file)

Recorded here because `BUGS_FOUND.md` claimed each as a defect and a future
reader would otherwise "fix" working code.

- **`draw_rectangle`, `fill_area`, `draw_circle` do not drop out-of-cel
  pixels.** `BUGS_FOUND.md` grouped them with `draw_pixels`/`draw_line` as
  sharing the `putPixel` bounds bug. They dispatch `app.useTool` with
  sprite-global points, which grows the cel itself. Probed against real
  Aseprite from a 2x2 cel: all three expanded it (to 26x26, 32x32 and 14x30)
  with the pixels landing at full alpha.
  `tests/test_drawing_fixes.py::test_usetool_siblings_already_grow_the_cel`
  pins this, so switching them to `putPixel` would fail loudly.
- **`render_onion_skin`'s traversal guard was not dead because of ordering.**
  `BUGS_FOUND.md` said the check ran after `os.path.exists`. It does not: the
  `path_exists` call guards the *input* `filename`, while the guarded
  `output_filename` is never exists-checked. The guard was dead purely because
  `reject_traversal` normalized first, which is now fixed.
- **Aseprite's `saveAs()` does NOT ignore directory permissions.**
  `BUGS_FOUND.md` claimed `create_canvas` into a `chmod 555` directory
  "writes the file anyway". Re-checked on 2026-08-15: the file is *not*
  written. The real defect was narrower — `saveAs()` fails silently, so the
  script still reached `print("OK")` and the tool reported creating a file
  that does not exist. `create_canvas` now confirms the file exists before
  reporting success. (Auto-creating *missing parent directories* is real and
  still happens; that half of the note was accurate.)
