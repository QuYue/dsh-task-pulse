#!/usr/bin/env bash
# Install TaskPulse into a DSH profile as a single scoped plugin package.
# Desktop profiles are exclusively managed by the Electron app, so `dsh plugin add`
# is not allowed; this installs a local symlink + loader patch instead.
# Usage: ./install.sh [profile]   (default: desktop)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${1:-${DSH_PROFILE:-desktop}}"
PROFILE_DIR="$HOME/.dsh/profiles/$PROFILE"
NAME="@quyue/dsh-task-pulse"
PKG_PATH="$PROFILE_DIR/node_modules/@quyue/dsh-task-pulse"
PATCH="$PROFILE_DIR/cordis.patch.yml"

if [ ! -f "$ROOT/lib/client.js" ] || [ ! -f "$ROOT/lib/index.js" ]; then
  echo "missing $ROOT/lib/*.js" >&2
  exit 1
fi
mkdir -p "$(dirname "$PKG_PATH")" "$PROFILE_DIR"
ln -sfn "$ROOT" "$PKG_PATH"

if [ ! -f "$PATCH" ]; then
  printf '%s\n' '# User patch layer for this profile.' > "$PATCH"
fi
if ! grep -q 'task-pulse' "$PATCH"; then
  cat >> "$PATCH" <<YAML

# TaskPulse
- insert:
    - id: task-pulse
      name: "$NAME"
YAML
  echo "Added loader entry to $PATCH"
else
  echo "Loader entry already present in $PATCH"
fi

# Verify Node can resolve the package from the profile.
(cd "$PROFILE_DIR" && node -e "import('$NAME').then(()=>console.log('resolved $NAME'))")

cat <<'EOF'

Installed. Restart DSH Desktop to load the plugin.
Then use:
  /task-pulse        skill
  /tp server status  native command
EOF
