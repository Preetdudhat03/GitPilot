# GitPilot Environment Bootstrap & Recovery System (V1.2 Explanation)

This document provides a deep, line-by-line concept and design breakdown of GitPilot's Environment Bootstrap, Recovery, and Diagnostic system (`gitpilot doctor` and `gitpilot setup`).

---

## 1. System Architecture Overview

GitPilot V1.2 decouples environment diagnostics from environment modification:

```
                          GitPilot CLI / Module Mode
                                       │
                      ┌────────────────┴────────────────┐
                      │                                 │
              gitpilot doctor                   gitpilot setup
                      │                                 │
                      ▼                                 ▼
             EnvironmentInspector               BootstrapManager
                      │                                 │
                      ▼                                 ▼
            Read-Only Diagnostics             Safe User-Level Repair
            - Python Version                  - Dependency Install
            - pip Availability                - Package Installation
            - Git Installation                - User PATH Repair
            - Virtualenv Status               - Fallback Notification
            - PATH Detection                            │
            - Registry State                            ▼
                      │                            SetupResult
                      ▼                                 │
               Diagnostic Table                         ▼
                                                 Health Check
```

---

## 2. Core Design Principles

### Principle 1: Safety & Zero Admin Elevation
GitPilot **never** attempts to request administrator privileges (`runas`), modify system-wide PATH (`HKLM`), disable Windows Execution Policies, alter Group Policy, or tamper with security settings. On restricted machines (such as college labs or enterprise PCs), all operations run strictly in the **Current User** context (`--user` scope for pip, `HKCU\Environment` for persistent Windows user PATH).

### Principle 2: Graceful Degradation & Visible Fallback
If the operating system denies PATH modification (e.g. registry policies restricting user environment edits), `gitpilot setup` does **not** fail the entire installation. Instead, it marks package installation as `SUCCESS`, reports PATH as `RESTRICTED`, exit code `1`, and displays a high-visibility fallback notification box:

```
+--------------------------------------------------------+
| GitPilot is installed successfully                     |
|                                                        |
| PATH modification was restricted by system policy.     |
| GitPilot will NOT request administrator privileges.    |
|                                                        |
| Safe Fallback Command:                                 |
|                                                        |
|     python -m gitpilot watch                           |
|                                                        |
| All GitPilot commands can be run via python -m module. |
+--------------------------------------------------------+
```

### Principle 3: Idempotency
Running `gitpilot setup` repeatedly produces identical, non-destructive results. It checks if dependencies or user PATH entries are already configured before attempting modifications, preventing duplicate PATH entries or redundant package reinstalls.

### Principle 4: Single Source of Truth for Python Requirement
The required Python version is dynamically extracted from `pyproject.toml` (`requires-python = ">=3.8"`), guaranteeing consistency between packaging configuration and CLI environment enforcement.

### Principle 5: Two-Layer Architecture & Bootstrap Independence
To allow `python -m gitpilot setup` and `python -m gitpilot doctor` to execute on fresh PCs without pre-installed runtime dependencies, GitPilot strictly enforces a two-layer architecture:

- **Layer 1 (Bootstrap Layer)**: `gitpilot/__main__.py`, `gitpilot/cli.py` (CLI dispatcher), and `gitpilot/bootstrap.py` (`EnvironmentInspector` & `BootstrapManager`). Depends ONLY on Python standard library modules and guaranteed components.
- **Layer 2 (Runtime Layer)**: `gitpilot/watcher.py`, `gitpilot/pipeline.py`, `gitpilot/monitor.py`, etc. May require third-party dependencies such as `watchdog`.

By lazily importing `GitPilotWatcher` inside `cmd_watch()` rather than at top-level `cli.py` module load time, the bootstrap commands (`setup` and `doctor`) start cleanly on fresh machines without triggering `ModuleNotFoundError`.

---

## 3. Code Implementation & Breakdown

### `gitpilot/__main__.py`
Enables direct package module invocation: `python -m gitpilot <command>`.
```python
from gitpilot.cli import main

if __name__ == "__main__":
    main()
```
Both `gitpilot <command>` (installed CLI) and `python -m gitpilot <command>` (module mode) invoke the exact same CLI entry point `gitpilot.cli.main()`.

### `gitpilot/bootstrap.py`
Contains data models (`EnvironmentStatus`, `SetupResult`), `EnvironmentInspector` (`gitpilot doctor`), and `BootstrapManager` (`gitpilot setup`).

#### Key Detection Logic:

1. **Python Version Check**:
   ```python
   python_min_req = parse_pyproject_python_version(pyproject_file)
   python_ok = check_python_req(python_min_req)
   ```
   Validates `sys.version_info` against `requires-python` in `pyproject.toml`.

2. **pip Verification**:
   ```python
   subprocess.run([sys.executable, "-m", "pip", "--version"], ...)
   ```
   Uses `sys.executable` to ensure `pip` belongs to the currently active Python interpreter.

3. **Git Availability**:
   ```python
   git_path = shutil.which("git")
   subprocess.run(["git", "--version"], ...)
   ```
   Ensures Git is available on system PATH and captures its version string.

4. **Virtual Environment Detection**:
   ```python
   is_venv = (sys.prefix != sys.base_prefix) or ("VIRTUAL_ENV" in os.environ)
   ```
   Distinguishes active virtual environments from user/system site installs.

5. **Git Identity Inspection & Source Resolution**:
   ```python
   inspect_git_identity(project_root)
   ```
   Safely inspects `user.name` and `user.email` using `git config --show-origin --get ...`. Parses configuration scope (`local`, `global`, `system`) to report where active identity originates.

6. **Windows Registry PATH Repair**:
   ```python
   with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
       # Appends scripts_dir idempotently to HKCU\Environment Path
   ```
   Modifies persistent User PATH safely, avoiding `HKLM` (System PATH). Sends `WM_SETTINGCHANGE` notification to alert open applications.

---

## 4. Git & Identity Preflight Philosophy

### Why Git is Not Automatically Installed
Installing Git on enterprise or university machines often requires administrator access (`sudo` / `runas`). Bypassing system policies is dangerous and violates security policies. GitPilot clearly flags missing Git dependencies (Exit Code `2`) and guides users to official system installers.

### Why Git Identity is Never Auto-Configured
Git commits permanently attribute code changes to `user.name` and `user.email`. GitPilot strictly treats Git identity as a user responsibility. If identity is incomplete:
- `gitpilot doctor` reports `[!] user.name/user.email is not configured`.
- `gitpilot setup` issues clear setup warnings with exact manual `git config --global ...` commands.
- `gitpilot watch` pauses automatic commits in **Limited Mode** before attempting invalid Git commits.

---

## 5. Exit Code Reference

| Exit Code | Meaning | Condition |
|---|---|---|
| `0` | Success | Environment healthy, package installed, CLI in PATH. |
| `1` | Restricted / Warning | Package installed successfully, but User PATH modified or blocked (fallback `python -m gitpilot watch` available). |
| `2` | Missing Dependency | Critical external requirement missing (e.g. Git binary not installed). |
| `3` | Unsupported Python | Active Python version does not satisfy `requires-python` in `pyproject.toml`. |
| `4` | Installation Failure | Pip or package installation encountered a fatal error. |

---

## 6. Command Reference

- `gitpilot doctor`: Read-only environment inspection (includes Python, pip, Git, Git identity & origin source). Zero modifications.
- `gitpilot setup`: Automatic environment bootstrap & recovery.
- `gitpilot setup --dry-run`: Previews setup actions without performing changes.
- `gitpilot setup --repair`: Re-attempts safe user-level repairs for missing PATH or broken installations.

