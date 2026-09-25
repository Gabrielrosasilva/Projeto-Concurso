"""Regras do sistema: consultar o que foi coletado, e reunir os assuntos.

Os cinco assuntos que tinham tamanho proprio moram em arquivos ao lado -
`coleta`, `avisos`, `provas`, `simulado` e `previsao` - e sao reexportados
aqui. Isto e de proposito: `servico.coletar_tudo(...)` continua existindo
igual para a CLI, para a web e para os testes.
"""
import logging
from dataclasses import dataclass, field

from sqlalchemy import case, func, select

from radar import eventos as linha_do_tempo
from radar import (
    calendario,
    detalhes,
    elegibilidade as leitor_de_elegibilidade,
    perfil as meu_perfil,
    questoes as leitor_de_questoes,
    regioes,
)
from radar import provas as arquivos_de_prova

# A tela de macetes chama `servico.macetes.fatias(...)`: o modulo continua
# aqui de proposito, ainda que este arquivo nao o use mais.
from radar import macetes                       # noqa: F401 - usado pela web
from radar.collectors.base import Buscador
from radar.util import fuso_local
from radar.db import criar_tabelas, sessao
from radar.servico.previsao import (    # noqa: F401 - a fachada
    FOLGA,
    VALIDADE_MAXIMA,
    VALIDADE_MINIMA,
    PrevisaoDeAbertura,
    _prever,
    previsao_de_abertura,
)
from radar.servico.provas import (      # noqa: F401 - a fachada
    FONTES_COM_ACERVO,
    PAGINAS_DO_HOTSITE,
    PRIORIDADE_ACERVO,
    CoberturaDaMateria,
    ResultadoAcervo,
    ResultadoExtracao,
    _caminho,
    _companheiros,
    _concursos_com_prova,
    _documentos_do_hotsite,
    _hotsite,
    _ler_caderno,
    _provas_por_ler,
    _questoes_filtradas,
    analisar_banca,
    baixar_do_manifesto,
    bancas_com_questao,
    bancas_sem_acervo,
    assuntos_permitidos,
    classificar_assuntos,
    cobertura_de_assunto,
    composicao_do_caderno,
    contar_questoes,
    extrair_questoes,
    gravar_assuntos,
    incidencia_por_materia,
    montar_acervo,
    provas_parecidas,
    questoes_repetidas,
    questoes_sem_assunto,
    recado_sobre_o_cargo,
)
from radar.servico.simulado import (    # noqa: F401 - a fachada
    QUANTIDADE_PADRAO,
    DesempenhoDaMateria,
    ItemDeRevisao,
    OrigemDasQuestoes,
    _impressoes_ja_respondidas,
    _questoes_para_o_alvo,
    _respostas,
    _sortear_para_o_alvo,
    _sortear_questoes,
    buscar_simulado,
    contar_questoes_do_alvo,
    criar_simulado,
    criar_simulado_do_alvo,
    desempenho,
    desempenho_das_geradas,
    materias_disponiveis,
    materias_universais,
    questao_atual,
    responder,
    resumo_do_simulado,
    revisao,
    simulados_recentes,
)
# As questoes escritas pela IA entram como MODULO, e nao funcao a funcao:
# `criar_simulado`, `gerar` e `contar` ja existem nesta fachada querendo dizer
# outra coisa. Escreva `servico.geradas.criar_simulado(...)`, e fica dito na
# chamada que aquilo nao e questao de prova.
from radar.servico import geradas       # noqa: F401 - usado pela CLI e pela web
from radar.servico.avisos import (      # noqa: F401 - a fachada
    JANELA_DE_NOVIDADE_EM_DIAS,
    LIMITE_DE_AVISOS,
    RELEVANCIA_AVISO,
    ResultadoAviso,
    _e_novidade,
    _nao_avisados,
    avisar,
    avisar_favoritos,
)
from radar.servico.coleta import (      # noqa: F401 - a fachada
    CAMPOS_CALCULADOS,
    _anel_da_lotacao,
    CAMPOS_DA_FONTE,
    COLETORES,
    PAGINAS_POR_DIA,
    VALORES_SEM_INFORMACAO,
    ResultadoColeta,
    _aplicar_classificacao,
    _gravar,
    _marcar_historico_como_avisado,
    _situacao_pelas_datas,
    atualizar_situacoes,
    carga_inicial,
    coletar_tudo,
    reclassificar,
)
from radar.servico.comum import sem_acento as _sem_acento
from radar.models import RELEVANCIAS, Concurso, agora

log = logging.getLogger(__name__)


