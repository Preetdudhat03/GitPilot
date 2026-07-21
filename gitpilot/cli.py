import argparse
import sys
import time
from pathlib import Path

from gitpilot.config import ConfigManager
from gitpilot.logger import setup_logger, SUCCESS_SYMBOL
from gitpilot.git_manager import GitManager, GitError
from gitpilot.safety import SafetyScanner
from gitpilot.commit_generator import RuleBasedCommitGenerator
from gitpilot.pipeline import GitPilotPipeline
from gitpilot.watcher import GitPilotWatcher

def print_banner():
    banner = """
   _____ _ _  _____  _ _       _   
  / ____(_) ||  __ \(_) |     | |  
 | |  __ _| || |__) |_| | ___ | |_ 
 | | |_ | | ||  ___/| | |/ _ \| __|
 | |__| | | || |    | | | (_) | |_ 
  \_____|_|\_|_|    |_|_|\___/ \__|
                                  
    """
    print(banner)

def get_pipeline(repo_path: Path, verbose: bool = False) -> GitPilotPipeline:
    """Helper to initialize the core components and return a configured Pipeline."""
    config_manager = ConfigManager(repo_path)
    config = config_manager.load()
    
    # We setup logger early in the main function, but passing verbose here ensures
    # the components logging at debug level will be seen if verbose is true.
    
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
        
    # We load default config and save it
    default_config = config_manager.load()
    config_manager.save(default_config)
    
    logger.info(f"Initialized GitPilot configuration at {config_manager.config_path}")
    logger.warning("IMPORTANT: If you do not want to share this configuration with your team, "
                   "add 'gitpilot.json' to your .gitignore file.")

def cmd_watch(args, repo_path: Path):
    """Starts the file system watcher."""
    logger = setup_logger(args.verbose)
    pipeline = get_pipeline(repo_path, args.verbose)
    
    # Check git repo first
    if not pipeline.git.is_git_repo():
        logger.error("Not a Git repository. Run 'git init' first.")
        sys.exit(1)
        
    print_banner()
    logger.info(f"{SUCCESS_SYMBOL} Repository detected")
    logger.info(f"{SUCCESS_SYMBOL} Watching branch: {pipeline.git.get_current_branch()}")
    logger.info(f"{SUCCESS_SYMBOL} Remote: {pipeline.config.remote}")
    logger.info(f"{SUCCESS_SYMBOL} Auto-push: {'enabled' if pipeline.config.auto_push else 'disabled'}")
    
    if args.dry_run:
        logger.warning("DRY RUN MODE ENABLED. No changes will be committed.")

    watcher = GitPilotWatcher(repo_path, pipeline.config, pipeline, dry_run=args.dry_run)
    watcher.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("") # newline after ^C
        watcher.stop()
        logger.info("GitPilot stopped.")

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
    config_manager = ConfigManager(repo_path)
    config = config_manager.load()
    git = GitManager(repo_path)
    
    branch = git.get_current_branch()
    logger.info(f"Pushing branch '{branch}' to '{config.remote}'...")
    
    try:
        git.push(config.remote, branch)
        logger.info(f"{SUCCESS_SYMBOL} Push successful.")
    except GitError as e:
        logger.error(f"Push failed: {e}")
        sys.exit(1)

def cmd_status(args, repo_path: Path):
    """Displays the current status of GitPilot and the repository."""
    logger = setup_logger(args.verbose)
    config_manager = ConfigManager(repo_path)
    config = config_manager.load()
    git = GitManager(repo_path)
    
    if not git.is_git_repo():
        logger.error("Not a git repository.")
        sys.exit(1)
        
    print("=== GitPilot Status ===")
    print(f"Repository:   {repo_path.absolute()}")
    print(f"Branch:       {git.get_current_branch()}")
    print(f"Remote:       {config.remote}")
    print(f"Auto-push:    {config.auto_push}")
    print(f"Watch delay:  {config.delay} seconds")
    print(f"Max file size:{config.max_file_size_mb} MB")
    
    try:
        changed = git.get_changed_files()
        print(f"\nUncommitted changes: {'Yes' if changed else 'No'} ({len(changed)} files)")
    except GitError:
        print("\nCould not determine uncommitted changes.")

def cmd_config(args, repo_path: Path):
    """Gets or sets a configuration value."""
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
        # Get Mode
        current_val = getattr(config, key)
        print(f"{key} = {current_val}")
    else:
        # Set Mode
        current_val = getattr(config, key)
        try:
            if isinstance(current_val, bool):
                lower_val = value.lower()
                if lower_val in ('true', '1', 'yes', 'y'):
                    new_val = True
                elif lower_val in ('false', '0', 'no', 'n'):
                    new_val = False
                else:
                    raise ValueError("Expected boolean (true/false)")
            elif isinstance(current_val, int):
                new_val = int(value)
            else:
                new_val = value
                
            setattr(config, key, new_val)
            config_manager.save(config)
            logger.info(f"{SUCCESS_SYMBOL} Updated {key} to {new_val}")
        except ValueError as e:
            logger.error(f"Invalid value for {key}: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="GitPilot: A safe automated git commit watcher.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose/debug output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)
    
    # Init
    subparsers.add_parser("init", help="Initialize gitpilot.json in the current directory")
    
    # Watch
    watch_parser = subparsers.add_parser("watch", help="Start watching the repository for changes")
    watch_parser.add_argument("--dry-run", action="store_true", help="Run without actually committing")
    
    # Status
    subparsers.add_parser("status", help="Show current git and gitpilot status")
    
    # Commit
    commit_parser = subparsers.add_parser("commit", help="Manually run the safe commit pipeline")
    commit_parser.add_argument("--push", action="store_true", help="Push to remote after committing")
    
    # Push
    subparsers.add_parser("push", help="Push existing local commits to the configured remote")
    
    # Config
    config_parser = subparsers.add_parser("config", help="Get or set a configuration value in gitpilot.json")
    config_parser.add_argument("key", help="The configuration key (e.g., auto_push, delay, branch)")
    config_parser.add_argument("value", nargs="?", help="The value to set. If omitted, prints the current value.")

    args = parser.parse_args()
    repo_path = Path.cwd()

    try:
        if args.command == "init":
            cmd_init(args, repo_path)
        elif args.command == "watch":
            cmd_watch(args, repo_path)
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
