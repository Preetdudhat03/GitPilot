# GitPilot Configuration Module (`gitpilot/config.py`)

## 1. Purpose of the file
This file is responsible for managing GitPilot's configuration. It provides a way to read configuration values from a `gitpilot.json` file located in the user's project repository and save them back if necessary. In Version 1.1, it includes options for **Intelligent Auto Sync** (`auto_sync`, `sync_strategy`) and periodic background fetches (`fetch_interval`).

## 2. Configuration Options

### Core Settings
- **`branch`** (string, default `"main"`): Target branch name.
- **`remote`** (string, default `"origin"`): Remote repository name.
- **`watch`** (boolean, default `True`): Global watch toggle.
- **`delay`** (integer, default `120`): Debounce inactivity period in seconds.
- **`auto_push`** (boolean, default `False`): Automatically push after commits.

### V1.1 Auto Sync Settings
- **`auto_sync`** (boolean, default `False`): Opt-in flag to enable intelligent remote synchronization when local is behind or push is rejected.
- **`sync_strategy`** (string, default `"merge"`): Synchronization strategy. Validated options: `"merge"` or `"rebase"`.
- **`fetch_interval`** (integer, default `300`): Background fetch frequency in seconds (`0` disables background fetch).
- **`max_file_size_mb`** (integer, default `50`): Maximum staging size threshold.

## 3. Data Validation
`GitPilotConfig` sanitizes all input:
- Invalid `sync_strategy` values (e.g., `"potato"`) fall back to `"merge"` with a warning log.
- Non-integer or negative `fetch_interval` values default to `300`.
- Missing JSON keys fall back gracefully to safe defaults.
