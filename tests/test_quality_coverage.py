"""Coverage tests for aseprite_mcp/tools/quality.py.

Covers the four @mcp.tool() entry points (ensure_layers_present,
validate_scene, audit_animation, animation_sanitize) plus the pure-Python
parser helpers (_parse_layer_frame_ranges, _parse_overlap_pairs).

The module-scoped `sprite` fixture (32x32, "body" layer painted on frame 1)
is reused and extended with extra frames/layers as each test needs, per
tests/conftest.py's guidance to avoid creating whole new sprites.
"""

import json

from conftest import ok, run

from aseprite_mcp.tools import animation, canvas, drawing, quality
from aseprite_mcp.tools.quality import _parse_layer_frame_ranges, _parse_overlap_pairs

# ---------------------------------------------------------------------------
# _parse_layer_frame_ranges (pure function, no Aseprite process)
# ---------------------------------------------------------------------------


def test_parse_layer_frame_ranges_none():
    assert _parse_layer_frame_ranges(None) == "{}"


def test_parse_layer_frame_ranges_empty_list():
    assert _parse_layer_frame_ranges([]) == "{}"


def test_parse_layer_frame_ranges_single_range():
    result = _parse_layer_frame_ranges(["body:1-8"])
    assert result == '{["body"]={{1,8}},}'


def test_parse_layer_frame_ranges_multiple_spans_same_layer():
    result = _parse_layer_frame_ranges(["body:1-8,17-24"])
    assert result == '{["body"]={{1,8},{17,24}},}'


def test_parse_layer_frame_ranges_multiple_layers():
    result = _parse_layer_frame_ranges(["body:1-8", "clouds:1-12"])
    assert '["body"]={{1,8}}' in result
    assert '["clouds"]={{1,12}}' in result


def test_parse_layer_frame_ranges_skips_empty_entry():
    # entries with no ":" are dropped entirely
    assert _parse_layer_frame_ranges(["", "no-colon-here"]) == "{}"


def test_parse_layer_frame_ranges_skips_falsy_entry():
    # None-ish/empty-string entries in the list are skipped, not raised
    result = _parse_layer_frame_ranges(["", "body:1-8"])
    assert result == '{["body"]={{1,8}},}'


def test_parse_layer_frame_ranges_blank_layer_name_skipped():
    # "  :1-8" -> layer strips to "" -> skipped
    assert _parse_layer_frame_ranges(["  :1-8"]) == "{}"


def test_parse_layer_frame_ranges_malformed_span_non_numeric():
    # "a-b" fails int() -> ValueError -> span dropped; layer has no spans
    # so it is never added to the ranges dict at all.
    assert _parse_layer_frame_ranges(["body:a-b"]) == "{}"


def test_parse_layer_frame_ranges_start_le_zero_dropped():
    # start must be > 0
    assert _parse_layer_frame_ranges(["body:0-8"]) == "{}"


def test_parse_layer_frame_ranges_end_less_than_start_dropped():
    # end must be >= start
    assert _parse_layer_frame_ranges(["body:8-1"]) == "{}"


def test_parse_layer_frame_ranges_span_without_dash_ignored():
    # no "-" in span -> span silently skipped (loop just doesn't append)
    assert _parse_layer_frame_ranges(["body:5"]) == "{}"


def test_parse_layer_frame_ranges_mixed_valid_and_invalid_spans():
    # one bad span, one good span for the same layer -> only good one kept
    result = _parse_layer_frame_ranges(["body:0-8,10-20"])
    assert result == '{["body"]={{10,20}},}'


def test_parse_layer_frame_ranges_whitespace_trimmed():
    result = _parse_layer_frame_ranges([" body : 1 - 8 "])
    assert result == '{["body"]={{1,8}},}'


# ---------------------------------------------------------------------------
# _parse_overlap_pairs (pure function, no Aseprite process)
# ---------------------------------------------------------------------------


def test_parse_overlap_pairs_none():
    assert _parse_overlap_pairs(None) == "{}"


def test_parse_overlap_pairs_empty_list():
    assert _parse_overlap_pairs([]) == "{}"


