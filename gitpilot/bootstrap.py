"""
GitPilot Environment Bootstrap & Diagnostic System (V1.2)
Provides environment inspection (gitpilot doctor) and safe, idempotent setup/repair (gitpilot setup).
"""

import os
import sys
import shutil
import sysconfig
import subprocess
import importlib.util
import importlib.metadata
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import winreg
except ImportError:
    winreg = None

@dataclass
class EnvironmentStatus:
    python_version: str
    python_path: str
    python_ok: bool
    python_min_req: str
    is_venv: bool
    venv_path: Optional[str]
    pip_available: bool
    pip_version: Optional[str]
    git_available: bool
    git_version: Optional[str]
    git_path: Optional[str]
    is_source_tree: bool
    package_installed: bool
    package_version: Optional[str]
    watchdog_installed: bool
    watchdog_version: Optional[str]
    scripts_dir: str
    gitpilot_exec_path: Optional[str]
    cli_in_path: bool
    user_path_configured: bool
    user_path_restricted: bool
    module_mode_working: bool

@dataclass
class SetupResult:
    success: bool
    exit_code: int
    status: EnvironmentStatus
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    actions_performed: List[str] = field(default_factory=list)
    fallback_available: bool = True

def parse_pyproject_python_version(pyproject_path: Path) -> str:
    """Reads requires-python from pyproject.toml as single source of truth."""
    default_version = ">=3.8"
    if not pyproject_path.exists():
        return default_version
    try:
        content = pyproject_path.read_text(encoding="utf-8")
        match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return default_version

def get_project_dependencies(pyproject_path: Optional[Path] = None) -> List[str]:
    """
    Derives required dependencies dynamically from installed package metadata or pyproject.toml.
    Prevents hardcoding dependency lists inside bootstrap logic.
    """
    deps = []
    try:
        reqs = importlib.metadata.requires("GitPilot")
        if reqs:
            return list(reqs)
    except Exception:
        pass

    if pyproject_path and pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                raw_deps = match.group(1)
                for item in re.findall(r'["\']([^"\']+)["\']', raw_deps):
                    deps.append(item.strip())
        except Exception:
            pass

    return deps or ["watchdog>=3.0.0"]

def check_python_req(version_str: str) -> bool:
    """Validates python version against standard requirement (e.g. >=3.8)."""
    current = sys.version_info[:2]
    match = re.search(r'>=\s*(\d+)\.(\d+)', version_str)
    if match:
        req_major, req_minor = int(match.group(1)), int(match.group(2))
        return current >= (req_major, req_minor)
    return current >= (3, 8)


