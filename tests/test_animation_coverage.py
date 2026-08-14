"""Coverage-gap tests for animation.py.

Covers validation paths, branches, and tools not exercised by
test_animation.py or test_error_propagation.py.

Uses its own module-scoped sprite (module name "animation_coverage") so it
does not interfere with test_animation.py's frame/tag state. Frame budget:
the shared `sprite` fixture starts at 1 frame; the first test here grows it
to 6 frames and every range-based test below stays inside 1..6. Frame
deletion down to a single frame (for delete_frame's "only frame" guard) uses
a dedicated one-off sprite instead of exhausting the shared one.
"""

import json
from unittest.mock import patch

from conftest import BASE, ok, run

from aseprite_mcp.tools import animation, canvas

MISSING = f"{BASE}/does_not_exist.aseprite"


# --- missing-file guard (os.path.exists check) shared by every tool ---
# These return "File {filename} not found" -- starts with "File", so ok()
# would wrongly pass; assert the literal substring instead.


def test_missing_file_every_tool() -> None:
    checks = [
        animation.add_frames(MISSING, 1),
        animation.set_frame_duration_all(MISSING, 100),
        animation.set_layer_visibility(MISSING, "body"),
        animation.set_layer_opacity(MISSING, "body", 100),
        animation.get_sprite_info(MISSING),
        animation.duplicate_frame_range(MISSING, 1, 1),
        animation.set_cel_position(MISSING, "body", 1, 0, 0),
        animation.tween_cel_positions(MISSING, "body", 1, 1, 0, 0, 1, 1),
        animation.offset_cel_positions(MISSING, "body", 1, 1, 1, 1),
        animation.create_cel(MISSING, "body", 1),
        animation.clear_cel(MISSING, "body", 1),
        animation.copy_cel(MISSING, "body", 1, 1),
        animation.copy_frame(MISSING, 1),
        animation.propagate_frame_to_range(MISSING, 1, 1, 1),
        animation.set_tag(MISSING, "tag", 1, 1),
        animation.set_onion_skin(MISSING),
        animation.propagate_cels(MISSING, ["body"], 1, 1, 1),
        animation.tween_cel_positions_eased(MISSING, "body", 1, 1, 0, 0, 1, 1),
        animation.oscillate_cel_positions(MISSING, "body", 1, 1),
        animation.tween_cel_opacity_eased(MISSING, "body", 1, 1, 0, 255),
        animation.tween_cel_scale_eased(MISSING, "body", 1, 1, 1.0, 2.0),
        animation.delete_frame(MISSING, 1),
        animation.delete_tag(MISSING, "tag"),
        animation.set_cel_opacity(MISSING, "body", 1, 100),
    ]
    for coro in checks:
        result = run(coro)
        assert "not found" in result, result


# --- grow the shared sprite to 6 frames for range-based tests below ---


def test_add_frames_grows_sprite(sprite: str) -> None:
    ok(run(animation.add_frames(sprite, 5, 100)))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    assert info["frames"] == 6


def test_add_frames_rejects_count_below_one(sprite: str) -> None:
    result = run(animation.add_frames(sprite, 0))
    assert result == "Count must be >= 1"


def test_add_frames_no_duration(sprite: str) -> None:
    # duration_ms=None takes the false branch of "duration_ms is not None"
    ok(run(animation.add_frames(sprite, 1, None)))


def test_add_frames_zero_duration_skips_duration_line(sprite: str) -> None:
    # duration_ms=0 is not None but fails "> 0", covering the other half
    # of the "and" short-circuit on line ~23.
    ok(run(animation.add_frames(sprite, 1, 0)))


# --- set_frame_duration_all ---


def test_set_frame_duration_all_success(sprite: str) -> None:
    ok(run(animation.set_frame_duration_all(sprite, 150)))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    assert all(d == 150 for d in info["durations_ms"])


def test_set_frame_duration_all_rejects_zero(sprite: str) -> None:
    result = run(animation.set_frame_duration_all(sprite, 0))
    assert result == "Duration must be > 0"


def test_set_frame_duration_all_rejects_negative(sprite: str) -> None:
    result = run(animation.set_frame_duration_all(sprite, -5))
    assert result == "Duration must be > 0"


# --- set_layer_visibility ---


