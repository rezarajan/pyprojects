#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

if [ -d .venv ]; then 
  source .venv/bin/activate
fi

echo "🔍 LSM Tree Implementation Validation"
echo "====================================="

# Check dependencies
echo "📦 Checking dependencies..."
uv pip list | grep -E "(pytest|sortedcontainers|lsm-tree)" || {
    echo "❌ Missing dependencies. Installing..."
    uv pip install -e .
}

# Run linting/type checking if available
if command -v ruff &> /dev/null; then
    echo "🔧 Running linting..."
    ruff check src/ tests/ || echo "⚠️  Linting issues found"
fi

if command -v mypy &> /dev/null; then
    echo "🔍 Running type checking..."
    mypy src/ || echo "⚠️  Type checking issues found"
fi

# Test structure validation
echo "📁 Validating test structure..."
required_dirs=("tests/unit" "tests/integration" "tests/performance")
for dir in "${required_dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        echo "❌ Missing directory: $dir"
        exit 1
    fi
done

required_files=("tests/unit/test_wal.py" "tests/unit/test_memtable.py" "tests/unit/test_bloom.py" "tests/integration/test_lsm_integration.py")
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Missing test file: $file"
        exit 1
    fi
done

echo "✅ Test structure validated"

# Run tests in sequence
echo ""
echo "🧪 Running Test Suite"
echo "======================"

echo "1️⃣  Unit Tests..."
./tools/scripts/run_tests.sh unit || {
    echo "❌ Unit tests failed"
    exit 1
}

echo ""
echo "2️⃣  Integration Tests..."
./tools/scripts/run_tests.sh integration || {
    echo "❌ Integration tests failed"
    exit 1
}

echo ""
echo "3️⃣  Performance Tests (basic)..."
pytest tests/performance/ -k "not large_dataset" -v || {
    echo "❌ Performance tests failed"
    exit 1
}

# Component validation
echo ""
echo "🏗️  Component Validation"
echo "======================="

echo "🔧 Testing LSM Store API..."
python3 -c "
from lsm_tree import SimpleLSMStore, LSMConfig
import tempfile
import shutil

tmpdir = tempfile.mkdtemp()
try:
    config = LSMConfig(data_dir=tmpdir)
    with SimpleLSMStore(config) as store:
        # Basic operations
        store.put(b'test_key', b'test_value')
        result = store.get(b'test_key')
        assert result == b'test_value', f'Expected b\"test_value\", got {result}'
        
        # Delete
        store.delete(b'test_key')
        result = store.get(b'test_key')
        assert result is None, f'Expected None after delete, got {result}'
        
        # Range
        store.put(b'a', b'1')
        store.put(b'b', b'2')
        store.put(b'c', b'3')
        results = list(store.range(None, None))
        assert len(results) == 3, f'Expected 3 results, got {len(results)}'
        
        print('✅ LSM Store API validation passed')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
"

echo "💾 Testing WAL durability..."
python3 -c "
from lsm_tree.components.wal import SimpleWAL
import tempfile
import shutil

tmpdir = tempfile.mkdtemp()
try:
    wal_path = f'{tmpdir}/test.wal'
    
    # Write data
    wal1 = SimpleWAL(wal_path, flush_every_write=True)
    wal1.append(b'key1', b'value1', 1000)
    wal1.append(b'key2', None, 1001)  # tombstone
    wal1.close()
    
    # Read back
    wal2 = SimpleWAL(wal_path)
    records = list(wal2)
    wal2.close()
    
    expected = [(b'key1', b'value1', 1000), (b'key2', None, 1001)]
    assert records == expected, f'WAL records mismatch: {records} != {expected}'
    
    print('✅ WAL durability validation passed')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
"

echo "🗂️  Testing Memtable operations..."
python3 -c "
from lsm_tree.components.memtable import SimpleMemtable

memtable = SimpleMemtable()

# Test operations
memtable.put(b'key1', b'value1', 1000)
memtable.put(b'key2', b'value2', 1001)
memtable.delete(b'key1', 1002)

# Verify
result = memtable.get(b'key1')
assert result == (None, 1002), f'Expected tombstone, got {result}'

result = memtable.get(b'key2')
assert result == (b'value2', 1001), f'Expected value2, got {result}'

# Test ordering
items = list(memtable.items())
keys = [k for k, v, t in items]
assert keys == sorted(keys), f'Keys not sorted: {keys}'

print('✅ Memtable operations validation passed')
"

echo "🌸 Testing Bloom Filter accuracy..."
python3 -c "
from lsm_tree.components.bloom import SimpleBloomFilter

bf = SimpleBloomFilter(1000, 0.01)

# Add keys
test_keys = [f'key{i}'.encode() for i in range(100)]
for key in test_keys:
    bf.add(key)

# Test no false negatives
for key in test_keys:
    assert key in bf, f'False negative for {key}'