class EnvironmentInspector:
    """Read-only environment diagnostic inspector for 'gitpilot doctor'."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()

    def inspect_environment(self) -> EnvironmentStatus:
        # Python check
        pyproject_file = self.project_root / "pyproject.toml"
        python_min_req = parse_pyproject_python_version(pyproject_file)
        python_version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        python_ok = check_python_req(python_min_req)
        python_path = sys.executable

        # Virtualenv check
        is_venv = (sys.prefix != sys.base_prefix) or ("VIRTUAL_ENV" in os.environ)
        venv_path = sys.prefix if is_venv else None

        # Pip check
        pip_available = False
        pip_version = None
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                pip_available = True
                pip_version = res.stdout.strip().split()[1] if len(res.stdout.strip().split()) > 1 else "detected"
        except Exception:
            pip_available = False

        # Git check
        git_available = False
        git_version = None
        git_path = shutil.which("git")
        try:
            res = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                git_available = True
                git_version = res.stdout.strip().replace("git version", "").strip()
        except Exception:
            git_available = False

        # Source tree check
        is_source_tree = False
        if pyproject_file.exists():
            try:
                content = pyproject_file.read_text(encoding="utf-8")
                if 'name = "GitPilot"' in content or "name = 'GitPilot'" in content:
                    is_source_tree = True
            except Exception:
                pass

        # Package check
        package_installed = False
        package_version = None
        try:
            package_version = importlib.metadata.version("GitPilot")
            package_installed = True
        except Exception:
            # Fallback check if importable
            if importlib.util.find_spec("gitpilot") is not None:
                package_installed = True
                package_version = "source/local"

        # Watchdog dependency check
        watchdog_installed = False
        watchdog_version = None
        try:
            watchdog_version = importlib.metadata.version("watchdog")
            watchdog_installed = True
        except Exception:
            if importlib.util.find_spec("watchdog") is not None:
                watchdog_installed = True
                watchdog_version = "available"

        # Scripts directory & GitPilot executable detection
        scripts_dir = sysconfig.get_path("scripts")
        if not scripts_dir or not os.path.exists(scripts_dir):
            # Fallback for user base scripts on POSIX/Windows if needed
            if hasattr(sys, 'user_base'):
                user_scripts = os.path.join(sys.user_base, 'Scripts' if sys.platform == 'win32' else 'bin')
                if os.path.exists(user_scripts):
                    scripts_dir = user_scripts

        exec_name = "gitpilot.exe" if sys.platform == "win32" else "gitpilot"
        gitpilot_exec_path = None
        
        # Check standard places for gitpilot executable
        found_which = shutil.which("gitpilot")
        if found_which:
            gitpilot_exec_path = found_which
        elif scripts_dir and os.path.exists(os.path.join(scripts_dir, exec_name)):
            gitpilot_exec_path = os.path.join(scripts_dir, exec_name)

        # CLI PATH check
        cli_in_path = False
        if scripts_dir:
            norm_scripts = os.path.normcase(os.path.normpath(scripts_dir))
            env_paths = [os.path.normcase(os.path.normpath(p)) for p in os.environ.get("PATH", "").split(os.pathsep) if p]
            if norm_scripts in env_paths or (gitpilot_exec_path and shutil.which("gitpilot")):
                cli_in_path = True

        # User PATH registry check (Windows)
        user_path_configured = False
        user_path_restricted = False
        if sys.platform == "win32" and winreg and scripts_dir:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as key:
                    try:
                        user_path_val, _ = winreg.QueryValueEx(key, "Path")
                        norm_user_paths = [os.path.normcase(os.path.normpath(p)) for p in user_path_val.split(";") if p]
                        if os.path.normcase(os.path.normpath(scripts_dir)) in norm_user_paths:
                            user_path_configured = True
                    except FileNotFoundError:
                        user_path_configured = False
            except Exception as e:
                user_path_restricted = True

        # Module mode execution check
        module_mode_working = False
        try:
            res = subprocess.run(
                [sys.executable, "-m", "gitpilot", "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                module_mode_working = True
        except Exception:
            module_mode_working = False

        return EnvironmentStatus(
            python_version=python_version_str,
            python_path=python_path,
            python_ok=python_ok,
            python_min_req=python_min_req,
            is_venv=is_venv,
            venv_path=venv_path,
            pip_available=pip_available,
            pip_version=pip_version,
            git_available=git_available,
            git_version=git_version,
            git_path=git_path,
            is_source_tree=is_source_tree,
            package_installed=package_installed,
            package_version=package_version,
            watchdog_installed=watchdog_installed,
            watchdog_version=watchdog_version,
            scripts_dir=scripts_dir,
            gitpilot_exec_path=gitpilot_exec_path,
            cli_in_path=cli_in_path,
            user_path_configured=user_path_configured,
            user_path_restricted=user_path_restricted,
            module_mode_working=module_mode_working
        )

    def run_doctor(self) -> int:
        """Executes read-only diagnostic output."""
        status = self.inspect_environment()
        print("=== GitPilot Environment Doctor ===")
        print("")
        print(f"Python:       [{'OK' if status.python_ok else 'FAIL'}] {status.python_version} ({status.python_path})")
        if not status.python_ok:
            print(f"              Requires Python {status.python_min_req}")
        
        if status.is_venv:
            print(f"Virtualenv:   [ACTIVE] {status.venv_path}")
        else:
            print(f"Virtualenv:   [NONE] User/System site mode")

        print(f"pip:          [{'OK' if status.pip_available else 'FAIL'}] {status.pip_version or 'Not found'}")
        print(f"Git:          [{'OK' if status.git_available else 'FAIL'}] {status.git_version or 'Not found'} ({status.git_path or 'N/A'})")
        print(f"Context:      {'Source Tree' if status.is_source_tree else 'Installed Package Context'}")
        print(f"GitPilot:     [{'OK' if status.package_installed else 'MISSING'}] {status.package_version or 'Not installed'}")
        print(f"watchdog:     [{'OK' if status.watchdog_installed else 'MISSING'}] {status.watchdog_version or 'Not installed'}")
        print(f"Scripts Dir:  {status.scripts_dir}")
        print(f"Executable:   {status.gitpilot_exec_path or 'Not generated yet'}")
        print(f"CLI PATH:     [{'OK' if status.cli_in_path else 'WARN'}] {'Available in PATH' if status.cli_in_path else 'Missing from process PATH'}")
        
        if sys.platform == "win32":
            path_reg_str = "Configured in HKCU\\Environment" if status.user_path_configured else ("Restricted by system policy" if status.user_path_restricted else "Not configured in HKCU\\Environment")
            print(f"User PATH:    [{'OK' if status.user_path_configured else 'WARN'}] {path_reg_str}")
        
        print(f"Module Mode:  [{'OK' if status.module_mode_working else 'FAIL'}] python -m gitpilot is {'working' if status.module_mode_working else 'unavailable'}")
        print("")
        
        if not status.python_ok:
            print(f"[X] Doctor check failed: Python {status.python_min_req} or newer required.")
            return 3
        elif not status.git_available:
            print("[!] Doctor recommendation: Git is not installed. Please install Git to continue.")
            return 2
        elif not status.cli_in_path:
            print("Recommended action:")
            print("    python -m gitpilot setup")
            return 0
        else:
            print("GitPilot environment is healthy.")
            return 0


class BootstrapManager:
    """Environment bootstrap & recovery manager for 'gitpilot setup'."""

    def __init__(self, project_root: Optional[Path] = None):
        self.inspector = EnvironmentInspector(project_root)

    def update_user_path_windows(self, scripts_dir: str) -> Tuple[bool, bool]:
        """
        Updates HKCU\\Environment Path idempotently on Windows.
        Returns (success, restricted).
        """
        if not winreg:
            return False, False

        norm_scripts = os.path.normcase(os.path.normpath(scripts_dir))
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                try:
                    user_path_val, reg_type = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    user_path_val = ""
                    reg_type = winreg.REG_EXPAND_SZ

                current_paths = [p for p in user_path_val.split(";") if p.strip()]
                norm_paths = [os.path.normcase(os.path.normpath(p)) for p in current_paths]

                if norm_scripts not in norm_paths:
                    new_path_val = f"{user_path_val};{scripts_dir}" if user_path_val else scripts_dir
                    winreg.SetValueEx(key, "Path", 0, reg_type, new_path_val)

                    # Notify Windows environment update
                    try:
                        import ctypes
                        HWND_BROADCAST = 0xFFFF
                        WM_SETTINGCHANGE = 0x001A
                        SMTO_ABORTIFHUNG = 0x0002
                        result = ctypes.c_ulong()
                        ctypes.windll.user32.SendMessageTimeoutW(
                            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
                            SMTO_ABORTIFHUNG, 5000, ctypes.byref(result)
                        )
                    except Exception:
                        pass
                return True, False
        except (PermissionError, OSError) as e:
            return False, True
        except Exception:
            return False, False

    def render_fallback_box(self):
        """Displays prominent user fallback notification box for restricted PCs."""
        box = """
