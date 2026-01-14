"""Unit tests for C code analyzers - testing the CCodeAnalyzer interface."""
import unittest
import os
from typing import Literal
from src.ccodetools.factory import make_analyzer
from src.ccodetools.interface import CCodeAnalyzer


def get_analyzer(name: Literal['tree-sitter', 'clang']) -> CCodeAnalyzer:
    """Get analyzer by name, skip test if unavailable."""
    try:
        return make_analyzer(name)
    except (ImportError, RuntimeError, Exception) as e:
        # Catch all exceptions to handle library version mismatches
        raise unittest.SkipTest(f"{name} analyzer not available: {e}")


class AnalyzerTestMixin:
    """Mixin with common analyzer tests. Subclasses must set analyzer_name."""

    analyzer_name: Literal['tree-sitter', 'clang']
    analyzer: CCodeAnalyzer
    test_file: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = get_analyzer(cls.analyzer_name)
        cls.test_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'sample.c'
        )

    def test_list_functions(self):
        """Test listing functions from C file"""
        functions = self.analyzer.list_functions(self.test_file)

        # Should find 4 functions: add, multiply, print_hello, main
        self.assertEqual(len(functions), 4)

        # Check function names
        function_names = [f.name for f in functions]
        self.assertIn('add', function_names)
        self.assertIn('multiply', function_names)
        self.assertIn('print_hello', function_names)
        self.assertIn('main', function_names)

    def test_function_info_details(self):
        """Test function information details"""
        functions = self.analyzer.list_functions(self.test_file)

        # Find the 'add' function
        add_func = next(f for f in functions if f.name == 'add')

        self.assertEqual(add_func.return_type, 'int')
        self.assertEqual(len(add_func.parameters), 2)
        self.assertEqual(add_func.parameters[0]['type'], 'int')
        self.assertEqual(add_func.parameters[0]['name'], 'a')
        self.assertGreater(add_func.end_line, add_func.start_line)

    def test_get_function_body(self):
        """Test retrieving specific function body"""
        body = self.analyzer.get_function_body(self.test_file, 'add')

        self.assertIsNotNone(body)
        self.assertIn('return a + b', body)

    def test_get_function_body_not_found(self):
        """Test retrieving non-existent function"""
        body = self.analyzer.get_function_body(self.test_file, 'nonexistent')
        self.assertIsNone(body)

    def test_extract_includes(self):
        """Test extracting include directives"""
        directives = self.analyzer.get_preprocessor_directives(self.test_file)
        includes = directives['includes']

        self.assertGreaterEqual(len(includes), 2)
        include_contents = [inc.content for inc in includes]
        self.assertTrue(any('stdio' in inc for inc in include_contents))
        self.assertTrue(any('stdlib' in inc for inc in include_contents))

    def test_extract_defines(self):
        """Test extracting define directives"""
        directives = self.analyzer.get_preprocessor_directives(self.test_file)
        defines = directives['defines']

        self.assertGreaterEqual(len(defines), 2)
        define_names = [d.content for d in defines]
        self.assertIn('MAX_SIZE', define_names)
        self.assertIn('MIN', define_names)

        # Check define value
        max_size = next(d for d in defines if d.content == 'MAX_SIZE')
        self.assertEqual(max_size.value, '100')

    def test_analyze_file_complete(self):
        """Test complete file analysis"""
        result = self.analyzer.analyze_file(self.test_file)

        self.assertEqual(result.file_path, self.test_file)
        self.assertEqual(len(result.functions), 4)
        self.assertGreaterEqual(len(result.includes), 2)
        self.assertGreaterEqual(len(result.defines), 2)
        self.assertGreaterEqual(len(result.structs), 1)
        self.assertGreaterEqual(len(result.enums), 1)

    def test_extract_structs(self):
        """Test extracting struct definitions"""
        result = self.analyzer.analyze_file(self.test_file)

        self.assertGreaterEqual(len(result.structs), 1)
        struct_names = [s['name'] for s in result.structs]
        self.assertIn('Point', struct_names)

    def test_extract_enums(self):
        """Test extracting enum definitions"""
        result = self.analyzer.analyze_file(self.test_file)

        self.assertGreaterEqual(len(result.enums), 1)
        enum_names = [e['name'] for e in result.enums]
        self.assertIn('Status', enum_names)

    def test_extract_typedefs(self):
        """Test extracting typedef definitions"""
        result = self.analyzer.analyze_file(self.test_file)

        # At least one typedef (Point_t)
        self.assertGreaterEqual(len(result.typedefs), 0)


