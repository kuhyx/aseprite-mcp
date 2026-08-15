"""Coverage tests for export.py: validation, error, and branch paths."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from conftest import BASE, ok, run

from aseprite_mcp.tools import animation, canvas, export


def _fresh_sprite(name: str) -> str:
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(canvas.add_layer(path, "body")))
    return path


# ── missing-file guards ──────────────────────────────────────────────────


def test_export_sprite_missing_file() -> None:
    result = run(
        export.export_sprite(f"{BASE}/does-not-exist.aseprite", f"{BASE}/out.png")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_copy_sprite_missing_file() -> None:
    result = run(
        export.copy_sprite(f"{BASE}/does-not-exist.aseprite", f"{BASE}/out.aseprite")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_frame_missing_file() -> None:
    result = run(
        export.export_frame(f"{BASE}/does-not-exist.aseprite", 1, f"{BASE}/out.png")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_spritesheet_missing_file() -> None:
    result = run(
        export.export_spritesheet(f"{BASE}/does-not-exist.aseprite", f"{BASE}/out.png")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_layers_missing_file() -> None:
    result = run(
        export.export_layers(f"{BASE}/does-not-exist.aseprite", f"{BASE}/layers_out")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_export_tag_missing_file() -> None:
    result = run(
        export.export_tag(f"{BASE}/does-not-exist.aseprite", "clip", f"{BASE}/out.gif")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_import_image_as_layer_missing_file() -> None:
    result = run(
        export.import_image_as_layer(
            f"{BASE}/does-not-exist.aseprite", f"{BASE}/x.png", "ref"
        )
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_import_image_as_layer_missing_image(sprite: str) -> None:
    result = run(
        export.import_image_as_layer(sprite, f"{BASE}/no-such-image.png", "ref")
    )
    assert result == f"Image {BASE}/no-such-image.png not found"


# ── copy_sprite: extension, traversal, overwrite branches ──────────────


def test_copy_sprite_appends_extension_and_succeeds(sprite: str) -> None:
    out = f"{BASE}/copy_no_ext"
    result = ok(run(export.copy_sprite(sprite, out)))
    assert result == f"Sprite copied to {out}.aseprite"
    assert Path(f"{out}.aseprite").exists()


def test_copy_sprite_keeps_existing_extension(sprite: str) -> None:
    out = f"{BASE}/copy_with_ext.aseprite"
    result = ok(run(export.copy_sprite(sprite, out)))
    assert result == f"Sprite copied to {out}"


def test_copy_sprite_rejects_traversal(sprite: str) -> None:
    result = run(export.copy_sprite(sprite, "../evil.aseprite"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_copy_sprite_rejects_existing_without_overwrite(sprite: str) -> None:
    out = f"{BASE}/copy_exists.aseprite"
    ok(run(export.copy_sprite(sprite, out)))
    result = run(export.copy_sprite(sprite, out))
    assert result == f"Output file {out} already exists"


def test_copy_sprite_overwrite_allowed(sprite: str) -> None:
    out = f"{BASE}/copy_overwrite.aseprite"
    ok(run(export.copy_sprite(sprite, out)))
    result = ok(run(export.copy_sprite(sprite, out, overwrite=True)))
    assert result == f"Sprite copied to {out}"


# ── export_frame: scale validation, traversal, extension branch ────────


def test_export_frame_rejects_scale_out_of_range(sprite: str) -> None:
    result = run(export.export_frame(sprite, 1, f"{BASE}/f.png", scale=0))
    assert result == "scale must be between 1 and 64"

    result = run(export.export_frame(sprite, 1, f"{BASE}/f.png", scale=65))
    assert result == "scale must be between 1 and 64"


def test_export_frame_rejects_traversal(sprite: str) -> None:
    result = run(export.export_frame(sprite, 1, "../evil.png"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_frame_keeps_existing_png_extension(sprite: str) -> None:
    out = f"{BASE}/frame_ext.png"
    result = ok(run(export.export_frame(sprite, 1, out, scale=1)))
    assert result == f"Frame 1 exported to {out} at 1x"


def test_export_frame_appends_png_extension(sprite: str) -> None:
    out = f"{BASE}/frame_no_ext"
    result = ok(run(export.export_frame(sprite, 1, out, scale=1)))
    assert result == f"Frame 1 exported to {out}.png at 1x"


def test_export_frame_out_of_range_frame_errors() -> None:
    # Aseprite's --frame-range silently clamps/no-ops for a frame past the
    # last one and the CLI still exits 0, so the frame index is validated up
    # front instead -- the same approach export_tag uses for tags. Without
    # it, the tool wrote a fully transparent PNG and called it a success.
    fresh = _fresh_sprite("export-frame-oob")
    out = f"{BASE}/frame_oob.png"
    result = run(export.export_frame(fresh, 999, out))
    assert result.startswith("Failed to export frame:"), result
    assert "Frame index out of range" in result
    assert not Path(out).exists(), "wrote a file for a frame that does not exist"


def test_export_frame_reports_subprocess_failure() -> None:
    # The frame-index precheck also goes through run_command (via
    # execute_lua_script_checked), so let the precheck succeed and fail only
    # the export itself -- otherwise this covers the validation branch
    # instead of the CLI-failure branch it is meant to exercise.
    fresh = _fresh_sprite("export-frame-fail")
    with (
        patch(
            "aseprite_mcp.tools.export.AsepriteCommand.execute_lua_script_checked"
        ) as check,
        patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m,
    ):
        check.return_value = (True, "OK")
        m.return_value = (False, "boom")
        result = run(export.export_frame(fresh, 1, f"{BASE}/frame_fail.png"))
    assert result == "Failed to export frame: boom"


def test_export_frame_reports_precheck_failure() -> None:
    # The precheck's own failure path, distinct from the CLI failure above.
    fresh = _fresh_sprite("export-frame-precheck-fail")
    with patch(
        "aseprite_mcp.tools.export.AsepriteCommand.execute_lua_script_checked"
    ) as check:
        check.return_value = (False, "no sprite")
        result = run(export.export_frame(fresh, 1, f"{BASE}/frame_precheck.png"))
    assert result == "Failed to export frame: no sprite"


def test_export_frame_renames_frame_numbered_sibling() -> None:
    # NOTE: verified directly against real Aseprite that --frame-range
    # writes exactly to the requested filename even for frame 2+ of a
    # multi-frame sprite - no numbered sibling is produced in practice, so
    # this rename fallback is not reachable through the real CLI as
    # documented. Covering it here via a mock instead, since it's still
    # live code that should behave correctly if that CLI behavior ever
    # changes (or differs on another platform/Aseprite version).
    fresh = _fresh_sprite("export-frame-rename")
    out = f"{BASE}/frame_rename.png"
    sibling = f"{BASE}/frame_rename1.png"
    with Path(sibling).open("wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (True, "")
        result = run(export.export_frame(fresh, 2, out, scale=1))
    assert result == f"Frame 2 exported to {out} at 1x"
    assert Path(out).exists()
    assert not Path(sibling).exists()


# ── export_spritesheet: validation branches ─────────────────────────────


def test_export_spritesheet_rejects_bad_sheet_type(sprite: str) -> None:
    result = run(
        export.export_spritesheet(sprite, f"{BASE}/sheet.png", sheet_type="diagonal")
    )
    assert result.startswith("sheet_type must be one of")


def test_export_spritesheet_rejects_scale_out_of_range(sprite: str) -> None:
    result = run(export.export_spritesheet(sprite, f"{BASE}/sheet.png", scale=0))
    assert result == "scale must be between 1 and 64"

    result = run(export.export_spritesheet(sprite, f"{BASE}/sheet.png", scale=100))
    assert result == "scale must be between 1 and 64"


def test_export_spritesheet_rejects_negative_padding(sprite: str) -> None:
    result = run(export.export_spritesheet(sprite, f"{BASE}/sheet.png", padding=-1))
    assert result == "padding must be >= 0"


def test_export_spritesheet_rejects_bad_data_format(sprite: str) -> None:
    result = run(
        export.export_spritesheet(sprite, f"{BASE}/sheet.png", data_format="json-weird")
    )
    assert result == "data_format must be 'json-array' or 'json-hash'"


def test_export_spritesheet_rejects_traversal_on_output(sprite: str) -> None:
    result = run(export.export_spritesheet(sprite, "../evil.png"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_spritesheet_rejects_traversal_on_data_filename(sprite: str) -> None:
    result = run(
        export.export_spritesheet(
            sprite, f"{BASE}/sheet_dt.png", data_filename="../evil.json"
        )
    )
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_spritesheet_keeps_existing_png_extension(sprite: str) -> None:
    out = f"{BASE}/sheet_ext.png"
    result = ok(run(export.export_spritesheet(sprite, out)))
    assert f"Sprite sheet exported to {out}" in result


def test_export_spritesheet_appends_png_extension(sprite: str) -> None:
    out = f"{BASE}/sheet_no_ext"
    result = ok(run(export.export_spritesheet(sprite, out)))
    assert f"Sprite sheet exported to {out}.png" in result


def test_export_spritesheet_reports_unknown_tag(sprite: str) -> None:
    result = run(
        export.export_spritesheet(sprite, f"{BASE}/sheet_badtag.png", tag_name="nope")
    )
    assert result.startswith("Failed to resolve tag:")


def test_export_spritesheet_json_hash_and_list_tags(sprite: str) -> None:
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
    assert Path(data).exists()


# ── export_layers ────────────────────────────────────────────────────────


def test_export_layers_rejects_traversal(sprite: str) -> None:
    result = run(export.export_layers(sprite, "../evil_dir"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_layers_include_hidden(sprite: str) -> None:
    out_dir = f"{BASE}/layers_hidden"
    result = ok(run(export.export_layers(sprite, out_dir, include_hidden=True)))
    assert "Layers exported to" in result


# ── export_tag ────────────────────────────────────────────────────────


def test_export_tag_rejects_scale_out_of_range(sprite: str) -> None:
    result = run(export.export_tag(sprite, "clip", f"{BASE}/tag.gif", scale=0))
    assert result == "scale must be between 1 and 64"

    result = run(export.export_tag(sprite, "clip", f"{BASE}/tag.gif", scale=65))
    assert result == "scale must be between 1 and 64"


def test_export_tag_rejects_traversal(sprite: str) -> None:
    result = run(export.export_tag(sprite, "clip", "../evil.gif"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_export_tag_reports_unknown_tag(sprite: str) -> None:
    result = run(export.export_tag(sprite, "no-such-tag", f"{BASE}/tag_missing.gif"))
    assert result.startswith("Failed to export tag:")
    assert "Tag not found" in result


def test_export_tag_png_sequence_with_scale(sprite: str) -> None:
    ok(run(animation.set_tag(sprite, "seq", 1, 1, "forward")))
    out = f"{BASE}/tag_seq.png"
    result = ok(run(export.export_tag(sprite, "seq", out, scale=2)))
    assert "exported to" in result


# ── import_image_as_layer ────────────────────────────────────────────────


def test_import_image_as_layer_success(sprite: str) -> None:
    png = f"{BASE}/import_src.png"
    ok(run(export.export_frame(sprite, 1, png, scale=1)))
    result = ok(run(export.import_image_as_layer(sprite, png, "imported", 1, 2, 2)))
    assert "imported onto 'imported' frame 1" in result


def test_import_image_as_layer_creates_new_layer(sprite: str) -> None:
    png = f"{BASE}/import_src2.png"
    ok(run(export.export_frame(sprite, 1, png, scale=1)))
    fresh_layer = "brand-new-import"
    result = ok(run(export.import_image_as_layer(sprite, png, fresh_layer)))
    assert fresh_layer in result


def test_import_image_as_layer_frame_out_of_range(sprite: str) -> None:
    png = f"{BASE}/import_src3.png"
    ok(run(export.export_frame(sprite, 1, png, scale=1)))
    result = run(export.import_image_as_layer(sprite, png, "ref", frame_index=999))
    assert result.startswith("Failed to import image:")
    assert "out of range" in result


# ── export_sprite: extension handling and gif branch ────────────────────


def test_export_sprite_appends_extension(sprite: str) -> None:
    out = f"{BASE}/export_no_ext"
    result = ok(run(export.export_sprite(sprite, out, "png")))
    assert result == f"Sprite exported successfully to {out}.png"


def test_export_sprite_keeps_existing_extension(sprite: str) -> None:
    out = f"{BASE}/export_ext.png"
    result = ok(run(export.export_sprite(sprite, out, "png")))
    assert result == f"Sprite exported successfully to {out}"


def test_export_sprite_gif_format(sprite: str) -> None:
    out = f"{BASE}/export.gif"
    result = ok(run(export.export_sprite(sprite, out, "gif")))
    assert result == f"Sprite exported successfully to {out}"


def test_export_sprite_multiframe_still_accepts_numbered_siblings() -> None:
    # A multi-frame sprite saved to a still image format doesn't produce
    # the exact requested filename - Aseprite writes frame-numbered
    # siblings (outN.png) instead. export_sprite must still report success
    # by finding those via glob, not just an exact Path.exists check.
    fresh = _fresh_sprite("export-sprite-multiframe")
    ok(run(canvas.add_frame(fresh)))
    out = f"{BASE}/export_multiframe.png"
    result = ok(run(export.export_sprite(fresh, out, "png")))
    assert result == f"Sprite exported successfully to {out}"


def test_export_sprite_reports_unwritable_format(sprite: str) -> None:
    # "json" is not a writable --save-as image format; Aseprite either
    # exits nonzero (-> "Failed to export sprite") or exits 0 without
    # producing a file (-> the explicit exited-0-but-no-file guard).
    # Either way this exercises the failure path at export.py's tail.
    out = f"{BASE}/export_bad_format"
    result = run(export.export_sprite(sprite, out, "json"))
    assert result.startswith("Failed to export sprite:")


# ── mocked run_command/execute_lua_script_checked: unreachable-via-real-
#    Aseprite failure branches ("exited 0 but wrote no X", nonzero exit) ──


def test_export_sprite_exited_zero_no_file() -> None:
    fresh = _fresh_sprite("export-sprite-zero")
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (True, "")
        result = run(export.export_sprite(fresh, f"{BASE}/export_sprite_zero_out.png"))
    assert "Aseprite exited 0 but wrote no file" in result


def test_export_sprite_reports_subprocess_failure() -> None:
    fresh = _fresh_sprite("export-sprite-fail")
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (False, "boom")
        result = run(export.export_sprite(fresh, f"{BASE}/export_sprite_fail_out.png"))
    assert result == "Failed to export sprite: boom"


def test_copy_sprite_reports_subprocess_failure() -> None:
    fresh = _fresh_sprite("copy-fail")
    with patch(
        "aseprite_mcp.tools.export.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(export.copy_sprite(fresh, f"{BASE}/copy_fail_out.aseprite"))
    assert result == "Failed to copy sprite: boom"


def test_copy_sprite_exited_zero_no_file() -> None:
    fresh = _fresh_sprite("copy-zero")
    with patch(
        "aseprite_mcp.tools.export.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "OK")
        result = run(export.copy_sprite(fresh, f"{BASE}/copy_zero_out.aseprite"))
    assert result == "Failed to copy sprite: Aseprite exited 0 but wrote no file"


def test_export_frame_renaming_finds_no_candidate() -> None:
    fresh = _fresh_sprite("frame-no-candidate")
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (True, "")
        result = run(export.export_frame(fresh, 1, f"{BASE}/frame_none.png"))
    assert (
        result == f"Export reported success but {BASE}/frame_none.png was not created"
    )


def test_export_spritesheet_tag_resolution_no_range_returned() -> None:
    fresh = _fresh_sprite("sheet-no-range")
    with patch(
        "aseprite_mcp.tools.export.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "no RANGE: line here")
        result = run(
            export.export_spritesheet(
                fresh, f"{BASE}/sheet_no_range.png", tag_name="whatever"
            )
        )
    assert result == "Failed to resolve tag: no range returned"


def test_export_spritesheet_exited_zero_no_sheet_file() -> None:
    fresh = _fresh_sprite("sheet-zero")
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (True, "")
        result = run(export.export_spritesheet(fresh, f"{BASE}/sheet_zero.png"))
    assert (
        result
        == "Failed to export sprite sheet: Aseprite exited 0 but wrote no sheet file"
    )


def test_export_spritesheet_exited_zero_no_data_file() -> None:
    # Sheet image is written for real by the real run_command call; only
    # the data_filename existence check is faked to report "missing", to
    # reach the second (data-file) guard without faking the whole command.
    fresh = _fresh_sprite("sheet-zero-data")
    out = f"{BASE}/sheet_zero_data.png"
    data_out = f"{BASE}/sheet_zero_data.json"
    real_exists = Path.exists

    async def fake_path_exists(p: str) -> bool:
        return False if p == data_out else real_exists(Path(p))

    with patch(
        "aseprite_mcp.tools.export.path_exists",
        AsyncMock(side_effect=fake_path_exists),
    ):
        result = run(export.export_spritesheet(fresh, out, data_filename=data_out))
    assert (
        result
        == "Failed to export sprite sheet: Aseprite exited 0 but wrote no data file"
    )


def test_export_layers_reports_subprocess_failure() -> None:
    fresh = _fresh_sprite("layers-fail")
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (False, "boom")
        result = run(export.export_layers(fresh, f"{BASE}/layers_fail_out"))
    assert result == "Failed to export layers: boom"


def test_export_layers_exited_zero_no_png_files() -> None:
    fresh = _fresh_sprite("layers-zero")
    out_dir = f"{BASE}/layers_zero_out"
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (True, "")
        result = run(export.export_layers(fresh, out_dir))
    assert result == "Failed to export layers: Aseprite exited 0 but wrote no PNG files"


def test_export_tag_exited_zero_no_file() -> None:
    fresh = _fresh_sprite("tag-zero")
    ok(run(animation.set_tag(fresh, "tagzero", 1, 1, "forward")))
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (True, "")
        result = run(export.export_tag(fresh, "tagzero", f"{BASE}/tag_zero.png"))
    assert result == "Failed to export tag: Aseprite exited 0 but wrote no file"


def test_export_tag_reports_tag_check_failure() -> None:
    # The tag-existence check (execute_lua_script_checked) itself bottoms
    # out in run_command, so mocking run_command with a single failing
    # return value fails THAT call, not the later export call - this test
    # exercises the tag-check's own "Failed to export tag" return, a
    # distinct branch from the export-call failure below.
    fresh = _fresh_sprite("tag-check-fail")
    ok(run(animation.set_tag(fresh, "tagcheckfail", 1, 1, "forward")))
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.return_value = (False, "boom")
        result = run(export.export_tag(fresh, "tagcheckfail", f"{BASE}/tag_fail.png"))
    assert result == "Failed to export tag: boom"


def test_export_tag_reports_export_call_subprocess_failure() -> None:
    # First run_command call is the tag-existence check (must succeed so
    # export_tag proceeds past line 313); second is the real --tag export
    # call, which is the one this test forces to fail.
    fresh = _fresh_sprite("tag-export-fail")
    ok(run(animation.set_tag(fresh, "tagexportfail", 1, 1, "forward")))
    with patch("aseprite_mcp.tools.export.AsepriteCommand.run_command") as m:
        m.side_effect = [(True, "OK"), (False, "boom")]
        result = run(
            export.export_tag(fresh, "tagexportfail", f"{BASE}/tag_export_fail.png")
        )
    assert result == "Failed to export tag: boom"
