#!/bin/bash
set -euo pipefail

sudo chown -R vscode:vscode /home/vscode
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
  sudo -H -u vscode bash -lc "cd '$workdir' && $cmd" > "$logfile" 2>&1 || {
    echo "[startup] $name failed, see $logfile"
    return 1
  }
  echo "[startup] $name ok"
}

start_ssh

if [ -d backend ]; then
  # 环境密钥兜底：backend/.env.dev 是派生文件，缺失/被删时自动重渲染（幂等，
  # .devcontainer/.env 为真相源、只补缺绝不覆盖）。
  # 注意：它兜不了 .devcontainer/.env 本身丢失——compose 的 ${VAR:?} 校验发生在
  # 容器创建之前，那时容器没起来、本脚本没机会执行。该场景需在 WSL 仓库根目录
  # 手动跑一次：python3 scripts/ensure_env.py --env dev
  run_step ensure_env backend "python3 scripts/ensure_env.py --env dev" \
    || echo "[startup] ensure_env failed (non-fatal, see log)"
  run_step uv_sync backend "uv sync"
fi

if [ -d frontend ]; then
  if [ -f frontend/package.json ]; then
    run_step npm_install frontend "npm install"
  fi
fi

echo "[startup] ready"
sleep infinity
