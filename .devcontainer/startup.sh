#!/bin/bash
set -euo pipefail

LOGDIR="$LOCAL_WORKSPACE_FOLDER/.devcontainer/logs"
mkdir -p "$LOGDIR"
cd "$LOCAL_WORKSPACE_FOLDER"

echo "[startup] running in $LOCAL_WORKSPACE_FOLDER"

start_ssh() {
    echo "[startup] starting SSH server..."
    
    sudo mkdir -p /var/run/sshd
    
    if pgrep -x "sshd" > /dev/null; then
        echo "[startup] SSH server already running, skipping"
        return 0
    fi
    
    sudo rm -f /var/run/sshd.pid
    
    sudo /usr/sbin/sshd
    
    sleep 0.5
    if pgrep -x "sshd" > /dev/null; then
        echo "[startup] SSH server ready on port 22 (host port 2222)"
    else
        echo "[startup] WARNING: SSH server failed to start"
        return 1
    fi
}


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

start_ssh

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
