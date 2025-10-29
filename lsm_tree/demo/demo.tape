Output demo.mp4

# Terminal setup
Set FontSize 42
Set Width 1280
Set Height 720
Set BorderRadius 10

# Title
# Setup
Hide
Type "uv run python"
Enter
Type "from lsm_tree.core.config import LSMConfig"
Enter
Type "from lsm_tree.core.store import SimpleLSMStore"
Enter
Type "cfg = LSMConfig(data_dir='/tmp/lsm_vhs_demo')"
Enter
Type "db = SimpleLSMStore(cfg)"
Enter
# Clear view
Ctrl+L
Show

# Put
Type "Put operation"
Sleep 1000ms
Backspace 13
Type "db.put(b'a', b'1')"
Sleep 500ms
Enter
Type "db.put(b'b', b'2')"
Enter
Sleep 1000ms
# Get
Type "We can get a value by key"
Sleep 1000ms
Backspace 25
Type "db.get(b'a')"
Sleep 250ms
Enter
Sleep 1500ms
Type "db.get(b'b')"
Sleep 250ms
Enter
Sleep 1500ms
Type "Both values returned"
Sleep 1000ms
Backspace 20
Sleep 1000ms


# Delete
Type "Delete operation"
Sleep 1000ms
Backspace 44
Type "db.delete(b'b')"
Sleep 1000ms
Enter
Type "Get should return None"
Sleep 1000ms
Backspace 22
Type "db.get(b'b')"
Sleep 1000ms
Enter
Type "Nothing returned..."
Sleep 1000ms
Backspace 19
Type "db.get(b'a')"
Sleep 1000ms
Enter
Sleep 1000ms
Type "But we can stil get 'a'"
Sleep 1000ms
Backspace 23
Sleep 1500ms

# Flush Memtable
Type "Flush Memtable"
Sleep 1000ms
Backspace 14
Type "print('L0 count (before):', len(db._catalog.list_level(0)))"
Sleep 1000ms
Enter
Sleep 1000ms
Type "db.flush_memtable()"
Sleep 1000ms
Enter
Sleep 1000ms
Type "print('L0 count (after):', len(db._catalog.list_level(0)))"
Sleep 1000ms
Enter
Sleep 1000ms
Ctrl+L
Sleep 500ms

Hide
Type "db.close()"
Enter
Type "exit()"
Enter
Show
Ctrl+L

# List resulting files for a quick peek
Type "Check Files Persisted on Disk"
Sleep 1000ms
Backspace 29
Type "WAL Files..."
Sleep 1000ms
Backspace 12
Type "ls -1 /tmp/lsm_vhs_demo/wal | sed 's/^/  /'"
Enter
Sleep 1500ms
Type "SSTable Files..."
Sleep 1000ms
Backspace 16
Type "ls -1 /tmp/lsm_vhs_demo/sst | sed 's/^/  /'"
Enter
Sleep 1500ms
Ctrl+L