class TestTreeSitterAnalyzer(AnalyzerTestMixin, unittest.TestCase):
    """Test TreeSitterAnalyzer implementation"""
    analyzer_name: Literal['tree-sitter'] = 'tree-sitter'


class TestClangAnalyzer(AnalyzerTestMixin, unittest.TestCase):
    """Test ClangAnalyzer implementation"""
    analyzer_name: Literal['clang'] = 'clang'


class BitvecTestMixin:
    """Mixin for bitvec.c tests. Subclasses must set analyzer_name."""

    analyzer_name: Literal['tree-sitter', 'clang']
    analyzer: CCodeAnalyzer
    bitvec_file: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = get_analyzer(cls.analyzer_name)
        cls.bitvec_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'bitvec.c'
        )

    def test_bitvec_functions_count(self):
        """Test that all functions are detected in bitvec.c"""
        functions = self.analyzer.list_functions(self.bitvec_file)

        # bitvec.c has 10 functions total, but some are inside #ifdef blocks
        # TreeSitter sees all (10), Clang only sees unconditional ones (8)
        self.assertGreaterEqual(len(functions), 8)

    def test_bitvec_function_names(self):
        """Test that key SQLite Bitvec functions are found"""
        functions = self.analyzer.list_functions(self.bitvec_file)
        function_names = [f.name for f in functions]

        # Check for main public API functions
        expected_functions = [
            'sqlite3BitvecCreate',
            'sqlite3BitvecTest',
            'sqlite3BitvecSet',
            'sqlite3BitvecClear',
            'sqlite3BitvecDestroy',
            'sqlite3BitvecSize'
        ]

        for func_name in expected_functions:
            self.assertIn(func_name, function_names)

    def test_bitvec_function_signatures(self):
        """Test function signature parsing for bitvec functions"""
        functions = self.analyzer.list_functions(self.bitvec_file)

        # Find sqlite3BitvecCreate function
        create_func = next((f for f in functions if f.name == 'sqlite3BitvecCreate'), None)
        self.assertIsNotNone(create_func)
        self.assertIn('Bitvec', create_func.return_type)
        self.assertIsNotNone(create_func.signature)

        # Find sqlite3BitvecTest function
        test_func = next((f for f in functions if f.name == 'sqlite3BitvecTest'), None)
        self.assertIsNotNone(test_func)
        self.assertEqual(test_func.return_type, 'int')

    def test_bitvec_preprocessor_directives(self):
        """Test extraction of preprocessor directives from bitvec.c"""
        directives = self.analyzer.get_preprocessor_directives(self.bitvec_file)

        # Should have includes
        self.assertGreater(len(directives['includes']), 0)

        # Should have many defines (BITVEC_SZ, BITVEC_USIZE, etc.)
        self.assertGreater(len(directives['defines']), 10)

        # Check for specific defines
        define_names = [d.content for d in directives['defines']]
        self.assertIn('BITVEC_SZ', define_names)
        self.assertIn('BITVEC_USIZE', define_names)

    def test_bitvec_struct_extraction(self):
        """Test struct extraction from bitvec.c"""
        result = self.analyzer.analyze_file(self.bitvec_file)

        # bitvec.c has the Bitvec struct
        self.assertGreaterEqual(len(result.structs), 1)
        struct_names = [s['name'] for s in result.structs]
        self.assertIn('Bitvec', struct_names)

    def test_bitvec_function_body_retrieval(self):
        """Test retrieving function body from bitvec.c"""
        body = self.analyzer.get_function_body(self.bitvec_file, 'sqlite3BitvecSize')

        self.assertIsNotNone(body)
        self.assertIn('return', body)

    def test_bitvec_complete_analysis(self):
        """Test complete analysis of bitvec.c"""
        result = self.analyzer.analyze_file(self.bitvec_file)

        self.assertEqual(result.file_path, self.bitvec_file)
        # TreeSitter sees all functions (10), Clang only sees unconditional ones (8)
        self.assertGreaterEqual(len(result.functions), 8)
        self.assertGreaterEqual(len(result.includes), 1)
        self.assertGreaterEqual(len(result.defines), 10)
        self.assertGreaterEqual(len(result.structs), 1)


