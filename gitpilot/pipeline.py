import logging
import threading
from typing import Optional

from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager, GitError
from gitpilot.safety import SafetyScanner
from gitpilot.commit_generator import CommitMessageGenerator
from gitpilot.logger import print_success
from gitpilot.status import RepositoryState, RepositoryStatus, SyncResult
from gitpilot.monitor import RepositoryMonitor

logger = logging.getLogger("gitpilot")

class GitPilotPipeline:
    """
    Coordinates the entire GitPilot workflow safely.
    Ensures only one operation happens at a time using a threading Lock.
    """
    
    def __init__(self, 
                 config: GitPilotConfig, 
                 git: GitManager, 
                 safety: SafetyScanner, 
                 generator: CommitMessageGenerator,
                 monitor: Optional[RepositoryMonitor] = None):
        self.config = config
        self.git = git
        self.safety = safety
        self.generator = generator
        
        # Lock to prevent concurrent Git pipeline operations
        self._lock = threading.Lock()
        self.monitor = monitor or RepositoryMonitor(git.repo_path, config, git, pipeline_lock=self._lock)

    def run(self, dry_run: bool = False, manual_push: Optional[bool] = None) -> bool:
        """
        Executes the safe commit pipeline.
        """
        logger.debug("Acquiring pipeline lock...")
        with self._lock:
            try:
                return self._run_internal(dry_run, manual_push)
            except Exception as e:
                logger.error(f"Unexpected error in pipeline: {e}")
                return False

    def synchronize(self, remote: Optional[str] = None, branch: Optional[str] = None, strategy: Optional[str] = None) -> SyncResult:
        """
        Runs synchronization (merge or rebase) against remote.
        Thread-safe method using the pipeline lock.
        """
        remote_name = remote or self.config.remote
        branch_name = branch or self.git.get_current_branch()
        sync_strat = strategy or self.config.sync_strategy

        with self._lock:
            return self._synchronize_internal(remote_name, branch_name, sync_strat)

    def _synchronize_internal(self, remote: str, branch: str, strategy: str) -> SyncResult:
        """Internal lock-held synchronization implementation."""
        # Step 1: Fetch
        self.git.fetch_remote(remote, branch)

        # Step 2: Sync execution based on strategy
        if strategy == "rebase":
            result = self.git.rebase_remote(remote, branch)
        else:
            result = self.git.merge_remote(remote, branch)

        if result.success:
            self.monitor.record_sync_telemetry()

        self.monitor.refresh_status(fetch_first=False)
        return result

    def evaluate_startup(self) -> RepositoryStatus:
        """
        Evaluates startup synchronization state before watching.
        If repository is behind or diverged and auto_sync is enabled, attempts sync.
        """
        with self._lock:
            remote = self.config.remote
            branch = self.git.get_current_branch()

            logger.info("Checking repository synchronization...")
            status = self.monitor.refresh_status(fetch_first=True)

            if status.state in (RepositoryState.BEHIND_REMOTE, RepositoryState.DIVERGED):
                logger.info(f"Repository is {status.state.value.lower().replace('_', ' ')} relative to {remote}/{branch}.")
                if not self.config.auto_sync:
                    logger.warning("Auto Sync is disabled. Please synchronize manually before enabling active mode.")
                    return status

                logger.info("Checking Auto Sync configuration...")
                print_success("Auto Sync enabled.")
                logger.info("Fetching latest changes...")
                print_success("Fetch completed.")
                logger.info(f"Synchronizing using {self.config.sync_strategy}...")

                sync_res = self._synchronize_internal(remote, branch, self.config.sync_strategy)
                if sync_res.success:
                    print_success("Synchronization completed.")
                    return self.monitor.refresh_status(fetch_first=False)
                else:
                    if sync_res.strategy == "rebase":
                        logger.error("[X] Rebase conflict detected. Aborted rebase and restored repository state.")
                    else:
                        logger.error("[X] Merge conflict detected.")
                    logger.error("Automatic synchronization stopped. Resolve the conflicts manually.")
                    return self.monitor.refresh_status(fetch_first=False)

            elif status.state == RepositoryState.UP_TO_DATE:
                print_success("Repository is already synchronized.")

            return status

    def _run_internal(self, dry_run: bool, manual_push: Optional[bool]) -> bool:
        logger.info("\nChecking repository status...")
        self.monitor.notify_activity()
        
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

        # Refresh monitor after commit
        self.monitor.refresh_status(fetch_first=False)
            
        # 8. Push with Auto Sync
        should_push = self.config.auto_push
        if manual_push is not None:
            should_push = manual_push
            
        if should_push:
            branch = self.git.get_current_branch()
            remote = self.config.remote
            logger.info(f"Attempting to push to {remote}/{branch}...")
            self._push_with_auto_sync(remote, branch)

        return True

    def _push_with_auto_sync(self, remote: str, branch: str) -> bool:
        """Handles pushing and Intelligent Auto Sync if push is rejected due to remote ahead."""
        try:
            self.git.push(remote, branch)
            print_success(f"Pushed to {remote}/{branch}")
            self.monitor.record_push_telemetry(success=True)
            self.monitor.refresh_status(fetch_first=False)
            return True
        except GitError as e:
            error_str = str(e)
            reason = self.git.classify_push_error(error_str)

            if reason == "REMOTE_AHEAD":
                logger.error("[X] Push rejected.")
                logger.error("Remote branch is ahead.")
                logger.info("Checking Auto Sync...")

                if self.config.auto_sync:
                    print_success("Auto Sync enabled.")
                    logger.info("Fetching latest changes...")
                    print_success("Fetch completed.")
                    logger.info(f"Synchronizing using {self.config.sync_strategy}...")

                    sync_res = self._synchronize_internal(remote, branch, self.config.sync_strategy)
                    if sync_res.success:
                        print_success("Synchronization completed.")
                        logger.info("Retrying push...")
                        try:
                            self.git.push(remote, branch)
                            print_success("Push successful.")
                            self.monitor.record_push_telemetry(success=True)
                            self.monitor.refresh_status(fetch_first=False)
                            return True
                        except GitError as push_err:
                            logger.error(f"[X] Retried push failed: {push_err}")
                            self.monitor.record_push_telemetry(success=False)
                            return False
                    else:
                        if sync_res.strategy == "rebase":
                            logger.error("[X] Rebase conflict detected. Aborted rebase and restored repository state.")
                        else:
                            logger.error("[X] Merge conflict detected.")
                        logger.error("Automatic synchronization stopped. Resolve the conflicts manually.")
                        logger.info("Your local commit remains safe.")
                        self.monitor.record_push_telemetry(success=False)
                        return False
                else:
                    logger.error("Auto Sync is disabled. You must pull and merge changes manually.")
                    logger.info("Your local commit remains safe.")
                    self.monitor.record_push_telemetry(success=False)
                    return False
            else:
                logger.error(f"[X] Push failed: {error_str}\nYour local commit was successful and remains intact.")
                self.monitor.record_push_telemetry(success=False)
                return False
