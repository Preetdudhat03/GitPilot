# Safety Scanner Module (`gitpilot/safety.py`)

## 1. Purpose of the file
This module is the "gatekeeper" of GitPilot. Because GitPilot automates Git commits, a tiny mistake by the developer (like accidentally saving an `.env` file) could be pushed to GitHub instantly, exposing secrets to the world.

The `SafetyScanner` runs at two distinct phases in the pipeline:
1. **Pre-stage**: Before `git add` is even run, it looks at filenames and file sizes. This is incredibly fast and prevents Git from choking on huge files or indexing known secret files.
2. **Post-stage**: After `git add` is run, but before `git commit`, it looks at the actual lines of code being added (the staged diff). It uses Regular Expressions to look for patterns that look like API keys or passwords.

## 2. Imports explained
```python
import os
import re
import logging
from pathlib import Path
from typing import List, Tuple
from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager
```
- **`import re`**: Python's Regular Expression engine. Used for advanced pattern matching to find secrets inside code.
- **`GitPilotConfig` & `GitManager`**: The scanner needs the config (to know the max file size) and the git manager (to ask Git for the current diff). We pass these in via Dependency Injection.

## 3. Classes explained

### `SafetyScanner`
**Purpose**: Contains all logic for verifying if a repository state and a set of changes are safe to commit.

**Important Instance Variables**:
- `SENSITIVE_FILENAMES` & `SENSITIVE_EXTENSIONS`: Python `set`s containing hardcoded lists of filenames that should never be committed. Using sets is extremely fast for lookups (`O(1)` time complexity).
- `SECRET_PATTERNS`: A list of tuples. The first item in the tuple is the Regular Expression (Regex). The second is a human-readable name of what the Regex detects.

## 4. Functions & Important lines explained line-by-line

### `check_repo_state(self)`
Checks if the fundamental Git environment is sane.
If `is_detached_head()` or `has_merge_conflicts()` is true, it logs an error and returns `False`. The Pipeline will see `False` and immediately abort the automatic commit.

### `pre_stage_scan(self, files: List[str])`
Scans files before staging.
```python
max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
```
- Converts the MB config value to bytes.

```python
if file_name in self.SENSITIVE_FILENAMES or full_path.suffix in self.SENSITIVE_EXTENSIONS:
```
- Checks if the exact filename (like `.env`) is in our forbidden set.
- Checks if the file extension (like `.pem`) is forbidden using `pathlib.Path.suffix`.

```python
if full_path.is_file():
    file_size = full_path.stat().st_size
```
- Uses `pathlib` to safely get file statistics (`stat()`) and checks the `st_size` (size in bytes).

### `post_stage_scan(self)`
Scans the actual code being added.
```python
diff_content = self.git.get_staged_diff()
```
- Grabs the raw text of the diff.

```python
if line.startswith("+") and not line.startswith("+++"):
```
- A Git diff prefixes added lines with `+` and deleted lines with `-`.
- We ONLY care about added lines. If a user is deleting a secret (`-`), we *want* them to commit that change!
- We skip `+++` because that represents the header of the diff block.

```python
for pattern, secret_type in self.SECRET_PATTERNS:
    if re.search(pattern, line):
        logger.error(f"Safety Violation: Possible {secret_type} detected in '{current_file}'")
```
- For every added line of code, we test all our Regex patterns.
- If we find a match, we log the `secret_type` (e.g., "AWS Access Key ID") but we **never** log the actual `line` variable, because that would print the secret to the developer's terminal log, defeating the point of safety!

## 5. Error-handling behavior
The module does not raise exceptions. It returns a simple boolean (`True` for safe, `False` for unsafe). It logs the exact reason it failed using the global logger. It's the responsibility of the calling Pipeline to respect the boolean and halt execution.