def test_set_layer_visibility_true_and_false(sprite: str) -> None:
    ok(run(animation.set_layer_visibility(sprite, "body", visible=False)))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    layer = next(item for item in info["layers"] if item["name"] == "body")
    assert layer["visible"] is False
    ok(run(animation.set_layer_visibility(sprite, "body", visible=True)))


# --- set_layer_opacity ---


def test_set_layer_opacity_success(sprite: str) -> None:
    ok(run(animation.set_layer_opacity(sprite, "body", 128)))


def test_set_layer_opacity_rejects_below_zero(sprite: str) -> None:
    result = run(animation.set_layer_opacity(sprite, "body", -1))
    assert result == "Opacity must be between 0 and 255"


def test_set_layer_opacity_rejects_above_255(sprite: str) -> None:
    result = run(animation.set_layer_opacity(sprite, "body", 256))
    assert result == "Opacity must be between 0 and 255"


# --- get_sprite_info: exercise groups/tags/colormode branches ---


def test_get_sprite_info_reports_group_and_tag(sprite: str) -> None:
    ok(run(canvas.add_group(sprite, "grp")))
    ok(run(canvas.add_layer(sprite, "child", group="grp")))
    ok(run(animation.set_tag(sprite, "info_tag", 1, 2, "forward")))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    child = next(item for item in info["layers"] if item["name"] == "child")
    assert child["parent"] == "grp"
    tag = next(t for t in info["tags"] if t["name"] == "info_tag")
    assert tag["direction"] == "forward"
    ok(run(animation.delete_tag(sprite, "info_tag")))


# --- duplicate_frame_range ---


def test_duplicate_frame_range_success(sprite: str) -> None:
    before = json.loads(run(animation.get_sprite_info(sprite)))["frames"]
    ok(run(animation.duplicate_frame_range(sprite, 1, 2, 1)))
    after = json.loads(run(animation.get_sprite_info(sprite)))["frames"]
    assert after == before + 2


def test_duplicate_frame_range_rejects_times_below_one(sprite: str) -> None:
    result = run(animation.duplicate_frame_range(sprite, 1, 2, 0))
    assert result == "Times must be >= 1"


def test_duplicate_frame_range_out_of_bounds(sprite: str) -> None:
    result = run(animation.duplicate_frame_range(sprite, 1, 999, 1))
    assert "Frame range out of bounds" in result


def test_duplicate_frame_range_start_after_end(sprite: str) -> None:
    result = run(animation.duplicate_frame_range(sprite, 3, 1, 1))
    assert "Frame range out of bounds" in result


# --- set_cel_position ---


def test_set_cel_position_existing_cel(sprite: str) -> None:
    ok(run(animation.set_cel_position(sprite, "body", 1, 4, 4)))


def test_set_cel_position_create_if_missing_no_source(sprite: str) -> None:
    # frame 3 has no "body" cel yet; create_if_missing=True, no source ->
    # falls into the "no source_cel" branch that creates a blank image.
    ok(run(animation.set_cel_position(sprite, "body", 3, 1, 1, create_if_missing=True)))


def test_set_cel_position_create_if_missing_with_source(sprite: str) -> None:
    ok(
        run(
            animation.set_cel_position(
                sprite, "body", 4, 2, 2, create_if_missing=True, source_frame_index=1
            )
        )
    )


def test_set_cel_position_missing_cel_no_create_is_noop(sprite: str) -> None:
    # create_if_missing defaults False and there's no cel on frame 5 yet;
    # the Lua "if not cel then return end" branch fires but the script
    # still prints OK, so this is a fabricated success (no bug fix here,
    # just documenting current behavior per task instructions).
    result = ok(run(animation.set_cel_position(sprite, "body", 5, 9, 9)))
    assert "Cel position set" in result


# --- tween_cel_positions ---


def test_tween_cel_positions_success(sprite: str) -> None:
    ok(run(animation.tween_cel_positions(sprite, "body", 1, 2, 0, 0, 4, 4)))


def test_tween_cel_positions_out_of_bounds(sprite: str) -> None:
    result = run(animation.tween_cel_positions(sprite, "body", 1, 999, 0, 0, 4, 4))
    assert "Frame range out of bounds" in result


def test_tween_cel_positions_missing_layer(sprite: str) -> None:
    result = run(animation.tween_cel_positions(sprite, "NOPE", 1, 2, 0, 0, 4, 4))
    assert "Layer not found" in result


