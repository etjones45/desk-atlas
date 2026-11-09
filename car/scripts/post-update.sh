#!/bin/bash
# Applies an update: refresh Python packages and service files, restart the background services.
# The dashcam drive (car-atlas-teslacam) is NOT restarted here, so recording is never interrupted;
# changes to it take effect on the next boot.
set -u
SRC_ROOT=/opt/car-atlas/src
CAR="$SRC_ROOT/car"
VENV=/opt/car-atlas/venv

chmod +x "$CAR"/scripts/*.sh

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --disable-pip-version-check -r "$CAR/requirements.txt" || echo "[post-update] pip install failed (will retry next update)"

changed=0
for unit in "$CAR"/systemd/*; do
  name=$(basename "$unit")
  if ! cmp -s "$unit" "/etc/systemd/system/$name"; then
    cp "$unit" "/etc/systemd/system/$name"
    changed=1
  fi
done
[ "$changed" = 1 ] && systemctl daemon-reload

systemctl enable car-atlas-teslacam.service car-atlas-uploader.service car-atlas-monitor.service car-atlas-update.timer >/dev/null 2>&1
systemctl restart car-atlas-monitor.service car-atlas-uploader.service
systemctl start car-atlas-update.timer

# One-off migrations can go here, keyed on the previous version ($1).
echo "[post-update] done"
