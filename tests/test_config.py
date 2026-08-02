import unittest
from pathlib import Path
import json
import tempfile
import os

from gitpilot.config import GitPilotConfig, ConfigManager

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        self.config_manager = ConfigManager(self.repo_path)
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_config(self):
        """Test that default values are assigned when loading an empty or missing config."""
        config = self.config_manager.load()
        self.assertEqual(config.branch, "main")
        self.assertEqual(config.remote, "origin")
        self.assertTrue(config.watch)
        self.assertEqual(config.delay, 120)
        self.assertFalse(config.auto_push)
        self.assertFalse(config.auto_sync)
        self.assertEqual(config.sync_strategy, "merge")
        self.assertEqual(config.fetch_interval, 300)
        self.assertEqual(config.max_file_size_mb, 50)

    def test_load_valid_config(self):
        """Test loading a valid JSON configuration."""
        data = {
            "branch": "develop",
            "remote": "upstream",
            "watch": False,
            "delay": 300,
            "auto_push": True,
            "auto_sync": True,
            "sync_strategy": "rebase",
            "fetch_interval": 120,
            "max_file_size_mb": 100
        }
        config_file = self.repo_path / "gitpilot.json"
        with open(config_file, "w") as f:
            json.dump(data, f)
            
        config = self.config_manager.load()
        self.assertEqual(config.branch, "develop")
        self.assertEqual(config.remote, "upstream")
        self.assertFalse(config.watch)
        self.assertEqual(config.delay, 300)
        self.assertTrue(config.auto_push)
        self.assertTrue(config.auto_sync)
        self.assertEqual(config.sync_strategy, "rebase")
        self.assertEqual(config.fetch_interval, 120)
        self.assertEqual(config.max_file_size_mb, 100)

    def test_load_invalid_sync_strategy(self):
        """Test fallback to 'merge' when invalid sync_strategy is provided."""
        data = {
            "sync_strategy": "potato"
        }
        config_file = self.repo_path / "gitpilot.json"
        with open(config_file, "w") as f:
            json.dump(data, f)
            
        config = self.config_manager.load()
        self.assertEqual(config.sync_strategy, "merge")

    def test_load_invalid_json(self):
        """Test fallback to defaults when JSON is malformed."""
        config_file = self.repo_path / "gitpilot.json"
        with open(config_file, "w") as f:
            f.write("{ invalid json ")
            
        config = self.config_manager.load()
        self.assertEqual(config.branch, "main")

    def test_load_invalid_data_types(self):
        """Test robustness against invalid data types in JSON."""
        data = {
            "delay": "not-an-integer",
            "max_file_size_mb": "large"
        }
        config_file = self.repo_path / "gitpilot.json"
        with open(config_file, "w") as f:
            json.dump(data, f)
            
        config = self.config_manager.load()
        self.assertEqual(config.delay, 120)
        self.assertEqual(config.max_file_size_mb, 50)

    def test_save_config(self):
        """Test saving configuration writes properly formatted JSON."""
        config = GitPilotConfig({"branch": "feature/test", "auto_sync": True, "sync_strategy": "rebase"})
        self.config_manager.save(config)
        
        config_file = self.repo_path / "gitpilot.json"
        self.assertTrue(config_file.exists())
        
        with open(config_file, "r") as f:
            data = json.load(f)
            
        self.assertEqual(data["branch"], "feature/test")
        self.assertTrue(data["auto_sync"])
        self.assertEqual(data["sync_strategy"], "rebase")

if __name__ == '__main__':
    unittest.main()
