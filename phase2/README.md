# Desk Atlas — Phase 2 software kit

**Status:** ready for hardware landing. Hermes owns artifacts here. Ethan owns flash / physical / first Wi-Fi / WhisPlay install run / key-on-Pi.

| Artifact | Path |
| --- | --- |
| Exact Bookworm image URLs | `IMAGE.md` |
| Flash + default login checklist | `FLASH-CHECKLIST.md` (**first deliverable**) |
| WhisPlay install + verify (2.5) | `WHISPLAY-VERIFY.md` |
| Secret/key handoff (no values) | `KEY-HANDOFF.md` |
| Speak package + install script | `package/` |
| Named tunnel template | `cloudflared/config.named.example.yml` |
| systemd speak+tunnel | `systemd-HOLD-UNTIL-2.5/` (**enable only after 2.5 green**) |

## Split of labor

**Hermes:** image pin, docs, speak package, tunnel/systemd templates, key process notes.  
**Ethan:** flash SD, header/HAT, first power, home Wi-Fi, run install, verify, put xAI key on Pi, guest Wi-Fi last.  
**Atlas:** PM, 2.5 green gate for systemd enable, mouth smoke after tunnel. No Hermes→Ethan ping until Atlas says.

## Install lock (2.5)

1. **Primary:** Orange Pi Debian Bookworm + `sudo bash script/install_orangepi_zero2w.sh` from https://github.com/PiSugar/Whisplay  
2. **Fallback if 2.5 fails:** turfptax / Armbian community path (see `WHISPLAY-VERIFY.md`)
