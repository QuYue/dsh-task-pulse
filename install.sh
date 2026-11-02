#!/usr/bin/env bash
# Install the live-progress skill for DSH discovery.
#
#   ./install.sh                     # project-level: <cwd>/.dsh/skills/live-progress
#   ./install.sh --global            # user-level:    ~/.dsh/skills/live-progress
#   ./install.sh --global --agents   # + append the AGENTS.md snippet to <cwd>/AGENTS.md
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$REPO_DIR/skill"
TARGET="$PWD/.dsh/skills/live-progress"

if [[ "${1:-}" == "--global" ]]; then
  TARGET="$HOME/.dsh/skills/live-progress"
  shift || true
fi

mkdir -p "$(dirname "$TARGET")"
ln -sfn "$SKILL_DIR" "$TARGET"
echo "linked: $TARGET -> $SKILL_DIR"

if [[ "${1:-}" == "--agents" ]]; then
  AGENTS_FILE="$PWD/AGENTS.md"
  if [[ -f "$AGENTS_FILE" ]] && grep -q "live-progress" "$AGENTS_FILE"; then
    echo "AGENTS.md already mentions live-progress; skipped"
  else
    {
      echo
      cat "$REPO_DIR/docs/AGENTS.snippet.md"
    } >> "$AGENTS_FILE"
    echo "appended snippet to $AGENTS_FILE"
  fi
fi

cat <<'EOF'

Verify with:
  python3 "$TARGET/scripts/board.py" --version
Start the board:
  python3 "$TARGET/scripts/board.py" serve --port 8770
EOF
