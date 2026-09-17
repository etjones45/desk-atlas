# Desk Atlas Pi git-sync

`~/desk-atlas` is the live package and is never replaced by a clone. The upstream clone lives at `~/desk-atlas-upstream`; updates are pulled there and copied only through the approved map.

The sync path preserves `.env`, virtual environments, and live ears. CLI-only `software/ears/ears.py` is refused when it lacks `--listen`.
