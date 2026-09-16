# Phase 2 — WhisPlay install + verify (2.5)

**OS lock:** official Orange Pi **Debian Bookworm** for Zero 2W (see `IMAGE.md`).  
**Primary install:** PiSugar `script/install_orangepi_zero2w.sh` (matches Ethan’s Grok paste).  
**Fallback only if 2.5 fails:** turfptax / Armbian community path (below).

Systemd / tunnel still **HOLD** until Jarvis says 2.5 green.

## 2.5 Primary — PiSugar Orange Pi script

On the board, after **home Wi-Fi** works:

```bash
sudo apt update
sudo apt install -y git python3-pip
git clone https://github.com/PiSugar/Whisplay.git --depth 1
cd Whisplay
sudo bash script/install_orangepi_zero2w.sh
sudo reboot
```

Script is on PiSugar `main`/`master` at `script/install_orangepi_zero2w.sh`.

After reboot, keep speaker volume ~70% (higher can distort).

## Verify checklist (report to Jarvis)

```bash
# SPI (display bus on Zero 2W is SPI1)
ls -l /dev/spidev1.0 || ls -l /dev/spidev*

# I2C — expect WM8960 at 0x1a on the header bus (often i2c-3 on H618)
sudo i2cdetect -y 3 || sudo i2cdetect -y 1

# Sound card
cat /proc/asound/cards

# Speaker
speaker-test -c 1 -t sine -l 1 -D plughw:0,0
# or named card once present:
# speaker-test -c 1 -t sine -l 1 -D plughw:wm8960soundcard

# Mic (2s) then playback
arecord -d 2 -f S16_LE -r 16000 /tmp/whis-test.wav
aplay /tmp/whis-test.wav

# Optional: LCD / LED / button demos under ~/Whisplay/example if present
```

**2.5 green:** screen lights, speaker tone heard, mics round-trip, button works.  
**Fail:** stop — do **not** install tunnel/systemd. Paste script output + verify failures to Jarvis.

## Fallback — only if primary 2.5 fails

Community Orange Pi path (turfptax prefers Armbian Noble upstream; adapt to Bookworm if staying on official image, or reflash Armbian only if Jarvis agrees):

```bash
git clone https://github.com/turfptax/orangepi-whisplay.git
cd orangepi-whisplay
sudo bash setup.sh
# Optional WM8960 for Orange Pi OS:
# https://github.com/MJD19994/WM8960_AudioHAT_OrangePiZero_Drivers
sudo reboot
```

Then re-run the same verify checklist.
