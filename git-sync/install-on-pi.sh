#!/usr/bin/env bash
# Safe git-sync bootstrap for Desk Atlas Pi. Does NOT overwrite ~/desk-atlas.
set -euo pipefail
LIVE="${HOME}/desk-atlas"
UPSTREAM="${HOME}/desk-atlas-upstream"
REPO_URL="${DESK_ATLAS_REPO_URL:-https://github.com/etjones45/desk-atlas.git}"

if [[ ! -d "$LIVE" ]]; then
  echo "WARN: $LIVE missing — creating empty dir so layout stays clear; not cloning into it."
  mkdir -p "$LIVE"
fi

if ! command -v git >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y git
fi

if [[ -d "$UPSTREAM/.git" ]]; then
  echo "Upstream clone exists — fetching"
  git -C "$UPSTREAM" fetch --all --prune
  git -C "$UPSTREAM" pull --ff-only || git -C "$UPSTREAM" status
else
  if [[ -e "$UPSTREAM" ]]; then
    echo "ERROR: $UPSTREAM exists but is not a git repo. Move it aside first."
    exit 1
  fi
  echo "Cloning into $UPSTREAM (not $LIVE)"
  git clone "$REPO_URL" "$UPSTREAM"
fi

install -d "${HOME}/bin"
install -m 755 "$(dirname "$0")/pull-upstream.sh" "${HOME}/bin/desk-atlas-pull"
echo "OK: pull with ~/bin/desk-atlas-pull"
echo "Live package untouched at $LIVE"
