#!/bin/bash
# Car Atlas installer. On the Pi:
#   curl -fsSL https://raw.githubusercontent.com/etjones45/desk-atlas/car/car/install.sh | sudo bash
# Safe to run again; it just updates.
set -eu
REPO_URL=https://github.com/etjones45/desk-atlas
BRANCH=car
SRC=/opt/car-atlas/src

if [ "$(id -u)" != 0 ]; then echo "Run with sudo"; exit 1; fi
echo "=== Installing Car Atlas ==="

echo "-> Installing system packages (a minute or two)"
apt-get update -qq || echo "   (apt update had trouble; continuing)"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git rclone dosfstools fdisk python3-venv util-linux >/dev/null

echo "-> Getting the code"
mkdir -p /opt/car-atlas /etc/car-atlas /var/lib/car-atlas
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" fetch --depth 1 origin "$BRANCH" && git -C "$SRC" reset --hard FETCH_HEAD >/dev/null
else
  git clone -q --depth 1 --branch "$BRANCH" --single-branch "$REPO_URL" "$SRC"
fi
chmod +x "$SRC"/car/scripts/*.sh

if [ ! -f /etc/car-atlas/config.env ]; then
  TOPIC="car-atlas-$(tr -dc 'a-z0-9' </dev/urandom | head -c 16)"
  cat > /etc/car-atlas/config.env <<EOF
# Your local settings. Anything here overrides car/config.default.env.
NTFY_TOPIC=$TOPIC
EOF
fi

cat > /usr/local/bin/car-atlas <<'EOF'
#!/bin/bash
S=/opt/car-atlas/src/car/scripts
case "${1:-}" in
  doctor) exec "$S/doctor.sh" ;;
  drive-setup) exec "$S/drive-setup.sh" ;;
  update) exec "$S/update.sh" ;;
  logs) exec journalctl -u car-atlas-teslacam -u car-atlas-uploader -u car-atlas-monitor -u car-atlas-update -n 80 --no-pager ;;
  status) cat /var/lib/car-atlas/status.json ;;
  *) echo "car-atlas doctor | drive-setup | update | logs | status" ;;
esac
EOF
chmod +x /usr/local/bin/car-atlas

echo "-> Turning off the Desk Atlas face + listening (they heat up the Pi; voice can't work in a closed glovebox)"
systemctl disable --now desk-atlas.service desk-atlas-ears.service >/dev/null 2>&1 || true

echo "-> Setting up services"
"$SRC/car/scripts/post-update.sh" install

echo "-> Starting the dashcam drive (first time creates a 16 GB drive on the SD card)"
systemctl start car-atlas-teslacam.service || true
sleep 3

echo
"$SRC/car/scripts/doctor.sh" || true

. /etc/car-atlas/config.env
cat <<EOF

=== Installed ===
Next:
 1) Connect Google Drive (one time):   sudo car-atlas drive-setup
 2) Phone alerts: install the free "ntfy" app, tap +, and subscribe to:
        $NTFY_TOPIC
 3) Check anytime:                     sudo car-atlas doctor
EOF
