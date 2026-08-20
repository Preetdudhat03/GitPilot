import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gitpilot.bootstrap import (
    EnvironmentInspector,
    BootstrapManager,
    EnvironmentStatus,
    parse_pyproject_python_version,
    check_python_req,
)

class TestBootstrap(unittest.TestCase):

    def test_parse_pyproject_python_version(self):
        tmp_dir = Path(sys.prefix) # simple path reference
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_text", return_value='requires-python = ">=3.10"'):
            ver = parse_pyproject_python_version(Path("dummy/pyproject.toml"))
            self.assertEqual(ver, ">=3.10")

    def test_check_python_req(self):
        self.assertTrue(check_python_req(">=3.8"))
        # Test artificially lower version requirement
        self.assertTrue(check_python_req(">=3.0"))

    @patch("gitpilot.bootstrap.subprocess.run")
    @patch("gitpilot.bootstrap.shutil.which")
    def test_doctor_healthy(self, mock_which, mock_subproc):
        mock_which.return_value = "/usr/bin/git"
        
        # Setup subprocess returns
        def subproc_side_effect(cmd, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 0
            if "pip" in cmd:
                mock_res.stdout = "pip 24.0 from ..."
            elif "git" in cmd:
                mock_res.stdout = "git version 2.40.0"
            elif "gitpilot" in cmd:
                mock_res.stdout = "GitPilot CLI help"
            return mock_res

        mock_subproc.side_effect = subproc_side_effect

        inspector = EnvironmentInspector()
        with patch.object(inspector, "inspect_environment") as mock_inspect:
            mock_inspect.return_value = EnvironmentStatus(
                python_version="3.12.0",
                python_path="/bin/python",
                python_ok=True,
                python_min_req=">=3.8",
                is_venv=True,
                venv_path="/path/to/venv",
                pip_available=True,
                pip_version="24.0",
                git_available=True,
                git_version="2.40.0",
                git_path="/usr/bin/git",
                is_source_tree=True,
                package_installed=True,
                package_version="1.2.0",
                watchdog_installed=True,
                watchdog_version="3.0.0",
                scripts_dir="/path/to/venv/bin",
                gitpilot_exec_path="/path/to/venv/bin/gitpilot",
                cli_in_path=True,
                user_path_configured=True,
                user_path_restricted=False,
                module_mode_working=True
            )
            exit_code = inspector.run_doctor()
            self.assertEqual(exit_code, 0)

    def test_doctor_missing_git(self):
        inspector = EnvironmentInspector()
        with patch.object(inspector, "inspect_environment") as mock_inspect:
            mock_inspect.return_value = EnvironmentStatus(
                python_version="3.12.0",
                python_path="/bin/python",
                python_ok=True,
                python_min_req=">=3.8",
                is_venv=True,
                venv_path="/path/to/venv",
                pip_available=True,
                pip_version="24.0",
                git_available=False,
                git_version=None,
                git_path=None,
                is_source_tree=True,
                package_installed=True,
                package_version="1.2.0",
                watchdog_installed=True,
                watchdog_version="3.0.0",
                scripts_dir="/path/to/venv/bin",
                gitpilot_exec_path=None,
                cli_in_path=False,
                user_path_configured=False,
                user_path_restricted=False,
                module_mode_working=True
            )
            exit_code = inspector.run_doctor()
            self.assertEqual(exit_code, 2)

    def test_setup_dry_run(self):
        manager = BootstrapManager()
        with patch.object(manager.inspector, "inspect_environment") as mock_inspect:
            mock_inspect.return_value = EnvironmentStatus(
                python_version="3.12.0",
                python_path="/bin/python",
                python_ok=True,
                python_min_req=">=3.8",
                is_venv=True,
                venv_path="/path/to/venv",
                pip_available=True,
                pip_version="24.0",
                git_available=True,
                git_version="2.40.0",
                git_path="/usr/bin/git",
                is_source_tree=True,
                package_installed=False,
                package_version=None,
                watchdog_installed=False,
                watchdog_version=None,
                scripts_dir="/path/to/venv/bin",
                gitpilot_exec_path=None,
                cli_in_path=False,
                user_path_configured=False,
                user_path_restricted=False,
                module_mode_working=True
            )
            res = manager.run_setup(dry_run=True)
            self.assertIn("Would install GitPilot package", res.actions_performed)

    def test_setup_restricted_path_fallback(self):
        manager = BootstrapManager()
        with patch.object(manager.inspector, "inspect_environment") as mock_inspect, \
             patch.object(manager, "update_user_path_windows", return_value=(False, True)):
            
            mock_status = EnvironmentStatus(
                python_version="3.12.0",
                python_path="/bin/python",
                python_ok=True,
                python_min_req=">=3.8",
                is_venv=False,
                venv_path=None,
                pip_available=True,
                pip_version="24.0",
                git_available=True,
                git_version="2.40.0",
                git_path="/usr/bin/git",
                is_source_tree=True,
                package_installed=True,
                package_version="1.2.0",
                watchdog_installed=True,
                watchdog_version="3.0.0",
                scripts_dir="C:\\Users\\User\\AppData\\Roaming\\Python\\Scripts",
                gitpilot_exec_path="C:\\Users\\User\\AppData\\Roaming\\Python\\Scripts\\gitpilot.exe",
                cli_in_path=False,
                user_path_configured=False,
                user_path_restricted=True,
                module_mode_working=True
            )
            mock_inspect.return_value = mock_status

            res = manager.run_setup(dry_run=False)
            self.assertEqual(res.exit_code, 1)
            self.assertTrue(res.success)
            self.assertIn("User PATH modification denied by policy", res.warnings)

if __name__ == "__main__":
    unittest.main()
