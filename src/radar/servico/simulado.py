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

from sqlalchemy import case, func, select

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
from radar.servico.comum import cargo_parecido as _cargo_parecido


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
    e o que caiu na minha prova, e nao o catalogo de materias da banca.
    """
    candidatas = list(s.scalars(
        select(QuestaoDeProva).where(QuestaoDeProva.resposta.is_not(None))
    ))

    proprias = [
        q for q in candidatas if alvos.nomeia_cargo_do_principal(q.cargo or "")
    ]
    if not proprias:
        return [], []

    materias = {regioes.normalizar(q.materia) for q in proprias if q.materia}
    bancas = [regioes.normalizar(b) for b in alvos.bancas_do_principal()]
    proprias_ids = {q.id for q in proprias}

    da_banca = [
        q for q in candidatas
        if q.id not in proprias_ids
        and q.materia and regioes.normalizar(q.materia) in materias
        and any(banca in regioes.normalizar(q.banca or "") for banca in bancas)
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


@dataclass
class DesempenhoDaMateria:
    materia: str
    respondidas: int = 0
    acertos: int = 0

    @property
    def porcentagem(self) -> float:
        return (self.acertos / self.respondidas * 100) if self.respondidas else 0.0


def desempenho(simulado_id: int | None = None) -> list[DesempenhoDaMateria]:
    """Acerto por materia nas questoes REAIS. Sem id, soma todos os simulados.

    O acumulado e o que responde a pergunta que importa: em que materia eu
    estou pior e preciso estudar.

    Questao gerada nao entra aqui, e nunca vai entrar somada: acertar uma
    variacao que a IA escreveu nao e a mesma coisa que acertar o que a FEPESE
    cobrou. O numero delas sai em `desempenho_das_geradas`, do lado.
    """
    criar_tabelas()
    consulta = (
        select(
            QuestaoDeProva.materia,
            func.count(),
            # Somar a coluna booleana direto NAO funciona: o SQLAlchemy
            # devolve a soma com o tipo da coluna, entao 2 acertos voltam
            # como True e viram 1. O case transforma em inteiro antes.
            func.sum(case((RespostaDeSimulado.acertou.is_(True), 1), else_=0)),
        )
        .join(QuestaoDeProva, QuestaoDeProva.id == RespostaDeSimulado.questao_id)
        .where(RespostaDeSimulado.escolhida.is_not(None))
        .where(RespostaDeSimulado.gerada.is_(False))
        .group_by(QuestaoDeProva.materia)
    )
    return _somar_desempenho(consulta, simulado_id)


def desempenho_das_geradas(
    simulado_id: int | None = None,
) -> list[DesempenhoDaMateria]:
    """O mesmo, para as questoes escritas pela IA. Sempre um numero a parte.

    Existe como funcao propria, e nao como parametro de `desempenho`, porque
    o parametro convidaria alguem a somar os dois um dia. Sao duas perguntas
    diferentes: "quanto eu acerto do que a banca cobrou" e "quanto eu acerto
    no treino que eu mandei escrever".
    """
    criar_tabelas()
    consulta = (
        select(
            QuestaoGerada.materia,
            func.count(),
            func.sum(case((RespostaDeSimulado.acertou.is_(True), 1), else_=0)),
        )
        .join(QuestaoGerada, QuestaoGerada.id == RespostaDeSimulado.questao_id)
        .where(RespostaDeSimulado.escolhida.is_not(None))
        .where(RespostaDeSimulado.gerada.is_(True))
        .group_by(QuestaoGerada.materia)
    )
    return _somar_desempenho(consulta, simulado_id)


def _somar_desempenho(consulta, simulado_id: int | None) -> list[DesempenhoDaMateria]:
    """Roda a consulta de acerto por materia e ordena pior primeiro."""
    if simulado_id is not None:
        consulta = consulta.where(RespostaDeSimulado.simulado_id == simulado_id)

    with sessao() as s:
        linhas = s.execute(consulta).all()

    resultado = [
        DesempenhoDaMateria(m or "sem materia", int(total), int(acertos or 0))
        for m, total, acertos in linhas
    ]
    # pior primeiro: e onde vale gastar tempo de estudo
    resultado.sort(key=lambda d: d.porcentagem)
    return resultado


def simulados_recentes(limite: int = 10) -> list[Simulado]:
    criar_tabelas()
    with sessao() as s:
        return list(s.scalars(
            select(Simulado).order_by(Simulado.criado_em.desc()).limit(limite)
        ))


def resumo_do_simulado(simulado_id: int) -> dict:
    """Quantas questoes, quantas respondidas e quantos acertos."""
    respostas = _respostas(simulado_id)
    respondidas = [r for r in respostas if r.escolhida]
    return {
        "total": len(respostas),
        "respondidas": len(respondidas),
        "acertos": sum(1 for r in respondidas if r.acertou),
        "terminou": bool(respostas) and len(respondidas) == len(respostas),
    }


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
        ))
    # errado primeiro: e o que eu preciso rever
    itens.sort(key=lambda i: i.acertou)
    return itens
