import os
import re
import logging
from pathlib import Path
from typing import List, Tuple
from gitpilot.config import GitPilotConfig
from gitpilot.git_manager import GitManager

logger = logging.getLogger("gitpilot")

class SafetyScanner:
    """
    Handles all safety checks for GitPilot to prevent catastrophic mistakes 
    like committing secrets, large files, or breaking merge states.
    """

    # Basic sensitive filename patterns
    SENSITIVE_FILENAMES = {
        ".env", ".env.local", ".env.production", ".env.development",
        "credentials.json", "service-account.json", "client_secret.json",
        "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"
    }

    SENSITIVE_EXTENSIONS = {
        ".pem", ".key", ".pkcs12", ".p12", ".pfx"
    }

    # High-confidence credential patterns (basic examples)
    # WARNING: This is NOT a replacement for dedicated secret scanners.
    SECRET_PATTERNS = [
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
        (r"-----BEGIN (?:RSA )?PRIVATE KEY-----", "Private Key Header"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
        (r"sk_live_[a-zA-Z0-9]{24,}", "Stripe Secret Key")
    ]

    def __init__(self, repo_path: Path, config: GitPilotConfig, git_manager: GitManager):
        self.repo_path = repo_path
        self.config = config
        self.git = git_manager

    def check_repo_state(self) -> bool:
        """
        Checks the overall health of the Git repository before attempting operations.
        Returns True if safe, False if unsafe.
        """
        if not self.git.is_git_repo():
            logger.error("Not a Git repository.")
            return False

        if self.git.is_detached_head():
            logger.error("Repository is in a detached HEAD state. Committing safely is not possible.")
            return False

        if self.git.has_merge_conflicts():
            logger.error("Repository has unresolved merge conflicts. Please resolve them manually.")
            return False

        user_name, user_email, _, identity_ok = self.git.get_user_identity()
        if not identity_ok:
            logger.error("Git identity is not configured. Automatic commits are paused.")
            logger.info("Configure your Git identity:")
            if not user_name:
                logger.info('    git config --global user.name "Your Name"')
            if not user_email:
                logger.info('    git config --global user.email "you@example.com"')
            return False

        return True


    def pre_stage_scan(self, files: List[str]) -> bool:
        """
        Scans files BEFORE they are staged to Git.
        Checks for sensitive filenames and large file sizes.
        Returns True if safe, False if unsafe.
        """
        if not files:
            return True

        is_safe = True
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024

        for file_path_str in files:
            # Handle deleted files (they won't exist on disk)
            full_path = self.repo_path / file_path_str
            if not full_path.exists():
                continue

            # 1. Check Filename
            file_name = full_path.name
            if file_name in self.SENSITIVE_FILENAMES or full_path.suffix in self.SENSITIVE_EXTENSIONS:
                logger.error(f"Safety Violation: Attempting to commit potentially sensitive file: '{file_path_str}'")
                is_safe = False

            # 2. Check File Size
            if full_path.is_file():
                file_size = full_path.stat().st_size
                if file_size > max_size_bytes:
                    logger.error(
                        f"Safety Violation: File '{file_path_str}' ({file_size / 1024 / 1024:.2f} MB) "
                        f"exceeds the configured limit of {self.config.max_file_size_mb} MB. "
                        "Consider using Git LFS or adding it to .gitignore."
                    )
                    is_safe = False

        return is_safe

    def post_stage_scan(self) -> bool:
        """
        Scans the currently staged diff for potential secrets inside the code.
        Returns True if safe, False if unsafe secrets are detected.
        """
        diff_content = self.git.get_staged_diff()
        if not diff_content:
            return True

        is_safe = True

        # Process line by line to accurately identify which file has the issue
        current_file = "Unknown"
        for line in diff_content.splitlines():
            # diff format indicates file start with "+++ b/filename"
            if line.startswith("+++ b/"):
                current_file = line[6:]
                continue
                
            # We only care about added/modified lines in the diff, which start with '+'
            # Ignore '+++' which are headers
            if line.startswith("+") and not line.startswith("+++"):
                for pattern, secret_type in self.SECRET_PATTERNS:
                    if re.search(pattern, line):
                        # DO NOT print the actual line or secret value!
                        logger.error(f"Safety Violation: Possible {secret_type} detected in '{current_file}'")
                        is_safe = False
                        
        return is_safe
