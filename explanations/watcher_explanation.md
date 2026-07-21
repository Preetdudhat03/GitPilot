# Watcher Module (`gitpilot/watcher.py`)

## 1. Purpose of the file
This module is the "eyes" of GitPilot. It monitors the user's project directory continuously and detects when files are created, modified, deleted, or moved. 

Most importantly, it implements **debouncing**. We do not want GitPilot to create a commit every single time the user presses `Ctrl+S` (which could result in dozens of tiny, useless commits per minute). Instead, we wait for a period of *inactivity* (e.g., 120 seconds).

## 2. Imports explained
```python
import time
import logging
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
```
- **`threading.Timer`**: A utility that waits a specified number of seconds and then runs a function in the background.
- **`watchdog.observers.Observer`**: The third-party engine that talks directly to the Operating System (Windows, macOS, Linux) to receive highly efficient filesystem notifications without polling.
- **`watchdog.events.FileSystemEventHandler`**: The base class we must inherit from to tell Watchdog what to do when it sees an event.

## 3. Classes explained

### `GitEventHandler`
**Purpose**: Responds to events (like "file modified") from Watchdog.
- Inherits from `FileSystemEventHandler`.
- **`IGNORE_PATHS`**: A `set` of folders and files that should be completely ignored. If `.git/index` is modified, we ignore it to prevent an infinite loop (where our own commit triggers another commit!).

### `GitPilotWatcher`
**Purpose**: A simple manager that binds the `Observer` to the `GitEventHandler` and provides `start()` and `stop()` methods for the CLI to use.

## 4. Important lines explained line-by-line

```python
def _is_ignored(self, path_str: str) -> bool:
    rel_path = Path(path_str).relative_to(self.repo_path)
```
- Converts the absolute path triggered by Watchdog into a relative path from the repository root.
- E.g., `C:/project/node_modules/file.js` becomes `node_modules/file.js`.

```python
for part in rel_path.parts:
    if part in self.IGNORE_PATHS:
        return True
```
- `rel_path.parts` splits the path into pieces: `('node_modules', 'file.js')`.
- We loop through the parts. Because `node_modules` is in our `IGNORE_PATHS` set, this returns `True` immediately, skipping the event.

```python
def _reset_timer(self):
    with self._lock:
        if self.timer:
            self.timer.cancel()
```
- **Concurrency Safety**: Because Watchdog runs on background threads, multiple file events can happen at the exact same millisecond. 
- `with self._lock:` guarantees that only one thread can modify the timer at a time.
- If a timer is already counting down (because the user saved a file 10 seconds ago), we `cancel()` it.

```python
        self.timer = threading.Timer(self.config.delay, self._trigger_pipeline)
        self.timer.daemon = True
        self.timer.start()
```
- We create a *new* timer set to the configured delay (e.g., 120 seconds). 
- `self._trigger_pipeline` is the function that will run when the timer reaches zero.
- `daemon = True` means this timer thread will automatically die if the main program exits. This prevents the program from hanging in the terminal if the user presses `Ctrl+C`.

## 5. Data Flow & Execution
1. User types `gitpilot watch`.
2. `GitPilotWatcher.start()` is called. The `Observer` starts monitoring in the background.
3. User edits and saves a file.
4. OS notifies Watchdog -> Watchdog calls `handler.on_modified()`.
5. Handler checks if the file is ignored. It isn't.
6. Handler calls `_reset_timer()`. A 120s countdown starts.
7. User saves another file 30 seconds later.
8. Steps 4-5 repeat. `_reset_timer()` cancels the old timer and starts a brand new 120s countdown.
9. User stops typing. 120 seconds pass.
10. Timer reaches zero and calls `_trigger_pipeline()`.
11. `_trigger_pipeline()` calls `pipeline.run()`, kicking off the Git and Safety operations safely.
