"""Interface web minima: uma pagina com filtros.

Roda so em 127.0.0.1 de proposito (veja cli.web). Nao ha login porque nao ha
outro usuario, e por isso mesmo ela nao deve ficar exposta na rede.
"""
import time
from html import escape
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi import FastAPI, Form, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from radar import acompanhando as meus_favoritos
from radar import amostra
from radar import eventos as linha_do_tempo
from radar import foco as foco_do_alvo
from radar import auditoria
from radar import automacao
from radar import config
from radar import cronograma
from radar import fichas as fichas_puras
from radar import leis
from radar import onde_estudar
from radar import origem
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
# Mora em eventos.py porque a linha do tempo usa os mesmos nomes na frase.
SITUACAO_LEGIVEL = linha_do_tempo.NOME_DA_SITUACAO

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

# O design system (design.css) e servido como arquivo, e nao colado em cada
# pagina: um lugar so para a cor e o espaco, e o navegador guarda em cache.
from fastapi.staticfiles import StaticFiles  # noqa: E402 - junto de quem usa

app.mount(
    "/estatico",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="estatico",
)
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
# A descricao do evento sai do banco como a coleta gravou ("Situacao:
# inscricoes_abertas -> encerrado"); na tela vira frase. Banco nao muda.
templates.env.filters["evento"] = linha_do_tempo.para_tela
templates.env.filters["tipo_do_evento"] = linha_do_tempo.rotulo_do_tipo
# A linha "N questoes = acertos + erros + ..." sai do servico.metricas, a
# fonte unica: a tela e o `radar hoje` escrevem a mesma frase.
templates.env.globals["frase_da_conta"] = servico.metricas.frase_da_conta
templates.env.globals["frase_da_ia"] = servico.metricas.frase_da_ia
# Numero com virgula, como se escreve em portugues. A mesma funcao que monta a
# frase de conclusao do "Onde estudar primeiro", para o grafico e o texto ao
# lado dele nunca arredondarem diferente.
templates.env.filters["numero"] = onde_estudar.numero
# Os minimos de resposta, para a tela dizer "2 de 20" com o mesmo numero que
# faz a conta - e nao com um numero escrito no template. Os dois saem do
# config/amostra.yml (Etapa 4): um lugar so para as telas e para as contas.
templates.env.globals["MINIMO_NA_MATERIA"] = amostra.carregar().do_nivel("materia")
templates.env.globals["MINIMO_NO_ASSUNTO"] = amostra.carregar().do_nivel("assunto")
# E o "base pequena": com menos provas que isto, o que sai delas leva o
# aviso. Mesmo arquivo, para o 3 nao ficar escrito em tres templates.
templates.env.globals["PROVAS_PARA_TENDENCIA"] = amostra.carregar().provas_para_tendencia
# Os nomes do caderno de erros (motivo, fonte, o que a lista mostra) e a
# pergunta "este erro esta vencido?". Vem do servico para nao existir um
# "Pegadinha" escrito no HTML e outro no banco.
templates.env.globals["MOTIVOS_DO_ERRO"] = servico.erros.MOTIVOS
templates.env.globals["FONTES_DO_ERRO"] = servico.erros.FONTES
templates.env.globals["SITUACOES_DO_ERRO"] = servico.erros.SITUACOES
templates.env.globals["ESTA_PARA_REVER"] = servico.erros.esta_para_rever
# Os selos e as duas frases que nao podem variar (Etapa 7A): moram no
# radar/origem.py, e a tela, a ficha e o terminal leem de la. O "Amostra
# insuficiente" e o estado do radar/amostra.py, o mesmo do desempenho.
templates.env.globals["SELOS"] = origem.SELOS
templates.env.globals["FRASE_SEM_EVIDENCIA"] = origem.FRASE_SEM_EVIDENCIA
templates.env.globals["FRASE_DA_QUESTAO_DE_IA"] = origem.FRASE_DA_QUESTAO_DE_IA
templates.env.globals["AMOSTRA_INSUFICIENTE"] = amostra.INSUFICIENTE


# --- o tema (claro ou escuro) -----------------------------------------------
# Escuro e o padrao; claro e escolha minha, guardada no cookie `tema`. O
# `?cor=` da URL vence o cookie: serve para comparar os dois sem trocar a
# escolha. Um lugar so decide - toda pagina chama tema_da_pagina no <html>.
# O parametro era `?tema=` ate 04/10, e esbarrava no filtro "Materia ou tema"
# dos Macetes: `/macetes?tema=claro` pintava a tela E procurava "claro".
TEMAS = ("claro", "escuro")
TEMA_PADRAO = "escuro"
PARAMETRO_DA_COR = "cor"
# Dez anos: a escolha e minha e so muda quando eu clicar de novo.
VALIDADE_DO_COOKIE_DE_TEMA = 10 * 365 * 24 * 3600


def tema_da_pagina(request: Request) -> str:
    """O tema desta pagina: o da URL (`?cor=`), senao o do cookie, senao o escuro."""
    for escolha in (request.query_params.get(PARAMETRO_DA_COR), request.cookies.get("tema")):
        if escolha in TEMAS:
            return escolha
    return TEMA_PADRAO


def link_de_trocar_tema(request: Request) -> str:
    """O link do botao ☀️/🌙: pede o outro tema e volta para esta pagina.

    O `cor` sai da volta de proposito: se ficasse, o `?cor=` da URL venceria
    o cookie recem-gravado e o clique pareceria nao fazer nada. O resto da URL
    fica - inclusive o `tema` do filtro dos Macetes.
    """
    outro = "claro" if tema_da_pagina(request) == "escuro" else "escuro"
    resto = [(k, v) for k, v in request.query_params.multi_items()
             if k != PARAMETRO_DA_COR]
    volta = request.url.path + (f"?{urlencode(resto)}" if resto else "")
    return f"/tema?{urlencode({'valor': outro, 'volta': volta})}"


def _volta_interna(volta: str) -> str:
    """So caminho deste site. "//outro.site" e "/\\outro.site" comecam com
    barra, mas o navegador os le como outro endereco - por isso a recusa."""
    if not volta.startswith("/") or volta.startswith("//") or volta.startswith("/\\"):
        return "/"
    return volta


templates.env.globals["tema_da_pagina"] = tema_da_pagina
templates.env.globals["link_de_trocar_tema"] = link_de_trocar_tema


# --- a tela Hoje (o cronograma) ---------------------------------------------
# Os nomes que a tela mostra. O cru (qconcursos, nao_fiz) e o do arquivo e do
# banco; aqui ele vira gente.
ONDE_LEGIVEL = {"qconcursos": "Qconcursos", "radar": "Radar", "videoaula": "Videoaula"}
META_LEGIVEL = {"ideal": "Ideal", "reduzida": "Reduzida", "minima": "Mínima",
                "nao_fiz": "Não fiz"}
# (valor, emoji, rotulo, explicacao) dos quatro botoes do "Como foi o dia".
OPCOES_DE_META = [
    ("ideal", "✅", "Ideal", "dia completo"),
    ("reduzida", "🟦", "Reduzida", "manhã + parte da noite"),
    ("minima", "🟨", "Mínima", "Plano B"),
    ("nao_fiz", "❌", "Não fiz", "o dia zerou"),
]
# O detalhe destas faixas e o que estudar, artigo por artigo: fica aberto. O
# das outras (questoes, correcao...) e instrucao, e fica num "ver detalhe".
DETALHE_ABERTO = {"teoria", "lei_seca", "portugues", "raciocinio"}
DIAS_LONGOS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")


