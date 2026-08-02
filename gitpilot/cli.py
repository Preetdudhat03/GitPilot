import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from gitpilot.config import ConfigManager
from gitpilot.logger import setup_logger, SUCCESS_SYMBOL
from gitpilot.git_manager import GitManager, GitError
from gitpilot.safety import SafetyScanner
from gitpilot.commit_generator import RuleBasedCommitGenerator
from gitpilot.pipeline import GitPilotPipeline
from gitpilot.watcher import GitPilotWatcher
from gitpilot.status import RepositoryState

def print_banner():
    banner = r"""
   _____ _ _    _____  _ _       _   
  / ____(_) |  |  __ \(_) |     | |  
 | |  __ _| |_ | |__) |_| | ___ | |_ 
 | | |_ | |  _||  ___/| | |/ _ \| __|
 | |__| | | |_ | |    | | | (_) | |_ 
  \_____|_|\__||_|    |_|_|\___/ \__|
                                  
    """
    print(banner)

def format_relative_time(timestamp: Optional[float]) -> str:
    """Formats a Unix timestamp into a human-readable relative time string."""
    if timestamp is None:
        return "Never"
    
    elapsed = time.time() - timestamp
    if elapsed < 5:
        return "Just now"
    elif elapsed < 60:
        return f"{int(elapsed)} seconds ago"
    elif elapsed < 3600:
        minutes = int(elapsed // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif elapsed < 86400:
        hours = int(elapsed // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))

def get_pipeline(repo_path: Path, verbose: bool = False) -> GitPilotPipeline:
    """Helper to initialize core components and return a configured Pipeline."""
    config_manager = ConfigManager(repo_path)
    config = config_manager.load()
    
    git = GitManager(repo_path)
    safety = SafetyScanner(repo_path, config, git)
    generator = RuleBasedCommitGenerator()
    return GitPilotPipeline(config, git, safety, generator)

def cmd_init(args, repo_path: Path):
    """Initializes a new GitPilot configuration in the current repository."""
    logger = setup_logger(args.verbose)
    config_manager = ConfigManager(repo_path)
    
    if config_manager.config_path.exists():
        logger.warning(f"{config_manager.CONFIG_FILENAME} already exists.")
        return
        
    default_config = config_manager.load()
    config_manager.save(default_config)
    
    logger.info(f"Initialized GitPilot configuration at {config_manager.config_path}")
    logger.warning("IMPORTANT: If you do not want to share this configuration with your team, "
                   "add 'gitpilot.json' to your .gitignore file.")

def cmd_watch(args, repo_path: Path):
    """Starts the file system watcher with automatic initial synchronization."""
    logger = setup_logger(args.verbose)
    pipeline = get_pipeline(repo_path, args.verbose)
    
    if not pipeline.git.is_git_repo():
        logger.error("Not a Git repository. Run 'git init' first.")
        sys.exit(1)
        
    print_banner()
    logger.info(f"{SUCCESS_SYMBOL} Repository detected")
    logger.info(f"{SUCCESS_SYMBOL} Watching branch: {pipeline.git.get_current_branch()}")
    logger.info(f"{SUCCESS_SYMBOL} Remote: {pipeline.config.remote}")
    logger.info(f"{SUCCESS_SYMBOL} Auto-push: {'enabled' if pipeline.config.auto_push else 'disabled'}")
    logger.info(f"{SUCCESS_SYMBOL} Auto-sync: {'enabled (' + pipeline.config.sync_strategy + ')' if pipeline.config.auto_sync else 'disabled'}")
    
    if args.dry_run:
        logger.warning("DRY RUN MODE ENABLED. No changes will be committed.")

    # Execute Automatic Initial Synchronization Check
    startup_status = pipeline.evaluate_startup()

    initial_mode = "active"
    if startup_status.state in (RepositoryState.BEHIND_REMOTE, RepositoryState.DIVERGED, RepositoryState.CONFLICT) or startup_status.has_conflicts:
        initial_mode = "limited"
        logger.warning("[!] Starting watcher in LIMITED (READ-ONLY) MODE.")
        logger.warning("    Automatic commits and pushes are paused until repository synchronization completes.")
        logger.info("    Run 'gitpilot sync' or resolve conflicts manually to activate automatic commits.")

    watcher = GitPilotWatcher(repo_path, pipeline.config, pipeline, dry_run=args.dry_run, initial_mode=initial_mode)
    watcher.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("")
        watcher.stop()
        logger.info("GitPilot stopped.")

def cmd_sync(args, repo_path: Path):
    """Manually triggers repository synchronization with remote."""
    logger = setup_logger(args.verbose)
    pipeline = get_pipeline(repo_path, args.verbose)
    
    if not pipeline.git.is_git_repo():
        logger.error("Not a Git repository.")
        sys.exit(1)
        
    logger.info(f"Synchronizing repository using strategy '{pipeline.config.sync_strategy}'...")
    sync_res = pipeline.synchronize()

    if sync_res.success:
        logger.info(f"{SUCCESS_SYMBOL} Synchronization successful using strategy '{sync_res.strategy}'.")
    else:
        logger.error(f"[X] Synchronization failed: {sync_res.error_message or 'Conflicts encountered.'}")
        if sync_res.conflicts:
            logger.error("Please resolve conflicts manually.")
        sys.exit(1)

def cmd_commit(args, repo_path: Path):
    """Manually triggers the commit pipeline once."""
    logger = setup_logger(args.verbose)
    pipeline = get_pipeline(repo_path, args.verbose)
    
    logger.info("Executing manual commit pipeline...")
    success = pipeline.run(dry_run=False, manual_push=args.push)
    if not success:
        logger.error("Commit pipeline did not complete successfully.")
        sys.exit(1)

def cmd_push(args, repo_path: Path):
    """Manually pushes local commits to the remote."""
    logger = setup_logger(args.verbose)
    pipeline = get_pipeline(repo_path, args.verbose)
    
    branch = pipeline.git.get_current_branch()
    logger.info(f"Pushing branch '{branch}' to '{pipeline.config.remote}'...")
    
    try:
        pipeline.git.push(pipeline.config.remote, branch)
        pipeline.monitor.record_push_telemetry(success=True)
        logger.info(f"{SUCCESS_SYMBOL} Push successful.")
    except GitError as e:
        pipeline.monitor.record_push_telemetry(success=False)
        logger.error(f"Push failed: {e}")
        sys.exit(1)

def cmd_status(args, repo_path: Path):
    """Displays the rich status dashboard for GitPilot and the repository."""
    logger = setup_logger(args.verbose)
    pipeline = get_pipeline(repo_path, args.verbose)
    
    if not pipeline.git.is_git_repo():
        logger.error("Not a git repository.")
        sys.exit(1)

    status = pipeline.monitor.refresh_status(fetch_first=False)
    
    print("=== GitPilot Developer Dashboard ===")
    print(f"Repository:          {repo_path.absolute()}")
    print(f"Branch:              {status.current_branch}")
    print(f"Remote:              {status.remote_name}/{status.remote_branch}")
    print(f"Repository State:    {status.state.value}")
    print(f"Ahead Commits:       {status.ahead_count}")
    print(f"Behind Commits:      {status.behind_count}")
    print(f"Auto-push:           {'Enabled' if pipeline.config.auto_push else 'Disabled'}")
    print(f"Auto-sync:           {'Enabled (' + pipeline.config.sync_strategy + ')' if pipeline.config.auto_sync else 'Disabled'}")
    print(f"Fetch Interval:      {pipeline.config.fetch_interval}s ({'Enabled' if pipeline.config.fetch_interval > 0 else 'Disabled'})")
    print(f"Last Fetch:          {format_relative_time(status.last_fetch)}")
    print(f"Last Status Refresh: {format_relative_time(status.last_status_refresh)}")
    print(f"Last Sync:           {format_relative_time(status.last_sync)}")
    push_str = format_relative_time(status.last_push)
    if status.last_push_status:
        push_str += f" ({status.last_push_status})"
    print(f"Last Push:           {push_str}")
    print(f"Pipeline Lock:       {'Locked' if pipeline._lock.locked() else 'Idle'}")

    try:
        changed = pipeline.git.get_changed_files()
        print(f"\nUncommitted changes: {'Yes' if changed else 'No'} ({len(changed)} files)")
    except GitError:
        print("\nCould not determine uncommitted changes.")

def cmd_config(args, repo_path: Path):
    """Gets or sets a configuration value with validation."""
    logger = setup_logger(args.verbose)
    config_manager = ConfigManager(repo_path)
    
    if not config_manager.config_path.exists():
        logger.error(f"No {config_manager.CONFIG_FILENAME} found. Run 'gitpilot init' first.")
        sys.exit(1)
        
    config = config_manager.load()
    key = args.key
    value = args.value
    
    if not hasattr(config, key):
        logger.error(f"Unknown configuration key: '{key}'. Available keys: {list(config.__dict__.keys())}")
        sys.exit(1)
        
    if value is None:
        current_val = getattr(config, key)
        print(f"{key} = {current_val}")
    else:
        current_val = getattr(config, key)
        try:
            if key == "sync_strategy":
                val_lower = str(value).lower()
                if val_lower not in ("merge", "rebase"):
                    logger.error(f"Invalid value for sync_strategy: '{value}'. Expected 'merge' or 'rebase'.")
                    sys.exit(1)
                new_val = val_lower
            elif isinstance(current_val, bool):
                lower_val = str(value).lower()
                if lower_val in ('true', '1', 'yes', 'y'):
                    new_val = True
                elif lower_val in ('false', '0', 'no', 'n'):
                    new_val = False
                else:
                    raise ValueError("Expected boolean (true/false)")
            elif isinstance(current_val, int):
                new_val = int(value)
                if new_val < 0:
                    raise ValueError("Must be a non-negative integer")
            else:
                new_val = value
                
            setattr(config, key, new_val)
            config_manager.save(config)
            logger.info(f"{SUCCESS_SYMBOL} Updated {key} to {new_val}")
        except ValueError as e:
            logger.error(f"Invalid value for {key}: {e}")
            sys.exit(1)

def main():
    epilog_text = """
Detailed Command Reference:

  init
    Initializes a new GitPilot configuration in the current repository.

  watch
    Starts the background watcher with Automatic Initial Synchronization.

  sync
    Manually triggers repository synchronization with remote.

  commit
    Manually triggers the safe commit pipeline.

  push
    Manually pushes existing local commits to the remote.

  status
    Displays the developer status dashboard.

  config <key> [value]
    Gets or sets configuration values (auto_push, auto_sync, sync_strategy, fetch_interval, etc.).
"""
    parser = argparse.ArgumentParser(
        description="GitPilot: A safe automated git commit watcher.",
        epilog=epilog_text,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose/debug output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)
    
    # Init
    subparsers.add_parser("init", help="Initialize gitpilot.json in the current directory")
    
    # Watch
    watch_parser = subparsers.add_parser("watch", help="Start watching the repository for changes")
    watch_parser.add_argument("--dry-run", action="store_true", help="Run without actually committing")
    
    # Sync (New in V1.1)
    subparsers.add_parser("sync", help="Manually synchronize repository with remote")
    
    # Status
    subparsers.add_parser("status", help="Show current git and gitpilot status")
    
    # Commit
    commit_parser = subparsers.add_parser("commit", help="Manually run the safe commit pipeline")
    commit_parser.add_argument("--push", action="store_true", help="Push to remote after committing")
    
    # Push
    subparsers.add_parser("push", help="Push existing local commits to the configured remote")
    
    # Config
    config_parser = subparsers.add_parser("config", help="Get or set a configuration value in gitpilot.json")
    config_parser.add_argument("key", help="The configuration key (e.g., auto_push, auto_sync, sync_strategy)")
    config_parser.add_argument("value", nargs="?", help="The value to set. If omitted, prints the current value.")

    args = parser.parse_args()
    repo_path = Path.cwd()

    try:
        if args.command == "init":
            cmd_init(args, repo_path)
        elif args.command == "watch":
            cmd_watch(args, repo_path)
        elif args.command == "sync":
            cmd_sync(args, repo_path)
        elif args.command == "status":
            cmd_status(args, repo_path)
        elif args.command == "commit":
            cmd_commit(args, repo_path)
        elif args.command == "push":
            cmd_push(args, repo_path)
        elif args.command == "config":
            cmd_config(args, repo_path)
    except Exception as e:
        logger = setup_logger(args.verbose)
        logger.debug(f"Unhandled exception: {e}", exc_info=True)
        logger.error("An unexpected error occurred. Use --verbose for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
