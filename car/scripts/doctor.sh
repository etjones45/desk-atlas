#!/bin/bash
# Quick health check. Run on the Pi:  sudo car-atlas doctor
SRC="$(cd "$(dirname "$0")/.." && pwd)"
ok()   { echo "  [OK]   $*"; }
bad()  { echo "  [!!]   $*"; }
info() { echo "  [..]   $*"; }

echo "== Car Atlas check ($(date)) =="
echo "Code version: $(git -C "$SRC/.." rev-parse --short HEAD 2>/dev/null)"

echo "-- Dashcam drive (what the car records to)"
G=$(cat /run/car-atlas/gadget.json 2>/dev/null)
case "$G" in
  *'"attached"'*) ok "Pi is presenting a USB drive to the car";;
  *'"unsupported"'*) bad "This Pi's kernel can't act as a USB drive. KEEP A FLASH DRIVE IN THE CAR.";;
  *) bad "USB drive mode not running: ${G:-no state}";;
esac
UDC=$(cat /sys/kernel/config/usb_gadget/teslacam/UDC 2>/dev/null)
if [ -n "$UDC" ]; then
  S=$(cat "/sys/class/udc/$UDC/state" 2>/dev/null)
  if [ "$S" = "configured" ]; then ok "Car has connected to the drive (USB state: configured)"
  else info "USB state: ${S:-unknown} (should say 'configured' when plugged into the car's glovebox port with the car awake)"; fi
fi
echo "   USB device controllers on this Pi: $(ls /sys/class/udc 2>/dev/null | tr '\n' ' ')"
[ -f /var/lib/car-atlas/teslacam.img ] && info "Drive image: $(du -h --apparent-size /var/lib/car-atlas/teslacam.img | cut -f1)"

echo "-- Services"
for s in car-atlas-teslacam car-atlas-uploader car-atlas-monitor car-atlas-update.timer tailscaled; do
  st=$(systemctl is-active "$s" 2>/dev/null)
  [ "$st" = active ] && ok "$s" || bad "$s: $st"
done

echo "-- Network"
info "WiFi: $(nmcli -t -f ACTIVE,SSID,SIGNAL dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2- )"
if timeout 5 bash -c '</dev/tcp/www.googleapis.com/443' 2>/dev/null; then ok "Internet"; else bad "No internet right now"; fi
if timeout 3 bash -c '</dev/tcp/192.168.100.1/9200' 2>/dev/null; then ok "Starlink dish answering"; else info "Starlink dish not reachable (normal if not on the Starlink WiFi)"; fi

echo "-- Google Drive"
if grep -q '\[gdrive\]' /etc/car-atlas/rclone.conf 2>/dev/null; then ok "Drive connected"; else bad "Drive not set up yet: run  sudo car-atlas drive-setup"; fi

echo "-- Pi"
info "Temp: $(awk '{printf "%.1f C", $1/1000}' /sys/class/thermal/thermal_zone0/temp)   SD free: $(df -h / | awk 'NR==2{print $4}')"
U=$(cat /run/car-atlas/uploader.json 2>/dev/null)
[ -n "$U" ] && info "Uploader: $(echo "$U" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("pending",d.get("pending"),"| waiting for",d.get("waiting_for"),"| last upload",(d.get("last_upload") or {}).get("folder"))' 2>/dev/null)"
