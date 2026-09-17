"""Interface web minima: uma pagina com filtros.

Roda so em 127.0.0.1 de proposito (veja cli.web). Nao ha login porque nao ha
outro usuario, e por isso mesmo ela nao deve ficar exposta na rede.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from radar import servico
from radar.util import formatar_data
try:                                    # fastapi>=0.115 traz o Jinja2Templates
    from fastapi.templating import Jinja2Templates
except ImportError:                     # pragma: no cover
    from starlette.templating import Jinja2Templates

app = FastAPI(title="Radar de Concursos")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
# Deixa formatar_data disponivel dentro do HTML, para o template nao precisar
# saber nada de fuso horario.
templates.env.filters["data"] = formatar_data


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    uf: str | None = None,
    banca: str | None = None,
    termo: str | None = None,
    situacao: str | None = None,
):
    itens = servico.listar(
        uf=uf, banca=banca, termo=termo, situacao=situacao, limite=100
    )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "itens": itens,
            "total_geral": servico.contar(),
            "uf": uf or "",
            "banca": banca or "",
            "termo": termo or "",
            "situacao": situacao or "",
        },
    )


@app.post("/coletar")
def coletar():
    """Dispara a coleta pela web. Devolve o resumo por fonte."""
    return [
        {
            "fonte": r.fonte,
            "novos": r.novos,
            "atualizados": r.atualizados,
            "erro": r.erro,
        }
        for r in servico.coletar_tudo()
    ]
