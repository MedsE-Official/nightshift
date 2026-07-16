import unittest
from pathlib import Path
import tempfile
from review import _run_api_guard, run_review, ReviewResult
from api_guard import ApiGuardResult
from builder import BuilderResult, BuilderStatus


class TestReviewResult(unittest.TestCase):
    
    def test_review_result_stores_passed(self):
        """Test that ReviewResult stores passed value."""
        result = ReviewResult(passed=True, errors=())
        self.assertTrue(result.passed)
        
        result = ReviewResult(passed=False, errors=())
        self.assertFalse(result.passed)
    
    def test_review_result_stores_errors(self):
        """Test that ReviewResult stores errors."""
        errors = ("error1", "error2")
        result = ReviewResult(passed=True, errors=errors)
        self.assertEqual(result.errors, errors)
    
    def test_review_result_is_immutable(self):
        """Test that ReviewResult is immutable."""
        result = ReviewResult(passed=True, errors=("error1",))
        
        # Try to modify the fields (should raise an exception)
        with self.assertRaises(AttributeError):
            result.passed = False
        
        with self.assertRaises(AttributeError):
            result.errors = ("new_error",)


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
                diff="",
                builder_result=BuilderResult(
                    status=BuilderStatus.SUCCESS,
                    return_code=0,
                    stdout="",
                    stderr="",
                    has_changes=True
                )
            )
            
            # Verify success conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertTrue(result.passed)
            self.assertEqual(result.errors, ())
    
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
                diff="",
                builder_result=BuilderResult(
                    status=BuilderStatus.SUCCESS,
                    return_code=0,
                    stdout="",
                    stderr="",
                    has_changes=True
                )
            )
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("func2", result.errors[0])
    
    def test_run_review_builder_failed(self):
        """Test that run_review returns failed result when builder fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Call run_review with failed builder result
            result = run_review(
                project_root=project_root,
                config={},
                block={},
                diff="",
                builder_result=BuilderResult(
                    status=BuilderStatus.FAILED,
                    return_code=1,
                    stdout="",
                    stderr="",
                    has_changes=False
                )
            )
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("Builder execution failed.", result.errors[0])
    
    def test_run_review_builder_timeout(self):
        """Test that run_review returns failed result when builder times out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Call run_review with timeout builder result
            result = run_review(
                project_root=project_root,
                config={},
                block={},
                diff="",
                builder_result=BuilderResult(
                    status=BuilderStatus.TIMEOUT,
                    return_code=124,
                    stdout="",
                    stderr="",
                    has_changes=False
                )
            )
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("Builder execution timed out.", result.errors[0])
    
    def test_run_review_builder_no_changes(self):
        """Test that run_review returns failed result when builder produces no changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Call run_review with no changes builder result
            result = run_review(
                project_root=project_root,
                config={},
                block={},
                diff="",
                builder_result=BuilderResult(
                    status=BuilderStatus.NO_CHANGES,
                    return_code=0,
                    stdout="",
                    stderr="",
                    has_changes=False
                )
            )
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("Builder produced no file changes.", result.errors[0])


if __name__ == '__main__':
    unittest.main()
