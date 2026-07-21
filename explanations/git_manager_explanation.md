# Git Manager Module (`gitpilot/git_manager.py`)

## 1. Purpose of the file
The `git_manager.py` file is responsible for all interactions with Git. Instead of scattering `subprocess.run(["git", ...])` commands all over the application, we centralize them here. This provides a safe, object-oriented API for the rest of GitPilot to use. 

By having a dedicated `GitManager` class, we can carefully control *how* Git commands are executed, handle errors gracefully, and enforce safety rules (like never allowing a force push).

## 2. Imports explained
```python
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import logging
```
- **`import subprocess`**: Python's standard library for spawning new processes, connecting to their input/output/error pipes, and obtaining their return codes. We use this to execute Git commands on the terminal exactly as a human would.
- **`typing` (`List`, `Tuple`, `Optional`)**: Used for Type Hinting. `List[str]` means "A list of strings". `Optional[str]` means "This might be a string, or it might be `None`".
- **`logging`**: Used to log warnings if a Git command fails unexpectedly.

## 3. Classes explained

### `GitError`
```python
class GitError(Exception):
    pass
```
**Purpose**: A custom exception class. 
**Why?**: If `subprocess` throws a `CalledProcessError` (which happens when a command fails), it's a very generic error. By catching it and raising our own `GitError`, we signal to the rest of the application "Something specifically related to Git failed". It makes error handling higher up in the application much cleaner.

### `GitManager`
**Purpose**: Wraps the Git command-line interface.
- **Constructor (`__init__`)**: Takes the `repo_path` (a `Path` object) so it knows *where* to run the Git commands.

## 4. Functions & Important lines explained line-by-line

### `_run_git(self, *args, check=True)`
This is the core helper method. The underscore (`_`) at the start of the name is a Python convention meaning "this is an internal, private method meant only to be used inside this class".

```python
cmd = ["git"] + list(args)
```
- If someone calls `self._run_git("status", "--porcelain")`, `args` is a tuple `("status", "--porcelain")`. This line combines `"git"` and the arguments into a single list: `["git", "status", "--porcelain"]`.

```python
result = subprocess.run(
    cmd,
    cwd=str(self.repo_path),
    capture_output=True,
    text=True,
    check=check
)
```
- `subprocess.run()`: Executes the command.
- `cwd=str(...)`: "Current Working Directory". Tells Python to run the command inside the repository folder, not wherever the GitPilot script happens to be running from.
- `capture_output=True`: Grabs the standard output (stdout) and error output (stderr) so we can read it in Python instead of it just printing to the terminal.
- `text=True`: Returns strings instead of raw binary bytes.
- `check=check`: If `True`, Python will automatically raise a `CalledProcessError` if Git returns a non-zero exit code (meaning Git failed).

### `get_changed_files(self)`
**Purpose**: Asks Git what files have changed. We use `git status --porcelain` because its output is designed for machines to parse, unlike standard `git status` which changes based on user configuration or Git version.

```python
for line in status.splitlines():
    ...
    filename = line[3:].strip()
```
- `--porcelain` outputs lines like ` M myfile.py` or `?? newfile.py`. The first two characters are the status code, the third is a space, and the filename starts at index 3.
- `.strip()` removes any accidental whitespace.

### `unstage_files(self, files: List[str])`
**Purpose**: If the Safety module detects a secret in a file we just staged, we need to unstage it safely WITHOUT DELETING the user's work!

```python
self._run_git("restore", "--staged", "--", file)
```
- `git restore --staged <file>` is the modern, safe way to pull a file out of the staging area (index) while leaving the working directory completely untouched.
- `--`: The double dash is a standard command-line convention that means "stop parsing flags here, everything after this is a file path". This prevents bugs if a user accidentally names a file `--force`.
- **Fallback**: Older versions of Git (pre 2.23) don't have `restore`. If it fails, we catch the `GitError` and try `git rm --cached -- <file>`, which accomplishes the same thing.

### `is_remote_ahead(self, remote, branch)`
**Purpose**: Safety check before pushing. If the remote GitHub server has commits that the local machine doesn't have, a standard push will fail. 

```python
self._run_git("fetch", remote, branch)
behind = self._run_git("rev-list", "--count", f"HEAD..{remote}/{branch}")
```
- First, we `fetch`. This downloads metadata from the remote server but DOES NOT merge it (unlike `pull`), making it perfectly safe.
- `rev-list --count HEAD..origin/main`: This Git command literally means "Count how many commits exist on `origin/main` that do NOT exist in my current `HEAD`". If it's greater than 0, we know the remote is ahead and we should abort the push.

## 5. Data Flow & Communication
- The `Pipeline` module will call `get_changed_files()` to see if work needs to be done.
- If so, it will call `stage_files()`.
- The `Safety` module might then ask `GitManager` to `unstage_files()` if it finds a secret.
- Finally, the `Pipeline` calls `commit()` and `push()`.

## 6. Error-handling behavior
If Git isn't installed, `FileNotFoundError` is caught and a clear `GitError` is raised.
If a command fails (e.g., trying to push without internet), a `GitError` is raised containing Git's actual error message (`stderr`). This prevents ugly stack traces from crashing the app and allows the `Pipeline` to catch the `GitError` and print a nice, friendly message to the user.
