# Testing GitPilot

This document outlines how to thoroughly test the GitPilot CLI application. It is divided into two sections: **Automated Unit Testing** (testing individual components) and **Manual End-to-End Testing** (simulating real-world usage).

---

## 1. Automated Unit Testing

GitPilot comes with a comprehensive suite of automated tests covering all core modules (`cli`, `config`, `git_manager`, `pipeline`, `safety`, `commit_generator`, `watcher`).

### Running the Test Suite

1. Open your terminal and navigate to the root of the `GitPilot` project.
2. Ensure you have the required dependencies installed:
   ```bash
   pip install -e .
   ```
3. Run the standard Python `unittest` discover command:
   ```bash
   # On Windows (PowerShell):
   $env:PYTHONPATH="."; python -m unittest discover -s tests -v

   # On Windows (Command Prompt / CMD):
   set PYTHONPATH=. && python -m unittest discover -s tests -v

   # On macOS / Linux:
   PYTHONPATH="." python -m unittest discover -s tests -v
   ```

**Expected Output**:
You should see output detailing the execution of all 37 tests, ending with:
```text
Ran 37 tests in X.XXXs

OK
```

> [!NOTE] 
> Because GitPilot executes shell commands (like `git`), the unit tests heavily use Python's `unittest.mock.patch` to simulate file system changes and Git outputs without actually modifying your environment.

---

## 2. Manual End-to-End Testing

To test GitPilot in a real environment without risking your actual project code, follow these steps to create an isolated "dummy" repository.

### Step 2.1: Setup a Dummy Repository
Open a new terminal window and run the following commands to create a safe sandbox:

```bash
# Create a new temporary directory
mkdir gitpilot-test-repo
cd gitpilot-test-repo

# Initialize a new Git repository
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Create an initial commit
echo "Hello GitPilot" > README.md
git add README.md
git commit -m "Initial commit"
```

### Step 2.2: Initialize GitPilot
Initialize the GitPilot configuration inside your dummy repository:

```bash
gitpilot init
```
*You should see a `gitpilot.json` file generated in the directory containing the default configuration.*

### Step 2.3: Test Manual Commit
Make a change to a file and use GitPilot to manually commit it:

```bash
echo "print('hello world')" > main.py
gitpilot commit
```
*Run `git log -1` to verify the commit was created with an automatically generated prefix (e.g., `feat: Update main.py...`).*

### Step 2.4: Test Watcher (Dry Run)
Test the background watcher safely using the `--dry-run` flag so it doesn't actually commit anything.

1. Start the watcher:
   ```bash
   gitpilot watch --dry-run
   ```
2. Open a second terminal window, navigate to the `gitpilot-test-repo`, and edit a file:
   ```bash
   echo "Adding a new feature" >> README.md
   ```
3. Watch the first terminal. After 120 seconds (the default delay), GitPilot will log a proposed commit message and indicate that no changes were made because it is in dry-run mode. 
*(Tip: You can change the `"delay"` in `gitpilot.json` to `5` seconds for faster testing).*

### Step 2.5: Test Safety Mechanisms (Secret Protection)
GitPilot is designed to block secrets from being committed.

1. Create a dummy secret file:
   ```bash
   echo "SECRET=123" > .env
   ```
2. Run a manual commit:
   ```bash
   gitpilot commit
   ```
3. **Expected Result**: GitPilot should log an error: `Safety Violation: Attempting to commit potentially sensitive file: '.env'` and abort the commit.

You can also test in-file secrets:
1. Delete the `.env` file.
2. Add a fake AWS key to your `main.py`:
   ```bash
   echo 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"' >> main.py
   ```
3. Run `gitpilot commit`.
4. **Expected Result**: GitPilot will stage the file, scan the diff, detect the AWS key, log a safety violation, and immediately unstage the file to protect you.

### Step 2.6: Test Safety Mechanisms (Large Files)
GitPilot blocks files over 50MB by default.

1. Generate a large dummy file (e.g., 55MB):
   ```bash
   # On Windows PowerShell:
   $file = [System.IO.File]::Create("large.bin"); $file.SetLength(55MB); $file.Close()
   
   # On macOS/Linux:
   dd if=/dev/zero of=large.bin bs=1M count=55
   ```
2. Run a manual commit:
   ```bash
   gitpilot commit
   ```
3. **Expected Result**: GitPilot will detect the file size and abort the commit, advising you to use Git LFS.

### Step 2.7: Test Push Failure Resilience
If GitPilot is configured to auto-push but the network is down or the remote is invalid, it should NOT lose your local commit.

1. Add a fake remote:
   ```bash
   git remote add origin https://invalid-url.com/fake/repo.git
   ```
2. Edit a file:
   ```bash
   echo "Push test" > test.txt
   ```
3. Trigger a commit and push:
   ```bash
   gitpilot commit --push
   ```
4. **Expected Result**: The console will show an error indicating the push failed, but it will specifically state `Your local commit was successful and remains intact.` 
Run `git log -1` to verify the commit exists locally!

---

### Step 2.8: Cleanup
When you are done testing, you can safely delete the dummy repository:
```bash
cd ..
# On Windows PowerShell:
Remove-Item -Recurse -Force gitpilot-test-repo

# On macOS/Linux:
rm -rf gitpilot-test-repo
```
..