def test_tween_cel_positions_create_missing_with_source(sprite: str) -> None:
    ok(
        run(
            animation.tween_cel_positions(
                sprite,
                "body",
                1,
                3,
                0,
                0,
                2,
                2,
                create_missing_cels=True,
                source_frame_index=1,
            )
        )
    )


def test_tween_cel_positions_single_frame_span_zero(sprite: str) -> None:
    # start_frame == end_frame -> span == 0, covers the "span > 0" false
    # branch (t stays 0).
    ok(run(animation.tween_cel_positions(sprite, "body", 1, 1, 0, 0, 5, 5)))


# --- offset_cel_positions ---


def test_offset_cel_positions_success(sprite: str) -> None:
    ok(run(animation.offset_cel_positions(sprite, "body", 1, 2, 1, -1)))


def test_offset_cel_positions_out_of_bounds(sprite: str) -> None:
    result = run(animation.offset_cel_positions(sprite, "body", 1, 999, 1, 1))
    assert "Frame range out of bounds" in result


def test_offset_cel_positions_missing_layer(sprite: str) -> None:
    result = run(animation.offset_cel_positions(sprite, "NOPE", 1, 2, 1, 1))
    assert "Layer not found" in result


# --- create_cel ---


def test_create_cel_success(sprite: str) -> None:
    ok(run(animation.create_cel(sprite, "body", 6, 3, 3)))


def test_create_cel_out_of_range(sprite: str) -> None:
    result = run(animation.create_cel(sprite, "body", 999, 0, 0))
    assert "Frame index out of range" in result


def test_create_cel_missing_layer(sprite: str) -> None:
    result = run(animation.create_cel(sprite, "NOPE", 1, 0, 0))
    assert "Layer not found" in result


def test_create_cel_already_exists_is_noop(sprite: str) -> None:
    # frame 1 already has a "body" cel; the Lua "if cel then return end"
    # branch fires but still prints OK -- fabricated success, documenting
    # current behavior only.
    result = ok(run(animation.create_cel(sprite, "body", 1, 0, 0)))
    assert "Cel created" in result


# --- clear_cel ---


def test_clear_cel_success(sprite: str) -> None:
    ok(run(animation.create_cel(sprite, "body", 6, 0, 0)))
    ok(run(animation.clear_cel(sprite, "body", 6)))


def test_clear_cel_out_of_range(sprite: str) -> None:
    result = run(animation.clear_cel(sprite, "body", 999))
    assert "Frame index out of range" in result


def test_clear_cel_missing_layer(sprite: str) -> None:
    result = run(animation.clear_cel(sprite, "NOPE", 1))
    assert "Layer not found" in result


def test_clear_cel_no_cel_is_noop(sprite: str) -> None:
    # No cel on frame 6 after the clear above; the Lua "if cel then"
    # guard skips deleteCel but still succeeds.
    ok(run(animation.clear_cel(sprite, "body", 6)))


# --- copy_cel ---


def test_copy_cel_success_replace_true(sprite: str) -> None:
    ok(run(animation.copy_cel(sprite, "body", 1, 2, replace=True)))


def test_copy_cel_success_replace_false_no_existing(sprite: str) -> None:
    ok(run(animation.create_cel(sprite, "body", 6, 0, 0)))
    ok(run(animation.clear_cel(sprite, "body", 6)))
    ok(run(animation.copy_cel(sprite, "body", 1, 6, replace=False)))


def test_copy_cel_replace_false_existing_dst_is_noop(sprite: str) -> None:
    # dst already has a cel and replace=False -> "if not dst" is false,
    # skip creating a new cel, but still prints OK (fabricated success).
    result = ok(run(animation.copy_cel(sprite, "body", 1, 2, replace=False)))
    assert "Cel copied" in result


def test_copy_cel_source_out_of_range(sprite: str) -> None:
    result = run(animation.copy_cel(sprite, "body", 999, 1))
    assert "Source frame out of range" in result


def test_copy_cel_target_out_of_range(sprite: str) -> None:
    result = run(animation.copy_cel(sprite, "body", 1, 999))
    assert "Target frame out of range" in result


def test_copy_cel_missing_layer(sprite: str) -> None:
    result = run(animation.copy_cel(sprite, "NOPE", 1, 2))
    assert "Layer not found" in result


