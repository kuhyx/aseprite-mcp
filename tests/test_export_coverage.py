"""Coverage tests for export.py: validation, error, and branch paths."""

import os

from conftest import BASE, ok, run

from aseprite_mcp.tools import animation, canvas, export


def _fresh_sprite(name):
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(canvas.add_layer(path, "body")))
    return path


# ── missing-file guards ──────────────────────────────────────────────────


def test_export_sprite_missing_file():
    result = run(
        export.export_sprite(f"{BASE}/does-not-exist.aseprite", f"{BASE}/out.png")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_copy_sprite_missing_file():
    result = run(
        export.copy_sprite(f"{BASE}/does-not-exist.aseprite", f"{BASE}/out.aseprite")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_frame_missing_file():
    result = run(
        export.export_frame(f"{BASE}/does-not-exist.aseprite", 1, f"{BASE}/out.png")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_spritesheet_missing_file():
    result = run(
        export.export_spritesheet(f"{BASE}/does-not-exist.aseprite", f"{BASE}/out.png")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_layers_missing_file():
    result = run(
        export.export_layers(f"{BASE}/does-not-exist.aseprite", f"{BASE}/layers_out")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_tag_missing_file():
    result = run(
        export.export_tag(f"{BASE}/does-not-exist.aseprite", "clip", f"{BASE}/out.gif")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_import_image_as_layer_missing_file():
    result = run(
        export.import_image_as_layer(
            f"{BASE}/does-not-exist.aseprite", f"{BASE}/x.png", "ref"
        )
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_import_image_as_layer_missing_image(sprite):
    result = run(
        export.import_image_as_layer(sprite, f"{BASE}/no-such-image.png", "ref")
    )
    assert result == f"Image {BASE}/no-such-image.png not found"


# ── copy_sprite: extension, traversal, overwrite branches ──────────────


def test_copy_sprite_appends_extension_and_succeeds(sprite):
    out = f"{BASE}/copy_no_ext"
    result = ok(run(export.copy_sprite(sprite, out)))
    assert result == f"Sprite copied to {out}.aseprite"
    assert os.path.exists(f"{out}.aseprite")


def test_copy_sprite_keeps_existing_extension(sprite):
    out = f"{BASE}/copy_with_ext.aseprite"
    result = ok(run(export.copy_sprite(sprite, out)))
    assert result == f"Sprite copied to {out}"


def test_copy_sprite_rejects_traversal(sprite):
    result = run(export.copy_sprite(sprite, "../evil.aseprite"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_copy_sprite_rejects_existing_without_overwrite(sprite):
    out = f"{BASE}/copy_exists.aseprite"
    ok(run(export.copy_sprite(sprite, out)))
    result = run(export.copy_sprite(sprite, out))
    assert result == f"Output file {out} already exists"


def test_copy_sprite_overwrite_allowed(sprite):
    out = f"{BASE}/copy_overwrite.aseprite"
    ok(run(export.copy_sprite(sprite, out)))
    result = ok(run(export.copy_sprite(sprite, out, overwrite=True)))
    assert result == f"Sprite copied to {out}"


# ── export_frame: scale validation, traversal, extension branch ────────


def test_export_frame_rejects_scale_out_of_range(sprite):
    result = run(export.export_frame(sprite, 1, f"{BASE}/f.png", scale=0))
    assert result == "scale must be between 1 and 64"

    result = run(export.export_frame(sprite, 1, f"{BASE}/f.png", scale=65))
    assert result == "scale must be between 1 and 64"


def test_export_frame_rejects_traversal(sprite):
    result = run(export.export_frame(sprite, 1, "../evil.png"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_frame_keeps_existing_png_extension(sprite):
    out = f"{BASE}/frame_ext.png"
    result = ok(run(export.export_frame(sprite, 1, out, scale=1)))
    assert result == f"Frame 1 exported to {out} at 1x"


def test_export_frame_out_of_range_frame_fabricates_success():
    # KNOWN BUG (not fixed here, out of scope for this pass): a frame index
    # past the last frame does NOT error. Aseprite's --frame-range silently
    # clamps/no-ops and the CLI still exits 0, so export_frame reports
    # success and writes a transparent/empty PNG instead of failing.
    # Verified directly: the written file is fully transparent, not a real
    # render of any existing frame. Documenting actual behavior so this
    # regresses loudly if the underlying CLI behavior ever changes.
    fresh = _fresh_sprite("export-frame-oob")
    out = f"{BASE}/frame_oob.png"
    result = run(export.export_frame(fresh, 999, out))
    assert result == f"Frame 999 exported to {out} at 1x"
    assert os.path.exists(out)


def test_export_frame_renames_frame_numbered_sibling():
    # With a multi-frame sprite, exporting a non-first frame makes Aseprite
    # append the frame number to the output filename; export_frame must
    # detect and rename that sibling to the exact requested name.
    fresh = _fresh_sprite("export-frame-rename")
    ok(run(canvas.add_frame(fresh)))
    out = f"{BASE}/frame_rename.png"
    result = ok(run(export.export_frame(fresh, 2, out, scale=1)))
    assert result == f"Frame 2 exported to {out} at 1x"
    assert os.path.exists(out)


# ── export_spritesheet: validation branches ─────────────────────────────


def test_export_spritesheet_rejects_bad_sheet_type(sprite):
    result = run(
        export.export_spritesheet(sprite, f"{BASE}/sheet.png", sheet_type="diagonal")
    )
    assert result.startswith("sheet_type must be one of")


def test_export_spritesheet_rejects_scale_out_of_range(sprite):
    result = run(export.export_spritesheet(sprite, f"{BASE}/sheet.png", scale=0))
    assert result == "scale must be between 1 and 64"

    result = run(export.export_spritesheet(sprite, f"{BASE}/sheet.png", scale=100))
    assert result == "scale must be between 1 and 64"


def test_export_spritesheet_rejects_negative_padding(sprite):
    result = run(export.export_spritesheet(sprite, f"{BASE}/sheet.png", padding=-1))
    assert result == "padding must be >= 0"


def test_export_spritesheet_rejects_bad_data_format(sprite):
    result = run(
        export.export_spritesheet(sprite, f"{BASE}/sheet.png", data_format="json-weird")
    )
    assert result == "data_format must be 'json-array' or 'json-hash'"


def test_export_spritesheet_rejects_traversal_on_output(sprite):
    result = run(export.export_spritesheet(sprite, "../evil.png"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_spritesheet_rejects_traversal_on_data_filename(sprite):
    result = run(
        export.export_spritesheet(
            sprite, f"{BASE}/sheet_dt.png", data_filename="../evil.json"
        )
    )
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_spritesheet_keeps_existing_png_extension(sprite):
    out = f"{BASE}/sheet_ext.png"
    result = ok(run(export.export_spritesheet(sprite, out)))
    assert f"Sprite sheet exported to {out}" in result


def test_export_spritesheet_reports_unknown_tag(sprite):
    result = run(
        export.export_spritesheet(sprite, f"{BASE}/sheet_badtag.png", tag_name="nope")
    )
    assert result.startswith("Failed to resolve tag:")


def test_export_spritesheet_json_hash_and_list_tags(sprite):
    ok(run(animation.set_tag(sprite, "walk", 1, 1, "forward")))
    out = f"{BASE}/sheet_hash.png"
    data = f"{BASE}/sheet_hash.json"
    result = ok(
        run(
            export.export_spritesheet(
                sprite,
                out,
                data_filename=data,
                data_format="json-hash",
                list_tags=True,
            )
        )
    )
    assert "with data file" in result
    assert os.path.exists(data)


# ── export_layers ────────────────────────────────────────────────────────


def test_export_layers_rejects_traversal(sprite):
    result = run(export.export_layers(sprite, "../evil_dir"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_layers_include_hidden(sprite):
    out_dir = f"{BASE}/layers_hidden"
    result = ok(run(export.export_layers(sprite, out_dir, include_hidden=True)))
    assert "Layers exported to" in result


# ── export_tag ────────────────────────────────────────────────────────


def test_export_tag_rejects_scale_out_of_range(sprite):
    result = run(export.export_tag(sprite, "clip", f"{BASE}/tag.gif", scale=0))
    assert result == "scale must be between 1 and 64"

    result = run(export.export_tag(sprite, "clip", f"{BASE}/tag.gif", scale=65))
    assert result == "scale must be between 1 and 64"


def test_export_tag_rejects_traversal(sprite):
    result = run(export.export_tag(sprite, "clip", "../evil.gif"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_tag_reports_unknown_tag(sprite):
    result = run(export.export_tag(sprite, "no-such-tag", f"{BASE}/tag_missing.gif"))
    assert result.startswith("Failed to export tag:")
    assert "Tag not found" in result


def test_export_tag_png_sequence_with_scale(sprite):
    ok(run(animation.set_tag(sprite, "seq", 1, 1, "forward")))
    out = f"{BASE}/tag_seq.png"
    result = ok(run(export.export_tag(sprite, "seq", out, scale=2)))
    assert "exported to" in result


# ── import_image_as_layer ────────────────────────────────────────────────


def test_import_image_as_layer_success(sprite):
    png = f"{BASE}/import_src.png"
    ok(run(export.export_frame(sprite, 1, png, scale=1)))
    result = ok(run(export.import_image_as_layer(sprite, png, "imported", 1, 2, 2)))
    assert "imported onto 'imported' frame 1" in result


def test_import_image_as_layer_creates_new_layer(sprite):
    png = f"{BASE}/import_src2.png"
    ok(run(export.export_frame(sprite, 1, png, scale=1)))
    fresh_layer = "brand-new-import"
    result = ok(run(export.import_image_as_layer(sprite, png, fresh_layer)))
    assert fresh_layer in result


def test_import_image_as_layer_frame_out_of_range(sprite):
    png = f"{BASE}/import_src3.png"
    ok(run(export.export_frame(sprite, 1, png, scale=1)))
    result = run(export.import_image_as_layer(sprite, png, "ref", frame_index=999))
    assert result.startswith("Failed to import image:")
    assert "out of range" in result


# ── export_sprite: extension handling and gif branch ────────────────────


def test_export_sprite_appends_extension(sprite):
    out = f"{BASE}/export_no_ext"
    result = ok(run(export.export_sprite(sprite, out, "png")))
    assert result == f"Sprite exported successfully to {out}.png"


def test_export_sprite_keeps_existing_extension(sprite):
    out = f"{BASE}/export_ext.png"
    result = ok(run(export.export_sprite(sprite, out, "png")))
    assert result == f"Sprite exported successfully to {out}"


def test_export_sprite_gif_format(sprite):
    out = f"{BASE}/export.gif"
    result = ok(run(export.export_sprite(sprite, out, "gif")))
    assert result == f"Sprite exported successfully to {out}"


def test_export_sprite_reports_unwritable_format(sprite):
    # "json" is not a writable --save-as image format; Aseprite either
    # exits nonzero (-> "Failed to export sprite") or exits 0 without
    # producing a file (-> the explicit exited-0-but-no-file guard).
    # Either way this exercises the failure path at export.py's tail.
    out = f"{BASE}/export_bad_format"
    result = run(export.export_sprite(sprite, out, "json"))
    assert result.startswith("Failed to export sprite:")