def test_parse_overlap_pairs_comma_separated():
    assert _parse_overlap_pairs(["body,clouds"]) == '{{"body","clouds"}}'


def test_parse_overlap_pairs_colon_separated():
    assert _parse_overlap_pairs(["body:clouds"]) == '{{"body","clouds"}}'


def test_parse_overlap_pairs_comma_takes_precedence_over_colon():
    # entry contains both "," and ":"; comma branch wins per the if/elif order
    result = _parse_overlap_pairs(["a:b,c:d"])
    assert result == '{{"a:b","c:d"}}'


def test_parse_overlap_pairs_multiple_entries():
    result = _parse_overlap_pairs(["a,b", "c:d"])
    assert result == '{{"a","b"},{"c","d"}}'


def test_parse_overlap_pairs_skips_empty_entry():
    assert _parse_overlap_pairs(["", "a,b"]) == '{{"a","b"}}'


def test_parse_overlap_pairs_skips_entry_without_separator():
    assert _parse_overlap_pairs(["nosep"]) == "{}"


def test_parse_overlap_pairs_skips_blank_sides():
    # "a," -> left="a", right="" -> right falsy -> pair dropped
    assert _parse_overlap_pairs(["a,"]) == "{}"
    assert _parse_overlap_pairs([",b"]) == "{}"


def test_parse_overlap_pairs_whitespace_trimmed():
    assert _parse_overlap_pairs([" a , b "]) == '{{"a","b"}}'


# ---------------------------------------------------------------------------
# ensure_layers_present
# ---------------------------------------------------------------------------


def test_ensure_layers_present_missing_file():
    result = run(
        quality.ensure_layers_present("/tmp/ase-pytest/NOPE.aseprite", ["body"])
    )
    assert "not found" in result


def test_ensure_layers_present_empty_layer_list(sprite):
    result = run(quality.ensure_layers_present(sprite, []))
    assert result == "Layer names list cannot be empty"


def test_ensure_layers_present_success(sprite):
    ok(run(animation.add_frames(sprite, 2, 100)))  # sprite now has 3 frames
    ok(run(canvas.add_layer(sprite, "ensure_target")))
    result = ok(run(quality.ensure_layers_present(sprite, ["ensure_target"], 1, 3)))
    assert "ensure_target" in result
    assert "1-3" in result


def test_ensure_layers_present_default_end_frame(sprite):
    ok(run(canvas.add_layer(sprite, "ensure_target2")))
    result = ok(run(quality.ensure_layers_present(sprite, ["ensure_target2"])))
    assert "end" in result


def test_ensure_layers_present_frame_range_out_of_bounds(sprite):
    result = run(quality.ensure_layers_present(sprite, ["body"], 1, 9999))
    assert result.startswith("Failed")


def test_ensure_layers_present_no_layers_found(sprite):
    result = run(quality.ensure_layers_present(sprite, ["TOTALLY_MISSING_LAYER"]))
    assert result.startswith("Failed")


# ---------------------------------------------------------------------------
# validate_scene
# ---------------------------------------------------------------------------


def test_validate_scene_missing_file():
    result = run(quality.validate_scene("/tmp/ase-pytest/NOPE.aseprite", ["body"]))
    assert "not found" in result


def test_validate_scene_empty_required_layers(sprite):
    result = run(quality.validate_scene(sprite, []))
    assert result == "Required layers list cannot be empty"


def test_validate_scene_all_present(sprite):
    result = ok(run(quality.validate_scene(sprite, ["body"], 1, 1)))
    data = json.loads(result)
    assert data["missing_layers"] == []
    assert data["missing_cels"] == []


def test_validate_scene_missing_layer_and_cel(sprite):
    ok(run(canvas.add_layer(sprite, "validate_empty_layer")))
    result = ok(
        run(
            quality.validate_scene(
                sprite, ["body", "validate_empty_layer", "NOT_A_LAYER"], 1, 1
            )
        )
    )
    data = json.loads(result)
    assert "NOT_A_LAYER" in data["missing_layers"]
    assert any(
        entry["layer"] == "validate_empty_layer" for entry in data["missing_cels"]
    )


