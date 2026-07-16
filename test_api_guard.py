import unittest
from api_guard import extract_public_symbols, compare_symbol_sets


class TestExtractPublicSymbols(unittest.TestCase):
    
    def test_module_level_functions_and_classes(self):
        """Test that module-level functions and classes are returned."""
        source = """
def func1():
    pass

class Class1:
    pass

async def async_func():
    pass
"""
        result = extract_public_symbols(source)
        expected = {"func1", "Class1", "async_func"}
        self.assertEqual(result, expected)
    
    def test_nested_definitions_are_ignored(self):
        """Test that nested definitions are ignored."""
        source = """
def outer_func():
    def inner_func():
        pass
    
    class InnerClass:
        pass
    
    return inner_func

class OuterClass:
    def method(self):
        def nested_func():
            pass
"""
        result = extract_public_symbols(source)
        # Only the outermost definitions should be included
        expected = {"outer_func", "OuterClass"}
        self.assertEqual(result, expected)
    
    def test_empty_source(self):
        """Test with empty source."""
        result = extract_public_symbols("")
        self.assertEqual(result, set())
    
    def test_syntax_error_returns_empty_set(self):
        """Test that syntax errors return empty set."""
        source = """
def func1()
    pass
"""
        result = extract_public_symbols(source)
        self.assertEqual(result, set())


class TestCompareSymbolSets(unittest.TestCase):
    
    def test_removed_symbols(self):
        """Test that removed symbols are correctly identified."""
        before = {"func1", "func2", "Class1"}
        after = {"func1", "Class1"}
        removed, added = compare_symbol_sets(before, after)
        self.assertEqual(removed, {"func2"})
        self.assertEqual(added, set())
    
    def test_added_symbols(self):
        """Test that added symbols are correctly identified."""
        before = {"func1", "Class1"}
        after = {"func1", "func2", "Class1"}
        removed, added = compare_symbol_sets(before, after)
        self.assertEqual(removed, set())
        self.assertEqual(added, {"func2"})
    
    def test_unchanged_symbol_sets(self):
        """Test that unchanged symbol sets return empty sets."""
        before = {"func1", "func2", "Class1"}
        after = {"func1", "func2", "Class1"}
        removed, added = compare_symbol_sets(before, after)
        self.assertEqual(removed, set())
        self.assertEqual(added, set())


if __name__ == '__main__':
    unittest.main()
