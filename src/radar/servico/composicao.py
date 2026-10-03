"""A composicao das rodadas que MEDEM: o diagnostico e o simulado do sabado.

Uma fonte so para a pergunta "de quais assuntos sao as questoes desta faixa?"
(decisao 67). E a mesma regra no diagnostico de 03/10 e no simulado de 07/11 -
e por isso o acerto por materia dos dois pode ser comparado.

A regra, na ordem:

  1. o total e o do plano. Com mais de uma materia, ele se divide pelo quadro
     do edital, com o `compilado.distribuir` - o mesmo do simulado compilado;
  2. dentro da materia, cada assunto do edital:
     - com amostra no ALVO (config/amostra.yml: 3 questoes em 2 provas) entra
       pela incidencia: fatia do alvo + peso do complementar x fatia do
       complementar (config/prioridade.yml, a mesma conta da prioridade);
     - sem amostra, divide o resto em partes iguais, e a tela diz a frase
       padrao: o edital nao da peso entre os assuntos de uma materia.
     A parte da materia que vai para os assuntos com amostra e a fatia das
     questoes do alvo que caem neles;
  3. so questao REAL da FEPESE classificada no assunto: do alvo primeiro,
     depois do complementar ACEITO; uma por enunciado, sem anulada, com
     gabarito. Questao gerada por IA nunca entra aqui: ela treina, nao mede;
  4. assunto sem questao bastante: o que falta vai para os outros assuntos da
     materia, pelo mesmo peso. Se a materia inteira nao tiver, falta mesmo, e
     a tela diz quanto - completar com outra materia desfiguraria o peso.

A composicao e deterministica: os mesmos dados dao os mesmos numeros e as
mesmas questoes (a semente e a faixa), e a rodada guarda a composicao usada em
`Simulado.filtros["composicao"]`.
"""
import random
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select

from radar import conteudos as arvore
from radar import incidencia
from radar import prioridade as regra_da_prioridade
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.origem import ACERVO, AUTOMATICO, OFICIAL
from radar.servico import compilado
from radar.servico import complementar as acervo_complementar
from radar.servico import conteudos as servico_conteudos
from radar.servico import evidencia
from radar.servico import incidencia as servico_incidencia
from radar.servico.classificacoes import chave_de

#: Os dois grupos de assunto dentro de uma materia.
COM_AMOSTRA, SEM_AMOSTRA = "com_amostra", "sem_amostra"

#: Quem fez a regra. Vai na rodada, para eu saber depois com que regra ela foi
#: montada - se a regra mudar, a rodada antiga continua dizendo a sua.
REGRA = "decisão 67: incidência do alvo onde há amostra, edital onde não há"

#: As faixas que medem, e por isso saem por esta regra: o diagnostico e o
#: simulado feitos NO RADAR. O simulado do Qconcursos fica de fora (ele nao
#: cria rodada aqui), e a revisao que refaz erros tambem (ela nao compoe nada).
TIPOS_QUE_MEDEM = ("diagnostico", "simulado")


# --- o que a composicao diz ------------------------------------------------------

@dataclass
class AssuntoNaComposicao:
    """Um assunto do edital dentro da composicao de uma materia."""

    #: A posicao do assunto no edital. E ela que desempata dois assuntos de
    #: mesmo peso - e nao a ordem alfabetica, que nao quer dizer nada aqui.
    ordem: int
    caminho: str
    nome: str
    grupo: str                    # COM_AMOSTRA ou SEM_AMOSTRA
    #: O peso usado para dividir. Com amostra: fatia do alvo + peso do
    #: complementar x fatia do complementar. Sem amostra: 1, igual para todos.
    peso: float
    alvo: str                     # a amostra do alvo: "9 questões · 2 provas"
    complementar: str | None      # a do complementar aceito, separada
    estoque: int                  # questoes reais classificadas ali
    pedidas: int = 0
    #: {subassunto: quantas}, das questoes que a rodada escolhe. "" e a
    #: questao classificada so no assunto, sem subassunto.
    subassuntos: dict = field(default_factory=dict)
    #: So no simulado do Qconcursos: o filtro do tema la (o da faixa do plano)
    #: e o dia em que o tema foi estudado.
    filtro: str | None = None
    estudado_em: date | None = None