def test_validate_scene_default_end_frame(sprite):
    result = ok(run(quality.validate_scene(sprite, ["body"])))
    data = json.loads(result)
    assert data["frames"] >= 1


def test_validate_scene_frame_range_out_of_bounds(sprite):
    result = run(quality.validate_scene(sprite, ["body"], 1, 9999))
    assert result.startswith("Failed")


# ---------------------------------------------------------------------------
# audit_animation
# ---------------------------------------------------------------------------


def test_audit_animation_missing_file():
    result = run(quality.audit_animation("/tmp/ase-pytest/NOPE.aseprite"))
    assert "not found" in result


def test_audit_animation_start_frame_invalid(sprite):
    result = run(quality.audit_animation(sprite, start_frame=0))
    assert result == "Start frame must be >= 1"


def test_audit_animation_end_before_start(sprite):
    result = run(quality.audit_animation(sprite, start_frame=5, end_frame=2))
    assert result == "End frame must be >= start frame"


def test_audit_animation_negative_max_overlaps(sprite):
    result = run(quality.audit_animation(sprite, max_overlaps=-1))
    assert result == "Max limits must be >= 0"


def test_audit_animation_negative_max_out_of_range(sprite):
    result = run(quality.audit_animation(sprite, max_out_of_range=-1))
    assert result == "Max limits must be >= 0"


def test_audit_animation_default_layers_all_non_group(sprite):
    result = ok(run(quality.audit_animation(sprite, start_frame=1, end_frame=1)))
    data = json.loads(result)
    assert data["summary"]["total_layers"] >= 1
    assert data["summary"]["layers_checked"] >= 1


def test_audit_animation_explicit_layer_names(sprite):
    result = ok(
        run(
            quality.audit_animation(
                sprite, start_frame=1, end_frame=1, layer_names=["body"]
            )
        )
    )
    data = json.loads(result)
    assert data["summary"]["layers_checked"] == 1


def test_audit_animation_report_cels_no_bounds(sprite):
    result = ok(
        run(
            quality.audit_animation(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["body"],
                report_cels=True,
            )
        )
    )
    data = json.loads(result)
    assert "cels" in data
    frame1 = data["cels"][0]
    assert frame1["cels"][0]["layer"] == "body"
    assert "w" not in frame1["cels"][0]


def test_audit_animation_report_cels_with_bounds(sprite):
    result = ok(
        run(
            quality.audit_animation(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["body"],
                report_cels=True,
                report_bounds=True,
            )
        )
    )
    data = json.loads(result)
    cel = data["cels"][0]["cels"][0]
    assert cel["layer"] == "body"
    assert "w" in cel and "h" in cel and "x" in cel and "y" in cel


def test_audit_animation_overlap_detection(sprite):
    ok(run(canvas.add_layer(sprite, "overlap_a")))
    ok(run(canvas.add_layer(sprite, "overlap_b")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "overlap_a", 1, 0, 0, 10, 10, "#ff0000", True
            )
        )
    )
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "overlap_b", 1, 5, 5, 10, 10, "#00ff00", True
            )
        )
    )
    result = ok(
        run(
            quality.audit_animation(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["overlap_a", "overlap_b"],
                overlap_pairs=["overlap_a,overlap_b"],
            )
        )
    )
    data = json.loads(result)
    assert data["summary"]["overlaps"] == 1
    assert data["overlaps"][0]["a"] == "overlap_a"
    assert data["overlaps"][0]["b"] == "overlap_b"


def test_audit_animation_overlap_with_bounds(sprite):
    result = ok(
        run(
            quality.audit_animation(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["overlap_a", "overlap_b"],
                overlap_pairs=["overlap_a,overlap_b"],
                report_bounds=True,
            )
        )
    )
    data = json.loads(result)
    entry = data["overlaps"][0]
    assert "a_bounds" in entry and "b_bounds" in entry


