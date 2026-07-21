import unittest
from pathlib import Path
import tempfile
import json
from unittest.mock import MagicMock

from gitpilot.safety import SafetyScanner
from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager

class TestSafetyScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        
        self.config = GitPilotConfig({"max_file_size_mb": 1}) # 1 MB limit
        self.git_manager_mock = MagicMock(spec=GitManager)
        
        self.scanner = SafetyScanner(self.repo_path, self.config, self.git_manager_mock)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_check_repo_state_safe(self):
        self.git_manager_mock.is_git_repo.return_value = True
        self.git_manager_mock.is_detached_head.return_value = False
        self.git_manager_mock.has_merge_conflicts.return_value = False
        
        self.assertTrue(self.scanner.check_repo_state())

    def test_check_repo_state_detached_head(self):
        self.git_manager_mock.is_git_repo.return_value = True
        self.git_manager_mock.is_detached_head.return_value = True
        
        self.assertFalse(self.scanner.check_repo_state())

    def test_pre_stage_scan_sensitive_filenames(self):
        # Create a mock .env file
        env_file = self.repo_path / ".env"
        env_file.touch()
        
        # Create a safe file
        safe_file = self.repo_path / "main.py"
        safe_file.touch()
        
        # Test just the safe file
        self.assertTrue(self.scanner.pre_stage_scan(["main.py"]))
        
        # Test with the sensitive file
        self.assertFalse(self.scanner.pre_stage_scan(["main.py", ".env"]))

    def test_pre_stage_scan_large_file(self):
        # Create a file slightly larger than 1 MB (our mock config limit)
        large_file = self.repo_path / "large_model.bin"
        with open(large_file, "wb") as f:
            f.write(b"0" * (1024 * 1024 + 10))
            
        self.assertFalse(self.scanner.pre_stage_scan(["large_model.bin"]))

    def test_post_stage_scan_clean(self):
        clean_diff = '''
diff --git a/main.py b/main.py
+++ b/main.py
@@ -1,2 +1,3 @@
 def test():
+    print("Hello")
         '''
        self.git_manager_mock.get_staged_diff.return_value = clean_diff
        self.assertTrue(self.scanner.post_stage_scan())

    def test_post_stage_scan_aws_key(self):
        dirty_diff = '''
diff --git a/config.py b/config.py
+++ b/config.py
@@ -10,2 +10,3 @@
+    aws_key = "AKIAIOSFODNN7EXAMPLE"
         '''
        self.git_manager_mock.get_staged_diff.return_value = dirty_diff
        self.assertFalse(self.scanner.post_stage_scan())

    def test_post_stage_scan_ignores_deleted_secrets(self):
        """If a user is deleting a secret, we shouldn't block the commit."""
        dirty_diff = '''
diff --git a/config.py b/config.py
+++ b/config.py
@@ -10,3 +10,2 @@
-    aws_key = "AKIAIOSFODNN7EXAMPLE"
+    aws_key = os.environ.get("AWS_KEY")
         '''
        self.git_manager_mock.get_staged_diff.return_value = dirty_diff
        self.assertTrue(self.scanner.post_stage_scan())

if __name__ == '__main__':
    unittest.main()
