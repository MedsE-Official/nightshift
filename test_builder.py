import inspect
import unittest
from pathlib import Path
from builder import run_builder, BuilderTask

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

if __name__ == '__main__':
    unittest.main()
