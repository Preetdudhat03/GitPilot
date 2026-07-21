import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from watchdog.events import FileModifiedEvent

from gitpilot.watcher import GitEventHandler
from gitpilot.config import GitPilotConfig
from gitpilot.pipeline import GitPilotPipeline

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
        # Simulate a file modification
        event = FileModifiedEvent("/mock/repo/src/main.py")
        self.handler.on_modified(event)
        
        # Timer should be reset
        mock_reset.assert_called_once()

    @patch.object(GitEventHandler, '_reset_timer')
    def test_rapid_changes_debounce(self, mock_reset):
        event = FileModifiedEvent("/mock/repo/src/main.py")
        
        # Fire event 3 times rapidly
        self.handler.on_modified(event)
        self.handler.on_modified(event)
        self.handler.on_modified(event)
        
        # Reset should be called 3 times
        self.assertEqual(mock_reset.call_count, 3)

if __name__ == '__main__':
    unittest.main()
