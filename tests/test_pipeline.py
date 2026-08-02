import unittest
from unittest.mock import MagicMock
from gitpilot.pipeline import GitPilotPipeline
from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager, GitError
from gitpilot.safety import SafetyScanner
from gitpilot.commit_generator import RuleBasedCommitGenerator
from gitpilot.status import RepositoryState, RepositoryStatus, SyncResult

class TestGitPilotPipeline(unittest.TestCase):
    def setUp(self):
        self.config = GitPilotConfig({"auto_push": True, "auto_sync": False, "sync_strategy": "merge"})
        self.git = MagicMock(spec=GitManager)
        self.safety = MagicMock(spec=SafetyScanner)
        self.generator = MagicMock(spec=RuleBasedCommitGenerator)
        
        self.pipeline = GitPilotPipeline(self.config, self.git, self.safety, self.generator)

    def test_run_no_changes(self):
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = []
        
        result = self.pipeline.run()
        
        self.assertFalse(result)
        self.git.stage_all.assert_not_called()

    def test_run_unsafe_repo_state(self):
        self.safety.check_repo_state.return_value = False
        
        result = self.pipeline.run()
        self.assertFalse(result)
        self.git.get_changed_files.assert_not_called()

    def test_run_unsafe_pre_stage(self):
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["secrets.json"]
        self.safety.pre_stage_scan.return_value = False
        
        result = self.pipeline.run()
        self.assertFalse(result)
        self.git.stage_all.assert_not_called()

    def test_run_unsafe_post_stage(self):
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        
        self.git.get_staged_files.return_value = ["main.py"]
        self.safety.post_stage_scan.return_value = False
        
        result = self.pipeline.run()
        
        self.assertFalse(result)
        self.git.stage_all.assert_called_once()
        self.git.unstage_files.assert_called_once_with(["main.py"])
        self.git.commit.assert_not_called()

    def test_run_successful_commit_and_push(self):
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        self.git.get_staged_files.return_value = ["main.py"]
        self.safety.post_stage_scan.return_value = True
        self.git.get_staged_diff.return_value = "+print('hello')"
        self.generator.generate.return_value = "feat: add hello"
        self.git.get_current_branch.return_value = "main"
        
        result = self.pipeline.run()
        
        self.assertTrue(result)
        self.git.commit.assert_called_once_with("feat: add hello")
        self.git.push.assert_called_once_with("origin", "main")

    def test_auto_sync_disabled_on_remote_ahead(self):
        self.config.auto_sync = False
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        self.safety.post_stage_scan.return_value = True
        self.git.get_current_branch.return_value = "main"

        self.git.push.side_effect = GitError("Push rejected: Remote branch is ahead")
        self.git.classify_push_error.return_value = "REMOTE_AHEAD"

        result = self.pipeline.run()
        self.assertTrue(result) # Local commit succeeded
        self.git.merge_remote.assert_not_called()

    def test_auto_sync_enabled_merge_success_retry_push_success(self):
        self.config.auto_sync = True
        self.config.sync_strategy = "merge"
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        self.safety.post_stage_scan.return_value = True
        self.git.get_current_branch.return_value = "main"

        # First push fails (remote ahead), second push succeeds
        self.git.push.side_effect = [GitError("Push rejected: Remote branch is ahead"), None]
        self.git.classify_push_error.return_value = "REMOTE_AHEAD"
        self.git.merge_remote.return_value = SyncResult(success=True, strategy="merge")

        result = self.pipeline.run()
        self.assertTrue(result)
        self.git.merge_remote.assert_called_once_with("origin", "main")
        self.assertEqual(self.git.push.call_count, 2)

    def test_auto_sync_enabled_rebase_conflict_abort(self):
        self.config.auto_sync = True
        self.config.sync_strategy = "rebase"
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        self.safety.post_stage_scan.return_value = True
        self.git.get_current_branch.return_value = "main"

        self.git.push.side_effect = GitError("Push rejected: Remote branch is ahead")
        self.git.classify_push_error.return_value = "REMOTE_AHEAD"
        self.git.rebase_remote.return_value = SyncResult(success=False, strategy="rebase", conflicts=True)

        result = self.pipeline.run()
        self.assertTrue(result) # Local commit safe
        self.git.rebase_remote.assert_called_once_with("origin", "main")

    def test_evaluate_startup_up_to_date(self):
        mock_status = RepositoryStatus(
            state=RepositoryState.UP_TO_DATE,
            current_branch="main",
            remote_name="origin",
            remote_branch="main"
        )
        self.pipeline.monitor.refresh_status = MagicMock(return_value=mock_status)

        status = self.pipeline.evaluate_startup()
        self.assertEqual(status.state, RepositoryState.UP_TO_DATE)

    def test_dry_run_mode(self):
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        
        result = self.pipeline.run(dry_run=True)
        self.assertTrue(result)
        self.git.stage_all.assert_not_called()

if __name__ == '__main__':
    unittest.main()
