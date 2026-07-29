import logging
import threading
from pathlib import Path
from typing import Optional
from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager, GitError
from gitpilot.safety import SafetyScanner
from gitpilot.commit_generator import CommitMessageGenerator
from gitpilot.logger import print_success
from gitpilot.stats import PushTracker

logger = logging.getLogger("gitpilot")

class GitPilotPipeline:
    """
    Coordinates the entire GitPilot workflow safely.
    It ensures only one operation happens at a time using a threading Lock.
    """
    
    def __init__(self, 
                 config: GitPilotConfig, 
                 git: GitManager, 
                 safety: SafetyScanner, 
                 generator: CommitMessageGenerator,
                 stats: Optional[PushTracker] = None):
        self.config = config
        self.git = git
        self.safety = safety
        self.generator = generator
        repo_path = getattr(git, "repo_path", None) or Path.cwd()
        self.stats = stats if stats is not None else PushTracker(repo_path)
        
        # Thread lock to prevent concurrent git operations
        self._lock = threading.Lock()

    def run(self, dry_run: bool = False, manual_push: Optional[bool] = None) -> bool:
        """
        Executes the safe commit pipeline.
        
        Args:
            dry_run: If True, performs safety checks and generates a message but does not execute git commands.
            manual_push: If True, overrides config.auto_push to force a push attempt. If False, overrides to prevent push.
        
        Returns:
            True if a commit was successfully created (or would have been in dry_run), False otherwise.
        """
        # Acquire the lock. If already held by a running pipeline, this will block and queue the execution.
        # This ensures that any changes occurring while a commit/push is active are not lost.
        logger.debug("Acquiring pipeline lock...")
        self._lock.acquire()
        try:
            return self._run_internal(dry_run, manual_push)
        except Exception as e:
            logger.error(f"Unexpected error in pipeline: {e}")
            return False
        finally:
            self._lock.release()

    def _run_internal(self, dry_run: bool, manual_push: Optional[bool]) -> bool:
        logger.info("\nChecking repository status...")
        
        # 1. Check Repo State
        if not self.safety.check_repo_state():
            return False
            
        # 2. Get Changed Files
        changed_files = self.git.get_changed_files()
        if not changed_files:
            logger.info("No relevant changes detected.")
            return False
            
        logger.info(f"{len(changed_files)} files changed.")
        
        # 3. Pre-Stage Safety Scan
        logger.info("Running pre-stage safety checks...")
        if not self.safety.pre_stage_scan(changed_files):
            logger.error("Pre-stage safety checks failed. Aborting.")
            return False
            
        if dry_run:
            logger.warning("[DRY RUN] Would stage the following files:")
            for f in changed_files:
                logger.info(f"  - {f}")
                
            msg = self.generator.generate(changed_files, "mock diff content")
            logger.warning(f"[DRY RUN] Proposed commit message:\n  {msg}")
            logger.warning("[DRY RUN] No Git commit or push was performed.")
            return True
            
        # 4. Stage Files
        logger.info("Staging changes...")
        self.git.stage_all()
        
        # 5. Post-Stage Safety Scan (Diff inspection)
        staged_files = self.git.get_staged_files()
        if not self.safety.post_stage_scan():
            logger.error("Post-stage safety checks failed! Unstaging files to protect user workspace...")
            # Unstage ONLY the files we just staged
            self.git.unstage_files(staged_files)
            return False
            
        # 6. Generate Commit Message
        diff_content = self.git.get_staged_diff()
        commit_msg = self.generator.generate(staged_files, diff_content)
        
        # 7. Commit
        logger.info(f"Generating commit message...\n\nCommit:\n{commit_msg}\n")
        try:
            self.git.commit(commit_msg)
            print_success("Commit created locally.")
        except GitError as e:
            logger.error(f"Failed to create commit: {e}")
            return False
            
        # 8. Push
        should_push = self.config.auto_push
        if manual_push is not None:
            should_push = manual_push
            
        if should_push:
            branch = self.git.get_current_branch()
            remote = self.config.remote
            logger.info(f"Attempting to push to {remote}/{branch}...")
            
            try:
                self.git.push(remote, branch)
                print_success(f"Pushed to {remote}/{branch}")
                count = self.stats.increment_push_count()
                logger.info(f"Total pushes today: {count}")
            except GitError as e:
                # We log the error, but we DON'T undo the commit! The commit is safe locally.
                logger.error(f"Push failed: {e}\nYour local commit was successful and remains intact.")
                
        return True
