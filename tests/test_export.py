"""Export and import tools (export.py)."""

import struct
from pathlib import Path

from conftest import BASE, ok, run

from aseprite_mcp.tools import animation, export


def png_size(path: str) -> tuple[int, int]:
    with Path(path).open("rb") as f:
        data = f.read(24)
    return struct.unpack(">II", data[16:24])


def test_export_frame_scaled(sprite: str) -> None:
    out = f"{BASE}/frame1.png"
    ok(run(export.export_frame(sprite, 1, out, 8)))
    assert png_size(out) == (256, 256)


def test_export_spritesheet_with_data(sprite: str) -> None:
    ok(run(animation.add_frames(sprite, 3, 100)))
    out = f"{BASE}/sheet.png"
    data = f"{BASE}/sheet.json"
    ok(run(export.export_spritesheet(sprite, out, "horizontal", data, 2, 1)))
    assert Path(out).exists()
    assert Path(data).exists()


def test_export_spritesheet_tag_filter(sprite: str) -> None:
    ok(run(animation.set_tag(sprite, "clip", 1, 2, "forward")))
    out = f"{BASE}/sheet_tag.png"
    ok(run(export.export_spritesheet(sprite, out, "horizontal", "", 1, 0, "clip")))
    w, h = png_size(out)
    assert (w, h) == (64, 32), "tag filter must export only the 2 tagged frames"


def test_export_layers(sprite: str) -> None:
    result = ok(run(export.export_layers(sprite, f"{BASE}/layers")))
    assert ".png" in result


def test_export_tag_gif(sprite: str) -> None:
    out = f"{BASE}/clip.gif"
    ok(run(export.export_tag(sprite, "clip", out, 4)))
    assert Path(out).exists()


def test_import_image_as_layer(sprite: str) -> None:
    ok(run(export.import_image_as_layer(sprite, f"{BASE}/frame1.png", "ref", 1, 0, 0)))
