#!/usr/bin/env bash
# Pull source of truth into ~/desk-atlas-upstream only.
set -euo pipefail
UPSTREAM="${HOME}/desk-atlas-upstream"
if [[ ! -d "$UPSTREAM/.git" ]]; then echo "No upstream clone. Run install-on-pi.sh first."; exit 1; fi
git -C "$UPSTREAM" fetch --all --prune
git -C "$UPSTREAM" pull --ff-only
git -C "$UPSTREAM" log -1 --oneline
echo "Done. Live ~/desk-atlas was not modified."
