import logging
import sys

# Define ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DEBUG = "\033[90m"      # Dark Gray
    INFO = "\033[94m"       # Blue
    SUCCESS = "\033[92m"    # Green
    WARNING = "\033[93m"    # Yellow
    ERROR = "\033[91m"      # Red

class GitPilotFormatter(logging.Formatter):
    """Custom logging formatter to provide colored output without cluttered stack traces."""

    def format(self, record: logging.LogRecord) -> str:
        # Save original levelname to restore later
        original_levelname = record.levelname
        
        # Colorize based on level
        if record.levelno == logging.DEBUG:
            color = Colors.DEBUG
        elif record.levelno == logging.INFO:
            # We don't generally prefix INFO messages to keep the CLI clean
            color = "" 
        elif record.levelno == logging.WARNING:
            color = Colors.WARNING
            record.levelname = f"⚠️ WARNING:"
        elif record.levelno >= logging.ERROR:
            color = Colors.ERROR
            record.levelname = f"✖ ERROR:"
        else:
            color = ""

        # Format message
        if record.levelno == logging.INFO:
            # For info, just print the message (clean CLI output)
            message = f"{color}{record.getMessage()}{Colors.RESET}"
        else:
            # For warning/error, prepend the level name
            message = f"{color}{record.levelname} {record.getMessage()}{Colors.RESET}"
        
        # Restore original levelname
        record.levelname = original_levelname
        
        return message

def setup_logger(verbose: bool = False) -> logging.Logger:
    """
    Sets up the global gitpilot logger.
    
    Args:
        verbose: If True, sets logging level to DEBUG. Otherwise INFO.
    """
    logger = logging.getLogger("gitpilot")
    
    # Avoid adding handlers multiple times if setup is called again
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Apply custom formatter
    formatter = GitPilotFormatter()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # Prevent propagation to the root logger
    logger.propagate = False
    
    return logger

def print_success(message: str):
    """Helper function to print success messages cleanly (e.g. with a checkmark)."""
    logger = logging.getLogger("gitpilot")
    logger.info(f"{Colors.SUCCESS}✓ {message}{Colors.RESET}")
