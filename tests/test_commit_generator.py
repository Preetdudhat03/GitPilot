import unittest
from gitpilot.commit_generator import RuleBasedCommitGenerator

class TestRuleBasedCommitGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = RuleBasedCommitGenerator()

    def test_single_file_feat(self):
        msg = self.generator.generate(["gitpilot/watcher.py"], "def watch():\n+    pass")
        self.assertEqual(msg, "feat: update gitpilot/watcher.py")

    def test_single_file_fix(self):
        msg = self.generator.generate(["gitpilot/watcher.py"], "+    # fix the timeout error")
        self.assertEqual(msg, "fix: update gitpilot/watcher.py")

    def test_docs_only(self):
        msg = self.generator.generate(["README.md"], "+ # GitPilot")
        self.assertEqual(msg, "docs: update documentation in README.md")

    def test_tests_only(self):
        msg = self.generator.generate(["tests/test_watcher.py"], "def test_watch(): pass")
        self.assertEqual(msg, "test: add/update tests in tests/test_watcher.py")

    def test_config_only(self):
        msg = self.generator.generate(["pyproject.toml"], "version = 1.0")
        self.assertEqual(msg, "chore: update pyproject.toml")

    def test_multiple_files_feat(self):
        msg = self.generator.generate(["gitpilot/cli.py", "gitpilot/watcher.py"], "diff content")
        self.assertEqual(msg, "feat: update cli.py, watcher.py")

    def test_many_files(self):
        files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
        msg = self.generator.generate(files, "diff content")
        self.assertEqual(msg, "feat: modify 5 project files")

if __name__ == '__main__':
    unittest.main()
