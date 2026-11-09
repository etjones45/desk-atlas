#!/bin/bash
# Links this Pi to the Car Atlas app (car.etjarvis.com).
#   sudo car-atlas pair ABCD-EFGH        (get the code in the app: Settings -> Connect the Pi)
set -u
CODE="${1:-}"
URL="${CLOUD_URL_OVERRIDE:-https://car.etjarvis.com}"
CONF=/etc/car-atlas/config.env
if [ -z "$CODE" ]; then
  echo "Usage: sudo car-atlas pair YOUR-CODE   (make a code in the app: Settings -> Connect the Pi)"
  exit 2
fi
if [ "$(id -u)" != 0 ]; then echo "Run with sudo"; exit 1; fi

echo "Linking this Pi to $URL ..."
RESP=$(curl -sS -m 30 -X POST -H "Content-Type: application/json" \
  -d "{\"code\":\"$CODE\",\"hostname\":\"$(hostname)\"}" "$URL/api/pair" 2>&1)
KEY=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try:
    d = json.load(sys.stdin); print(d.get("key", ""))
except Exception:
    print("")')
if [ -z "$KEY" ]; then
  MSG=$(printf '%s' "$RESP" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("error",""))
except Exception: print("")')
  echo "Couldn't link: ${MSG:-$RESP}"
  echo "Make a new code in the app (Settings -> Connect the Pi) and try again."
  exit 1
fi

mkdir -p /etc/car-atlas
touch "$CONF"
sed -i '/^CLOUD_URL=/d;/^CLOUD_KEY=/d' "$CONF"
printf 'CLOUD_URL=%s\nCLOUD_KEY=%s\n' "$URL" "$KEY" >> "$CONF"
chmod 600 "$CONF"
systemctl restart car-atlas-monitor.service car-atlas-uploader.service 2>/dev/null
echo "Linked! Open the app: the Pi shows up within a minute."
