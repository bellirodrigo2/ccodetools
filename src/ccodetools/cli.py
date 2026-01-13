import click
import json
from pprint import pprint
from dataclasses import asdict, is_dataclass

from .impl.tree_sitter import TreeSitterAnalyzer


# Registry de analyzers
ANALYZERS = {
    "tree_sitter": TreeSitterAnalyzer,
}


def get_analyzer(name: str):
    if name not in ANALYZERS:
        raise click.ClickException(
            f"Analyzer '{name}' não encontrado. "
            f"Disponíveis: {', '.join(ANALYZERS.keys())}"
        )
    return ANALYZERS[name]()


def serialize(obj):
    """Converte dataclasses e listas para dict (JSON-friendly)"""
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [serialize(o) for o in obj]
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    return obj


@click.group()
@click.option(
    "--analyzer",
    default="tree_sitter",
    help="Nome do analyzer a usar"
)
@click.pass_context
def cli(ctx, analyzer):
    """CLI para análise de código C"""
    ctx.ensure_object(dict)
    ctx.obj["analyzer"] = get_analyzer(analyzer)


# -------------------------------------------------
# analyze_c_file
# -------------------------------------------------
@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Saída em JSON")
@click.pass_context
def analyze_c_file(ctx, file_path, as_json):
    """Analisa completamente um arquivo C"""
    analyzer = ctx.obj["analyzer"]
    result = analyzer.analyze_file(file_path)

    if as_json:
        click.echo(json.dumps(serialize(result), indent=2, ensure_ascii=False))
    else:
        pprint(result)


# -------------------------------------------------
# list_functions
# -------------------------------------------------
@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Saída em JSON")
@click.pass_context
def list_functions(ctx, file_path, as_json):
    """Lista funções do arquivo"""
    analyzer = ctx.obj["analyzer"]
    functions = analyzer.list_functions(file_path)

    if as_json:
        click.echo(json.dumps(serialize(functions), indent=2, ensure_ascii=False))
    else:
        pprint(functions)


# -------------------------------------------------
# get_function_body
# -------------------------------------------------
@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("function_name", type=str)
@click.pass_context
def get_function_body(ctx, file_path, function_name):
    """Mostra o corpo de uma função"""
    analyzer = ctx.obj["analyzer"]
    body = analyzer.get_function_body(file_path, function_name)

    if body is None:
        raise click.ClickException(f"Função '{function_name}' não encontrada")

    click.echo(body)


# -------------------------------------------------
# get_preprocessor_directives
# -------------------------------------------------
@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Saída em JSON")
@click.pass_context
def get_preprocessor_directives(ctx, file_path, as_json):
    """Lista diretivas de pré-processador"""
    analyzer = ctx.obj["analyzer"]
    directives = analyzer.get_preprocessor_directives(file_path)

    if as_json:
        click.echo(json.dumps(serialize(directives), indent=2, ensure_ascii=False))
    else:
        pprint(directives)


if __name__ == "__main__":
    cli()
