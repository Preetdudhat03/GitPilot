import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger("gitpilot")

class GitError(Exception):
    """Custom exception raised when a Git command fails."""
    pass

class GitManager:
    """Provides a safe, object-oriented wrapper around the Git command line."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def _run_git(self, *args: str, check: bool = True) -> str:
        """
        Executes a git command in the repository path.
        
        Args:
            *args: Git command arguments (e.g. 'status', '--porcelain')
            check: If True, raises GitError on non-zero exit code.
            
        Returns:
            The stripped standard output of the command.
        """
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=check
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if check:
                error_msg = e.stderr.strip() or e.stdout.strip()
                logger.debug(f"Git command failed: {' '.join(cmd)}\nError: {error_msg}")
                raise GitError(error_msg)
            return e.stdout.strip()
        except FileNotFoundError:
            raise GitError("Git executable not found. Please ensure Git is installed and in your PATH.")

    def is_git_repo(self) -> bool:
        """Checks if the current directory is a valid Git repository."""
        try:
            self._run_git("rev-parse", "--is-inside-work-tree")
            return True
        except GitError:
            return False

    def get_current_branch(self) -> str:
        """Gets the name of the currently checked out branch."""
        return self._run_git("rev-parse", "--abbrev-ref", "HEAD")

    def is_detached_head(self) -> bool:
        """Checks if the repository is in a detached HEAD state."""
        branch = self.get_current_branch()
        return branch == "HEAD"

    def has_merge_conflicts(self) -> bool:
        """Checks if there are unresolved merge conflicts."""
        # 'git ls-files -u' lists unmerged files
        unmerged = self._run_git("ls-files", "-u")
        return len(unmerged) > 0

    def get_changed_files(self) -> List[str]:
        """
        Gets a list of all changed files (modified, deleted, untracked) 
        that are not ignored by .gitignore.
        """
        # --porcelain is machine-readable status
        status = self._run_git("status", "--porcelain")
        files = []
        for line in status.splitlines():
            if not line:
                continue
            # Output format is "XY filename"
            # Extract just the filename (which starts at index 3)
            filename = line[3:].strip()
            # Handle quoted filenames (e.g. spaces in names)
            if filename.startswith('"') and filename.endswith('"'):
                filename = filename[1:-1]
            files.append(filename)
        return files

    def stage_files(self, files: List[str]) -> None:
        """Stages specific files."""
        if not files:
            return
        # Add files in chunks to avoid command line length limits
        chunk_size = 50
        for i in range(0, len(files), chunk_size):
            chunk = files[i:i + chunk_size]
            self._run_git("add", "--", *chunk)

    def stage_all(self) -> None:
        """Stages all changed files."""
        self._run_git("add", "-A")

    def unstage_files(self, files: List[str]) -> None:
        """
        Safely unstages files without modifying the working directory.
        Uses 'git restore --staged <file>'.
        """
        if not files:
            return
        
        for file in files:
            try:
                self._run_git("restore", "--staged", "--", file)
            except GitError:
                # Fallback for older git versions
                try:
                    self._run_git("rm", "--cached", "--", file)
                except GitError as e:
                    logger.warning(f"Failed to unstage {file}: {e}")

    def get_staged_diff(self) -> str:
        """Gets the diff of currently staged files."""
        return self._run_git("diff", "--cached")
        
    def get_staged_files(self) -> List[str]:
        """Returns a list of files that are currently staged."""
        diff_names = self._run_git("diff", "--cached", "--name-only")
        return [f.strip() for f in diff_names.splitlines() if f.strip()]

    def commit(self, message: str) -> None:
        """Creates a commit with the given message."""
        self._run_git("commit", "-m", message)

    def is_remote_ahead(self, remote: str, branch: str) -> bool:
        """
        Checks if the remote branch has commits that are not present locally.
        Avoids attempting a push if it will be rejected.
        """
        try:
            # Update remote tracking branches (does not merge)
            self._run_git("fetch", remote, branch)
            
            # Count how many commits the remote has that we don't
            behind = self._run_git("rev-list", "--count", f"HEAD..{remote}/{branch}")
            return int(behind) > 0
        except GitError:
            # If the branch doesn't exist on remote yet, it can't be ahead
            return False

    def push(self, remote: str, branch: str) -> None:
        """
        Safely pushes to the remote. 
        Will NEVER use force push.
        """
        if self.is_remote_ahead(remote, branch):
            raise GitError(
                f"Push rejected: Remote branch '{remote}/{branch}' is ahead of your local branch.\n"
                "You must pull and merge changes manually before GitPilot can push."
            )
            
        self._run_git("push", remote, branch)