# O botao do link da lei diz ONDE ela abre: o Planalto (lei federal) ou a
# ALESC (lei de SC). Pelo endereco, e nao por um campo a mais no YAML - o
# link ja diz de onde e.
SITES_DA_LEI = (("planalto.gov.br", "Ler no Planalto"), ("alesc.sc.gov.br", "Ler na ALESC"))


def tempo_do_plano_b(minutos: int) -> str:
    """"30 min", "1 hora", "2 horas": como o botao e o resumo dizem o tempo."""
    if minutos % 60:
        return f"{minutos} min"
    horas = minutos // 60
    return "1 hora" if horas == 1 else f"{horas} horas"


# As faixas em que eu respondo questao - e, portanto, as que ganham o botao
# "Anotar erro". A Revisao semanal fica de fora: ela nao tem materia e ganha,
# no lugar, o link para os erros da semana.
TIPOS_QUE_ANOTAM = {"questoes", "revisao", "simulado", "diagnostico"}


def link_de_anotar_erro(data, materia, assunto, volta: str) -> str:
    """O endereco do formulario com a faixa ja preenchida, e a volta para ela.

    Monta com urlencode de proposito: titulo de faixa tem "&", ":" e acento, e
    colar isso na mao no endereco quebra o pre-preenchimento em silencio.
    """
    return "/erros/novo?" + urlencode({
        "data": data.isoformat(),
        "materia": materia or "",
        "assunto": assunto or "",
        "volta": volta,
    })


def _filhos_na_tela(materia: str | None, assunto: str | None = None) -> list[str]:
    """Os nomes que nascem direto debaixo daquele no, para o seletor da tela.

    Vazio quando o pai nao foi escolhido ainda: a tela nao oferece assunto de
    materia nenhuma, nem subassunto de assunto nenhum.
    """
    from radar import conteudos as arvore

    if not materia:
        return []
    pai = materia if not assunto else arvore.SEPARADOR.join([materia, assunto])
    caminhos = servico.conteudos.caminhos()
    if pai not in caminhos:
        return []
    comeco = pai + arvore.SEPARADOR
    return sorted(
        c[len(comeco):] for c in caminhos
        if c.startswith(comeco) and arvore.SEPARADOR not in c[len(comeco):]
    )


def opcoes_de_conteudo(raiz: str | None = None) -> list[tuple[str, str]]:
    """[(caminho, rotulo recuado)] para o seletor de conteudo (Etapa 4).

    Um `select` so, com o caminho inteiro no valor e o nome recuado no rotulo,
    em vez de tres caixas encadeadas: encadear precisaria de JavaScript, e o
    cronometro continua sendo o unico JS do projeto. O recuo ja mostra a
    hierarquia materia > assunto > subassunto > elemento.

    Com `raiz`, so aquele no e os de baixo dele - e o caso da faixa, que nao
    deixa anotar fora do ramo dela.
    """
    from radar import conteudos as arvore

    caminhos = sorted(servico.conteudos.caminhos())
    if raiz:
        caminhos = [c for c in caminhos
                    if c == raiz or c.startswith(raiz + arvore.SEPARADOR)]
        corte = len(arvore.partes(raiz)) - 1
    else:
        corte = 0
    saida = []
    for caminho in caminhos:
        nomes = arvore.partes(caminho)
        recuo = " " * 3 * max(0, len(nomes) - 1 - corte)
        saida.append((caminho, f"{recuo}{nomes[-1]}"))
    return saida


def rotulo_da_lei(link: str) -> str:
    """"Ler no Planalto", "Ler na ALESC" ou, de qualquer outro site, "Ler a lei"."""
    site = (urlparse(link).hostname or "").lower()
    for dominio, rotulo in SITES_DA_LEI:
        if site == dominio or site.endswith("." + dominio):
            return rotulo
    return "Ler a lei"

templates.env.globals.update(
    OPCOES_DE_CONTEUDO=opcoes_de_conteudo,
    linha_do_grafico=servico.materias.linha_do_grafico,
    GRAFICO_LARGURA=servico.materias.LARGURA,
    GRAFICO_ALTURA=servico.materias.ALTURA,
    O_QUE_DO_EXTRA=servico.extra.O_QUE, ONDE_DO_EXTRA=servico.extra.ONDE,
    ONDE_SEM_QUESTOES=servico.extra.ONDE_SEM_QUESTOES,
    TEM_ACERTO=cronograma.tem_acerto,
    CONSULTA_POR_PADRAO=cronograma.consulta_por_padrao,
    duracao=cronograma.duracao_legivel,
    ONDE_LEGIVEL=ONDE_LEGIVEL, META_LEGIVEL=META_LEGIVEL,
    OPCOES_DE_META=OPCOES_DE_META, DETALHE_ABERTO=DETALHE_ABERTO,
    DIAS_LONGOS=DIAS_LONGOS, MESES=cronograma.MESES,
    TIPO_LEGIVEL=cronograma.TIPO_LEGIVEL, ICONE_DO_TIPO=cronograma.ICONE_DO_TIPO,
    FRASE_DO_ANKI_DESATIVADO=cronograma.FRASE_DO_ANKI_DESATIVADO,
    duracao_legivel=cronograma.duracao_legivel,
    rotulo_da_lei=rotulo_da_lei,
    tempo_do_plano_b=tempo_do_plano_b,
    TIPOS_QUE_ANOTAM=TIPOS_QUE_ANOTAM,
    link_de_anotar_erro=link_de_anotar_erro,
)


def _dia_mes(valor) -> str:
    """'2026-09-28' ou date -> '28/09'. A origem da revisao vem como texto."""
    if isinstance(valor, str):
        valor = date.fromisoformat(valor)
    return valor.strftime("%d/%m")


templates.env.filters["dia_mes"] = _dia_mes


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


@app.get("/tema")
def trocar_tema(valor: str = TEMA_PADRAO, volta: str = "/"):
    """O botao ☀️/🌙: grava a escolha no cookie e volta para onde eu estava.
    E um link simples, sem JavaScript - por isso GET."""
    if valor not in TEMAS:
        valor = TEMA_PADRAO
    resposta = RedirectResponse(_volta_interna(volta), status_code=303)
    resposta.set_cookie("tema", valor, max_age=VALIDADE_DO_COOKIE_DE_TEMA,
                        httponly=True, samesite="lax")
    return resposta


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
        # O segundo numero, sempre do lado e nunca somado ao primeiro.
        "desempenho_das_geradas": servico.desempenho_das_geradas(),
        # As rodadas, cada uma com o botao de descartar.
        "rodadas": servico.listar_simulados(),
        # Os dois cadernos da fase 4: os meus erros, e o compilado pelos
        # pesos do edital - um plano por tamanho, para a tabela mostrar o
        # que cada um vai pedir antes de eu clicar.
        "erradas": len(servico.questoes_erradas()),
        "planos_compilados": [
            p for p in (servico.compilado.planejar(n)
                        for n in servico.compilado.TAMANHOS) if p
        ],
        "tamanhos": servico.compilado.TAMANHOS,
    }
    contexto.update(extra)
    return templates.TemplateResponse(
        request=request, name="simulado.html", context=contexto
    )


