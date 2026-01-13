import hashlib
from typing import Any
from collections import OrderedDict
from ..interface import CCodeAnalyzer, AnalysisResult, FunctionInfo, PreprocessorDirective


class CachedAnalyzer(CCodeAnalyzer):
    """
    Decorator / Proxy that adds caching to any CCodeAnalyzer.
    """

    def __init__(
        self,
        analyzer: CCodeAnalyzer,
        max_files: int = 32
    ) -> None:
        self._analyzer = analyzer
        self._max_files = max_files

        # LRU cache by file
        # key = (backend_id, file_path, content_hash)
        self._file_cache: OrderedDict[
            tuple[str, str, str], dict[str, Any]
        ] = OrderedDict()

    # ---------- internal helpers ----------

    def _backend_id(self) -> str:
        return self._analyzer.__class__.__name__

    def _read_and_hash(self, file_path: str) -> tuple[bytes, str]:
        with open(file_path, "rb") as f:
            content = f.read()
        h = hashlib.sha256(content).hexdigest()
        return content, h

    def _get_file_entry(self, file_path: str) -> dict[str, Any]:
        content, content_hash = self._read_and_hash(file_path)
        key = (self._backend_id(), file_path, content_hash)

        if key in self._file_cache:
            # LRU bump
            self._file_cache.move_to_end(key)
            return self._file_cache[key]

        # Cache miss → evict if needed
        if len(self._file_cache) >= self._max_files:
            self._file_cache.popitem(last=False)

        entry: dict[str, Any] = {
            "file_path": file_path,
            "hash": content_hash,
            "content": content,
            "derived": {}
        }

        self._file_cache[key] = entry
        return entry

    # ---------- delegated + cached API ----------

    def analyze_file(self, file_path: str) -> AnalysisResult:
        entry = self._get_file_entry(file_path)

        if "analysis_result" not in entry["derived"]:
            entry["derived"]["analysis_result"] = \
                self._analyzer.analyze_file(file_path)

        return entry["derived"]["analysis_result"]

    def list_functions(self, file_path: str) -> list[FunctionInfo]:
        entry = self._get_file_entry(file_path)

        if "functions" not in entry["derived"]:
            entry["derived"]["functions"] = \
                self._analyzer.list_functions(file_path)

        return entry["derived"]["functions"]

    def get_call_graph(self, file_path: str) -> dict[str, list[str]]:
        entry = self._get_file_entry(file_path)

        if "call_graph" not in entry["derived"]:
            entry["derived"]["call_graph"] = \
                self._analyzer.get_call_graph(file_path)

        return entry["derived"]["call_graph"]

    def list_globals(self, file_path: str) -> list[dict[str, Any]]:
        entry = self._get_file_entry(file_path)

        if "globals" not in entry["derived"]:
            entry["derived"]["globals"] = \
                self._analyzer.list_globals(file_path)

        return entry["derived"]["globals"]

    # ---------- pass-through (no cache yet) ----------

    def get_function_body(self, file_path: str, function_name: str) -> str | None:
        return self._analyzer.get_function_body(file_path, function_name)

    def get_preprocessor_directives(
        self, file_path: str
    ) -> dict[str, list[PreprocessorDirective]]:
        return self._analyzer.get_preprocessor_directives(file_path)

    def get_function_dependencies(
        self, file_path: str, function_name: str
    ) -> dict[str, Any]:
        return self._analyzer.get_function_dependencies(file_path, function_name)

    def summarize_function(
        self, file_path: str, function_name: str
    ) -> dict[str, Any]:
        return self._analyzer.summarize_function(file_path, function_name)

    def find_symbol(self, file_path: str, symbol: str) -> dict[str, Any]:
        return self._analyzer.find_symbol(file_path, symbol)

    def get_error_handling_paths(
        self, file_path: str, function_name: str
    ) -> list[dict[str, Any]]:
        return self._analyzer.get_error_handling_paths(file_path, function_name)

    def list_side_effects(
        self, file_path: str, function_name: str
    ) -> dict[str, Any]:
        return self._analyzer.list_side_effects(file_path, function_name)
