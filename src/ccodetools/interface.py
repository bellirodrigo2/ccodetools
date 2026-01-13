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