#!/usr/bin/env bash
# Install Desk Jarvis speak stack onto the Orange Pi (run on the board after WhisPlay verifies).
# Does NOT enable systemd units until Phase 2.5 is green (see ../systemd-HOLD-UNTIL-2.5/).
set -euo pipefail
DEST="${DEST:-/opt/desk-jarvis}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

sudo mkdir -p "$DEST" "$DEST/dropbox"
sudo cp -a "$SCRIPT_DIR/speak_server.py" "$DEST/"
if [[ ! -f "$DEST/config.json" ]]; then
  sudo cp -a "$SCRIPT_DIR/config.example.json" "$DEST/config.json"
fi
if [[ ! -f "$DEST/env" ]]; then
  sudo cp -a "$SCRIPT_DIR/env.example" "$DEST/env"
  sudo chmod 600 "$DEST/env"
  echo "Created $DEST/env — add XAI_API_KEY locally (never via chat)."
fi
if [[ ! -f "$DEST/speak.secret" ]]; then
  # Generate local speak secret if missing; Hermes may also scp Phase-0 secret offline.
  openssl rand -hex 24 | sudo tee "$DEST/speak.secret" >/dev/null
  sudo chmod 600 "$DEST/speak.secret"
  echo "Generated new speak.secret at $DEST/speak.secret"
fi
echo "Installed to $DEST. Systemd units are HOLD until Phase 2.5 green."
echo "Manual test: cd $DEST && set -a && source ./env && set +a && JARVIS_PLAY=1 python3 speak_server.py"
