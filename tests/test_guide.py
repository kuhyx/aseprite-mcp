"""Pure string-building guide (guide.py) - no Aseprite process needed."""

from conftest import run

from aseprite_mcp.tools import guide


def test_animation_workflow_guide_character_default() -> None:
    out = run(guide.animation_workflow_guide())
    assert "Use case: character" in out
    assert "copy_frame/copy_cel" in out


def test_animation_workflow_guide_character_explicit() -> None:
    out = run(guide.animation_workflow_guide("Character"))
    assert "Use case: character" in out


def test_animation_workflow_guide_environment() -> None:
    out = run(guide.animation_workflow_guide("environment"))
    assert "Use case: environment" in out
    assert "copy_sprite" in out


def test_animation_workflow_guide_unknown_use_case_falls_back() -> None:
    out = run(guide.animation_workflow_guide("robot"))
    assert "Use case: robot" in out
    assert "duplicate cels/frames" in out


def test_animation_workflow_guide_blank_use_case_falls_back_to_generic() -> None:
    # Whitespace is truthy, so it survives the `or "character"` default and
    # strips to "" - falls into the generic branch, not the character one.
    out = run(guide.animation_workflow_guide("   "))
    assert "Use case: \n" in out
    assert "duplicate cels/frames" in out
