"""Base class for C code analyzers with common utilities."""
from abc import ABC


class BaseAnalyzer(ABC):
    """Base class providing common utilities for C code analyzers."""

    def _read_file(self, file_path: str) -> tuple[str, list[str]]:
        """Read file and return content as bytes and lines as list of strings."""
        with open(file_path, 'rb') as f:
            content = f.read()
        lines = content.decode('utf-8').split('\n')
        return content, lines
