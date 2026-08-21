import logging
import os
import sys
import re
import ctypes

# Regex pattern for stripping ANSI escape sequences
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def _enable_windows_vt_support() -> bool:
    """Enables Virtual Terminal (VT) processing on Windows console if available."""
    if sys.platform != "win32":
        return True
    
    # Environment variables indicating native VT/ANSI support
    if any(k in os.environ for k in ("WT_SESSION", "VSCODE_PID", "TERM_PROGRAM", "ANSICON", "ConEmuANSI")):
        return True

    try:
        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        hOut = kernel32.GetStdHandle(-11)
        if hOut == 0 or hOut == -1:
            return False
        
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(hOut, ctypes.byref(mode)) == 0:
            return False
        
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if (mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING) == 0:
            new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            if kernel32.SetConsoleMode(hOut, new_mode) == 0:
                return False
        return True
    except Exception:
        return False

def _detect_color_support() -> bool:
    """Determines whether the terminal supports ANSI color output."""
    if "NO_COLOR" in os.environ or "--no-color" in sys.argv:
        return False
    
    is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    if not is_tty and not any(k in os.environ for k in ("WT_SESSION", "VSCODE_PID", "TERM_PROGRAM")):
        return False
        
    return _enable_windows_vt_support()

def _detect_unicode_support() -> bool:
    """Determines whether stdout can safely display Unicode symbols."""
    if sys.platform != "win32":
        return True
    if any(k in os.environ for k in ("WT_SESSION", "VSCODE_PID", "TERM_PROGRAM")):
        return True
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
        return sys.stdout.encoding.lower() in ("utf-8", "utf8")
    return False

SUPPORTS_COLOR = _detect_color_support()
SUPPORTS_UNICODE = _detect_unicode_support()

class Colors:
    if SUPPORTS_COLOR:
        RESET = "\033[0m"
        BOLD = "\033[1m"
        DEBUG = "\033[90m"      # Dark Gray
        INFO = "\033[94m"       # Blue
        SUCCESS = "\033[92m"    # Green
        WARNING = "\033[93m"    # Yellow
        ERROR = "\033[91m"      # Red
    else:
        RESET = ""
        BOLD = ""
        DEBUG = ""
        INFO = ""
        SUCCESS = ""
        WARNING = ""
        ERROR = ""

# Status Symbols (ASCII fallbacks when Unicode isn't safe)
SUCCESS_SYMBOL = "✓" if SUPPORTS_UNICODE else "[OK]"
WARN_SYMBOL = "[!]"
ERROR_SYMBOL = "[X]"

class GitPilotFormatter(logging.Formatter):
    """Custom logging formatter to provide clean, colored, or plain-text output without duplicate resets."""

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        msg = record.getMessage()

        # If color is not supported, strip any ANSI escape sequences from msg
        if not SUPPORTS_COLOR:
            msg = ANSI_ESCAPE_PATTERN.sub('', msg)

        # Select color based on log level
        if record.levelno == logging.DEBUG:
            color = Colors.DEBUG
        elif record.levelno == logging.INFO:
            color = ""
        elif record.levelno == logging.WARNING:
            color = Colors.WARNING
            if not msg.startswith(WARN_SYMBOL):
                record.levelname = f"{WARN_SYMBOL} WARNING:"
            else:
                record.levelname = "WARNING:"
        elif record.levelno >= logging.ERROR:
            color = Colors.ERROR
            if not msg.startswith(ERROR_SYMBOL):
                record.levelname = f"{ERROR_SYMBOL} ERROR:"
            else:
                record.levelname = "ERROR:"
        else:
            color = ""

        # Format message cleanly without double reset codes
        if record.levelno == logging.INFO:
            if color and Colors.RESET and not msg.endswith(Colors.RESET):
                formatted_msg = f"{color}{msg}{Colors.RESET}"
            else:
                formatted_msg = f"{color}{msg}"
        else:
            if color and Colors.RESET and not msg.endswith(Colors.RESET):
                formatted_msg = f"{color}{record.levelname} {msg}{Colors.RESET}"
            else:
                formatted_msg = f"{color}{record.levelname} {msg}"

        record.levelname = original_levelname
        return formatted_msg

def setup_logger(verbose: bool = False) -> logging.Logger:
    """Sets up the global gitpilot logger."""
    logger = logging.getLogger("gitpilot")
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(GitPilotFormatter())

    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

def print_success(message: str):
    """Helper function to print success messages cleanly."""
    logger = logging.getLogger("gitpilot")
    if Colors.SUCCESS and Colors.RESET:
        logger.info(f"{Colors.SUCCESS}{SUCCESS_SYMBOL} {message}{Colors.RESET}")
    else:
        logger.info(f"{SUCCESS_SYMBOL} {message}")