def test_audit_animation_overlap_truncation(sprite):
    # max_overlaps=0 with a real overlap -> overlaps list stays empty but
    # overlaps_truncated flips true and overlaps_total still counts it.
    result = ok(
        run(
            quality.audit_animation(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["overlap_a", "overlap_b"],
                overlap_pairs=["overlap_a,overlap_b"],
                max_overlaps=0,
            )
        )
    )
    data = json.loads(result)
    assert data["summary"]["overlaps"] == 0
    assert data["summary"]["overlaps_total"] == 1
    assert data["summary"]["overlaps_truncated"] is True
    assert data["overlaps"] == []


def test_audit_animation_out_of_range_detection(sprite):
    ok(run(animation.add_frames(sprite, 2, 100)))  # total frames should now be >=3
    info = json.loads(run(animation.get_sprite_info(sprite)))
    total_frames = info["frames"]
    ok(run(canvas.add_layer(sprite, "range_layer")))
    for fi in range(1, total_frames + 1):
        ok(
            run(
                drawing.draw_rectangle_at(
                    sprite, "range_layer", fi, 0, 0, 4, 4, "#0000ff", True
                )
            )
        )
    result = ok(
        run(
            quality.audit_animation(
                sprite,
                start_frame=1,
                end_frame=total_frames,
                layer_names=["range_layer"],
                layer_frame_ranges=["range_layer:1-1"],
            )
        )
    )
    data = json.loads(result)
    assert data["summary"]["out_of_range"] == total_frames - 1
    assert all(e["layer"] == "range_layer" for e in data["out_of_range"])


def test_audit_animation_out_of_range_truncation(sprite):
    info = json.loads(run(animation.get_sprite_info(sprite)))
    total_frames = info["frames"]
    result = ok(
        run(
            quality.audit_animation(
                sprite,
                start_frame=1,
                end_frame=total_frames,
                layer_names=["range_layer"],
                layer_frame_ranges=["range_layer:1-1"],
                max_out_of_range=1,
            )
        )
    )
    data = json.loads(result)
    assert len(data["out_of_range"]) == 1


def test_audit_animation_frame_range_out_of_bounds(sprite):
    result = run(quality.audit_animation(sprite, start_frame=1, end_frame=99999))
    assert result.startswith("Failed")


# ---------------------------------------------------------------------------
# animation_sanitize
# ---------------------------------------------------------------------------


def test_animation_sanitize_missing_file():
    result = run(quality.animation_sanitize("/tmp/ase-pytest/NOPE.aseprite"))
    assert "not found" in result


def test_animation_sanitize_start_frame_invalid(sprite):
    result = run(quality.animation_sanitize(sprite, start_frame=0))
    assert result == "Start frame must be >= 1"


def test_animation_sanitize_end_before_start(sprite):
    result = run(quality.animation_sanitize(sprite, start_frame=5, end_frame=2))
    assert result == "End frame must be >= start frame"


def test_animation_sanitize_negative_max_overlaps(sprite):
    result = run(quality.animation_sanitize(sprite, max_overlaps=-1))
    assert result == "max_overlaps must be >= 0"


def test_animation_sanitize_bad_out_of_range_action(sprite):
    result = run(quality.animation_sanitize(sprite, out_of_range_action="explode"))
    assert result == "Unsupported out_of_range_action"


def test_animation_sanitize_opacity_out_of_bounds_low(sprite):
    result = run(quality.animation_sanitize(sprite, out_of_range_opacity=-1))
    assert result == "out_of_range_opacity must be 0-255"


def test_animation_sanitize_opacity_out_of_bounds_high(sprite):
    result = run(quality.animation_sanitize(sprite, out_of_range_opacity=256))
    assert result == "out_of_range_opacity must be 0-255"


def test_animation_sanitize_frame_range_out_of_bounds(sprite):
    result = run(quality.animation_sanitize(sprite, start_frame=1, end_frame=99999))
    assert result.startswith("Failed")


def test_animation_sanitize_report_only_basic(sprite):
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["body"],
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert data["ensured"] == 0
    assert "analysis" in data
    assert "layer_stats" in data  # include_stats defaults True


def test_animation_sanitize_no_stats(sprite):
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["body"],
                report_only=True,
                include_stats=False,
            )
        )
    )
    data = json.loads(result)
    assert "layer_stats" not in data


