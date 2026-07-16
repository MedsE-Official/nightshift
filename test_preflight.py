import unittest
from pathlib import Path
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from preflight import PreflightResult, run_preflight


class TestPreflight(unittest.TestCase):
    
    def test_run_preflight_returns_preflight_result(self):
        """Test that run_preflight returns a PreflightResult."""
        result = run_preflight(Path("."))
        self.assertIsInstance(result, PreflightResult)
    
    def test_initial_result_passes(self):
        """Test that the initial preflight result passes."""
        result = run_preflight(Path("."))
        self.assertTrue(result.passed)
    
    @patch('subprocess.run')
    def test_python_executable_validation_success(self, mock_run):
        """Test successful Python executable validation."""
        # Mock successful execution for python --version
        mock_result_version = MagicMock()
        mock_result_version.returncode = 0
        mock_result_version.stdout = "Python 3.8.0\n"
        mock_result_version.stderr = ""
        
        # Mock successful execution for python -c "import pytest"
        mock_result_pytest = MagicMock()
        mock_result_pytest.returncode = 0
        mock_result_pytest.stdout = ""
        mock_result_pytest.stderr = ""
        
        # Use side_effect to return different results per call
        mock_run.side_effect = [mock_result_version, mock_result_pytest]
        
        result = run_preflight(Path("."))
        self.assertTrue(result.passed)
        self.assertEqual(len(result.checks), 2)
        # Check that key concepts are present rather than exact wording
        self.assertTrue(any("Python executable" in check for check in result.checks))
        self.assertTrue(any("pytest import" in check for check in result.checks))
    
    @patch('subprocess.run')
    def test_python_executable_validation_failure(self, mock_run):
        """Test failed Python executable path."""
        # Mock failed execution for python --version
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command not found"
        mock_run.return_value = mock_result
        
        result = run_preflight(Path("."))
        self.assertFalse(result.passed)
        self.assertEqual(len(result.errors), 1)
        # Check that key concepts are present rather than exact wording
        self.assertTrue(any("Python executable" in error for error in result.errors))
    
    @patch('subprocess.run')
    def test_pytest_import_validation_failure(self, mock_run):
        """Test failed pytest import."""
        # Mock successful execution for python --version
        mock_result_version = MagicMock()
        mock_result_version.returncode = 0
        mock_result_version.stdout = "Python 3.8.0\n"
        mock_result_version.stderr = ""
        
        # Mock failed execution for python -c "import pytest"
        mock_result_pytest = MagicMock()
        mock_result_pytest.returncode = 1
        mock_result_pytest.stdout = ""
        mock_result_pytest.stderr = "ModuleNotFoundError: No module named 'pytest'"
        
        # Use side_effect to return different results per call
        mock_run.side_effect = [mock_result_version, mock_result_pytest]
        
        result = run_preflight(Path("."))
        self.assertFalse(result.passed)
        self.assertEqual(len(result.errors), 1)
        # Check that both "pytest" and "import" occur in error (case insensitive)
        error_msg = result.errors[0].lower()
        self.assertIn("pytest", error_msg)
        self.assertIn("import", error_msg)
    
    def test_missing_executable_with_config(self):
        """Test missing executable by using a config with nonexistent python path."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            # Create config.json with nonexistent python executable
            config_content = {
                "model": "qwen3-coder:latest",
                "aider_model": "openai/qwen3-coder:latest",
                "max_blocks": 5,
                "max_attempts_per_block": 2,
                "timeout_minutes_per_aider_run": 30,
                "commands": {
                    "test": "/Users/matsedenius/.pyenv/versions/3.10.13/bin/python -m pytest -q"
                },
                "protected_paths": [
                    ".git",
                    ".venv",
                    "__pycache__"
                ],
                "python_executable": "/non/existent/python"
            }
            
            config_file = project_root / "config.json"
            with open(config_file, 'w') as f:
                json.dump(config_content, f)
            
            # Change to temp directory and run preflight
            original_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                result = run_preflight(project_root)
                self.assertFalse(result.passed)
                self.assertEqual(len(result.errors), 1)
                # Check that key concepts are present rather than exact wording
                self.assertTrue(any("Python executable" in error for error in result.errors))
            finally:
                os.chdir(original_cwd)


if __name__ == '__main__':
    unittest.main()
