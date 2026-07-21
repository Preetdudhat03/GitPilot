# GitPilot Logger Module (`gitpilot/logger.py`)

## 1. Purpose of the file
This file configures Python's built-in `logging` module. By default, Python's `print()` function is useful, but it lacks structure. A proper CLI tool needs to differentiate between regular output, debugging information, warnings, and critical errors. This file sets up a specialized logger that formats text nicely with colors for the terminal, providing a professional user experience.

## 2. Imports explained
```python
import logging
import sys
```
- **`import logging`**: Python's powerful built-in logging library. It handles routing messages, filtering by severity (DEBUG, INFO, ERROR), and formatting.
- **`import sys`**: The sys module provides access to some variables used or maintained by the Python interpreter. We use it specifically for `sys.stdout` to tell the logger to print to the standard console output.

## 3. Classes explained

### `Colors`
**Purpose**: A simple container for ANSI escape codes.
- **What are ANSI codes?**: Terminals (like command prompt or bash) understand special sequences of characters as instructions to change text color. For example, `\033[91m` tells the terminal "make the following text red". `\033[0m` tells it "reset color back to normal".

### `GitPilotFormatter`
**Purpose**: This class inherits from `logging.Formatter`. It tells the logging system exactly what a log message should look like before it is printed to the screen.

**Why a custom formatter?**: We want our CLI to look clean. We don't want every normal message prefixed with `INFO:root:`. But if there is an error, we *do* want it clearly marked as an `ERROR` and colored red. The custom formatter contains the logic to format different severities differently.

## 4. Important lines explained line-by-line

```python
class GitPilotFormatter(logging.Formatter):
```
- `class ... (logging.Formatter)`: This is called **Inheritance**. It means `GitPilotFormatter` is a specialized version of Python's standard `logging.Formatter`.

```python
def format(self, record: logging.LogRecord) -> str:
```
- `format()` is a special method that the logging system calls automatically for every single message. It passes in a `LogRecord` (an object containing the message text, severity level, time, etc.), and expects a formatted string back.

```python
if record.levelno == logging.INFO:
    message = f"{color}{record.getMessage()}{Colors.RESET}"
```
- `record.levelno == logging.INFO`: Checks if this is a standard informational message.
- `f"..."`: This is an f-string (formatted string literal). It allows us to seamlessly inject variables into a string.
- Notice how we do not include `record.levelname` (which would be the word "INFO"). This keeps standard output clean.

```python
logger.propagate = False
```
- **Why is this needed?**: Python loggers are hierarchical. If you log a message on "gitpilot", it might bubble up to the "root" logger, causing the message to be printed twice! Setting `propagate = False` stops this bubbling.

## 5. Functions explained

### `setup_logger(verbose: bool = False)`
**Purpose**: Initializes and configures the logger. This should be called once when the CLI starts.
- **`verbose`**: A boolean. If true, the logger will print `DEBUG` messages (useful for developers). If false, it only prints `INFO` and above (for normal users).

### `print_success(message: str)`
**Purpose**: A tiny helper function. It just logs an `INFO` message but prepends a green checkmark (`✓`). This makes it easy for other parts of the application to print satisfying success messages.

## 6. Python Concepts Used
- **Inheritance**: Creating a specialized class based on a standard library class (`logging.Formatter`).
- **ANSI Escape Codes**: Low-level terminal manipulation for coloring.
- **F-Strings**: Modern Python string formatting.
- **Singletons/Globals**: `logging.getLogger("gitpilot")` always returns the exact same object everywhere in the application.

## 7. Error-handling behavior
The logger itself doesn't typically encounter errors. Its job is to cleanly present the errors that *other* modules encounter, ensuring stack traces aren't dumped onto the user unless explicitly requested.