+--------------------------------------------------------+
| GitPilot is installed successfully                     |
|                                                        |
| PATH modification was restricted by system policy.     |
| GitPilot will NOT request administrator privileges.    |
|                                                        |
| Safe Fallback Command:                                 |
|                                                        |
|     python -m gitpilot watch                           |
|                                                        |
| All GitPilot commands can be run via python -m module. |
+--------------------------------------------------------+
"""
        print(box)


    def run_setup(self, dry_run: bool = False, verbose: bool = False, repair: bool = False) -> SetupResult:
        print("GitPilot Setup")
        print("Environment Bootstrap & Recovery")
        print("-" * 40)

        status = self.inspector.inspect_environment()
        actions_performed = []
        warnings = []
        errors = []

        # 1. Check Python
        if status.python_ok:
            print(f"[OK] Python detected: Python {status.python_version}")
        else:
            print(f"[X] Unsupported Python version: {status.python_version}")
            print(f"    GitPilot requires Python {status.python_min_req}")
            errors.append(f"Python {status.python_min_req} required, detected {status.python_version}")
            return SetupResult(success=False, exit_code=3, status=status, errors=errors)

        # 2. Check pip
        if status.pip_available:
            print(f"[OK] pip detected: {status.pip_version}")
        else:
            print("[X] pip is not available for active Python interpreter.")
            errors.append("pip missing")

        # 3. Check Git
        if status.git_available:
            print(f"[OK] Git detected: {status.git_version}")
            if verbose and status.git_path:
                print(f"     Location: {status.git_path}")
        else:
            print("[X] Git was not found. GitPilot requires Git.")
            print("    Please install Git and restart your terminal.")
            errors.append("Git not installed")
            return SetupResult(success=False, exit_code=2, status=status, errors=errors)

        # 4. Check & Install GitPilot package / dependencies
        print("\nChecking GitPilot installation & dependencies...")
        if status.package_installed and not repair:
            print(f"[OK] GitPilot package installed ({status.package_version})")
        else:
            if dry_run:
                print("[WOULD CHANGE] Install GitPilot package")
                actions_performed.append("Would install GitPilot package")
            else:
                print("Installing GitPilot package...")
                try:
                    cmd = [sys.executable, "-m", "pip", "install"]
                    if not status.is_venv:
                        cmd.append("--user")
                    
                    if status.is_source_tree:
                        cmd.extend(["-e", "."])
                    else:
                        cmd.append("GitPilot")

                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if res.returncode == 0:
                        print("[OK] GitPilot package installed successfully")
                        actions_performed.append("Installed GitPilot package")
                    else:
                        print(f"[!] Warning during package installation: {res.stderr.strip()}")
                        warnings.append("Package installation warning")
                except Exception as e:
                    print(f"[X] Failed to install package: {e}")
                    errors.append(str(e))

        # Check & Install declared project dependencies dynamically
        declared_deps = get_project_dependencies(self.inspector.project_root / "pyproject.toml")
        for dep in declared_deps:
            dep_name = re.split(r'[<>=!~]', dep)[0].strip()
            dep_installed = False
            dep_version = None
            try:
                dep_version = importlib.metadata.version(dep_name)
                dep_installed = True
            except Exception:
                if importlib.util.find_spec(dep_name) is not None:
                    dep_installed = True
                    dep_version = "available"

            if dep_installed:
                print(f"[OK] {dep_name} dependency available ({dep_version})")
            else:
                if dry_run:
                    print(f"[WOULD CHANGE] Install {dep} dependency")
                    actions_performed.append(f"Would install {dep}")
                else:
                    print(f"Installing {dep} dependency...")
                    try:
                        cmd = [sys.executable, "-m", "pip", "install"]
                        if not status.is_venv:
                            cmd.append("--user")
                        cmd.append(dep)

                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if res.returncode == 0:
                            print(f"[OK] {dep} dependency installed")
                            actions_performed.append(f"Installed {dep} dependency")
                        else:
                            print(f"[X] Failed to install {dep}: {res.stderr.strip()}")
                            errors.append(f"Failed to install {dep}")
                    except Exception as e:
                        print(f"[X] Failed to install {dep}: {e}")
                        errors.append(str(e))


        # Re-inspect status after package actions
        status = self.inspector.inspect_environment()

        # 5. Check PATH & Executable Availability
        print("\nChecking PATH & executable availability...")
        path_repaired = False
        user_restricted = False

        if status.cli_in_path:
            print("[OK] gitpilot command is available in PATH")
        else:
            print("[!] gitpilot command is not available from PATH")
            if status.scripts_dir:
                print(f"    Executable directory: {status.scripts_dir}")

            if dry_run:
                print(f"[WOULD CHANGE] Add {status.scripts_dir} to User PATH")
                actions_performed.append("Would update User PATH")
            else:
                print("Attempting USER-level PATH repair...")
                if sys.platform == "win32":
                    ok, restricted = self.update_user_path_windows(status.scripts_dir)
                    if ok:
                        print("[OK] User PATH updated in HKCU\\Environment")
                        print("\nIMPORTANT: Open a NEW terminal window for PATH changes to take effect.")
                        actions_performed.append("Updated HKCU Environment Path")
                        path_repaired = True
                    elif restricted:
                        print("[X] User PATH modification was denied by operating system policy.")
                        print("    GitPilot will NOT attempt administrator elevation.")
                        user_restricted = True
                        warnings.append("User PATH modification denied by policy")
                    else:
                        print("[!] Could not automatically update User PATH.")
                        warnings.append("PATH update failed")
                else:
                    print(f"[!] Please manually add {status.scripts_dir} to your shell PATH (.bashrc/.zshrc).")

        # 6. Final Health Check
        print("\nRunning final health check...")
        status = self.inspector.inspect_environment()

        if status.module_mode_working:
            print("[OK] GitPilot module execution (python -m gitpilot) is operational")

        if dry_run:
            print("\n[DRY RUN COMPLETE] Zero modifications were made to the system.")
            return SetupResult(
                success=True,
                exit_code=0,
                status=status,
                actions_performed=actions_performed,
                warnings=warnings
            )

        if status.package_installed and (status.cli_in_path or path_repaired):
            print("[OK] GitPilot CLI setup completed successfully.")
            print("\nYou can now use:")
            print("    gitpilot watch")
            return SetupResult(
                success=True,
                exit_code=0,
                status=status,
                actions_performed=actions_performed
            )
        elif status.package_installed and user_restricted:
            print("\nSetup finished with environment restrictions.")
            self.render_fallback_box()
            return SetupResult(
                success=True,
                exit_code=1,
                status=status,
                warnings=warnings,
                actions_performed=actions_performed
            )
        elif status.package_installed:
            print("\nGitPilot package is ready, but executable is missing from current process PATH.")
            print("You can run GitPilot using:")
            print("    python -m gitpilot watch")
            return SetupResult(
                success=True,
                exit_code=1,
                status=status,
                warnings=warnings,
                actions_performed=actions_performed
            )
        else:
            print("\n[X] GitPilot setup was unable to complete package installation.")
            return SetupResult(
                success=False,
                exit_code=4,
                status=status,
                errors=errors,
                actions_performed=actions_performed
            )

