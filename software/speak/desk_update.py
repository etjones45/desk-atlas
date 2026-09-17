# Desk Atlas desk_update (face/listen handoff)

Canonical sources for Octavian / Hermes (**full Python is on the box**, not this stub):

- `/workspace/desk-atlas/pi-update-deploy/desk_update.py`
- `/workspace/desk-atlas/pi-update-deploy/speak_server.py`
- `/workspace/desk-atlas/pi-update-deploy/ears.py`
- `/workspace/desk-atlas/pi-update-deploy/deploy-via-mac.sh`
- `/workspace/desk-atlas/pi-update-deploy/README.md`

CopyFromBox → Mac `~/Documents/desk-atlas-pi-update/`, then:
`SRC_DIR=~/Documents/desk-atlas-pi-update bash deploy-via-mac.sh`
(Mac Shell machineId `060a321a-71ef-4a39-8be6-0ef9647aba28`).

Sync protection in the real file: refuses CLI-only `software/ears/ears.py` overwrite of live listen ears (upstream must contain `--listen`).
