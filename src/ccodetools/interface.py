from typing import Protocol,  Any
from dataclasses import dataclass

@dataclass
class FunctionInfo:
    """Function Information"""
    name: str
    signature: str
    start_line: int
    end_line: int
    return_type: str
    parameters: list[dict[str, str]]  # [{"type": "int", "name": "x"}, ...]
    doc_comment: str | None = None
    file_path: str | None = None

@dataclass
class PreprocessorDirective:
    """Preprocessor Directives"""
    type: str  # "include", "define", "ifdef", "ifndef", "if", "else", "endif"
    content: str
    line: int
    value: str | None = None  # Para defines

@dataclass
class AnalysisResult:
    """Analysis Complete Result"""
    file_path: str
    functions: list[FunctionInfo]
    includes: list[PreprocessorDirective]
    defines: list[PreprocessorDirective]
    conditionals: list[PreprocessorDirective]
    structs: list[dict[str, Any]]
    enums: list[dict[str, Any]]
    typedefs: list[dict[str, Any]]

class CCodeAnalyzer(Protocol):
    """C Code Analyzer Protocol"""
    
    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyzes a C file and returns the complete structure"""
        ...
    
    def list_functions(self, file_path: str) -> list[FunctionInfo]:
        """List only the functions in the file"""
        ...
    
    def get_function_body(self, file_path: str, function_name: str) -> str|None:
        """Returns the body of a specific function"""
        ...
    
    def get_preprocessor_directives(self, file_path: str) -> dict[str, list[PreprocessorDirective]]:
        """Returns all preprocessor directives"""
        ...

    # ===== CAMADA 1 – NOVAS =====

    def get_call_graph(self, file_path: str) -> dict[str, list[str]]:
        """Return call graph per function"""
        ...

    def get_function_dependencies(
        self, file_path: str, function_name: str
    ) -> dict[str, Any]:
        """Return structural dependencies of a function"""
        ...

    def summarize_function(
        self, file_path: str, function_name: str
    ) -> dict[str, Any]:
        """Return heuristic structural summary of a function"""
        ...

    def list_globals(self, file_path: str) -> list[dict[str, Any]]:
        """List global variables"""
        ...

    def find_symbol(self, file_path: str, symbol: str) -> dict[str, Any]:
        """Find symbol occurrences in file"""
        ...

    def get_error_handling_paths(
        self, file_path: str, function_name: str
    ) -> list[dict[str, Any]]:
        """Detect error-handling patterns in a function"""
        ...

    def list_side_effects(
        self, file_path: str, function_name: str
    ) -> dict[str, Any]:
        """List side effects of a function"""
        ...