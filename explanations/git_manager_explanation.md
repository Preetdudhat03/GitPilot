# Git Manager Module (`gitpilot/git_manager.py`)

## 1. Purpose of the file
`GitManager` provides an object-oriented Python wrapper around standard Git CLI commands. In V1.1, all Git operations (fetching, merging, rebasing, aborting, status evaluation, push error classification) are strictly encapsulated within `GitManager`. No raw Git commands are executed directly in the pipeline or CLI.

## 2. Key Methods

### Status & Synchronization Methods
- **`fetch_remote(remote, branch)`**: Executes `git fetch <remote> [branch]`.
- **`get_ahead_behind_count(remote, branch)`**: Runs `git rev-list --left-right --count HEAD...<remote>/<branch>` to return `(ahead, behind)` counts.
- **`evaluate_status(remote, branch, fetch_first)`**: Evaluates repository state into 8 granular states (`UP_TO_DATE`, `BEHIND_REMOTE`, `AHEAD_REMOTE`, `DIVERGED`, `MERGING`, `REBASING`, `CONFLICT`, `UNKNOWN`).
- **`merge_remote(remote, branch)`**: Runs `git merge <remote>/<branch>` and returns a `SyncResult`.
- **`rebase_remote(remote, branch)`**: Runs `git rebase <remote>/<branch>`. If conflicts occur, automatically invokes `abort_rebase()` to leave working directory clean.
- **`abort_merge()` & `abort_rebase()`**: Runs `git merge --abort` or `git rebase --abort`.

### Push Failure Classification
- **`classify_push_error(error_msg)`**: Analyzes Git stderr output and returns standardized error codes: `REMOTE_AHEAD`, `NETWORK_ERROR`, `AUTH_ERROR`, `PERMISSION_DENIED`, `REPO_NOT_FOUND`, or `UNKNOWN`.
