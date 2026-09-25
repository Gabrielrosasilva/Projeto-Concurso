"""Questoes escritas pela IA: montar o pedido, guardar, e sortear para treino.

A regra que manda aqui esta em `radar.gerador`, e vale repetir: questao gerada
serve para TREINAR, nunca para MEDIR o que a banca cobra. Este arquivo so fala
com a tabela `questoes_geradas` - e por isso nenhuma conta de incidencia, peso
de materia, macete ou "Onde estudar primeiro" alcanca o que esta aqui.

De onde sai a materia-prima: as provas do MEU cargo, no MEU estado - as mesmas
que o Meu foco conta. Variar uma questao de Merendeira da mesma banca daria
uma questao de Merendeira, que nao me serve.
"""
import logging
import random

from sqlalchemy import func, select

from radar import config, gerador
from radar import gerador as motor
from radar.db import criar_tabelas, sessao
from radar.models import (
    QuestaoDeProva,
    QuestaoGerada,
    RespostaDeSimulado,
    Simulado,
)

log = logging.getLogger(__name__)

# Quantas questoes a tela oferece de uma vez, quando eu nao digito nada.
QUANTIDADE_PADRAO = 5


def _provas_do_alvo(s) -> set[str]:
    """Os cadernos que sao a MINHA prova. A regra mora no `foco`, nao aqui."""
    from radar import foco

    return foco._provas_do_alvo(s)


def _reais_do_alvo(s, materia: str | None = None) -> list[QuestaoDeProva]:
    """As questoes reais que podem servir de base, na materia pedida.

    Anulada fica de fora: a banca disse que ela nao tem resposta certa, e
    variar uma questao sem gabarito seria multiplicar o problema.
    """
    consulta = (
        select(QuestaoDeProva)
        .where(QuestaoDeProva.prova_url.in_(_provas_do_alvo(s)))
        .where(QuestaoDeProva.resposta.is_not(None))
        .where(QuestaoDeProva.anulada.is_not(True))
    )
    if materia:
        consulta = consulta.where(QuestaoDeProva.materia == materia)

    # Uma por enunciado: a mesma pergunta aparece em mais de um caderno, e
    # variar as duas copias daria as mesmas variacoes duas vezes.
    por_enunciado: dict[str, QuestaoDeProva] = {}
    for questao in s.scalars(consulta):
        por_enunciado.setdefault(questao.impressao, questao)
    return list(por_enunciado.values())


def materias_para_gerar() -> list[tuple[str, int, int]]:
    """[(materia, quantas reais servem de base, quantas ja foram geradas)].

    E o que a tela de "Gerar questoes" mostra no seletor: antes de eu escolher,
    ja da para ver em que materia existe base para variar.
    """
    criar_tabelas()
    with sessao() as s:
        reais = _reais_do_alvo(s)
        geradas = s.execute(
            select(QuestaoGerada.materia, func.count())
            .where(QuestaoGerada.rejeitada.is_(False))
            .group_by(QuestaoGerada.materia)
        ).all()

    por_materia: dict[str, int] = {}
    for questao in reais:
        nome = questao.materia or "sem materia"
        por_materia[nome] = por_materia.get(nome, 0) + 1

    ja_geradas = {(m or "sem materia"): int(n) for m, n in geradas}
    for nome in ja_geradas:
        por_materia.setdefault(nome, 0)

    return sorted(
        ((nome, quantas, ja_geradas.get(nome, 0))
         for nome, quantas in por_materia.items()),
        key=lambda linha: (-linha[1], linha[0]),
    )


def _origens_ja_usadas(s) -> set[str]:
    """A impressao das questoes reais que ja viraram variacao alguma vez."""
    linhas = s.execute(
        select(QuestaoGerada.origem_impressao)
        .where(QuestaoGerada.origem_impressao.is_not(None))
        .distinct()
    ).all()
    return {impressao for (impressao,) in linhas if impressao}


def _impressoes_geradas(s) -> set[str]:
    """Tudo que ja foi gerado, inclusive o que eu rejeitei.

    O rejeitado entra de proposito: pedir de novo a mesma pergunta que eu ja
    marquei como errada seria pagar para repetir o erro.
    """
    return {i for (i,) in s.execute(select(QuestaoGerada.impressao)).all()}


