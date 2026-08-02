import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import argparse

from gitpilot.cli import cmd_status, cmd_init, cmd_sync, cmd_config
from gitpilot.status import SyncResult

class TestCLI(unittest.TestCase):
    @patch('gitpilot.cli.get_pipeline')
    def test_cmd_status_not_repo(self, mock_get_pipeline):
        mock_pipeline = MagicMock()
        mock_pipeline.git.is_git_repo.return_value = False
        mock_get_pipeline.return_value = mock_pipeline
        
        args = argparse.Namespace(verbose=False)
        
        with self.assertRaises(SystemExit) as cm:
            cmd_status(args, Path("/mock"))
            
        self.assertEqual(cm.exception.code, 1)

    @patch('gitpilot.cli.ConfigManager')
    def test_cmd_init_creates_config(self, mock_config_mgr):
        mock_instance = MagicMock()
        mock_instance.config_path.exists.return_value = False
        mock_config_mgr.return_value = mock_instance
        
        args = argparse.Namespace(verbose=False)
        cmd_init(args, Path("/mock"))
        
        mock_instance.load.assert_called_once()
        mock_instance.save.assert_called_once()

    @patch('gitpilot.cli.get_pipeline')
    def test_cmd_sync_success(self, mock_get_pipeline):
        mock_pipeline = MagicMock()
        mock_pipeline.git.is_git_repo.return_value = True
        mock_pipeline.config.sync_strategy = "merge"
        mock_pipeline.synchronize.return_value = SyncResult(success=True, strategy="merge")
        mock_get_pipeline.return_value = mock_pipeline

        args = argparse.Namespace(verbose=False)
        cmd_sync(args, Path("/mock"))
        mock_pipeline.synchronize.assert_called_once()

    @patch('gitpilot.cli.ConfigManager')
    def test_cmd_config_invalid_sync_strategy(self, mock_config_mgr):
        mock_instance = MagicMock()
        mock_instance.config_path.exists.return_value = True
        mock_config = MagicMock()
        mock_config.sync_strategy = "merge"
        mock_instance.load.return_value = mock_config
        mock_config_mgr.return_value = mock_instance

        args = argparse.Namespace(verbose=False, key="sync_strategy", value="potato")

        with self.assertRaises(SystemExit) as cm:
            cmd_config(args, Path("/mock"))

        self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
