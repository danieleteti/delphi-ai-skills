#!/usr/bin/env bash
#
# delphi-ai-skills - install for Claude Code (macOS / Linux)
#
#   ./install_in_claude.sh            installs for your user (every project)
#   ./install_in_claude.sh .          installs into the current project (.claude/skills)
#   ./install_in_claude.sh <path>     installs into that project
#
# Claude Code discovers skills automatically - there is nothing else to configure.
#
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"
if [ ! -d "$SRC" ]; then
    echo "[ERROR] Cannot find \"$SRC\"." >&2
    echo "        Run this script from the folder where you cloned delphi-ai-skills." >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    DEST="$HOME/.claude/skills"
    SCOPE="your user account (available in every project)"
else
    if [ ! -d "$1" ]; then
        echo "[ERROR] No such folder: $1" >&2
        exit 1
    fi
    TARGET="$(cd "$1" && pwd)"
    DEST="$TARGET/.claude/skills"
    SCOPE="the project at $TARGET"
fi

echo
echo "Installing delphi-ai-skills for Claude Code"
echo "  from : $SRC"
echo "  to   : $DEST"
echo "  scope: $SCOPE"
echo

mkdir -p "$DEST"

# Copy each skill folder, overwriting existing files (idempotent). Plain files
# in skills/ (e.g. VERSION) are copied too.
cp -R "$SRC"/. "$DEST"/

# Make shipped helper scripts executable, if any.
find "$DEST" -name '*.sh' -exec chmod +x {} + 2>/dev/null || true

echo "Installed:"
for d in "$SRC"/*/; do
    echo "  - $(basename "$d")"
done
echo
echo "Done. Start Claude Code in any Delphi project and ask, for example:"
echo '  "Find the memory leak in this Delphi unit"'
echo '  "Review this unit and tell me what is actually wrong with it"'
echo
echo "The Delphi skills (delphi, delphi-code-smells, ...) assume nothing:"
echo "any .pas, any project, no framework and no particular layout."
echo
echo "The DMVCFramework skills are the ones with a prerequisite. They add"
echo "features to an existing project, so create it with the IDE wizard"
echo "first, then start the agent from that project folder:"
echo '  "Create a DMVCFramework REST controller for Customers with full CRUD"'
echo