# Test serialization
serialized = bf.serialize()
bf2 = SimpleBloomFilter.deserialize(serialized)

for key in test_keys[:10]:  # Sample check
    assert (key in bf) == (key in bf2), f'Serialization mismatch for {key}'

print('✅ Bloom Filter accuracy validation passed')
"

# Acceptance criteria validation
echo ""
echo "📋 Acceptance Criteria Validation"
echo "================================="

echo "🔐 Testing crash recovery..."
python3 -c "
from lsm_tree import SimpleLSMStore, LSMConfig
import tempfile
import shutil

tmpdir = tempfile.mkdtemp()
try:
    config = LSMConfig(data_dir=tmpdir, wal_flush_every_write=True)
    
    # Write data and 'crash'
    store1 = SimpleLSMStore(config)
    store1.put(b'persistent_key', b'persistent_value')
    store1.close()  # Simulate restart
    
    # Recover
    store2 = SimpleLSMStore(config)
    result = store2.get(b'persistent_key')
    assert result == b'persistent_value', f'Recovery failed: {result}'
    store2.close()
    
    print('✅ Crash recovery validation passed')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
"

echo "⏰ Testing timestamp consistency..."
python3 -c "
from lsm_tree import SimpleLSMStore, LSMConfig
import tempfile
import shutil
import time

tmpdir = tempfile.mkdtemp()
try:
    config = LSMConfig(data_dir=tmpdir)
    store = SimpleLSMStore(config)
    
    # Multiple updates to same key
    store.put(b'conflict_key', b'value1')
    store.put(b'conflict_key', b'value2') 
    store.put(b'conflict_key', b'value3')
    
    result = store.get(b'conflict_key')
    assert result == b'value3', f'Timestamp ordering failed: {result}'
    
    store.close()
    
    print('✅ Timestamp consistency validation passed')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
"

echo "🗑️  Testing tombstone handling..."
python3 -c "
from lsm_tree import SimpleLSMStore, LSMConfig
import tempfile
import shutil

tmpdir = tempfile.mkdtemp()
try:
    config = LSMConfig(data_dir=tmpdir)
    store = SimpleLSMStore(config)
    
    # Put, delete, verify
    store.put(b'delete_me', b'will_be_deleted')
    assert store.get(b'delete_me') == b'will_be_deleted'
    
    store.delete(b'delete_me')
    assert store.get(b'delete_me') is None
    
    # Range should exclude deleted
    store.put(b'keep_me', b'keep_this')
    results = list(store.range(None, None))
    keys = [k for k, v in results]
    assert b'delete_me' not in keys, f'Deleted key in range: {keys}'
    assert b'keep_me' in keys, f'Valid key missing from range: {keys}'
    
    store.close()
    
    print('✅ Tombstone handling validation passed')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
"

# Performance check
echo ""
echo "⚡ Performance Validation"
echo "========================"

python3 -c "
from lsm_tree import SimpleLSMStore, LSMConfig
import tempfile
import shutil
import time

tmpdir = tempfile.mkdtemp()
try:
    config = LSMConfig(data_dir=tmpdir, wal_flush_every_write=False)
    store = SimpleLSMStore(config)
    
    # Write performance check
    num_writes = 1000
    start = time.time()
    
    for i in range(num_writes):
        store.put(f'perf_key_{i:04d}'.encode(), f'perf_value_{i}'.encode())
    
    store.flush_memtable()
    store._wal.sync()
    
    duration = time.time() - start
    writes_per_sec = num_writes / duration if duration > 0 else float('inf')
    
    print(f'📈 Write performance: {writes_per_sec:.0f} ops/sec')
    assert writes_per_sec > 100, f'Write performance too low: {writes_per_sec}'
    
    # Read performance check
    start = time.time()
    for i in range(0, num_writes, 10):  # Every 10th key
        key = f'perf_key_{i:04d}'.encode()
        result = store.get(key)
        assert result is not None
    
    duration = time.time() - start
    reads_per_sec = (num_writes // 10) / duration if duration > 0 else float('inf')
    
    print(f'📖 Read performance: {reads_per_sec:.0f} ops/sec')
    assert reads_per_sec > 50, f'Read performance too low: {reads_per_sec}'
    
    store.close()
    
    print('✅ Performance validation passed')
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
"

# Final summary
echo ""
echo "🎉 Implementation Validation Summary"
echo "===================================="
echo "✅ Test structure validated"
echo "✅ All unit tests passed"
echo "✅ All integration tests passed"
echo "✅ Performance tests passed"
echo "✅ Component APIs validated"
echo "✅ Acceptance criteria met"
echo "✅ Performance benchmarks passed"
echo ""
echo "🚀 LSM Tree implementation is ready for use!"
echo ""
echo "📊 Test Statistics:"
pytest tests/unit/ tests/integration/ --tb=no -q | grep -E "passed|failed|error" | tail -1