import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

# Import the function we're testing
from preflight import run_preflight


class TestPreflight(unittest.TestCase):
    
    @patch('preflight._validate_ollama_server')
    @patch('preflight._validate_python_environment')
    def test_preflight_success(self, mock_validate_python, mock_validate_ollama):
        # Setup mocks
        mock_validate_python.return_value = MagicMock(passed=True, checks=[], errors=[])
        mock_validate_ollama.return_value = MagicMock(passed=True, checks=[], errors=[])
        
        # Create a temporary directory structure for testing
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # Mock the config file content
            with patch('preflight.open', unittest.mock.mock_open(read_data='{"model": "test-model"}')):
                with patch('preflight.json.load') as mock_json_load:
                    mock_json_load.return_value = {"model": "test-model"}
                    
                    # Mock the subprocess calls
                    with patch('subprocess.run') as mock_subprocess:
                        mock_subprocess.return_value = MagicMock(returncode=0)
                        
                        # Run preflight
                        result = run_preflight(Path("/tmp"))
                        
                        # Assertions
                        self.assertTrue(result.passed)
    
    @patch('preflight._validate_ollama_server')
    @patch('preflight._validate_python_environment')
    def test_preflight_ollama_model_not_found(self, mock_validate_python, mock_validate_ollama):
        # Setup mocks
        mock_validate_python.return_value = MagicMock(passed=True, checks=[], errors=[])
        mock_validate_ollama.return_value = MagicMock(passed=False, checks=[], errors=["Config file not found: config.json"])
        
        # Create a temporary directory structure for testing
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False  # Config file doesn't exist
            
            # Run preflight
            result = run_preflight(Path("/tmp"))
            
            # Assertions
            self.assertFalse(result.passed)
            self.assertIn("Config file not found: config.json", result.errors)
    
    @patch('preflight._validate_ollama_server')
    @patch('preflight._validate_python_environment')
    def test_preflight_ollama_model_not_available(self, mock_validate_python, mock_validate_ollama):
        # Setup mocks
        mock_validate_python.return_value = MagicMock(passed=True, checks=[], errors=[])
        mock_validate_ollama.return_value = MagicMock(passed=False, checks=[], errors=["Ollama model 'test-model' is not available"])
        
        # Create a temporary directory structure for testing
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # Mock the config file content
            with patch('preflight.open', unittest.mock.mock_open(read_data='{"model": "test-model"}')):
                with patch('preflight.json.load') as mock_json_load:
                    mock_json_load.return_value = {"model": "test-model"}
                    
                    # Mock the subprocess calls
                    with patch('subprocess.run') as mock_subprocess:
                        mock_subprocess.return_value = MagicMock(returncode=0)
                        
                        # Run preflight
                        result = run_preflight(Path("/tmp"))
                        
                        # Assertions
                        self.assertFalse(result.passed)
                        self.assertIn("Ollama model 'test-model' is not available", result.errors)


if __name__ == '__main__':
    unittest.main()
