"""Interface web minima: uma pagina com filtros.

Roda so em 127.0.0.1 de proposito (veja cli.web). Nao ha login porque nao ha
outro usuario, e por isso mesmo ela nao deve ficar exposta na rede.
"""
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from radar import acompanhando as meus_favoritos
from radar import eventos as linha_do_tempo
from radar import foco as foco_do_alvo
from radar import regioes
from radar import servico
from radar.util import (
    converter_valor,
    dias_ate,
    formatar_data,
    separar_campos_grudados,
)
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
    "inscricoes_abertas": "inscrições abertas",
    "encerrado": "encerrado",
    "desconhecida": "sem informação",
}

ROTULO_DO_ANEL = {
    "nucleo": "Perto",
    "proximo": "Próximo",
    "estadual": "Estadual SC",
    "remoto": "Longe",
    "indefinida": "A confirmar",
}

# Faixas de remuneracao como atalho: e mais rapido clicar do que digitar, e
# tira a duvida de qual valor usar. (rotulo, minimo, maximo)
FAIXAS_DE_SALARIO = [
    ("até R$ 2.000", None, 2000),
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
    ("inscricoes_abertas", "inscrições abertas"),
    ("encerrado", "encerrado"),
]
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
# Deixa formatar_data disponivel dentro do HTML, para o template nao precisar
# saber nada de fuso horario.
templates.env.filters["data"] = formatar_data
templates.env.filters["dias"] = dias_ate
# A FEPESE as vezes cola os campos do titulo sem separador. Isto e so
# exibicao: o titulo gravado continua o que a fonte mandou.
templates.env.filters["titulo"] = separar_campos_grudados
# O municipio sai do banco com a grafia da fonte, que quase sempre vem sem
# acento. A grafia certa e a de config/regioes.yml, e e ela que a tela
# mostra - sem precisar reescrever o que ja esta gravado.
templates.env.filters["municipio"] = regioes.nome_canonico


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


def _url_sem(request, parametro: str) -> str:
    """A URL atual sem um parametro. Usado para fechar o campo de edicao."""
    if isinstance(request, str):
        # Ja e uma URL montada: tira o parametro dela do jeito mais simples.
        caminho, _, consulta = request.partition("?")
        restante = [
            pedaco for pedaco in consulta.split("&")
            if pedaco and not pedaco.startswith(parametro + "=")
        ]
        return caminho + ("?" + "&".join(restante) if restante else "")

    restante = [
        f"{chave}={valor}"
        for chave, valor in request.query_params.multi_items()
        if chave != parametro
    ]
    return request.url.path + ("?" + "&".join(restante) if restante else "")


def _url_com(request: Request, parametro: str) -> str:
    """Prefixo pronto para receber o id: .../?...&editar=

    O parametro que ja estiver na URL sai antes, senao clicar em "anotar" com
    um campo de salario aberto deixaria os dois abertos ao mesmo tempo.
    """
    base = _url_sem(_url_sem_pedido(request, "editar", "anotar"), parametro)
    return base + ("&" if "?" in base else "?") + parametro + "="


def _url_sem_pedido(request: Request, *parametros: str):
    """A URL de agora sem nenhum dos parametros dados, como objeto de consulta."""
    restante = [
        (chave, valor)
        for chave, valor in request.query_params.multi_items()
        if chave not in parametros
    ]
    return request.url.path + (
        "?" + "&".join(f"{c}={v}" for c, v in restante) if restante else ""
    )


# Quantos cartoes a lista mostra de uma vez, e de quanto em quanto ela
# cresce no "ver mais". A lista inteira de uma vez chegava a 200 cartoes numa
# rolagem so, e o que interessa esta sempre nos primeiros.
CARTOES_POR_VEZ = 30


