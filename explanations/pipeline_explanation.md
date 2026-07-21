# Pipeline Module (`gitpilot/pipeline.py`)

## 1. Purpose of the file
This module is the "conductor" or "orchestrator" of the application. The user explicitly requested that the CLI layer (parsing commands) should be separate from the workflow layer (doing the work).

By putting the entire commit workflow into `GitPilotPipeline`, we ensure that both `gitpilot watch` (automatic) and `gitpilot commit` (manual) use the *exact same* sequence of safety checks and Git commands. 

## 2. Imports explained
```python
import threading
from typing import Optional
```
- **`import threading`**: Used to import `Lock`. A Lock ensures that if two things try to run the pipeline at the exact same time, one of them will be blocked.
- **`Optional`**: A type hint meaning a variable can be a specific type (like `bool`) OR it can be `None`.

## 3. Classes explained

### `GitPilotPipeline`
**Purpose**: Executes the step-by-step workflow of safely committing code.

**Constructor (`__init__`)**:
It takes all its dependencies (config, git, safety, generator) as arguments. This is a design pattern called **Dependency Injection**. It makes the `GitPilotPipeline` incredibly easy to test, because we can pass in "mock" (fake) versions of Git and Safety during testing to simulate different scenarios without ever actually touching the hard drive.

## 4. Important lines explained line-by-line

### `run()` Method
```python
if not self._lock.acquire(blocking=False):
    logger.warning("Pipeline is already running. Skipping this trigger.")
    return False
```
- **Concurrency Safety**: This is how we fulfill the requirement: *"If GitPilot is committing or pushing, and another file changes, GitPilot must NOT start a second Git operation simultaneously."*
- `acquire(blocking=False)` means: "Try to grab the lock. If someone else already has it, don't wait for them (`blocking=False`), just return `False` immediately."
- If it grabs the lock, it proceeds to the `try/finally` block.

```python
try:
    return self._run_internal(dry_run, manual_push)
finally:
    self._lock.release()
```
- `finally`: No matter what happens inside `_run_internal`—even if Python crashes with a massive error—the `finally` block is guaranteed to run. This ensures we always release the lock so the application doesn't freeze forever.

### `_run_internal()` Method
This is the literal step-by-step implementation of the user's requested data flow.

```python
if dry_run:
    # ...
    return True
```
- **Dry-run**: If the user ran `gitpilot watch --dry-run`, we stop right before `git.stage_all()`. We print out what *would* have happened, and return `True` (success).

```python
if not self.safety.post_stage_scan():
    self.git.unstage_files(staged_files)
    return False
```
- **Post-stage Safety**: If the safety scanner finds an AWS key in the diff, we IMMEDIATELY call `git.unstage_files()`. This uses `git restore --staged` to remove the file from Git's index, but leaves the file exactly as it was in the user's folder. We never delete user changes.

```python
try:
    self.git.push(remote, branch)
except GitError as e:
    logger.error(f"Push failed: {e}\nYour local commit was successful and remains intact.")
```
- **Push Failure Behavior**: If `git push` fails (e.g., no internet, or remote is ahead), `git_manager` raises a `GitError`. We catch it here. 
- Notice that we DO NOT `return False` or throw an error. The local commit was already created successfully! We just log the failure and let the program continue.

## 5. Execution Flow
1. Check if we already hold the lock.
2. `safety.check_repo_state()`
3. `git.get_changed_files()`
4. `safety.pre_stage_scan(files)`
5. `git.stage_all()`
6. `safety.post_stage_scan()` (unstage and abort if failed)
7. `generator.generate()`
8. `git.commit()`
9. `git.push()` (if configured or requested)
