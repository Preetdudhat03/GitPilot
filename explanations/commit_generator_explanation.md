# Commit Message Generator Module (`gitpilot/commit_generator.py`)

## 1. Purpose of the file
This module creates automatic commit messages for the changes the user has made. Git requires a commit message, but the goal of GitPilot is to prevent the user from typing `git commit -m "update"`.

To keep the repository history clean, GitPilot attempts to generate messages following the **Conventional Commits** specification (e.g., `feat: update file`, `fix: update file`).

## 2. Imports explained
```python
import abc
from typing import List
import re
```
- **`import abc`**: Stands for Abstract Base Classes. It's a Python module used to define interfaces. We use it to ensure that any future commit generators (like an AI generator) implement the exact same methods as our basic rule-based one.

## 3. Classes explained

### `CommitMessageGenerator` (Abstract Base Class)
**Purpose**: Defines the "contract" for what a commit generator must look like.
```python
class CommitMessageGenerator(abc.ABC):
    @abc.abstractmethod
    def generate(self, staged_files: List[str], diff_content: str) -> str:
        pass
```
- By inheriting from `abc.ABC` and using the `@abc.abstractmethod` decorator, Python will throw an error if a developer tries to instantiate this class directly. 
- It forces any subclass (like `RuleBasedCommitGenerator`) to actually write the code for the `generate` function. This makes it trivial to swap in an `AICommitGenerator` in Version 2.

### `RuleBasedCommitGenerator`
**Purpose**: The concrete implementation for Version 1. It uses simple heuristics (rules of thumb) to guess what the user did.

## 4. Important lines explained line-by-line

```python
has_tests = any("test" in f.lower() for f in staged_files)
```
- `any(...)`: A built-in Python function that returns `True` if at least one item in the provided iterable is `True`.
- `"test" in f.lower() for f in staged_files`: This is a generator expression. It loops through every filename, converts it to lowercase, and checks if the word "test" is in it.

```python
elif has_python:
    diff_lower = diff_content.lower()
    if "bug" in diff_lower or "fix" in diff_lower or "error" in diff_lower:
        prefix = "fix"
```
- If Python files were changed, we look at the actual code changes (`diff_content`).
- If the developer wrote the word "bug", "fix", or "error" anywhere in their code (like in a comment or a variable name), we assume this commit is a `fix`. Otherwise, we assume it's a new feature (`feat`). 
- *Note: This is a very basic heuristic, but it provides significantly better history than defaulting to `update` for everything.*

```python
elif file_count < 4:
    file_names = [f.split('/')[-1] for f in staged_files]
    subject = f"update {', '.join(file_names)}"
```
- If 2 or 3 files changed, we list their names.
- `f.split('/')[-1]`: Splits the file path by slashes and grabs the very last element (the filename itself). E.g., `gitpilot/watcher.py` becomes `watcher.py`.
- `', '.join(file_names)`: Turns the list `['cli.py', 'watcher.py']` into the string `"cli.py, watcher.py"`.

## 5. Data Flow & Execution
1. The Pipeline stages files safely.
2. The Pipeline asks the GitManager for the list of staged files and the raw diff.
3. The Pipeline passes these to `generator.generate()`.
4. The generator inspects the files, decides on a prefix (`feat`, `fix`, `docs`, `chore`, `test`), creates a short summary, and returns it as a string.
5. The Pipeline passes that string back to GitManager to finalize the commit.
