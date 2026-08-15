"""Validate SKILL.md frontmatter and cross-references for a skills directory.

Run against the INSTALLED skills (`~/.claude/skills`), not just the repo copy —
the installed ones are what Claude Code actually loads, and they are the ones
that silently go stale after a repo edit.

Usage:
    python3 check_skills.py [skills_dir]
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Cited by item-icons but deliberately living at the aseprite-mcp repo root
# rather than inside the skill, so they are not resolvable from a skill dir.
REPO_ROOT_REFS = frozenset(
    {
        "references/MEASUREMENTS.md",
        "references/SHAPE_RESEARCH.md",
        "references/CREDITS.md",
    }
)

MIN_DESCRIPTION_LEN = 40


def _scalar(frontmatter: str, key: str) -> str | None:
    r"""Read a frontmatter value, supporting YAML folded/literal scalars.

    `description: >` puts the text on following indented lines; a naive
    `^key:\s*(.+)$` match reads that as empty and reports a valid skill as
    having no description. Several real skills use this form.
    """
    inline = re.search(rf"^{key}:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    if inline is None:
        return None

    value = inline.group(1).strip()
    if value not in (">", "|", ">-", "|-", ">+", "|+"):
        return value

    # Folded/literal block: collect the indented lines that follow.
    lines: list[str] = []
    for line in frontmatter[inline.end() :].splitlines():
        if line.strip() and not line[:1].isspace():
            break  # dedented -> next key
        lines.append(line.strip())
    return " ".join(part for part in lines if part)


def check_skill(skill_dir: Path) -> list[str]:
    """Return a list of problems with one skill directory (empty if valid)."""
    errors: list[str] = []
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return [f"{skill_dir.name}: no SKILL.md"]

    text = md.read_text()
    frontmatter = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not frontmatter:
        return [f"{skill_dir.name}: missing or malformed frontmatter"]

    body = frontmatter.group(1)
    name = _scalar(body, "name")
    description = _scalar(body, "description")

    if name is None:
        errors.append(f"{skill_dir.name}: no name: field")
    elif name != skill_dir.name:
        errors.append(f"{skill_dir.name}: name '{name}' does not match its directory")

    if description is None:
        errors.append(f"{skill_dir.name}: no description: field")
    elif len(description) < MIN_DESCRIPTION_LEN:
        errors.append(f"{skill_dir.name}: description too short to trigger well")

    for ref in sorted(set(re.findall(r"`(references/[\w.\-]+)`", text))):
        if ref in REPO_ROOT_REFS:
            continue
        if not (skill_dir / ref).exists():
            errors.append(f"{skill_dir.name}: broken reference {ref}")

    return errors


def main(argv: list[str] | None = None) -> int:
    """Validate the given skill dirs (or every skill in a single dir)."""
    args = sys.argv[1:] if argv is None else argv
    paths = (
        [Path(a) for a in args]
        if args
        else [Path(__file__).resolve().parent.parent / "skills"]
    )

    for path in paths:
        if not path.is_dir():
            logger.error("not a directory: %s", path)
            return 1

    # A single directory means "every skill in it"; several mean "exactly
    # these skills", which is how the installer checks only what it owns.
    if len(paths) == 1 and not (paths[0] / "SKILL.md").exists():
        skill_dirs = sorted(
            d for d in paths[0].iterdir() if d.is_dir() and d.name != "references"
        )
    else:
        skill_dirs = paths

    if not skill_dirs:
        logger.error("no skills found in %s", paths[0])
        return 1

    all_errors: list[str] = []
    for d in skill_dirs:
        errors = check_skill(d)
        logger.info("%-5s%s", "FAIL" if errors else "ok", d.name)
        all_errors.extend(errors)

    if all_errors:
        logger.error("")
        logger.error("errors:")
        for error in all_errors:
            logger.error("  - %s", error)
        return 1

    logger.info("")
    logger.info("%d skills valid", len(skill_dirs))
    return 0


if __name__ == "__main__":
    # Bare message format: this is CLI output, not application logging.
    logging.basicConfig(format="%(message)s", level=logging.INFO, stream=sys.stdout)
    sys.exit(main())
