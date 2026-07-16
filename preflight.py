from dataclasses import dataclass
from pathlib import Path
from typing import List
import subprocess
import sys
import urllib.request
import json


@dataclass
class PreflightResult:
    passed: bool
    checks: List[str]
    errors: List[str]


def _validate_ollama_server() -> PreflightResult:
    """Validate that the Ollama server is available and responding."""
    try:
        # Construct the URL using the settings from config.py
        from config import settings
        url = f"{settings.ollama_host}/api/tags"
        
        # Make the request with a 10 second timeout
        response = urllib.request.urlopen(url, timeout=10)
        response_data = response.read().decode('utf-8')
        
        # Try to parse the JSON response
        json.loads(response_data)
        
        return PreflightResult(
            passed=True,
            checks=[f"Ollama server is available at {settings.ollama_host}"],
            errors=[]
        )
    except Exception as e:
        return PreflightResult(
            passed=False,
            checks=[],
            errors=[f"Ollama server validation failed: {str(e)}"]
        )


def _validate_ollama_model(project_root: Path) -> PreflightResult:
    """Validate that the configured Ollama model is available."""
    try:
        # Read the config file using the same pattern as _validate_python_environment
        config_path = project_root / "config.json"
        if not config_path.exists():
            return PreflightResult(
                passed=False,
                checks=[],
                errors=["Config file not found: config.json"]
            )
        
        with config_path.open('r') as f:
            config = json.load(f)
        
        # Get the model from config
        model = config.get("model")
        if not model:
            return PreflightResult(
                passed=False,
                checks=[],
                errors=["Model not specified in config.json"]
            )
        
        # Query the Ollama server for available models
        from config import settings
        url = f"{settings.ollama_host}/api/tags"
        
        response = urllib.request.urlopen(url, timeout=10)
        response_data = response.read().decode('utf-8')
        
        # Parse the JSON response
        response_json = json.loads(response_data)
        
        # Check if the configured model is in the list of available models
        models = response_json.get("models", [])
        if not isinstance(models, list):
            return PreflightResult(
                passed=False,
                checks=[],
                errors=["Invalid response format from Ollama server"]
            )
        
        # Look for the configured model in the list
        model_available = any(model_info.get("name") == model for model_info in models)
        
        if model_available:
            return PreflightResult(
                passed=True,
                checks=[f"Ollama model '{model}' is available"],
                errors=[]
            )
        else:
            return PreflightResult(
                passed=False,
                checks=[],
                errors=[f"Ollama model '{model}' is not available"]
            )
            
    except Exception as e:
        return PreflightResult(
            passed=False,
            checks=[],
            errors=[f"Ollama model validation failed: {str(e)}"]
        )


def run_preflight(project_root: Path) -> PreflightResult:
    # For now, perform no real checks
    checks = []
    errors = []
    
    # Validate Python environment
    try:
        # Get the configured Python executable from config.json
        config_path = project_root / "config.json"
        if config_path.exists():
            with config_path.open('r') as f:
                config = json.load(f)
            
            python_executable = config.get("python_executable", sys.executable)
        else:
            python_executable = sys.executable
            
        # Check 1: Verify that the executable exists
        if not Path(python_executable).exists():
            errors.append(f"Python executable not found: {python_executable}")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=errors
            )
        
        # Check 2: Verify that it can be executed
        try:
            result = subprocess.run(
                [python_executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                errors.append(f"Python executable cannot be executed: {python_executable}")
                return PreflightResult(
                    passed=False,
                    checks=checks,
                    errors=errors
                )
            checks.append(f"Python executable verified: {python_executable}")
        except subprocess.TimeoutExpired:
            errors.append(f"Timeout checking Python executable: {python_executable}")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=errors
            )
        except Exception as e:
            errors.append(f"Error checking Python executable: {python_executable} - {str(e)}")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=errors
            )
        
        # Check 3: Verify that "import pytest" succeeds using that exact interpreter
        try:
            result = subprocess.run(
                [python_executable, "-c", "import pytest"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                errors.append(f"Cannot import pytest with Python executable: {python_executable}")
                return PreflightResult(
                    passed=False,
                    checks=checks,
                    errors=errors
                )
            checks.append(f"pytest import verified with: {python_executable}")
        except subprocess.TimeoutExpired:
            errors.append(f"Timeout checking pytest import: {python_executable}")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=errors
            )
        except Exception as e:
            errors.append(f"Error checking pytest import: {python_executable} - {str(e)}")
            return PreflightResult(
                passed=False,
                checks=checks,
                errors=errors
            )
            
    except Exception as e:
        errors.append(f"Unexpected error during Python validation: {str(e)}")
        return PreflightResult(
            passed=False,
            checks=checks,
            errors=errors
        )
    
    # Validate Ollama server
    server_result = _validate_ollama_server()
    if not server_result.passed:
        errors.extend(server_result.errors)
        return PreflightResult(
            passed=False,
            checks=checks,
            errors=errors
        )
    checks.extend(server_result.checks)
    
    # Validate Ollama model
    model_result = _validate_ollama_model(project_root)
    if not model_result.passed:
        errors.extend(model_result.errors)
        return PreflightResult(
            passed=False,
            checks=checks,
            errors=errors
        )
    checks.extend(model_result.checks)
    
    return PreflightResult(
        passed=True,
        checks=checks,
        errors=errors
    )
