#!/bin/bash
# Makes the Pi show up to the car as a USB drive (for Dashcam + Sentry).
# The "drive" is a disk image file on the SD card. Runs early at boot.
#   teslacam-gadget.sh start   -> create image if needed, attach to car
#   teslacam-gadget.sh stop    -> detach from car
#   teslacam-gadget.sh status  -> print state
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
set -a
# shellcheck disable=SC1091
[ -f "$SRC/config.default.env" ] && . "$SRC/config.default.env"
# shellcheck disable=SC1091
[ -f /etc/car-atlas/config.env ] && . /etc/car-atlas/config.env
set +a

IMG="${TESLACAM_IMAGE:-/var/lib/car-atlas/teslacam.img}"
SIZE_GB="${TESLACAM_SIZE_GB:-16}"
G=/sys/kernel/config/usb_gadget/teslacam
STATE=/run/car-atlas/gadget.json
mkdir -p /run/car-atlas "$(dirname "$IMG")"

log() { echo "[teslacam] $*"; }
state() { # state <gadget> <detail>
  printf '{"gadget":"%s","detail":"%s","udc":"%s","at":%s}\n' "$1" "$2" "${UDC:-}" "$(date +%s)" > "$STATE"
}

make_image() {
  [ -f "$IMG" ] && return 0
  local free_gb
  free_gb=$(df -BG --output=avail "$(dirname "$IMG")" | tail -1 | tr -dc '0-9')
  if [ "${free_gb:-0}" -lt $((SIZE_GB + 3)) ]; then
    SIZE_GB=$((free_gb - 3))
    log "Not enough space for full size, using ${SIZE_GB}G"
  fi
  if [ "$SIZE_GB" -lt 4 ]; then
    log "Less than 4G available for the dashcam drive"; state error "no space on SD card"; return 1
  fi
  log "Creating ${SIZE_GB}G dashcam drive at $IMG (one time only)"
  fallocate -l "${SIZE_GB}G" "$IMG.tmp" || truncate -s "${SIZE_GB}G" "$IMG.tmp" || return 1
  # One partition, FAT32 (type c). The car wants a partition table.
  echo 'type=c' | sfdisk --quiet "$IMG.tmp" || return 1
  local loop
  loop=$(losetup -P -f --show "$IMG.tmp") || return 1
  sleep 1
  mkfs.vfat -F 32 -n TESLACAM "${loop}p1" >/dev/null || { losetup -d "$loop"; return 1; }
  local mnt
  mnt=$(mktemp -d)
  mount "${loop}p1" "$mnt" && mkdir -p "$mnt/TeslaCam" && sync && umount "$mnt"
  rmdir "$mnt"
  losetup -d "$loop"
  mv "$IMG.tmp" "$IMG"
  log "Dashcam drive created"
}

find_udc() {
  UDC=$(ls /sys/class/udc 2>/dev/null | head -1)
  [ -n "$UDC" ] && return 0
  # Try to switch the OTG port into "device" mode (different kernels expose this differently)
  for f in /sys/class/usb_role/*/role; do [ -w "$f" ] && echo device > "$f" 2>/dev/null; done
  for f in /sys/devices/platform/soc*/*usbc0*/usb_device /sys/devices/platform/*usbc0*/usb_device; do
    [ -w "$f" ] && echo 1 > "$f" 2>/dev/null
  done
  for m in sunxi_usb_udc musb_hdrc sunxi; do modprobe "$m" 2>/dev/null; done
  sleep 2
  UDC=$(ls /sys/class/udc 2>/dev/null | head -1)
  [ -n "$UDC" ]
}

start() {
  make_image || { state error "could not create dashcam drive"; exit 1; }
  modprobe libcomposite 2>/dev/null
  mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config
  if ! find_udc; then
    log "This Pi's kernel is not offering USB device mode. The car cannot see the Pi as a drive."
    state unsupported "kernel has no USB device controller (UDC)"
    exit 0
  fi
  if [ -d "$G" ] && [ -n "$(cat "$G/UDC" 2>/dev/null)" ]; then
    log "Already attached on $UDC"; state attached "already attached"; exit 0
  fi
  mkdir -p "$G" && cd "$G" || exit 1
  echo 0x1d6b > idVendor
  echo 0x0104 > idProduct
  echo 0x0100 > bcdDevice
  echo 0x0200 > bcdUSB
  mkdir -p strings/0x409 configs/c.1/strings/0x409 functions/mass_storage.usb0
  echo "CA$(cat /etc/machine-id 2>/dev/null | cut -c1-10)" > strings/0x409/serialnumber
  echo "Car Atlas" > strings/0x409/manufacturer
  echo "TeslaCam Drive" > strings/0x409/product
  echo "TeslaCam" > configs/c.1/strings/0x409/configuration
  echo 250 > configs/c.1/MaxPower
  echo 1 > functions/mass_storage.usb0/stall 2>/dev/null
  echo 1 > functions/mass_storage.usb0/lun.0/removable
  echo 0 > functions/mass_storage.usb0/lun.0/ro
  echo 0 > functions/mass_storage.usb0/lun.0/cdrom 2>/dev/null
  echo "$IMG" > functions/mass_storage.usb0/lun.0/file
  [ -e configs/c.1/mass_storage.usb0 ] || ln -s functions/mass_storage.usb0 configs/c.1/
  if echo "$UDC" > UDC; then
    log "Attached dashcam drive to the car on $UDC"
    state attached "ok"
  else
    log "Could not attach to $UDC"
    state error "attach failed on $UDC"
    exit 1
  fi
}

stop() {
  [ -d "$G" ] || { state off "stopped"; return 0; }
  echo "" > "$G/UDC" 2>/dev/null
  rm -f "$G/configs/c.1/mass_storage.usb0"
  rmdir "$G/configs/c.1/strings/0x409" "$G/configs/c.1" "$G/functions/mass_storage.usb0" \
        "$G/strings/0x409" "$G" 2>/dev/null
  state off "stopped"
  log "Detached"
}

status() {
  cat "$STATE" 2>/dev/null || echo '{"gadget":"unknown"}'
  local u
  u=$(cat "$G/UDC" 2>/dev/null)
  [ -n "$u" ] && echo "USB link state: $(cat /sys/class/udc/"$u"/state 2>/dev/null)"
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  *) echo "usage: $0 start|stop|status"; exit 2 ;;
esac
