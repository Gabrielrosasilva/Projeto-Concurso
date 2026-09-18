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
# O nome do campo e cru (vai para o banco); na tela vira gente.
SITUACAO_LEGIVEL = {
    "prevista": "previsto",
    "autorizado": "autorizado",
    "banca_definida": "banca contratada",
    "edital_publicado": "edital publicado",
    "inscricoes_abertas": "inscricoes abertas",
    "encerrado": "encerrado",
    "desconhecida": "sem informacao",
}

ROTULO_DO_ANEL = {
    "nucleo": "Perto",
    "proximo": "Proximo",
    "remoto": "Longe",
    "indefinida": "A confirmar",
}

# Faixas de remuneracao como atalho: e mais rapido clicar do que digitar, e
# tira a duvida de qual valor usar. (rotulo, minimo, maximo)
FAIXAS_DE_SALARIO = [
    ("ate R$ 2.000", None, 2000),
    ("R$ 2.100 a R$ 5.000", 2100, 5000),
    ("R$ 5.000 a R$ 10.000", 5000, 10000),
    ("acima de R$ 10.000", 10000, None),
]


def _para_campo(valor: float | None) -> str:
    """O numero como ele deve aparecer no campo do formulario."""
    if valor is None:
        return ""
    return str(int(valor)) if valor == int(valor) else str(valor)


def _faixa_ativa(minimo: float | None, maximo: float | None) -> str | None:
    """Qual faixa esta selecionada agora, para destacar o botao."""
    for rotulo, faixa_min, faixa_max in FAIXAS_DE_SALARIO:
        if minimo == faixa_min and maximo == faixa_max:
            return rotulo
    return None


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