@app.get("/concursos", response_class=HTMLResponse)
def concursos(
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
    anotar: str | None = None,
    mostrar: int = CARTOES_POR_VEZ,
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
    cartao_anotando = int(anotar) if (anotar or "").strip().isdigit() else None

    # Um a mais do que vai para a tela: e assim que se sabe se ha proxima
    # pagina sem fazer uma segunda consulta so para contar.
    mostrar = max(CARTOES_POR_VEZ, mostrar)
    if noticias:
        # A aba de noticias nao filtra nada: quem procura "PM" quer saber de
        # qualquer concurso de policia militar, onde quer que seja e na fase
        # em que estiver.
        itens = servico.buscar_noticias(termo=termo, limite=mostrar + 1)
    else:
        itens = servico.listar(
            uf=uf, banca=banca, termo=termo, situacao=situacao,
            relevancia=relevancia, todas_relevancias=todos, abertas=abertas,
            favoritos=favoritos, salario_min=minimo, salario_max=maximo,
            limite=mostrar + 1,
        )

    tem_mais = len(itens) > mostrar
    itens = itens[:mostrar]
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
            "url_sem_termo": _url_base_sem(request, "termo").rstrip("?&") or "/",
            "n_sem_salario": (
                servico.contar_sem_salario()
                if (minimo is not None or maximo is not None) else 0
            ),
            "favorito": servico.FAVORITO,
            "etapas": ETAPAS,
            # Qual cartao esta com o campo de salario aberto.
            "editar": cartao_em_edicao,
            # A URL de agora, com e sem o parametro `editar`: uma abre o campo
            # no cartao certo, a outra fecha e volta para a lista limpa.
            "url_com_editar": _url_com(request, "editar"),
            "url_sem_editar": _url_sem_pedido(request, "editar", "anotar"),
            "anotar": cartao_anotando,
            "url_com_anotar": _url_com(request, "anotar"),
            "url_atual": str(request.url.path) + (
                "?" + str(request.url.query) if request.url.query else ""
            ),
            "rotulo_anel": ROTULO_DO_ANEL,
            "rotulo_situacao": SITUACAO_LEGIVEL,
            # Paginacao: quantos cabem agora, e para onde vai o "ver mais".
            "tem_mais": tem_mais,
            "por_vez": CARTOES_POR_VEZ,
            "url_ver_mais": (
                _url_base_sem(request, "mostrar")
                + f"mostrar={mostrar + CARTOES_POR_VEZ}"
            ),
            # Um filtro escondido continua valendo, e a tela precisa dizer
            # isso: senao a lista parece curta sem motivo.
            "filtros_avancados_ativos": any(
                [uf, banca, minimo is not None, maximo is not None, situacao]
            ),
        },
    )


@app.post("/favoritar")
def favoritar(concurso_id: int = Form(...), voltar: str = Form("/concursos")):
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
    voltar: str = Form("/concursos"),
):
    """Grava a remuneracao que eu digitei.

    Campo vazio - ou texto que nao vira numero - limpa o valor e devolve o
    campo ao classificador.
    """
    servico.definir_salario(concurso_id, converter_valor(salario))
    destino = voltar if voltar.startswith("/") else "/"
    return RedirectResponse(destino, status_code=303)


@app.post("/notas")
def notas(
    concurso_id: int = Form(...),
    notas: str = Form(""),
    voltar: str = Form("/concursos"),
):
    """Grava a minha anotacao. Campo vazio apaga a nota."""
    servico.definir_notas(concurso_id, notas)
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


# --- o icone da aba (etapa 12) ----------------------------------------------
#
# Um radar: o circulo, o anel de dentro, a varredura e o ponto que ela achou.
# Vai inline, como texto, para nao precisar de pasta de estatico nem de
# dependencia nova - sao 500 bytes.
#
# O fundo e solido de proposito: aba clara e aba escura mostram o mesmo
# desenho, e um SVG so com traco azul some no tema escuro.
FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#1d4ed8"/>
  <g fill="none" stroke="#ffffff" stroke-width="3.5" opacity=".85">
    <circle cx="32" cy="32" r="19"/>
    <circle cx="32" cy="32" r="9.5"/>
  </g>
  <path d="M32 32 L32 11 A21 21 0 0 1 50 22 Z" fill="#ffffff" opacity=".55"/>
  <circle cx="44" cy="22" r="5" fill="#4ade80"/>
