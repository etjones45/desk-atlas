#!/bin/bash
# Quick health check. Run on the Pi:  sudo car-atlas doctor
SRC="$(cd "$(dirname "$0")/.." && pwd)"
ok()   { echo "  [OK]   $*"; }
bad()  { echo "  [!!]   $*"; }
info() { echo "  [..]   $*"; }

echo "== Car Atlas check ($(date)) =="
echo "Version: v$(cat "$SRC/VERSION" 2>/dev/null) ($(git -C "$SRC/.." rev-parse --short HEAD 2>/dev/null))"
U=$(cat /var/lib/car-atlas/update.json 2>/dev/null)
[ -n "$U" ] && info "Last update check: $(echo "$U" | python3 -c 'import sys,json,time;d=json.load(sys.stdin);print(d.get("result"),"·",time.strftime("%b %d %I:%M %p",time.localtime(d.get("checked_at",0))))' 2>/dev/null)"

echo "-- Dashcam drive (what the car records to)"
G=$(cat /run/car-atlas/gadget.json 2>/dev/null)
case "$G" in
  *'"attached"'*) ok "Pi is offering a USB drive to the car";;
  *'"unsupported"'*) bad "This Pi isn't offering USB drive mode. KEEP A FLASH DRIVE IN THE CAR.";;
  *) bad "USB drive mode not running: ${G:-no state}";;
esac
UDC=$(cat /sys/kernel/config/usb_gadget/teslacam/UDC 2>/dev/null)
S=""
[ -n "$UDC" ] && S=$(cat "/sys/class/udc/$UDC/state" 2>/dev/null)
if [ "$S" = "configured" ]; then
  ok "Car is connected to the drive (USB state: configured)"
else
  bad "Car is NOT connected (USB state: ${S:-unknown})"
  echo "         -> The cable from the glovebox must be in the Pi's USB0 port: the USB-C port at the END of"
  echo "            the board, next to the little antenna connector, farthest from the mini-HDMI."
  echo "            (USB1, the middle port, is host-only, so the car can't see a drive through it.)"
  echo "         -> The car must be awake. Try a different cable if it still won't connect."
fi
DR=$(tr -d '\0' 2>/dev/null < /sys/firmware/devicetree/base/soc/usb@5100000/dr_mode)
info "USB0 mode: ${DR:-unknown}   controllers: $(ls /sys/class/udc 2>/dev/null | tr '\n' ' ')"
if grep -E '^(overlays|user_overlays)=' /boot/orangepiEnv.txt 2>/dev/null | grep -q 'usb0-host'; then
  bad "orangepi-config has USB0 set to HOST mode (usb0-host overlay). Remove it so the car can see the drive."
fi
grep -q 'car-atlas-usb0-otg' /boot/orangepiEnv.txt 2>/dev/null && info "Fallback USB mode (usb-fix) is installed. Undo: sudo car-atlas usb-fix undo"
[ -f /var/lib/car-atlas/teslacam.img ] && info "Drive size: $(du -h --apparent-size /var/lib/car-atlas/teslacam.img | cut -f1)  (Tesla recommends 64G+; a bigger SD card gets you there)"

echo "-- Services"
for s in car-atlas-teslacam car-atlas-uploader car-atlas-monitor car-atlas-update.timer tailscaled; do
  st=$(systemctl is-active "$s" 2>/dev/null)
  [ "$st" = active ] && ok "$s" || bad "$s: $st"
done

echo "-- Network"
info "WiFi: $(nmcli -t -f ACTIVE,SSID,SIGNAL dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2- )"
if timeout 5 bash -c '</dev/tcp/www.googleapis.com/443' 2>/dev/null; then ok "Internet"; else bad "No internet right now"; fi
if timeout 3 bash -c '</dev/tcp/192.168.100.1/9200' 2>/dev/null; then ok "Starlink dish answering"; else info "Starlink dish not reachable (normal if not on the Starlink WiFi)"; fi

echo "-- Location"
GPSDEV=$(ls /dev/serial/by-id/* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -1)
if [ -n "$GPSDEV" ]; then ok "USB GPS found: $GPSDEV"; else info "No USB GPS (optional; powers the coverage map and Find my car)"; fi

echo "-- Google Drive"
if grep -q '\[gdrive\]' /etc/car-atlas/rclone.conf 2>/dev/null; then ok "Drive connected"; else bad "Drive not set up yet: run  sudo car-atlas drive-setup"; fi

echo "-- Car Atlas app"
if grep -q '^CLOUD_KEY=' /etc/car-atlas/config.env 2>/dev/null; then ok "Linked to car.etjarvis.com"
else bad "Not linked to the app yet: make a code in the app (Settings -> Connect the Pi), then run  sudo car-atlas pair CODE"; fi

echo "-- Pi"
info "Temp: $(awk '{printf "%.1f C", $1/1000}' /sys/class/thermal/thermal_zone0/temp 2>/dev/null)   CPU: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)   SD free: $(df -h / | awk 'NR==2{print $4}')   Time zone: $(cat /etc/timezone 2>/dev/null)"
UP=$(cat /run/car-atlas/uploader.json 2>/dev/null)
[ -n "$UP" ] && info "Uploader: $(echo "$UP" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("pending",d.get("pending"),"| waiting for",d.get("waiting_for"),"| last upload",(d.get("last_upload") or {}).get("folder"))' 2>/dev/null)"
