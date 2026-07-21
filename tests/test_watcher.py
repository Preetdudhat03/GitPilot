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

    @patch('gitpilot.watcher.threading.Timer')
    def test_debounce_triggers_pipeline(self, mock_timer_cls):
        mock_timer_instance = MagicMock()
        mock_timer_cls.return_value = mock_timer_instance
        
        # Simulate a file modification
        event = FileModifiedEvent("/mock/repo/src/main.py")
        self.handler.on_modified(event)
        
        # Timer should be created with 120s delay and the trigger function
        mock_timer_cls.assert_called_once_with(120, self.handler._trigger_pipeline)
        mock_timer_instance.start.assert_called_once()
        
        # Manually trigger the pipeline to simulate timer expiration
        self.handler._trigger_pipeline()
        
        self.pipeline.run.assert_called_once()

    @patch('gitpilot.watcher.threading.Timer')
    def test_rapid_changes_debounce(self, mock_timer_cls):
        mock_timer_instance1 = MagicMock()
        mock_timer_instance2 = MagicMock()
        mock_timer_instance3 = MagicMock()
        mock_timer_cls.side_effect = [mock_timer_instance1, mock_timer_instance2, mock_timer_instance3]
        
        event = FileModifiedEvent("/mock/repo/src/main.py")
        
        # Fire event 3 times rapidly
        self.handler.on_modified(event)
        self.handler.on_modified(event)
        self.handler.on_modified(event)
        
        # Timer should be created 3 times
        self.assertEqual(mock_timer_cls.call_count, 3)
        
        # The first two timers should have been cancelled!
        mock_timer_instance1.cancel.assert_called_once()
        mock_timer_instance2.cancel.assert_called_once()
        
        # The final timer should be started but NOT cancelled
        mock_timer_instance3.start.assert_called_once()
        mock_timer_instance3.cancel.assert_not_called()

if __name__ == '__main__':
    unittest.main()