def test_copy_cel_no_source_cel_is_noop(sprite: str) -> None:
    # Ensure frame 6 has no cel right before use (earlier tests in this
    # file may have populated it) so "if not src then return end" fires;
    # the script still prints OK -- fabricated success.
    ok(run(animation.clear_cel(sprite, "body", 6)))
    result = ok(run(animation.copy_cel(sprite, "body", 6, 2)))
    assert "Cel copied" in result


# --- copy_frame ---


def test_copy_frame_append_new(sprite: str) -> None:
    before = json.loads(run(animation.get_sprite_info(sprite)))["frames"]
    result = ok(run(animation.copy_frame(sprite, 1)))
    assert "copied to new frame" in result
    after = json.loads(run(animation.get_sprite_info(sprite)))["frames"]
    assert after == before + 1


def test_copy_frame_explicit_target_overwrite(sprite: str) -> None:
    result = ok(run(animation.copy_frame(sprite, 1, 2, overwrite=True)))
    assert "copied to frame 2" in result


def test_copy_frame_explicit_target_no_overwrite(sprite: str) -> None:
    ok(run(animation.copy_frame(sprite, 1, 3, overwrite=False)))


def test_copy_frame_source_out_of_range(sprite: str) -> None:
    result = run(animation.copy_frame(sprite, 999))
    assert "Source frame out of range" in result


def test_copy_frame_target_out_of_range_is_fabricated_success(sprite: str) -> None:
    # dst_idx out of range -> Lua "if dst_idx < 1 or dst_idx > #spr.frames
    # then return end" fires *inside* the transaction, still prints OK;
    # Python reports success. Fabricated success, documenting current
    # behavior only (not touching source per task instructions).
    result = ok(run(animation.copy_frame(sprite, 1, 999, overwrite=True)))
    assert "copied to frame 999" in result


# --- propagate_frame_to_range ---


def test_propagate_frame_to_range_success(sprite: str) -> None:
    ok(run(animation.propagate_frame_to_range(sprite, 1, 2, 3, overwrite=True)))


def test_propagate_frame_to_range_no_overwrite(sprite: str) -> None:
    ok(run(animation.propagate_frame_to_range(sprite, 1, 2, 3, overwrite=False)))


def test_propagate_frame_to_range_source_out_of_range(sprite: str) -> None:
    result = run(animation.propagate_frame_to_range(sprite, 999, 1, 2))
    assert "Source frame out of range" in result


def test_propagate_frame_to_range_bounds_out_of_range(sprite: str) -> None:
    result = run(animation.propagate_frame_to_range(sprite, 1, 1, 999))
    assert "Frame range out of bounds" in result


# --- set_tag ---


def test_set_tag_all_directions(sprite: str) -> None:
    for direction in ("forward", "reverse", "pingpong", "pingpong_reverse"):
        ok(run(animation.set_tag(sprite, f"dir_{direction}", 1, 2, direction)))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    names = {t["name"]: t["direction"] for t in info["tags"]}
    assert names["dir_forward"] == "forward"
    assert names["dir_reverse"] == "reverse"
    assert names["dir_pingpong"] == "pingpong"
    assert names["dir_pingpong_reverse"] == "pingpong_reverse"


def test_set_tag_rejects_unsupported_direction(sprite: str) -> None:
    result = run(animation.set_tag(sprite, "bad", 1, 2, "sideways"))
    assert result.startswith("Unsupported direction")


def test_set_tag_updates_existing_tag(sprite: str) -> None:
    ok(run(animation.set_tag(sprite, "reused", 1, 2, "forward")))
    ok(run(animation.set_tag(sprite, "reused", 2, 3, "reverse")))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    tag = next(t for t in info["tags"] if t["name"] == "reused")
    assert tag["from"] == 2
    assert tag["to"] == 3
    assert tag["direction"] == "reverse"


def test_set_tag_out_of_bounds(sprite: str) -> None:
    result = run(animation.set_tag(sprite, "oob", 1, 999))
    assert "Frame range out of bounds" in result


# --- set_onion_skin: pure-Python tool, full branch coverage ---


def test_set_onion_skin_success(sprite: str) -> None:
    result = ok(
        run(
            animation.set_onion_skin(
                sprite, enabled=True, before=2, after=2, opacity=128
            )
        )
    )
    assert "UI-only in batch mode" in result


