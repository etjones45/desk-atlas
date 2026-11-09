#!/bin/bash
# Applies an update: refresh Python packages, service files, the car-atlas command and Pi settings,
# then restart the background services.
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

# The car-atlas command (kept in sync with the code)
cat > /usr/local/bin/car-atlas <<'EOF'
#!/bin/bash
S=/opt/car-atlas/src/car/scripts
case "${1:-}" in
  doctor) exec "$S/doctor.sh" ;;
  drive-setup) exec "$S/drive-setup.sh" ;;
  pair) shift; exec "$S/pair.sh" "$@" ;;
  update) exec "$S/update.sh" ;;
  usb-fix) shift; exec "$S/usb-fix.sh" "$@" ;;
  usb-rebind) exec "$S/teslacam-gadget.sh" rebind ;;
  version) echo "Car Atlas v$(cat /opt/car-atlas/src/car/VERSION) ($(git -C /opt/car-atlas/src rev-parse --short HEAD))" ;;
  logs) exec journalctl -u car-atlas-teslacam -u car-atlas-uploader -u car-atlas-monitor -u car-atlas-update -u car-atlas-tune -n 100 --no-pager ;;
  status) cat /var/lib/car-atlas/status.json ;;
  *) echo "car-atlas doctor | version | drive-setup | pair CODE | update | usb-rebind | usb-fix [undo] | logs | status" ;;
esac
EOF
chmod +x /usr/local/bin/car-atlas

systemctl enable car-atlas-teslacam.service car-atlas-uploader.service car-atlas-monitor.service \
  car-atlas-tune.service car-atlas-update.timer >/dev/null 2>&1
systemctl start car-atlas-tune.service || true
systemctl restart car-atlas-monitor.service car-atlas-uploader.service
systemctl start car-atlas-update.timer

echo "[post-update] done (v$(cat "$CAR/VERSION"))"
