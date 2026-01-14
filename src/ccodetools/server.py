from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from .interface import CCodeAnalyzer
from .factory import make_analyzer
import json

analyzer: CCodeAnalyzer = make_analyzer('tree-sitter')

app = Server("c-code-analyzer")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_c_file",
            description="Analisa um arquivo C e retorna estrutura completa",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"]
            }
        ),

        Tool(
            name="list_functions",
            description="Lista funções com signature, linhas e comentários",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"]
            }
        ),

        Tool(
            name="get_function_body",
            description="Retorna o corpo completo de uma função",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "function_name": {"type": "string"},
                },
                "required": ["file_path", "function_name"]
            }
        ),

        Tool(
            name="get_preprocessor_directives",
            description="Lista diretivas de preprocessador",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"]
            }
        ),

        Tool(
            name="get_call_graph",
            description="Retorna o grafo de chamadas por função",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"]
            }
        ),

        Tool(
            name="get_function_dependencies",
            description="Retorna dependências estruturais de uma função",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "function_name": {"type": "string"},
                },
                "required": ["file_path", "function_name"]
            }
        ),

        Tool(
            name="summarize_function",
            description="Resumo estrutural heurístico de uma função",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "function_name": {"type": "string"},
                },
                "required": ["file_path", "function_name"]
            }
        ),

        Tool(
            name="list_globals",
            description="Lista variáveis globais do arquivo",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                },
                "required": ["file_path"]
            }
        ),

        Tool(
            name="find_symbol",
            description="Busca ocorrências de um símbolo no arquivo",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "symbol": {"type": "string"},
                },
                "required": ["file_path", "symbol"]
            }
        ),

        Tool(
            name="get_error_handling_paths",
            description="Detecta caminhos de erro em uma função",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "function_name": {"type": "string"},
                },
                "required": ["file_path", "function_name"]
            }
        ),

        Tool(
            name="list_side_effects",
            description="Lista efeitos colaterais de uma função",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "function_name": {"type": "string"},
                },
                "required": ["file_path", "function_name"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        # ===== EXISTENTES =====

        if name == "analyze_c_file":
            result = analyzer.analyze_file(arguments["file_path"])
            return [TextContent(
                type="text",
                text=json.dumps(result, default=lambda o: o.__dict__, indent=2)
            )]

        elif name == "list_functions":
            functions = analyzer.list_functions(arguments["file_path"])
            return [TextContent(
                type="text",
                text=json.dumps([f.__dict__ for f in functions], indent=2)
            )]

        elif name == "get_function_body":
            body = analyzer.get_function_body(
                arguments["file_path"],
                arguments["function_name"]
            )
            return [TextContent(type="text", text=body or "Função não encontrada")]

        elif name == "get_preprocessor_directives":
            directives = analyzer.get_preprocessor_directives(arguments["file_path"])
            return [TextContent(
                type="text",
                text=json.dumps(directives, default=lambda o: o.__dict__, indent=2)
            )]

        elif name == "get_call_graph":
            return [TextContent(
                type="text",
                text=json.dumps(
                    analyzer.get_call_graph(arguments["file_path"]),
                    indent=2
                )
            )]

        elif name == "get_function_dependencies":
            return [TextContent(
                type="text",
                text=json.dumps(
                    analyzer.get_function_dependencies(
                        arguments["file_path"],
                        arguments["function_name"]
                    ),
                    indent=2
                )
            )]

        elif name == "summarize_function":
            return [TextContent(
                type="text",
                text=json.dumps(
                    analyzer.summarize_function(
                        arguments["file_path"],
                        arguments["function_name"]
                    ),
                    indent=2
                )
            )]

        elif name == "list_globals":
            return [TextContent(
                type="text",
                text=json.dumps(
                    analyzer.list_globals(arguments["file_path"]),
                    indent=2
                )
            )]

        elif name == "find_symbol":
            return [TextContent(
                type="text",
                text=json.dumps(
                    analyzer.find_symbol(
                        arguments["file_path"],
                        arguments["symbol"]
                    ),
                    indent=2
                )
            )]

        elif name == "get_error_handling_paths":
            return [TextContent(
                type="text",
                text=json.dumps(
                    analyzer.get_error_handling_paths(
                        arguments["file_path"],
                        arguments["function_name"]
                    ),
                    indent=2
                )
            )]

        elif name == "list_side_effects":
            return [TextContent(
                type="text",
                text=json.dumps(
                    analyzer.list_side_effects(
                        arguments["file_path"],
                        arguments["function_name"]
                    ),
                    indent=2
                )
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