def contar_por_relevancia(incluir_noticias: bool = False) -> dict[str, int]:
    """Quantos concursos em cada anel. Alimenta os atalhos da pagina web."""
    criar_tabelas()
    consulta = select(Concurso.relevancia, func.count()).group_by(Concurso.relevancia)
    if not incluir_noticias:
        consulta = consulta.where(Concurso.tipo != "noticia")

    with sessao() as s:
        contagem = dict(s.execute(consulta).all())

    # garante todas as chaves, mesmo zeradas, para a pagina nao ter que checar
    return {anel: contagem.get(anel, 0) for anel in RELEVANCIAS}


def contar_por_alvo() -> dict[str, int]:
    """Quantos itens em cada marca de alvo. Noticia entra na conta.

    Noticia entra de proposito, ao contrario da contagem por anel: noticia
    sobre a Policia Penal SC e sinal, nao ruido - e o que avisa que o
    concurso vem antes de existir edital.
    """
    criar_tabelas()
    consulta = (
        select(Concurso.alvo, func.count())
        .where(Concurso.alvo.is_not(None))
        .group_by(Concurso.alvo)
    )
    with sessao() as s:
        return dict(s.execute(consulta).all())


def concursos_do_alvo(marca: str) -> list[Concurso]:
    """O que esta marcado com esse alvo, do mais novo para o mais velho."""
    criar_tabelas()
    consulta = (
        select(Concurso)
        .where(Concurso.alvo == marca)
        .order_by(Concurso.publicado_em.desc().nullslast())
    )
    with sessao() as s:
        return list(s.scalars(consulta))


def contar() -> int:
    """Quantos concursos existem no banco, sem filtro nenhum."""
    criar_tabelas()
    with sessao() as s:
        return s.scalar(select(func.count()).select_from(Concurso)) or 0


# O que aparece quando voce nao pede nada: o que esta perto. O resto continua
# no banco e sai com --relevancia ou --todos.
RELEVANCIA_PADRAO = ("nucleo", "proximo")


def listar(
    uf: str | None = None,
    banca: str | None = None,
    termo: str | None = None,
    situacao: str | None = None,
    relevancia: str | None = None,
    incluir_noticias: bool = False,
    todas_relevancias: bool = False,
    abertas: bool = False,
    favoritos: bool = False,
    salario_min: float | None = None,
    salario_max: float | None = None,
    limite: int = 30,
) -> list[Concurso]:
    """Consulta o que ja foi coletado, com filtros opcionais."""
    criar_tabelas()

    if abertas:
        # Ordena pelo prazo, nao pela data de publicacao: aqui o que importa
        # e o que fecha primeiro.
        consulta = select(Concurso).where(_inscricao_aberta()).order_by(
            Concurso.inscricoes_ate.asc()
        )
    elif favoritos:
        # Meus favoritos primeiro pelo que fecha antes; o que nao tem prazo
        # conhecido vai para o fim da lista, nao some.
        consulta = select(Concurso).order_by(
            Concurso.inscricoes_ate.asc().nullslast(),
            Concurso.publicado_em.desc().nullslast(),
        )
    else:
        # A ordem da lista responde "o que eu ainda posso fazer?": inscricao
        # aberta primeiro, depois quem nao tem prazo conhecido - que pode
        # abrir a qualquer momento - e por ultimo o que ja encerrou. Antes
        # disto o primeiro cartao da tela era, em geral, um concurso vencido:
        # ordenar so por data de publicacao poe o mais novo na frente, e o
        # mais novo muitas vezes e o que acabou de fechar.
        #
        # Quem decide o grupo e a DATA, e nao o campo `situacao`: data e fato.
        # Dentro do grupo continua valendo o mais recente primeiro.
        consulta = select(Concurso).order_by(
            case(
                (_inscricao_aberta(), 0),
                (Concurso.inscricoes_ate.is_(None), 1),
                else_=2,
            ),
            Concurso.publicado_em.desc().nullslast(),
        )

    if favoritos:
        # Favorito e escolha minha: nenhum outro filtro pode esconder um.
        # Quem eu marquei, eu vejo, mesmo que seja longe ou ganhe pouco.
        consulta = consulta.where(Concurso.interesse == FAVORITO)
        with sessao() as s:
            return list(s.scalars(consulta.limit(limite)))

    # A partir daqui os filtros excluem - e o favorito escapa de todos eles.
    #
    # Isto era papel do mural lateral, que mostrava os favoritos em qualquer
    # aba. O mural saiu na etapa 8, e sem esta linha a promessa antiga -
    # "NENHUM filtro esconde um favorito, nem distancia, nem salario, nem
    # prazo vencido" - passaria a valer so dentro da aba Acompanhando.
    #
    # Busca explicita continua sendo busca: quem digita "Palhoca" ou escolhe
    # uma banca esta fazendo uma pergunta, e a resposta nao pode vir com um
    # favorito de Itajai no meio. Por isso o escape cobre os filtros que eu
    # nao pedi (o anel padrao, o salario), e nao os que eu digitei.
    escapa = Concurso.interesse == FAVORITO

    if salario_min is not None or salario_max is not None:
        # Filtro filtra: quem nao tem salario conhecido fica de fora.
        #
        # A primeira versao deixava os sem valor passarem, para nao esconder
        # concurso bom - mas 1.115 dos 2.185 nao trazem salario no titulo, e o
        # resultado era um filtro que nao filtrava nada. Quem usa precisa
        # saber do ponto cego, e nao adivinhar: a tela avisa quantos ficaram
        # de fora por falta de valor, e `contar_sem_salario` da esse numero.
        faixa = Concurso.salario.is_not(None)
        if salario_min is not None:
            faixa = faixa & (Concurso.salario >= salario_min)
        if salario_max is not None:
            faixa = faixa & (Concurso.salario <= salario_max)
        consulta = consulta.where(faixa | escapa)
        consulta = consulta.order_by(None).order_by(Concurso.salario.desc())

    # Noticia que veio junto no feed nao e concurso: fica de fora por padrao.
    if not incluir_noticias:
        consulta = consulta.where(Concurso.tipo != "noticia")

    if relevancia:
        # Anel escolhido a dedo e pergunta explicita, como a busca: aqui o
        # favorito nao escapa, senao "Longe" viria com um favorito de Palhoca.
        consulta = consulta.where(Concurso.relevancia == relevancia)
    elif not todas_relevancias:
        # Este e o recorte que eu NAO pedi - ele e o padrao da tela. Favorito
        # passa por cima dele: foi para isso que eu marquei a estrela.
        consulta = consulta.where(
            Concurso.relevancia.in_(RELEVANCIA_PADRAO) | escapa
        )

    if uf:
        consulta = consulta.where(Concurso.uf == uf.upper())
    if banca:
        # Aceita o nome curto e o por extenso: quem digita "Fundacao Carlos
        # Chagas" quer os mesmos concursos de quem digita "FCC".
        nomes = expandir_banca(banca)
        if nomes:
            consulta = consulta.where(
                Concurso.banca.in_(nomes) | Concurso.banca.ilike(f"%{banca}%")
            )
        else:
            consulta = consulta.where(Concurso.banca.ilike(f"%{banca}%"))
    if situacao:
        consulta = consulta.where(Concurso.situacao == situacao)
    if termo:
        # Busca ignorando acento: quem digita no campo raramente poe cedilha,
        # e "Palhoca" precisa achar "Palhoca" acentuada.
        procurado = f"%{_sem_acento(termo)}%"
        sem_acento_sql = func.sem_acento
        consulta = consulta.where(
            sem_acento_sql(Concurso.titulo).ilike(procurado)
            | sem_acento_sql(func.coalesce(Concurso.resumo, "")).ilike(procurado)
            | sem_acento_sql(func.coalesce(Concurso.municipio, "")).ilike(procurado)
        )

    with sessao() as s:
        return list(s.scalars(consulta.limit(limite)))