@dataclass
class MateriaNaComposicao:
    materia: str
    total: int
    alvo: str                     # a amostra da materia no alvo
    assuntos: list[AssuntoNaComposicao] = field(default_factory=list)
    faltaram: int = 0

    @property
    def com_amostra(self) -> list[AssuntoNaComposicao]:
        return [a for a in self.assuntos if a.grupo == COM_AMOSTRA]

    @property
    def sem_amostra(self) -> list[AssuntoNaComposicao]:
        return [a for a in self.assuntos if a.grupo == SEM_AMOSTRA]

    @property
    def pedidas(self) -> int:
        return sum(a.pedidas for a in self.assuntos)


@dataclass
class Composicao:
    materias: list[MateriaNaComposicao]
    total: int
    peso_do_complementar: float
    regra: str = REGRA
    #: So no simulado do Qconcursos: as materias da faixa sem tema estudado
    #: antes do dia. Ficam fora da divisao - questao do que eu nao estudei
    #: nao mede o que eu estudei.
    fora: list[str] = field(default_factory=list)
    #: O peso entre as materias e oficial (o quadro do edital); a amostra e do
    #: acervo; a divisao e conta do sistema.
    origens = {"pesos": OFICIAL, "amostra": ACERVO, "conta": AUTOMATICO}

    @property
    def faltaram(self) -> int:
        return sum(m.faltaram for m in self.materias)

    @property
    def pedidas(self) -> int:
        return sum(m.pedidas for m in self.materias)

    def como_dicionario(self) -> dict:
        """O que a rodada grava: a regra e, por assunto, quanto e por que."""
        return {
            "regra": self.regra,
            "total": self.total,
            "peso_do_complementar": self.peso_do_complementar,
            "materias": [{
                "materia": m.materia,
                "total": m.total,
                "alvo": m.alvo,
                "faltaram": m.faltaram,
                "assuntos": [{
                    "caminho": a.caminho, "grupo": a.grupo,
                    "peso": round(a.peso, 4), "alvo": a.alvo,
                    "complementar": a.complementar, "estoque": a.estoque,
                    "pedidas": a.pedidas, "subassuntos": a.subassuntos,
                } for a in m.assuntos],
            } for m in self.materias],
        }


@dataclass
class Candidata:
    """Uma questao real que pode entrar na rodada."""

    id: int
    chave: str
    impressao: str
    assunto: str                  # o caminho do assunto
    conteudo: str                 # o caminho da classificacao
    evidencia: str                # alvo | complementar

    @property
    def subassunto(self) -> str:
        """O subassunto da classificacao, ou "" quando ela para no assunto."""
        partes = arvore.partes(self.conteudo)
        return partes[2] if len(partes) > 2 else ""


# --- a conta pura ----------------------------------------------------------------

def _distribuir(membros: list[AssuntoNaComposicao], total: int) -> dict[int, int]:
    """{ordem do assunto: quantas}, pelo `compilado.distribuir` - a mesma conta
    do simulado compilado. A chave e a ordem no edital, escrita com zeros a
    esquerda: e ela que o `distribuir` usa no ultimo desempate."""
    pedidas = compilado.distribuir({f"{a.ordem:04d}": a.peso for a in membros}, total)
    return {int(chave): n for chave, n in pedidas.items()}


def _dar(excesso: int, membros: list[AssuntoNaComposicao]) -> int:
    """Distribui `excesso` entre os assuntos com folga no estoque, pelo peso.
    Devolve o que nao coube."""
    while excesso > 0:
        com_folga = [a for a in membros if a.estoque > a.pedidas]
        if not com_folga:
            break
        extra = _distribuir(com_folga, excesso)
        dado = 0
        for a in com_folga:
            cabe = min(extra.get(a.ordem, 0), a.estoque - a.pedidas)
            a.pedidas += cabe
            dado += cabe
        if not dado:
            break
        excesso -= dado
    return excesso


