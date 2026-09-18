"""Interface web minima: uma pagina com filtros.

Roda so em 127.0.0.1 de proposito (veja cli.web). Nao ha login porque nao ha
outro usuario, e por isso mesmo ela nao deve ficar exposta na rede.
"""
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from radar import servico
from radar.util import converter_valor, dias_ate, formatar_data
try:                                    # fastapi>=0.115 traz o Jinja2Templates
    from fastapi.templating import Jinja2Templates
except ImportError:                     # pragma: no cover
    from starlette.templating import Jinja2Templates

app = FastAPI(title="Radar de Concursos")

# O ciclo de vida do concurso, na ordem. A tela mostra ate onde ele chegou:
# tudo antes da etapa atual ja aconteceu, por definicao da sequencia.
# "nucleo" e jargao do codigo; na tela vale o que a pessoa entende.
# As cores continuam as mesmas: quem le "Perto" ve o mesmo verde de antes.
ROTULO_DO_ANEL = {
    "nucleo": "Perto",
    "proximo": "Proximo",
    "remoto": "Longe",
    "indefinida": "A confirmar",
}

ETAPAS = [
    ("prevista", "previsto"),
    ("autorizado", "autorizado"),
    ("banca_definida", "banca contratada"),
    ("edital_publicado", "edital publicado"),
    ("inscricoes_abertas", "inscricoes abertas"),
    ("encerrado", "encerrado"),
]
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
# Deixa formatar_data disponivel dentro do HTML, para o template nao precisar
# saber nada de fuso horario.
templates.env.filters["data"] = formatar_data
templates.env.filters["dias"] = dias_ate


def _url_sem(request: Request, parametro: str) -> str:
    """A URL atual sem um parametro. Usado para fechar o campo de edicao."""
    restante = [
        f"{chave}={valor}"
        for chave, valor in request.query_params.multi_items()
        if chave != parametro
    ]
    return request.url.path + ("?" + "&".join(restante) if restante else "")


def _url_com_editar(request: Request) -> str:
    """Prefixo pronto para receber o id: .../?...&editar="""
    base = _url_sem(request, "editar")
    return base + ("&" if "?" in base else "?") + "editar="


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    uf: str | None = None,
    banca: str | None = None,
    termo: str | None = None,
    situacao: str | None = None,
    relevancia: str | None = None,
    todos: bool = False,
    abertas: bool = False,
    favoritos: bool = False,
    salario_min: float | None = None,
    editar: int | None = None,
):
    itens = servico.listar(
        uf=uf, banca=banca, termo=termo, situacao=situacao,
        relevancia=relevancia, todas_relevancias=todos, abertas=abertas,
        favoritos=favoritos, salario_min=salario_min, limite=200,
    )
    contagem = servico.contar_por_relevancia()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "itens": itens,
            "contagem": contagem,
            "perto": contagem["nucleo"] + contagem["proximo"],
            "total_geral": sum(contagem.values()),
            "uf": uf or "",
            "banca": banca or "",
            "termo": termo or "",
            "situacao": situacao or "",
            "relevancia": relevancia or "",
            "todos": todos,
            "abertas": abertas,
            "n_abertas": servico.contar_abertas(),
            "favoritos": favoritos,
            "n_favoritos": servico.contar_favoritos(),
            "salario_min": ("" if salario_min is None
                             else int(salario_min) if salario_min == int(salario_min)
                             else salario_min),
            "n_sem_salario": servico.contar_sem_salario() if salario_min else 0,
            "favorito": servico.FAVORITO,
            "etapas": ETAPAS,
            # O mural fica visivel em qualquer aba: sao os concursos que eu
            # escolhi acompanhar, e some-los atras de uma aba derrotaria o
            # proposito.
            "mural": servico.listar(favoritos=True, limite=20),
            # Qual cartao esta com o campo de salario aberto.
            "editar": editar,
            # A URL de agora, com e sem o parametro `editar`: uma abre o campo
            # no cartao certo, a outra fecha e volta para a lista limpa.
            "url_com_editar": _url_com_editar(request),
            "url_sem_editar": _url_sem(request, "editar"),
            "url_atual": str(request.url.path) + (
                "?" + str(request.url.query) if request.url.query else ""
            ),
            "rotulo_anel": ROTULO_DO_ANEL,
        },
    )


@app.post("/favoritar")
def favoritar(concurso_id: int = Form(...), voltar: str = Form("/")):
    """Liga ou desliga o favorito e devolve para a pagina de onde veio.

    E POST, e nao um link: o navegador pre-carrega link ao passar o mouse, e
    isso favoritaria concurso sozinho. Depois vem um redirecionamento 303,
    que e o que impede o F5 de repetir a acao.
    """
    servico.alternar_favorito(concurso_id)
    # so aceita caminho interno: nao vira redirecionador para fora
    destino = voltar if voltar.startswith("/") else "/"
    return RedirectResponse(destino, status_code=303)


@app.post("/salario")
def salario(
    concurso_id: int = Form(...),
    salario: str = Form(""),
    voltar: str = Form("/"),
):
    """Grava a remuneracao que eu digitei.

    Campo vazio - ou texto que nao vira numero - limpa o valor e devolve o
    campo ao classificador.
    """
    servico.definir_salario(concurso_id, converter_valor(salario))
    destino = voltar if voltar.startswith("/") else "/"
    return RedirectResponse(destino, status_code=303)


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
