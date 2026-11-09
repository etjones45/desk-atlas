#!/bin/bash
# Connects the Pi to ET's Google Drive (one time). Run on the Pi:  sudo car-atlas drive-setup
set -u
CONF=/etc/car-atlas/rclone.conf
SRC="$(cd "$(dirname "$0")/.." && pwd)"
set -a
# shellcheck disable=SC1091
. "$SRC/config.default.env"
# shellcheck disable=SC1091
[ -f /etc/car-atlas/config.env ] && . /etc/car-atlas/config.env
set +a

cat <<'EOF'

=== Connect the Pi to Google Drive ===
Do the next step on your MAC, not the Pi. Open a NEW Terminal window on the Mac.
The line you type on should start with your Mac name (like ejones45@...), NOT orangepi@.
Then run these two lines there:

  curl -fsSL https://rclone.org/install.sh | sudo bash
  rclone authorize "drive"

A browser opens. Sign in with skethanjones@gmail.com and click Allow.
Back in the Mac Terminal, copy the line that starts with {"access_token" ... and ends with }
(everything between "Paste the following" and "End paste").

EOF
read -r -p "Paste it here and press Enter: " RAW
TOKEN=$(printf '%s' "$RAW" | python3 -c '
import sys, json, re
s = sys.stdin.read()
m = re.search(r"\{.*\}", s, re.S)
if not m: sys.exit(1)
t = json.loads(m.group(0))
if "access_token" not in t and "refresh_token" not in t: sys.exit(1)
print(json.dumps(t, separators=(",", ":")))
') || { echo "That didn't look like the token. Run this again and paste the whole {...} line."; exit 1; }

mkdir -p /etc/car-atlas
umask 077
cat > "$CONF" <<EOF
[gdrive]
type = drive
scope = drive
token = $TOKEN
EOF
chmod 600 "$CONF"

echo "Checking the connection..."
if rclone --config "$CONF" lsf "gdrive,root_folder_id=${DRIVE_ROOT_ID}:" >/tmp/car-atlas-drive-test 2>&1; then
  echo "Connected. I can see these folders in Tesla Footage:"
  sed 's/^/   /' /tmp/car-atlas-drive-test
  systemctl restart car-atlas-monitor.service car-atlas-uploader.service 2>/dev/null
  echo "All set. Status will show up on the dashboard within a minute or two."
else
  echo "Couldn't reach Google Drive with that token:"
  tail -5 /tmp/car-atlas-drive-test
  exit 1
fi