def test_set_onion_skin_rejects_negative_before(sprite: str) -> None:
    result = run(
        animation.set_onion_skin(sprite, enabled=True, before=-1, after=2, opacity=128)
    )
    assert result == "Before/after must be >= 0"


def test_set_onion_skin_rejects_negative_after(sprite: str) -> None:
    result = run(
        animation.set_onion_skin(sprite, enabled=True, before=2, after=-1, opacity=128)
    )
    assert result == "Before/after must be >= 0"


def test_set_onion_skin_rejects_opacity_below_zero(sprite: str) -> None:
    result = run(
        animation.set_onion_skin(sprite, enabled=True, before=2, after=2, opacity=-1)
    )
    assert result == "Opacity must be between 0 and 255"


def test_set_onion_skin_rejects_opacity_above_255(sprite: str) -> None:
    result = run(
        animation.set_onion_skin(sprite, enabled=True, before=2, after=2, opacity=256)
    )
    assert result == "Opacity must be between 0 and 255"


def test_set_onion_skin_disabled(sprite: str) -> None:
    result = ok(run(animation.set_onion_skin(sprite, enabled=False)))
    assert "enabled=False" in result


# --- propagate_cels ---


def test_propagate_cels_success(sprite: str) -> None:
    ok(run(animation.propagate_cels(sprite, ["body"], 1, 2, 3, replace=True)))


def test_propagate_cels_no_replace(sprite: str) -> None:
    ok(run(animation.propagate_cels(sprite, ["body"], 1, 2, 3, replace=False)))


def test_propagate_cels_rejects_empty_layer_list(sprite: str) -> None:
    result = run(animation.propagate_cels(sprite, [], 1, 2, 3))
    assert result == "Layer names list cannot be empty"


def test_propagate_cels_source_out_of_range(sprite: str) -> None:
    result = run(animation.propagate_cels(sprite, ["body"], 999, 1, 2))
    assert "Source frame out of range" in result


def test_propagate_cels_bounds_out_of_range(sprite: str) -> None:
    result = run(animation.propagate_cels(sprite, ["body"], 1, 1, 999))
    assert "Frame range out of bounds" in result


def test_propagate_cels_no_layers_found(sprite: str) -> None:
    result = run(animation.propagate_cels(sprite, ["NOPE_LAYER"], 1, 2, 3))
    assert "No layers found" in result


def test_propagate_cels_partial_layers_found(sprite: str) -> None:
    # one real, one bogus name -> targets list has exactly 1 entry, still
    # succeeds because "#targets == 0" is false.
    ok(run(animation.propagate_cels(sprite, ["body", "NOPE"], 1, 2, 3)))


# --- tween_cel_positions_eased ---


def test_tween_cel_positions_eased_all_modes(sprite: str) -> None:
    for easing in ("linear", "ease_in", "ease_out", "ease_in_out", "smoothstep"):
        ok(
            run(
                animation.tween_cel_positions_eased(
                    sprite, "body", 1, 3, 0, 0, 4, 4, easing=easing
                )
            )
        )


def test_tween_cel_positions_eased_default_via_empty_string(sprite: str) -> None:
    # easing="" is falsy -> "(easing or 'smoothstep')" fallback branch.
    ok(
        run(
            animation.tween_cel_positions_eased(
                sprite, "body", 1, 2, 0, 0, 2, 2, easing=""
            )
        )
    )


def test_tween_cel_positions_eased_normalizes_case_and_whitespace(sprite: str) -> None:
    ok(
        run(
            animation.tween_cel_positions_eased(
                sprite, "body", 1, 2, 0, 0, 2, 2, easing=" SMOOTHSTEP "
            )
        )
    )


def test_tween_cel_positions_eased_rejects_unsupported(sprite: str) -> None:
    result = run(
        animation.tween_cel_positions_eased(
            sprite, "body", 1, 2, 0, 0, 2, 2, easing="bogus"
        )
    )
    assert result.startswith("Unsupported easing")


def test_tween_cel_positions_eased_out_of_bounds(sprite: str) -> None:
    result = run(
        animation.tween_cel_positions_eased(sprite, "body", 1, 999, 0, 0, 2, 2)
    )
    assert "Frame range out of bounds" in result


