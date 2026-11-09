#!/bin/bash
# Try to make the Pi's USB-C OTG port show up to the car as a drive.
# The Orange Pi image sets the port to "peripheral", which some H618 boards
# never report to the host. This switches it to "otg" with a small device-tree overlay.
#   sudo car-atlas usb-fix        -> apply and reboot
#   sudo car-atlas usb-fix undo   -> remove it and reboot
set -eu
ENV=/boot/orangepiEnv.txt
DIR=/boot/overlay-user
NAME=car-atlas-usb0-otg
if [ "$(id -u)" != 0 ]; then echo "Run with sudo"; exit 1; fi
[ -f "$ENV" ] || { echo "Can't find $ENV on this Pi"; exit 1; }

if [ "${1:-}" = "undo" ]; then
  sed -i "s/ *$NAME//; /^user_overlays= *$/d" "$ENV"
  rm -f "$DIR/$NAME.dtbo"
  echo "Removed the USB fix. Restarting in 5 seconds..."
  sleep 5; systemctl reboot; exit 0
fi

command -v dtc >/dev/null || DEBIAN_FRONTEND=noninteractive apt-get install -y -qq device-tree-compiler >/dev/null
mkdir -p "$DIR"
cp -n "$ENV" "$ENV.before-car-atlas" 2>/dev/null || true
cat > "/tmp/$NAME.dts" <<'EOF'
/dts-v1/;
/plugin/;
/ {
	fragment@0 {
		target-path = "/soc/usb@5100000";
		__overlay__ {
			dr_mode = "otg";
		};
	};
};
EOF
dtc -q -@ -I dts -O dtb -o "$DIR/$NAME.dtbo" "/tmp/$NAME.dts"
if grep -q '^user_overlays=' "$ENV"; then
  grep -q "$NAME" "$ENV" || sed -i "s/^user_overlays=\(.*\)/user_overlays=\1 $NAME/" "$ENV"
else
  echo "user_overlays=$NAME" >> "$ENV"
fi
echo "USB fix installed (backup of the old settings: $ENV.before-car-atlas)."
echo "Restarting in 5 seconds. After it's back (about 1-2 min, car awake), run: sudo car-atlas doctor"
echo "If anything looks wrong afterward, run: sudo car-atlas usb-fix undo"
sleep 5
systemctl reboot
