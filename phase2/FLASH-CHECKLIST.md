# Phase 2 — Flash checklist (Ethan)

Hermes prepped software. **Ethan does** flash + physical + first boot Wi-Fi.

## Defaults (Orange Pi Debian Bookworm)

| Account | Password |
| --- | --- |
| `root` | `orangepi` |
| `orangepi` | `orangepi` |

SSH enabled by default. Password is typed blind (no echo) — that is normal.

## Before power

- [ ] Downloaded **Bookworm server** image for **1GB/2GB** (see `IMAGE.md`) — not Armbian, not 4GB build, not desktop
- [ ] Decompressed `.7z` → `.img` (+ verify `.sha` if present)
- [ ] Flashed `.img` to **32GB+** microSD with **balenaEtcher** (or Win32Diskimager / `dd`)
- [ ] Hammer-in **40-pin header** seated on Orange Pi Zero 2W 2GB
- [ ] **WhisPlay HAT** seated on header; antenna connected
- [ ] microSD inserted; **USB-C 5V 2A+** wall supply ready (not a flaky cable)

## First power (home)

- [ ] Mini-HDMI + keyboard once for first boot (or serial 115200 if preferred)
- [ ] Power on; wait for green LED heartbeat
- [ ] Log in (`orangepi` / `orangepi`)
- [ ] Join **home Wi-Fi** (not guest yet):

```bash
sudo nmcli dev wifi list
sudo nmcli dev wifi connect "HOME_SSID" password "HOME_PASS"
ip a s wlan0
```

Or `sudo nmtui`. Optional first-boot file on the SD boot partition: copy `orangepi_first_run.txt.template` → `orangepi_first_run.txt` and set WIFI vars before first insert.

- [ ] Note board IP; confirm SSH from laptop: `ssh orangepi@BOARD_IP`
- [ ] **Guest / work Wi-Fi last** (after home bring-up works)

## Then software (still Ethan-run)

- [ ] Run WhisPlay **primary** install: `cd Whisplay && sudo bash script/install_orangepi_zero2w.sh` then reboot (see `WHISPLAY-VERIFY.md`; turfptax only if 2.5 fails)
- [ ] Reboot; run verify commands; report pass/fail + script output to Jarvis
- [ ] Place `XAI_API_KEY` on Pi himself (see `KEY-HANDOFF.md`) — never paste into chat
- [ ] Copy/run `phase2/package/install-desk-jarvis.sh` when ready
- [ ] **Do not enable** `systemd-HOLD-UNTIL-2.5/` units until Jarvis says **2.5 green**