def dividir(materia: str, total: int, assuntos: list[AssuntoNaComposicao],
            alvo_com_amostra: int, alvo_sem_amostra: int) -> int:
    """Preenche `pedidas` de cada assunto e devolve quantas faltaram.

    `alvo_com_amostra` e `alvo_sem_amostra` sao as questoes do alvo que caem
    em cada grupo: e a fatia delas que divide o total entre os dois.
    """
    com = [a for a in assuntos if a.grupo == COM_AMOSTRA]
    sem = [a for a in assuntos if a.grupo == SEM_AMOSTRA]
    if com and sem:
        partes = compilado.distribuir(
            {COM_AMOSTRA: alvo_com_amostra, SEM_AMOSTRA: alvo_sem_amostra}, total)
        # Sem questao do alvo fora dos assuntos com amostra, o resto vai todo
        # para eles; e o contrario tambem.
        if not partes:
            partes = {COM_AMOSTRA: total}
    elif com:
        partes = {COM_AMOSTRA: total}
    else:
        partes = {SEM_AMOSTRA: total}

    for grupo, membros in ((COM_AMOSTRA, com), (SEM_AMOSTRA, sem)):
        if membros and partes.get(grupo):
            pedidas = _distribuir(membros, partes[grupo])
            for a in membros:
                a.pedidas = pedidas.get(a.ordem, 0)

    # O que o estoque nao cobre vai primeiro para o mesmo grupo, depois para o
    # outro - e so entao falta.
    faltaram = 0
    for grupo, membros, outros in ((COM_AMOSTRA, com, sem), (SEM_AMOSTRA, sem, com)):
        excesso = 0
        for a in membros:
            if a.pedidas > a.estoque:
                excesso += a.pedidas - a.estoque
                a.pedidas = a.estoque
        sobra = _dar(excesso, membros)
        faltaram += _dar(sobra, outros)
    return faltaram


# --- o que vem do banco ----------------------------------------------------------

def _estoque(materias: list[str] | None = None) -> dict[str, list[Candidata]]:
    """{caminho do assunto: [questoes reais classificadas ali]}, alvo primeiro.

    Sem `materias`, de todas: a tela pergunta uma vez e usa em cada faixa.

    So a FEPESE que mede: o alvo e o complementar ACEITO no
    data/acervo_complementar.json (regra do CLAUDE.md: prova complementar so
    entra em estatistica se estiver aceita). Sem anulada, com gabarito, e a
    mesma questao (a chave) uma vez so.
    """
    aceitas = acervo_complementar.provas_aceitas()
    criar_tabelas()
    with sessao() as s:
        principais = {c.chave: c for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True)))}
        questoes = list(s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.resposta.is_not(None))
            .where(QuestaoDeProva.anulada.is_not(True))
            .where(QuestaoDeProva.evidencia.in_((evidencia.ALVO, evidencia.COMPLEMENTAR)))
            .order_by(QuestaoDeProva.id)))

    estoque: dict[str, dict[str, Candidata]] = {}
    for q in questoes:
        if q.evidencia == evidencia.COMPLEMENTAR and q.prova_url not in aceitas:
            continue
        chave = chave_de(q)
        c = principais.get(chave)
        if c is None or c.status == "pendente" or not c.conteudo:
            continue
        partes = arvore.partes(c.conteudo)
        if len(partes) < 2 or (materias is not None and not any(
                compilado.mesma_materia(m, partes[0]) for m in materias)):
            continue
        assunto = arvore.SEPARADOR.join(partes[:2])
        do_assunto = estoque.setdefault(assunto, {})
        atual = do_assunto.get(chave)
        # A mesma questao no alvo e no complementar vale como do alvo.
        if atual is None or (atual.evidencia != evidencia.ALVO
                             and q.evidencia == evidencia.ALVO):
            do_assunto[chave] = Candidata(
                id=q.id, chave=chave, impressao=q.impressao or chave,
                assunto=assunto, conteudo=c.conteudo, evidencia=q.evidencia)
    return {assunto: sorted(por_chave.values(), key=lambda c: c.id)
            for assunto, por_chave in estoque.items()}


def _pesos_do_edital(materias: list[str]) -> dict[str, int]:
    pesos, _edital, _arquivo = compilado._pesos(materias)
    return pesos


