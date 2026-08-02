# GitPilot Pipeline Module (`gitpilot/pipeline.py`)

## 1. Purpose of the file
`GitPilotPipeline` orchestrates the entire safe commit, synchronization, and push workflow. Thread locking (`self._lock`) guarantees that pipeline runs, background fetches, and manual commands never execute concurrent Git operations.

## 2. V1.1 Auto Sync Workflow

```
Commit
  ↓
Push
  ↓
Success?
  ├── YES ──► Done
  └── NO
       ↓
Classify Error (REMOTE_AHEAD?)
       ├── NO ──► Log error, keep local commit safe
       └── YES
            ↓
Auto Sync Enabled?
       ├── NO ──► Log rejection, keep local commit safe
       └── YES
            ↓
Fetch Remote & Synchronize (merge or rebase)
            ↓
Sync Success?
       ├── NO (Conflict) ──► Log conflict details, keep commit safe, transition watcher to Limited Mode
       └── YES
            ↓
Retry Push
            ↓
Success!
```

## 3. Core Engine Methods
- **`synchronize(remote, branch, strategy)`**: Thread-safe synchronization helper powering manual `gitpilot sync`, startup sync, and push recovery.
- **`evaluate_startup()`**: Validates repository state before `gitpilot watch` starts, triggering auto-sync if local is behind or diverged.
- **`_push_with_auto_sync(remote, branch)`**: Handles push rejection classification, auto-sync execution, retry push, and telemetry recording.
