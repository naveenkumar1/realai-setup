#!/bin/bash
# Start the Monthly Analysis Report API
# Usage: ./start_api.sh [port]   (default port: 8000)

set -e

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
pyenv activate realsi

PORT=${1:-8000}
cd "$(dirname "$0")"

echo "Starting API on http://0.0.0.0:$PORT"
echo "Docs at http://localhost:$PORT/docs"
echo ""

uvicorn api.main:app --host 0.0.0.0 --port "$PORT" --reload
