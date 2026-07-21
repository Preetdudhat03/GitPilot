import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("gitpilot")

class GitPilotConfig:
    """Represents the GitPilot configuration settings."""
    def __init__(self, data: Dict[str, Any]):
        self.branch: str = str(data.get("branch", "main"))
        self.remote: str = str(data.get("remote", "origin"))
        self.watch: bool = bool(data.get("watch", True))
        
        # Ensure delay is an integer and reasonable (e.g. at least 1 second)
        try:
            self.delay: int = int(data.get("delay", 120))
            if self.delay < 1:
                self.delay = 1
        except ValueError:
            self.delay = 120
            
        self.auto_push: bool = bool(data.get("auto_push", False))
        
        # Maximum file size in MB before blocking a commit
        try:
            self.max_file_size_mb: int = int(data.get("max_file_size_mb", 50))
            if self.max_file_size_mb < 1:
                self.max_file_size_mb = 50
        except ValueError:
            self.max_file_size_mb = 50

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary format for saving."""
        return {
            "branch": self.branch,
            "remote": self.remote,
            "watch": self.watch,
            "delay": self.delay,
            "auto_push": self.auto_push,
            "max_file_size_mb": self.max_file_size_mb
        }


class ConfigManager:
    """Manages loading and saving the gitpilot configuration."""
    
    CONFIG_FILENAME = "gitpilot.json"

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.config_path = self.repo_path / self.CONFIG_FILENAME

    def load(self) -> GitPilotConfig:
        """
        Load configuration from gitpilot.json if it exists.
        If it doesn't exist or is invalid, return default configuration.
        """
        if not self.config_path.exists():
            logger.debug(f"Configuration file not found at {self.config_path}. Using defaults.")
            return GitPilotConfig({})

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logger.warning("Configuration file is not a valid JSON object. Using defaults.")
                    return GitPilotConfig({})
                return GitPilotConfig(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse configuration file (invalid JSON): {e}. Using defaults.")
            return GitPilotConfig({})
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}. Using defaults.")
            return GitPilotConfig({})

    def save(self, config: GitPilotConfig) -> None:
        """Save the given configuration to gitpilot.json."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.info(f"Configuration saved to {self.CONFIG_FILENAME}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