def test_tween_cel_positions_eased_missing_layer(sprite: str) -> None:
    result = run(animation.tween_cel_positions_eased(sprite, "NOPE", 1, 2, 0, 0, 2, 2))
    assert "Layer not found" in result


def test_tween_cel_positions_eased_create_missing_with_source(sprite: str) -> None:
    ok(
        run(
            animation.tween_cel_positions_eased(
                sprite,
                "body",
                1,
                3,
                0,
                0,
                2,
                2,
                create_missing_cels=True,
                source_frame_index=1,
            )
        )
    )


def test_tween_cel_positions_eased_single_frame_span_zero(sprite: str) -> None:
    ok(run(animation.tween_cel_positions_eased(sprite, "body", 1, 1, 0, 0, 5, 5)))


# --- oscillate_cel_positions ---


def test_oscillate_cel_positions_success(sprite: str) -> None:
    ok(
        run(
            animation.oscillate_cel_positions(
                sprite,
                "body",
                1,
                3,
                amplitude_x=2,
                amplitude_y=1,
                cycles=1.0,
                phase_deg=90.0,
            )
        )
    )


def test_oscillate_cel_positions_out_of_bounds(sprite: str) -> None:
    result = run(animation.oscillate_cel_positions(sprite, "body", 1, 999))
    assert "Frame range out of bounds" in result


def test_oscillate_cel_positions_missing_layer(sprite: str) -> None:
    result = run(animation.oscillate_cel_positions(sprite, "NOPE", 1, 2))
    assert "Layer not found" in result


def test_oscillate_cel_positions_create_missing_with_source(sprite: str) -> None:
    ok(
        run(
            animation.oscillate_cel_positions(
                sprite,
                "body",
                1,
                3,
                amplitude_x=1,
                amplitude_y=1,
                create_missing_cels=True,
                source_frame_index=1,
            )
        )
    )


def test_oscillate_cel_positions_single_frame_span_zero(sprite: str) -> None:
    ok(run(animation.oscillate_cel_positions(sprite, "body", 1, 1, amplitude_x=3)))


# --- tween_cel_opacity_eased ---


def test_tween_cel_opacity_eased_success(sprite: str) -> None:
    ok(run(animation.tween_cel_opacity_eased(sprite, "body", 1, 3, 255, 0)))


def test_tween_cel_opacity_eased_rejects_start_below_zero(sprite: str) -> None:
    result = run(animation.tween_cel_opacity_eased(sprite, "body", 1, 2, -1, 255))
    assert result == "Opacity must be between 0 and 255"


def test_tween_cel_opacity_eased_rejects_start_above_255(sprite: str) -> None:
    result = run(animation.tween_cel_opacity_eased(sprite, "body", 1, 2, 256, 0))
    assert result == "Opacity must be between 0 and 255"


def test_tween_cel_opacity_eased_rejects_end_below_zero(sprite: str) -> None:
    result = run(animation.tween_cel_opacity_eased(sprite, "body", 1, 2, 255, -1))
    assert result == "Opacity must be between 0 and 255"


def test_tween_cel_opacity_eased_rejects_end_above_255(sprite: str) -> None:
    result = run(animation.tween_cel_opacity_eased(sprite, "body", 1, 2, 0, 256))
    assert result == "Opacity must be between 0 and 255"


def test_tween_cel_opacity_eased_rejects_unsupported_easing(sprite: str) -> None:
    result = run(
        animation.tween_cel_opacity_eased(sprite, "body", 1, 2, 0, 255, easing="bogus")
    )
    assert result.startswith("Unsupported easing")


def test_tween_cel_opacity_eased_out_of_bounds(sprite: str) -> None:
    result = run(animation.tween_cel_opacity_eased(sprite, "body", 1, 999, 0, 255))
    assert "Frame range out of bounds" in result


def test_tween_cel_opacity_eased_missing_layer(sprite: str) -> None:
    result = run(animation.tween_cel_opacity_eased(sprite, "NOPE", 1, 2, 0, 255))
    assert "Layer not found" in result


def test_tween_cel_opacity_eased_create_missing_with_source(sprite: str) -> None:
    ok(
        run(
            animation.tween_cel_opacity_eased(
                sprite,
                "body",
                1,
                3,
                0,
                255,
                create_missing_cels=True,
                source_frame_index=1,
            )
        )
    )


