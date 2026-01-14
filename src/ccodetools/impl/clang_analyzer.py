import os
from typing import Any
from dotenv import load_dotenv
from ..interface import (
    AnalysisResult,
    FunctionInfo,
    PreprocessorDirective,
)
from .base import BaseAnalyzer
from clang.cindex import Config

load_dotenv()

path_clang_library = os.getenv("LIBCLANG_PATH", "/usr/lib/llvm-18/lib/libclang.so.1")

Config.set_library_file(path_clang_library)


class ClangAnalyzer(BaseAnalyzer):
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
        _, lines = self._read_file(file_path)

        functions = self.list_functions(file_path)
        includes = self._extract_includes_from_lines(lines)
        defines = self._extract_defines_from_lines(lines)
        conditionals = self._extract_conditionals(lines)
        structs = self._extract_structs(tu, file_path)
        enums = self._extract_enums(tu, file_path)
        typedefs = self._extract_typedefs(tu, file_path)

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
        import os
        tu = self._parse(file_path)
        functions: list[FunctionInfo] = []
        abs_path = os.path.abspath(file_path)

        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.FUNCTION_DECL and cursor.is_definition():
                # Only include functions defined in the target file
                if cursor.location.file and os.path.abspath(cursor.location.file.name) == abs_path:
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

    def _extract_includes_from_lines(self, lines: list[str]) -> list[PreprocessorDirective]:
        """Extract #include directives by parsing source lines."""
        includes = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#include'):
                includes.append(PreprocessorDirective(
                    type='include',
                    content=stripped,
                    line=i + 1
                ))
        return includes

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

    def _extract_structs(self, tu, file_path: str) -> list[dict[str, Any]]:
        import os
        abs_path = os.path.abspath(file_path)
        structs = []
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.STRUCT_DECL and cursor.is_definition():
                if cursor.location.file and os.path.abspath(cursor.location.file.name) == abs_path:
                    structs.append({
                        "name": cursor.spelling,
                        "line": cursor.location.line,
                    })
        return structs

    def _extract_enums(self, tu, file_path: str) -> list[dict[str, Any]]:
        import os
        abs_path = os.path.abspath(file_path)
        enums = []
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.ENUM_DECL:
                if cursor.location.file and os.path.abspath(cursor.location.file.name) == abs_path:
                    enums.append({
                        "name": cursor.spelling,
                        "line": cursor.location.line,
                    })
        return enums

    def _extract_typedefs(self, tu, file_path: str) -> list[dict[str, Any]]:
        import os
        abs_path = os.path.abspath(file_path)
        typedefs = []
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == self._CursorKind.TYPEDEF_DECL:
                if cursor.location.file and os.path.abspath(cursor.location.file.name) == abs_path:
                    typedefs.append({
                        "name": cursor.spelling,
                        "line": cursor.location.line,
                    })
        return typedefs

    # ---------- preprocessor directives ----------

    def get_preprocessor_directives(self, file_path: str) -> dict[str, list[PreprocessorDirective]]:
        """Returns all preprocessor directives."""
        _, lines = self._read_file(file_path)

        includes = self._extract_includes_from_lines(lines)
        defines = self._extract_defines_from_lines(lines)
        conditionals = self._extract_conditionals(lines)

        return {
            "includes": includes,
            "defines": defines,
            "conditionals": conditionals,
        }

    def _extract_defines_from_lines(self, lines: list[str]) -> list[PreprocessorDirective]:
        """Extract #define directives by parsing source lines."""
        defines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#define'):
                rest = stripped[7:].strip()

                space_idx = rest.find(' ')
                tab_idx = rest.find('\t')
                paren_idx = rest.find('(')

                delimiters = [idx for idx in [space_idx, tab_idx, paren_idx] if idx != -1]
                end_idx = min(delimiters) if delimiters else len(rest)

                name = rest[:end_idx] if end_idx > 0 else rest
                value = rest[end_idx:].strip() if end_idx < len(rest) else None

                defines.append(PreprocessorDirective(
                    type='define',
                    content=name,
                    line=i + 1,
                    value=value
                ))
        return defines

    def _extract_conditionals(self, lines: list[str]) -> list[PreprocessorDirective]:
        """Extract #if, #ifdef, #ifndef, #else, #endif."""
        conditionals = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            for directive in ['#ifdef', '#ifndef', '#if', '#elif', '#else', '#endif']:
                if stripped.startswith(directive):
                    conditionals.append(PreprocessorDirective(
                        type=directive[1:],
                        content=stripped,
                        line=i + 1
                    ))
                    break
        return conditionals

    # ---------- advanced tools ----------

    def get_function_dependencies(self, file_path: str, function_name: str) -> dict[str, Any]:
        """Return structural dependencies of a function."""
        tu = self._parse(file_path)

        deps: dict[str, Any] = {
            "function": function_name,
            "calls": set(),
            "types": set(),
            "macros": set(),
        }

        def traverse(cursor, active=False):
            if cursor.kind == self._CursorKind.FUNCTION_DECL and cursor.is_definition():
                active = cursor.spelling == function_name

            if not active:
                for child in cursor.get_children():
                    traverse(child, active)
                return

            if cursor.kind == self._CursorKind.CALL_EXPR and cursor.referenced:
                deps["calls"].add(cursor.referenced.spelling)

            if cursor.kind == self._CursorKind.TYPE_REF:
                deps["types"].add(cursor.spelling)

            text = cursor.spelling
            if cursor.kind == self._CursorKind.DECL_REF_EXPR and text.isupper():
                deps["macros"].add(text)

            for child in cursor.get_children():
                traverse(child, active)

        traverse(tu.cursor)
        return {k: sorted(v) if isinstance(v, set) else v for k, v in deps.items()}

    def summarize_function(self, file_path: str, function_name: str) -> dict[str, Any]:
        """Return heuristic structural summary of a function."""
        tu = self._parse(file_path)

        summary = {
            "function": function_name,
            "allocates_memory": False,
            "frees_memory": False,
            "multiple_returns": False,
            "uses_goto": False,
        }

        return_count = 0

        def traverse(cursor, active=False):
            nonlocal return_count

            if cursor.kind == self._CursorKind.FUNCTION_DECL and cursor.is_definition():
                active = cursor.spelling == function_name

            if not active:
                for child in cursor.get_children():
                    traverse(child, active)
                return

            if cursor.kind == self._CursorKind.CALL_EXPR and cursor.referenced:
                name = cursor.referenced.spelling
                if name == "malloc":
                    summary["allocates_memory"] = True
                if name == "free":
                    summary["frees_memory"] = True

            if cursor.kind == self._CursorKind.RETURN_STMT:
                return_count += 1
                if return_count > 1:
                    summary["multiple_returns"] = True

            if cursor.kind == self._CursorKind.GOTO_STMT:
                summary["uses_goto"] = True

            for child in cursor.get_children():
                traverse(child, active)

        traverse(tu.cursor)
        return summary

    def find_symbol(self, file_path: str, symbol: str) -> dict[str, Any]:
        """Find symbol occurrences in file."""
        tu = self._parse(file_path)

        result: dict[str, Any] = {
            "symbol": symbol,
            "lines": []
        }

        for cursor in tu.cursor.walk_preorder():
            if cursor.spelling == symbol:
                result["lines"].append(cursor.location.line)

        return result

    def get_error_handling_paths(self, file_path: str, function_name: str) -> list[dict[str, Any]]:
        """Detect error-handling patterns in a function."""
        tu = self._parse(file_path)

        errors: list[dict[str, Any]] = []

        def traverse(cursor, active=False):
            if cursor.kind == self._CursorKind.FUNCTION_DECL and cursor.is_definition():
                active = cursor.spelling == function_name

            if not active:
                for child in cursor.get_children():
                    traverse(child, active)
                return

            if cursor.kind == self._CursorKind.RETURN_STMT:
                errors.append({
                    "line": cursor.location.line,
                    "type": "return"
                })

            if cursor.kind == self._CursorKind.GOTO_STMT:
                errors.append({
                    "line": cursor.location.line,
                    "type": "goto"
                })

            for child in cursor.get_children():
                traverse(child, active)

        traverse(tu.cursor)
        return errors

    def list_side_effects(self, file_path: str, function_name: str) -> dict[str, Any]:
        """List side effects of a function."""
        tu = self._parse(file_path)

        effects: dict[str, Any] = {
            "io": set(),
            "allocates_memory": False
        }

        io_calls = {"printf", "write", "send"}

        def traverse(cursor, active=False):
            if cursor.kind == self._CursorKind.FUNCTION_DECL and cursor.is_definition():
                active = cursor.spelling == function_name

            if not active:
                for child in cursor.get_children():
                    traverse(child, active)
                return

            if cursor.kind == self._CursorKind.CALL_EXPR and cursor.referenced:
                name = cursor.referenced.spelling
                if name in io_calls:
                    effects["io"].add(name)
                if name == "malloc":
                    effects["allocates_memory"] = True

            for child in cursor.get_children():
                traverse(child, active)

        traverse(tu.cursor)
        effects["io"] = sorted(effects["io"])
        return effects
