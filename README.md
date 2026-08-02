# GitPilot V1.1

GitPilot is a smart, developer-productivity CLI tool that automatically watches a Git repository for file changes, waits until you stop typing (debouncing), and then safely stages, commits, and pushes your changes. 

Version 1.1 introduces **Intelligent Auto Sync**, an automatic startup synchronization check, a developer status dashboard, and a lock-safe background fetch architecture.

---

## Features
- **Smart Debouncing**: Waits for a configurable period of inactivity before committing. Rapid saves group into one meaningful commit.
- **Intelligent Auto Sync**: Automatically fetches and synchronizes (`merge` or `rebase`) when the remote branch is ahead, both on startup and when a push is rejected.
- **Limited / Read-Only Watcher Mode**: If your repository requires manual conflict resolution, GitPilot enters Limited Mode (watching files & notifying, pausing auto-commits) instead of exiting.
- **Repository Health State Machine**: Evaluates 8 distinct repository states (`UP_TO_DATE`, `BEHIND_REMOTE`, `AHEAD_REMOTE`, `DIVERGED`, `MERGING`, `REBASING`, `CONFLICT`, `UNKNOWN`).
- **Centralized `RepositoryMonitor`**: Manages status caching, debouncing, idle detection, telemetry tracking (`last_fetch`, `last_status_refresh`, `last_sync`, `last_push`), and event callbacks.
- **Safety Guarantees**: Never uses `git push --force`, `git push --force-with-lease`, or `git reset --hard`. Your local commits remain safe.
- **Pre-Stage & Post-Stage Scanning**: Blocks large files and scans git diffs for sensitive credentials.

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

## Configuration (`gitpilot.json`)

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
- **`auto_sync`**: Automatically fetch and synchronize remote changes (`true`/`false`). Default: `false`.
- **`sync_strategy`**: Synchronization method (`"merge"` or `"rebase"`). Default: `"merge"`.
- **`fetch_interval`**: Background fetch frequency in seconds. Default: `300` (set `0` to disable).

---

## CLI Commands

| Command | Description |
| :--- | :--- |
| `gitpilot init` | Creates initial `gitpilot.json` configuration file. |
| `gitpilot watch` | Starts background watcher with Automatic Initial Synchronization. |
| `gitpilot sync` | Manually triggers repository synchronization with remote. |
| `gitpilot commit [--push]` | Manually triggers the safe commit pipeline. |
| `gitpilot push` | Manually pushes local commits to remote. |
| `gitpilot status` | Displays the rich developer status dashboard. |
| `gitpilot config <key> [val]` | Gets or sets configuration values. |

---

## Developer Dashboard (`gitpilot status`)

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

## Testing

```bash
python -m pytest tests
```
or
```bash
python -m unittest discover -s tests
```