@dataclass
class Contexto:
    """O que toda composicao precisa e nao muda de uma faixa para outra:
    contado uma vez por tela, e nao uma vez por faixa."""

    mapas: list
    complementar: dict
    estoque: dict[str, list[Candidata]]
    respondidas: set[str]
    #: O que a composicao por tema (o Qconcursos) conta de novo para cada tema.
    nos: list = field(default_factory=list)
    ocorrencias: list = field(default_factory=list)
    complementares: list = field(default_factory=list)

    @classmethod
    def ler(cls, com_estoque: bool = True) -> "Contexto":
        """`com_estoque=False` quando so o simulado do Qconcursos vai compor:
        ele nao escolhe questao, e o estoque e a parte mais cara da leitura."""
        nos = servico_conteudos.nos()
        alvo = servico_incidencia.ocorrencias()
        complementares = servico_incidencia.ocorrencias_complementares()
        return cls(
            mapas=incidencia.montar(nos, alvo),
            complementar=incidencia.complementar_por_no(nos, complementares),
            estoque=_estoque() if com_estoque else {},
            respondidas=_respondidas() if com_estoque else set(),
            nos=nos, ocorrencias=alvo, complementares=complementares)


def compor(materias: list[str], total: int, *, pesos: dict[str, int] | None = None,
           contexto: "Contexto | None" = None) -> Composicao:
    """A composicao de uma rodada de `total` questoes nestas materias.

    `pesos` e o quadro do edital ({materia: questoes}); sem ele, e lido do
    edital como no simulado compilado. Uma materia so nao precisa dele.
    """
    regra = regra_da_prioridade.carregar()
    minimos = incidencia.carregar_minimos()
    contexto = contexto or Contexto.ler()
    if len(materias) == 1:
        por_materia = {materias[0]: total}
    else:
        pesos = pesos if pesos is not None else _pesos_do_edital(materias)
        do_edital = {m: p for m, p in pesos.items()
                     if any(compilado.mesma_materia(m, escolhida) for escolhida in materias)}
        por_materia = compilado.distribuir(do_edital, total)

    estoque, mapas, complementar = contexto.estoque, contexto.mapas, contexto.complementar

    saida = []
    for materia, n in por_materia.items():
        mapa = next((m for m in mapas if compilado.mesma_materia(m.materia, materia)), None)
        if mapa is None:
            saida.append(MateriaNaComposicao(materia=materia, total=n,
                                             alvo=incidencia.amostra(0, 0), faltaram=n))
            continue
        total_alvo = len(mapa.topo.questoes)
        linha_c = complementar.get(mapa.materia)
        classificadas_c = linha_c.classificadas if linha_c else 0

        assuntos, alvo_com, alvo_sem = [], 0, 0
        for ordem, linha in enumerate(mapa.linhas):
            if linha.nivel != "assunto" or linha.fora_do_edital:
                continue
            n_alvo, n_provas = len(linha.questoes), len(linha.provas)
            tem_amostra = n_alvo >= minimos.questoes and n_provas >= minimos.provas
            lc = complementar.get(linha.caminho)
            if tem_amostra:
                fatia_alvo = n_alvo / total_alvo if total_alvo else 0.0
                fatia_c = (lc.classificadas / classificadas_c
                           if lc and classificadas_c else 0.0)
                peso = fatia_alvo + regra.peso_do_complementar * fatia_c
                alvo_com += n_alvo
            else:
                peso = 1.0
                alvo_sem += n_alvo
            assuntos.append(AssuntoNaComposicao(
                ordem=ordem, caminho=linha.caminho, nome=linha.nome,
                grupo=COM_AMOSTRA if tem_amostra else SEM_AMOSTRA, peso=peso,
                alvo=linha.amostra,
                complementar=lc.amostra if lc and lc.classificadas else None,
                estoque=len(estoque.get(linha.caminho, []))))

        faltaram = dividir(materia, n, assuntos, alvo_com, alvo_sem)
        # Na tela: os com amostra primeiro, do maior para o menor; depois os
        # do edital, na ordem do edital.
        com = sorted((a for a in assuntos if a.grupo == COM_AMOSTRA),
                     key=lambda a: (-a.pedidas, a.nome))
        sem = [a for a in assuntos if a.grupo == SEM_AMOSTRA]
        saida.append(MateriaNaComposicao(
            materia=mapa.materia, total=n, alvo=mapa.topo.amostra,
            assuntos=com + sem, faltaram=faltaram))
    return Composicao(materias=saida, total=total,
                      peso_do_complementar=regra.peso_do_complementar)


