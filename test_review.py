import unittest
from pathlib import Path
import tempfile
from review import _run_api_guard, run_review
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


class TestRunReview(unittest.TestCase):
    
    def test_run_review_no_errors_when_passed(self):
        """Test that run_review produces no API Guard errors when check passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Create test files
            before_file = project_root / "before.py"
            after_file = project_root / "after.py"
            
            content = """
def func1():
    pass

def func2():
    pass
"""
            
            before_file.write_text(content)
            after_file.write_text(content)
            
            # Call run_review with minimal arguments
            result = run_review(
                project_root=project_root,
                config={},
                block={},
                diff=""
            )
            
            # Verify success conditions
            self.assertNotIn("errors", result)
            self.assertTrue(result["api_guard_result"].passed)
            self.assertEqual(result["api_guard_result"].removed_symbols, set())
    
    def test_run_review_adds_error_when_failed(self):
        """Test that run_review adds exactly one review error when check fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Create test files
            before_file = project_root / "before.py"
            after_file = project_root / "after.py"
            
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
            
            # Call run_review with minimal arguments
            result = run_review(
                project_root=project_root,
                config={},
                block={},
                diff=""
            )
            
            # Verify failure conditions
            self.assertIn("errors", result)
            self.assertEqual(len(result["errors"]), 1)
            self.assertIn("func2", result["errors"][0])
            self.assertFalse(result["api_guard_result"].passed)
            self.assertEqual(result["api_guard_result"].removed_symbols, {"func2"})


if __name__ == '__main__':
    unittest.main()
