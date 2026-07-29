import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("gitpilot")

class PushTracker:
    """Tracks the number of successful pushes performed on the current date."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        git_dir = self.repo_path / ".git"
        if git_dir.exists() and git_dir.is_dir():
            self.stats_file = git_dir / "gitpilot_stats.json"
        else:
            self.stats_file = self.repo_path / ".gitpilot_stats.json"

    def _load_stats(self) -> dict:
        if not self.stats_file.exists():
            return {}
        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.debug(f"Failed to read stats file: {e}")
            return {}

    def _save_stats(self, data: dict) -> None:
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save stats file: {e}")

    def get_pushes_today(self) -> int:
        """Returns the number of pushes made today."""
        data = self._load_stats()
        today_str = date.today().isoformat()
        if data.get("date") == today_str:
            return int(data.get("pushes_today", 0))
        return 0

    def increment_push_count(self) -> int:
        """Increments today's push count by 1 and returns the updated count."""
        data = self._load_stats()
        today_str = date.today().isoformat()
        if data.get("date") == today_str:
            count = int(data.get("pushes_today", 0)) + 1
        else:
            count = 1

        self._save_stats({"date": today_str, "pushes_today": count})
        return count
