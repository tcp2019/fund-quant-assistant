#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

PIDS=()

cleanup() {
  trap - SIGINT SIGTERM
  echo ""
  echo "Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "Error: backend/.venv not found."
  echo "Run: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\""
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Error: frontend/node_modules not found."
  echo "Run: cd frontend && npm install"
  exit 1
fi

check_port() {
  local port="$1" name="$2"
  local pids
  pids="$(lsof -ti ":$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Error: port $port ($name) already in use."
    echo "  PIDs: $pids"
    echo "  Run: kill $pids"
    echo "  Or:  lsof -ti :$port | xargs kill"
    return 1
  fi
}

check_port 8000 "backend" || exit 1
check_port 5173 "frontend" || exit 1

echo "Starting backend (http://127.0.0.1:8000)..."
(
  cd "$BACKEND_DIR"
  # shellcheck source=/dev/null
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
PIDS+=($!)

echo "Starting frontend (http://localhost:5173)..."
(
  cd "$FRONTEND_DIR"
  exec npm run dev
) &
PIDS+=($!)

echo ""
echo "Fund Quant Assistant is running."
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://127.0.0.1:8000"
echo "  API docs: http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

wait || true