# --- inscricoes abertas (fase 2.5) ------------------------------------------

def _inscricao_aberta():
    """Condicao SQL de "da para se inscrever hoje".

    Exige `inscricoes_ate` preenchido: sem prazo conhecido nao da para afirmar
    que esta aberto. O comeco e opcional - se eu sei que fecha dia 30 mas nao
    sei quando abriu, ainda assim vale mostrar.
    """
    hoje = agora()
    return (
        Concurso.inscricoes_ate.is_not(None)
        & (Concurso.inscricoes_ate >= hoje)
        & (Concurso.inscricoes_de.is_(None) | (Concurso.inscricoes_de <= hoje))
        & (Concurso.tipo != "noticia")
    )


def contar_abertas() -> int:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(
            select(func.count()).select_from(Concurso).where(_inscricao_aberta())
        ) or 0


# --- leitura da pagina de detalhe -------------------------------------------

# Ordem de prioridade para gastar requisicao. Ler a pagina de todos os 2.200
# levaria quase uma hora e nao serviria para nada: 1.400 sao de outro estado.
PRIORIDADE_DETALHE = (
    # 1. o que ja sei que esta perto
    lambda: Concurso.relevancia.in_(("nucleo", "proximo")),
    # 2. orgao estadual de SC: a pagina e que diz os polos de prova, e e onde
    #    mora a carreira que eu mais quero
    lambda: Concurso.relevancia == "estadual",
    # 3. concurso de SC que ficou indefinido - e aqui que mora o caso da
    #    SEFAZ SC: orgao estadual nao tem "Prefeitura de X" no titulo, entao
    #    o classificador nao acha municipio e marca indefinida
    lambda: (Concurso.relevancia == "indefinida") & (Concurso.uf == "SC"),
    # 4. federal ou nacional: pode aplicar prova em Florianopolis
    lambda: (Concurso.relevancia == "indefinida") & Concurso.uf.is_(None),
)


