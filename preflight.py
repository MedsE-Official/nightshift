from dataclasses import dataclass
from pathlib import Path
from typing import List
import subprocess
import sys


@dataclass
class PreflightResult:
    passed: bool
    checks: List[str]
    errors: List[str]


def run_preflight(project_root: Path) -> PreflightResult:
    # For now, perform no real checks
    checks = []
    errors = []
    
    # Validate Python environment
    try:
        # Get the configured Python executable from config.json
        import json
        config_path = project_root / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
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
    
    return PreflightResult(
        passed=True,
        checks=checks,
        errors=errors
    )
