import unittest
import time
from gitpilot.status import RepositoryState, RepositoryStatus, SyncResult

class TestStatusModels(unittest.TestCase):
    def test_repository_state_enum(self):
        self.assertEqual(RepositoryState.UP_TO_DATE.value, "UP_TO_DATE")
        self.assertEqual(RepositoryState.BEHIND_REMOTE.value, "BEHIND_REMOTE")
        self.assertEqual(RepositoryState.DIVERGED.value, "DIVERGED")
        self.assertEqual(RepositoryState.CONFLICT.value, "CONFLICT")

    def test_repository_status_defaults(self):
        status = RepositoryStatus(
            state=RepositoryState.UP_TO_DATE,
            current_branch="main",
            remote_name="origin",
            remote_branch="main"
        )
        self.assertEqual(status.state, RepositoryState.UP_TO_DATE)
        self.assertEqual(status.behind_count, 0)
        self.assertEqual(status.ahead_count, 0)
        self.assertTrue(status.auto_sync_possible)
        self.assertFalse(status.has_conflicts)
        self.assertIsNone(status.last_sync)
        self.assertIsNone(status.last_push)

    def test_sync_result(self):
        res = SyncResult(
            success=True,
            strategy="merge",
            conflicts=False
        )
        self.assertTrue(res.success)
        self.assertEqual(res.strategy, "merge")
        self.assertFalse(res.conflicts)

if __name__ == "__main__":
    unittest.main()
