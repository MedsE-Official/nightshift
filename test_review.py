import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from review import _run_api_guard, run_review, ReviewResult, ExecutionResult
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


class TestExecutionResult(unittest.TestCase):
    
    def test_test_result_stores_return_code(self):
        """Test that ExecutionResult stores return_code."""
        result = ExecutionResult(return_code=0, stdout="", stderr="")
        self.assertEqual(result.return_code, 0)
        
        result = ExecutionResult(return_code=1, stdout="", stderr="")
        self.assertEqual(result.return_code, 1)
    
    def test_test_result_stores_stdout(self):
        """Test that ExecutionResult stores stdout."""
        result = ExecutionResult(return_code=0, stdout="output", stderr="")
        self.assertEqual(result.stdout, "output")
    
    def test_test_result_stores_stderr(self):
        """Test that ExecutionResult stores stderr."""
        result = ExecutionResult(return_code=0, stdout="", stderr="error")
        self.assertEqual(result.stderr, "error")
    
    def test_test_result_passed_is_true_when_return_code_zero(self):
        """Test that ExecutionResult.passed is True when return_code is 0."""
        result = ExecutionResult(return_code=0, stdout="", stderr="")
        self.assertTrue(result.passed)
    
    def test_test_result_passed_is_false_when_return_code_nonzero(self):
        """Test that ExecutionResult.passed is False when return_code is non-zero."""
        result = ExecutionResult(return_code=1, stdout="", stderr="")
        self.assertFalse(result.passed)
    
    def test_test_result_is_immutable(self):
        """Test that ExecutionResult is immutable."""
        result = ExecutionResult(return_code=0, stdout="output", stderr="error")
        
        # Try to modify the fields (should raise an exception)
        with self.assertRaises(AttributeError):
            result.return_code = 1
        
        with self.assertRaises(AttributeError):
            result.stdout = "new_output"
        
        with self.assertRaises(AttributeError):
            result.stderr = "new_error"


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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr=""
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr=""
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr=""
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr=""
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr=""
                )
            )
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("Builder produced no file changes.", result.errors[0])

    @patch('review._run_api_guard')
    def test_run_review_api_guard_not_called_on_failed_builder(self, mock_api_guard):
        """Test that _run_api_guard is not called when builder fails."""
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr="",
                )
            )
            
            # Verify _run_api_guard was not called
            mock_api_guard.assert_not_called()
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("Builder execution failed.", result.errors[0])

    @patch('review._run_api_guard')
    def test_run_review_api_guard_not_called_on_timeout_builder(self, mock_api_guard):
        """Test that _run_api_guard is not called when builder times out."""
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr="",
                )
            )
            
            # Verify _run_api_guard was not called
            mock_api_guard.assert_not_called()
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("Builder execution timed out.", result.errors[0])

    @patch('review._run_api_guard')
    def test_run_review_api_guard_not_called_on_no_changes_builder(self, mock_api_guard):
        """Test that _run_api_guard is not called when builder produces no changes."""
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr="",
                )
            )
            
            # Verify _run_api_guard was not called
            mock_api_guard.assert_not_called()
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("Builder produced no file changes.", result.errors[0])

    @patch('review._run_api_guard')
    def test_run_review_api_guard_called_on_success_builder(self, mock_api_guard):
        """Test that _run_api_guard is called exactly once when builder succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Mock _run_api_guard to return a successful result
            mock_api_guard.return_value = ApiGuardResult(
                passed=True,
                removed_symbols=set(),
            )
            
            # Call run_review with successful builder result
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr=""
                )
            )
            
            # Verify _run_api_guard was called exactly once
            mock_api_guard.assert_called_once()
            
            # Verify success conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertTrue(result.passed)
            self.assertEqual(result.errors, ())

    def test_run_review_test_failure_returns_correct_error(self):
        """Test that failed tests return passed=False with exactly 'Test execution failed.'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Call run_review with failed test result
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
                ),
                test_result=ExecutionResult(
                    return_code=1,
                    stdout="",
                    stderr=""
                )
            )
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertEqual(result.errors[0], "Test execution failed.")

    @patch('review._run_api_guard')
    def test_run_review_api_guard_not_called_on_failed_test(self, mock_api_guard):
        """Test that _run_api_guard is not called when tests fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Call run_review with failed test result
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
                ),
                test_result=ExecutionResult(
                    return_code=1,
                    stdout="",
                    stderr=""
                )
            )
            
            # Verify _run_api_guard was not called
            mock_api_guard.assert_not_called()
            
            # Verify failure conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertFalse(result.passed)
            self.assertEqual(len(result.errors), 1)
            self.assertEqual(result.errors[0], "Test execution failed.")

    @patch('review._run_api_guard')
    def test_run_review_api_guard_called_on_success_builder_and_tests(self, mock_api_guard):
        """Test that _run_api_guard is called exactly once when both builder and tests pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            
            # Mock _run_api_guard to return a successful result
            mock_api_guard.return_value = ApiGuardResult(
                passed=True,
                removed_symbols=set(),
            )
            
            # Call run_review with successful builder and test results
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
                ),
                test_result=ExecutionResult(
                    return_code=0,
                    stdout="",
                    stderr=""
                )
            )
            
            # Verify _run_api_guard was called exactly once
            mock_api_guard.assert_called_once()
            
            # Verify success conditions
            self.assertIsInstance(result, ReviewResult)
            self.assertTrue(result.passed)
            self.assertEqual(result.errors, ())


if __name__ == '__main__':
    unittest.main()
