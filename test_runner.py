#!/usr/bin/env python3

import subprocess
import sys

def run_tests():
    """Run all tests for the orchestrator"""
    print("Running orchestrator tests...")
    
    try:
        # Test compilation
        result = subprocess.run([sys.executable, "-m", "py_compile", "orchestrator.py", "config.py"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("Compilation failed:")
            print(result.stderr)
            return False
        
        print("✓ Compilation successful")
        
        # Run unit tests
        result = subprocess.run([sys.executable, "-m", "unittest", "test_orchestrator.py"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("Unit tests failed:")
            print(result.stderr)
            return False
            
        print("✓ Unit tests passed")
        
        # Check git diff
        result = subprocess.run(["git", "--no-pager", "diff", "--check"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("Git diff check failed:")
            print(result.stdout)
            return False
            
        print("✓ Git diff check passed")
        
        print("\nAll checks passed!")
        return True
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
