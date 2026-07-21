import unittest
from unittest.mock import MagicMock
from pathlib import Path
import time

from watchdog.events import FileModifiedEvent

from gitpilot.watcher import GitEventHandler
from gitpilot.config import GitPilotConfig
from gitpilot.pipeline import GitPilotPipeline

class TestGitEventHandler(unittest.TestCase):
    def setUp(self):
        self.repo_path = Path("/mock/repo")
        # Extremely short delay for testing
        self.config = GitPilotConfig({"delay": 0.1})
        self.pipeline = MagicMock(spec=GitPilotPipeline)
        
        self.handler = GitEventHandler(self.repo_path, self.config, self.pipeline)

    def tearDown(self):
        if self.handler.timer:
            self.handler.timer.cancel()

    def test_ignore_paths(self):
        self.assertTrue(self.handler._is_ignored("/mock/repo/.git/config"))
        self.assertTrue(self.handler._is_ignored("/mock/repo/node_modules/package/index.js"))
        self.assertTrue(self.handler._is_ignored("/mock/repo/gitpilot.json"))
        self.assertTrue(self.handler._is_ignored("/mock/repo/__pycache__/main.pyc"))
        
        self.assertFalse(self.handler._is_ignored("/mock/repo/src/main.py"))
        self.assertFalse(self.handler._is_ignored("/mock/repo/README.md"))

    def test_debounce_triggers_pipeline(self):
        # Simulate a file modification
        event = FileModifiedEvent("/mock/repo/src/main.py")
        self.handler.on_modified(event)
        
        # Pipeline should not be called immediately
        self.pipeline.run.assert_not_called()
        
        # Wait for the delay (0.1s) plus a tiny margin
        time.sleep(0.3)
        
        # Now it should be called exactly once
        self.pipeline.run.assert_called_once()

    def test_rapid_changes_debounce(self):
        event = FileModifiedEvent("/mock/repo/src/main.py")
        
        # Fire event 3 times rapidly
        self.handler.on_modified(event)
        time.sleep(0.02)
        self.handler.on_modified(event)
        time.sleep(0.02)
        self.handler.on_modified(event)
        
        # Wait for timer to expire after the LAST event
        time.sleep(0.3)
        
        # Should still only be called ONCE
        self.pipeline.run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