@dataclass
class ResultadoDetalhe:
    lidos: int = 0
    com_prazo: int = 0
    com_banca: int = 0
    reclassificados: int = 0
    erros: int = 0

    def __str__(self) -> str:
        if not self.lidos:
            return "Nada novo para detalhar."
        texto = (
            f"{self.lidos} pagina(s) lida(s): {self.com_prazo} com prazo de "
            f"inscricao, {self.com_banca} com banca"
        )
        if self.reclassificados:
            texto += f", {self.reclassificados} mudaram de anel"
        if self.erros:
            texto += f", {self.erros} falharam"
        return texto


def _pendentes_de_detalhe(limite: int) -> list[Concurso]:
    """Quem ainda nao teve a pagina lida, na ordem de prioridade."""
    escolhidos: list[Concurso] = []
    vistos: set[int] = set()

    with sessao() as s:
        for condicao in PRIORIDADE_DETALHE:
            if len(escolhidos) >= limite:
                break
            consulta = (
                select(Concurso)
                .where(Concurso.detalhado_em.is_(None))
                .where(Concurso.tipo != "noticia")
                .where(condicao())
                .order_by(Concurso.publicado_em.desc().nullslast())
                .limit(limite - len(escolhidos))
            )
            for concurso in s.scalars(consulta):
                if concurso.id not in vistos:
                    vistos.add(concurso.id)
                    escolhidos.append(concurso)

    return escolhidos


def detalhar_pendentes(limite: int = 150) -> ResultadoDetalhe:
    """Le a pagina de cada concurso que interessa e completa o registro.

    Traz prazo de inscricao, banca e - quando a pagina deixa claro - o
    municipio de lotacao. O municipio novo faz o registro ser reclassificado,
    que e como um concurso estadual sai de `indefinida` para `nucleo`.
    """
    criar_tabelas()
    resultado = ResultadoDetalhe()

    pendentes = _pendentes_de_detalhe(limite)
    if not pendentes:
        return resultado

    municipios = regioes.nomes_originais()
    buscador = Buscador()

    for pendente in pendentes:
        try:
            html = buscador.get(pendente.url).text
        except Exception as erro:  # noqa: BLE001 - pagina fora do ar e rotina
            log.warning("nao consegui ler %s: %s", pendente.url, type(erro).__name__)
            resultado.erros += 1
            continue

        ano = pendente.publicado_em.year if pendente.publicado_em else agora().year
        achado = detalhes.extrair(html, ano, municipios)
        resultado.lidos += 1

        with sessao() as s:
            concurso = s.get(Concurso, pendente.id)
            concurso.detalhado_em = agora()

            if achado.inscricoes_ate:
                # So vira evento quando o prazo MUDA: `detalhar` pode passar de
                # novo pela mesma pagina, e reler nao e acontecimento.
                if achado.inscricoes_ate != concurso.inscricoes_ate:
                    linha_do_tempo.registrar_prazo(
                        s, concurso.url, achado.inscricoes_de,
                        achado.inscricoes_ate, concurso.url,
                    )
                concurso.inscricoes_de = achado.inscricoes_de
                concurso.inscricoes_ate = achado.inscricoes_ate
                resultado.com_prazo += 1
            if achado.banca and not concurso.banca:
                concurso.banca = achado.banca
                resultado.com_banca += 1
            if achado.hotsite and not _hotsite(concurso):
                # E o que liga o concurso ao acervo: sem hotsite, quem vem do
                # feed de noticias nunca rende edital nem prova.
                extra = dict(concurso.extra or {})
                extra["hotsite"] = achado.hotsite
                concurso.extra = extra

            # Municipio novo muda o anel: e o caminho da SEFAZ SC sair de
            # indefinida para nucleo.
            if achado.municipio and not concurso.municipio:
                anel_antes = concurso.relevancia
                concurso.municipio = regioes.nome_canonico(achado.municipio)
                # veio da pagina, que e fonte melhor que o titulo
                concurso.municipio_confirmado = True
                # A frase e a conta sao as mesmas do reclassificar: uma
                # funcao so, para as duas nunca divergirem.
                concurso.relevancia, concurso.motivo_relevancia = (
                    _anel_da_lotacao(achado.municipio)
                )
                if concurso.relevancia != anel_antes:
                    resultado.reclassificados += 1

    atualizar_situacoes()
    return resultado


