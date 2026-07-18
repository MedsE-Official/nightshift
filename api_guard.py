import ast
from typing import Set
from pathlib import Path


def extract_public_symbols(source: str) -> Set[str]:
    """
    Extract module-level function, async function, and class names from Python source.
    
    Args:
        source: Python source code as a string
        
    Returns:
        A set of symbol names at module level
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # If the source has syntax errors, return empty set
        return set()
    
    symbols = set()
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Only include top-level definitions (module level)
            if not any(isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) 
                      for parent in ast.walk(tree) 
                      if hasattr(parent, 'body') and node in parent.body):
                symbols.add(node.name)
    
    return symbols


def compare_symbol_sets(
    before: set[str],
    after: set[str],
) -> tuple[set[str], set[str]]:
    """
    Compare two sets of Python symbols and return removed and added symbols.
    
    Args:
        before: Set of symbols before
        after: Set of symbols after
        
    Returns:
        A tuple of (removed_symbols, added_symbols)
    """
    removed = before - after
    added = after - before
    return (removed, added)


def detect_removed_public_symbols(
    before_source: str,
    after_source: str,
) -> set[str]:
    """
    Detect removed public Python symbols between two source code versions.
    
    Args:
        before_source: Previous version of Python source code
        after_source: Current version of Python source code
        
    Returns:
        A set of symbol names that were removed
    """
    before_symbols = extract_public_symbols(before_source)
    after_symbols = extract_public_symbols(after_source)
    removed, _ = compare_symbol_sets(before_symbols, after_symbols)
    return removed


def detect_removed_public_symbols_from_files(
    before_file: Path,
    after_file: Path,
) -> set[str]:
    """
    Detect removed public Python symbols by reading two Python files.
    
    Args:
        before_file: Path to the previous version of a Python file
        after_file: Path to the current version of a Python file
        
    Returns:
        A set of symbol names that were removed
    """
    # Handle missing files gracefully
    try:
        before_source = before_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        before_source = ""
    
    try:
        after_source = after_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        after_source = ""
    
    return detect_removed_public_symbols(before_source, after_source)


# New code added below
from dataclasses import dataclass

@dataclass(frozen=True)
class ApiGuardResult:
    passed: bool
    removed_symbols: set[str]


def check_public_api(
    before_file: Path,
    after_file: Path,
) -> ApiGuardResult:
    """
    Check if the public API has changed by comparing two Python files.
    
    Args:
        before_file: Path to the previous version of a Python file
        after_file: Path to the current version of a Python file
        
    Returns:
        An ApiGuardResult indicating whether the check passed and any removed symbols
    """
    removed_symbols = detect_removed_public_symbols_from_files(before_file, after_file)
    passed = len(removed_symbols) == 0
    return ApiGuardResult(passed=passed, removed_symbols=removed_symbols)
