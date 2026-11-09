#!/bin/bash
# Pulls the newest Car Atlas code from GitHub. Runs at boot and every 30 min (car-atlas-update.timer).
# Never touches the dashcam drive while the car might be recording.
set -u
SRC_ROOT=/opt/car-atlas/src
set -a
# shellcheck disable=SC1091
. "$SRC_ROOT/car/config.default.env"
# shellcheck disable=SC1091
[ -f /etc/car-atlas/config.env ] && . /etc/car-atlas/config.env
set +a
BRANCH="${REPO_BRANCH:-car}"
cd "$SRC_ROOT" || exit 1

before=$(git rev-parse HEAD)
if ! timeout 300 git fetch --depth 1 origin "$BRANCH" 2>&1; then
  echo "[update] no internet or GitHub unreachable; will try again later"
  exit 0
fi
after=$(git rev-parse FETCH_HEAD)
if [ "$before" = "$after" ]; then
  echo "[update] already up to date (${before:0:7})"
  exit 0
fi
git reset --hard FETCH_HEAD >/dev/null
echo "[update] updated ${before:0:7} -> ${after:0:7}"
exec "$SRC_ROOT/car/scripts/post-update.sh" "$before"
