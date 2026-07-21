# CLI Module (`gitpilot/cli.py`)

## 1. Purpose of the file
This file is the **entry point** for GitPilot. When the user types `gitpilot` in their terminal, this is the code that runs. Its sole responsibility is to translate terminal commands (`watch`, `commit`, `init`) into actions performed by the underlying classes (`Pipeline`, `Watcher`, `GitManager`).

By keeping this file focused entirely on *command parsing* and *component wiring*, we ensure that our core business logic remains clean, testable, and completely independent of how the user ran the command.

## 2. Imports explained
```python
import argparse
import sys
import time
```
- **`argparse`**: The standard Python library for building command-line interfaces. It automatically generates help messages (`--help`) and handles missing or invalid arguments gracefully.
- **`sys`**: Used here primarily for `sys.exit(1)`, which tells the operating system "this program crashed or failed". An exit code of `0` means success, anything else means failure.
- **`time`**: Used in the `watch` command to pause the main thread in a loop so the program doesn't exit immediately while the background Watchdog observer runs.

## 3. Important lines explained line-by-line

### Argument Parsing (`main()`)
```python
parser = argparse.ArgumentParser(description="GitPilot: A safe automated git commit watcher.")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose/debug output")
```
- `ArgumentParser` initializes the parser. 
- `action="store_true"` means if the user types `-v` or `--verbose`, the `args.verbose` variable becomes `True`. They don't need to type `--verbose=True`.

```python
subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)
watch_parser = subparsers.add_parser("watch", help="Start watching the repository for changes")
watch_parser.add_argument("--dry-run", action="store_true", help="Run without actually committing")
```
- **Subparsers** are how we create commands like `gitpilot watch` and `gitpilot init`. 
- `dest="command"` means whatever command the user types will be stored in `args.command`.
- We add the `--dry-run` argument ONLY to the `watch` command. It wouldn't make sense on `init`.

### Wiring it together (`get_pipeline()`)
```python
def get_pipeline(repo_path: Path, verbose: bool = False) -> GitPilotPipeline:
```
- This is a factory function. Because `watch` and `commit` both need a fully configured `GitPilotPipeline`, we centralize the creation logic here so we don't repeat `git = GitManager(...)`, `safety = SafetyScanner(...)` everywhere.

### The Watch Command (`cmd_watch()`)
```python
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("") # newline after ^C
    watcher.stop()
```
- `watcher.start()` spins up a new background thread that watches the file system.
- If we didn't have the `while True: time.sleep(1)` loop, Python would immediately reach the end of the file and exit, killing the background thread with it.
- We catch `KeyboardInterrupt` (which happens when the user hits `Ctrl+C` in their terminal) and safely call `watcher.stop()` to shut everything down cleanly instead of spewing a massive stack trace.

## 4. Error-handling behavior
At the bottom of `main()`, there is a global `try/except Exception as e:` block.
If *anything* goes catastrophically wrong that we didn't predict, this catches it.
If the user passed `--verbose`, we log the full stack trace (`exc_info=True`). If they didn't, we just print a clean message telling them to try with `--verbose`. This ensures the tool feels like a polished commercial application rather than a brittle script.
