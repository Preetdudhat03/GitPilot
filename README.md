# GitPilot

GitPilot is a smart, developer-productivity CLI tool that automatically watches a Git repository for file changes, waits until you stop typing (debouncing), and then safely stages, commits, and pushes your changes. 

The goal of this project is twofold:
1. **Save Time**: Stop typing `git add .`, `git commit -m "update"`, `git push` 50 times a day.
2. **Learn Python**: This project was built as an educational reference. Every core file in `gitpilot/` has a corresponding, highly detailed explanation file in `explanations/`.

## Features
- **Smart Debouncing**: Waits for a configurable period of inactivity before committing. Rapid saves group into one meaningful commit.
- **Safety First**: Never force pushes. Never deletes your local changes.
- **Pre-Stage Scanning**: Blocks accidental staging of large files (configurable MB limit) and sensitive filenames (e.g. `.env`, `.pem`).
- **Post-Stage Scanning**: Uses regex to scan the git diff for obvious secrets (AWS keys, private keys) before committing.
- **Conventional Commits**: Automatically generates meaningful commit messages (e.g., `feat: update cli.py`, `docs: update README.md`) instead of useless timestamps.
- **Dry-Run Mode**: Test the pipeline safely without altering your repository.

> **Disclaimer**: The secret scanning in GitPilot is basic and heuristic-based. It is **not** a replacement for enterprise secret-scanning tools (like GitGuardian or GitHub Advanced Security).

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/GitPilot.git
cd GitPilot

# 2. Install using pip (requires Python 3.8+)
pip install -e .
```
*Note: Installing with `-e` (editable mode) means if you modify the code while learning, the `gitpilot` command updates immediately!*

## Quick Start

Navigate into any git repository on your machine:
```bash
cd my-project

# Initialize the configuration
gitpilot init
```

*Important: If you do not want to share GitPilot settings with your team, add `gitpilot.json` to your `.gitignore` file.*

```bash
# Start watching for changes
gitpilot watch
```

## CLI Commands

- `gitpilot init`: Creates a `gitpilot.json` config file.
- `gitpilot watch`: Starts the background file watcher.
- `gitpilot watch --dry-run`: Runs the watcher, but simulates commits and prints the output instead of executing git operations.
- `gitpilot commit`: Manually triggers the safe commit pipeline immediately.
- `gitpilot commit --push`: Commits and then pushes to the remote.
- `gitpilot push`: Manually pushes local commits.
- `gitpilot status`: Prints the current configuration and repository status.

*(Add `-v` or `--verbose` to any command for debugging output).*

## Configuration

`gitpilot.json` is generated in the root of your repository:
```json
{
  "branch": "main",
  "remote": "origin",
  "watch": true,
  "delay": 120,
  "auto_push": false,
  "max_file_size_mb": 50
}
```
- **delay**: The inactivity period (in seconds) required before GitPilot triggers a commit.
- **auto_push**: If `true`, GitPilot will attempt to push after every automated commit.

## Project Architecture & Learning

If you are learning Python, start by reading `explanations/README.md` to understand the data flow. 
Then, read the source files and their corresponding explanations side-by-side:

1. `gitpilot/config.py` & `explanations/config_explanation.md`
2. `gitpilot/git_manager.py` & `explanations/git_manager_explanation.md`
3. `gitpilot/safety.py` & `explanations/safety_explanation.md`
4. `gitpilot/commit_generator.py` & `explanations/commit_generator_explanation.md`
5. `gitpilot/pipeline.py` & `explanations/pipeline_explanation.md`
6. `gitpilot/watcher.py` & `explanations/watcher_explanation.md`
7. `gitpilot/cli.py` & `explanations/cli_explanation.md`

## Testing

To run the automated test suite, execute:
```bash
# Set PYTHONPATH so the tests can import the gitpilot module
$env:PYTHONPATH="."  # (Windows PowerShell)
export PYTHONPATH="." # (Linux / macOS)

python -m unittest discover -s tests
```

## Known Limitations & V2 Ideas
- GitPilot does not automatically resolve merge conflicts. If a pull is required, GitPilot halts and waits for manual intervention.
- The rule-based commit generator is heuristic. V2 could integrate a local LLM or API (like OpenAI) to generate semantic commit messages based on diff analysis.
