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
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.ClassDef):
                # Check if this is a module-level definition
                if not any(isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) 
                          for parent in ast.walk(tree) 
                          if hasattr(parent, 'body') and node in parent.body):
                    symbols.add(node.name)
    
    return symbols
