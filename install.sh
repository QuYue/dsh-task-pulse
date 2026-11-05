#!/usr/bin/env bash
# TaskPulse is a DSH bundle. DSH 0.2.2+ installs bundles through Plugin Manager;
# this script only prints the local checkout path to paste there.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat <<TXT
TaskPulse path:
  $ROOT

Install:
  1. Open DSH Desktop → Settings → Plugins → Add plugin
  2. Paste the path above
  3. Install, then restart DSH Desktop

Verify:
  /task-pulse
  /tp server status

The package declares dsh.bundle.patch; do not edit cordis.patch.yml manually.
TXT