@app.get("/simulado", response_class=HTMLResponse)
def simulado_inicio(request: Request):
    """A tela de comecar, com o acumulado de acertos por materia."""
    return _pagina_do_simulado(request)


@app.post("/simulado/{simulado_id}/descartar")
def simulado_descartar(simulado_id: int):
    """Apaga a rodada e as respostas dela, do banco e do backup.

    So chega aqui pelo segundo botao - o de confirmar, dentro do <details> da
    tela. Rodada que nao existe mais (F5 depois de apagar) volta sem erro.
    """
    servico.descartar_simulado(simulado_id)
    return RedirectResponse("/simulado?descartado=1", status_code=303)


@app.post("/simulado/compilado")
def simulado_compilado(
    tamanho: int = Form(40),
    materias: list[str] = Form([]),
):
    """Monta o compilado pelos pesos do edital e vai para a primeira questao.

    Sem materia marcada, valem todas as do quadro - e o que "a prova" quer
    dizer. Tamanho fora da lista cai no primeiro dela.
    """
    if tamanho not in servico.compilado.TAMANHOS:
        tamanho = servico.compilado.TAMANHOS[0]
    montado = servico.compilado.criar_simulado_compilado(tamanho, materias or None)
    if montado is None:
        return RedirectResponse("/simulado", status_code=303)
    return RedirectResponse(f"/simulado/{montado[0].id}", status_code=303)


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
    de_ia = bool((simulado.filtros or {}).get("geradas"))

    if atual is None:
        # Rodada de questao gerada tem o acerto medido pelo outro lado: o
        # `desempenho` comum nao enxerga a tabela das geradas, e devolveria
        # uma tabela vazia no lugar do resultado.
        da_rodada = (
            servico.desempenho_das_geradas(simulado_id) if de_ia
            else servico.desempenho(simulado_id)
        )
        revisao = servico.revisao(simulado_id)
        return templates.TemplateResponse(
            request=request,
            name="relatorio.html",
            context={
                "simulado": simulado,
                "resumo": resumo,
                "de_ia": de_ia,
                "desempenho_da_rodada": da_rodada,
                "revisao": revisao,
                # O 🟣 de cada erro: a explicacao importada pelo caminho sem
                # API, e o macete que cita aquela questao.
                "explicacoes": servico.manual.carregar_explicacoes(),
                "macetes_da_questao": _macetes_por_questao(),
                "leis_das_materias": {
                    item.materia: leis.da_materia(item.materia) for item in revisao
                },
            },
        )

    resposta, questao = atual
    return templates.TemplateResponse(
        request=request,
        name="questao.html",
        context={
            "simulado": simulado,
            "resposta": resposta,
            "questao": questao,
            "resumo": resumo,
            "de_ia": de_ia,
            # O selo precisa dos dois: em que questao real ela se baseia, e
            # onde eu leio o artigo que ela diz estar cobrando.
            "origem": servico.geradas.origem_de(questao) if de_ia else None,
            "lei": (leis.do_assunto(questao.materia, questao.assunto)
                    if de_ia else None),
        },
    )


def _macetes_por_questao() -> dict[str, list]:
    """{"<caderno>#<numero>": [macete, ...]} dos macetes que podem aparecer.

    A mesma regra dos cartoes: macete sem fonte ou sem procedencia nao sai.
    """
    por_questao: dict[str, list] = {}
    for m in servico.manual.carregar_macetes():
        if not servico.cartoes._macete_aparece(m):
            continue
        for q in m.get("questoes") or []:
            chave = f"{q.get('prova_url')}#{q.get('numero')}"
            por_questao.setdefault(chave, []).append({**m, "origem": origem.IA})
    return por_questao


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


# --- questoes geradas pela IA (etapa 15) ------------------------------------
#
# Tela propria para GERAR, e a mesma tela de sempre para RESPONDER. Duas
# coisas diferentes: escrever questao de treino nao e o mesmo que treinar, mas
# uma segunda tela de responder questao seria so uma copia pior da primeira.

# O que cada recado de volta quer dizer. Vem pela URL porque o caminho passa
# por um redirecionamento - e sem isso o F5 mandaria gerar de novo.
RECADOS_DAS_GERADAS = {
    "sem_chave": (
        "Falta a chave da Anthropic. Ponha RADAR_ANTHROPIC_KEY no .env e "
        "recarregue - o passo a passo está em COMO_LIGAR_A_IA.txt."
    ),
    "sem_base": (
        "Não há questão real do meu cargo para variar nesta matéria."
    ),
    "nada": (
        "A IA não devolveu nenhuma questão aproveitável desta vez. Nada foi "
        "guardado; se houve chamada, ela foi cobrada do mesmo jeito."
    ),
    "errada": (
        "Marcada como errada. Ela saiu do sorteio para sempre, e as respostas "
        "dela saíram da conta do meu acerto."
    ),
}


@app.get("/geradas", response_class=HTMLResponse)
def geradas(
    request: Request,
    materia: str = "",
    assunto: str = "",
    subassunto: str = "",
    quantas: int = 5,
    modo: str = "",
    recado: str = "",
):
    """A tela de gerar questao, com o custo antes do botao.

    O filtro hierarquico e o MESMO do terminal (Etapa 5): o escopo sai do
    `radar.conteudos`, e nome que a arvore nao tem vira recado na tela, sem
    gerar nada - a §7 proibe gerar de outra coisa.
    """
    from radar import conteudos as arvore
    from radar import gerador

    escolhida = materia.strip() or None
    quantas = quantas if 1 <= quantas <= 30 else 5

    escopo = erro_do_escopo = None
    try:
        escopo = arvore.resolver_escopo(
            servico.conteudos.caminhos(), escolhida,
            assunto.strip() or None, subassunto.strip() or None,
        )
    except arvore.EscopoInvalido as erro:
        erro_do_escopo = str(erro)

    try:
        plano = servico.geradas.preparar(
            escolhida, quantas, escopo=escopo,
            modo=modo.strip() or None,
        )
    except (arvore.EscopoInvalido, ValueError) as erro:
        erro_do_escopo = erro_do_escopo or str(erro)
        plano = servico.geradas.preparar(escolhida, quantas)

    real = {d.materia: d for d in servico.desempenho()}
    gerado = {d.materia: d for d in servico.desempenho_das_geradas()}

    return templates.TemplateResponse(
        request=request,
        name="geradas.html",
        context={
            "plano": plano,
            "assunto": assunto,
            "subassunto": subassunto,
            "modo": modo,
            "erro_do_escopo": erro_do_escopo,
            # Os assuntos e subassuntos da materia escolhida, para o seletor
            # nao oferecer nome que nao existe.
            "assuntos": _filhos_na_tela(escolhida),
            "subassuntos": _filhos_na_tela(escolhida, assunto.strip() or None),
            "materias": servico.geradas.materias_para_gerar(),
            "resumo": servico.geradas.contar(),
            "materia": escolhida,
            "quantas": quantas,
            "cambio": config.CAMBIO_DE_REFERENCIA,
            "modelo": gerador.MODELO,
            "recado": RECADOS_DAS_GERADAS.get(recado),
            "desempenho_real": real,
            "desempenho_gerado": gerado,
            # A uniao das duas, para a tabela ter uma linha por materia mesmo
            # quando so um dos lados tem numero.
            "materias_com_acerto": sorted(set(real) | set(gerado)),
        },
    )


