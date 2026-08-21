import subprocess
import time
from pathlib import Path
from typing import List, Tuple, Optional
import logging

from gitpilot.status import RepositoryState, RepositoryStatus, SyncResult

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
                encoding="utf-8",
                errors="replace",
                check=check
            )
            return result.stdout.strip('\r\n')
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() or e.stdout.strip()
            if check:
                logger.debug(f"Git command failed: {' '.join(cmd)}\nError: {error_msg}")
                raise GitError(error_msg)
            return error_msg
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
        try:
            return self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        except GitError:
            return "HEAD"

    def is_detached_head(self) -> bool:
        """Checks if the repository is in a detached HEAD state."""
        branch = self.get_current_branch()
        return branch == "HEAD"

    def is_merge_in_progress(self) -> bool:
        """Checks if a merge operation is currently in progress."""
        git_dir = self.repo_path / ".git"
        merge_head = git_dir / "MERGE_HEAD" if git_dir.is_dir() else self.repo_path / "MERGE_HEAD"
        return merge_head.exists()

    def is_rebase_in_progress(self) -> bool:
        """Checks if a rebase operation is currently in progress."""
        git_dir = self.repo_path / ".git"
        rebase_apply = git_dir / "rebase-apply" if git_dir.is_dir() else self.repo_path / "rebase-apply"
        rebase_merge = git_dir / "rebase-merge" if git_dir.is_dir() else self.repo_path / "rebase-merge"
        return rebase_apply.exists() or rebase_merge.exists()

    def has_merge_conflicts(self) -> bool:
        """Checks if there are unresolved merge conflicts."""
        try:
            unmerged = self._run_git("ls-files", "-u")
            return len(unmerged) > 0
        except GitError:
            return False

    def has_rebase_conflicts(self) -> bool:
        """Checks if there are unresolved rebase conflicts."""
        return self.is_rebase_in_progress() or self.has_merge_conflicts()

    def fetch_remote(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Fetches latest changes from the remote repository without merging.
        Returns True if successful, False if network/remote error occurs.
        """
        try:
            args = ["fetch", remote]
            if branch:
                args.append(branch)
            self._run_git(*args)
            return True
        except GitError as e:
            logger.debug(f"Fetch failed: {e}")
            return False

    def get_ahead_behind_count(self, remote: str = "origin", branch: str = "main") -> Tuple[int, int]:
        """
        Returns (ahead_count, behind_count) relative to remote tracking branch.
        """
        try:
            out = self._run_git("rev-list", "--left-right", "--count", f"HEAD...{remote}/{branch}")
            parts = out.split()
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
            return 0, 0
        except GitError:
            return 0, 0

    def evaluate_status(self, remote: str = "origin", branch: str = "main", fetch_first: bool = True) -> RepositoryStatus:
        """
        Evaluates full RepositoryStatus data object, checking in-progress operations,
        conflicts, and commit counts against the remote tracking branch.
        """
        now = time.time()
        last_fetch_time = None

        if not self.is_git_repo():
            return RepositoryStatus(
                state=RepositoryState.UNKNOWN,
                current_branch="N/A",
                remote_name=remote,
                remote_branch=branch,
                error_message="Not a valid Git repository.",
                last_updated=now
            )

        curr_branch = self.get_current_branch()
        if curr_branch == "HEAD":
            return RepositoryStatus(
                state=RepositoryState.DETACHED_HEAD,
                current_branch="HEAD",
                remote_name=remote,
                remote_branch=branch,
                error_message="Repository is currently detached from any branch. Please checkout or create a branch before continuing.",
                last_updated=now
            )

        if fetch_first:
            if self.fetch_remote(remote, curr_branch):
                last_fetch_time = now

        # In-progress / Conflict checks
        if self.has_merge_conflicts():
            return RepositoryStatus(
                state=RepositoryState.CONFLICT,
                current_branch=curr_branch,
                remote_name=remote,
                remote_branch=branch,
                has_conflicts=True,
                error_message="Merge conflicts detected.",
                last_updated=now,
                last_fetch=last_fetch_time
            )

        if self.is_merge_in_progress():
            return RepositoryStatus(
                state=RepositoryState.MERGING,
                current_branch=curr_branch,
                remote_name=remote,
                remote_branch=branch,
                error_message="Merge operation in progress.",
                last_updated=now,
                last_fetch=last_fetch_time
            )

        if self.is_rebase_in_progress():
            return RepositoryStatus(
                state=RepositoryState.REBASING,
                current_branch=curr_branch,
                remote_name=remote,
                remote_branch=branch,
                error_message="Rebase operation in progress.",
                last_updated=now,
                last_fetch=last_fetch_time
            )

        ahead, behind = self.get_ahead_behind_count(remote, curr_branch)

        if ahead == 0 and behind == 0:
            state = RepositoryState.UP_TO_DATE
        elif ahead > 0 and behind == 0:
            state = RepositoryState.AHEAD_REMOTE
        elif ahead == 0 and behind > 0:
            state = RepositoryState.BEHIND_REMOTE
        else:
            state = RepositoryState.DIVERGED

        return RepositoryStatus(
            state=state,
            current_branch=curr_branch,
            remote_name=remote,
            remote_branch=curr_branch,
            ahead_count=ahead,
            behind_count=behind,
            last_updated=now,
            last_fetch=last_fetch_time
        )

    def merge_remote(self, remote: str = "origin", branch: str = "main") -> SyncResult:
        """
        Merges remote/branch into the current local branch.
        """
        remote_ref = f"{remote}/{branch}"
        try:
            out = self._run_git("merge", remote_ref)
            return SyncResult(
                success=True,
                strategy="merge",
                conflicts=False,
                error_message=None
            )
        except GitError as e:
            has_conflicts = self.has_merge_conflicts()
            return SyncResult(
                success=False,
                strategy="merge",
                conflicts=has_conflicts,
                error_message=str(e)
            )

    def rebase_remote(self, remote: str = "origin", branch: str = "main") -> SyncResult:
        """
        Rebases current local branch onto remote/branch.
        If a conflict occurs, automatically aborts the rebase to leave working tree clean.
        """
        remote_ref = f"{remote}/{branch}"
        try:
            out = self._run_git("rebase", remote_ref)
            return SyncResult(
                success=True,
                strategy="rebase",
                conflicts=False,
                error_message=None
            )
        except GitError as e:
            # Abort rebase immediately to restore repo state
            self.abort_rebase()
            return SyncResult(
                success=False,
                strategy="rebase",
                conflicts=True,
                error_message=str(e)
            )

    def abort_merge(self) -> None:
        """Aborts an active merge operation."""
        try:
            self._run_git("merge", "--abort")
        except GitError as e:
            logger.debug(f"Failed to abort merge: {e}")

    def abort_rebase(self) -> None:
        """Aborts an active rebase operation."""
        try:
            self._run_git("rebase", "--abort")
        except GitError as e:
            logger.debug(f"Failed to abort rebase: {e}")

    def get_changed_files(self) -> List[str]:
        """
        Gets a list of all changed files (modified, deleted, untracked) 
        that are not ignored by .gitignore.
        """
        status = self._run_git("status", "--porcelain")
        files = []
        for line in status.splitlines():
            if not line:
                continue
            filename = line[3:].strip()
            if filename.startswith('"') and filename.endswith('"'):
                filename = filename[1:-1]
            files.append(filename)
        return files

    def stage_files(self, files: List[str]) -> None:
        """Stages specific files."""
        if not files:
            return
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

    def get_user_identity(self) -> Tuple[Optional[str], Optional[str], str, bool]:
        """
        Safely inspects the effective Git user.name, user.email, and origin source.
        Returns (user_name, user_email, origin_source, identity_ok).
        """
        user_name = None
        user_email = None
        name_source = None
        email_source = None

        try:
            out_n = self._run_git("config", "--show-origin", "--get", "user.name", check=False)
            if out_n and "\t" in out_n:
                origin_str, val = out_n.split("\t", 1)
                user_name = val.strip()
                name_source = self._parse_config_origin(origin_str)
            elif out_n and not out_n.startswith("error") and not out_n.startswith("Git"):
                out_simple = self._run_git("config", "--get", "user.name", check=False)
                if out_simple and not out_simple.startswith("error"):
                    user_name = out_simple.strip()
                    name_source = "global"

            out_e = self._run_git("config", "--show-origin", "--get", "user.email", check=False)
            if out_e and "\t" in out_e:
                origin_str, val = out_e.split("\t", 1)
                user_email = val.strip()
                email_source = self._parse_config_origin(origin_str)
            elif out_e and not out_e.startswith("error") and not out_e.startswith("Git"):
                out_simple_e = self._run_git("config", "--get", "user.email", check=False)
                if out_simple_e and not out_simple_e.startswith("error"):
                    user_email = out_simple_e.strip()
                    email_source = "global"

        except Exception:
            pass

        if name_source and email_source:
            if name_source == email_source:
                origin_source = name_source
            else:
                origin_source = f"{name_source}/{email_source}"
        elif name_source:
            origin_source = name_source
        elif email_source:
            origin_source = email_source
        else:
            origin_source = "none"

        identity_ok = bool(user_name and user_email)
        return user_name, user_email, origin_source, identity_ok

    @staticmethod
    def _parse_config_origin(origin_str: str) -> str:
        """Parses git config origin string to identify local, global, or system scope."""
        s = origin_str.lower()
        if ".git/config" in s or ".git\\config" in s or "local" in s:
            return "local"
        elif ".gitconfig" in s or "global" in s or "home" in s or "appdata" in s or "users" in s:
            return "global"
        elif "etc" in s or "system" in s or "program files" in s:
            return "system"
        return "global"

    def has_valid_identity(self) -> bool:
        """Returns True if both user.name and user.email are configured."""
        _, _, _, identity_ok = self.get_user_identity()
        return identity_ok

    def commit(self, message: str) -> None:
        """Creates a commit with the given message, handling identity errors gracefully."""
        try:
            self._run_git("commit", "-m", message)
        except GitError as e:
            err_str = str(e)
            if any(k in err_str.lower() for k in ["author identity unknown", "please tell me who you are"]):
                user_name, user_email, _, _ = self.get_user_identity()
                cmd_hints = []
                if not user_name:
                    cmd_hints.append('git config --global user.name "Your Name"')
                if not user_email:
                    cmd_hints.append('git config --global user.email "you@example.com"')
                hint_str = "\n".join(f"    {c}" for c in cmd_hints)
                raise GitError(
                    f"Git identity is not configured (Author identity unknown).\n"
                    f"Automatic commits are paused. Configure your Git identity using:\n{hint_str}"
                )
            raise


    def is_remote_ahead(self, remote: str, branch: str) -> bool:
        """
        Checks if the remote branch has commits that are not present locally.
        """
        try:
            self.fetch_remote(remote, branch)
            behind = self._run_git("rev-list", "--count", f"HEAD..{remote}/{branch}")
            return int(behind) > 0
        except GitError:
            return False

    def classify_push_error(self, error_msg: str) -> str:
        """
        Classifies a push failure error message into standardized error codes.
        """
        lower = error_msg.lower()
        if any(keyword in lower for keyword in ["ahead", "fetch first", "non-fast-forward", "behind", "rejected"]):
            return "REMOTE_AHEAD"
        elif any(keyword in lower for keyword in ["could not resolve host", "network", "connection refused", "timed out"]):
            return "NETWORK_ERROR"
        elif any(keyword in lower for keyword in ["authentication failed", "could not read username", "access denied", "401"]):
            return "AUTH_ERROR"
        elif any(keyword in lower for keyword in ["permission denied", "403"]):
            return "PERMISSION_DENIED"
        elif any(keyword in lower for keyword in ["does not appear to be a git repository", "could not read from remote"]):
            return "REPO_NOT_FOUND"
        return "UNKNOWN"

    def push(self, remote: str, branch: str) -> None:
        """
        Safely pushes to the remote. 
        Will NEVER use force push.
        """
        if self.is_remote_ahead(remote, branch):
            raise GitError(
                f"Push rejected: Remote branch '{remote}/{branch}' is ahead of your local branch.\n"
                "You must pull and merge changes before GitPilot can push."
            )
            
        self._run_git("push", remote, branch)
