"""Linha de comando do radar.

    radar coletar
    radar listar --uf SC --termo "guarda municipal"
    radar web
"""
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from radar import acervo, servico
from radar.util import formatar_data

app = typer.Typer(help="Radar de concursos publicos (uso pessoal)", no_args_is_help=True)
console = Console()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@app.command()
def coletar() -> None:
    """Busca nas fontes e grava os concursos novos e os que mudaram."""
    with console.status("Coletando..."):
        resultados = servico.coletar_tudo()

    houve_erro = False
    for resultado in resultados:
        if resultado.erro:
            houve_erro = True
            console.print(f"[red]{resultado}[/]")
        else:
            console.print(f"[green]{resultado}[/]")

    if houve_erro:
        console.print(
            "\n[yellow]Uma ou mais fontes falharam.[/] As demais foram gravadas "
            "normalmente."
        )


@app.command()
def listar(
    uf: str = typer.Option(None, help="Sigla do estado, ex: SC"),
    banca: str = typer.Option(None, help="Nome da banca, ex: FEPESE"),
    termo: str = typer.Option(None, help="Palavra no titulo ou no resumo"),
    situacao: str = typer.Option(None, help="Ex: edital_publicado, autorizado"),
    limite: int = typer.Option(30, help="Quantidade maxima de linhas"),
) -> None:
    """Mostra o que ja esta no banco."""
    itens = servico.listar(
        uf=uf, banca=banca, termo=termo, situacao=situacao, limite=limite
    )

    tabela = Table(title=f"{len(itens)} concurso(s)")
    tabela.add_column("Data", style="dim", no_wrap=True)
    tabela.add_column("UF", width=3)
    tabela.add_column("Situacao", style="cyan", no_wrap=True)
    tabela.add_column("Titulo")

    for c in itens:
        tabela.add_row(
            formatar_data(c.publicado_em),
            c.uf or "--",
            c.situacao,
            c.titulo,
        )

    console.print(tabela)


@app.command()
def exportar(caminho: str = typer.Option(None, help="Destino do JSON")) -> None:
    """Grava o banco inteiro em data/concursos.json (o que vai para o git)."""
    destino = Path(caminho) if caminho else acervo.caminho_padrao()
    total = acervo.exportar(destino)
    console.print(f"[green]{total}[/] concurso(s) exportado(s) para {destino}")


@app.command()
def importar(caminho: str = typer.Option(None, help="Origem do JSON")) -> None:
    """Reconstroi o banco a partir do JSON. Seguro rodar quantas vezes quiser."""
    origem = Path(caminho) if caminho else acervo.caminho_padrao()
    total = acervo.importar(origem)
    if total == 0:
        console.print(f"[yellow]Nada a importar[/] (nao achei {origem})")
    else:
        console.print(f"[green]{total}[/] concurso(s) importado(s) de {origem}")


@app.command()
def web(porta: int = 8000) -> None:
    """Sobe a interface web em http://localhost:8000"""
    import uvicorn

    uvicorn.run("radar.web.app:app", host="127.0.0.1", port=porta, reload=True)


if __name__ == "__main__":
    app()
