# Phase 2 — Exact OS image (locked)

**Board:** Orange Pi Zero 2W **2GB**  
**OS:** Official **Orange Pi Debian 12 Bookworm server** (linux6.1) — **not Armbian**, not desktop XFCE, not 4GB-suffixed builds.

WhisPlay path on this project expects official Orange Pi Bookworm (Atlas 2026-09-05).

## Exact file to flash (1GB/2GB boards)

| Field | Value |
| --- | --- |
| Filename | `Orangepizero2w_1.0.0_debian_bookworm_server_linux6.1.31.7z` |
| RAM folder | **1GB_2GB** (do **not** use `*-4gb.7z`) |
| Variant | **server** (CLI) — not `desktop_xfce` |
| Kernel | linux**6.1**.31 |

## Official download URLs

1. **Debian images parent (EN support page):**  
   https://drive.google.com/drive/folders/1EH8mMQbgh4IgtOWKgg4nmRuZ57Gvfp9X?usp=sharing  
   (also linked from http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-Zero-2W.html → **Debian Image**)

2. **1GB/2GB memory folder (pick the Bookworm server .7z here):**  
   https://drive.google.com/drive/folders/1Lnosr3bmdbG6F9RsDjY_RCLJl2zT4l61  
   File: `Orangepizero2w_1.0.0_debian_bookworm_server_linux6.1.31.7z` (~480 MB compressed)

3. **CN Baidu (Debian 镜像, extract code `n88g`):**  
   https://pan.baidu.com/s/1T2DZzZxJpR2w5DVJXIxhqg?pwd=n88g

## Direct HTTP fallback (same family, newer patch 1.0.4 — verified 200)

If Google Drive is painful, this community mirror of orangepi-build Bookworm server is a known-good alternate:

https://github.com/silver-alx/sbc/releases/download/next/Orangepizero2w_1.0.4_debian_bookworm_server_linux6.1.31.7z

Prefer official Drive `1.0.0` when reachable; `1.0.4` is acceptable if Atlas/Ethan agree.

## After download

```bash
7z x Orangepizero2w_*_debian_bookworm_server_linux6.1*.7z
sha256sum -c *.sha   # if .sha present
# Flash the .img with balenaEtcher (see FLASH-CHECKLIST.md)
```
