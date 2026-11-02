#!/usr/bin/env bash
# Install the v2 live-progress card into a DSH profile.
# Usage: ./install.sh [profile]   (default: desktop)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${1:-${DSH_PROFILE:-desktop}}"
PROFILE_DIR="$HOME/.dsh/profiles/$PROFILE"
PATCH="$PROFILE_DIR/cordis.patch.yml"

if ! command -v dsh >/dev/null 2>&1; then
  echo "dsh not found in PATH" >&2
  exit 1
fi
if [ ! -f "$ROOT/lib/client.js" ]; then
  echo "missing $ROOT/lib/client.js" >&2
  exit 1
fi

mkdir -p "$PROFILE_DIR"
echo "Installing $ROOT into profile '$PROFILE' ..."
dsh plugin --profile "$PROFILE" add "file:$ROOT"

if [ ! -f "$PATCH" ]; then
  printf '%s\n' '# User patch layer for this profile.' > "$PATCH"
fi
if ! grep -q 'dsh-live-progress-card' "$PATCH"; then
  cat >> "$PATCH" <<'YAML'

# live-progress v2 card
- id: dsh-live-progress-card
  name: "dsh-live-progress-card"
YAML
  echo "Added loader entry to $PATCH"
else
  echo "Loader entry already present in $PATCH"
fi

echo
echo "Installed. Restart DSH Desktop to load the client plugin."
echo "After restart, start a live-progress task and the card should appear above the composer."