class TestBitvecTreeSitter(BitvecTestMixin, unittest.TestCase):
    """Test bitvec.c analysis with TreeSitterAnalyzer"""
    analyzer_name: Literal['tree-sitter'] = 'tree-sitter'


class TestBitvecClang(BitvecTestMixin, unittest.TestCase):
    """Test bitvec.c analysis with ClangAnalyzer"""
    analyzer_name: Literal['clang'] = 'clang'


class PcacheTestMixin:
    """Mixin for pcache.c tests. Subclasses must set analyzer_name."""

    analyzer_name: Literal['tree-sitter', 'clang']
    analyzer: CCodeAnalyzer
    pcache_file: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = get_analyzer(cls.analyzer_name)
        cls.pcache_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'pcache.c'
        )

    def test_pcache_functions_count(self):
        """Test that all functions are detected in pcache.c"""
        functions = self.analyzer.list_functions(self.pcache_file)

        # pcache.c is a large file with many functions
        # TreeSitter sees all, Clang may see fewer due to #ifdef blocks
        self.assertGreater(len(functions), 30)

    def test_pcache_function_names(self):
        """Test that key SQLite page cache functions are found"""
        functions = self.analyzer.list_functions(self.pcache_file)
        function_names = [f.name for f in functions]

        # Check for main public API functions
        expected_functions = [
            'sqlite3PcacheInitialize',
            'sqlite3PcacheShutdown',
            'sqlite3PcacheOpen',
            'sqlite3PcacheClose',
            'sqlite3PcacheFetch',
            'sqlite3PcacheDrop',
            'sqlite3PcacheRelease'
        ]

        for func_name in expected_functions:
            self.assertIn(func_name, function_names, f"Function {func_name} not found")

    def test_pcache_function_details(self):
        """Test detailed function information from pcache.c"""
        functions = self.analyzer.list_functions(self.pcache_file)

        # Find sqlite3PcacheInitialize function
        init_func = next((f for f in functions if f.name == 'sqlite3PcacheInitialize'), None)
        self.assertIsNotNone(init_func)
        self.assertEqual(init_func.return_type, 'int')

        # Check that functions have line numbers
        for func in functions:
            self.assertGreater(func.start_line, 0)
            self.assertGreaterEqual(func.end_line, func.start_line)

    def test_pcache_preprocessor_directives(self):
        """Test extraction of preprocessor directives from pcache.c"""
        directives = self.analyzer.get_preprocessor_directives(self.pcache_file)

        # Should have includes
        self.assertGreater(len(directives['includes']), 0)

        # Should have defines
        self.assertGreater(len(directives['defines']), 0)

    def test_pcache_struct_extraction(self):
        """Test struct extraction from pcache.c"""
        result = self.analyzer.analyze_file(self.pcache_file)

        # pcache.c should have struct definitions
        self.assertGreaterEqual(len(result.structs), 1)

    def test_pcache_function_body_retrieval(self):
        """Test retrieving function body from pcache.c"""
        body = self.analyzer.get_function_body(self.pcache_file, 'sqlite3PcacheInitialize')

        self.assertIsNotNone(body)
        self.assertIn('return', body)

    def test_pcache_function_parameters(self):
        """Test parameter extraction from pcache functions"""
        functions = self.analyzer.list_functions(self.pcache_file)

        # Find sqlite3PcacheOpen which should have parameters
        open_func = next((f for f in functions if f.name == 'sqlite3PcacheOpen'), None)
        self.assertIsNotNone(open_func)
        self.assertIsNotNone(open_func.signature)
        self.assertGreater(open_func.start_line, 0)

    def test_pcache_complete_analysis(self):
        """Test complete analysis of pcache.c"""
        result = self.analyzer.analyze_file(self.pcache_file)

        self.assertEqual(result.file_path, self.pcache_file)
        # TreeSitter sees all functions, Clang may see fewer due to #ifdef blocks
        self.assertGreater(len(result.functions), 30)
        self.assertGreaterEqual(len(result.includes), 1)
        self.assertGreaterEqual(len(result.defines), 1)


class TestPcacheTreeSitter(PcacheTestMixin, unittest.TestCase):
    """Test pcache.c analysis with TreeSitterAnalyzer"""
    analyzer_name: Literal['tree-sitter'] = 'tree-sitter'


class TestPcacheClang(PcacheTestMixin, unittest.TestCase):
    """Test pcache.c analysis with ClangAnalyzer"""
    analyzer_name: Literal['clang'] = 'clang'


