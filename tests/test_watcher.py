import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from watchdog.events import FileModifiedEvent

from gitpilot.watcher import GitEventHandler, GitPilotWatcher
from gitpilot.config import GitPilotConfig
from gitpilot.pipeline import GitPilotPipeline
from gitpilot.status import RepositoryState, RepositoryStatus

class TestGitEventHandler(unittest.TestCase):
    def setUp(self):
        self.repo_path = Path("/mock/repo")
        self.config = GitPilotConfig({"delay": 120})
        self.pipeline = MagicMock(spec=GitPilotPipeline)
        self.handler = GitEventHandler(self.repo_path, self.config, self.pipeline)

    def test_ignore_paths(self):
        self.assertTrue(self.handler._is_ignored("/mock/repo/.git/config"))
        self.assertTrue(self.handler._is_ignored("/mock/repo/node_modules/package/index.js"))
        self.assertTrue(self.handler._is_ignored("/mock/repo/gitpilot.json"))
        self.assertTrue(self.handler._is_ignored("/mock/repo/__pycache__/main.pyc"))
        
        self.assertFalse(self.handler._is_ignored("/mock/repo/src/main.py"))
        self.assertFalse(self.handler._is_ignored("/mock/repo/README.md"))

    @patch.object(GitEventHandler, '_reset_timer')
    def test_debounce_triggers_pipeline(self, mock_reset):
        event = FileModifiedEvent("/mock/repo/src/main.py")
        self.handler.on_modified(event)
        mock_reset.assert_called_once()

    def test_limited_mode_pauses_pipeline(self):
        mock_watcher = MagicMock()
        mock_watcher.mode = "limited"
        self.handler.watcher = mock_watcher

        self.handler._trigger_pipeline()
        self.pipeline.run.assert_not_called()

if __name__ == '__main__':
    unittest.main()
