import unittest
from pathlib import Path
import tempfile
from review import _run_api_guard
from api_guard import ApiGuardResult


class TestRunApiGuard(unittest.TestCase):
    
    def test_run_api_guard_delegates_to_check_public_api(self):
        """Test that _run_api_guard delegates to check_public_api."""
        with tempfile.TemporaryDirectory() as tmpdir:
            before_file = Path(tmpdir) / "before.py"
            after_file = Path(tmpdir) / "after.py"
            
            # Create test content
            before_content = """
def func1():
    pass

def func2():
    pass
"""
            after_content = """
def func1():
    pass
"""
            
            before_file.write_text(before_content)
            after_file.write_text(after_content)
            
            # Call the function we're testing
            result = _run_api_guard(before_file, after_file)
            
            # Verify it returns an ApiGuardResult
            self.assertIsInstance(result, ApiGuardResult)
            self.assertFalse(result.passed)
            self.assertEqual(result.removed_symbols, {"func2"})
    
    def test_run_api_guard_returns_correct_result(self):
        """Test that _run_api_guard returns ApiGuardResult unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            before_file = Path(tmpdir) / "before.py"
            after_file = Path(tmpdir) / "after.py"
            
            # Create test content with no changes
            content = """
def func1():
    pass

def func2():
    pass
"""
            
            before_file.write_text(content)
            after_file.write_text(content)
            
            # Call the function we're testing
            result = _run_api_guard(before_file, after_file)
            
            # Verify it returns an ApiGuardResult with passed=True and empty removed_symbols
            self.assertIsInstance(result, ApiGuardResult)
            self.assertTrue(result.passed)
            self.assertEqual(result.removed_symbols, set())


if __name__ == '__main__':
    unittest.main()