def expandir_banca(termo: str) -> list[str]:
    """Os nomes de banca que casam com o que foi digitado.

    Banca tem nome curto e nome por extenso, e quem busca usa qualquer um dos
    dois: "FCC" e "Fundacao Carlos Chagas" sao a mesma coisa. A tabela de
    apelidos ja existia em `detalhes.BANCAS`, usada para reconhecer a banca na
    pagina do edital; aqui ela serve ao contrario.
    """
    procurado = _sem_acento(termo).strip().lower()
    if not procurado:
        return []

    achados = [
        nome for nome, apelidos in detalhes.BANCAS.items()
        if procurado in _sem_acento(nome).lower()
        or any(procurado in apelido or apelido.strip() in procurado
               for apelido in apelidos)
    ]
    return achados


# --- favoritos (fase 1.55) --------------------------------------------------

# A coluna `interesse` e minha, nao da fonte: a coleta nunca a sobrescreve.
FAVORITO = "favorito"


def favoritar(concurso_id: int, favorito: bool = True) -> Concurso | None:
    """Marca ou desmarca um concurso como favorito."""
    criar_tabelas()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.interesse = FAVORITO if favorito else None
        return concurso


def alternar_favorito(concurso_id: int) -> Concurso | None:
    """Favorita se nao for, desfavorita se for. E o que o botao da tela faz."""
    criar_tabelas()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.interesse = None if concurso.interesse == FAVORITO else FAVORITO
        return concurso


def contar_sem_salario() -> int:
    """Quantos concursos nao trazem salario no titulo.

    E o ponto cego do filtro de remuneracao, e a tela mostra este numero para
    eu saber o tamanho do que estou deixando de ver.
    """
    criar_tabelas()
    with sessao() as s:
        return s.scalar(
            select(func.count()).select_from(Concurso)
            .where(Concurso.salario.is_(None))
            .where(Concurso.tipo != "noticia")
        ) or 0


def contar_favoritos() -> int:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(
            select(func.count()).select_from(Concurso)
            .where(Concurso.interesse == FAVORITO)
        ) or 0


# --- status derivado das datas ----------------------------------------------

def eventos_do_concurso(concurso_id: int) -> tuple[Concurso, list] | None:
    """A linha do tempo de um concurso, e o concurso junto.

    Devolve os dois porque quem mostra precisa do titulo: uma lista de datas
    sem dizer de que concurso e nao serve para nada. None quando o id nao
    existe.
    """
    criar_tabelas()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        return concurso, linha_do_tempo.do_concurso(s, concurso.url)


def definir_notas(concurso_id: int, texto: str | None) -> Concurso | None:
    """Grava a minha anotacao sobre o concurso.

    Este campo e MEU: a coleta nunca o sobrescreve, como acontece com
    `interesse`. E onde fica o que nenhuma fonte sabe - "conversei com quem
    fez em 2022", "prova cai no mesmo dia da outra", "conferir se aceita
    Sistemas de Informacao".
    """
    criar_tabelas()
    limpo = (texto or "").strip()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.notas = limpo or None
        return concurso


def definir_salario(concurso_id: int, valor: float | None) -> Concurso | None:
    """Grava o salario que eu digitei, e trava contra a proxima coleta.

    Existe porque 1.115 dos 2.185 concursos nao trazem valor no titulo. Sem
    isto, eles ficariam para sempre sem remuneracao conhecida e fora do filtro
    - inclusive os bons, como o de 300 vagas de Sao Jose.

    Passar None limpa o valor e devolve o campo ao classificador.
    """
    criar_tabelas()
    with sessao() as s:
        concurso = s.get(Concurso, concurso_id)
        if concurso is None:
            return None
        concurso.salario = valor
        concurso.salario_manual = valor is not None
        return concurso


# --- aba de noticias --------------------------------------------------------

# Quanto mais adiantado, maior o numero. Serve para ordenar do que esta mais
# proximo de acontecer para o que ja passou.
ORDEM_DAS_FASES = {
    "inscricoes_abertas": 0,
    "banca_definida": 1,
    "autorizado": 2,
    "prevista": 3,
    "edital_publicado": 4,
    "desconhecida": 5,
    "encerrado": 6,
}


def buscar_noticias(termo: str | None = None, limite: int = 60) -> list[Concurso]:
    """Busca em TUDO: qualquer anel, qualquer fase, inclusive o que virou
    noticia.

    As outras abas filtram para nao afogar o que importa. Aqui e o contrario:
    quem procura "PM" quer saber de qualquer concurso de policia militar, esteja
    ele onde estiver e na fase que estiver - inclusive os que ja passaram, que
    e o que diz se o orgao costuma abrir.

    A ordem nao e por data: e pelo ANDAMENTO. O que esta com inscricao aberta
    vem primeiro, depois o que tem banca contratada, depois o autorizado, e o
    encerrado por ultimo.
    """
    criar_tabelas()
    consulta = select(Concurso)

    if termo:
        procurado = f"%{_sem_acento(termo)}%"
        consulta = consulta.where(
            func.sem_acento(Concurso.titulo).ilike(procurado)
            | func.sem_acento(func.coalesce(Concurso.resumo, "")).ilike(procurado)
            | func.sem_acento(func.coalesce(Concurso.municipio, "")).ilike(procurado)
            | func.sem_acento(func.coalesce(Concurso.orgao, "")).ilike(procurado)
        )

    with sessao() as s:
        achados = list(s.scalars(consulta.limit(limite * 4)))

    achados.sort(key=lambda c: (
        ORDEM_DAS_FASES.get(c.situacao, 9),
        -(c.publicado_em.timestamp() if c.publicado_em else 0),
    ))
    return achados[:limite]


