# GitPilot Data Flow

This document provides a high-level overview of how data moves through GitPilot. It's the perfect place to start if you want to understand the architecture before diving into individual files.

## High-Level Architecture
GitPilot uses a strictly modular architecture. 
- **CLI (`cli.py`)**: Parses what the user wants to do.
- **Config (`config.py`)**: Stores user preferences.
- **GitManager (`git_manager.py`)**: Executes raw Git commands.
- **SafetyScanner (`safety.py`)**: Enforces rules to protect the repository.
- **CommitMessageGenerator (`commit_generator.py`)**: Creates readable commit messages.
- **Watcher (`watcher.py`)**: Monitors the file system for changes.
- **Pipeline (`pipeline.py`)**: The conductor that orchestrates all the other components into a safe, repeatable workflow.

## Execution Flow: `gitpilot watch`

Here is exactly what happens when you type `gitpilot watch` in your terminal:

1. **CLI Layer (`cli.py`)**
   - Parses the `watch` argument.
   - Loads the configuration (`config.py`).
   - Checks if the current folder is actually a Git repository (`git_manager.py`).
   - Creates a `GitPilotWatcher` and calls `.start()`.

2. **File Watching Layer (`watcher.py`)**
   - The background `watchdog` Observer monitors for changes.
   - When you press `Ctrl+S` (save) on a file, Watchdog triggers `on_modified()`.
   - The watcher checks if the file is ignored (e.g., inside `.git/` or `node_modules/`).
   - If it's a valid change, the watcher starts a `threading.Timer` (e.g., 120 seconds).
   - If you save *another* file 10 seconds later, the watcher **cancels** the old timer and starts a new one. This is called **debouncing**.
   - When the timer finally hits zero, it triggers the `Pipeline`.

3. **Workflow Layer (`pipeline.py`)**
   - The Pipeline acquires a lock to prevent concurrency bugs.
   - **Step 1: Check state**: Asks `SafetyScanner` if the repository is in a healthy state (e.g., not mid-merge, not detached HEAD).
   - **Step 2: Get changes**: Asks `GitManager` for a list of modified/untracked files.
   - **Step 3: Pre-stage scan**: Passes those files to `SafetyScanner.pre_stage_scan()`. The scanner checks if you accidentally added a `.env` file or a massive 1GB video. If it fails, the pipeline aborts.
   - **Step 4: Stage**: If safe, tells `GitManager` to run `git add -A`.
   - **Step 5: Post-stage scan**: Now that files are staged, tells `SafetyScanner.post_stage_scan()` to read the raw Git diff. The scanner looks for Regex patterns matching AWS keys, Stripe tokens, etc.
   - **Step 6: Unstage (if unsafe)**: If a secret is found, the Pipeline immediately tells `GitManager` to run `git restore --staged` on the files. This protects the repository without deleting your local work. The pipeline aborts.
   - **Step 7: Generate message**: If safe, passes the diff to `CommitMessageGenerator`. The generator creates a message like `feat: update watcher.py`.
   - **Step 8: Commit**: Tells `GitManager` to run `git commit -m "..."`.
   - **Step 9: Push**: If `auto_push` is enabled, tells `GitManager` to push. If the push fails (e.g., no internet), the Pipeline catches the error, logs it, and moves on (the local commit remains safe).

4. **Back to Watcher**
   - The Pipeline releases the lock.
   - The Watcher continues waiting for the next file modification.

## Execution Flow: `gitpilot commit`

When you type `gitpilot commit`, the flow is nearly identical, except:
1. `cli.py` does not start the `Watcher`.
2. It simply calls `pipeline.run()` immediately.
3. The exact same safety checks, staging, and generation rules are applied!