# --- as questoes da rodada --------------------------------------------------------

def _respondidas() -> set[str]:
    from radar.servico.simulado import _impressoes_ja_respondidas

    criar_tabelas()
    with sessao() as s:
        return _impressoes_ja_respondidas(s)


def escolher(composicao: Composicao, estoque: dict[str, list[Candidata]],
             semente: str, respondidas: set[str] | None = None) -> list[Candidata]:
    """As questoes da rodada, na ordem do edital e assunto por assunto.

    Em cada assunto: do alvo antes do complementar, e a que eu nunca respondi
    antes da que ja respondi; embaralhado dentro de cada grupo pela semente,
    para a mesma faixa dar sempre as mesmas questoes. Um enunciado so uma vez
    na rodada - a regra do simulado do alvo.

    Preenche o `subassuntos` de cada assunto com o que foi escolhido.
    """
    respondidas = respondidas if respondidas is not None else set()
    sorteio = random.Random(semente)
    escolhidas: list[Candidata] = []
    usadas_chave: set[str] = set()
    usadas_enunciado: set[str] = set()
    for materia in composicao.materias:
        for assunto in materia.assuntos:
            candidatas = estoque.get(assunto.caminho, [])
            grupos = []
            for origem_da_questao in (evidencia.ALVO, evidencia.COMPLEMENTAR):
                da_origem = [c for c in candidatas if c.evidencia == origem_da_questao]
                novas = [c for c in da_origem if c.impressao not in respondidas]
                velhas = [c for c in da_origem if c.impressao in respondidas]
                sorteio.shuffle(novas)
                sorteio.shuffle(velhas)
                grupos.append((novas, velhas))
            ordem = grupos[0][0] + grupos[1][0] + grupos[0][1] + grupos[1][1]

            do_assunto: list[Candidata] = []
            for c in ordem:
                if len(do_assunto) >= assunto.pedidas:
                    break
                if c.chave in usadas_chave or c.impressao in usadas_enunciado:
                    continue
                usadas_chave.add(c.chave)
                usadas_enunciado.add(c.impressao)
                do_assunto.append(c)
            assunto.subassuntos = dict(Counter(c.subassunto for c in do_assunto))
            escolhidas.extend(do_assunto)
    return escolhidas


# --- o simulado do Qconcursos (subetapa 2B, decisao 69) ---------------------------
#
# O simulado da semana fica no Qconcursos: o acervo do radar nao tem questao
# bastante (a LEP tem 8 no acervo inteiro, e o de 31/10 pede 12). Ele nao cria
# rodada aqui, mas a composicao e a mesma regra - com uma troca so: dentro da
# materia, a unidade e o TEMA que eu ja estudei (o do cronograma, com os nos da
# ficha), e nao o assunto do edital. E o tema que tem o filtro do Qconcursos.

#: A unidade da composicao no Qconcursos nao tem estoque que acabe.
SEM_LIMITE = 10 ** 6

REGRA_DO_QCONCURSOS = "decisão 69: a regra da 67, entre os temas estudados antes do dia"


def no_qconcursos(faixa) -> bool:
    """O simulado da semana, no Qconcursos, com as materias escritas no plano."""
    return (faixa is not None and faixa.tipo == "simulado"
            and faixa.onde == "qconcursos" and bool(faixa.questoes)
            and bool(getattr(faixa, "materias_da_rodada", ())))


def _filtro_do_tema(tema) -> str | None:
    """O filtro do Qconcursos do tema: o da primeira faixa dele que tem um."""
    return next((f.faixa.filtro for f in tema.faixas if f.faixa.filtro), None)


def _estudados(temas, materia: str, data: date) -> list[tuple]:
    """[(tema, faixa de estudo)] da materia estudados antes de `data`, o mais
    recente primeiro."""
    estudados = [(tema, tema.estudo()) for tema in temas
                 if compilado.mesma_materia(materia, tema.materia)]
    estudados = [(tema, estudo) for tema, estudo in estudados
                 if estudo is not None and estudo.data < data]
    estudados.sort(key=lambda par: (par[1].data, par[0].tema), reverse=True)
    return estudados