def _url_base_sem(request: Request, *parametros: str) -> str:
    """A URL atual sem certos parametros, pronta para receber outros.

    Termina em "?" ou "&" de proposito: quem monta o link so acrescenta o que
    quer, sem precisar saber se ja havia pergunta na URL.
    """
    restante = [
        f"{chave}={valor}"
        for chave, valor in request.query_params.multi_items()
        if chave not in parametros
    ]
    base = request.url.path
    return base + "?" + ("&".join(restante) + "&" if restante else "")


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
    noticias: bool = False,
    salario_min: str | None = None,
    salario_max: str | None = None,
    editar: str | None = None,
):
    """Os campos numericos chegam como TEXTO de proposito.

    Formulario HTML manda todo campo, inclusive o vazio: filtrar so pela banca
    enviava `salario_min=`, e o FastAPI tentava converter "" para float e
    devolvia 422 - o que quebrava a pagina inteira, nao so o campo. Chegando
    como texto, a conversao fica com `converter_valor`, que ja sabe devolver
    None para vazio e para o que nao e numero.
    """
    minimo = converter_valor(salario_min)
    maximo = converter_valor(salario_max)
    cartao_em_edicao = int(editar) if (editar or "").strip().isdigit() else None

    if noticias:
        # A aba de noticias nao filtra nada: quem procura "PM" quer saber de
        # qualquer concurso de policia militar, onde quer que seja e na fase
        # em que estiver.
        itens = servico.buscar_noticias(termo=termo, limite=80)
    else:
        itens = servico.listar(
            uf=uf, banca=banca, termo=termo, situacao=situacao,
            relevancia=relevancia, todas_relevancias=todos, abertas=abertas,
            favoritos=favoritos, salario_min=minimo, salario_max=maximo,
            limite=200,
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
            "salario_min": _para_campo(minimo),
            "salario_max": _para_campo(maximo),
            "faixas": FAIXAS_DE_SALARIO,
            "faixa_ativa": _faixa_ativa(minimo, maximo),
            # Com filtro ligado e zero resultado, a tela precisa dizer que foi
            # o FILTRO que nao achou nada - e nao que nao ha concurso perto,
            # que e outra coisa e leva a conclusao errada.
            "noticias": noticias,
            "fases": servico.contar_por_fase(termo) if noticias else {},
            "ordem_das_fases": list(servico.ORDEM_DAS_FASES),
            "filtro_ativo": any([uf, banca, termo, situacao,
                                 minimo is not None, maximo is not None]),
            "url_sem_salario": _url_base_sem(request, "salario_min", "salario_max"),
            "n_sem_salario": (
                servico.contar_sem_salario()
                if (minimo is not None or maximo is not None) else 0
            ),
            "favorito": servico.FAVORITO,
            "etapas": ETAPAS,
            # O mural fica visivel em qualquer aba: sao os concursos que eu
            # escolhi acompanhar, e some-los atras de uma aba derrotaria o
            # proposito.
            "mural": servico.listar(favoritos=True, limite=20),
            # Qual cartao esta com o campo de salario aberto.
            "editar": cartao_em_edicao,
            # A URL de agora, com e sem o parametro `editar`: uma abre o campo
            # no cartao certo, a outra fecha e volta para a lista limpa.
            "url_com_editar": _url_com_editar(request),
            "url_sem_editar": _url_sem(request, "editar"),
            "url_atual": str(request.url.path) + (
                "?" + str(request.url.query) if request.url.query else ""
            ),
            "rotulo_anel": ROTULO_DO_ANEL,
            "rotulo_situacao": SITUACAO_LEGIVEL,
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


# --- simulado (fase 5) ------------------------------------------------------

def _pagina_do_simulado(request: Request, simulado=None, **extra):
    """Monta o contexto da tela de simulado, seja qual for o estado dela."""
    contexto = {
        "simulado": simulado,
        "materias": servico.materias_disponiveis(),
        "total_de_questoes": servico.contar_questoes(),
        "desempenho_geral": servico.desempenho(),
    }
    contexto.update(extra)
    return templates.TemplateResponse(
        request=request, name="simulado.html", context=contexto
    )


@app.get("/simulado", response_class=HTMLResponse)
def simulado_inicio(request: Request):
    """A tela de comecar, com o acumulado de acertos por materia."""
    return _pagina_do_simulado(request)


@app.post("/simulado/novo")
def simulado_novo(
    materia: str = Form(""),
    quantidade: str = Form("10"),
):
    """Monta a rodada e manda para a primeira questao."""
    quantas = converter_valor(quantidade)
    quantas = int(quantas) if quantas and 1 <= quantas <= 50 else 10

    novo = servico.criar_simulado(
        quantidade=quantas,
        materia=materia.strip() or None,
        # Sem materia escolhida, vale o que cai em qualquer concurso - e o que
        # serve independente do cargo que eu for prestar.
        universais=not materia.strip(),
    )
    if novo is None:
        return RedirectResponse("/simulado", status_code=303)
    return RedirectResponse(f"/simulado/{novo.id}", status_code=303)


@app.get("/simulado/{simulado_id}", response_class=HTMLResponse)
def simulado_questao(request: Request, simulado_id: int):
    """A proxima questao sem resposta, ou o resultado quando acabou."""
    simulado = servico.buscar_simulado(simulado_id)
    if simulado is None:
        return RedirectResponse("/simulado", status_code=303)

    resumo = servico.resumo_do_simulado(simulado_id)
    atual = servico.questao_atual(simulado_id)

    if atual is None:
        return _pagina_do_simulado(
            request,
            simulado=simulado,
            questao=None,
            resumo=resumo,
            desempenho_da_rodada=servico.desempenho(simulado_id),
            revisao=servico.revisao(simulado_id),
        )

    resposta, questao = atual
    return _pagina_do_simulado(
        request, simulado=simulado, resposta=resposta, questao=questao, resumo=resumo
    )


@app.post("/simulado/{simulado_id}/responder")
def simulado_responder(
    simulado_id: int,
    questao_id: int = Form(...),
    letra: str = Form(...),
):
    """Grava a resposta e volta para a mesma URL.

    O redirecionamento 303 e o que impede o F5 de responder de novo - alem da
    trava no servico, que ignora questao ja respondida.
    """
    servico.responder(simulado_id, questao_id, letra)
    return RedirectResponse(f"/simulado/{simulado_id}", status_code=303)
