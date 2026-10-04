"""O simulado: montar a rodada, responder, e medir o acerto por materia.

Sao dois modos, e a diferenca entre eles e de ONDE a questao vem:

- o simulado comum responde "quero treinar Portugues", e sorteia por materia
  ou pelo que cai em qualquer concurso;
- o simulado do alvo responde "quero treinar para a MINHA prova", e tem ordem
  de preferencia - as provas do proprio cargo primeiro, a mesma banca nas
  mesmas materias depois.

O estado de cada rodada fica no banco, e nao na sessao do navegador: da para
fechar a pagina no meio e voltar depois, e o historico serve para medir se eu
estou melhorando.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select

from radar import alvo as alvos
from radar import macetes, regioes
from radar.db import criar_tabelas, sessao
from radar.models import (
    QuestaoDeProva,
    QuestaoGerada,
    RespostaDeSimulado,
    Simulado,
    agora,
)
from radar.origem import IA, OFICIAL, PROVA
from radar.servico.comum import cargo_parecido as _cargo_parecido
# A conta do acerto mora no `servico.metricas`, a fonte unica (Etapa 1C).
# Os nomes continuam aqui porque a fachada `servico` e a home os leem daqui.
from radar.servico.metricas import (     # noqa: F401 - reexportados
    DIAS_DA_EVOLUCAO,
    DesempenhoDaMateria,
    Evolucao,
    desempenho,
    desempenho_das_geradas,
    evolucao,
    placar,
    resumo_do_simulado,
)
from radar.servico.metricas import ultimas_respostas_reais as _ultimas_respostas_reais


# Materias que caem em QUALQUER concurso, independente do cargo. Sao as que
# valem treinar mesmo sem haver prova do cargo que eu quero no acervo.
def materias_universais() -> list[str]:
    """As materias que caem em QUALQUER concurso, do jeito que cada banca as
    escreve.

    Nao vale uma lista fixa de nomes: a FEPESE escreve "Raciocinio Logico" e
    "Nocoes de Informatica", a IESES escreve "Matematica e Raciocinio Logico" e
    "Informatica". Com a lista fixa, o simulado sem materia escolhida so trazia
    Portugues das provas da IESES. Quem decide e o catalogo de apelidos, que ja
    sabe que as duas coisas sao a mesma materia.
    """
    criar_tabelas()
    with sessao() as s:
        nomes = s.scalars(
            select(QuestaoDeProva.materia).where(QuestaoDeProva.materia.is_not(None))
            .group_by(QuestaoDeProva.materia)
        )
        return [nome for nome in nomes if macetes.chave_da_materia(nome)]

QUANTIDADE_PADRAO = 10


def materias_disponiveis() -> list[tuple[str, int]]:
    """[(materia, quantas questoes distintas)], da maior para a menor."""
    criar_tabelas()
    consulta = (
        select(QuestaoDeProva.materia, func.count(func.distinct(QuestaoDeProva.impressao)))
        .group_by(QuestaoDeProva.materia)
        .order_by(func.count(func.distinct(QuestaoDeProva.impressao)).desc())
    )
    with sessao() as s:
        return [(m or "sem materia", n) for m, n in s.execute(consulta)]


def _sortear_questoes(
    quantidade: int,
    materia: str | None = None,
    cargo: str | None = None,
    banca: str | None = None,
    universais: bool = False,
) -> list[int]:
    """Ids de questoes sorteadas, SEM repetir enunciado.

    A banca reaproveita muito: das 5.021 questoes, so 1.815 tem enunciado
    diferente, e uma delas aparece em 44 cadernos. Sortear sem cuidado daria um
    simulado com a mesma pergunta varias vezes.
    """
    consulta = select(QuestaoDeProva).where(QuestaoDeProva.resposta.is_not(None))

    if materia:
        consulta = consulta.where(QuestaoDeProva.materia == materia)
    elif universais:
        consulta = consulta.where(QuestaoDeProva.materia.in_(materias_universais()))
    if cargo:
        consulta = consulta.where(_cargo_parecido(cargo))
    if banca:
        consulta = consulta.where(QuestaoDeProva.banca.ilike(f"%{banca}%"))

    with sessao() as s:
        candidatas = list(s.scalars(consulta))

    # uma questao por enunciado
    por_enunciado: dict[str, QuestaoDeProva] = {}
    for questao in candidatas:
        por_enunciado.setdefault(questao.impressao, questao)

    import random

    escolhidas = list(por_enunciado.values())
    random.shuffle(escolhidas)
    return [q.id for q in escolhidas[:quantidade]]


def criar_simulado(
    quantidade: int = QUANTIDADE_PADRAO,
    materia: str | None = None,
    cargo: str | None = None,
    banca: str | None = None,
    universais: bool = False,
) -> Simulado | None:
    """Monta uma rodada. Devolve None se nao houver questao que sirva."""
    criar_tabelas()

    ids = _sortear_questoes(quantidade, materia, cargo, banca, universais)
    if not ids:
        return None

    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": quantidade, "materia": materia, "cargo": cargo,
            "banca": banca, "universais": universais,
        })
        s.add(simulado)
        s.flush()                      # precisa do id antes de ligar as questoes

        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=questao_id, ordem=ordem
            ))
        return simulado


# --- o simulado do alvo (etapa 9) -------------------------------------------
#
# A diferenca para o simulado comum e de ONDE vem a questao, e ela importa.
# O simulado comum responde "quero treinar Portugues"; este responde "quero
# treinar para a MINHA prova", e por isso ele tem ordem de preferencia:
#
#   1. as questoes das provas do proprio cargo - 2013 e 2019, as unicas que
#      existem. Elas sao a prova de verdade, e nenhuma outra chega perto;
#   2. quando elas acabam, as da mesma banca NAS MESMAS MATERIAS, de outros
#      concursos. E a segunda melhor coisa: a FEPESE cobra Portugues do mesmo
#      jeito em qualquer caderno que faca;
#   3. so entao repete o que eu ja respondi, avisando que esta repetindo.
#
# Fora das materias do meu edital nao entra NADA: "Conhecimentos Especificos"
# da prova de Merendeira e da mesma banca e nao me serve de nada.


@dataclass
class OrigemDasQuestoes:
    """De onde saiu cada questao da rodada. Vai para `Simulado.filtros`."""

    proprias: int = 0
    da_banca: int = 0
    repetidas: int = 0

    def como_dicionario(self) -> dict:
        return {
            "proprias": self.proprias,
            "da_banca": self.da_banca,
            "repetidas": self.repetidas,
        }


def _impressoes_ja_respondidas(s) -> set[str]:
    """O enunciado que eu ja respondi alguma vez, em qualquer simulado.

    Por IMPRESSAO e nao por id: a mesma pergunta aparece em varios cadernos, e
    reve-la com outro numero nao seria questao nova - seria a mesma questao.
    """
    linhas = s.execute(
        select(QuestaoDeProva.impressao)
        .join(RespostaDeSimulado, RespostaDeSimulado.questao_id == QuestaoDeProva.id)
        .where(RespostaDeSimulado.escolhida.is_not(None))
        # Sem isto o `questao_id` de uma rodada gerada casaria com a questao
        # real de mesmo numero, e uma pergunta que eu nunca vi sairia do
        # sorteio. As duas tabelas numeram a partir do 1.
        .where(RespostaDeSimulado.gerada.is_(False))
        .distinct()
    ).all()
    return {impressao for (impressao,) in linhas if impressao}


def _questoes_para_o_alvo(s) -> tuple[list, list]:
    """(questoes das provas do cargo, questoes da banca nas mesmas materias).

    A segunda lista sai das materias da PRIMEIRA: o que define o que me serve
    e o que caiu na minha prova, e nao o catalogo de materias da banca. E dela
    so entram as provas ACEITAS no data/acervo_complementar.json (decisao 75):
    o treino e o compilado, que mede, saem daqui, e uma prova que a Etapa 3B
    recusou pode ter o gabarito ou a materia errados.
    """
    # Alvo e complementar pela regra unica do `servico.evidencia` (Etapa 2).
    # Antes o simulado olhava so o cargo, e o Meu foco o cargo E o estado.
    from radar.servico import complementar, evidencia

    por_prova = evidencia.por_prova(s)
    aceitas = complementar.provas_aceitas()
    candidatas = list(s.scalars(
        select(QuestaoDeProva).where(QuestaoDeProva.resposta.is_not(None))
    ))

    proprias = [q for q in candidatas if por_prova.get(q.prova_url) == evidencia.ALVO]
    if not proprias:
        return [], []

    materias = {regioes.normalizar(q.materia) for q in proprias if q.materia}
    da_banca = [
        q for q in candidatas
        if por_prova.get(q.prova_url) == evidencia.COMPLEMENTAR
        and q.prova_url in aceitas
        and q.materia and regioes.normalizar(q.materia) in materias
    ]
    return proprias, da_banca


def _sortear_para_o_alvo(quantidade: int) -> tuple[list[int], OrigemDasQuestoes]:
    """Os ids da rodada, na ordem de preferencia, e de onde cada um veio."""
    import random

    with sessao() as s:
        proprias, da_banca = _questoes_para_o_alvo(s)
        respondidas = _impressoes_ja_respondidas(s)

        # Uma questao por enunciado, aqui pelo mesmo motivo de sempre: a banca
        # reaproveita muito, e um simulado com a mesma pergunta duas vezes e
        # um simulado menor do que parece.
        vistas: set[str] = set()
        origem = OrigemDasQuestoes()
        escolhidos: list[int] = []

        def separar(questoes: list) -> tuple[list, list]:
            """(as que eu nunca respondi, as que eu ja respondi)."""
            novas = [q for q in questoes if q.impressao not in respondidas]
            velhas = [q for q in questoes if q.impressao in respondidas]
            random.shuffle(novas)
            random.shuffle(velhas)
            return novas, velhas

        proprias_novas, proprias_velhas = separar(proprias)
        banca_novas, banca_velhas = separar(da_banca)

        # A ordem desta lista E a regra da etapa 9, escrita uma vez so.
        for questoes, campo in (
            (proprias_novas, "proprias"),
            (banca_novas, "da_banca"),
            (proprias_velhas, "repetidas"),
            (banca_velhas, "repetidas"),
        ):
            for questao in questoes:
                if len(escolhidos) >= quantidade:
                    break
                if questao.impressao in vistas:
                    continue
                vistas.add(questao.impressao)
                escolhidos.append(questao.id)
                setattr(origem, campo, getattr(origem, campo) + 1)

    return escolhidos, origem


def criar_simulado_do_alvo(quantidade: int = QUANTIDADE_PADRAO) -> Simulado | None:
    """Uma rodada para a minha prova. None quando nao ha questao do cargo.

    None e nao "sorteia qualquer coisa": sem prova do cargo no acervo, isto
    aqui nao teria como ser um simulado DO ALVO, e chamar de alvo o que nao e
    seria a mesma mentira que a tela de foco evita.
    """
    criar_tabelas()

    ids, origem = _sortear_para_o_alvo(quantidade)
    if not ids:
        return None

    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": quantidade,
            "alvo": (alvos.principal().get("nome") or "alvo principal"),
            **origem.como_dicionario(),
        })
        s.add(simulado)
        s.flush()

        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=questao_id, ordem=ordem
            ))
        return simulado


def contar_questoes_do_alvo() -> dict[str, int]:
    """Quantas questoes existem de cada fonte, e quantas eu ainda nao respondi.

    E o que a tela usa para dizer de onde a proxima rodada vai sair - antes de
    eu clicar, e nao depois.
    """
    criar_tabelas()
    with sessao() as s:
        proprias, da_banca = _questoes_para_o_alvo(s)
        respondidas = _impressoes_ja_respondidas(s)

    def contar(questoes: list) -> tuple[int, int]:
        impressoes = {q.impressao for q in questoes if q.impressao}
        return len(impressoes), len(impressoes - respondidas)

    total_proprias, novas_proprias = contar(proprias)
    total_banca, novas_banca = contar(da_banca)
    return {
        "proprias": total_proprias,
        "proprias_novas": novas_proprias,
        "da_banca": total_banca,
        "da_banca_novas": novas_banca,
    }


def _respostas(simulado_id: int) -> list[RespostaDeSimulado]:
    with sessao() as s:
        return list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .order_by(RespostaDeSimulado.ordem)
        ))


def _tabela_da_resposta(resposta: RespostaDeSimulado):
    """Em que tabela o `questao_id` desta linha existe.

    Uma linha so, para nao espalhar o `if resposta.gerada` por cinco funcoes.
    """
    return QuestaoGerada if resposta.gerada else QuestaoDeProva


def questao_atual(
    simulado_id: int,
) -> tuple[RespostaDeSimulado, QuestaoDeProva | QuestaoGerada] | None:
    """A proxima questao sem resposta, ou None quando acabou.

    E isso que permite fechar a pagina no meio e voltar depois: o lugar onde
    eu parei esta no banco, nao na sessao do navegador.

    A questao pode vir das duas tabelas, e a tela e a mesma. Quem diz de qual
    e a coluna `gerada` da propria linha da resposta.
    """
    criar_tabelas()
    with sessao() as s:
        resposta = s.scalar(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.escolhida.is_(None))
            .order_by(RespostaDeSimulado.ordem)
            .limit(1)
        )
        if resposta is None:
            return None
        return resposta, s.get(_tabela_da_resposta(resposta), resposta.questao_id)


def responder(simulado_id: int, questao_id: int, letra: str) -> bool | None:
    """Grava a resposta e devolve se acertou. None se a questao nao e desta
    rodada, ou se ja foi respondida - recarregar a pagina nao pode contar
    duas vezes."""
    criar_tabelas()
    letra = (letra or "").strip().lower()[:1]

    with sessao() as s:
        resposta = s.scalar(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.questao_id == questao_id)
        )
        if resposta is None or resposta.escolhida is not None:
            return None

        questao = s.get(_tabela_da_resposta(resposta), questao_id)
        if questao is None or letra not in (questao.alternativas or {}):
            return None

        resposta.escolhida = letra
        resposta.acertou = letra == questao.resposta
        resposta.respondida_em = agora()

        # acabou? marca o fim da rodada
        faltam = s.scalar(
            select(func.count()).select_from(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.escolhida.is_(None))
        )
        if not faltam:
            simulado = s.get(Simulado, simulado_id)
            if simulado:
                simulado.finalizado_em = agora()

        return resposta.acertou


def simulados_recentes(limite: int = 10) -> list[Simulado]:
    criar_tabelas()
    with sessao() as s:
        return list(s.scalars(
            select(Simulado).order_by(Simulado.criado_em.desc()).limit(limite)
        ))


def buscar_simulado(simulado_id: int) -> Simulado | None:
    criar_tabelas()
    with sessao() as s:
        return s.get(Simulado, simulado_id)


@dataclass
class ItemDeRevisao:
    enunciado: str
    escolhida: str | None
    correta: str | None
    texto_escolhido: str
    texto_correto: str
    acertou: bool
    materia: str | None = None
    #: Escrita pela IA. A revisao precisa dizer isso: rever uma questao
    #: gerada achando que e da banca e o erro que esta etapa inteira evita.
    gerada: bool = False
    #: O artigo em que a questao gerada se apoia, para eu conferir na lei.
    artigo: str | None = None
    #: O que identifica a questao fora deste banco: e por aqui que o
    #: relatorio acha a explicacao importada (pela impressao) e o macete que
    #: cita esta questao (pelo caderno e numero).
    impressao: str | None = None
    prova_url: str | None = None
    numero: int | None = None
    ano: int | None = None
    banca: str | None = None

    @property
    def origem(self) -> str:
        """A questao: tirada da prova, ou escrita pela IA (Etapa 7A)."""
        return IA if self.gerada else PROVA

    @property
    def origem_da_resposta(self) -> str:
        """A letra certa: o gabarito definitivo, ou a resposta que a IA deu."""
        return IA if self.gerada else OFICIAL


def revisao(simulado_id: int) -> list[ItemDeRevisao]:
    """O que eu marquei e qual era a correta, questao a questao.

    Errar sem ver a correta nao ensina nada; e a revisao que faz o simulado
    valer mais que um numero no fim.
    """
    criar_tabelas()
    with sessao() as s:
        respostas = list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .order_by(RespostaDeSimulado.ordem)
        ))
        # Uma busca por linha, em vez do join de antes: a rodada tem no
        # maximo 50 questoes, e elas podem estar em duas tabelas diferentes.
        linhas = [
            (resposta, s.get(_tabela_da_resposta(resposta), resposta.questao_id))
            for resposta in respostas
        ]

    itens = []
    for resposta, questao in linhas:
        if questao is None:
            continue
        alternativas = questao.alternativas or {}
        itens.append(ItemDeRevisao(
            enunciado=questao.enunciado,
            escolhida=resposta.escolhida,
            correta=questao.resposta,
            texto_escolhido=alternativas.get(resposta.escolhida, ""),
            texto_correto=alternativas.get(questao.resposta, ""),
            acertou=bool(resposta.acertou),
            materia=questao.materia,
            gerada=bool(resposta.gerada),
            artigo=getattr(questao, "artigo", None),
            impressao=questao.impressao,
            prova_url=getattr(questao, "prova_url", None),
            numero=getattr(questao, "numero", None),
            ano=getattr(questao, "ano", None),
            banca=getattr(questao, "banca", None),
        ))
    # errado primeiro: e o que eu preciso rever
    itens.sort(key=lambda i: i.acertou)
    return itens


# --- os meus erros, e a minha evolucao (home, 25/09/2026) -------------------
#
def questoes_erradas() -> list[int]:
    """As questoes reais que eu errei na ULTIMA vez que respondi.

    A ultima vez, e nao "alguma vez": questao que eu errei e depois acertei
    ja foi revisada. E anulada fica de fora - a banca desfez a pergunta, e
    revisar uma questao sem resposta certa nao ensina nada.
    """
    criar_tabelas()
    with sessao() as s:
        ultimas = _ultimas_respostas_reais(s)
        erradas = [qid for qid, r in ultimas.items() if r.acertou is False]
        if not erradas:
            return []
        validas = set(s.scalars(
            select(QuestaoDeProva.id)
            .where(QuestaoDeProva.id.in_(erradas))
            .where(QuestaoDeProva.anulada.is_not(True))
        ))
    return [qid for qid in erradas if qid in validas]


def criar_simulado_de_erros(quantidade: int = QUANTIDADE_PADRAO) -> Simulado | None:
    """Uma rodada so com o que eu errei. None quando nao ha erro para revisar."""
    import random

    ids = questoes_erradas()
    if not ids:
        return None
    random.shuffle(ids)
    ids = ids[:quantidade]

    with sessao() as s:
        simulado = Simulado(filtros={"quantidade": len(ids), "erros": True})
        s.add(simulado)
        s.flush()
        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=questao_id, ordem=ordem
            ))
        return simulado


# --- listar e descartar rodadas ---------------------------------------------
#
# Rodada de teste - chutada sem ler, so para ver se a tela funcionava - estraga
# tudo que mede: a taxa de acerto, a prioridade da home, o "Onde estudar
# primeiro" e a revisao. Descartar APAGA de verdade, simulado e respostas: dado
# de teste nao tem valor historico, e marcar como "ignorado" obrigaria cada
# conta do radar a lembrar do filtro.


@dataclass
class ResumoDaRodada:
    id: int
    criado_em: object
    questoes: int
    respondidas: int
    acertos: int
    materias: list[str]
    gerada: bool

    @property
    def origem(self) -> str:
        """De onde vieram as questoes da rodada: da prova, ou da IA."""
        return IA if self.gerada else PROVA

    @property
    def porcentagem(self) -> float | None:
        return (self.acertos / self.respondidas * 100) if self.respondidas else None


def listar_simulados() -> list[ResumoDaRodada]:
    """Todas as rodadas, da mais nova para a mais velha."""
    criar_tabelas()
    with sessao() as s:
        rodadas = list(s.scalars(select(Simulado).order_by(Simulado.criado_em.desc())))
        resumo = []
        for sim in rodadas:
            respostas = list(s.scalars(
                select(RespostaDeSimulado)
                .where(RespostaDeSimulado.simulado_id == sim.id)
            ))
            reais = [r.questao_id for r in respostas if not r.gerada]
            geradas = [r.questao_id for r in respostas if r.gerada]
            materias = set()
            if reais:
                materias |= set(s.scalars(
                    select(QuestaoDeProva.materia).where(QuestaoDeProva.id.in_(reais))
                ))
            if geradas:
                materias |= set(s.scalars(
                    select(QuestaoGerada.materia).where(QuestaoGerada.id.in_(geradas))
                ))
            respondidas, acertos = placar(respostas)
            resumo.append(ResumoDaRodada(
                id=sim.id, criado_em=sim.criado_em, questoes=len(respostas),
                respondidas=respondidas,
                acertos=acertos,
                materias=sorted(m for m in materias if m),
                gerada=bool((sim.filtros or {}).get("geradas")),
            ))
    return resumo


def _apagar(s, simulados: list) -> tuple[int, int]:
    """Apaga as rodadas e todas as linhas delas. (rodadas, respostas DADAS).

    Conta so a resposta que eu dei: a rodada abandonada tem 20 linhas e
    nenhuma resposta, e "apaguei 108 respostas" quando eu respondi 8 seria
    um numero que nao diz nada.
    """
    respondidas = 0
    for sim in simulados:
        for r in s.scalars(
            select(RespostaDeSimulado).where(RespostaDeSimulado.simulado_id == sim.id)
        ):
            respondidas += r.escolhida is not None
            s.delete(r)
        s.delete(sim)
    return len(simulados), respondidas


def descartar_simulado(simulado_id: int) -> int | None:
    """Apaga uma rodada e as respostas dela. Quantas respostas DADAS saíram;
    None quando a rodada nao existe.

    Sai do banco E do data/simulados.json - so do banco, o proximo importar
    a traria de volta.
    """
    from radar import acervo

    criar_tabelas()
    with sessao() as s:
        sim = s.get(Simulado, simulado_id)
        if sim is None:
            return None
        criado = sim.criado_em
        _, respostas = _apagar(s, [sim])
    acervo.esquecer_simulados([criado])
    return respostas


def descartar_todos() -> tuple[int, int]:
    """Apaga TODAS as rodadas e respostas. (rodadas, respostas)."""
    from radar import acervo

    criar_tabelas()
    with sessao() as s:
        simulados = list(s.scalars(select(Simulado)))
        criados = [sim.criado_em for sim in simulados]
        resultado = _apagar(s, simulados)
    acervo.esquecer_simulados(criados)
    return resultado


# Quanto tempo um simulado sem resposta tem antes de virar lixo. Um dia: o de
# hoje pode ser a rodada que eu abri e ainda vou fazer.
IDADE_PARA_LIMPAR = timedelta(days=1)


def simulados_vazios(agora_: datetime | None = None) -> list[tuple[int, datetime]]:
    """Os simulados SEM NENHUMA resposta e criados ha mais de um dia.

    Cada clique em "Treinar" cria uma rodada, e a que eu abandonei fica com
    as questoes sorteadas e nenhuma resposta. Uma resposta que seja e
    historico de treino: nunca entra aqui. (id, criado_em), do mais antigo.
    """
    limite = (agora_ or agora()) - IDADE_PARA_LIMPAR
    criar_tabelas()
    with sessao() as s:
        respondidos = select(RespostaDeSimulado.simulado_id).where(
            RespostaDeSimulado.escolhida.is_not(None))
        achados = s.execute(
            select(Simulado.id, Simulado.criado_em)
            .where(Simulado.criado_em < limite)
            .where(Simulado.id.not_in(respondidos))
            .order_by(Simulado.criado_em)
        )
        return [(ident, criado) for ident, criado in achados]


def descartar_vazios(agora_: datetime | None = None) -> list[tuple[int, datetime]]:
    """Apaga os simulados_vazios do banco E do data/simulados.json.

    O arquivo pelo mesmo caminho do descartar: so do banco, o proximo
    importar os traria de volta. Devolve os que sairam.
    """
    from radar import acervo

    vazios = simulados_vazios(agora_)
    if not vazios:
        return []
    with sessao() as s:
        simulados = [s.get(Simulado, ident) for ident, _ in vazios]
        # Confere de novo, dentro da transacao: uma resposta dada entre a
        # listagem e aqui tira o simulado da limpeza.
        simulados = [sim for sim in simulados if sim is not None and not s.scalar(
            select(func.count()).select_from(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == sim.id)
            .where(RespostaDeSimulado.escolhida.is_not(None)))]
        sairam = [(sim.id, sim.criado_em) for sim in simulados]
        _apagar(s, simulados)
    acervo.esquecer_simulados([criado for _, criado in sairam])
    return sairam