def contar_por_fase(termo: str | None = None) -> dict[str, int]:
    """Quantos concursos em cada fase, para o resumo da aba de noticias."""
    criar_tabelas()
    contagem: dict[str, int] = {}
    for concurso in buscar_noticias(termo=termo, limite=10000):
        contagem[concurso.situacao] = contagem.get(concurso.situacao, 0) + 1
    return contagem


# --- elegibilidade: o que o edital exige de mim (fase 2.5) ------------------

@dataclass
class ResultadoElegibilidade:
    concursos: int = 0
    lidos: int = 0
    ilegiveis: int = 0
    sem_edital: int = 0
    #: Os arquivos que nem abriram - PDF cortado no meio, quase sempre
    #: download interrompido. Guardo o NOME porque e o que permite apagar o
    #: arquivo e baixar de novo; o numero sozinho nao diz qual.
    quebrados: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if not self.concursos:
            return "Nenhum concurso com edital no acervo para ler."
        texto = f"{self.concursos} concurso(s), {self.lidos} com exigencias lidas"
        if self.ilegiveis:
            texto += f", {self.ilegiveis} com edital so em imagem"
        if self.sem_edital:
            texto += f", {self.sem_edital} sem edital no acervo"
        if self.quebrados:
            texto += (
                f", [yellow]{len(self.quebrados)} arquivo(s) corrompido(s)"
                f": {', '.join(self.quebrados[:3])}"
            )
            if len(self.quebrados) > 3:
                texto += f" e mais {len(self.quebrados) - 3}"
            texto += "[/]"
        return texto


def _editais_por_concurso() -> dict[str, list[dict]]:
    """{url do concurso: [registros de edital]}, do manifesto.

    O edital principal vem primeiro: e o maior arquivo. Termo aditivo e
    retificacao sao curtos e costumam mudar so um item, entao servem de
    segunda tentativa quando o principal nao rende nada.
    """
    por_concurso: dict[str, list[dict]] = {}
    for registro in arquivos_de_prova.carregar_manifesto():
        if registro.get("tipo") != arquivos_de_prova.EDITAL:
            continue
        if not registro.get("concurso_url"):
            continue
        por_concurso.setdefault(registro["concurso_url"], []).append(registro)

    for registros in por_concurso.values():
        registros.sort(key=lambda r: -(r.get("tamanho") or 0))
    return por_concurso


def _exigencias_do_concurso(
    registros: list[dict], quebrados: list[str] | None = None
) -> leitor_de_elegibilidade.Exigencias:
    """Le os editais daquele concurso ate um deles dizer alguma coisa.

    PDF que nem abre nao derruba a rodada. Acontece de verdade: download
    interrompido deixa no disco meio arquivo, e o leitor estoura
    `PdfStreamError` na primeira pagina. Antes disso parar aqui, o `radar
    elegibilidade` inteiro morria no primeiro arquivo cortado - e os outros 36
    concursos da fila ficavam sem ser lidos por causa de um.

    O arquivo que falhou vai para `quebrados` pelo NOME, e nao so contado: e o
    nome que permite apaga-lo e baixar de novo.
    """
    melhor = leitor_de_elegibilidade.Exigencias(legivel=False)

    for registro in registros:
        caminho = _caminho(registro)
        if caminho is None:
            continue

        try:
            texto = leitor_de_questoes.extrair_texto(caminho)
        except Exception as erro:  # noqa: BLE001 - de proposito: loga e segue
            nome = registro.get("arquivo") or caminho.name
            log.warning(
                "nao consegui ler o edital %s (%s)", nome, type(erro).__name__
            )
            if quebrados is not None:
                quebrados.append(nome)
            continue

        achado = leitor_de_elegibilidade.ler(texto)
        if achado.niveis:
            return achado
        if achado.legivel:
            melhor = achado

    return melhor