@app.post("/geradas/gerar")
def geradas_gerar(materia: str = Form(""), quantas: str = Form("5")):
    """Gera de verdade - isto GASTA - e cai direto na rodada com as novas.

    A rodada leva so o que acabou de nascer, e nao o acervo de geradas
    inteiro: eu cliquei para treinar estas, e nao para rever as de ontem.
    """
    pedidas = converter_valor(quantas)
    pedidas = int(pedidas) if pedidas and 1 <= pedidas <= 30 else 5
    escolhida = materia.strip() or None

    resultado = servico.geradas.gerar(materia=escolhida, quantas=pedidas)

    if resultado.get("erro"):
        return RedirectResponse(
            f"/geradas?recado={resultado['erro'].replace(' ', '_')}",
            status_code=303,
        )

    novas = resultado.get("impressoes") or []
    rodada = servico.geradas.criar_simulado(
        quantidade=len(novas), impressoes=novas
    ) if novas else None

    if rodada is None:
        return RedirectResponse("/geradas?recado=nada", status_code=303)
    return RedirectResponse(f"/simulado/{rodada.id}", status_code=303)


@app.post("/geradas/treinar")
def geradas_treinar(materia: str = Form(""), quantidade: str = Form("5")):
    """Uma rodada com o que ja foi gerado antes. Nao gasta nada."""
    quantas = converter_valor(quantidade)
    quantas = int(quantas) if quantas and 1 <= quantas <= 30 else 5

    rodada = servico.geradas.criar_simulado(
        quantidade=quantas, materia=materia.strip() or None
    )
    if rodada is None:
        return RedirectResponse("/geradas", status_code=303)
    return RedirectResponse(f"/simulado/{rodada.id}", status_code=303)


@app.post("/geradas/{questao_id}/errada")
def geradas_errada(questao_id: int, voltar: str = Form("/geradas")):
    """Um clique: a questao sai do sorteio para sempre.

    Volta para onde eu estava. No meio de uma rodada isso e a proxima questao,
    porque as respostas da rejeitada saem junto - e a rodada anda.
    """
    servico.geradas.rejeitar(questao_id)
    destino = voltar if voltar.startswith("/") else "/geradas"
    if destino == "/geradas":
        destino = "/geradas?recado=errada"
    return RedirectResponse(destino, status_code=303)


# --- previsao de abertura (fase 6) ------------------------------------------

@app.get("/", response_class=HTMLResponse)
def meu_foco(request: Request):
    """A home: o alvo, o que estudar agora, o que revisar - e duas faixas.

    Tres blocos cheios em vez dos cinco da especificacao: com pouco treino, a
    evolucao e as novidades nasceriam vazias, e bloco vazio do tamanho de um
    cheio e ruido. O detalhe do edital contra as provas foi para Analises.
    """
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "h": servico.inicio.montar(),
            "hoje": date.today(),
            # O cartao "Hoje no cronograma": so aparece em dia do ciclo.
            "cronograma_hoje": servico.cronograma.tela_do_dia(),
            "questoes_do_treino": foco_do_alvo.QUESTOES_DO_TREINO,
        },
    )


@app.get("/hoje", response_class=HTMLResponse)
def hoje(request: Request, data: str | None = None):
    """O dia do cronograma: horario, materia, questoes, e onde marco como foi."""
    return _pagina_de_hoje(request, data)


def _pagina_de_hoje(request: Request, data: str | None, erro: str | None = None,
                    form: dict | None = None, status: int = 200,
                    erro_da_faixa: str | None = None,
                    erro_do_extra: str | None = None,
                    form_do_extra: dict | None = None):
    quando = erro_de_data = None
    if data:
        try:
            quando = date.fromisoformat(data)
        except ValueError:
            erro_de_data = f"Data inválida: {data!r}. Use AAAA-MM-DD; mostrando hoje."
    tela = servico.cronograma.tela_do_dia(quando)
    return templates.TemplateResponse(
        request=request,
        name="hoje.html",
        status_code=status,
        context={
            "t": tela,
            # A ficha de estudo de cada faixa (Etapa 6B), pelo titulo do tema.
            # So le o data/fichas.json: abrir a tela Hoje continua rapido.
            "fichas_das_faixas": servico.fichas.das_faixas(tela.blocos),
            # O assunto, o subassunto e o elemento de cada faixa, na propria
            # faixa (decisao 71): pela ficha, ou pelos nos do plano.
            "arvore_das_faixas": servico.fichas.arvore_das_faixas(tela.blocos),
            # A composicao das faixas que medem (decisao 67) e a do simulado do
            # Qconcursos (decisao 69). So conta quando o dia tem uma delas.
            "composicoes": servico.composicao.das_faixas(tela.blocos, tela.data, tela.plano),
            # A revisao semanal, o R+7 dos diagnosticos e a comparacao do
            # fechamento (decisao 70). So conta no sabado.
            "do_sabado": servico.sabado.das_faixas(tela.blocos, tela.data, tela.plano),
            "erro": erro,
            "erro_de_data": erro_de_data,
            "form": form,
            "erro_da_faixa": erro_da_faixa,
            "erro_do_extra": erro_do_extra,
            "form_do_extra": form_do_extra,
            # Quantos erros do caderno vencem hoje. Vem daqui, e nao do
            # TelaDoDia, porque o caderno ja le o cronograma - e o contrario
            # tambem faria um importar o outro.
            "erros_para_rever": servico.erros.quantos_para_rever(),
        },
    )


def _inteiro(texto: str, campo: str) -> int | None:
    """Campo numerico do formulario: vazio vira None, lixo vira recusa."""
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return int(texto)
    except ValueError:
        raise servico.cronograma.RegistroInvalido(
            f"{campo} precisa ser um número inteiro (veio {texto!r})"
        )


@app.post("/hoje/rodada")
def hoje_rodada(data: str = Form(""), bloco: str = Form(""), indice: str = Form("")):
    """Cria a rodada da faixa que mede, ja com a composicao, e vai para ela.

    A rodada que ja existe e reaberta, e nunca recriada: o que eu respondi
    fica como foi gravado. Sem questao para compor, volta para a faixa.
    """
    try:
        quando = date.fromisoformat(data)
        posicao = int(indice)
    except ValueError:
        return RedirectResponse("/hoje", status_code=303)
    simulado = servico.composicao.criar_rodada_do_dia(quando, bloco, posicao)
    if simulado is None:
        return RedirectResponse(f"/hoje?data={quando.isoformat()}#faixa-{bloco}-{posicao}",
                                status_code=303)
    return RedirectResponse(f"/simulado/{simulado.id}", status_code=303)


