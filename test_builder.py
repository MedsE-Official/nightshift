import inspect
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from builder import run_builder, BuilderTask, builder_task_has_changes, BuilderResult

class TestBuilderLibrary(unittest.TestCase):
    def test_builder_is_library_only(self):
        """Test that builder module can be imported without CLI side effects."""
        # This test ensures the builder module doesn't have CLI entry points
        # when imported as a library
        
        # Verify we can import and use run_builder function
        self.assertTrue(callable(run_builder))
        
        # Verify main function is not exposed at module level
        with self.assertRaises(AttributeError):
            getattr(__import__('builder'), 'main')

    def test_builder_task_prompt_storage(self):
        """Test that BuilderTask stores the prompt."""
        task = BuilderTask(prompt="test prompt", files=())
        self.assertEqual(task.prompt, "test prompt")

    def test_builder_task_files_storage(self):
        """Test that BuilderTask stores the files."""
        files = (Path("file1.py"), Path("file2.py"))
        task = BuilderTask(prompt="test prompt", files=files)
        self.assertEqual(task.files, files)

    def test_builder_task_immutable(self):
        """Test that BuilderTask is immutable."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"),))
        
        # Try to modify the prompt (should raise FrozenInstanceError)
        with self.assertRaises(Exception):
            task.prompt = "new prompt"
            
        # Try to modify the files (should raise FrozenInstanceError)
        with self.assertRaises(Exception):
            task.files = (Path("file2.py"),)

    def test_run_builder_accepts_builder_task(self):
        """Test that run_builder accepts a BuilderTask instead of separate arguments."""
        # Get the function signature
        sig = inspect.signature(run_builder)
        
        # Assert that "task" is present
        self.assertIn('task', sig.parameters)
        
        # Assert that "prompt" is absent
        self.assertNotIn('prompt', sig.parameters)
        
        # Assert that "files" is absent
        self.assertNotIn('files', sig.parameters)

    def test_builder_result_has_changes_field(self):
        """Test that BuilderResult has the has_changes field."""
        result = BuilderResult(
            return_code=0,
            stdout="test stdout",
            stderr="test stderr",
            has_changes=True
        )
        
        self.assertTrue(hasattr(result, 'has_changes'))
        self.assertTrue(result.has_changes)

    def test_builder_result_passed_true_when_success_and_changes(self):
        """Test that passed returns True when return_code is 0 and has_changes is True."""
        result = BuilderResult(
            return_code=0,
            stdout="test stdout",
            stderr="test stderr",
            has_changes=True
        )
        
        self.assertTrue(result.passed)

    def test_builder_result_passed_false_when_success_no_changes(self):
        """Test that passed returns False when return_code is 0 but has_changes is False."""
        result = BuilderResult(
            return_code=0,
            stdout="test stdout",
            stderr="test stderr",
            has_changes=False
        )
        
        self.assertFalse(result.passed)

    def test_builder_result_passed_false_when_failure_even_with_changes(self):
        """Test that passed returns False when return_code is non-zero even if has_changes is True."""
        result = BuilderResult(
            return_code=1,
            stdout="test stdout",
            stderr="test stderr",
            has_changes=True
        )
        
        self.assertFalse(result.passed)

    def test_run_builder_normal_execution_with_changes(self):
        """Test that normal execution with changed files returns has_changes=True."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"),))
        
        with patch('subprocess.run') as mock_run, \
             patch('builder.builder_task_has_changes') as mock_has_changes:
            
            # Mock subprocess to return successful completion
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test stdout"
            mock_result.stderr = "test stderr"
            mock_run.return_value = mock_result
            
            # Mock builder_task_has_changes to return True
            mock_has_changes.return_value = True
            
            result = run_builder(
                task=task,
                project_root=Path("/tmp")
            )
            
            self.assertTrue(result.has_changes)

    def test_run_builder_normal_execution_without_changes(self):
        """Test that normal execution without changed files returns has_changes=False."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"),))
        
        with patch('subprocess.run') as mock_run, \
             patch('builder.builder_task_has_changes') as mock_has_changes:
            
            # Mock subprocess to return successful completion
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test stdout"
            mock_result.stderr = "test stderr"
            mock_run.return_value = mock_result
            
            # Mock builder_task_has_changes to return False
            mock_has_changes.return_value = False
            
            result = run_builder(
                task=task,
                project_root=Path("/tmp")
            )
            
            self.assertFalse(result.has_changes)

    def test_run_builder_timeout_returns_has_changes_false(self):
        """Test that timeout returns has_changes=False."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"),))
        
        with patch('subprocess.run') as mock_run:
            # Mock subprocess to raise TimeoutExpired
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["aider"], 
                timeout=900, 
                output=b"test stdout", 
                stderr=b"test stderr"
            )
            
            result = run_builder(
                task=task,
                project_root=Path("/tmp")
            )
            
            self.assertFalse(result.has_changes)

    def test_builder_task_has_changes_empty_output(self):
        """Test that builder_task_has_changes returns False for empty Git output."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"),))
        
        with patch('subprocess.run') as mock_run:
            # Mock subprocess to return empty stdout
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = builder_task_has_changes(task=task, project_root=Path("/tmp"))
            
            self.assertFalse(result)
            # Verify the command was called with correct arguments
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            command = args[0]
            self.assertIn("git", command)
            self.assertIn("status", command)
            self.assertIn("--porcelain", command)
            self.assertIn("--", command)
            self.assertIn("file1.py", command)

    def test_builder_task_has_changes_modified_file(self):
        """Test that builder_task_has_changes returns True for modified file output."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"),))
        
        with patch('subprocess.run') as mock_run:
            # Mock subprocess to return modified file output
            mock_result = MagicMock()
            mock_result.stdout = " M file1.py\n"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = builder_task_has_changes(task=task, project_root=Path("/tmp"))
            
            self.assertTrue(result)

    def test_builder_task_has_changes_untracked_file(self):
        """Test that builder_task_has_changes returns True for untracked file output."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"),))
        
        with patch('subprocess.run') as mock_run:
            # Mock subprocess to return untracked file output
            mock_result = MagicMock()
            mock_result.stdout = "?? file1.py\n"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = builder_task_has_changes(task=task, project_root=Path("/tmp"))
            
            self.assertTrue(result)

    def test_builder_task_has_changes_command_structure(self):
        """Test that the command contains only task.files."""
        task = BuilderTask(prompt="test prompt", files=(Path("file1.py"), Path("file2.py")))
        
        with patch('subprocess.run') as mock_run:
            # Mock subprocess to return empty stdout
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            builder_task_has_changes(task=task, project_root=Path("/tmp"))
            
            # Verify the command was called with correct arguments
            args, kwargs = mock_run.call_args
            command = args[0]
            # Should contain git status --porcelain -- file1.py file2.py
            self.assertIn("file1.py", command)
            self.assertIn("file2.py", command)
            # Should have exactly 2 files in the command (no more, no less)
            file_args_count = sum(1 for arg in command if arg in ["file1.py", "file2.py"])
            self.assertEqual(file_args_count, 2)

if __name__ == '__main__':
    unittest.main()
