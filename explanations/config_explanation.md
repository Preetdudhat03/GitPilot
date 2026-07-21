# GitPilot Configuration Module (`gitpilot/config.py`)

## 1. Purpose of the file
This file is responsible for managing GitPilot's configuration. It provides a way to read configuration values from a `gitpilot.json` file located in the user's project repository and save them back if necessary. It ensures that the rest of the application always has valid, usable settings, even if the user provides an invalid file or no file at all.

## 2. Imports explained
```python
import json
import logging
from pathlib import Path
from typing import Any, Dict
```
- **`import json`**: This is Python's built-in module for parsing (reading) and stringifying (writing) JSON data. We use it to read the `gitpilot.json` file.
- **`import logging`**: Python's built-in logging module. We use it to record warnings or errors (like "invalid JSON file") without crashing the app.
- **`from pathlib import Path`**: `pathlib` provides an object-oriented way to work with filesystem paths. It is much safer and cleaner than using raw strings and `os.path.join()`.
- **`from typing import Any, Dict`**: These are Type Hints. They don't change how the code runs, but they tell developers (and tools) what kind of data to expect. `Dict` means a Dictionary, and `Any` means any data type.

## 3. Classes explained

### `GitPilotConfig`
**Purpose**: This is a simple container class (often called a Data Object). Instead of passing around a raw Python dictionary containing configuration values throughout our application, we convert it into a `GitPilotConfig` object. 

**Why a class?**: It provides a concrete structure. We can safely do `config.branch` instead of `config.get("branch", "main")` everywhere in our app. It also acts as the central place to define defaults.

### `ConfigManager`
**Purpose**: This class handles the actual reading and writing of the JSON file on the hard drive. 

**Why a class?**: It encapsulates the file system logic. The rest of the application just asks the `ConfigManager` to `load()` the config, without needing to know *where* or *how* it's stored.

## 4. Important lines explained line-by-line

```python
self.branch: str = str(data.get("branch", "main"))
```
- `data.get("branch", "main")`: This asks the dictionary `data` for the key `"branch"`. If the key doesn't exist, it returns the default value `"main"`.
- `str(...)`: We wrap it in `str()` to guarantee it is a string. If the user accidentally put a number `123` as their branch name in JSON, this prevents the app from crashing later.
- `self.branch: str =`: We assign it to an instance variable (`self.branch`) and hint that it is a string (`: str`).

```python
try:
    self.delay: int = int(data.get("delay", 120))
    if self.delay < 1:
        self.delay = 1
except ValueError:
    self.delay = 120
```
- **Why is this needed?**: The user might have typed `"delay": "two minutes"` in their JSON file. `int("two minutes")` will crash Python with a `ValueError`.
- **`try` / `except ValueError`**: We attempt to convert the delay to an integer. If it fails, Python jumps to the `except` block, and we safely assign the default `120`. We also ensure the delay is never less than 1 second to prevent the app from frantically looping.

```python
def load(self) -> GitPilotConfig:
```
- `def load(self)`: Defines a method on the `ConfigManager` class. `self` is a reference to the specific instance of the class being called.
- `-> GitPilotConfig`: This is a return type hint. It means "this method will always return an instance of `GitPilotConfig`".

```python
if not self.config_path.exists():
    logger.debug(...)
    return GitPilotConfig({})
```
- `self.config_path.exists()`: Uses `pathlib` to check if the file is actually on the hard drive.
- `return GitPilotConfig({})`: If there is no file, we create a new config object passing an empty dictionary. The `GitPilotConfig` class will automatically fill in all the default values!

## 5. Data Flow & Execution
1. The application starts.
2. It finds the current repository path and creates `manager = ConfigManager(repo_path)`.
3. It calls `config = manager.load()`.
4. `load()` checks if `gitpilot.json` exists.
5. If yes, it reads it with `json.load()`.
6. It passes the dictionary to `GitPilotConfig(data)`.
7. `GitPilotConfig` reads the dictionary, applies defaults for missing fields, sanitizes invalid data (like negative delays), and creates an object.
8. The application now uses `config.branch`, `config.delay`, etc.

## 6. Error-handling behavior
The file is designed to **never crash**. 
- Missing file? Returns defaults.
- Bad JSON syntax? Logs an error and returns defaults.
- JSON is a list instead of a dictionary? Logs a warning and returns defaults.
- Values are the wrong type (e.g. string instead of int)? Falls back to default values for those specific fields.
