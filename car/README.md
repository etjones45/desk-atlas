# Car Atlas (Desk Atlas, moved into the Model Y)

Orange Pi Zero 2W in the glovebox + Starlink Mini in the back window. Current version: see `VERSION`
(release notes in `CHANGELOG.md`).

## Wiring
- **Glovebox USB port → the Pi's USB0.** USB0 is the USB-C port at the end of the board, next to the
  antenna connector, farthest from the mini-HDMI. It's the only port that can act as a USB drive for the car.
  Use a data cable (some USB-C cables only charge).
- **USB1** (the middle USB-C) is host-only. Optional: a USB GPS stick there (with a USB-C OTG adapter).

## What it does
- **Dashcam / Sentry drive**: the Pi acts as a USB drive for the car (`scripts/teslacam-gadget.sh`).
  The car records to a disk image on the SD card. With `TESLACAM_SIZE_GB=auto` the image uses the free
  space on the SD card (minus 5 GB), and grows on boot only while it's still empty. The Pi re-offers the
  drive once if the car doesn't connect, and alerts if it never does.
- **Uploads to Google Drive** (`atlas/uploader.py`): saved Dashcam clips (and EncryptedClips) ->
  `Tesla Footage/Dashcam`, Sentry events -> `Tesla Footage/Sentry`. Read-only access while the car owns
  the drive (FAT32 or exFAT); a folder is uploaded only after it stops changing. Capped on Starlink,
  unlimited at home. The rolling last hour (RecentClips) is uploaded only on request (app button).
- **Frees space** at home: when the drive is 70%+ full, deletes clips that are already in Drive and
  older than 3 days (the drive is unplugged from the car for ~10 s while this runs).
- **Starlink + Pi health** (`atlas/monitor.py`): dish state, ping, drops, obstructions, alerts, power,
  data usage, Pi temp/WiFi/Tailscale, dashcam USB link.
- **Location**: Starlink removed dish GPS from its local API in May 2026. A USB GPS (`atlas/gps.py`)
  powers the coverage map, Find my car and speed. Clip pins use the car's own event.json location.
- **Auto-restart** the dish if it's stuck (sky clear, no service) for 15 minutes.
- **Pi tuning** at every boot (`scripts/tune.sh`): time zone, CPU governor, Starlink WiFi retries, log size.
- **Auto-updates** from the `car` branch at boot, every 30 min, and right away when the app reports a
  newer version. Updates never restart the dashcam drive.

## App-controlled settings
Upload rules, speed tests, heat protection, Drive retention and the data plan are set in the app and sent to the
Pi with every check-in (`/var/lib/car-atlas/app_settings.json`, see `DEFAULT_SETTINGS` in `atlas/common.py`).
Add-ons live in `atlas/extras.py` (drops, offline catch-up, energy, devices, sky view, speed tests, housekeeping).
Upgrading an existing database: `cloud/migrate-1.2.sql`.

## Versions
`car/VERSION` is the release number. The Pi reports what it runs; the app (Pi tab → Software) compares it
with `VERSION` on GitHub ("should be on"). Release = bump `car/VERSION` + `APP_VERSION` in
`cloud/src/index.js` and `cloud/public/app.js`, add notes to `CHANGELOG.md`, push, deploy the worker.

## Install (on the Pi)
```
curl -fsSL https://raw.githubusercontent.com/etjones45/desk-atlas/car/car/install.sh | sudo bash -s -- PAIRCODE
sudo car-atlas drive-setup
```

## Commands
`sudo car-atlas doctor` · `version` · `logs` · `update` · `status` · `usb-rebind` · `usb-fix [undo]` · `pair CODE`

## Settings
Defaults: `car/config.default.env`. Local overrides: `/etc/car-atlas/config.env`.
Google auth lives only on the Pi in `/etc/car-atlas/rclone.conf` (never in git).

## Phone app: https://car.etjarvis.com
Cloudflare Worker + D1 in `car/cloud/` (deploy with `npx wrangler deploy`). Household password login,
web push notifications (add to Home Screen on iPhone first), Pi pairing from Settings.
The Pi reports every 30 s (`/api/pi/status`), pushes coverage points and uploaded clips (with Tesla's
thumbnail), and polls `/api/pi/commands` for app actions: save recent dashcam, restart Starlink,
check for updates, restart services, restart the Pi, test alert, re-offer the dashcam drive, USB fallback mode.
Secrets (push signing key, password hash, device key) live only in Cloudflare, never in git.

The older Claude-artifact dashboard (`car/dashboard/`) still reads `Pi Status/status.txt` from Drive as a backup.
