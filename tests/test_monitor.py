import unittest
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager
from gitpilot.status import RepositoryState, RepositoryStatus
from gitpilot.monitor import RepositoryMonitor

class TestRepositoryMonitor(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.tmpdir.name)
        self.config = GitPilotConfig({"fetch_interval": 300})
        self.git = MagicMock(spec=GitManager)
        self.git.repo_path = self.repo_path

        mock_status = RepositoryStatus(
            state=RepositoryState.UP_TO_DATE,
            current_branch="main",
            remote_name="origin",
            remote_branch="main"
        )
        self.git.evaluate_status.return_value = mock_status
        self.monitor = RepositoryMonitor(self.repo_path, self.config, self.git)

    def tearDown(self):
        self.monitor.stop_background_fetch()
        self.tmpdir.cleanup()

    def test_status_caching_and_refresh(self):
        status = self.monitor.current_status
        self.assertEqual(status.state, RepositoryState.UP_TO_DATE)
        self.git.evaluate_status.assert_called_once()

        # Second access should return cached status without evaluating git
        status2 = self.monitor.current_status
        self.assertEqual(status2, status)
        self.git.evaluate_status.assert_called_once()

    def test_listener_callback_on_state_change(self):
        listener = MagicMock()
        self.monitor.register_listener(listener)

        # Force state change
        new_status = RepositoryStatus(
            state=RepositoryState.BEHIND_REMOTE,
            current_branch="main",
            remote_name="origin",
            remote_branch="main",
            behind_count=2
        )
        self.git.evaluate_status.return_value = new_status
        self.monitor.refresh_status()

        listener.assert_called_once_with(new_status)

    def test_idle_detection_and_telemetry(self):
        self.monitor.notify_activity()
        self.assertFalse(self.monitor.is_idle(idle_threshold_sec=30.0))

        self.monitor.record_sync_telemetry()
        self.assertIsNotNone(self.monitor.last_sync)

        self.monitor.record_push_telemetry(success=True)
        self.assertIsNotNone(self.monitor.last_push)
        self.assertEqual(self.monitor.last_push_status, "Success")

if __name__ == "__main__":
    unittest.main()