def compor_por_tema(data: date, materias: list[str], total: int, plano, *,
                    pesos: dict[str, int] | None = None,
                    contexto: "Contexto | None" = None) -> Composicao:
    """A composicao do simulado do Qconcursos de `data`.

    As materias se dividem pelo quadro do edital, e cada materia pelos temas
    estudados ANTES de `data` (a faixa de estudo do tema veio antes): o tema
    com amostra nas provas do cargo, pela incidencia dos nos da ficha; o resto,
    por igual, com a frase padrao. No empate, o tema mais recente primeiro: e o
    simulado DA SEMANA, e o tema antigo volta no R+30 e no fechamento. Materia
    sem tema estudado antes do dia fica fora da divisao.

    A unica diferenca de conta para a regra da 67 e a parte dos temas sem
    amostra: ela e o RESTO da incidencia da materia (as questoes do alvo fora
    dos temas com amostra), e nao a soma do que se contou neles. Tema sem
    ficha ou sem no nao tem incidencia contada - a tela diz isso, e nao "nao
    apareceu" -, e contar zero para ele podia zerar o grupo inteiro.
    """
    from radar import fichas
    from radar.servico import fichas as servico_fichas

    regra = regra_da_prioridade.carregar()
    minimos = incidencia.carregar_minimos()
    temas = fichas.temas_do_plano(plano)
    com_tema = [m for m in materias if _estudados(temas, m, data)]
    fora = [m for m in materias if m not in com_tema]
    if len(com_tema) == 1:
        por_materia = {com_tema[0]: total}
    elif com_tema:
        pesos = pesos if pesos is not None else _pesos_do_edital(com_tema)
        do_edital = {m: p for m, p in pesos.items()
                     if any(compilado.mesma_materia(m, escolhida) for escolhida in com_tema)}
        por_materia = compilado.distribuir(do_edital, total)
    else:
        por_materia = {}

    escritas = servico_fichas.carregar()
    contexto = contexto or Contexto.ler(com_estoque=False)
    ocorrencias, complementares = contexto.ocorrencias, contexto.complementares

    saida = []
    for materia, n in por_materia.items():
        mapa = next((m for m in contexto.mapas
                     if compilado.mesma_materia(m.materia, materia)), None)
        nome_na_arvore = mapa.materia if mapa else materia
        total_alvo = len(mapa.topo.questoes) if mapa else 0
        linha_c = contexto.complementar.get(nome_na_arvore)
        classificadas_c = linha_c.classificadas if linha_c else 0

        assuntos, alvo_com = [], 0
        for ordem, (tema, estudo) in enumerate(_estudados(temas, materia, data)):
            escrita = fichas.da_faixa(estudo.faixa, escritas)
            nos = escrita.nos if escrita else []
            if nos:
                dentro = fichas.dentro_de(nos)
                linha = incidencia.linha_do_escopo(f"tema:{tema.tema}", tema.tema, dentro,
                                                   nome_na_arvore, ocorrencias)
                lc = incidencia.complementar_do_escopo(f"tema:{tema.tema}", dentro,
                                                       complementares)
                n_alvo, n_provas, amostra = len(linha.questoes), len(linha.provas), linha.amostra
            else:
                lc, n_alvo, n_provas = None, 0, 0
                amostra = "o tema não tem nó na árvore: o acervo não foi contado"
            tem_amostra = n_alvo >= minimos.questoes and n_provas >= minimos.provas
            if tem_amostra:
                fatia_alvo = n_alvo / total_alvo if total_alvo else 0.0
                fatia_c = (lc.classificadas / classificadas_c
                           if lc and classificadas_c else 0.0)
                peso = fatia_alvo + regra.peso_do_complementar * fatia_c
                alvo_com += n_alvo
            else:
                peso = 1.0
            assuntos.append(AssuntoNaComposicao(
                ordem=ordem, caminho=f"tema:{tema.tema}", nome=tema.tema,
                grupo=COM_AMOSTRA if tem_amostra else SEM_AMOSTRA, peso=peso,
                alvo=amostra,
                complementar=lc.amostra if lc and lc.classificadas else None,
                estoque=SEM_LIMITE, filtro=_filtro_do_tema(tema),
                estudado_em=estudo.data))

        dividir(materia, n, assuntos, alvo_com, max(total_alvo - alvo_com, 0))
        com = sorted((a for a in assuntos if a.grupo == COM_AMOSTRA),
                     key=lambda a: (-a.pedidas, a.ordem))
        sem = [a for a in assuntos if a.grupo == SEM_AMOSTRA]
        saida.append(MateriaNaComposicao(
            materia=nome_na_arvore, total=n,
            alvo=mapa.topo.amostra if mapa else incidencia.amostra(0, 0),
            assuntos=com + sem))
    return Composicao(materias=saida, total=total,
                      peso_do_complementar=regra.peso_do_complementar,
                      regra=REGRA_DO_QCONCURSOS, fora=fora)


