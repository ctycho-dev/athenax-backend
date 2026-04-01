#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RUN_MODE="${RUN_MODE:-prod}"
LOG_LEVEL="${LOG_LEVEL:-info}"

if [ -x ".venv/bin/python3.13" ]; then
	PYTHON_BIN=".venv/bin/python3.13"
elif [ -x ".venv/bin/python" ]; then
	PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
	PYTHON_BIN="$(command -v python)"
else
	echo "Python not found. Install Python or create .venv first." >&2
	exit 1
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
	echo "Running migrations..."
	"$PYTHON_BIN" -m alembic upgrade head
fi

if [ "$RUN_MODE" = "dev" ]; then
	exec "$PYTHON_BIN" -m uvicorn \
		app.main:app \
		--host "$HOST" \
		--port "$PORT" \
		--reload \
		--log-level "$LOG_LEVEL"
fi

exec "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --log-level "$LOG_LEVEL"
