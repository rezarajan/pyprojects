#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
cd "$PROJECT_ROOT"

if [ -d .venv ]; then 
  source .venv/bin/activate
fi

echo "🧪 Running LSM Tree tests..."

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

PYTEST_ARGS=""
if [[ "$VERBOSE" == "-v" || "$VERBOSE" == "--verbose" ]]; then
    PYTEST_ARGS="-v"
fi

case "$TEST_TYPE" in
    "unit")
        echo "📋 Running unit tests only..."
        pytest $PYTEST_ARGS tests/unit/
        ;;
    "integration")
        echo "🔗 Running integration tests only..."
        pytest $PYTEST_ARGS tests/integration/
        ;;
    "performance")
        echo "⚡ Running performance tests only..."
        pytest $PYTEST_ARGS tests/performance/ -s
        ;;
    "fast")
        echo "🚀 Running fast tests (unit + integration)..."
        pytest $PYTEST_ARGS tests/unit/ tests/integration/
        ;;
    "all")
        echo "🎯 Running all tests..."
        pytest $PYTEST_ARGS tests/
        ;;
    *)
        echo "Usage: $0 [unit|integration|performance|fast|all] [-v|--verbose]"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  performance - Run performance tests only"
        echo "  fast        - Run unit + integration tests"
        echo "  all         - Run all tests (default)"
        exit 1
        ;;
esac

echo "✅ Tests completed!"