def preparar(
    materia: str | None = None,
    quantas: int = QUANTIDADE_PADRAO,
    semente: int | None = None,
) -> dict:
    """Monta a lista de pedidos e estima o custo. NAO gasta nada.

    Uma questao real rende `VARIACOES_POR_QUESTAO` variacoes, entao o numero
    de chamadas e o de questoes pedidas dividido por tres, arredondado para
    cima - a ultima chamada pede so o que falta.

    A escolha da questao de base prefere a que nunca foi variada. Variar de
    novo a mesma questao daria uma quarta versao da mesma pergunta, quando
    ainda ha pergunta que nunca virou treino nenhum.
    """
    criar_tabelas()
    quantas = max(1, int(quantas))

    with sessao() as s:
        candidatas = _reais_do_alvo(s, materia)
        ja_usadas = _origens_ja_usadas(s)
        ja_geradas = _impressoes_geradas(s)
        exemplos_da_materia = candidatas or _reais_do_alvo(s)

    novas = [q for q in candidatas if q.impressao not in ja_usadas]
    repetidas = [q for q in candidatas if q.impressao in ja_usadas]

    embaralhar = random.Random(semente)
    embaralhar.shuffle(novas)
    embaralhar.shuffle(repetidas)
    ordenadas = novas + repetidas

    pedidos: list[dict] = []
    faltam = quantas
    for questao in ordenadas:
        if faltam <= 0:
            break
        neste = min(motor.VARIACOES_POR_QUESTAO, faltam)
        pedidos.append({"modo": "variacao", "questao": questao, "quantas": neste})
        faltam -= neste

    # Sem questao real na materia nao ha o que variar, e ai vale o modo do
    # zero - com questoes reais servindo so de exemplo de estilo. E a excecao,
    # e a tela precisa dizer isso.
    sem_base = not candidatas
    if sem_base and faltam > 0 and exemplos_da_materia:
        exemplos = exemplos_da_materia[: motor.EXEMPLOS_DO_ZERO]
        while faltam > 0:
            neste = min(motor.VARIACOES_POR_QUESTAO, faltam)
            pedidos.append({
                "modo": "do_zero",
                "materia": materia or "sem materia",
                "assunto": None,
                "exemplos": exemplos,
                "quantas": neste,
            })
            faltam -= neste

    caracteres = 0
    for pedido in pedidos:
        if pedido["modo"] == "do_zero":
            corpo = motor._montar_pedido_do_zero(
                pedido["materia"], pedido["assunto"], pedido["exemplos"],
                pedido["quantas"],
            )
            caracteres += len(motor.INSTRUCAO_DO_ZERO) + len(corpo)
        else:
            corpo = motor._montar_pedido_variacao(
                pedido["questao"], pedido["quantas"]
            )
            caracteres += len(motor.INSTRUCAO_VARIACAO) + len(corpo)

    entrada, saida, custo = motor.estimar(
        len(pedidos), caracteres, motor.VARIACOES_POR_QUESTAO
    )
    return {
        "pedidos": pedidos,
        "quantas": sum(p["quantas"] for p in pedidos),
        "modo": "do_zero" if sem_base and pedidos else "variacao",
        "sem_base": sem_base,
        "base_disponivel": len(candidatas),
        "ja_geradas": ja_geradas,
        "entrada": entrada,
        "saida": saida,
        "custo": custo,
    }


def gravar(questoes: list) -> int:
    """Guarda as questoes novas. Devolve quantas entraram.

    Enunciado repetido nao entra duas vezes: a impressao e unica na tabela, e
    e ela que diz que duas perguntas sao a mesma pergunta.
    """
    if not questoes:
        return 0

    criar_tabelas()
    gravadas = 0
    with sessao() as s:
        existentes = _impressoes_geradas(s)
        for nova in questoes:
            if nova.impressao in existentes:
                continue
            existentes.add(nova.impressao)
            s.add(QuestaoGerada(
                modo=nova.modo,
                origem_impressao=nova.origem_impressao,
                modelo=nova.modelo,
                materia=nova.materia,
                assunto=nova.assunto,
                artigo=nova.artigo,
                enunciado=nova.enunciado,
                alternativas=nova.alternativas,
                resposta=nova.resposta,
                impressao=nova.impressao,
            ))
            gravadas += 1
    return gravadas


def gerar(
    materia: str | None = None,
    quantas: int = QUANTIDADE_PADRAO,
    teto_em_dolar: float = gerador.TETO_PADRAO,
) -> dict:
    """Gera de verdade: chama a API, grava, e exporta para o arquivo.

    Custa dinheiro. Quem decide se chega aqui e a CLI ou a tela - as duas
    simulam por padrao.
    """
    chave = config.chave_da_anthropic()
    if not chave:
        return {"erro": "sem chave", "geradas": 0}

    plano = preparar(materia, quantas)
    if not plano["pedidos"]:
        return {"erro": "sem base", "geradas": 0, "pedidos": 0}

    resultado = motor.gerar(
        plano["pedidos"], chave,
        teto_em_dolar=teto_em_dolar,
        ja_existentes=plano["ja_geradas"],
    )
    gravadas = gravar(resultado.questoes)

    guardadas = 0
    if gravadas:
        from radar import acervo

        guardadas = acervo.exportar_geradas()

    return {
        "pedidos": len(plano["pedidos"]),
        "geradas": gravadas,
        # A impressao do que acabou de nascer. E com ela que a tela monta uma
        # rodada SO com as questoes desta geracao, em vez de misturar com o
        # que ja estava guardado de antes.
        "impressoes": [q.impressao for q in resultado.questoes],
        "descartadas": resultado.descartadas,
        "guardadas": guardadas,
        "custo": resultado.uso.custo,
        "chamadas": resultado.uso.chamadas,
        "parou_no_teto": resultado.parou_no_teto,
        "falhas": resultado.falhas,
    }