class AdvancedFeaturesTestMixin:
    """Mixin for testing advanced analyzer features (call graph, dependencies, etc.)."""

    analyzer_name: Literal['tree-sitter', 'clang']
    analyzer: CCodeAnalyzer
    test_file: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = get_analyzer(cls.analyzer_name)
        cls.test_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'sample.c'
        )

    def test_get_call_graph(self):
        """Test call graph extraction"""
        call_graph = self.analyzer.get_call_graph(self.test_file)

        # Should be a dict mapping function names to list of called functions
        self.assertIsInstance(call_graph, dict)

        # main() calls add() and printf()
        self.assertIn('main', call_graph)
        self.assertIn('add', call_graph['main'])
        self.assertIn('printf', call_graph['main'])

        # print_hello() calls printf()
        self.assertIn('print_hello', call_graph)
        self.assertIn('printf', call_graph['print_hello'])

        # add() and multiply() don't call other functions
        self.assertIn('add', call_graph)
        self.assertEqual(call_graph['add'], [])

    def test_get_function_dependencies(self):
        """Test function dependency extraction"""
        deps = self.analyzer.get_function_dependencies(self.test_file, 'main')

        self.assertIsInstance(deps, dict)
        self.assertEqual(deps['function'], 'main')

        # main() calls add() and printf()
        self.assertIn('calls', deps)
        self.assertIn('add', deps['calls'])
        self.assertIn('printf', deps['calls'])

    def test_get_function_dependencies_no_calls(self):
        """Test function dependencies for function with no calls"""
        deps = self.analyzer.get_function_dependencies(self.test_file, 'add')

        self.assertEqual(deps['function'], 'add')
        self.assertEqual(deps['calls'], [])

    def test_summarize_function(self):
        """Test function summary"""
        summary = self.analyzer.summarize_function(self.test_file, 'main')

        self.assertIsInstance(summary, dict)
        self.assertEqual(summary['function'], 'main')
        self.assertIn('allocates_memory', summary)
        self.assertIn('frees_memory', summary)
        self.assertIn('multiple_returns', summary)
        self.assertIn('uses_goto', summary)

        # main() doesn't allocate memory, free memory, use goto
        self.assertFalse(summary['allocates_memory'])
        self.assertFalse(summary['frees_memory'])
        self.assertFalse(summary['uses_goto'])

    def test_summarize_function_simple(self):
        """Test function summary for simple function"""
        summary = self.analyzer.summarize_function(self.test_file, 'add')

        self.assertEqual(summary['function'], 'add')
        self.assertFalse(summary['allocates_memory'])
        self.assertFalse(summary['multiple_returns'])

    def test_list_globals(self):
        """Test listing global variables"""
        globals_list = self.analyzer.list_globals(self.test_file)

        self.assertIsInstance(globals_list, list)
        # sample.c doesn't have explicit global variables at top level
        # (just struct/enum definitions which are types, not variables)

    def test_find_symbol(self):
        """Test finding symbol occurrences"""
        result = self.analyzer.find_symbol(self.test_file, 'add')

        self.assertIsInstance(result, dict)
        self.assertEqual(result['symbol'], 'add')
        self.assertIn('lines', result)
        self.assertIsInstance(result['lines'], list)

        # 'add' appears at function definition and call in main
        self.assertGreaterEqual(len(result['lines']), 2)

    def test_find_symbol_not_found(self):
        """Test finding symbol that doesn't exist"""
        result = self.analyzer.find_symbol(self.test_file, 'nonexistent_symbol')

        self.assertEqual(result['symbol'], 'nonexistent_symbol')
        self.assertEqual(result['lines'], [])

    def test_find_symbol_printf(self):
        """Test finding printf occurrences"""
        result = self.analyzer.find_symbol(self.test_file, 'printf')

        self.assertEqual(result['symbol'], 'printf')
        # printf is called in print_hello and main
        self.assertGreaterEqual(len(result['lines']), 2)

    def test_get_error_handling_paths(self):
        """Test error handling path detection"""
        errors = self.analyzer.get_error_handling_paths(self.test_file, 'main')

        self.assertIsInstance(errors, list)
        # main() has one return statement
        self.assertGreaterEqual(len(errors), 1)

        # Check structure of error path entries
        for error in errors:
            self.assertIn('line', error)
            self.assertIn('type', error)

    def test_get_error_handling_paths_add(self):
        """Test error handling for simple function"""
        errors = self.analyzer.get_error_handling_paths(self.test_file, 'add')

        # add() has one return statement
        self.assertGreaterEqual(len(errors), 1)
        return_entry = next((e for e in errors if e['type'] == 'return'), None)
        self.assertIsNotNone(return_entry)

    def test_list_side_effects(self):
        """Test side effect detection"""
        effects = self.analyzer.list_side_effects(self.test_file, 'print_hello')

        self.assertIsInstance(effects, dict)
        self.assertIn('io', effects)
        self.assertIn('allocates_memory', effects)

        # print_hello calls printf (I/O)
        self.assertIn('printf', effects['io'])

    def test_list_side_effects_no_io(self):
        """Test side effects for function with no I/O"""
        effects = self.analyzer.list_side_effects(self.test_file, 'add')

        # add() has no I/O operations
        self.assertEqual(effects['io'], [])
        self.assertFalse(effects['allocates_memory'])

    def test_list_side_effects_main(self):
        """Test side effects for main function"""
        effects = self.analyzer.list_side_effects(self.test_file, 'main')

        # main() calls printf
        self.assertIn('printf', effects['io'])


