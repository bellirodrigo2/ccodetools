# C Code Analyzer MCP Server

An MCP (Model Context Protocol) server for efficient C code analysis using tree-sitter. This tool enables Claude and other MCP clients to analyze C code more efficiently than reading large files in chunks.

## Features

- **Function Analysis**: Extract function signatures, parameters, return types, and documentation
- **Preprocessor Directives**: Parse includes, defines, and conditional compilation directives
- **Structure Extraction**: Identify structs, enums, and typedefs
- **Efficient Parsing**: Uses tree-sitter for fast, accurate parsing of C code

## Installation

```bash
# Install in development mode
pip install -e .
```

## Requirements

- Python 3.12+
- tree-sitter >= 0.23.0
- tree-sitter-c >= 0.23.0
- mcp >= 1.0.0

## Usage

### Setting Up with VSCode Claude Code Extension

1. **Install dependencies in the project**:
   ```bash
   cd c:\Users\RBELLI\Desktop\code\ccodetools
   pip install -e .
   ```

2. **Configure Claude Code to use this MCP server**:

   Open your Claude Code MCP settings file. You can access it by:
   - Opening Windows Explorer and pasting this path: `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\`
   - Then open or create the file: `cline_mcp_settings.json`
   - Full path: `C:\Users\RBELLI\AppData\Roaming\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

   **Note:** If the file doesn't exist, create it with empty JSON: `{}`

3. **Add this configuration** to the `mcpServers` section:
   ```json
   {
     "mcpServers": {
       "c-code-analyzer": {
         "command": "python",
         "args": ["-m", "src"],
         "cwd": "c:\\Users\\RBELLI\\Desktop\\code\\ccodetools",
         "env": {}
       }
     }
   }
   ```

4. **Restart VSCode** or reload the Claude Code extension

5. **Verify the server is running**:
   - Open Claude Code
   - The C Code Analyzer tools should now be available
   - Claude can now use these tools automatically when analyzing C code

### Running as Standalone MCP Server

```bash
python -m src
```

### Available MCP Tools

Once configured, Claude Code can use these tools automatically:

1. **analyze_c_file**
   - Complete file analysis including functions, preprocessor directives, structs, enums
   - Input: `file_path` (string)
   - Returns: JSON with complete file structure

2. **list_functions**
   - Quick listing of all functions with signatures and line numbers
   - Input: `file_path` (string)
   - Returns: JSON array of function information

3. **get_function_body**
   - Retrieve the complete body of a specific function
   - Input: `file_path` (string), `function_name` (string)
   - Returns: Function body as text

4. **get_preprocessor_directives**
   - Extract all preprocessor directives (includes, defines, conditionals)
   - Input: `file_path` (string)
   - Returns: JSON with categorized directives

### Example Usage in Claude Code

When you're working with C code in VSCode with Claude Code:

```
You: "Analyze the functions in src/main.c"
Claude: [Uses list_functions tool automatically]

You: "Show me the implementation of the parse_config function"
Claude: [Uses get_function_body tool automatically]

You: "What includes and defines are in this file?"
Claude: [Uses get_preprocessor_directives tool automatically]
```

## Testing

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_tree_sitter_analyzer

# Run with verbose output
python -m unittest discover tests -v
```

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py           # MCP server implementation
│   ├── interface.py        # Protocol and data classes
│   └── impl/
│       ├── __init__.py
│       └── tree_sitter.py  # Tree-sitter analyzer implementation
├── tests/
│   ├── __init__.py
│   ├── test_interface.py
│   ├── test_tree_sitter_analyzer.py
│   └── fixtures/
│       └── sample.c
├── pyproject.toml
└── README.md
```

## Development

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run type checking
mypy src
```

## License

MIT
