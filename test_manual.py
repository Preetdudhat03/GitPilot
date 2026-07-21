import os
import time
import subprocess
import tempfile
from pathlib import Path

# Setup temp repo
with tempfile.TemporaryDirectory() as tmpdir:
    os.chdir(tmpdir)
    subprocess.run(['git', 'init'], check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'test'], check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], check=True)
    
    print('\n--- Testing Push Failure ---')
    Path('push_fail.txt').write_text('test')
    subprocess.run(['git', 'add', '.'])
    subprocess.run(['git', 'commit', '-m', 'initial'])
    
    Path('push_fail.txt').write_text('updated')
    subprocess.run(['python', '-m', 'gitpilot.cli', 'init'], check=True)
    
    res = subprocess.run(['python', '-m', 'gitpilot.cli', 'commit', '--push'], capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
    
    log = subprocess.run(['git', 'log', '-1', '--oneline'], capture_output=True, text=True)
    print('Latest commit:', log.stdout.strip())
    
    print('\n--- Testing Secret Protection ---')
    Path('.env').write_text('SECRET=123')
    res = subprocess.run(['python', '-m', 'gitpilot.cli', 'commit'], capture_output=True, text=True)
    print("STDERR (.env):", res.stderr)
    Path('.env').unlink()
    
    Path('config.py').write_text('AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"')
    res = subprocess.run(['python', '-m', 'gitpilot.cli', 'commit'], capture_output=True, text=True)
    print("STDERR (config.py):", res.stderr)
    
    status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    print('Git Status:\n' + status.stdout)

    print('\n--- Testing Large File Protection ---')
    with open('large.bin', 'wb') as f:
        f.write(os.urandom(1024 * 1024 * 51)) # 51MB (max is 50MB by default config)
    res = subprocess.run(['python', '-m', 'gitpilot.cli', 'commit'], capture_output=True, text=True)
    print("STDERR (large file):", res.stderr)

    print('\n--- Testing Dry Run ---')
    # Start watch --dry-run as subprocess, write file, wait 3 seconds, kill it
    Path('config.py').unlink()
    Path('large.bin').unlink()
    Path('gitpilot.json').write_text('{"delay": 1, "auto_push": false, "max_file_size_mb": 50, "watch": true, "branch": "master", "remote": "origin"}')
    Path('dryrun.txt').write_text('dry run test')
    
    proc = subprocess.Popen(['python', '-m', 'gitpilot.cli', 'watch', '--dry-run'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    Path('dryrun.txt').write_text('modified')
    time.sleep(3)
    proc.terminate()
    stdout, stderr = proc.communicate()
    print("STDOUT (dry run):", stdout)
    print("STDERR (dry run):", stderr)
