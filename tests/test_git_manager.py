import unittest
import tempfile
import subprocess
from pathlib import Path
from gitpilot.git_manager import GitManager, GitError

class TestGitManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        
        # Initialize a real git repository inside the temp directory
        subprocess.run(["git", "init"], cwd=str(self.repo_path), check=True, capture_output=True)
        # Set dummy user info for commits
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(self.repo_path), check=True)
        # Set default branch to main
        subprocess.run(["git", "config", "init.defaultBranch", "main"], cwd=str(self.repo_path), check=True)
        
        # Create an initial commit so we are on a valid branch
        (self.repo_path / "README.md").write_text("Hello World")
        subprocess.run(["git", "add", "README.md"], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(self.repo_path), check=True)
        
        self.git = GitManager(self.repo_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_git_repo(self):
        self.assertTrue(self.git.is_git_repo())
        
        # Test a non-repo directory
        with tempfile.TemporaryDirectory() as non_repo:
            non_repo_git = GitManager(Path(non_repo))
            self.assertFalse(non_repo_git.is_git_repo())

    def test_get_current_branch(self):
        branch = self.git.get_current_branch()
        # It could be 'main' or 'master' depending on system git config
        self.assertTrue(branch in ["main", "master"])

    def test_get_changed_files(self):
        # Create a new untracked file
        (self.repo_path / "new_file.txt").write_text("New")
        # Modify tracked file
        (self.repo_path / "README.md").write_text("Modified")
        
        changed = self.git.get_changed_files()
        self.assertIn("new_file.txt", changed)
        self.assertIn("README.md", changed)
        self.assertEqual(len(changed), 2)

    def test_stage_and_unstage_files(self):
        # Create new file
        test_file = "test.txt"
        (self.repo_path / test_file).write_text("test content")
        
        # Stage it
        self.git.stage_files([test_file])
        
        staged = self.git.get_staged_files()
        self.assertIn(test_file, staged)
        
        # Unstage it
        self.git.unstage_files([test_file])
        staged_after = self.git.get_staged_files()
        self.assertNotIn(test_file, staged_after)
        
        # The file should still exist on disk (working tree untouched)
        self.assertTrue((self.repo_path / test_file).exists())

    def test_commit(self):
        test_file = "commit_test.txt"
        (self.repo_path / test_file).write_text("test content")
        
        self.git.stage_all()
        self.git.commit("feat: test commit")
        
        # Verify the commit message is in the log
        log = subprocess.run(["git", "log", "-1", "--pretty=%B"], cwd=str(self.repo_path), capture_output=True, text=True)
        self.assertIn("feat: test commit", log.stdout)
        
        # No files should be changed anymore
        self.assertEqual(len(self.git.get_changed_files()), 0)

if __name__ == '__main__':
    unittest.main()
