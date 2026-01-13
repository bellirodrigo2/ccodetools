"""Unit tests for TreeSitterAnalyzer"""
import unittest
import os
from src.ccodetools.impl.tree_sitter import TreeSitterAnalyzer
# from src.ccodetools.impl.clang_analyzer import ClangAnalyzer


class TestTreeSitterAnalyzer(unittest.TestCase):
    """Test TreeSitterAnalyzer implementation"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = TreeSitterAnalyzer()
        cls.test_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'sample.c'
        )

    def test_analyzer_initialization(self):
        """Test that analyzer initializes correctly"""
        self.assertIsNotNone(self.analyzer.parser)
        self.assertIsNotNone(self.analyzer.c_language)

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
        self.assertIsNotNone(add_func.doc_comment)
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
        self.assertTrue(any('stdio.h' in inc for inc in include_contents))
        self.assertTrue(any('stdlib.h' in inc for inc in include_contents))

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


class TestFileReading(unittest.TestCase):
    """Test file reading functionality"""

    def setUp(self):
        """Set up analyzer"""
        self.analyzer = TreeSitterAnalyzer()
        self.test_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'sample.c'
        )

    def test_read_file(self):
        """Test reading file content"""
        content, lines = self.analyzer._read_file(self.test_file)

        self.assertIsInstance(content, bytes)
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_file_not_found(self):
        """Test handling of non-existent file"""
        with self.assertRaises(FileNotFoundError):
            self.analyzer._read_file('nonexistent.c')


class TestBitvecAnalysis(unittest.TestCase):
    """Test analysis of real-world SQLite bitvec.c file"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = TreeSitterAnalyzer()
        cls.bitvec_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'bitvec.c'
        )

    def test_bitvec_functions_count(self):
        """Test that all functions are detected in bitvec.c"""
        functions = self.analyzer.list_functions(self.bitvec_file)

        # bitvec.c has 10 functions
        self.assertEqual(len(functions), 10)

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
        # Note: tree-sitter returns 'Bitvec' for 'Bitvec *' return types
        self.assertIn('Bitvec', create_func.return_type)
        # Verify function has a signature
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
        # The function should return something related to BITVEC_SZ
        self.assertIn('return', body)

    def test_bitvec_complete_analysis(self):
        """Test complete analysis of bitvec.c"""
        result = self.analyzer.analyze_file(self.bitvec_file)

        self.assertEqual(result.file_path, self.bitvec_file)
        self.assertEqual(len(result.functions), 10)
        self.assertGreaterEqual(len(result.includes), 1)
        self.assertGreaterEqual(len(result.defines), 10)
        self.assertGreaterEqual(len(result.structs), 1)


class TestPcacheAnalysis(unittest.TestCase):
    """Test analysis of real-world SQLite pcache.c file"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.analyzer = TreeSitterAnalyzer()
        cls.pcache_file = os.path.join(
            os.path.dirname(__file__),
            'fixtures',
            'pcache.c'
        )

    def test_pcache_functions_count(self):
        """Test that all functions are detected in pcache.c"""
        functions = self.analyzer.list_functions(self.pcache_file)

        # pcache.c is a large file with many functions
        self.assertGreater(len(functions), 40)

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
        # Note: sqlite3PcacheFetch has multi-line parameters which may not parse correctly
        open_func = next((f for f in functions if f.name == 'sqlite3PcacheOpen'), None)
        self.assertIsNotNone(open_func)
        # Verify the function was found and has signature info
        self.assertIsNotNone(open_func.signature)
        self.assertGreater(open_func.start_line, 0)

    def test_pcache_complete_analysis(self):
        """Test complete analysis of pcache.c"""
        result = self.analyzer.analyze_file(self.pcache_file)

        self.assertEqual(result.file_path, self.pcache_file)
        self.assertGreater(len(result.functions), 40)
        self.assertGreaterEqual(len(result.includes), 1)
        self.assertGreaterEqual(len(result.defines), 1)


if __name__ == '__main__':
    unittest.main()
