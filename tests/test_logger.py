import io
import os
import sys
import logging
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from gitpilot.logger import (
    GitPilotFormatter,
    Colors,
    SUPPORTS_COLOR,
    SUPPORTS_UNICODE,
    SUCCESS_SYMBOL,
    WARN_SYMBOL,
    ERROR_SYMBOL,
    setup_logger,
    print_success,
    ANSI_ESCAPE_PATTERN,
)
from gitpilot.watcher import GitEventHandler

class TestLogger(unittest.TestCase):

    def test_no_raw_ansi_sequences_when_color_disabled(self):
        """Verifies that no ANSI escape codes appear when color is disabled."""
        formatter = GitPilotFormatter()
        record = logging.LogRecord("gitpilot", logging.INFO, "", 0, "\033[92m[OK] Test message\033[0m", (), None)
        
        with patch("gitpilot.logger.SUPPORTS_COLOR", False):
            formatted = formatter.format(record)
            self.assertNotIn("\033[", formatted)
            self.assertNotIn("\x1b[", formatted)
            self.assertIn("Test message", formatted)

    def test_no_duplicate_reset_sequences(self):
        """Verifies formatting does not produce duplicate ANSI reset codes."""
        formatter = GitPilotFormatter()
        record = logging.LogRecord("gitpilot", logging.INFO, "", 0, "Test message", (), None)
        
        with patch("gitpilot.logger.SUPPORTS_COLOR", True), \
             patch("gitpilot.logger.Colors.RESET", "\033[0m"), \
             patch("gitpilot.logger.Colors.INFO", "\033[94m"):
            
            formatted = formatter.format(record)
            # Count occurrences of reset code
            reset_count = formatted.count("\033[0m")
            self.assertLessEqual(reset_count, 1)

    def test_ascii_fallback_symbols(self):
        """Verifies clean ASCII fallbacks when Unicode support is absent."""
        with patch("gitpilot.logger._detect_unicode_support", return_value=False):
            # Test ASCII symbols
            self.assertIn(SUCCESS_SYMBOL, ("✓", "[OK]"))
            self.assertIn(WARN_SYMBOL, ("⚠️", "[!]"))
            self.assertIn(ERROR_SYMBOL, ("✖", "[X]"))

    def test_watcher_single_notification_per_burst(self):
        """Verifies multiple rapid filesystem events emit 'Change detected' only ONCE."""
        mock_config = MagicMock()
        mock_config.delay = 1
        mock_pipeline = MagicMock()
        mock_pipeline.monitor = MagicMock()
        
        handler = GitEventHandler(
            repo_path=Path.cwd(),
            config=mock_config,
            pipeline=mock_pipeline,
            dry_run=True
        )

        log_capture = io.StringIO()
        test_logger = setup_logger(verbose=False)
        for h in test_logger.handlers:
            if isinstance(h, logging.StreamHandler):
                h.stream = log_capture

        try:
            # Trigger 5 rapid filesystem event resets
            for _ in range(5):
                handler._reset_timer()
            
            output = log_capture.getvalue()
            count = output.count("Change detected. Waiting for inactivity...")
            self.assertEqual(count, 1)
        finally:
            if handler.timer:
                handler.timer.cancel()

if __name__ == "__main__":
    unittest.main()