# --- o que a tela precisa ---------------------------------------------------

def contar() -> dict:
    """Quantas questoes geradas existem, quantas eu rejeitei, quantas restam."""
    criar_tabelas()
    with sessao() as s:
        total = s.scalar(select(func.count()).select_from(QuestaoGerada)) or 0
        rejeitadas = s.scalar(
            select(func.count()).select_from(QuestaoGerada)
            .where(QuestaoGerada.rejeitada.is_(True))
        ) or 0
    return {"total": total, "rejeitadas": rejeitadas, "valem": total - rejeitadas}


def buscar(questao_id: int) -> QuestaoGerada | None:
    criar_tabelas()
    with sessao() as s:
        return s.get(QuestaoGerada, questao_id)


def origem_de(questao: QuestaoGerada | None) -> QuestaoDeProva | None:
    """A questao REAL em que a gerada se baseou, para o selo da tela.

    None quando a questao foi escrita do zero, ou quando o acervo local ainda
    nao tem o caderno de origem - o selo entao diz so o que sabe.
    """
    if questao is None or not questao.origem_impressao:
        return None

    criar_tabelas()
    with sessao() as s:
        return s.scalar(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.impressao == questao.origem_impressao)
            .limit(1)
        )


def rejeitar(questao_id: int) -> bool:
    """Marca "essa questao esta errada". Ela sai do sorteio para sempre.

    A QUESTAO nao e apagada: o erro guardado e o que me diz, depois, se um
    assunto da errado toda vez - e ai o problema nao e a questao, e o pedido
    que eu mandei. Apagar jogaria fora essa informacao.

    O que sai sao as RESPOSTAS dela, em todas as rodadas. Uma questao que eu
    declarei errada nao pode continuar pesando no meu acerto: se ela nao vale
    como questao, nao vale como acerto nem como erro. E e isso tambem que
    destrava a rodada em andamento, quando eu rejeito no meio dela.
    """
    criar_tabelas()
    with sessao() as s:
        questao = s.get(QuestaoGerada, questao_id)
        if questao is None:
            return False
        questao.rejeitada = True

        respostas = s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.questao_id == questao_id)
            .where(RespostaDeSimulado.gerada.is_(True))
        )
        for resposta in respostas:
            s.delete(resposta)
        return True


def _sortear(
    quantidade: int,
    materia: str | None = None,
    impressoes: list[str] | None = None,
) -> list[int]:
    """Ids de questoes geradas que valem para o sorteio."""
    consulta = (
        select(QuestaoGerada)
        .where(QuestaoGerada.rejeitada.is_(False))
        .where(QuestaoGerada.resposta.is_not(None))
    )
    if materia:
        consulta = consulta.where(QuestaoGerada.materia == materia)
    if impressoes is not None:
        consulta = consulta.where(QuestaoGerada.impressao.in_(impressoes))

    with sessao() as s:
        candidatas = list(s.scalars(consulta))

    random.shuffle(candidatas)
    return [q.id for q in candidatas[:quantidade]]


def criar_simulado(
    quantidade: int = QUANTIDADE_PADRAO,
    materia: str | None = None,
    impressoes: list[str] | None = None,
) -> Simulado | None:
    """Uma rodada SO de questoes geradas, na mesma tela do simulado de sempre.

    Rodada so de geradas, e nunca misturada com as reais: assim o resultado
    daquela rodada ja e um dos dois numeros que a tela mostra separados, sem
    ninguem precisar separar depois.
    """
    criar_tabelas()

    ids = _sortear(quantidade, materia, impressoes)
    if not ids:
        return None

    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(ids),
            "materia": materia,
            # E esta marca que a tela le para mostrar o selo no topo.
            "geradas": True,
        })
        s.add(simulado)
        s.flush()

        for ordem, questao_id in enumerate(ids, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id,
                questao_id=questao_id,
                ordem=ordem,
                gerada=True,
            ))
        return simulado
