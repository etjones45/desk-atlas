#!/bin/bash
# Makes the Pi show up to the car as a USB drive (for Dashcam + Sentry).
# The "drive" is a disk image file on the SD card. Runs early at boot.
#   teslacam-gadget.sh start   -> create/grow image if needed, offer it to the car
#   teslacam-gadget.sh stop    -> stop offering it
#   teslacam-gadget.sh rebind  -> re-offer it (like unplugging and plugging back in)
#   teslacam-gadget.sh status  -> print state
# The car must be plugged into the Pi's USB0 port (end of the board, next to the antenna).
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
set -a
# shellcheck disable=SC1091
[ -f "$SRC/config.default.env" ] && . "$SRC/config.default.env"
# shellcheck disable=SC1091
[ -f /etc/car-atlas/config.env ] && . /etc/car-atlas/config.env
set +a

IMG="${TESLACAM_IMAGE:-/var/lib/car-atlas/teslacam.img}"
SIZE_SETTING="${TESLACAM_SIZE_GB:-auto}"
RESERVE_GB=4
G=/sys/kernel/config/usb_gadget/teslacam
STATE=/run/car-atlas/gadget.json
mkdir -p /run/car-atlas "$(dirname "$IMG")"
UDC=""

log() { echo "[teslacam] $*"; }
state() { # state <gadget> <detail>
  printf '{"gadget":"%s","detail":"%s","udc":"%s","image_gb":%s,"at":%s}\n' \
    "$1" "$2" "${UDC:-}" "$(image_gb)" "$(date +%s)" > "$STATE"
}
image_gb() { if [ -f "$IMG" ]; then echo $(( $(stat -c %s "$IMG") / 1000000000 )); else echo 0; fi; }

target_gb() {
  # How big the drive should be: a fixed number, or "auto" = all free space minus a reserve.
  if [ "$SIZE_SETTING" != "auto" ]; then echo "$SIZE_SETTING"; return; fi
  local free_gb current_gb
  free_gb=$(df -BG --output=avail "$(dirname "$IMG")" | tail -1 | tr -dc '0-9')
  current_gb=0
  [ -f "$IMG" ] && current_gb=$(( $(stat -c %s "$IMG") / 1073741824 ))
  echo $(( free_gb + current_gb - RESERVE_GB ))
}

part_attach() { # part_attach <image> [ro] -> prints "<device> <loops...>"
  local img=$1 ro=${2:-} loop start size p
  loop=$(losetup ${ro:+-r} -P -f --show "$img") || return 1
  for _ in 1 2 3 4 5 6 7 8 9 10; do [ -e "${loop}p1" ] && { echo "${loop}p1 $loop"; return 0; }; sleep 0.3; done
  # No partition node (no udev): map partition 1 by its offset instead
  read -r start size < <(sfdisk -d "$img" 2>/dev/null | awk -F'[=,]' '/start=/{for(i=1;i<=NF;i++){if($i~/start/)s=$(i+1);if($i~/size/)z=$(i+1)}; gsub(/ /,"",s); gsub(/ /,"",z); print s, z; exit}')
  if [ -n "${start:-}" ]; then
    p=$(losetup ${ro:+-r} -f --show -o $((start * 512)) --sizelimit $((size * 512)) "$img") || { echo "$loop $loop"; return 0; }
    echo "$p $loop $p"; return 0
  fi
  echo "$loop $loop"
}
part_detach() { shift; for l in "$@"; do losetup -d "$l" 2>/dev/null; done; }

build_image() { # build_image <size_gb>
  local size=$1 att mnt
  log "Creating ${size}G dashcam drive at $IMG"
  rm -f "$IMG.tmp"
  fallocate -l "${size}G" "$IMG.tmp" || truncate -s "${size}G" "$IMG.tmp" || return 1
  echo 'type=c' | sfdisk --quiet "$IMG.tmp" || return 1   # one FAT32 partition; the car wants a partition table
  att=$(part_attach "$IMG.tmp") || return 1
  # shellcheck disable=SC2086
  set -- $att
  mkfs.vfat -F 32 -n TESLACAM "$1" >/dev/null || { part_detach "$@"; return 1; }
  mnt=$(mktemp -d)
  if mount "$1" "$mnt" 2>/dev/null; then
    mkdir -p "$mnt/TeslaCam" && sync; umount "$mnt"
  elif command -v mmd >/dev/null; then
    MTOOLS_SKIP_CHECK=1 mmd -i "$1" ::/TeslaCam 2>/dev/null   # same thing without mounting
  else
    log "Couldn't add the TeslaCam folder (the car can still format the drive itself)"
  fi
  rmdir "$mnt"
  part_detach "$@"
  mv "$IMG.tmp" "$IMG"
  log "Dashcam drive ready (${size}G)"
}

