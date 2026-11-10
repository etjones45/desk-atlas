# Car Atlas versions

## 1.2 (2026-11-10)
- Run the Pi's health check, USB check, logs and "what's it doing" from the app and read the report there. No laptop needed.
- Speed tests: run one from the app, plus one small automatic test a day. History chart on the Starlink tab.
- Drops: the Pi logs every time the Starlink loses service for 30+ seconds, how long, and why.
- Nothing gets lost while offline: readings and alerts are kept on the Pi and sent when the internet is back.
- Today card: time awake, % of time with a good signal, data, drops, clips, Starlink energy use.
- "What works right now" (video calls / streaming / browsing) and how many devices are on the car WiFi.
- Drive mode: one big glanceable screen for a phone mount.
- Sky view: the dish's own picture of which parts of the sky are blocked.
- Upload rules in the app: pause uploads, Starlink on/off for clips and Sentry, upload speed, daily limit.
- Live upload progress with time left. Each clip opens to buttons for every camera.
- Google Drive storage meter, a low-space alert, and optional auto-clear of old footage.
- Monthly data plan tracking with a heads-up at 80% and uploads that wait for home WiFi near the limit.
- Heat protection: uploads pause above 84 C and resume when the Pi cools.
- Share the car WiFi with a QR code. Siri Shortcuts for car status, saving dashcam and speed tests.
- New notifications: daily recap, Starlink online, car woke up at night, quiet hours.
- Activity page with everything that happened, filterable.
- Dashcam drive: shows when the car last wrote video, counts connection resets, and tries a full re-setup
  if the car doesn't connect. Clearer cable tips (flip the plug, swap the cable, computer test).
- Housekeeping for long Sentry sessions: trims logs before they fill up, quiets a known noisy empty USB port.

## 1.1.2 (2026-11-09)
- Stop the USB readings from filling the system log (one register dump on this chip logs warnings).

## 1.1.1 (2026-11-09)
- Dashcam USB troubleshooting: `car-atlas usb-debug` shows what the Pi's USB chip sees (power from the car,
  session, kernel messages). The same readings go to the app so Atlas can check them remotely.
- Time zone shows correctly (the Pi was already on Denver time; the check was reading an old file).

## 1.1 (2026-11-09)
- Versions: the Pi reports which version it's running; the app compares it with the latest.
- Dashcam drive: live USB diagnostics (which port, whether the car connected), automatic retry if the
  car doesn't connect in the first minute, alerts the first time the car connects and if it stops seeing the drive.
- Dashcam drive grows to use the free space on the SD card (only while it's still empty).
- Reads the car's drive whether it's FAT32 or exFAT (if the car ever reformats it), with or without a partition table.
- Uploads EncryptedClips too, if dashcam encryption is turned on in the car.
- Location: Starlink stopped sharing GPS with local devices (May 2026). The Pi now reads a USB GPS if one is
  plugged in (USB1 port). Saved/Sentry clips show on the map using the car's own event location.
- Driving speed and parked/driving state when a GPS is connected.
- Pi tuning at every boot: Denver time zone, cooler CPU setting, Starlink WiFi never gives up reconnecting,
  smaller system logs.
- Lighter health checks (less CPU, cooler Pi) and shorter network timeouts so a weak signal doesn't stall anything.
- Drive setup instructions now say clearly to run the login step on the Mac.
- New commands: `car-atlas version`, `car-atlas usb-fix` (fallback USB mode, with undo).
- The drive image is built and read even where the system can't see its partition (offset fallback, and mtools
  as a backup reader). The drive is never resized or checked while the car is using it.
- Alerts if the dashcam drive can't be set up at boot, if the car never connects to it, and when the Pi
  finishes an update.
- The Pi updates itself within minutes when the app says a newer version exists (not just every 30 min).

## 1.0 (2026-11-08)
- First release: dashcam USB drive, Google Drive uploads, Starlink monitor, coverage map, car.etjarvis.com app,
  push notifications, remote commands, auto-updates.