def ler_elegibilidade(limite: int = 50, refazer: bool = False) -> ResultadoElegibilidade:
    """Le os editais do acervo e grava o que cada concurso exige.

    Nao vai a internet: trabalha nos PDFs que `radar provas` ja baixou.
    """
    criar_tabelas()
    resultado = ResultadoElegibilidade()
    por_concurso = _editais_por_concurso()
    if not por_concurso:
        return resultado

    with sessao() as s:
        consulta = select(Concurso).where(Concurso.url.in_(list(por_concurso)))
        if not refazer:
            consulta = consulta.where(Concurso.elegibilidade == "a_confirmar")

        for concurso in s.scalars(consulta.limit(limite)):
            resultado.concursos += 1
            quebrados: list[str] = []
            exigencias = _exigencias_do_concurso(
                por_concurso[concurso.url], quebrados
            )
            resultado.quebrados.extend(quebrados)

            if not exigencias.legivel:
                resultado.ilegiveis += 1
                concurso.motivo_elegibilidade = leitor_de_elegibilidade.resumir(exigencias)
                continue

            _gravar_exigencias(concurso, exigencias)
            resultado.lidos += 1

    return resultado


def _gravar_exigencias(concurso: Concurso, exigencias) -> None:
    """Passa o que o edital diz para as colunas do concurso.

    `elegivel` aqui quer dizer uma coisa so: o concurso TEM vaga de nivel
    superior, que e o que eu posso prestar. Nao e promessa de que eu sirvo para
    todas as vagas dele - isso muda de cargo para cargo, e o radar guarda um
    registro por concurso.
    """
    if exigencias.niveis:
        concurso.escolaridade = ", ".join(exigencias.niveis)
    concurso.idade_maxima = exigencias.idade_maxima

    # O veredito cruza o edital com config/perfil.yml. Sem perfil preenchido
    # ele fica em "a confirmar", que e o certo: campo em branco quer dizer
    # "nao sei", e nao "nao tenho".
    veredito = meu_perfil.avaliar(exigencias)
    concurso.elegibilidade = veredito.situacao
    resumo = leitor_de_elegibilidade.resumir(exigencias)
    if veredito.motivo:
        resumo = f"{resumo} | {veredito.motivo}"
    concurso.motivo_elegibilidade = resumo[:300]

    # CNH e teste fisico nao tem coluna propria, e nao vale criar uma agora: o
    # que interessa e ver na tela, e o `extra` ja guarda o que a fonte manda.
    extra = dict(concurso.extra or {})
    extra["exigencias"] = {
        "cnh": exigencias.cnh,
        "taf": exigencias.taf,
        "idade_minima": exigencias.idade_minima,
        "trechos": exigencias.trechos,
    }
    concurso.extra = extra


# --- calendario (fase 2.2) --------------------------------------------------

def eventos_do_calendario() -> list[calendario.Evento]:
    """Os prazos que valem entrar na minha agenda.

    Entra o que e meu interesse declarado (favorito) e o que esta perto de
    casa. Fica de fora o que ja venceu: compromisso no passado so atrapalha
    quem abre a agenda.

    O prazo de inscricao e o unico dado do radar que nao pode ser visto tarde
    demais - por isso ele vai para o celular, e nao so para a tela.
    """
    criar_tabelas()
    hoje = agora().astimezone(fuso_local()).date()

    consulta = (
        select(Concurso)
        .where(Concurso.tipo != "noticia")
        .where(Concurso.inscricoes_ate.is_not(None))
        .where(
            (Concurso.interesse == FAVORITO)
            | Concurso.relevancia.in_(("nucleo", "proximo"))
        )
        .order_by(Concurso.inscricoes_ate)
    )

    eventos: list[calendario.Evento] = []
    with sessao() as s:
        for concurso in s.scalars(consulta):
            fim = concurso.inscricoes_ate.astimezone(fuso_local()).date()
            if fim < hoje:
                continue

            onde = concurso.municipio or concurso.uf or "local a confirmar"
            detalhe = [f"{onde}."]
            if concurso.banca:
                detalhe.append(f"Banca: {concurso.banca}.")
            if concurso.salario:
                detalhe.append(f"Salario: R$ {concurso.salario:,.0f}."
                               .replace(",", "."))
            if concurso.motivo_elegibilidade:
                detalhe.append(concurso.motivo_elegibilidade)

            eventos.append(calendario.Evento(
                # A url e a chave natural do concurso: o mesmo concurso gera
                # sempre o mesmo evento, e o calendario atualiza em vez de
                # duplicar quando o prazo muda.
                identificador=f"inscricao:{concurso.url}",
                titulo=f"Ultimo dia de inscricao: {concurso.titulo}",
                quando=fim,
                descricao=" ".join(detalhe),
                url=concurso.url,
            ))

            if concurso.data_prova:
                prova = concurso.data_prova.astimezone(fuso_local()).date()
                if prova >= hoje:
                    eventos.append(calendario.Evento(
                        identificador=f"prova:{concurso.url}",
                        titulo=f"Prova: {concurso.titulo}",
                        quando=prova,
                        descricao=" ".join(detalhe),
                        url=concurso.url,
                    ))

    return eventos


