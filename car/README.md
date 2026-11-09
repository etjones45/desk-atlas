# Car Atlas (Desk Atlas, moved into the Model Y)

Orange Pi Zero 2W in the glovebox + Starlink Mini in the back window.

## What it does
- **Dashcam / Sentry drive**: the Pi pretends to be a USB drive for the car (`teslacam-gadget.sh`).
  The car records to a 16 GB disk image on the SD card.
- **Uploads to Google Drive** (`atlas/uploader.py`): saved Dashcam clips -> `Tesla Footage/Dashcam`,
  Sentry events -> `Tesla Footage/Sentry`. Read-only access while the car owns the drive; a folder is
  uploaded only after it stops changing. Capped to ~3 Mbps and 5 GB/day on Starlink, unlimited at home.
  The rolling last hour (RecentClips) is uploaded only on request (dashboard button).
- **Frees space** at home: when the drive is 70%+ full, deletes clips that are already in Drive and
  older than 3 days (drive is unplugged from the car for ~10 s while this runs).
- **Starlink + Pi health** (`atlas/monitor.py`): dish state, ping, drops, obstructions, alerts, power,
  data usage, GPS coverage map, Pi temp/WiFi/Tailscale. Published every minute to
  `Tesla Footage/Pi Status/status.txt` (and `coverage.txt`) for the dashboard.
- **Auto-restart** the dish if it is stuck (sky clear, no service) for 15 minutes.
- **Phone alerts** via the ntfy app (topic in `/etc/car-atlas/config.env`).
- **Auto-updates** from the `car` branch at boot and every 30 min. Updates never restart the dashcam drive.

## Install (on the Pi)
```
curl -fsSL https://raw.githubusercontent.com/etjones45/desk-atlas/car/car/install.sh | sudo bash
sudo car-atlas drive-setup
```

## Commands
`sudo car-atlas doctor` · `sudo car-atlas logs` · `sudo car-atlas update` · `sudo car-atlas status`

## Settings
Defaults: `car/config.default.env`. Local overrides: `/etc/car-atlas/config.env`.
Google auth lives only on the Pi in `/etc/car-atlas/rclone.conf` (never in git).
