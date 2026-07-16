import unittest
from pathlib import Path
import tempfile
import os
from api_guard import extract_public_symbols, compare_symbol_sets, detect_removed_public_symbols, detect_removed_public_symbols_from_files, ApiGuardResult, check_public_api


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


class TestDetectRemovedPublicSymbols(unittest.TestCase):
    
    def test_one_removed_symbol(self):
        """Test that one removed symbol is correctly identified."""
        before = """
def func1():
    pass

def func2():
    pass
"""
        after = """
def func1():
    pass
"""
        result = detect_removed_public_symbols(before, after)
        expected = {"func2"}
        self.assertEqual(result, expected)
    
    def test_no_removed_symbols(self):
        """Test that no removed symbols returns empty set."""
        before = """
def func1():
    pass

def func2():
    pass
"""
        after = """
def func1():
    pass

def func2():
    pass
"""
        result = detect_removed_public_symbols(before, after)
        self.assertEqual(result, set())


class TestDetectRemovedPublicSymbolsFromFiles(unittest.TestCase):
    
    def test_one_removed_symbol_from_files(self):
        """Test that one removed symbol is correctly identified from temporary files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            before_file = Path(tmpdir) / "before.py"
            after_file = Path(tmpdir) / "after.py"
            
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
            
            result = detect_removed_public_symbols_from_files(before_file, after_file)
            expected = {"func2"}
            self.assertEqual(result, expected)
    
    def test_no_removed_symbols_from_files(self):
        """Test that no removed symbols returns empty set from temporary files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            before_file = Path(tmpdir) / "before.py"
            after_file = Path(tmpdir) / "after.py"
            
            content = """
def func1():
    pass

def func2():
    pass
"""
            
            before_file.write_text(content)
            after_file.write_text(content)
            
            result = detect_removed_public_symbols_from_files(before_file, after_file)
            self.assertEqual(result, set())


class TestApiGuardResult(unittest.TestCase):
    
    def test_api_guard_result_passed_true(self):
        """Test that ApiGuardResult with passed=True is created correctly."""
        result = ApiGuardResult(passed=True, removed_symbols=set())
        self.assertTrue(result.passed)
        self.assertEqual(result.removed_symbols, set())
    
    def test_api_guard_result_passed_false(self):
        """Test that ApiGuardResult with passed=False is created correctly."""
        result = ApiGuardResult(passed=False, removed_symbols={"func1"})
        self.assertFalse(result.passed)
        self.assertEqual(result.removed_symbols, {"func1"})


class TestCheckPublicApi(unittest.TestCase):
    
    def test_no_removed_symbols_returns_passed_true(self):
        """Test that no removed symbols returns passed=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            before_file = Path(tmpdir) / "before.py"
            after_file = Path(tmpdir) / "after.py"
            
            content = """
def func1():
    pass

def func2():
    pass
"""
            
            before_file.write_text(content)
            after_file.write_text(content)
            
            result = check_public_api(before_file, after_file)
            self.assertTrue(result.passed)
            self.assertEqual(result.removed_symbols, set())
    
    def test_removed_symbol_returns_passed_false_and_includes_symbol(self):
        """Test that removed symbol returns passed=False and includes the symbol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            before_file = Path(tmpdir) / "before.py"
            after_file = Path(tmpdir) / "after.py"
            
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
            
            result = check_public_api(before_file, after_file)
            self.assertFalse(result.passed)
            self.assertEqual(result.removed_symbols, {"func2"})


if __name__ == '__main__':
    unittest.main()
