#!/usr/bin/env bash
set -euo pipefail

# Bootstrap: create venv with uv, install deps, scaffold folders
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
cd "$PROJECT_ROOT"

echo "🔧 Bootstrapping LSM Tree project with uv..."

# Create venv with uv
if command -v uv &> /dev/null; then
  echo "📦 Creating virtual environment with uv..."
  uv venv
  source .venv/bin/activate
  
  echo "📦 Installing dependencies..."
  uv pip install -e ".[dev,agent]"
else
  echo "⚠️  uv not found, falling back to standard venv"
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -e ".[dev,agent]"
fi

# Create expected directories
echo "📁 Creating directory structure..."
mkdir -p src/lsm_tree/components src/lsm_tree/interfaces src/lsm_tree/core
mkdir -p tests
mkdir -p ai/logs ai/prompts tools/config .warp/workflows docs/build

# Seed placeholders if missing
[ -f src/lsm_tree/__init__.py ] || echo "__all__ = []" > src/lsm_tree/__init__.py
[ -f tests/test_smoke.py ] || cat > tests/test_smoke.py <<'PY'
import importlib

def test_import_package():
    pkg = importlib.import_module("lsm_tree")
    assert pkg is not None
PY

chmod +x tools/scripts/*.sh ai/run_agent.sh 2>/dev/null || true

echo "✅ Bootstrap complete!"
echo "💡 Activate venv: source .venv/bin/activate"
echo "🚀 Next: Run 'bash ai/run_agent.sh' or 'bash tools/scripts/run_tests.sh'"
