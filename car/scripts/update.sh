#!/bin/bash
# Pulls the newest Car Atlas code from GitHub. Runs at boot and every 30 min (car-atlas-update.timer),
# or right away from the app ("Check for updates"). Never touches the dashcam drive while the car might be recording.
set -u
SRC_ROOT=/opt/car-atlas/src
STATE=/var/lib/car-atlas/update.json
set -a
# shellcheck disable=SC1091
. "$SRC_ROOT/car/config.default.env"
# shellcheck disable=SC1091
[ -f /etc/car-atlas/config.env ] && . /etc/car-atlas/config.env
set +a
BRANCH="${REPO_BRANCH:-car}"
cd "$SRC_ROOT" || exit 1

exec 9>/run/car-atlas-update.lock
flock -n 9 || { echo "[update] already running"; exit 0; }

record() { # record <result> <from> <to>
  mkdir -p "$(dirname "$STATE")"
  printf '{"checked_at":%s,"result":"%s","from":"%s","to":"%s","branch":"%s"}\n' \
    "$(date +%s)" "$1" "$2" "$3" "$BRANCH" > "$STATE"
}
ver() { tr -d '[:space:]' < "$SRC_ROOT/car/VERSION" 2>/dev/null || echo unknown; }

before=$(git rev-parse HEAD)
before_v=$(ver)
if ! timeout 300 git fetch --depth 1 origin "$BRANCH" 2>&1; then
  echo "[update] no internet or GitHub unreachable; will try again later"
  record offline "$before_v" "$before_v"
  exit 0
fi
after=$(git rev-parse FETCH_HEAD)
if [ "$before" = "$after" ]; then
  echo "[update] already up to date (v$before_v, ${before:0:7})"
  record up-to-date "$before_v" "$before_v"
  exit 0
fi
git reset --hard FETCH_HEAD >/dev/null
after_v=$(ver)
echo "[update] updated v$before_v (${before:0:7}) -> v$after_v (${after:0:7})"
record updated "$before_v" "$after_v"
exec "$SRC_ROOT/car/scripts/post-update.sh" "$before"