def calendario_ics() -> str:
    """O arquivo .ics pronto, com os prazos que valem a minha agenda."""
    return calendario.montar(eventos_do_calendario())


# --- retificacao de edital (fase 2.5) ---------------------------------------

@dataclass
class Retificacao:
    """Um edital que mudou depois de eu ter baixado."""

    concurso_url: str
    titulo: str
    arquivo: str
    url: str
    sha_antigo: str
    sha_novo: str


@dataclass
class ResultadoRetificacao:
    conferidos: int = 0
    mudaram: list[Retificacao] = field(default_factory=list)
    falhas: int = 0

    def __str__(self) -> str:
        # Falha de download tem que aparecer na frase, e com estas palavras.
        # Antes, edital nenhum baixado dava "Nenhum edital em pe para
        # conferir" - que e outra coisa, e a unica que eu nao precisaria
        # fazer nada a respeito. Nao conferir porque o site nao respondeu e
        # justamente o caso de rodar de novo mais tarde.
        if not self.conferidos and not self.falhas:
            return "Nenhum edital em pe para conferir."

        partes = []
        if self.conferidos:
            partes.append(f"{self.conferidos} edital(is) conferido(s)")
            partes.append(
                f"[bold red]{len(self.mudaram)} mudou(ram)[/]"
                if self.mudaram else "nenhum mudou"
            )
        if self.falhas:
            partes.append(
                f"[yellow]nao consegui baixar {self.falhas} edital(is)[/]"
            )
        return ", ".join(partes)


def _editais_em_pe() -> list[tuple[dict, Concurso]]:
    """Editais de concurso cuja inscricao ainda nao encerrou.

    So esses valem reconferir: edital de concurso encerrado nao vai mais ser
    retificado, e cada conferencia custa uma requisicao e um download.
    """
    por_concurso = _editais_por_concurso()
    if not por_concurso:
        return []

    agora_ = agora()
    pares: list[tuple[dict, Concurso]] = []
    with sessao() as s:
        for concurso in s.scalars(
            select(Concurso).where(Concurso.url.in_(list(por_concurso)))
        ):
            if concurso.inscricoes_ate and concurso.inscricoes_ate < agora_:
                continue
            if concurso.situacao == "encerrado":
                continue
            for registro in por_concurso[concurso.url]:
                if registro.get("sha256"):
                    pares.append((registro, concurso))
    return pares


def conferir_retificacoes(limite: int = 20) -> ResultadoRetificacao:
    """Baixa de novo os editais em pe e ve se o conteudo mudou.

    O manifesto ja guarda o sha256 de cada arquivo desde a fase 3 - ele existia
    para reconstruir o acervo noutra maquina. Serve tambem para isto: se o
    mesmo endereco passa a devolver bytes diferentes, o edital foi retificado.

    Retificacao muda prazo, vaga e requisito. Descobrir isso tarde e o tipo de
    erro que nao da para corrigir depois.
    """
    criar_tabelas()
    resultado = ResultadoRetificacao()
    buscador = Buscador()

    for registro, concurso in _editais_em_pe()[:limite]:
        documento = arquivos_de_prova.Documento(
            tipo=arquivos_de_prova.EDITAL,
            url=registro["url"],
            arquivo=registro.get("arquivo", ""),
            banca=registro.get("banca"),
            municipio=registro.get("municipio"),
            ano=registro.get("ano"),
            concurso_url=registro.get("concurso_url"),
        )

        # `forcar` porque o arquivo ja esta em disco: sem isso, `baixar`
        # devolveria o sha do que eu tenho e nunca acusaria mudanca.
        baixado = arquivos_de_prova.baixar(documento, buscador, forcar=True)
        if baixado is None:
            resultado.falhas += 1
            continue

        resultado.conferidos += 1
        if baixado.sha256 == registro["sha256"]:
            continue

        resultado.mudaram.append(Retificacao(
            concurso_url=concurso.url,
            titulo=concurso.titulo,
            arquivo=registro.get("arquivo", ""),
            url=registro["url"],
            sha_antigo=registro["sha256"],
            sha_novo=baixado.sha256,
        ))

        # A linha do tempo guarda o que o aviso do Telegram nao guarda: daqui
        # a seis meses eu ainda vou poder ver que este edital ja foi retificado
        # duas vezes, e quando.
        with sessao() as s:
            linha_do_tempo.registrar_retificacao(
                s, concurso.url, registro.get("arquivo", ""), registro["url"]
            )

        # O manifesto passa a valer o arquivo novo, senao a proxima conferencia
        # acusaria a mesma retificacao de novo.
        todos = arquivos_de_prova.carregar_manifesto()
        for linha in todos:
            if linha.get("url") == registro["url"]:
                linha.update(arquivos_de_prova.para_registro(baixado))
        arquivos_de_prova.gravar_manifesto(todos)

    return resultado