@app.post("/hoje/registrar")
def hoje_registrar(
    request: Request,
    data: str = Form(""),
    meta: str = Form(""),
    anotacao: str = Form(""),
):
    """Grava como foi o dia e volta para ele. Recusa aparece na tela, sem 500.

    Desde a etapa E2 os numeros nao chegam mais do formulario: eles sao a soma
    das faixas marcadas, do estudo extra e do que eu respondi no radar. O que
    chega daqui e a META, que continua sendo escolha minha.
    """
    form = {"meta": meta, "anotacao": anotacao}
    try:
        quando = date.fromisoformat(data)
    except ValueError:
        return _pagina_de_hoje(request, None, erro=f"Data inválida: {data!r}.",
                               form=form, status=400)
    try:
        if not meta:
            raise servico.cronograma.RegistroInvalido(
                "Escolha como foi o dia: Ideal, Reduzida, Mínima ou Não fiz."
            )
        servico.cronograma.registrar_o_dia(quando, meta, anotacao.strip() or None)
    except servico.cronograma.RegistroInvalido as erro:
        return _pagina_de_hoje(request, data, erro=str(erro), form=form, status=400)

    cor = request.query_params.get(PARAMETRO_DA_COR)
    destino = f"/hoje?data={quando.isoformat()}" + (f"&cor={cor}" if cor else "")
    return RedirectResponse(destino, status_code=303)


@app.post("/hoje/faixa")
def hoje_faixa(
    request: Request,
    data: str = Form(""),
    bloco: str = Form(""),
    indice: str = Form(""),
    titulo: str = Form(""),
):
    """O circulo de cada faixa: marca ou desmarca, e volta para a MESMA faixa
    (o #faixa-... no fim do endereco), para eu nao perder o lugar na tela.

    O titulo vem junto de proposito: se o cronograma.yml mudou desde que a
    tela abriu, o servico recusa em vez de marcar a faixa errada.
    """
    try:
        quando = date.fromisoformat(data)
    except ValueError:
        return _pagina_de_hoje(request, None, erro_da_faixa=f"Data inválida: {data!r}.",
                               status=400)
    try:
        posicao = _inteiro(indice, "A faixa")
        if posicao is None:
            raise servico.cronograma.RegistroInvalido("Faltou dizer qual faixa marcar.")
        servico.cronograma.marcar_faixa(quando, bloco, posicao, titulo)
    except servico.cronograma.RegistroInvalido as erro:
        return _pagina_de_hoje(request, data, erro_da_faixa=str(erro), status=400)

    # Bloco e posicao ja passaram pelo servico: o endereco so leva o que e valido.
    cor = request.query_params.get(PARAMETRO_DA_COR)
    destino = (f"/hoje?data={quando.isoformat()}" + (f"&cor={cor}" if cor else "")
               + f"#faixa-{bloco}-{posicao}")
    return RedirectResponse(destino, status_code=303)


@app.post("/hoje/faixa/questoes")
def hoje_faixa_questoes(
    request: Request,
    data: str = Form(""),
    bloco: str = Form(""),
    indice: str = Form(""),
    titulo: str = Form(""),
    questoes: str = Form(""),
    acertos: str = Form(""),
    consulta: str = Form(""),
    conteudo: str = Form(""),
    desmarcar: str = Form(""),
):
    """O "fiz X, acertei Y" de uma faixa de questoes, e o botao de desmarcar.

    Volta para a MESMA faixa, como o circulo: a tela Hoje e longa, e perder o
    lugar depois de anotar um numero e o tipo de atrito que faz parar de anotar.
    """
    try:
        quando = date.fromisoformat(data)
    except ValueError:
        return _pagina_de_hoje(request, None, erro_da_faixa=f"Data inválida: {data!r}.",
                               status=400)
    try:
        posicao = _inteiro(indice, "A faixa")
        if posicao is None:
            raise servico.cronograma.RegistroInvalido("Faltou dizer qual faixa marcar.")
        if desmarcar:
            servico.cronograma.desmarcar_faixa(quando, bloco, posicao, titulo)
        else:
            servico.cronograma.anotar_faixa(
                quando, bloco, posicao, titulo,
                questoes=questoes, acertos=acertos, consulta=bool(consulta),
                conteudo=conteudo,
            )
    except servico.cronograma.RegistroInvalido as erro:
        return _pagina_de_hoje(request, data, erro_da_faixa=str(erro), status=400)

    cor = request.query_params.get(PARAMETRO_DA_COR)
    destino = (f"/hoje?data={quando.isoformat()}" + (f"&cor={cor}" if cor else "")
               + f"#faixa-{bloco}-{posicao}")
    return RedirectResponse(destino, status_code=303)


def _volta_do_dia(request: Request, quando: date, ancora: str = "extras") -> str:
    cor = request.query_params.get(PARAMETRO_DA_COR)
    return (f"/hoje?data={quando.isoformat()}" + (f"&cor={cor}" if cor else "")
            + f"#{ancora}")


@app.post("/hoje/extra")
def hoje_extra_novo(
    request: Request,
    data: str = Form(""),
    o_que: str = Form("questoes"),
    materia: str = Form(""),
    assunto: str = Form(""),
    minutos: str = Form(""),
    questoes: str = Form(""),
    acertos: str = Form(""),
    consulta: str = Form(""),
    onde: str = Form("outro"),
    anotacao: str = Form(""),
    conteudo: str = Form(""),
):
    """Anota um estudo que eu fiz fora das faixas do plano."""
    try:
        quando = date.fromisoformat(data)
    except ValueError:
        return _pagina_de_hoje(request, None, erro_do_extra=f"Data inválida: {data!r}.",
                               status=400)
    try:
        servico.extra.anotar(
            data=quando, o_que=o_que, materia=materia, assunto=assunto,
            minutos=minutos, questoes=questoes, acertos=acertos,
            consulta=bool(consulta), onde=onde, anotacao=anotacao,
            conteudo=conteudo,
        )
    except servico.cronograma.RegistroInvalido as erro:
        return _pagina_de_hoje(request, data, erro_do_extra=str(erro),
                               form_do_extra={
                                   "o_que": o_que, "materia": materia,
                                   "assunto": assunto, "minutos": minutos,
                                   "questoes": questoes, "acertos": acertos,
                                   "consulta": consulta, "onde": onde,
                                   "anotacao": anotacao, "conteudo": conteudo},
                               status=400)
    return RedirectResponse(_volta_do_dia(request, quando), status_code=303)


@app.post("/hoje/extra/{ident}")
def hoje_extra_editar(
    request: Request,
    ident: int,
    data: str = Form(""),
    o_que: str = Form("questoes"),
    materia: str = Form(""),
    assunto: str = Form(""),
    minutos: str = Form(""),
    questoes: str = Form(""),
    acertos: str = Form(""),
    consulta: str = Form(""),
    onde: str = Form("outro"),
    anotacao: str = Form(""),
    conteudo: str = Form(""),
    apagar: str = Form(""),
):
    """Corrige ou apaga um estudo extra que eu ja tinha anotado."""
    try:
        quando = date.fromisoformat(data)
    except ValueError:
        return _pagina_de_hoje(request, None, erro_do_extra=f"Data inválida: {data!r}.",
                               status=400)
    if apagar:
        # Apagar o que nao existe mais (F5 na pagina) nao e erro: a tela
        # recarregada ja conta a verdade.
        servico.extra.apagar(ident)
        return RedirectResponse(_volta_do_dia(request, quando), status_code=303)
    try:
        servico.extra.editar(
            ident, data=quando, o_que=o_que, materia=materia, assunto=assunto,
            minutos=minutos, questoes=questoes, acertos=acertos,
            consulta=bool(consulta), onde=onde, anotacao=anotacao,
            conteudo=conteudo,
        )
    except servico.cronograma.RegistroInvalido as erro:
        return _pagina_de_hoje(request, data, erro_do_extra=str(erro), status=400)
    return RedirectResponse(_volta_do_dia(request, quando), status_code=303)


