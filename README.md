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

## CLI Commands & Parameters

GitPilot uses a simple command structure: `gitpilot [global parameters] <command> [command parameters]`

### Global Parameters
Available on all commands:
| Parameter | Short | Description |
| :--- | :--- | :--- |
| `--verbose` | `-v` | Enables detailed debug logging for troubleshooting. |
| `--help` | `-h` | Displays the help manual and available arguments. |

### Commands

#### `init`
Creates the `gitpilot.json` configuration file in the current directory.
- **Usage:** `gitpilot init`
- **Parameters:** None

#### `watch`
Starts the background file system watcher. It will automatically commit changes after the configured delay.
- **Usage:** `gitpilot watch [parameters]`
- **Parameters:**
  - `--dry-run`: Simulates the watcher and pipeline without actually executing any Git commands. Excellent for testing your safety rules and commit generation.

#### `commit`
Manually triggers the safe commit pipeline exactly once.
- **Usage:** `gitpilot commit [parameters]`
- **Parameters:**
  - `--push`: Overrides the `auto_push` configuration to forcefully push the commit to the remote repository if the commit is successful.

#### `push`
Manually pushes existing local commits to the configured remote branch.
- **Usage:** `gitpilot push`
- **Parameters:** None

#### `status`
Displays the current GitPilot configuration, repository health, and uncommitted file count.
- **Usage:** `gitpilot status`
- **Parameters:** None

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
