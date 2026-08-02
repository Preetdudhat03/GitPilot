import unittest
import tempfile
import subprocess
from pathlib import Path
from gitpilot.git_manager import GitManager, GitError
from gitpilot.status import RepositoryState

class TestGitManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        
        subprocess.run(["git", "init"], cwd=str(self.repo_path), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "config", "init.defaultBranch", "main"], cwd=str(self.repo_path), check=True)
        
        (self.repo_path / "README.md").write_text("Hello World")
        subprocess.run(["git", "add", "README.md"], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(self.repo_path), check=True)
        
        self.git = GitManager(self.repo_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_git_repo(self):
        self.assertTrue(self.git.is_git_repo())
        
        with tempfile.TemporaryDirectory() as non_repo:
            non_repo_git = GitManager(Path(non_repo))
            self.assertFalse(non_repo_git.is_git_repo())

    def test_get_current_branch(self):
        branch = self.git.get_current_branch()
        self.assertTrue(branch in ["main", "master"])

    def test_get_changed_files(self):
        (self.repo_path / "new_file.txt").write_text("New")
        (self.repo_path / "README.md").write_text("Modified")
        
        changed = self.git.get_changed_files()
        self.assertIn("new_file.txt", changed)
        self.assertIn("README.md", changed)
        self.assertEqual(len(changed), 2)

    def test_stage_and_unstage_files(self):
        test_file = "test.txt"
        (self.repo_path / test_file).write_text("test content")
        
        self.git.stage_files([test_file])
        
        staged = self.git.get_staged_files()
        self.assertIn(test_file, staged)
        
        self.git.unstage_files([test_file])
        staged_after = self.git.get_staged_files()
        self.assertNotIn(test_file, staged_after)
        self.assertTrue((self.repo_path / test_file).exists())

    def test_commit(self):
        test_file = "commit_test.txt"
        (self.repo_path / test_file).write_text("test content")
        
        self.git.stage_all()
        self.git.commit("feat: test commit")
        
        log = subprocess.run(["git", "log", "-1", "--pretty=%B"], cwd=str(self.repo_path), capture_output=True, text=True)
        self.assertIn("feat: test commit", log.stdout)
        self.assertEqual(len(self.git.get_changed_files()), 0)

    def test_classify_push_error(self):
        self.assertEqual(self.git.classify_push_error("Push rejected: Remote branch 'origin/main' is ahead"), "REMOTE_AHEAD")
        self.assertEqual(self.git.classify_push_error("error: failed to push: non-fast-forward"), "REMOTE_AHEAD")
        self.assertEqual(self.git.classify_push_error("Could not resolve host: github.com"), "NETWORK_ERROR")
        self.assertEqual(self.git.classify_push_error("Authentication failed for repo"), "AUTH_ERROR")
        self.assertEqual(self.git.classify_push_error("Permission denied (publickey)"), "PERMISSION_DENIED")
        self.assertEqual(self.git.classify_push_error("fatal: 'origin' does not appear to be a git repository"), "REPO_NOT_FOUND")

    def test_evaluate_status(self):
        status = self.git.evaluate_status(remote="origin", branch="main", fetch_first=False)
        self.assertIn(status.state, [RepositoryState.UP_TO_DATE, RepositoryState.AHEAD_REMOTE, RepositoryState.BEHIND_REMOTE, RepositoryState.UNKNOWN])

if __name__ == '__main__':
    unittest.main()
