import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import argparse

# We have to patch sys.argv before importing cli because it parses args at the module level?
# Actually, it only parses them in main(), which is good.
from gitpilot.cli import cmd_status, cmd_init

class TestCLI(unittest.TestCase):
    @patch('gitpilot.cli.GitManager')
    @patch('gitpilot.cli.ConfigManager')
    def test_cmd_status_not_repo(self, mock_config_mgr, mock_git_mgr):
        # Setup mocks
        mock_git_instance = MagicMock()
        mock_git_instance.is_git_repo.return_value = False
        mock_git_mgr.return_value = mock_git_instance
        
        args = argparse.Namespace(verbose=False)
        
        # Should exit with code 1 if not a git repo
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
        
        # It should have loaded defaults and saved them
        mock_instance.load.assert_called_once()
        mock_instance.save.assert_called_once()

    @patch('gitpilot.cli.ConfigManager')
    def test_cmd_init_skips_if_exists(self, mock_config_mgr):
        mock_instance = MagicMock()
        mock_instance.config_path.exists.return_value = True
        mock_config_mgr.return_value = mock_instance
        
        args = argparse.Namespace(verbose=False)
        cmd_init(args, Path("/mock"))
        
        # It should NOT load or save if it already exists
        mock_instance.load.assert_not_called()
        mock_instance.save.assert_not_called()

if __name__ == '__main__':
    unittest.main()
