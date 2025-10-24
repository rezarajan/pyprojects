#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
cd "$PROJECT_ROOT"

if [ -d .venv ]; then 
  source .venv/bin/activate
fi

echo "🧪 Running tests..."
pytest -v