@app.get("/semanas", response_class=HTMLResponse)
def semanas(request: Request, erro: str | None = None):
    """Como eu fui em cada semana, agrupado pelos ciclos do mapa do ano.

    A conta inteira mora em `servico.semanas`; aqui so entra o que e de tela.
    """
    try:
        plano = cronograma.carregar()
    except FileNotFoundError as falta:
        return templates.TemplateResponse(
            request=request, name="semanas.html",
            context={"ciclos": [], "mensagem": f"Não achei {falta.filename}."},
        )
    except cronograma.ErroNoCronograma as problema:
        return templates.TemplateResponse(
            request=request, name="semanas.html",
            context={"ciclos": [], "mensagem": str(problema)},
        )

    hoje = servico.cronograma.hoje_local()
    return templates.TemplateResponse(
        request=request,
        name="semanas.html",
        context={
            "ciclos": servico.semanas.montar(plano, hoje),
            "plano": plano,
            "hoje": hoje,
            "erro": erro,
            "mensagem": None,
        },
    )


@app.post("/semanas/nota")
def semanas_nota(
    request: Request,
    inicio: str = Form(""),
    funcionou: str = Form(""),
    ajustar: str = Form(""),
):
    """A reflexao da semana: o que funcionou e o que ajustar."""
    try:
        quando = date.fromisoformat(inicio)
        servico.semanas.anotar(quando, funcionou, ajustar)
    except (ValueError, servico.cronograma.RegistroInvalido) as problema:
        return semanas(request, erro=str(problema))

    cor = request.query_params.get(PARAMETRO_DA_COR)
    destino = "/semanas" + (f"?cor={cor}" if cor else "")
    return RedirectResponse(f"{destino}#semana-{quando.isoformat()}", status_code=303)


@app.post("/hoje/plano-b")
def hoje_plano_b(request: Request, data: str = Form(""), minutos: str = Form("")):
    """Os botoes do Plano B: 30 ou 60 ativa; vazio volta ao plano completo."""
    try:
        quando = date.fromisoformat(data)
    except ValueError:
        return _pagina_de_hoje(request, None, erro_da_faixa=f"Data inválida: {data!r}.",
                               status=400)
    try:
        servico.cronograma.ativar_plano_b(quando, _inteiro(minutos, "O tempo do Plano B"))
    except servico.cronograma.RegistroInvalido as erro:
        return _pagina_de_hoje(request, data, erro_da_faixa=str(erro), status=400)

    cor = request.query_params.get(PARAMETRO_DA_COR)
    destino = f"/hoje?data={quando.isoformat()}" + (f"&cor={cor}" if cor else "")
    return RedirectResponse(destino, status_code=303)


@app.post("/revisao/hoje")
def revisao_de_hoje():
    """As revisoes espacadas que venceram, numa rodada so."""
    novo = servico.espacada.criar_simulado_de_revisao()
    if novo is None:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/simulado/{novo.id}", status_code=303)


@app.post("/revisar")
def revisar_agora():
    """[Revisar agora]: uma rodada so com o que eu errei na ultima vez."""
    novo = servico.criar_simulado_de_erros()
    if novo is None:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/simulado/{novo.id}", status_code=303)


