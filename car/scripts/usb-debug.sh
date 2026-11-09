#!/bin/bash
# Deep look at the dashcam USB link (what the USB chip on the Pi is doing).
# Run on the Pi:  sudo car-atlas usb-debug     (paste the output to Atlas)
[ "$(id -u)" = 0 ] || { echo "Run with sudo: sudo car-atlas usb-debug"; exit 1; }
SRC="$(cd "$(dirname "$0")/.." && pwd)"
r() { tr -d '\0' 2>/dev/null < "$1"; }
mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug 2>/dev/null

echo "== USB debug  v$(cat "$SRC/VERSION")  $(date '+%F %T %Z')  up $(cut -d. -f1 /proc/uptime)s =="
UDC=$(ls /sys/class/udc 2>/dev/null | head -1)
G=/sys/kernel/config/usb_gadget/teslacam
echo "udc: ${UDC:-none}   bound: $(r $G/UDC)   lun: $(r $G/functions/mass_storage.usb0/lun.0/file)"
if [ -n "$UDC" ]; then
  U=/sys/class/udc/$UDC
  echo "state: $(r $U/state)   speed: $(r $U/current_speed)   is_otg: $(r $U/is_otg)   selfpowered: $(r $U/is_selfpowered)"
  D=$(readlink -f "$U/device")
  echo "musb dev: $D"
  echo "musb mode (otg state): $(r "$D/mode")"
  echo "musb vbus: $(r "$D/vbus")"
  for dd in /sys/kernel/debug/usb/"$UDC" /sys/kernel/debug/"$UDC"; do
    [ -r "$dd/regdump" ] || continue
    echo "-- regdump ($dd)"
    grep -E '^(FAddr|Power|IntrUsb|DevCtl|Testmode|Frame|Index)' "$dd/regdump" 2>/dev/null | tr '\n' ' '; echo
    dc=$(awk -F: '/^DevCtl/{gsub(/ /,"",$2); print $2}' "$dd/regdump" 2>/dev/null)
    if [ -n "$dc" ]; then
      v=$((16#$dc))
      echo "   DevCtl=0x$dc  session=$((v & 1))  host_mode=$(( (v>>2) & 1 ))  vbus_level=$(( (v>>3) & 3 ))/3  b_device=$(( (v>>7) & 1 ))"
    fi
    break
  done
fi
echo "-- interrupts (musb counter should go up when the car talks to it)"
grep -iE 'musb|usb' /proc/interrupts | sed 's/  */ /g'
echo "-- extcon"
for e in /sys/class/extcon/*; do [ -d "$e" ] && echo "$(r "$e/name"): $(r "$e/state" | tr '\n' ' ')"; done
echo "-- role switch"
for f in /sys/class/usb_role/*/role; do [ -e "$f" ] && echo "$f: $(r "$f")"; done
echo "-- device tree"
echo "usb@5100000 dr_mode: $(r /sys/firmware/devicetree/base/soc/usb@5100000/dr_mode)  status: $(r /sys/firmware/devicetree/base/soc/usb@5100000/status)"
for p in /sys/firmware/devicetree/base/soc/phy@*; do
  [ -d "$p" ] && echo "$(basename "$p") props: $(ls "$p" | tr '\n' ' ')"
done
echo "overlays: $(grep -E '^(overlays|user_overlays)=' /boot/orangepiEnv.txt 2>/dev/null | tr '\n' ' ')"
echo "-- modules"
lsmod | grep -iE 'musb|sunxi|phy_sun4i|libcomposite|mass_storage|configfs|usb_f' | awk '{print $1}' | tr '\n' ' '; echo
echo "-- kernel log (USB lines)"
dmesg 2>/dev/null | grep -iE 'musb|sun4i-usb|usb.?phy|udc|gadget|mass_storage|vbus|extcon|otg|5100000\.usb' | tail -25
echo "-- gadget service"
journalctl -u car-atlas-teslacam -b --no-pager -n 12 2>/dev/null | cut -c1-200
echo "== end =="
