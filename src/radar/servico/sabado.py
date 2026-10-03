"""O sabado do cronograma: a revisao semanal, o R+7 dos diagnosticos e a
comparacao do fechamento (subetapa 2B, decisao 70).

O sabado era a parte mais generica do plano - "refaca TODAS as questoes que
voce errou", "releia os artigos-chave da semana", "compare com o diagnostico"
-, sem dizer quais nem com que numero. Aqui ele passa a dizer, com o que ja
esta gravado: os temas da semana (o plano), os erros anotados (o caderno), os
artigos-chave (o `essencial` de cada dia) e as rodadas que mediram (o radar).
Nenhum numero daqui esta escrito a mao no cronograma.yml.

Toda conta de acerto e de erro de rodada passa pelo `servico/metricas.py`, e
o minimo de amostra sai do `config/amostra.yml`, pelo `radar/amostra.py`.
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select

from radar import amostra as regua
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar import fichas
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.origem import AUTOMATICO
from radar.servico import compilado, composicao, metricas
from radar.servico import erros as caderno
from radar.servico import fichas as servico_fichas
from radar.servico.classificacoes import chave_de

# --- a revisao semanal -----------------------------------------------------------


@dataclass
class TemaDaSemana:
    """Um tema estudado na semana, com o que o caderno tem dele."""

    tema: str
    materia: str
    data: date                    # o dia da faixa de estudo
    nos: list[str] = field(default_factory=list)    # os da ficha
    ficha_id: str | None = None
    erros: int = 0                # anotados no caderno nesta semana


@dataclass
class ArtigoDaSemana:
    data: date
    artigos: str
    porque: str


@dataclass
class RevisaoDaSemana:
    """O que a Revisao semanal do sabado revisa, ja dito."""

    tipo = "revisao_semanal"
    origem = AUTOMATICO

    inicio: date
    fim: date
    temas: list[TemaDaSemana]
    #: Os erros anotados na semana, todos: e a lista do link "abrir os erros
    #: da semana", e por isso o mesmo numero.
    erros: int
    #: Os que nao casam com um tema da semana (sem assunto, ou de outro tema).
    sem_tema: int
    motivos: list                 # [erros.Contagem], o motivo mais comum primeiro
    artigos: list[ArtigoDaSemana]

    @property
    def mais_erros(self) -> list[TemaDaSemana]:
        """Os temas com mais erro, ate 5: "as 5 regras que mais te derrubaram"."""
        com_erro = sorted((t for t in self.temas if t.erros),
                          key=lambda t: (-t.erros, t.data, t.tema))
        return com_erro[:caderno.NO_QUE_DERRUBA]


def _do_tema(erro, temas: list[TemaDaSemana]) -> TemaDaSemana | None:
    """O tema da semana deste erro: pelo assunto que o "Anotar erro" da faixa
    preenche (o titulo dela), ou pelo no da arvore, quando o erro tem um."""
    chave = fichas.chave_do_tema(fichas.tema_da_faixa(erro.assunto, erro.materia))
    for tema in temas:
        if not compilado.mesma_materia(erro.materia or "", tema.materia):
            continue
        if chave and chave == fichas.chave_do_tema(tema.tema):
            return tema
        if erro.conteudo and tema.nos and fichas.dentro_de(tema.nos)(erro.conteudo):
            return tema
    return None


def revisao_da_semana(data: date, plano) -> RevisaoDaSemana | None:
    """A revisao do sabado `data`: os dias de estudo da semana dele.

    A semana e a do plano (`semana` do dia), e nao a do calendario: e ela que
    diz o que foi estudado. Os erros sao os do caderno de segunda a sabado - o
    mesmo filtro do link "abrir os erros da semana".
    """
    sabado = plano.dia(data)
    if sabado is None:
        return None
    dias = sorted((d for d in plano.dias if d.semana == sabado.semana and d.data < data),
                  key=lambda d: d.data)
    if not dias:
        return None

    escritas = servico_fichas.carregar()
    temas: dict[tuple, TemaDaSemana] = {}
    artigos: list[ArtigoDaSemana] = []
    for dia in dias:
        for bloco in plano_de_estudo.BLOCOS:
            for faixa in getattr(dia, bloco):
                if faixa.tipo not in fichas.TIPOS_QUE_DIZEM_O_TEMA or not faixa.materia:
                    continue
                tema = fichas.tema_da_faixa(faixa.titulo, faixa.materia)
                chave = (fichas.chave_do_tema(tema), faixa.materia)
                if chave in temas:
                    continue
                escrita = fichas.da_faixa(faixa, escritas)
                temas[chave] = TemaDaSemana(
                    tema=tema, materia=faixa.materia, data=dia.data,
                    nos=list(escrita.nos) if escrita else [],
                    ficha_id=escrita.id if escrita else None)
        if dia.essencial:
            artigos.extend(ArtigoDaSemana(dia.data, a.artigos, a.porque)
                           for a in dia.essencial.chave)

    da_semana = list(temas.values())
    anotados = caderno.listar(situacao="todos", semana=data)
    sem_tema = 0
    for erro in anotados:
        tema = _do_tema(erro, da_semana)
        if tema is None:
            sem_tema += 1
        else:
            tema.erros += 1
    _por_materia, motivos = caderno.o_que_mais_derruba(anotados)
    return RevisaoDaSemana(inicio=dias[0].data, fim=dias[-1].data, temas=da_semana,
                           erros=len(anotados), sem_tema=sem_tema, motivos=motivos,
                           artigos=artigos)


# --- as rodadas que mediram num dia ----------------------------------------------

def rodadas_do_dia(dia: date, plano) -> list[int]:
    """As rodadas ja criadas das faixas que medem no `dia`, na ordem do dia.

    Le o dia como esta no arquivo: a posicao e o titulo de cada faixa sao os
    mesmos do dia montado, e sao eles que reconhecem a rodada.
    """
    gravado = plano.dia(dia)
    if gravado is None:
        return []
    ids = []
    for bloco in plano_de_estudo.BLOCOS:
        for indice, faixa in enumerate(getattr(gravado, bloco)):
            if composicao.mede(faixa):
                rodada = composicao.rodada_da_faixa(dia, bloco, indice, faixa)
                if rodada is not None:
                    ids.append(rodada.id)
    return ids


# --- o R+7 dos diagnosticos ------------------------------------------------------

@dataclass
class ErroDaRodada:
    """Uma questao real que eu errei numa rodada que mediu."""

    questao_id: int
    materia: str
    assunto: str                  # o caminho do assunto; "" sem classificacao

    @property
    def nome_do_assunto(self) -> str:
        return self.assunto or "sem assunto classificado"


@dataclass
class ErrosDasRodadas:
    """O R+7 dos diagnosticos: os erros das rodadas do dia de origem."""

    tipo = "erros_das_rodadas"
    origem = AUTOMATICO

    dia: date                     # o dia de origem, o dos diagnosticos
    rodadas: list[int]            # as rodadas que mediram naquele dia
    erros: list[ErroDaRodada]     # todos os erros delas, na ordem delas
    escolhidos: list[ErroDaRodada]  # os que a rodada desta faixa refaz
    total: int                    # o do plano
    rodada_id: int | None = None  # a desta faixa, quando ja criada

    @property
    def por_assunto(self) -> list[tuple[str, int, int]]:
        """[(assunto, erros, refeitos nesta faixa)], o de mais erro primeiro."""
        erros = Counter(e.nome_do_assunto for e in self.erros)
        refeitos = Counter(e.nome_do_assunto for e in self.escolhidos)
        return sorted(((assunto, n, refeitos.get(assunto, 0)) for assunto, n in erros.items()),
                      key=lambda linha: (-linha[1], linha[0]))


def refaz_rodadas(faixa) -> bool:
    """A revisao NO RADAR com dia de origem refaz os erros das rodadas que
    mediram naquele dia: e o R+7 dos diagnosticos de 03/10."""
    return (faixa is not None and faixa.tipo == "revisao" and faixa.onde == "radar"
            and bool(faixa.origem) and bool(faixa.questoes))


def _erros(rodadas: list[int]) -> list[ErroDaRodada]:
    """Os erros das rodadas, com o assunto da classificacao de cada questao."""
    respostas = metricas.erros_das_rodadas(rodadas)
    if not respostas:
        return []
    with sessao() as s:
        questoes = {q.id: q for q in s.scalars(select(QuestaoDeProva).where(
            QuestaoDeProva.id.in_([r.questao_id for r in respostas])))}
        chaves = {qid: chave_de(q) for qid, q in questoes.items()}
        principais = {c.chave: c for c in s.scalars(
            select(Classificacao)
            .where(Classificacao.principal.is_(True))
            .where(Classificacao.chave.in_(list(chaves.values()))))}

    saida = []
    for resposta in respostas:
        questao = questoes.get(resposta.questao_id)
        if questao is None:
            continue
        c = principais.get(chaves[questao.id])
        partes = (arvore.partes(c.conteudo)
                  if c and c.status != "pendente" and c.conteudo else [])
        saida.append(ErroDaRodada(
            questao_id=questao.id, materia=questao.materia or "",
            assunto=arvore.SEPARADOR.join(partes[:2]) if len(partes) >= 2 else ""))
    return saida


def _escolher(erros: list[ErroDaRodada], total: int) -> list[ErroDaRodada]:
    """Ate `total` erros, divididos entre os assuntos pelo numero de erros de
    cada um - o `compilado.distribuir`, a conta de sempre: o assunto em que
    mais errei volta mais. Dentro do assunto, na ordem das rodadas."""
    if len(erros) <= total:
        return list(erros)
    quantos = compilado.distribuir(dict(Counter(e.assunto for e in erros)), total)
    escolhidos = []
    for erro in erros:
        if quantos.get(erro.assunto, 0) > 0:
            escolhidos.append(erro)
            quantos[erro.assunto] -= 1
    return escolhidos


def erros_das_rodadas(data: date, bloco: str, indice: int, faixa,
                      plano) -> ErrosDasRodadas | None:
    """O que o R+7 dos diagnosticos refaz. Criada a rodada dele, os escolhidos
    sao os gravados nela - o que eu respondi fica como foi."""
    if not refaz_rodadas(faixa):
        return None
    dia = date.fromisoformat(str(faixa.origem))
    rodadas = rodadas_do_dia(dia, plano)
    erros = _erros(rodadas)
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        criar_tabelas()
        with sessao() as s:
            gravadas = set(s.scalars(select(RespostaDeSimulado.questao_id).where(
                RespostaDeSimulado.simulado_id == existente.id)))
        escolhidos = [e for e in erros if e.questao_id in gravadas]
    else:
        escolhidos = _escolher(erros, faixa.questoes)
    return ErrosDasRodadas(dia=dia, rodadas=rodadas, erros=erros, escolhidos=escolhidos,
                           total=faixa.questoes,
                           rodada_id=existente.id if existente is not None else None)


def criar_rodada_dos_erros(data: date, bloco: str, indice: int, faixa,
                           plano) -> Simulado | None:
    """A rodada do R+7 com os erros escolhidos, ou a que ja existe.

    None sem erro gravado: sem rodada nos diagnosticos, ou sem erro nelas.
    So questao real - a rodada sai das respostas das rodadas que mediram.
    """
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return existente
    revisao = erros_das_rodadas(data, bloco, indice, faixa, plano)
    if revisao is None or not revisao.escolhidos:
        return None
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(revisao.escolhidos),
            # O relatorio e a tela da questao ja dizem "so as que eu errei".
            "erros": True,
            "rodada": "erros_das_rodadas",
            "faixa": composicao.identidade_da_faixa(data, bloco, indice, faixa),
            "origem": {"dia": revisao.dia.isoformat(), "rodadas": revisao.rodadas},
        })
        s.add(simulado)
        s.flush()
        for ordem, erro in enumerate(revisao.escolhidos, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id,
                                     questao_id=erro.questao_id, ordem=ordem))
    return simulado


# --- a comparacao do fechamento --------------------------------------------------

@dataclass
class Medida:
    """Um numero da comparacao: X de Y, e se a amostra sustenta a porcentagem."""

    respondidas: int
    acertos: int
    minimo: int

    @property
    def porcentagem(self) -> int | None:
        return round(100 * self.acertos / self.respondidas) if self.respondidas else None

    @property
    def suficiente(self) -> bool:
        return self.respondidas >= self.minimo


@dataclass
class LinhaDaComparacao:
    materia: str
    diagnostico: Medida | None    # None: a materia nao teve rodada naquele dia
    fechamento: Medida | None     # None: a rodada ainda nao tem resposta dela
    ciclo: Medida | None          # o acumulado sem consulta do ciclo


@dataclass
class Comparacao:
    """A correcao do fechamento: o acerto por materia nas rodadas do dia, nas
    do dia comparado e no acumulado do ciclo - tres numeros, nunca somados."""

    tipo = "comparacao"
    origem = AUTOMATICO

    com: date                     # o dia comparado (o dos diagnosticos)
    dia: date                     # o dia do fechamento
    linhas: list[LinhaDaComparacao]
    minimo: int                   # o da materia, do config/amostra.yml


def _medida(linhas: list, materia: str, minimo: int) -> Medida | None:
    """A linha do `metricas` desta materia, ou None quando nao ha."""
    linha = next((d for d in linhas if compilado.mesma_materia(materia, d.materia)), None)
    if linha is None or not linha.respondidas:
        return None
    return Medida(linha.respondidas, linha.acertos, minimo)


def comparacao(data: date, faixa, plano) -> Comparacao | None:
    """A comparacao da faixa com `compara_com`: as materias das rodadas que
    medem no proprio dia (o fechamento) e no dia comparado (o diagnostico)."""
    from radar.servico import materias as minhas_materias

    if not getattr(faixa, "compara_com", None):
        return None
    com = date.fromisoformat(str(faixa.compara_com))
    materias: list[str] = []
    for dia in (data, com):
        gravado = plano.dia(dia)
        for f in (gravado.faixas() if gravado else []):
            if composicao.mede(f):
                materias += [m for m in composicao.materias_da_faixa(f)
                             if not any(compilado.mesma_materia(m, j) for j in materias)]
    if not materias:
        return None

    minimo = regua.carregar().do_nivel("materia")
    diagnostico = metricas.desempenho_das_rodadas(rodadas_do_dia(com, plano))
    fechamento = metricas.desempenho_das_rodadas(rodadas_do_dia(data, plano))
    cartoes, _projecao = minhas_materias.montar(plano, data)

    linhas = []
    for materia in materias:
        cartao = next((c for c in cartoes if compilado.mesma_materia(materia, c.nome)), None)
        ciclo = None
        if cartao is not None and cartao.sem_consulta.medidas:
            ciclo = Medida(cartao.sem_consulta.medidas, cartao.sem_consulta.acertos,
                           cartao.minimo)
        linhas.append(LinhaDaComparacao(
            materia=materia,
            diagnostico=_medida(diagnostico, materia, minimo),
            fechamento=_medida(fechamento, materia, minimo),
            ciclo=ciclo))
    return Comparacao(com=com, dia=data, linhas=linhas, minimo=minimo)


# --- a tela -----------------------------------------------------------------------

def das_faixas(blocos, data: date, plano) -> dict:
    """{(bloco, indice): o que a faixa do sabado mostra} - a revisao semanal,
    o R+7 dos diagnosticos e a comparacao do fechamento. Dia sem nenhuma delas
    nao conta nada."""
    if plano is None:
        return {}
    saida = {}
    for bloco in blocos:
        for indice, faixa in enumerate(bloco.faixas):
            if faixa.tipo == "revisao_semanal":
                item = revisao_da_semana(data, plano)
            elif refaz_rodadas(faixa):
                item = erros_das_rodadas(data, bloco.chave, indice, faixa, plano)
            elif getattr(faixa, "compara_com", None):
                item = comparacao(data, faixa, plano)
            else:
                continue
            if item is not None:
                saida[(bloco.chave, indice)] = item
    return saida