@dataclass
class FaixaDoQconcursos:
    """O que a tela Hoje mostra no simulado do Qconcursos: so a composicao."""

    composicao: Composicao
    no_qconcursos: bool = True


# --- a faixa do cronograma --------------------------------------------------------

def mede(faixa) -> bool:
    """A faixa sai por esta regra? So diagnostico e simulado feitos no radar."""
    return (faixa is not None and faixa.tipo in TIPOS_QUE_MEDEM
            and faixa.onde == "radar" and bool(faixa.questoes)
            and bool(materias_da_faixa(faixa)))


def materias_da_faixa(faixa) -> list[str]:
    """As materias da rodada: a lista da faixa, ou a materia dela."""
    if getattr(faixa, "materias_da_rodada", None):
        return list(faixa.materias_da_rodada)
    return [faixa.materia] if faixa.materia else []


def _semente(data: date, bloco: str, indice: int) -> str:
    return f"{data.isoformat()}|{bloco}|{indice}"


def identidade_da_faixa(data: date, bloco: str, indice: int, faixa) -> dict:
    """O que reconhece a rodada de uma faixa: o dia, o bloco, a posicao e o
    titulo - os mesmos que reconhecem os checks da tela."""
    return {"data": data.isoformat(), "bloco": bloco, "indice": indice,
            "titulo": faixa.titulo}


def rodada_da_faixa(data: date, bloco: str, indice: int, faixa) -> Simulado | None:
    """A rodada ja criada para esta faixa, se houver. Criada uma vez, ela nao
    e recriada: o que eu respondi fica como foi gravado."""
    procurada = identidade_da_faixa(data, bloco, indice, faixa)
    criar_tabelas()
    with sessao() as s:
        for simulado in s.scalars(select(Simulado).order_by(Simulado.id)):
            if (simulado.filtros or {}).get("faixa") == procurada:
                return simulado
    return None


@dataclass
class FaixaQueMede:
    """O que a tela Hoje mostra numa faixa que mede."""

    composicao: Composicao
    rodada_id: int | None = None


def planejar(data: date, bloco: str, indice: int, faixa,
             contexto: "Contexto | None" = None) -> FaixaQueMede:
    """A composicao da faixa e as questoes que ela vai ter. NAO cria nada.

    Com a rodada ja criada, mostra a composicao GRAVADA nela - a de hoje pode
    ter mudado com uma classificacao nova, e a rodada continua sendo a que foi.
    """
    existente = rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return FaixaQueMede(_da_rodada(existente), rodada_id=existente.id)
    contexto = contexto or Contexto.ler()
    composicao = compor(materias_da_faixa(faixa), faixa.questoes, contexto=contexto)
    escolher(composicao, contexto.estoque, _semente(data, bloco, indice),
             contexto.respondidas)
    return FaixaQueMede(composicao)


def _da_rodada(simulado: Simulado) -> Composicao:
    """A composicao gravada numa rodada, de volta aos objetos da tela."""
    gravada = (simulado.filtros or {}).get("composicao") or {}
    materias = []
    for m in gravada.get("materias") or []:
        assuntos = [AssuntoNaComposicao(
            ordem=posicao, caminho=a["caminho"], nome=arvore.partes(a["caminho"])[-1],
            grupo=a["grupo"], peso=a["peso"], alvo=a["alvo"],
            complementar=a.get("complementar"), estoque=a["estoque"],
            pedidas=a["pedidas"], subassuntos=a.get("subassuntos") or {})
            for posicao, a in enumerate(m.get("assuntos") or [])]
        materias.append(MateriaNaComposicao(
            materia=m["materia"], total=m["total"], alvo=m["alvo"],
            assuntos=assuntos, faltaram=m.get("faltaram", 0)))
    return Composicao(materias=materias, total=gravada.get("total", 0),
                      peso_do_complementar=gravada.get("peso_do_complementar", 0.0),
                      regra=gravada.get("regra", REGRA))