def test_tween_cel_opacity_eased_single_frame_span_zero(sprite: str) -> None:
    ok(run(animation.tween_cel_opacity_eased(sprite, "body", 1, 1, 0, 255)))


def test_tween_cel_opacity_eased_all_easing_modes(sprite: str) -> None:
    for easing in ("linear", "ease_in", "ease_out", "ease_in_out", "smoothstep"):
        ok(
            run(
                animation.tween_cel_opacity_eased(
                    sprite, "body", 1, 2, 0, 255, easing=easing
                )
            )
        )


# --- tween_cel_scale_eased ---


def test_tween_cel_scale_eased_success_center_anchor(sprite: str) -> None:
    ok(run(animation.tween_cel_scale_eased(sprite, "body", 1, 2, 1.0, 2.0)))


def test_tween_cel_scale_eased_topleft_anchor(sprite: str) -> None:
    ok(
        run(
            animation.tween_cel_scale_eased(
                sprite, "body", 1, 2, 1.0, 0.5, anchor="topleft"
            )
        )
    )


def test_tween_cel_scale_eased_rejects_start_scale_zero(sprite: str) -> None:
    result = run(animation.tween_cel_scale_eased(sprite, "body", 1, 2, 0, 2.0))
    assert result == "Scale must be > 0"


def test_tween_cel_scale_eased_rejects_end_scale_negative(sprite: str) -> None:
    result = run(animation.tween_cel_scale_eased(sprite, "body", 1, 2, 1.0, -1))
    assert result == "Scale must be > 0"


def test_tween_cel_scale_eased_rejects_unsupported_easing(sprite: str) -> None:
    result = run(
        animation.tween_cel_scale_eased(sprite, "body", 1, 2, 1.0, 2.0, easing="bogus")
    )
    assert result.startswith("Unsupported easing")


def test_tween_cel_scale_eased_default_easing_via_empty_string(sprite: str) -> None:
    ok(run(animation.tween_cel_scale_eased(sprite, "body", 1, 2, 1.0, 2.0, easing="")))


def test_tween_cel_scale_eased_rejects_unsupported_anchor(sprite: str) -> None:
    result = run(
        animation.tween_cel_scale_eased(
            sprite, "body", 1, 2, 1.0, 2.0, anchor="bottomright"
        )
    )
    assert result.startswith("Unsupported anchor")


def test_tween_cel_scale_eased_default_anchor_via_empty_string(sprite: str) -> None:
    ok(run(animation.tween_cel_scale_eased(sprite, "body", 1, 2, 1.0, 2.0, anchor="")))


def test_tween_cel_scale_eased_out_of_bounds(sprite: str) -> None:
    result = run(animation.tween_cel_scale_eased(sprite, "body", 1, 999, 1.0, 2.0))
    assert "Frame range out of bounds" in result


def test_tween_cel_scale_eased_missing_layer(sprite: str) -> None:
    result = run(animation.tween_cel_scale_eased(sprite, "NOPE", 1, 2, 1.0, 2.0))
    assert "Layer not found" in result


def test_tween_cel_scale_eased_explicit_source_frame(sprite: str) -> None:
    ok(
        run(
            animation.tween_cel_scale_eased(
                sprite, "body", 1, 3, 1.0, 1.5, source_frame_index=1
            )
        )
    )


def test_tween_cel_scale_eased_source_frame_out_of_range(sprite: str) -> None:
    result = run(
        animation.tween_cel_scale_eased(
            sprite, "body", 1, 2, 1.0, 2.0, source_frame_index=999
        )
    )
    assert "Source frame out of range" in result


def test_tween_cel_scale_eased_no_source_cel(sprite: str) -> None:
    # Ensure frame 6 has no "body" cel right before use so
    # source_frame_index=6 hits "Source cel not found".
    ok(run(animation.clear_cel(sprite, "body", 6)))
    result = run(
        animation.tween_cel_scale_eased(
            sprite, "body", 6, 6, 1.0, 2.0, source_frame_index=6
        )
    )
    assert "Source cel not found" in result


def test_tween_cel_scale_eased_no_replace_keeps_existing(sprite: str) -> None:
    ok(
        run(
            animation.tween_cel_scale_eased(
                sprite, "body", 1, 2, 1.0, 1.2, replace=False, create_missing_cels=True
            )
        )
    )