def test_animation_sanitize_ensure_layers_apply(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_ensure_target")))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    total_frames = info["frames"]
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=total_frames,
                layer_names=["sanitize_ensure_target"],
                ensure_layers=["sanitize_ensure_target"],
            )
        )
    )
    data = json.loads(result)
    assert data["ensured"] == total_frames

    # Applying again should find nothing left to ensure.
    result2 = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=total_frames,
                layer_names=["sanitize_ensure_target"],
                ensure_layers=["sanitize_ensure_target"],
            )
        )
    )
    data2 = json.loads(result2)
    assert data2["ensured"] == 0


def test_animation_sanitize_ensure_layers_report_only_does_not_apply(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_ensure_reportonly")))
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["sanitize_ensure_reportonly"],
                ensure_layers=["sanitize_ensure_reportonly"],
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert data["ensured"] == 1

    # Cel must NOT actually have been created since report_only=True.
    validate = ok(
        run(quality.validate_scene(sprite, ["sanitize_ensure_reportonly"], 1, 1))
    )
    vdata = json.loads(validate)
    assert any(
        e["layer"] == "sanitize_ensure_reportonly" for e in vdata["missing_cels"]
    )


def test_animation_sanitize_out_of_range_set_opacity_zero(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_range_opacity")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "sanitize_range_opacity", 1, 0, 0, 4, 4, "#123456", True
            )
        )
    )
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["sanitize_range_opacity"],
                layer_frame_ranges=["sanitize_range_opacity:2-5"],
                out_of_range_action="set_opacity_zero",
                out_of_range_opacity=0,
            )
        )
    )
    data = json.loads(result)
    assert data["out_of_range"] == 1
    assert data["opacity_set"] == 1
    assert data["deleted"] == 0
    assert "cels_out_of_range" in data["alerts"]


def test_animation_sanitize_out_of_range_delete_cels(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_range_delete")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "sanitize_range_delete", 1, 0, 0, 4, 4, "#123456", True
            )
        )
    )
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["sanitize_range_delete"],
                layer_frame_ranges=["sanitize_range_delete:2-5"],
                out_of_range_action="delete_cels",
            )
        )
    )
    data = json.loads(result)
    assert data["out_of_range"] == 1
    assert data["deleted"] == 1
    assert data["opacity_set"] == 0

    validate = ok(run(quality.validate_scene(sprite, ["sanitize_range_delete"], 1, 1)))
    vdata = json.loads(validate)
    assert any(e["layer"] == "sanitize_range_delete" for e in vdata["missing_cels"])


def test_animation_sanitize_out_of_range_action_none(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_range_none")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "sanitize_range_none", 1, 0, 0, 4, 4, "#123456", True
            )
        )
    )
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["sanitize_range_none"],
                layer_frame_ranges=["sanitize_range_none:2-5"],
                out_of_range_action="none",
            )
        )
    )
    data = json.loads(result)
    assert data["out_of_range"] == 1
    assert data["deleted"] == 0
    assert data["opacity_set"] == 0

    # cel should still exist (nothing applied)
    validate = ok(run(quality.validate_scene(sprite, ["sanitize_range_none"], 1, 1)))
    vdata = json.loads(validate)
    assert not any(e["layer"] == "sanitize_range_none" for e in vdata["missing_cels"])


def test_animation_sanitize_empty_frames_alert(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_lonely")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "sanitize_lonely", 1, 0, 0, 4, 4, "#123456", True
            )
        )
    )
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["nonexistent_layer_for_empty_check"],
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert data["analysis"]["empty_frames"] == 1
    assert "empty_frames_detected" in data["alerts"]


def test_animation_sanitize_full_canvas_alert(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_full_canvas")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "sanitize_full_canvas", 1, 0, 0, 32, 32, "#123456", True
            )
        )
    )
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["sanitize_full_canvas"],
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert any(a.startswith("full_canvas_cels:") for a in data["alerts"])
    stats = data["layer_stats"]["sanitize_full_canvas"]
    assert stats["full_canvas_cels"] == 1
    assert stats["bounds"] == [0, 0, 32, 32]