</svg>"""


@app.get("/favicon.svg", include_in_schema=False)
def favicon_svg():
    """O icone da aba. SVG porque escala sozinho e cabe no proprio arquivo."""
    return Response(FAVICON, media_type="image/svg+xml")


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico():
    """O navegador pede este endereco por conta propria, mesmo com o <link>
    do SVG na pagina - e sem resposta ele registrava 404 no console a cada
    visita. 204 quer dizer "nao tenho, e esta tudo bem"."""
    return Response(status_code=204)


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


# --- previsao de abertura (fase 6) ------------------------------------------

@app.get("/", response_class=HTMLResponse)
def meu_foco(request: Request):
    """A tela que responde "o que esta acontecendo com o meu concurso?".

    E a home porque e a pergunta que eu faco todo dia. A lista de concursos
    responde "o que existe?", que e outra coisa e vem depois.
    """
    painel = foco_do_alvo.montar()
    return templates.TemplateResponse(
        request=request,
        name="foco.html",
        context={
            "p": painel,
            "questoes_do_treino": foco_do_alvo.QUESTOES_DO_TREINO,
            # De onde a proxima rodada vai sair, antes de eu clicar: quantas
            # questoes da prova do cargo ainda nao respondi, e quantas da
            # mesma banca nas mesmas materias esperam depois delas.
            "fontes_do_treino": servico.contar_questoes_do_alvo(),
            # As materias que cairam na prova mas nao estao no quadro do
            # edital lido. Elas nao podem sumir da tela so porque a tabela e
            # montada a partir do edital: sumir seria esconder que a prova
            # mudou de um ano para o outro.
            "fora_do_edital": sorted(
                m for m in painel.incidencia
                if m not in {x.nome for x in painel.materias_do_edital}
            ),
        },
    )


@app.get("/foco")
def foco_endereco_antigo():
    """Meu foco virou a home. O endereco antigo continua levando la."""
    return RedirectResponse("/", status_code=303)


@app.post("/foco/treinar")
def treinar_do_foco():
    """Sorteia uma rodada para a MINHA prova.

    Sem escolher materia: o ponto do botao e comecar a estudar em um clique,
    e a distribuicao do acervo do cargo ja e a da prova real. Primeiro as
    questoes das provas do proprio cargo; quando elas acabam, as da mesma
    banca nas mesmas materias.
    """
    novo = servico.criar_simulado_do_alvo(
        quantidade=foco_do_alvo.QUESTOES_DO_TREINO
    )
    if novo is None:
        return RedirectResponse("/simulado", status_code=303)
    return RedirectResponse(f"/simulado/{novo.id}", status_code=303)


@app.get("/acompanhando", response_class=HTMLResponse)
def acompanhando(request: Request):
    """Um bloco por favorito: o que aconteceu, e o que fazer agora.

    Esta tela substituiu o mural lateral. O mural cabia em qualquer aba mas
    nao cabia nada dentro dele; aqui cada favorito tem espaco para a linha do
    tempo inteira e para a proxima acao.
    """
    return templates.TemplateResponse(
        request=request,
        name="acompanhando.html",
        context={
            "blocos": meus_favoritos.blocos(),
            "importantes": linha_do_tempo.EVENTOS_IMPORTANTES,
            "rotulo_anel": ROTULO_DO_ANEL,
            "rotulo_situacao": SITUACAO_LEGIVEL,
        },
    )


@app.get("/estudar")
def estudar():
    """Estudar e uma secao com duas paginas; esta abre na primeira.

    Macetes vem antes do Simulado de proposito: ver o que a banca cobra e o
    passo que decide o que treinar depois.
    """
    return RedirectResponse("/macetes", status_code=303)


@app.get("/previsao", response_class=HTMLResponse)
def previsao(request: Request):
    """Onde vale ficar de olho: municipio parado ha tempo demais."""
    return templates.TemplateResponse(
        request=request,
        name="previsao.html",
        context={"previsoes": servico.previsao_de_abertura()},
    )


# --- macetes: o costume da banca --------------------------------------------

@app.get("/macetes", response_class=HTMLResponse)
def macetes(
    request: Request,
    banca: str | None = None,
    cargo: str | None = None,
    tema: str | None = None,
):
    """O que a banca costuma cobrar no recorte pedido.

    Os tres campos chegam como texto, e vazio vira None: formulario HTML manda
    todo campo, inclusive o que ficou em branco.
    """
    banca = (banca or "").strip() or None
    cargo = (cargo or "").strip() or None
    tema = (tema or "").strip() or None

    # Sem banca escolhida a pagina nao calcula nada: o retrato do acervo
    # inteiro misturava bancas e nao respondia pergunta nenhuma.
    analise = (
        servico.analisar_banca(banca=banca, cargo=cargo, tema=tema)
        if banca else servico.macetes.Analise()
    )
    composicao = servico.composicao_do_caderno(banca) if banca else []

    # A pizza precisa de um TODO real: somar "questoes por caderno" de
    # materias que caem em provas diferentes daria 81 numa prova de 40. Entao
    # a fatia e a participacao no total de questoes, e o numero por prova vai
    # na legenda, que e onde ele ajuda.
    fatias_do_caderno = servico.macetes.fatias(
        [(f.materia, f.total) for f in composicao],
        extras={f.materia: f.por_caderno for f in composicao},
    )
    fatias_de_assunto = (
        servico.macetes.fatias(
            [(a.nome, a.questoes) for a in analise.retrato.assuntos]
        )
        if analise.retrato else []
    )

    # Quando eu digito um cargo, a pergunta seguinte e "o acervo tem prova
    # disso?". Para Guarda Municipal e Policia Penal a resposta e nao, e a
    # tela precisa dizer isso em vez de mostrar recorte vazio.
    parecidas = servico.provas_parecidas(cargo, banca=banca) if cargo else []
    recado = servico.recado_sobre_o_cargo(cargo, parecidas) if cargo else ""

    return templates.TemplateResponse(
        request=request,
        name="macetes.html",
        context={
            "analise": analise,
            "parecidas": parecidas,
            "recado_do_cargo": recado,
            "composicao": composicao,
            "fatias_do_caderno": fatias_do_caderno,
            "fatias_de_assunto": fatias_de_assunto,
            "bancas": servico.bancas_com_questao(),
            "bancas_sem_acervo": servico.bancas_sem_acervo(),
            "banca": banca,
            "cargo": cargo,
            "tema": tema,
        },
    )


# --- pagina que nao existe --------------------------------------------------

# Quando este processo comecou. Serve para uma pergunta so, mas importante:
# o codigo em disco mudou depois que o servidor subiu?
SUBIU_EM = time.time()


def _codigo_mudou_depois_de_subir() -> bool:
    """Ha arquivo .py mais novo que o processo em execucao?

    O sintoma que isto explica e confuso: o link aparece na pagina mas da 404.
    O template e lido do disco a cada visita, entao o link NOVO aparece; o
    codigo Python foi carregado uma vez, na partida, entao a rota NOVA nao
    existe. Quem ve so o {"detail":"Not Found"} nao tem como adivinhar isso.
    """
    raiz = Path(__file__).resolve().parent.parent
    return any(
        arquivo.stat().st_mtime > SUBIU_EM for arquivo in raiz.rglob("*.py")
    )


@app.exception_handler(404)
def pagina_nao_encontrada(request: Request, excecao: HTTPException):
    """Explica o 404 em portugues, e diz o que fazer quando da para saber."""
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        status_code=404,
        context={
            "caminho": request.url.path,
            "servidor_velho": _codigo_mudou_depois_de_subir(),
        },
    )


# --- calendario (fase 2.2) --------------------------------------------------

@app.get("/calendario", response_class=HTMLResponse)
def calendario(request: Request):
    """Explica para que serve o arquivo, e mostra o que vai entrar na agenda.

    Antes o link da barra baixava o .ics direto, e um arquivo que aparece do
    nada nao diz o que e nem o que fazer com ele.
    """
    return templates.TemplateResponse(
        request=request,
        name="calendario.html",
        context={"eventos": servico.eventos_do_calendario()},
    )


@app.get("/calendario.ics")
def calendario_ics():
    """Os prazos em formato de calendario, para assinar no celular.

    Servido como arquivo, e nao como pagina: o celular reconhece o tipo e
    oferece importar. O nome termina em .ics porque e por ele que o Android
    decide qual aplicativo abre.
    """
    from fastapi.responses import Response

    return Response(
        content=servico.calendario_ics(),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="radar.ics"'},
    )
