import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List

class RepositoryState(Enum):
    """Enumeration of possible repository states."""
    UP_TO_DATE = "UP_TO_DATE"         # Local matches remote tracking branch
    AHEAD_REMOTE = "AHEAD_REMOTE"     # Local has unpushed commits (ahead > 0, behind == 0)
    BEHIND_REMOTE = "BEHIND_REMOTE"   # Remote has commits local lacks (behind > 0, ahead == 0)
    DIVERGED = "DIVERGED"             # Local and remote both have unique commits (behind > 0, ahead > 0)
    MERGING = "MERGING"               # Active merge state (.git/MERGE_HEAD)
    REBASING = "REBASING"             # Active rebase state (.git/rebase-apply or .git/rebase-merge)
    CONFLICT = "CONFLICT"             # Unresolved merge/rebase conflicts present
    UNKNOWN = "UNKNOWN"               # Remote missing, detached HEAD, or non-git repo

@dataclass
class RepositoryStatus:
    """Dataclass holding repository health status and operational telemetry."""
    state: RepositoryState
    current_branch: str
    remote_name: str
    remote_branch: str
    behind_count: int = 0
    ahead_count: int = 0
    auto_sync_possible: bool = True
    has_conflicts: bool = False
    error_message: Optional[str] = None
    last_updated: float = field(default_factory=time.time)
    
    # Operational Telemetry Timestamps
    last_fetch: Optional[float] = None
    last_status_refresh: Optional[float] = None
    last_sync: Optional[float] = None
    last_push: Optional[float] = None
    last_push_status: Optional[str] = None  # "Success", "Failed", or None

@dataclass
class SyncResult:
    """Dataclass encapsulating the result of a synchronization operation."""
    success: bool
    strategy: str                         # "merge" or "rebase"
    conflicts: bool = False
    retries: int = 1
    error_message: Optional[str] = None
    files_affected: List[str] = field(default_factory=list)