@app.get("/analises", response_class=HTMLResponse)
def analises(request: Request):
    """O que era a home ate a navegacao nova: o edital contra as provas, o
    meu acerto por materia e onde estudar primeiro, com o detalhe inteiro."""
    painel = foco_do_alvo.montar()
    return templates.TemplateResponse(
        request=request,
        name="foco.html",
        context={
            "p": painel,
            "rotulo_situacao": SITUACAO_LEGIVEL,
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


@app.get("/analises/materias", response_class=HTMLResponse)
def analises_materias(request: Request):
    """O progresso em cada materia do edital, e a projecao da prova.

    A conta inteira mora em `servico.materias`; aqui so entra o que e de tela.
    """
    try:
        plano = cronograma.carregar()
    except (FileNotFoundError, cronograma.ErroNoCronograma) as problema:
        mensagem = (f"Não achei {problema.filename}."
                    if isinstance(problema, FileNotFoundError) else str(problema))
        return templates.TemplateResponse(
            request=request, name="materias.html",
            context={"materias": [], "projecao": None, "mensagem": mensagem},
        )

    hoje = servico.cronograma.hoje_local()
    cartoes, projecao = servico.materias.montar(plano, hoje)
    return templates.TemplateResponse(
        request=request,
        name="materias.html",
        context={
            "materias": cartoes,
            "projecao": projecao,
            "plano": plano,
            "hoje": hoje,
            "mensagem": None,
        },
    )


@app.get("/fichas", response_class=HTMLResponse)
def fichas_do_cronograma(request: Request):
    """Os temas do cronograma de hoje em diante, com a ficha de cada um, a
    prioridade e o que ainda falta escrever."""
    return templates.TemplateResponse(
        request=request, name="fichas.html",
        context={"linhas": servico.fichas.lista(),
                 "hoje": servico.cronograma.hoje_local()},
    )


@app.get("/fichas/{ident}", response_class=HTMLResponse)
def ficha_de_estudo(request: Request, ident: str, data: str = ""):
    """A ficha inteira de um tema (secao 11): a tarefa com comeco, meio e fim.

    `data` e o dia aberto na tela Hoje, de onde vem o "por que agora". Toda a
    conta mora no `radar.fichas` e no `radar.prioridade`; aqui so a tela.
    """
    try:
        quando = date.fromisoformat(data) if data else servico.cronograma.hoje_local()
    except ValueError:
        quando = servico.cronograma.hoje_local()
    ficha = servico.fichas.ficha(ident, quando)
    if ficha is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request=request, name="ficha.html",
        context={"f": ficha, "data": quando,
                 "comando_de_gerar": fichas_puras.comando_de_gerar},
    )


@app.post("/fichas/{ident}/conferir")
def ficha_conferir(ident: str, data: str = Form("")):
    """Marca a ficha como conferida por mim, e volta para ela."""
    try:
        escrita = servico.fichas.conferir(ident)
    except LookupError:
        return RedirectResponse("/fichas", status_code=303)
    volta = f"/fichas/{escrita.id}" + (f"?data={data}" if data else "")
    return RedirectResponse(volta, status_code=303)


@app.get("/analises/desempenho", response_class=HTMLResponse)
def analises_desempenho(request: Request, materia: str = "", recorte: str = ""):
    """O meu desempenho por NO da arvore, com o estado e a amostra de cada um,
    quando eu estudei e revisei cada no (com a evolucao no assunto), o que
    voltou para revisao, o que eu nunca estudei e o que refazer.

    Toda a conta mora no `servico.desempenho_por_conteudo` e no
    `servico.estudo`; aqui so entra o que e de tela.
    """
    from radar.servico import desempenho_por_conteudo as por_conteudo

    escolhido = recorte if recorte in (por_conteudo.CICLO, por_conteudo.SEMPRE)         else por_conteudo.CICLO
    linhas = por_conteudo.tela(escolhido, materia or None)
    # Montadas uma vez so: a fila, os nao estudados e a ultima revisao saem
    # das mesmas situacoes.
    todas = servico.estudo.situacoes(recorte=escolhido)
    return templates.TemplateResponse(
        request=request, name="desempenho.html",
        context={
            "linhas": linhas,
            "materia": materia,
            "recorte": escolhido,
            "minimos": amostra.carregar(),
            # As materias da arvore, para o filtro - e nao so as que tem
            # resposta: eu preciso poder olhar uma materia vazia e ver que ela
            # esta vazia.
            "materias": sorted({no.nome for no in servico.conteudos.nos()
                                if no.nivel == "materia"}),
            "fila": servico.estudo.para_revisar(recorte=escolhido, todas=todas),
            "nao_estudados": servico.estudo.nao_estudados(todas=todas),
            "vistos": servico.estudo.estudados_ou_praticados(todas, materia or None),
            "refazer": servico.estudo.refazer(),
        },
    )


@app.get("/analises/incidencia", response_class=HTMLResponse)
def analises_incidencia(request: Request, materia: str = ""):
    """O mapa de incidencia do alvo, por no da arvore, sempre com a amostra.
    Os padroes de cobranca de cada no vao junto, ou a frase da falta de
    evidencia quando a amostra nao chega ao minimo do config/amostra.yml."""
    from radar import incidencia as regra

    mapas = servico.incidencia.mapa(materia or None)
    minimos = regra.carregar_minimos()
    # Lido uma vez so: a linha e os padroes do complementar saem da mesma
    # leitura, que e a parte cara desta tela.
    do_complementar = servico.incidencia.ocorrencias_complementares()
    return templates.TemplateResponse(
        request=request, name="incidencia.html",
        context={
            "mapas": mapas, "materia": materia, "minimos": minimos,
            # A linha do acervo complementar, SEMPRE separada da do alvo.
            "complementar": servico.incidencia.linhas_complementares(do_complementar),
            "padroes": {l.caminho: regra.padroes(l, minimos)
                        for m in mapas for l in m.linhas},
            # Os do acervo complementar, so das provas com gabarito
            # definitivo, ao lado dos do alvo e nunca somados (decisao 78).
            "padroes_complementares": servico.incidencia.padroes_complementares(
                mapas, minimos, do_complementar),
            # Os conceitos que caem juntos nas questoes do alvo (§14, item 7).
            "associados": servico.incidencia.associacoes(mapas),
            "todas":[m.materia for m in servico.incidencia.mapa()] if materia else
                     [m.materia for m in mapas],
        },
    )


@app.get("/analises/conferencia", response_class=HTMLResponse)
def analises_conferencia(request: Request, materia: str = "", abertas: str = "",
                         anuladas: str = "", evidencia: str = "", amostra: str = ""):
    """A conferencia da classificacao: enunciado, alternativas, gabarito e a
    proposta lado a lado, com confirmar / corrigir / pendente. O alvo por
    padrao; o complementar aceito pelo filtro, com a amostra do catalogo."""
    recorte = "complementar" if evidencia == "complementar" else "alvo"
    tela = servico.classificacoes.conferencia(
        materia or None, so_abertas=bool(abertas), com_anuladas=bool(anuladas),
        evidencia_escolhida=recorte, so_amostra=bool(amostra))
    return templates.TemplateResponse(
        request=request, name="conferencia.html",
        context={"t": tela, "materia": materia, "abertas": bool(abertas),
                 "anuladas": bool(anuladas), "evidencia": recorte,
                 "amostra": bool(amostra) and recorte == "complementar"},
    )


@app.post("/analises/conferencia")
def analises_conferir(
    chave: str = Form(""),
    acao: str = Form(""),
    conteudo: str = Form(""),
    motivo: str = Form(""),
    materia: str = Form(""),
    abertas: str = Form(""),
    evidencia: str = Form(""),
    amostra: str = Form(""),
):
    """Grava a minha decisao sobre UMA questao e volta para o mesmo lugar."""
    try:
        if acao == "confirmar":
            servico.classificacoes.conferir(chave)
        elif acao == "corrigir":
            servico.classificacoes.conferir(chave, corrigir_para=conteudo)
        elif acao == "pendente":
            servico.classificacoes.conferir(chave, pendente=motivo)
        else:
            raise servico.classificacoes.ClassificacaoInvalida(f"Ação {acao!r} não existe.")
    except servico.classificacoes.ClassificacaoInvalida as erro:
        return HTMLResponse(f"<p>Não gravei: {escape(str(erro))}</p>", status_code=400)
    servico.classificacoes.exportar()
    volta = "/analises/conferencia?" + urlencode(
        {k: v for k, v in (("materia", materia), ("abertas", abertas),
                           ("evidencia", evidencia), ("amostra", amostra)) if v})
    return RedirectResponse(f"{volta}#q-{chave}", status_code=303)


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
    """Estudar e treinar: abre no Simulado. Macetes foi para a Revisao."""
    return RedirectResponse("/simulado", status_code=303)


@app.get("/revisao")
def revisao_secao():
    """Revisao abre no Caderno de erros: o que eu errei manda mais."""
    return RedirectResponse("/erros", status_code=303)


# --- o caderno de erros -------------------------------------------------------
# A tela e o formulario. A regra da revisao (1-7-30) mora em servico/erros.py;
# aqui so entra o que e de tela: o filtro, o "volta para onde eu estava" e a
# recusa aparecendo na propria pagina em vez de num 500.


def _erro_de_data(valor: str | None) -> tuple[date | None, str | None]:
    """Data de query string: vazia vira None, lixo vira aviso na tela."""
    if not valor:
        return None, None
    try:
        return date.fromisoformat(valor), None
    except ValueError:
        return None, f"Data inválida: {valor!r}. Use AAAA-MM-DD."


@app.get("/erros", response_class=HTMLResponse)
def erros_anotados(
    request: Request,
    materia: str | None = None,
    motivo: str | None = None,
    situacao: str | None = None,
    semana: str | None = None,
):
    """O caderno de erros: o que me derruba, e o que esta para rever hoje."""
    materia = (materia or "").strip() or None
    motivo = (motivo or "").strip() or None
    situacao = (situacao or "").strip() or servico.erros.SITUACAO_PADRAO
    if situacao not in servico.erros.SITUACOES:
        situacao = servico.erros.SITUACAO_PADRAO
    da_semana, aviso = _erro_de_data(semana)

    hoje = servico.cronograma.hoje_local()
    lista = servico.erros.listar(materia=materia, motivo=motivo,
                                situacao=situacao, semana=da_semana, hoje=hoje)
    # As contagens do topo saem de TODOS os erros do recorte de materia,
    # motivo e semana - e nao do que esta vencido hoje. "O que mais te
    # derruba" e uma pergunta sobre o caderno inteiro.
    do_recorte = servico.erros.listar(materia=materia, motivo=motivo,
                                      situacao="todos", semana=da_semana, hoje=hoje)
    por_materia, por_motivo = servico.erros.o_que_mais_derruba(do_recorte)

    return templates.TemplateResponse(
        request=request,
        name="erros.html",
        context={
            "erros": lista,
            "hoje": hoje,
            "materia": materia,
            "motivo": motivo,
            "situacao": situacao,
            "semana": da_semana,
            "aviso": aviso,
            "por_materia": por_materia,
            "por_motivo": por_motivo,
            "total_do_recorte": len(do_recorte),
            "materias": servico.erros.materias_do_caderno(),
            "para_rever": servico.erros.quantos_para_rever(hoje),
            "volta": _caminho_de_volta(request),
            "semana_de_ate": servico.erros.semana_de(da_semana) if da_semana else None,
        },
    )


def _caminho_de_volta(request: Request) -> str:
    """O endereco desta pagina, para o formulario saber para onde voltar."""
    consulta = urlencode([(k, v) for k, v in request.query_params.multi_items()])
    return request.url.path + (f"?{consulta}" if consulta else "")


@app.get("/erros/novo", response_class=HTMLResponse)
def erro_novo(
    request: Request,
    data: str | None = None,
    materia: str | None = None,
    assunto: str | None = None,
    volta: str | None = None,
):
    """O formulario, aceitando tudo pre-preenchido pelo endereco.

    E assim que o botao "Anotar erro" de cada faixa da tela Hoje funciona: ele
    manda a data do dia, a materia e o assunto da faixa, e a volta com a
    ancora da propria faixa. Sem isso, anotar um erro custava tres campos
    digitados de novo - e erro que custa some.
    """
    quando, aviso = _erro_de_data(data)
    return _formulario_de_erro(
        request,
        form={"data_estudo": (quando or servico.cronograma.hoje_local()).isoformat(),
              "materia": (materia or "").strip(),
              "assunto": (assunto or "").strip()},
        volta=volta,
        aviso=aviso,
    )


def _formulario_de_erro(request: Request, form: dict, volta: str | None,
                        erro: str | None = None, aviso: str | None = None,
                        status: int = 200):
    return templates.TemplateResponse(
        request=request,
        name="erro_novo.html",
        status_code=status,
        context={
            "form": form,
            "volta": _volta_interna(volta or "/erros"),
            "erro": erro,
            "aviso": aviso,
            "materias": servico.erros.materias_sugeridas(),
            # O dia em que este erro volta, se eu gravar agora. E a mesma
            # conta do servico, e nao um "+1" escrito no HTML.
            "volta_em": (servico.cronograma.hoje_local()
                         + timedelta(days=servico.erros.INTERVALOS[0])),
        },
    )


@app.post("/erros/novo")
def erro_gravar(
    request: Request,
    data_estudo: str = Form(""),
    materia: str = Form(""),
    assunto: str = Form(""),
    motivo: str = Form(""),
    regra: str = Form(""),
    fonte: str = Form("qconcursos"),
    referencia: str = Form(""),
    conteudo: str = Form(""),
    volta: str = Form(""),
):
    """Grava o erro e volta para onde eu estava. Recusa aparece na tela."""
    form = {"data_estudo": data_estudo, "materia": materia, "assunto": assunto,
            "motivo": motivo, "regra": regra, "fonte": fonte,
            "referencia": referencia, "conteudo": conteudo}
    quando, aviso = _erro_de_data(data_estudo)
    if aviso:
        return _formulario_de_erro(request, form, volta, erro=aviso, status=400)
    try:
        servico.erros.anotar(
            data_estudo=quando, materia=materia, assunto=assunto, motivo=motivo,
            regra=regra, fonte=fonte, referencia=referencia, conteudo=conteudo,
        )
    except servico.erros.ErroInvalido as recusa:
        return _formulario_de_erro(request, form, volta, erro=str(recusa), status=400)

    return RedirectResponse(_volta_interna(volta or "/erros"), status_code=303)


@app.post("/erros/{ident}/revisar")
def erro_revisar(
    request: Request,
    ident: int,
    resultado: str = Form(""),
    volta: str = Form(""),
):
    """Os botoes "Ja sei" e "Ainda erro" de cada erro vencido."""
    destino = _volta_interna(volta or "/erros")
    try:
        servico.erros.revisar(ident, resultado)
    except servico.erros.ErroInvalido:
        # Erro que nao existe mais (apagado noutra aba) ou botao desconhecido:
        # a lista recarregada ja conta a verdade, e 500 aqui nao ajuda ninguem.
        return RedirectResponse(destino, status_code=303)
    return RedirectResponse(destino, status_code=303)


@app.get("/mais", response_class=HTMLResponse)
def mais(request: Request):
    """Fontes e evidencias: de onde vem cada dado, e onde mudar as regras."""
    return templates.TemplateResponse(
        request=request,
        name="mais.html",
        context={
            "cobertura": servico.previsao.cobertura_do_historico(),
            "leis_conferidas": leis.mudancas_conferidas(),
            "leis_por_conferir": leis.mudancas_por_conferir(),
            "auditoria_existe": auditoria.caminho_padrao().exists(),
            "auditoria_gerada_em": auditoria.data_do_relatorio(),
            # Como foi o ultimo backup automatico. Aparece aqui, e nao na
            # home, porque backup nao e estudo: e manutencao - mas falha de
            # backup em silencio e como nao ter backup.
            "backup": automacao.ultimo_backup(),
        },
    )


@app.get("/auditoria", response_class=HTMLResponse)
def relatorio_de_auditoria(request: Request):
    """O docs/auditoria.md como esta, num <pre>: sem renderizar Markdown.

    Sem arquivo, a pagina diz como gerar - e responde 200, porque "ainda nao
    rodei a auditoria" e um estado normal, e nao um erro.
    """
    caminho = auditoria.caminho_padrao()
    texto = caminho.read_text(encoding="utf-8") if caminho.exists() else None
    return templates.TemplateResponse(
        request=request,
        name="auditoria.html",
        context={
            "texto": texto,
            "gerada_em": auditoria.data_do_relatorio(caminho),
        },
    )


@app.get("/previsao", response_class=HTMLResponse)
def previsao(request: Request):
    """Onde vale ficar de olho: municipio parado ha tempo demais."""
    return templates.TemplateResponse(
        request=request,
        name="previsao.html",
        context={
            "previsoes": servico.previsao_de_abertura(),
            # De onde vem o historico, e a faixa legal: os dois eram texto
            # escrito a mao na tela.
            "cobertura": servico.previsao.cobertura_do_historico(),
            "validade_minima": servico.previsao.VALIDADE_MINIMA,
            "validade_maxima": servico.previsao.VALIDADE_MAXIMA,
        },
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
        provas={f.materia: f.cadernos for f in composicao},
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
            # A Central de Macetes vem primeiro: e ela que fala da MINHA
            # prova. O recorte por banca, embaixo, e para explorar.
            "cartoes": servico.cartoes.cartoes(),
            "leis_conferidas": leis.mudancas_conferidas(),
            "leis_por_conferir": leis.mudancas_por_conferir(),
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


@app.get("/macetes/{impressao}/questoes", response_class=HTMLResponse)
def questoes_do_macete(request: Request, impressao: str):
    """[Ver questoes reais relacionadas]: o macete de IA ao lado da prova.

    E aqui que eu confiro o 🟣 contra o 🟢 - a questao como a banca escreveu,
    com o gabarito definitivo. Macete que nao existe, ou que perdeu a fonte ou
    a procedencia no arquivo, da 404: ele tambem nao aparece nos cartoes.
    """
    achado = servico.cartoes.questoes_do_macete(impressao)
    if achado is None:
        raise HTTPException(status_code=404)
    macete, relacionadas = achado
    return templates.TemplateResponse(
        request=request,
        name="macete_questoes.html",
        context={
            "macete": macete,
            "relacionadas": relacionadas,
            "lei": leis.da_materia(macete.get("materia")),
            "leis_conferidas": leis.mudancas_conferidas(),
            "leis_por_conferir": leis.mudancas_por_conferir(),
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
