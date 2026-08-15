#!/bin/bash

# ============================================================================
# Install this repo's pixel-art skills into ~/.claude/skills so they load.
#
# Skills under skills/ are documentation only -- Claude Code loads skills from
# ~/.claude/skills. item-icons and seamless-tilesets sat in this repo for
# several sessions and never auto-triggered because nothing had copied them.
#
# Also fans out the canonical references/showcase.md to each skill that cites
# it, then diffs every copy. Editing a skill and forgetting to re-run this is
# the failure this script exists to make impossible.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
readonly REPO_ROOT
readonly SRC="$REPO_ROOT/skills"
readonly DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

# Skills this repo owns. anime-pixel-art is intentionally excluded: the global
# copy has diverged and is not ours to overwrite.
readonly SKILLS=(item-icons seamless-tilesets pixel-animation)

# The shared reference, and who gets a copy.
readonly CANON="$SRC/pixel-animation/references/showcase.md"
readonly CANON_CONSUMERS=(item-icons seamless-tilesets)

fail() {
    echo "Error: $*" >&2
    exit 1
}

validate_requirements() {
    [[ -d "$SRC" ]] || fail "no skills/ directory at $SRC"
    [[ -f "$CANON" ]] || fail "canonical showcase.md missing at $CANON"
    for s in "${SKILLS[@]}"; do
        [[ -f "$SRC/$s/SKILL.md" ]] || fail "missing $SRC/$s/SKILL.md"
    done
}

# Keep every consumer's showcase.md byte-identical to the canonical one.
sync_shared_reference() {
    for s in "${CANON_CONSUMERS[@]}"; do
        mkdir -p "$SRC/$s/references"
        cp "$CANON" "$SRC/$s/references/showcase.md"
    done
}

install_skill() {
    local skill="$1"
    rm -rf "${DEST:?}/$skill"
    mkdir -p "$DEST/$skill"
    cp "$SRC/$skill/SKILL.md" "$DEST/$skill/"
    if [[ -d "$SRC/$skill/references" ]]; then
        cp -r "$SRC/$skill/references" "$DEST/$skill/"
        # __pycache__ is build output; it must never ship in a skill.
        find "$DEST/$skill" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    fi
}

# Prove the install matches the source rather than assuming cp worked.
verify_installed() {
    local skill="$1"
    diff -r --exclude='__pycache__' "$SRC/$skill" "$DEST/$skill" >/dev/null \
        || fail "$skill differs between repo and $DEST after install"
}

main() {
    validate_requirements
    sync_shared_reference

    mkdir -p "$DEST"
    # A stale shared copy here would be cited by nothing and drift silently.
    rm -rf "${DEST:?}/references"

    for skill in "${SKILLS[@]}"; do
        install_skill "$skill"
        verify_installed "$skill"
        echo "installed  $skill"
    done

    # Gate the INSTALLED copies -- those are what actually load. Pass only the
    # skills this repo owns; $DEST also holds unrelated skills that are not
    # ours to validate or fail on.
    local installed=()
    for skill in "${SKILLS[@]}"; do
        installed+=("$DEST/$skill")
    done
    python3 "$SCRIPT_DIR/check_skills.py" "${installed[@]}" \
        || fail "installed skills failed validation"

    echo "All ${#SKILLS[@]} skills installed and verified in $DEST"
}

main "$@"
