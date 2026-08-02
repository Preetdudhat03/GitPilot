# Repository Monitor Module (`gitpilot/monitor.py`)

## 1. Purpose of the file
`RepositoryMonitor` is a central V1.1 component responsible for:
1. **Status Caching**: Caching `RepositoryStatus` in memory to eliminate redundant Git commands.
2. **Operational Telemetry**: Tracking `last_fetch`, `last_status_refresh`, `last_sync`, and `last_push` timestamps.
3. **Debounced Event Queueing**: Debouncing file system modification bursts (e.g. 400 changes during a build) into a single status refresh after 2 seconds of inactivity.
4. **Idle-Smart Background Fetching**: Periodically executing background fetches (`git fetch`) only when the workspace is idle (>30s) and the pipeline lock is available.
5. **Event Notifications**: Dispatched state change notifications to registered listeners (such as `GitPilotWatcher`), seamlessly switching between Active Mode and Limited (Read-Only) Mode.

## 2. Event & Mode Machine
When `RepositoryMonitor` detects a state change (e.g., repository becomes `BEHIND_REMOTE` or `CONFLICT`), registered listeners receive a callback. `GitPilotWatcher` listens to these events to switch between:
- **Active Mode**: Normal automated staging, commit generation, and pushing.
- **Limited Mode**: Read-only watching; file events refresh status but pause automatic commits.
