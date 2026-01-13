from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from .interface import CCodeAnalyzer
from .impl.tree_sitter import TreeSitterAnalyzer
import json

# Inicializa analyzer (pode trocar para ClangAnalyzer quando implementado)
analyzer: CCodeAnalyzer = TreeSitterAnalyzer()

app = Server("c-code-analyzer")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_c_file",
            description="Analisa um arquivo C e retorna estrutura completa: funções, includes, defines, structs, enums, typedefs",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Caminho do arquivo C"},
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="list_functions",
            description="Lista apenas as funções com signatures, parâmetros e comentários",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Caminho do arquivo C"},
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="get_function_body",
            description="Retorna o corpo completo de uma função específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Caminho do arquivo C"},
                    "function_name": {"type": "string", "description": "Nome da função"},
                },
                "required": ["file_path", "function_name"]
            }
        ),
        Tool(
            name="get_preprocessor_directives",
            description="Lista todas as diretivas de preprocessador: includes, defines, condicionais",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Caminho do arquivo C"},
                },
                "required": ["file_path"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "analyze_c_file":
            result = analyzer.analyze_file(arguments["file_path"])
            return [TextContent(
                type="text",
                text=json.dumps({
                    "file_path": result.file_path,
                    "functions": [
                        {
                            "name": f.name,
                            "signature": f.signature,
                            "start_line": f.start_line,
                            "end_line": f.end_line,
                            "return_type": f.return_type,
                            "parameters": f.parameters,
                            "doc_comment": f.doc_comment
                        } for f in result.functions
                    ],
                    "includes": [{"content": d.content, "line": d.line} for d in result.includes],
                    "defines": [{"content": d.content, "value": d.value, "line": d.line} for d in result.defines],
                    "conditionals": [{"type": d.type, "content": d.content, "line": d.line} for d in result.conditionals],
                    "structs": result.structs,
                    "enums": result.enums,
                    "typedefs": result.typedefs
                }, indent=2)
            )]
        
        elif name == "list_functions":
            functions = analyzer.list_functions(arguments["file_path"])
            return [TextContent(
                type="text",
                text=json.dumps([
                    {
                        "name": f.name,
                        "signature": f.signature,
                        "start_line": f.start_line,
                        "end_line": f.end_line,
                        "doc_comment": f.doc_comment
                    } for f in functions
                ], indent=2)
            )]
        
        elif name == "get_function_body":
            body = analyzer.get_function_body(
                arguments["file_path"],
                arguments["function_name"]
            )
            return [TextContent(
                type="text",
                text=body if body else f"Função '{arguments['function_name']}' não encontrada"
            )]
        
        elif name == "get_preprocessor_directives":
            directives = analyzer.get_preprocessor_directives(arguments["file_path"])
            return [TextContent(
                type="text",
                text=json.dumps({
                    "includes": [{"content": d.content, "line": d.line} for d in directives['includes']],
                    "defines": [{"content": d.content, "value": d.value, "line": d.line} for d in directives['defines']],
                    "conditionals": [{"type": d.type, "content": d.content, "line": d.line} for d in directives['conditionals']]
                }, indent=2)
            )]
        
        else:
            raise ValueError(f"Tool desconhecida: {name}")
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Erro ao executar {name}: {str(e)}"
        )]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())