def test_tween_cel_scale_eased_no_create_missing(sprite: str) -> None:
    # create_missing_cels=False and dst has no cel after a clear -> the
    # "if not dst_cel and {create_flag}" branch is false, no cel is
    # created, but the script still reports OK.
    ok(run(animation.clear_cel(sprite, "body", 6)))
    result = ok(
        run(
            animation.tween_cel_scale_eased(
                sprite,
                "body",
                6,
                6,
                1.0,
                1.0,
                replace=True,
                create_missing_cels=False,
                source_frame_index=1,
            )
        )
    )
    assert "Tweened cel scale" in result


# --- delete_frame ---


def test_delete_frame_success(sprite: str) -> None:
    before = json.loads(run(animation.get_sprite_info(sprite)))["frames"]
    ok(run(animation.delete_frame(sprite, before)))
    after = json.loads(run(animation.get_sprite_info(sprite)))["frames"]
    assert after == before - 1


def test_delete_frame_out_of_range(sprite: str) -> None:
    result = run(animation.delete_frame(sprite, 999))
    assert "Frame index out of range" in result


def test_delete_frame_rejects_only_frame(base_dir: str) -> None:
    # Needs a genuinely single-frame sprite; the shared module sprite has
    # accumulated many frames by this point in the file.
    path = f"{base_dir}/animation_coverage_single_frame.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    result = run(animation.delete_frame(path, 1))
    assert result == "Failed to delete frame: Cannot delete the only frame"


# --- delete_tag ---


def test_delete_tag_success(sprite: str) -> None:
    ok(run(animation.set_tag(sprite, "to_delete", 1, 2, "forward")))
    ok(run(animation.delete_tag(sprite, "to_delete")))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    assert all(t["name"] != "to_delete" for t in info["tags"])


def test_delete_tag_not_found(sprite: str) -> None:
    result = run(animation.delete_tag(sprite, "NO_SUCH_TAG"))
    assert result == "Failed to delete tag: Tag not found"


# --- set_cel_opacity ---


def test_set_cel_opacity_success(sprite: str) -> None:
    ok(run(animation.set_cel_opacity(sprite, "body", 1, 200)))


def test_set_cel_opacity_rejects_below_zero(sprite: str) -> None:
    result = run(animation.set_cel_opacity(sprite, "body", 1, -1))
    assert result == "Opacity must be between 0 and 255"


def test_set_cel_opacity_rejects_above_255(sprite: str) -> None:
    result = run(animation.set_cel_opacity(sprite, "body", 1, 256))
    assert result == "Opacity must be between 0 and 255"


def test_set_cel_opacity_out_of_range_frame(sprite: str) -> None:
    result = run(animation.set_cel_opacity(sprite, "body", 999, 100))
    assert "Frame index out of range" in result


def test_set_cel_opacity_missing_layer(sprite: str) -> None:
    result = run(animation.set_cel_opacity(sprite, "NOPE", 1, 100))
    assert "Layer not found" in result


def test_set_cel_opacity_no_cel_at_layer_frame(sprite: str) -> None:
    # frame 6 has no cel on "body" at this point (cleared earlier in the
    # file) -> "No cel at that layer/frame" guard.
    ok(run(animation.clear_cel(sprite, "body", 6)))
    result = run(animation.set_cel_opacity(sprite, "body", 6, 100))
    assert "No cel at that layer/frame" in result


# --- mocked execute_lua_script_checked: process-level subprocess failures ---


def test_add_frames_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.animation.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(animation.add_frames(sprite, 1))
    assert result == "Failed to add frames: boom"


def test_set_frame_duration_all_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.animation.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(animation.set_frame_duration_all(sprite, 100))
    assert result == "Failed to set frame durations: boom"


def test_set_layer_visibility_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.animation.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(animation.set_layer_visibility(sprite, "body", visible=True))
    assert result == "Failed to set layer visibility: boom"


def test_set_layer_opacity_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.animation.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(animation.set_layer_opacity(sprite, "body", 100))
    assert result == "Failed to set layer opacity: boom"


def test_get_sprite_info_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.animation.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(animation.get_sprite_info(sprite))
    assert result == "Failed to get sprite info: boom"


def test_set_cel_position_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.animation.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(animation.set_cel_position(sprite, "body", 1, 5, 5))
    assert result == "Failed to set cel position: boom"
