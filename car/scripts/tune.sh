#!/bin/bash
# Keeps the Pi set up the way Car Atlas wants it. Safe to run any time (runs at every boot).
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
set -a
# shellcheck disable=SC1091
. "$SRC/config.default.env"
# shellcheck disable=SC1091
[ -f /etc/car-atlas/config.env ] && . /etc/car-atlas/config.env
set +a
log() { echo "[tune] $*"; }

# Local time zone (daily upload limits and timestamps follow Denver time)
TZ_WANT="${TIMEZONE:-America/Denver}"
TZ_NOW=$(readlink -f /etc/localtime 2>/dev/null | sed 's|.*/zoneinfo/||')
if { [ "$TZ_NOW" != "$TZ_WANT" ] || [ "$(cat /etc/timezone 2>/dev/null)" != "$TZ_WANT" ]; } && [ -e "/usr/share/zoneinfo/$TZ_WANT" ]; then
  timedatectl set-timezone "$TZ_WANT" 2>/dev/null || ln -sf "/usr/share/zoneinfo/$TZ_WANT" /etc/localtime
  echo "$TZ_WANT" > /etc/timezone
  log "time zone set to $TZ_WANT"
fi

# Cooler CPU: scale speed with load instead of running flat out
for pol in /sys/devices/system/cpu/cpufreq/policy*; do
  [ -d "$pol" ] || continue
  avail=$(cat "$pol/scaling_available_governors" 2>/dev/null)
  for gov in schedutil ondemand conservative; do
    if echo "$avail" | grep -qw "$gov"; then
      [ "$(cat "$pol/scaling_governor")" = "$gov" ] || { echo "$gov" > "$pol/scaling_governor" 2>/dev/null && log "CPU governor -> $gov"; }
      break
    fi
  done
done

# Starlink WiFi: never stop trying to reconnect (the dish boots slower than the Pi)
if nmcli -t -f NAME connection show 2>/dev/null | grep -qx starlink; then
  if [ "$(nmcli -g connection.autoconnect-retries connection show starlink 2>/dev/null)" != "0" ]; then
    nmcli connection modify starlink connection.autoconnect-retries 0 && log "starlink WiFi: unlimited reconnect tries"
  fi
fi

# Smaller system logs (less SD card wear)
if [ ! -f /etc/systemd/journald.conf.d/car-atlas.conf ]; then
  mkdir -p /etc/systemd/journald.conf.d
  printf '[Journal]\nSystemMaxUse=60M\nRuntimeMaxUse=30M\n' > /etc/systemd/journald.conf.d/car-atlas.conf
  systemctl restart systemd-journald 2>/dev/null
  log "journal size capped"
fi

# Desk Atlas face/listening stay off in the car (heat, and the glovebox is closed)
for s in desk-atlas.service desk-atlas-ears.service; do
  if systemctl is-enabled "$s" >/dev/null 2>&1; then systemctl disable --now "$s" >/dev/null 2>&1 && log "disabled $s"; fi
done

# Tools the dashcam reader needs (exFAT if the car ever reformats the drive; mtools as a backup way
# to read the drive). Only when online.
need=""
command -v fsck.exfat >/dev/null 2>&1 || need="$need exfatprogs"
command -v mdir >/dev/null 2>&1 || need="$need mtools"
command -v arp-scan >/dev/null 2>&1 || need="$need arp-scan"   # counts devices on the car WiFi
if [ -n "$need" ] && timeout 5 bash -c '</dev/tcp/deb.debian.org/80' 2>/dev/null; then
  # shellcheck disable=SC2086
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $need >/dev/null 2>&1 \
     || { apt-get update -qq >/dev/null 2>&1 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $need >/dev/null 2>&1; }; then
    log "installed$need"
  fi
fi
exit 0
