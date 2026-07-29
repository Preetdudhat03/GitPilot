import unittest
from unittest.mock import MagicMock
from gitpilot.pipeline import GitPilotPipeline
from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager, GitError
from gitpilot.safety import SafetyScanner
from gitpilot.commit_generator import RuleBasedCommitGenerator

from gitpilot.stats import PushTracker

class TestGitPilotPipeline(unittest.TestCase):
    def setUp(self):
        self.config = GitPilotConfig({"auto_push": True})
        self.git = MagicMock(spec=GitManager)
        self.safety = MagicMock(spec=SafetyScanner)
        self.generator = MagicMock(spec=RuleBasedCommitGenerator)
        self.stats = MagicMock(spec=PushTracker)
        
        self.pipeline = GitPilotPipeline(self.config, self.git, self.safety, self.generator, stats=self.stats)

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
        self.stats.increment_push_count.assert_called_once()

    def test_run_push_failure_preserves_commit(self):
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        self.safety.post_stage_scan.return_value = True
        
        self.git.push.side_effect = GitError("Network disconnected")
        
        # The pipeline should still return True because the local commit was successful!
        result = self.pipeline.run()
        
        self.assertTrue(result)
        self.git.commit.assert_called_once()
        
    def test_dry_run_mode(self):
        self.safety.check_repo_state.return_value = True
        self.git.get_changed_files.return_value = ["main.py"]
        self.safety.pre_stage_scan.return_value = True
        
        result = self.pipeline.run(dry_run=True)
        
        self.assertTrue(result) # Completes the mock run successfully
        self.git.stage_all.assert_not_called()
        self.git.commit.assert_not_called()

if __name__ == '__main__':
    unittest.main()