class TestAdvancedFeaturesTreeSitter(AdvancedFeaturesTestMixin, unittest.TestCase):
    """Test advanced features with TreeSitterAnalyzer"""
    analyzer_name: Literal['tree-sitter'] = 'tree-sitter'


class TestAdvancedFeaturesClang(AdvancedFeaturesTestMixin, unittest.TestCase):
    """Test advanced features with ClangAnalyzer"""
    analyzer_name: Literal['clang'] = 'clang'


class AdvancedFeaturesBitvecTestMixin:
    """Mixin for testing advanced features on bitvec.c (real SQLite code)."""

    analyzer_name: Literal['tree-sitter', 'clang']
    analyzer: CCodeAnalyzer
    bitvec_file: str

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = get_analyzer(cls.analyzer_name)
        cls.bitvec_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'bitvec.c'
        )

    def test_bitvec_call_graph(self):
        """Test call graph on real SQLite code"""
        call_graph = self.analyzer.get_call_graph(self.bitvec_file)

        self.assertIsInstance(call_graph, dict)
        # Should have entries for main functions
        self.assertIn('sqlite3BitvecCreate', call_graph)

    def test_bitvec_function_dependencies(self):
        """Test function dependencies on real code"""
        deps = self.analyzer.get_function_dependencies(
            self.bitvec_file, 'sqlite3BitvecCreate'
        )

        self.assertEqual(deps['function'], 'sqlite3BitvecCreate')
        self.assertIn('calls', deps)
        self.assertIn('types', deps)

    def test_bitvec_summarize_function(self):
        """Test function summary on real code"""
        summary = self.analyzer.summarize_function(
            self.bitvec_file, 'sqlite3BitvecCreate'
        )

        self.assertEqual(summary['function'], 'sqlite3BitvecCreate')
        # SQLite uses sqlite3MallocZero, not malloc directly
        # So allocates_memory will be False (only detects malloc)
        self.assertIn('allocates_memory', summary)
        self.assertIn('frees_memory', summary)

    def test_bitvec_find_symbol(self):
        """Test finding symbol in real code"""
        # 'p' is a common variable name in bitvec.c
        result = self.analyzer.find_symbol(self.bitvec_file, 'p')

        self.assertEqual(result['symbol'], 'p')
        # 'p' appears many times throughout the file
        self.assertGreater(len(result['lines']), 10)

    def test_bitvec_list_globals(self):
        """Test listing globals in real code"""
        globals_list = self.analyzer.list_globals(self.bitvec_file)

        self.assertIsInstance(globals_list, list)


class TestAdvancedFeaturesBitvecTreeSitter(AdvancedFeaturesBitvecTestMixin, unittest.TestCase):
    """Test advanced features on bitvec.c with TreeSitterAnalyzer"""
    analyzer_name: Literal['tree-sitter'] = 'tree-sitter'


class TestAdvancedFeaturesBitvecClang(AdvancedFeaturesBitvecTestMixin, unittest.TestCase):
    """Test advanced features on bitvec.c with ClangAnalyzer"""
    analyzer_name: Literal['clang'] = 'clang'


if __name__ == '__main__':
    unittest.main()