image_is_empty() { # true if the car never saved any video to it
  local att mnt count
  att=$(part_attach "$IMG" ro) || return 1
  # shellcheck disable=SC2086
  set -- $att
  mnt=$(mktemp -d)
  if mount -o ro "$1" "$mnt" 2>/dev/null; then
    count=$(find "$mnt" -type f \( -iname '*.mp4' -o -iname '*.mov' \) 2>/dev/null | head -1 | wc -l)
    umount "$mnt"
  elif command -v mdir >/dev/null && MTOOLS_SKIP_CHECK=1 mdir -i "$1" ::/ >/dev/null 2>&1; then
    count=$(MTOOLS_SKIP_CHECK=1 mdir -/ -b -i "$1" ::/ 2>/dev/null | grep -ciE '\.(mp4|mov)$')
  else
    count=1   # can't read it: treat as not empty, never touch
  fi
  rmdir "$mnt"; part_detach "$@"
  [ "$count" = 0 ]
}

ensure_image() {
  local want have
  want=$(target_gb)
  if [ ! -f "$IMG" ]; then
    if [ "$want" -lt 4 ]; then log "Not enough free space for a dashcam drive"; state error "no space on SD card"; return 1; fi
    build_image "$want" || return 1
    return 0
  fi
  have=$(( $(stat -c %s "$IMG") / 1073741824 ))
  # Grow only while the drive is still empty (nothing to lose), and only if it's worth it.
  if [ "$SIZE_SETTING" = "auto" ] && [ $(( want - have )) -ge 3 ] && image_is_empty; then
    log "Growing empty dashcam drive from ${have}G to ${want}G"
    rm -f "$IMG"
    build_image "$want" || return 1
  fi
}

find_udc() {
  UDC=$(ls /sys/class/udc 2>/dev/null | head -1)
  [ -n "$UDC" ] && return 0
  for f in /sys/class/usb_role/*/role; do [ -w "$f" ] && echo device > "$f" 2>/dev/null; done
  for f in /sys/devices/platform/soc*/*usbc0*/usb_device /sys/devices/platform/*usbc0*/usb_device; do
    [ -r "$f" ] && cat "$f" >/dev/null 2>&1
  done
  for m in musb_hdrc sunxi sunxi_usb_udc; do modprobe "$m" 2>/dev/null; done
  sleep 2
  UDC=$(ls /sys/class/udc 2>/dev/null | head -1)
  [ -n "$UDC" ]
}

bind() {
  echo "$UDC" > "$G/UDC" 2>/dev/null
}

start() {
  modprobe libcomposite 2>/dev/null
  mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config
  # Never touch the image while the car is using it
  if [ -d "$G" ] && [ -n "$(cat "$G/UDC" 2>/dev/null)" ]; then
    UDC=$(cat "$G/UDC"); log "Already offered on $UDC"; state attached "already offered"; exit 0
  fi
  ensure_image || { state error "could not create dashcam drive"; exit 1; }
  if ! find_udc; then
    log "This Pi isn't offering USB device mode. The car cannot see the Pi as a drive."
    state unsupported "no USB device controller (UDC)"
    exit 0
  fi
  mkdir -p "$G" && cd "$G" || exit 1
  echo 0x1d6b > idVendor
  echo 0x0104 > idProduct
  echo 0x0100 > bcdDevice
  echo 0x0200 > bcdUSB
  mkdir -p strings/0x409 configs/c.1/strings/0x409 functions/mass_storage.usb0
  echo "CA$(cut -c1-10 /etc/machine-id 2>/dev/null)" > strings/0x409/serialnumber
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
  if bind; then
    log "Offering the dashcam drive on $UDC (car must be on the USB0 port)"
    state attached "ok"
  else
    log "Could not offer the drive on $UDC"
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
  log "Stopped offering the drive"
}

rebind() {
  if [ ! -d "$G" ]; then start; return; fi
  find_udc || { state unsupported "no USB device controller (UDC)"; return 0; }
  echo "" > "$G/UDC" 2>/dev/null
  sleep 2
  if bind; then state attached "re-offered"; log "Re-offered the drive on $UDC"; else state error "re-offer failed"; fi
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
  rebind) rebind ;;
  status) status ;;
  *) echo "usage: $0 start|stop|rebind|status"; exit 2 ;;
esac
