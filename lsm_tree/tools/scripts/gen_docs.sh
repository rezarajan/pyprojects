#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
cd "$PROJECT_ROOT"

if [ -d .venv ]; then 
  source .venv/bin/activate
fi

echo "📚 Generating documentation..."

# Build API docs if pdoc is available
if python -c "import pdoc" 2>/dev/null; then
  mkdir -p docs/build/api
  python -m pdoc -o docs/build/api src/lsm_tree || true
  echo "✅ API docs: docs/build/api/"
else
  echo "⚠️  pdoc not installed; skipping API doc generation"
fi

# Copy specs snapshot
mkdir -p docs/build/specs
cp -r docs/*.md docs/build/specs/ 2>/dev/null || true
echo "✅ Spec snapshot: docs/build/specs/"

echo "📚 Docs generated under docs/build/"
