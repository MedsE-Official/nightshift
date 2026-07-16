import ast
from typing import Set


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