def test_animation_sanitize_inactive_layer(sprite):
    ok(run(canvas.add_layer(sprite, "sanitize_inactive")))
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["sanitize_inactive"],
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert "sanitize_inactive" in data["analysis"]["inactive_layers"]
    stats = data["layer_stats"]["sanitize_inactive"]
    assert stats["bounds"] is None
    assert stats["cel_count"] == 0


def test_animation_sanitize_overlap_pairs_ignore_full_canvas(sprite):
    ok(run(canvas.add_layer(sprite, "ov_full")))
    ok(run(canvas.add_layer(sprite, "ov_small")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "ov_full", 1, 0, 0, 32, 32, "#111111", True
            )
        )
    )
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite, "ov_small", 1, 0, 0, 4, 4, "#222222", True
            )
        )
    )
    # Full-canvas overlap should be ignored by default.
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["ov_full", "ov_small"],
                overlap_pairs=["ov_full,ov_small"],
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert data["analysis"]["overlaps"] == 0
    assert data.get("overlap_samples", []) == []


def test_animation_sanitize_overlap_pairs_not_ignored(sprite):
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["ov_full", "ov_small"],
                overlap_pairs=["ov_full,ov_small"],
                ignore_full_canvas_overlaps=False,
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert data["analysis"]["overlaps"] == 1
    assert data["overlap_samples"][0]["a"] == "ov_full"
    assert data["overlap_samples"][0]["b"] == "ov_small"


def test_animation_sanitize_overlap_pairs_with_bounds(sprite):
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["ov_full", "ov_small"],
                overlap_pairs=["ov_full,ov_small"],
                ignore_full_canvas_overlaps=False,
                report_bounds=True,
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    entry = data["overlap_samples"][0]
    assert "a_bounds" in entry and "b_bounds" in entry


def test_animation_sanitize_overlap_truncation(sprite):
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["ov_full", "ov_small"],
                overlap_pairs=["ov_full,ov_small"],
                ignore_full_canvas_overlaps=False,
                max_overlaps=0,
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    assert data["analysis"]["overlaps"] == 1
    assert data.get("overlap_samples", []) == []


def test_animation_sanitize_reorder_applies_without_groups(sprite):
    ok(run(canvas.add_layer(sprite, "reorder_a")))
    ok(run(canvas.add_layer(sprite, "reorder_b")))
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["reorder_a", "reorder_b"],
                layer_order=["reorder_b", "reorder_a"],
            )
        )
    )
    data = json.loads(result)
    assert data["reordered"] is True


def test_animation_sanitize_reorder_report_only_not_applied(sprite):
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["reorder_a", "reorder_b"],
                layer_order=["reorder_a", "reorder_b"],
                report_only=True,
            )
        )
    )
    data = json.loads(result)
    # sanitized.reordered reflects "would reorder" regardless of report_only,
    # but the actual stackIndex mutation is skipped (verified by no crash /
    # no save; behavior captured for coverage of the report_only branch).
    assert data["reordered"] is True


def test_animation_sanitize_reorder_skipped_with_groups(sprite):
    ok(run(canvas.add_group(sprite, "sanitize_group")))
    ok(run(canvas.add_layer(sprite, "reorder_c", group="sanitize_group")))
    result = ok(
        run(
            quality.animation_sanitize(
                sprite,
                start_frame=1,
                end_frame=1,
                layer_names=["reorder_a", "reorder_b"],
                layer_order=["reorder_b", "reorder_a"],
            )
        )
    )
    data = json.loads(result)
    # has_groups becomes true because the sprite now contains a group layer,
    # so reordering is skipped even though order_names was provided.
    assert data["reordered"] is False


def test_animation_sanitize_no_layer_order_reordered_false(sprite):
    result = ok(
        run(
            quality.animation_sanitize(
                sprite, start_frame=1, end_frame=1, layer_names=["body"]
            )
        )
    )
    data = json.loads(result)
    assert data["reordered"] is False


def test_animation_sanitize_default_all_non_group_layers(sprite):
    result = ok(run(quality.animation_sanitize(sprite, start_frame=1, end_frame=1)))
    data = json.loads(result)
    assert data["analysis"]["layers_checked"] >= 1
