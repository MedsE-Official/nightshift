import unittest
from pathlib import Path
from builder import run_builder

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

if __name__ == '__main__':
    unittest.main()
