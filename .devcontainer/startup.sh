#!/bin/bash
set -euo pipefail

LOGDIR="$LOCAL_WORKSPACE_FOLDER/.devcontainer/logs"
mkdir -p "$LOGDIR"
cd "$LOCAL_WORKSPACE_FOLDER"

echo "[startup] running in $LOCAL_WORKSPACE_FOLDER"

run_step() {
  local name="$1"; shift
  local workdir="$1"; shift
  local cmd="$*"
  local logfile="$LOGDIR/${name}.log"
  echo "[startup] $name -> $logfile"
  (cd "$workdir" && bash -lc "$cmd") > "$logfile" 2>&1 || {
    echo "[startup] $name failed, see $logfile"
    return 1
  }
  echo "[startup] $name ok"
}

if [ -d backend ]; then
  run_step uv_sync backend "uv sync"
fi

if [ -d frontend ]; then
  if [ -f frontend/package.json ]; then
    run_step npm_install frontend "npm install"
  fi
fi

echo "[startup] ready"
sleep infinity
