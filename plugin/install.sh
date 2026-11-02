#!/usr/bin/env bash
# Install the v2 live-progress card into a DSH profile.
# Desktop profiles are exclusively managed by the Electron app, so `dsh plugin add`
# is not allowed; this installs a local symlink + loader patch instead.
# Usage: ./install.sh [profile]   (default: desktop)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${1:-${DSH_PROFILE:-desktop}}"
PROFILE_DIR="$HOME/.dsh/profiles/$PROFILE"
MODULES="$PROFILE_DIR/node_modules"
PATCH="$PROFILE_DIR/cordis.patch.yml"
NAME="dsh-live-progress-card"

if [ ! -f "$ROOT/lib/client.js" ]; then
  echo "missing $ROOT/lib/client.js" >&2
  exit 1
fi
mkdir -p "$MODULES" "$PROFILE_DIR"
ln -sfn "$ROOT" "$MODULES/$NAME"

if [ ! -f "$PATCH" ]; then
  printf '%s\n' '# User patch layer for this profile.' > "$PATCH"
fi
if ! grep -q "$NAME" "$PATCH"; then
  cat >> "$PATCH" <<YAML

# live-progress v2 card
- id: $NAME
  name: "$NAME"
YAML
  echo "Added loader entry to $PATCH"
else
  echo "Loader entry already present in $PATCH"
fi

# Verify Node can resolve the package from the profile.
(cd "$PROFILE_DIR" && node -e "import('$NAME').then(()=>console.log('resolved $NAME'))")

echo
echo "Installed. Restart DSH Desktop to load the client plugin."
echo "Then start a live-progress task; the card appears above the composer."