def criar_rodada(data: date, bloco: str, indice: int, faixa) -> Simulado | None:
    """Cria a rodada da faixa com a composicao, ou devolve a que ja existe.

    None quando nao ha questao nenhuma para a composicao.
    """
    if not mede(faixa):
        return None
    existente = rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return existente

    contexto = Contexto.ler()
    composicao = compor(materias_da_faixa(faixa), faixa.questoes, contexto=contexto)
    escolhidas = escolher(composicao, contexto.estoque, _semente(data, bloco, indice),
                          contexto.respondidas)
    if not escolhidas:
        return None

    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(escolhidas),
            "rodada": "composta",
            "faixa": identidade_da_faixa(data, bloco, indice, faixa),
            "composicao": composicao.como_dicionario(),
            # De onde veio cada questao, como o simulado do alvo grava.
            "proprias": sum(1 for c in escolhidas if c.evidencia == evidencia.ALVO),
            "da_banca": sum(1 for c in escolhidas if c.evidencia == evidencia.COMPLEMENTAR),
        })
        s.add(simulado)
        s.flush()
        for ordem, candidata in enumerate(escolhidas, start=1):
            # So questao real: `gerada` fica no padrao, falso. A rodada que
            # mede nunca alcanca a tabela das questoes geradas.
            s.add(RespostaDeSimulado(simulado_id=simulado.id,
                                     questao_id=candidata.id, ordem=ordem))
    return simulado


def criar_rodada_do_dia(data: date, bloco: str, indice: int) -> Simulado | None:
    """A rodada da faixa `indice` do `bloco` no dia `data`, como a tela mostra.

    Le o dia pela mesma montagem da tela Hoje, para a faixa ser a que eu vi.
    """
    from radar.servico import cronograma as servico_cronograma
    from radar.servico import sabado

    tela = servico_cronograma.tela_do_dia(data)
    for bloco_na_tela in tela.blocos:
        if bloco_na_tela.chave == bloco and 0 <= indice < len(bloco_na_tela.faixas):
            faixa = bloco_na_tela.faixas[indice]
            # O R+7 dos diagnosticos refaz os erros das rodadas do dia de
            # origem: a rodada dele sai do servico do sabado.
            if sabado.refaz_rodadas(faixa):
                return sabado.criar_rodada_dos_erros(data, bloco, indice, faixa, tela.plano)
            return criar_rodada(data, bloco, indice, faixa)
    return None


def das_faixas(blocos, data: date, plano=None) -> dict:
    """{(bloco, indice): FaixaQueMede ou FaixaDoQconcursos} das faixas do dia
    que medem: no radar, a rodada; no Qconcursos, so a composicao.

    Dia sem faixa que mede nao conta nada: a tela Hoje continua rapida."""
    que_medem = [(bloco.chave, indice, faixa) for bloco in blocos
                 for indice, faixa in enumerate(bloco.faixas) if mede(faixa)]
    no_site = [(bloco.chave, indice, faixa) for bloco in blocos
               for indice, faixa in enumerate(bloco.faixas) if no_qconcursos(faixa)]
    if plano is None:
        no_site = []
    if not que_medem and not no_site:
        return {}
    # Uma leitura so para as duas: no sabado de 03/10 elas estao no mesmo dia.
    contexto = Contexto.ler(com_estoque=bool(que_medem))
    saida: dict = {}
    saida.update({(bloco, indice): planejar(data, bloco, indice, faixa, contexto)
                  for bloco, indice, faixa in que_medem})
    saida.update({(bloco, indice): FaixaDoQconcursos(compor_por_tema(
        data, list(faixa.materias_da_rodada), faixa.questoes, plano, contexto=contexto))
        for bloco, indice, faixa in no_site})
    return saida
