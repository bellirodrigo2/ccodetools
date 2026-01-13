from typing import Any
from ..interface import CCodeAnalyzer, AnalysisResult, FunctionInfo, PreprocessorDirective

class TreeSitterAnalyzer(CCodeAnalyzer):
    """Implementation using tree-sitter"""
    
    def __init__(self)->None:
        try:
            from tree_sitter import Language, Parser
            import tree_sitter_c

            self.c_language = Language(tree_sitter_c.language())
            self.parser = Parser(self.c_language)
        except ImportError:
            raise ImportError(
                "tree-sitter is not installed. Execute: "
                "pip install tree-sitter tree-sitter-c"
            )
    
    def _read_file(self, file_path: str) -> tuple[str, list[str]]:
        """Read file and return content and lines"""
        with open(file_path, 'rb') as f:
            content = f.read()
        lines = content.decode('utf-8').split('\n')
        return content, lines
    
    def _extract_comment_before(self, lines: list[str], line_num: int) -> str | None:
        """Extract comment immediately before a line"""
        comments = []
        i = line_num - 2  # linha anterior (0-indexed)
        
        while i >= 0:
            line = lines[i].strip()
            if line.startswith('//'):
                comments.insert(0, line[2:].strip())
                i -= 1
            elif line.startswith('/*') or '*/' in line:
                # Comentário de bloco - coleta até encontrar início
                block = []
                while i >= 0:
                    l = lines[i].strip()
                    block.insert(0, l)
                    if l.startswith('/*'):
                        break
                    i -= 1
                # Limpa marcadores de bloco
                block_text = ' '.join(block)
                block_text = block_text.replace('/*', '').replace('*/', '').replace('*', '').strip()
                comments.insert(0, block_text)
                break
            elif line == '':
                i -= 1
            else:
                break
        
        return '\n'.join(comments) if comments else None
    
    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyze complete C file"""
        content, lines = self._read_file(file_path)
        tree = self.parser.parse(content)
        
        functions = self._extract_functions(tree, lines, file_path)
        includes = self._extract_includes(lines)
        defines = self._extract_defines(lines)
        conditionals = self._extract_conditionals(lines)
        structs = self._extract_structs(tree, lines)
        enums = self._extract_enums(tree, lines)
        typedefs = self._extract_typedefs(tree, lines)
        
        return AnalysisResult(
            file_path=file_path,
            functions=functions,
            includes=includes,
            defines=defines,
            conditionals=conditionals,
            structs=structs,
            enums=enums,
            typedefs=typedefs
        )
    
    def list_functions(self, file_path: str) -> list[FunctionInfo]:
        """list only functions"""
        content, lines = self._read_file(file_path)
        tree = self.parser.parse(content)
        return self._extract_functions(tree, lines, file_path)
    
    def get_function_body(self, file_path: str, function_name: str) -> str | None:
        """Return body of specific function"""
        content, lines = self._read_file(file_path)
        tree = self.parser.parse(content)
        
        def find_function(node)->str | None:
            if node.type == 'function_definition':
                declarator = node.child_by_field_name('declarator')
                if declarator:
                    name_node = self._get_function_name(declarator)
                    if name_node and name_node.text.decode('utf-8') == function_name:
                        body = node.child_by_field_name('body')
                        if body:
                            return body.text.decode('utf-8')
            
            for child in node.children:
                result = find_function(child)
                if result:
                    return result
            return None
        
        return find_function(tree.root_node)
    
    def get_preprocessor_directives(self, file_path: str) -> dict[str, list[PreprocessorDirective]]:
        """Retorna diretivas de preprocessador"""
        _, lines = self._read_file(file_path)
        
        return {
            'includes': self._extract_includes(lines),
            'defines': self._extract_defines(lines),
            'conditionals': self._extract_conditionals(lines)
        }
    
    def _get_function_name(self, declarator):
        """Extract function name from declarator"""
        if declarator.type == 'identifier':
            return declarator
        elif declarator.type == 'function_declarator':
            return self._get_function_name(declarator.child_by_field_name('declarator'))
        elif declarator.type == 'pointer_declarator':
            return self._get_function_name(declarator.child_by_field_name('declarator'))
        return None
    
    def _extract_functions(self, tree, lines: list[str], file_path: str) -> list[FunctionInfo]:
        """Extract all functions"""
        functions = []
        
        def traverse(node):
            if node.type == 'function_definition':
                func_info = self._parse_function(node, lines, file_path)
                if func_info:
                    functions.append(func_info)
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return functions
    
    def _parse_function(self, node, lines: list[str], file_path: str) -> FunctionInfo | None:
        """Parse of a function node"""
        declarator = node.child_by_field_name('declarator')
        if not declarator:
            return None
        
        # Nome da função
        name_node = self._get_function_name(declarator)
        if not name_node:
            return None
        name = name_node.text.decode('utf-8')
        
        # Tipo de retorno
        type_node = node.child_by_field_name('type')
        return_type = type_node.text.decode('utf-8') if type_node else 'void'
        
        # Parâmetros
        parameters = []
        if declarator.type == 'function_declarator':
            params_node = declarator.child_by_field_name('parameters')
            if params_node:
                for param in params_node.children:
                    if param.type == 'parameter_declaration':
                        param_type = param.child_by_field_name('type')
                        param_declarator = param.child_by_field_name('declarator')
                        parameters.append({
                            'type': param_type.text.decode('utf-8') if param_type else '',
                            'name': param_declarator.text.decode('utf-8') if param_declarator else ''
                        })
        
        # Linhas
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Signature
        signature = f"{return_type} {name}({', '.join([p['type'] + ' ' + p['name'] for p in parameters])})"
        
        # Comentário
        doc_comment = self._extract_comment_before(lines, start_line)
        
        return FunctionInfo(
            name=name,
            signature=signature,
            start_line=start_line,
            end_line=end_line,
            return_type=return_type,
            parameters=parameters,
            doc_comment=doc_comment,
            file_path=file_path
        )
    
    def _extract_includes(self, lines: list[str]) -> list[PreprocessorDirective]:
        """Extrai #include"""
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
    
    def _extract_defines(self, lines: list[str]) -> list[PreprocessorDirective]:
        """Extrai #define"""
        defines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#define'):
                # Remove '#define ' prefix
                rest = stripped[7:].strip()

                # Find where the name ends (space, tab, or opening paren)
                space_idx = rest.find(' ')
                tab_idx = rest.find('\t')
                paren_idx = rest.find('(')

                # Get first delimiter position
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
        """Extrai #if, #ifdef, #ifndef, #else, #endif"""
        conditionals = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            for directive in ['#ifdef', '#ifndef', '#if', '#elif', '#else', '#endif']:
                if stripped.startswith(directive):
                    conditionals.append(PreprocessorDirective(
                        type=directive[1:],  # Remove '#'
                        content=stripped,
                        line=i + 1
                    ))
                    break
        return conditionals
    
    def _extract_structs(self, tree, lines: list[str]) -> list[dict[str, Any]]:
        """Extrai structs"""
        structs = []
        
        def traverse(node):
            if node.type == 'struct_specifier':
                name_node = node.child_by_field_name('name')
                if name_node:
                    structs.append({
                        'name': name_node.text.decode('utf-8'),
                        'line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1
                    })
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return structs
    
    def _extract_enums(self, tree, lines: list[str]) -> list[dict[str, Any]]:
        """Extrai enums"""
        enums = []
        
        def traverse(node):
            if node.type == 'enum_specifier':
                name_node = node.child_by_field_name('name')
                if name_node:
                    enums.append({
                        'name': name_node.text.decode('utf-8'),
                        'line': node.start_point[0] + 1
                    })
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return enums
    
    def _extract_typedefs(self, tree, lines: list[str]) -> list[dict[str, Any]]:
        """Extrai typedefs"""
        typedefs = []
        
        def traverse(node):
            if node.type == 'type_definition':
                declarator = node.child_by_field_name('declarator')
                if declarator:
                    typedefs.append({
                        'name': declarator.text.decode('utf-8'),
                        'line': node.start_point[0] + 1
                    })
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return typedefs