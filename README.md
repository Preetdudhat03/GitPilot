# GitPilot V1.2

GitPilot is a smart, developer-productivity CLI tool that automatically watches a Git repository for file changes, waits until you stop typing (debouncing), and then safely stages, commits, and pushes your changes. 

Version 1.2 introduces the **Environment Bootstrap & Recovery System** (`gitpilot setup`) and **Environment Diagnostics** (`gitpilot doctor`), designed for safe, idempotent installation across developer laptops, office workstations, and restricted college PCs.

---

## Features
- **Environment Bootstrap & Recovery (`gitpilot setup`)**: One-command automated environment setup, dependency resolution, package installation, and user-level PATH recovery.
- **Environment Doctor (`gitpilot doctor`)**: Read-only diagnostic inspector for Python, pip, Git, dependencies, virtual environments, PATH, and permissions.
- **Restricted PC & Module Execution (`python -m gitpilot <command>`)**: Full command support via Python module execution when PATH cannot be modified due to OS security policies.
- **Smart Debouncing**: Waits for a configurable period of inactivity before committing. Rapid saves group into one meaningful commit.
- **Intelligent Auto Sync**: Automatically fetches and synchronizes (`merge` or `rebase`) when the remote branch is ahead.
- **Limited / Read-Only Watcher Mode**: Pauses auto-commits when manual conflict resolution or `DETACHED_HEAD` is detected.
- **Safety Guarantees**: Operates strictly at Current User level. Never uses `git push --force` or attempts administrator elevation.

---

## Installation & Setup

### 1. Standard Setup
```bash
# Clone repository
git clone https://github.com/yourusername/GitPilot.git
cd GitPilot

# Run automated bootstrap setup
python -m gitpilot setup
```

### 2. Restricted / College PC Setup
On restricted computers where persistent PATH modification is blocked by system policy:
```bash
cd GitPilot
python -m gitpilot setup

# Safe Fallback: Execute via python module mode
python -m gitpilot watch
```

---

## Environment Diagnostics (`gitpilot doctor`)

Run read-only environment checks anytime without making system changes:
```bash
gitpilot doctor
# or
python -m gitpilot doctor
```

Example Doctor Output:
```
=== GitPilot Environment Doctor ===

Python:       [OK] 3.13.1 (C:\Python313\python.exe)
Virtualenv:   [NONE] User/System site mode
pip:          [OK] 26.1.1
Git:          [OK] 2.42.0 (C:\Program Files\Git\cmd\git.exe)
Context:      Source Tree
GitPilot:     [OK] 1.2.0
watchdog:     [OK] 6.0.0
Scripts Dir:  C:\Users\User\AppData\Roaming\Python\Python313\Scripts
CLI PATH:     [OK] Available in PATH
User PATH:    [OK] Configured in HKCU\Environment
Module Mode:  [OK] python -m gitpilot is working

GitPilot environment is healthy.
```


---

## Quick Start

```bash
cd my-project

# Initialize configuration
gitpilot init

# Configure Auto Sync (opt-in)
gitpilot config auto_sync true
gitpilot config sync_strategy merge  # or rebase

# Start watching with Automatic Initial Synchronization
gitpilot watch

# Manually synchronize anytime
gitpilot sync

# View developer dashboard
gitpilot status
```

---

## Global CLI Arguments

Available across all commands:

| Argument | Short Flag | Description |
| :--- | :--- | :--- |
| `--verbose` | `-v` | Enables detailed debug and traceback logging. |
| `--help` | `-h` | Displays the help reference and available options. |

---

## Comprehensive Command Reference

### 1. `gitpilot init`
Initializes a new `gitpilot.json` configuration file in the repository root with safe default settings.
- **Usage**: `gitpilot init`
- **Arguments**: None.

---

### 2. `gitpilot watch`
Starts the background file system watcher with Automatic Initial Synchronization.
- **Usage**: `gitpilot watch [--dry-run]`
- **Arguments**:
  - `--dry-run`: Simulates file watching and commit pipeline execution without making any Git commits or pushes. Useful for testing safety rules and commit message generation.

---

### 3. `gitpilot sync` *(New in V1.1)*
Manually triggers repository synchronization with the remote tracking branch using the configured strategy (`merge` or `rebase`). Does not create new commits.
- **Usage**: `gitpilot sync`
- **Arguments**: None.

---

### 4. `gitpilot commit`
Manually triggers the safe commit pipeline once for all uncommitted changes.
- **Usage**: `gitpilot commit [--push]`
- **Arguments**:
  - `--push`: Overrides `auto_push` configuration to push to remote immediately after successful commit creation.

---

### 5. `gitpilot push`
Manually pushes existing local commits to the configured remote branch.
- **Usage**: `gitpilot push`
- **Arguments**: None.

---

### 6. `gitpilot status`
Displays the rich developer status dashboard showing repository health state, commit counts, watcher mode, auto-push/sync status, and telemetry metrics.
- **Usage**: `gitpilot status`
- **Arguments**: None.

---

### 7. `gitpilot config`
Gets or sets configuration values directly in `gitpilot.json`.
- **Usage**: `gitpilot config <key> [value]`
- **Arguments**:
  - `<key>` *(Required)*: The configuration key to inspect or update.
  - `[value]` *(Optional)*: The new value to set. If omitted, prints the current value of `<key>`.

#### Available Configuration Keys (`<key>`):
| Configuration Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `branch` | string | `"main"` | Default target branch name. |
| `remote` | string | `"origin"` | Default target remote repository name. |
| `watch` | boolean | `true` | Global watcher activation flag (`true`/`false`). |
| `delay` | integer | `120` | Inactivity delay in seconds before committing (min: 1). |
| `auto_push` | boolean | `false` | Automatically push to remote after committing (`true`/`false`). |
| `auto_sync` | boolean | `false` | Automatically fetch & sync when behind or push is rejected (`true`/`false`). |
| `sync_strategy` | string | `"merge"` | Strategy for Auto Sync (`"merge"` or `"rebase"`). |
| `fetch_interval` | integer | `300` | Background fetch interval in seconds (`0` to disable). |
| `max_file_size_mb` | integer | `50` | Maximum file size in MB allowed to be staged. |

---

## Configuration File (`gitpilot.json`)

```json
{
  "branch": "main",
  "remote": "origin",
  "watch": true,
  "delay": 120,
  "auto_push": true,
  "auto_sync": false,
  "sync_strategy": "merge",
  "fetch_interval": 300,
  "max_file_size_mb": 50
}
```

---

## Developer Dashboard Example (`gitpilot status`)

```
=== GitPilot Developer Dashboard ===
Repository:          p:\pro\GitPilot
Branch:              main
Remote:              origin/main
Repository State:    UP_TO_DATE
Ahead Commits:       0
Behind Commits:      0
Auto-push:           Enabled
Auto-sync:           Enabled (merge)
Fetch Interval:      300s (Enabled)
Last Fetch:          2 minutes ago
Last Status Refresh: 5 seconds ago
Last Sync:           Today 18:34
Last Push:           Success
Pipeline Lock:       Idle
```

---

## Automated Test Suite

Run the full test suite using pytest or unittest:

```bash
python -m pytest tests
```
or
```bash
python -m unittest discover -s tests
```
