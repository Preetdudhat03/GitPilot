import time
import threading
import logging
from typing import Callable, List, Optional
from pathlib import Path

from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager
from gitpilot.status import RepositoryState, RepositoryStatus

logger = logging.getLogger("gitpilot")

class RepositoryMonitor:
    """
    Centralized component that monitors repository health, maintains status cache,
    tracks telemetry metrics, manages debounced event processing, and dispatches state change events.
    """

    def __init__(self, repo_path: Path, config: GitPilotConfig, git: GitManager, pipeline_lock: Optional[threading.Lock] = None):
        self.repo_path = repo_path
        self.config = config
        self.git = git
        self.pipeline_lock = pipeline_lock or threading.Lock()

        self._monitor_lock = threading.Lock()
        self._listeners: List[Callable[[RepositoryStatus], None]] = []

        # Telemetry fields
        self.last_fetch: Optional[float] = None
        self.last_status_refresh: Optional[float] = None
        self.last_sync: Optional[float] = None
        self.last_push: Optional[float] = None
        self.last_push_status: Optional[str] = None
        self._last_activity_time: float = time.time()

        # Cached status
        self._cached_status: Optional[RepositoryStatus] = None

        # Debouncing timer
        self._debounce_timer: Optional[threading.Timer] = None

        # Background fetch worker thread
        self._fetch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def register_listener(self, callback: Callable[[RepositoryStatus], None]) -> None:
        """Registers a callback function to receive status updates when state changes."""
        with self._monitor_lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[RepositoryStatus], None]) -> None:
        """Unregisters a status update listener callback."""
        with self._monitor_lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def notify_activity(self) -> None:
        """Call whenever filesystem activity occurs to update the idle timer."""
        with self._monitor_lock:
            self._last_activity_time = time.time()

    def is_idle(self, idle_threshold_sec: float = 30.0) -> bool:
        """Returns True if no filesystem activity has occurred within idle_threshold_sec."""
        with self._monitor_lock:
            return (time.time() - self._last_activity_time) >= idle_threshold_sec

    @property
    def current_status(self) -> RepositoryStatus:
        """Returns the currently cached RepositoryStatus, refreshing if not available."""
        with self._monitor_lock:
            if self._cached_status is not None:
                return self._cached_status

        return self.refresh_status(fetch_first=False)

    def refresh_status(self, fetch_first: bool = False) -> RepositoryStatus:
        """
        Forces a fresh evaluation of the repository status, updating cache and telemetry.
        Dispatches state change events if state transitioned.
        """
        logger.debug("Refreshing repository status...")
        branch = self.config.branch
        remote = self.config.remote

        # Evaluate status using GitManager
        new_status = self.git.evaluate_status(remote, branch, fetch_first=fetch_first)

        now = time.time()
        with self._monitor_lock:
            old_status = self._cached_status
            self.last_status_refresh = now
            if fetch_first and new_status.last_fetch:
                self.last_fetch = new_status.last_fetch

            new_status.last_fetch = self.last_fetch
            new_status.last_status_refresh = self.last_status_refresh
            new_status.last_sync = self.last_sync
            new_status.last_push = self.last_push
            new_status.last_push_status = self.last_push_status

            self._cached_status = new_status

            # Notify listeners if state changed or error updated
            state_changed = (old_status is None or old_status.state != new_status.state or old_status.has_conflicts != new_status.has_conflicts)
            listeners_to_call = list(self._listeners) if state_changed else []

        for listener in listeners_to_call:
            try:
                listener(new_status)
            except Exception as e:
                logger.error(f"Error in repository status listener: {e}")

        return new_status

    def mark_dirty(self, debounce_sec: float = 2.0) -> None:
        """
        Marks repository state dirty and schedules a debounced status refresh.
        Multiple calls within debounce_sec reset the timer.
        """
        self.notify_activity()
        with self._monitor_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()

            self._debounce_timer = threading.Timer(debounce_sec, self._on_debounce_trigger)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _on_debounce_trigger(self) -> None:
        """Called when debounce timer expires."""
        logger.debug("Debounce timer expired. Running status refresh.")
        self.refresh_status(fetch_first=False)

    def record_sync_telemetry(self) -> None:
        """Records telemetry timestamp for a successful synchronization."""
        with self._monitor_lock:
            now = time.time()
            self.last_sync = now
            if self._cached_status:
                self._cached_status.last_sync = now

    def record_push_telemetry(self, success: bool) -> None:
        """Records telemetry timestamp and status for a push operation."""
        with self._monitor_lock:
            now = time.time()
            self.last_push = now
            self.last_push_status = "Success" if success else "Failed"
            if self._cached_status:
                self._cached_status.last_push = now
                self._cached_status.last_push_status = self.last_push_status

    def start_background_fetch(self) -> None:
        """Starts the background fetch thread if fetch_interval > 0."""
        if self.config.fetch_interval <= 0:
            logger.debug("Background fetch disabled (fetch_interval <= 0).")
            return

        if self._fetch_thread is not None and self._fetch_thread.is_alive():
            return

        self._stop_event.clear()
        self._fetch_thread = threading.Thread(target=self._background_fetch_loop, daemon=True)
        self._fetch_thread.start()
        logger.debug("Started background fetch thread.")

    def stop_background_fetch(self) -> None:
        """Stops the background fetch thread."""
        self._stop_event.set()
        if self._debounce_timer:
            self._debounce_timer.cancel()

    def _background_fetch_loop(self) -> None:
        """Worker loop that runs periodic background fetches when idle."""
        interval = self.config.fetch_interval
        while not self._stop_event.wait(interval):
            if self._stop_event.is_set():
                break

            # Only fetch if repository is idle and pipeline lock is available
            if self.is_idle(idle_threshold_sec=30.0):
                acquired = self.pipeline_lock.acquire(blocking=False)
                if acquired:
                    try:
                        logger.debug("Running background fetch...")
                        self.refresh_status(fetch_first=True)
                    except Exception as e:
                        logger.debug(f"Background fetch error: {e}")
                    finally:
                        self.pipeline_lock.release()
                else:
                    logger.debug("Pipeline lock busy; skipping background fetch cycle.")
