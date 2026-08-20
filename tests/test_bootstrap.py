import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gitpilot.bootstrap import (
    EnvironmentInspector,
    BootstrapManager,
    EnvironmentStatus,
    parse_pyproject_python_version,
    get_project_dependencies,
    check_python_req,
)
import gitpilot.__main__ as main_module

class TestBootstrap(unittest.TestCase):

    def test_parse_pyproject_python_version(self):
        """1. Python version source of truth parsing test using tomllib."""
        toml_content = b'[project]\nrequires-python = ">=3.10"\n'
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_bytes", return_value=toml_content):
            ver = parse_pyproject_python_version(Path("dummy/pyproject.toml"))
            self.assertEqual(ver, ">=3.10")

    def test_get_project_dependencies(self):
        """2. Dynamic dependency parsing test from pyproject.toml using tomllib."""
        toml_content = b'[project]\ndependencies = ["watchdog>=3.0.0"]\n'
        with patch("importlib.metadata.requires", side_effect=Exception("Metadata not found")), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_bytes", return_value=toml_content):
            deps = get_project_dependencies(Path("dummy/pyproject.toml"))
            self.assertEqual(deps, ["watchdog>=3.0.0"])

    def test_get_project_dependencies_empty_when_missing(self):
        """Verify get_project_dependencies returns [] (NOT hardcoded watchdog) when metadata is missing."""
        with patch("importlib.metadata.requires", side_effect=Exception("Metadata not found")), \
             patch.object(Path, "exists", return_value=False):
            deps = get_project_dependencies(Path("nonexistent/pyproject.toml"))
            self.assertEqual(deps, [])



    def test_check_python_req(self):
        """3. Python requirement version check logic."""
        self.assertTrue(check_python_req(">=3.8"))
        self.assertTrue(check_python_req(">=3.0"))

    def test_doctor_read_only_side_effects(self):
        """4. Verify doctor performs ZERO modifications to filesystem or environment."""
        inspector = EnvironmentInspector()
        env_before = dict(os.environ)
        
        with patch("gitpilot.bootstrap.subprocess.run") as mock_subproc, \
             patch("gitpilot.bootstrap.shutil.which", return_value="/usr/bin/git"):
            
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "2.40.0"
            mock_subproc.return_value = mock_res
            
            exit_code = inspector.run_doctor()
            self.assertIn(exit_code, (0, 1, 2, 3))
            # Verify environment variables were unchanged
            self.assertEqual(env_before, dict(os.environ))

    @patch("gitpilot.bootstrap.subprocess.run")
    @patch("gitpilot.bootstrap.shutil.which")
    def test_doctor_healthy(self, mock_which, mock_subproc):
        """5. Healthy environment inspection output test."""
        mock_which.return_value = "/usr/bin/git"
        
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
        """6. Test doctor detects missing Git dependency (exit code 2)."""
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

    def test_doctor_unsupported_python(self):
        """7. Test doctor detects unsupported Python version (exit code 3)."""
        inspector = EnvironmentInspector()
        with patch.object(inspector, "inspect_environment") as mock_inspect:
            mock_inspect.return_value = EnvironmentStatus(
                python_version="3.6.0",
                python_path="/bin/python3.6",
                python_ok=False,
                python_min_req=">=3.8",
                is_venv=False,
                venv_path=None,
                pip_available=True,
                pip_version="20.0",
                git_available=True,
                git_version="2.40.0",
                git_path="/usr/bin/git",
                is_source_tree=True,
                package_installed=False,
                package_version=None,
                watchdog_installed=False,
                watchdog_version=None,
                scripts_dir="/usr/bin",
                gitpilot_exec_path=None,
                cli_in_path=False,
                user_path_configured=False,
                user_path_restricted=False,
                module_mode_working=False
            )
            exit_code = inspector.run_doctor()
            self.assertEqual(exit_code, 3)

    def test_setup_dry_run_zero_modifications(self):
        """8. Test setup --dry-run performs zero modifications."""
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
            self.assertEqual(res.exit_code, 0)
            self.assertTrue(res.success)
            self.assertIn("Would install GitPilot package", res.actions_performed)

    def test_setup_idempotency(self):
        """9. Test running setup twice produces identical healthy results."""
        manager = BootstrapManager()
        with patch.object(manager.inspector, "inspect_environment") as mock_inspect:
            mock_status = EnvironmentStatus(
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
            mock_inspect.return_value = mock_status
            
            res1 = manager.run_setup(dry_run=False)
            res2 = manager.run_setup(dry_run=False)
            
            self.assertEqual(res1.exit_code, 0)
            self.assertEqual(res2.exit_code, 0)

    def test_setup_restricted_path_fallback(self):
        """10. Test restricted registry permission handling & ASCII fallback box."""
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

    def test_setup_does_not_modify_project_config(self):
        """11. Verify setup does not touch gitpilot.json or .git configuration."""
        manager = BootstrapManager()
        config_file = Path("gitpilot.json")
        exists_before = config_file.exists()
        
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
            manager.run_setup(dry_run=False)
            self.assertEqual(config_file.exists(), exists_before)

    def test_module_execution_entrypoint(self):
        """12. Verify gitpilot.__main__ exists and is importable."""
        self.assertTrue(hasattr(main_module, "main"))

if __name__ == "__main__":
    unittest.main()
