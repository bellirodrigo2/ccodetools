from typing import Literal
from .interface import CCodeAnalyzer


def make_analyzer(analyzer: Literal['tree-sitter', 'clang']) -> CCodeAnalyzer:
    """Factory to create analyzer instances.

    Args:
        analyzer: Type of analyzer to create ('tree-sitter' or 'clang')

    Returns:
        An instance implementing the CCodeAnalyzer protocol
    """
    if analyzer == 'tree-sitter':
        from .impl.tree_sitter import TreeSitterAnalyzer
        return TreeSitterAnalyzer()
    elif analyzer == 'clang':
        from .impl.clang_analyzer import ClangAnalyzer
        return ClangAnalyzer()
    else:
        raise ValueError(f"Analyzer '{analyzer}' not supported.")