import unittest
from pathlib import Path
import json
import tempfile
import os

from gitpilot.config import GitPilotConfig, ConfigManager

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to act as a fake repository
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
        self.assertEqual(config.max_file_size_mb, 50)

    def test_load_valid_config(self):
        """Test loading a valid JSON configuration."""
        data = {
            "branch": "develop",
            "remote": "upstream",
            "watch": False,
            "delay": 300,
            "auto_push": True,
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
        self.assertEqual(config.max_file_size_mb, 100)

    def test_load_invalid_json(self):
        """Test fallback to defaults when JSON is malformed."""
        config_file = self.repo_path / "gitpilot.json"
        with open(config_file, "w") as f:
            f.write("{ invalid json ")
            
        config = self.config_manager.load()
        # Should not crash, should return defaults
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
        self.assertEqual(config.delay, 120) # Fallback to default
        self.assertEqual(config.max_file_size_mb, 50) # Fallback to default

    def test_save_config(self):
        """Test saving configuration writes properly formatted JSON."""
        config = GitPilotConfig({"branch": "feature/test"})
        self.config_manager.save(config)
        
        config_file = self.repo_path / "gitpilot.json"
        self.assertTrue(config_file.exists())
        
        with open(config_file, "r") as f:
            data = json.load(f)
            
        self.assertEqual(data["branch"], "feature/test")
        self.assertEqual(data["delay"], 120) # Default was saved

if __name__ == '__main__':
    unittest.main()
