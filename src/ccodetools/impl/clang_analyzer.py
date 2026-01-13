from typing import Any
from ..interface import (
    CCodeAnalyzer,
    AnalysisResult,
    FunctionInfo,
    PreprocessorDirective,
)


class ClangAnalyzer(CCodeAnalyzer):
    """
    Semantic C analyzer based on libclang.
    """

    def __init__(self, compile_args: list[str] | None = None) -> None:
        try:
            from clang.cindex import Index, CursorKind
        except Exception as e:
            raise RuntimeError(
                "ClangAnalyzer requires libclang to be installed. "
                "Install libclang or use TreeSitterAnalyzer."
            ) from e
        self._Index = Index
        self._CursorKind = CursorKind
        self._index = Index.create()
        self._compile_args = compile_args or ["-std=c11"]

    # ---------- internal ----------

    def _parse(self, file_path: str):
        return self._index.parse(
            file_path,
            args=self._compile_args,
        )

    # ---------- interface implementation ----------

    def analyze_file(self, file_path: str) -> AnalysisResult:
        tu = self._parse(file_path)

        functions = self.list_functions(file_path)
        includes = self._extract_includes(tu)
        defines = self._extract_defines(tu)
        conditionals = []  # clang não expõe isso bem
        structs = self._extract_structs(tu)
        enums = self._extract_enums(tu)
        typedefs = self._extract_typedefs(tu)

        return AnalysisResult(
            file_path=file_path,
            functions=functions,
            includes=includes,
            defines=defines,
            conditionals=conditionals,
            structs=structs,
            enums=enums,
            typedefs=typedefs,
        )

    # ---------- functions ----------

    def list_functions(self, file_path: str) -> list[FunctionInfo]:
        tu = self._parse(file_path)
        functions: list[FunctionInfo] = []

        for cursor in tu.cursor.get_children():
            if cursor.kind == self._CursorKind.FUNCTION_DECL and cursor.is_definition():
                functions.append(self._parse_function(cursor, file_path))

        return functions

    def _parse_function(self, cursor, file_path: str) -> FunctionInfo:
        params = [
            {"type": arg.type.spelling, "name": arg.spelling}
            for arg in cursor.get_arguments()
        ]

        return FunctionInfo(
            name=cursor.spelling,
            signature=cursor.displayname,
            start_line=cursor.extent.start.line,
            end_line=cursor.extent.end.line,
            return_type=cursor.result_type.spelling,
            parameters=params,
            doc_comment=cursor.raw_comment,
            file_path=file_path,
        )

    def get_function_body(self, file_path: str, function_name: str) -> str | None:
        tu = self._parse(file_path)

        for cursor in tu.cursor.walk_preorder():
            if (
                cursor.kind == self._CursorKind.FUNCTION_DECL
                and cursor.spelling == function_name
                and cursor.is_definition()
            ):
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                start = cursor.extent.start.line - 1
                end = cursor.extent.end.line
                return "".join(lines[start:end])

        return None

    # ---------- advanced tools ----------

    def get_call_graph(self, file_path: str) -> dict[str, list[str]]:
        tu = self._parse(file_path)
        graph: dict[str, set[str]] = {}
        current_function = None

        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.FUNCTION_DECL and cursor.is_definition():
                current_function = cursor.spelling
                graph.setdefault(current_function, set())

            elif (
                cursor.kind == self._CursorKind.CALL_EXPR
                and current_function
                and cursor.referenced
            ):
                graph[current_function].add(cursor.referenced.spelling)

        return {k: sorted(v) for k, v in graph.items()}

    def list_globals(self, file_path: str) -> list[dict[str, Any]]:
        tu = self._parse(file_path)
        globals_ = []

        for cursor in tu.cursor.get_children():
            if cursor.kind == self._CursorKind.VAR_DECL and cursor.semantic_parent == tu.cursor:
                globals_.append({
                    "name": cursor.spelling,
                    "type": cursor.type.spelling,
                    "line": cursor.location.line,
                })

        return globals_

    # ---------- preprocess / types ----------

    def _extract_includes(self, tu) -> list[PreprocessorDirective]:
        includes = []
        for inc in tu.get_includes():
            includes.append(
                PreprocessorDirective(
                    type="include",
                    content=str(inc.include),
                    line=inc.location.line,
                )
            )
        return includes

    def _extract_defines(self, tu) -> list[PreprocessorDirective]:
        # libclang não expõe macros facilmente
        return []

    def _extract_structs(self, tu) -> list[dict[str, Any]]:
        structs = []
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.STRUCT_DECL and cursor.is_definition():
                structs.append({
                    "name": cursor.spelling,
                    "line": cursor.location.line,
                })
        return structs

    def _extract_enums(self, tu) -> list[dict[str, Any]]:
        enums = []
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.ENUM_DECL:
                enums.append({
                    "name": cursor.spelling,
                    "line": cursor.location.line,
                })
        return enums

    def _extract_typedefs(self, tu) -> list[dict[str, Any]]:
        typedefs = []
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.TYPEDEF_DECL:
                typedefs.append({
                    "name": cursor.spelling,
                    "line": cursor.location.line,
                })
        return typedefs
