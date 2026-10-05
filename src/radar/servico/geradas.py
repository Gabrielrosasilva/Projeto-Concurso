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

from sqlalchemy import func, or_, select

from radar import config, gerador
from radar import gerador as motor
from radar.db import criar_tabelas, sessao
from radar.origem import TENDENCIA
from radar.models import (
    QuestaoDeProva,
    QuestaoGerada,
    RespostaDeSimulado,
    Simulado,
)
from radar.questoes import chave_da_questao

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
        from radar import conteudos as arvore

        # Todas as grafias: a prova de 2013 escreve "Direito Processo Penal".
        consulta = consulta.where(
            QuestaoDeProva.materia.in_(arvore.grafias_da_materia(materia)))

    # Uma por enunciado: a mesma pergunta aparece em mais de um caderno, e
    # variar as duas copias daria as mesmas variacoes duas vezes.
    por_enunciado: dict[str, QuestaoDeProva] = {}
    for questao in s.scalars(consulta):
        por_enunciado.setdefault(questao.impressao, questao)
    return list(por_enunciado.values())


# --- as questoes reais de um ESCOPO (Etapa 5) -----------------------------------
#
# O `_reais_do_alvo` escolhe pela coluna `materia`, o texto que o caderno
# escreveu. Isso basta para o simulado, e nao basta para o treino: "Lei de
# Execucao Penal" tem dezenas de assuntos, e a §7 existe justamente para eu nao
# receber questao de um conteudo que ainda nem estudei.
#
# Aqui a escolha e pela CLASSIFICACAO (Etapa 3A): a questao entra se o no dela
# esta dentro do escopo. E a prioridade e a da §9 - questao real do mesmo no,
# ALVO primeiro, complementar depois, cada uma marcada.


def _por_chave(s, chaves: set) -> dict:
    """{chave: questao} das questoes reais daquelas chaves, sem anulada."""
    from radar.servico.classificacoes import chave_de

    if not chaves:
        return {}
    achadas = {}
    for questao in s.scalars(
        select(QuestaoDeProva)
        .where(QuestaoDeProva.resposta.is_not(None))
        .where(QuestaoDeProva.anulada.is_not(True))
    ):
        chave = chave_de(questao)
        if chave in chaves and chave not in achadas:
            achadas[chave] = questao
    return achadas


def reais_do_escopo(escopo) -> list[tuple[QuestaoDeProva, str]]:
    """[(questao, evidencia)] das reais classificadas DENTRO do escopo.

    Alvo primeiro, complementar depois (§9), e cada uma marcada com a sua
    evidencia - a tela e o pedido precisam dizer qual e qual, e os dois nunca
    se somam. Prova complementar so entra se estiver aceita no acervo
    (`data/acervo_complementar.json`), a mesma regra de toda estatistica.
    """
    from radar.models import Classificacao
    from radar.servico import complementar as acervo_complementar

    criar_tabelas()
    with sessao() as s:
        dentro = {c.chave for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True))
        ) if escopo.dentro(c.conteudo)}
        if not dentro:
            return []

        do_alvo = _provas_do_alvo(s)
        questoes = _por_chave(s, dentro)
        aceitas = acervo_complementar.provas_aceitas()

        saida, vistos = [], set()
        for evidencia, serve in (
            ("alvo", lambda q: q.prova_url in do_alvo),
            ("complementar", lambda q: q.prova_url in aceitas),
        ):
            for chave, questao in questoes.items():
                if chave in vistos or not serve(questao):
                    continue
                vistos.add(chave)
                saida.append((questao, evidencia))
        return saida


def nos_estudados(materia: str | None = None) -> list[str]:
    """Os nos que eu JA ESTUDEI, para o modo revisao (decisao 20).

    Vem do `servico.estudo`, e nao de uma conta nova: "estudado" tem uma
    definicao so, e ela mora la.
    """
    from radar.servico import estudo

    saida = []
    for caminho, situacao in estudo.situacoes().items():
        if not (situacao.estudado or situacao.praticado):
            continue
        if materia and situacao.materia != materia:
            continue
        saida.append(caminho)
    return sorted(saida)


def escopo_da_revisao(materia: str) -> object:
    """O escopo do modo revisao: a materia, restrita aos nos que eu estudei.

    Nenhum no estudado levanta `EscopoInvalido`: pedir revisao do que eu nunca
    vi nao e revisao, e gerar a materia inteira "para nao ficar vazio" seria
    exatamente o alargamento de escopo que a §8 proibe.
    """
    from radar import conteudos as arvore
    from radar.servico import conteudos as servico_conteudos

    caminhos = servico_conteudos.caminhos()
    da_materia = arvore.resolver_escopo(caminhos, materia)
    estudados = [c for c in nos_estudados(materia) if c != da_materia.no]
    if not estudados:
        raise arvore.EscopoInvalido(
            f"Eu ainda não estudei nenhum conteúdo de {materia!r}, então não há "
            f"o que revisar. O que conta como estudado está em "
            f"`radar desempenho` (Análises > Meu desempenho)."
        )
    return arvore.Escopo(no=da_materia.no, nivel="assunto",
                         elementos=tuple(estudados))


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


def _preparar_no_escopo(escopo, modo: str, quantas: int,
                        semente: int | None) -> dict:
    """Os pedidos de um escopo fechado: treino e revisao.

    A prioridade da base e a da §9, e ela decide tudo o que vem aqui:

      1. **questao real do mesmo no** - alvo primeiro, complementar depois.
         Cada uma vira um pedido de variacao, com a evidencia marcada;
      2. **fonte oficial** (`config/leis.yml`), quando nao houver questao real:
         o pedido do zero, com o dispositivo e o link;
      3. **item do edital**, quando nao houver nem lei: o texto literal do
         programa.

    O que NAO acontece aqui: alargar o escopo para achar base. Sem questao real
    do no, o pedido vai do zero DENTRO do mesmo no - e nunca de um no vizinho.
    """
    from radar import leis

    reais = reais_do_escopo(escopo)
    criar_tabelas()
    with sessao() as s:
        ja_usadas = _origens_ja_usadas(s)
        ja_geradas = _impressoes_geradas(s)

    novas = [(q, e) for q, e in reais if q.impressao not in ja_usadas]
    repetidas = [(q, e) for q, e in reais if q.impressao in ja_usadas]
    embaralhar = random.Random(semente)
    embaralhar.shuffle(novas)
    embaralhar.shuffle(repetidas)
    # O alvo volta para a frente depois do embaralho: a §9 nao e sugestao.
    ordenadas = sorted(novas + repetidas, key=lambda par: par[1] != "alvo")

    pedidos: list[dict] = []
    faltam = quantas
    nomes = _nomes_do_escopo(escopo)
    for questao, evidencia in ordenadas:
        if faltam <= 0:
            break
        neste = min(motor.VARIACOES_POR_QUESTAO, faltam)
        pedidos.append({
            "modo": "variacao", "questao": questao, "quantas": neste,
            # A materia e o assunto da gerada sao os do ESCOPO, como no do
            # zero, e nao os gravados na questao de base: a do complementar
            # pode vir de um bloco generico de outra prova ("Conhecimentos
            # Especificos"), e a gerada ficaria fora do treino da materia.
            "materia": escopo.materia, "assunto": nomes[-1],
            "conteudo": escopo.no, "escopo": escopo,
            "base": "questao_real", "evidencia_da_base": evidencia,
        })
        faltam -= neste

    # Faltou questao real DENTRO do escopo para o tanto que eu pedi: a fonte
    # oficial, e depois o item do edital. E a ordem da §9, e vale tambem quando
    # ha UMA real e eu pedi vinte - o que nao vale e sair do escopo para achar
    # base, que e o que a §7 veio consertar. A §9 manda registrar que estas nao
    # tem questao real de referencia, e e o que `base` e
    # `evidencia_da_base: nenhuma` dizem.
    sem_base = not reais
    if faltam > 0:
        lei = leis.do_assunto(escopo.materia, nomes[-1])
        base = "fonte_oficial" if lei else "item_do_edital"
        exemplos = _exemplos_de_estilo(escopo)
        while faltam > 0:
            neste = min(motor.VARIACOES_POR_QUESTAO, faltam)
            pedidos.append({
                "modo": "do_zero", "materia": escopo.materia,
                "assunto": nomes[-1], "exemplos": exemplos, "quantas": neste,
                "conteudo": escopo.no, "escopo": escopo,
                "base": base, "evidencia_da_base": "nenhuma", "lei": lei,
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
            corpo = motor._montar_pedido_variacao(pedido["questao"],
                                                  pedido["quantas"])
            caracteres += len(motor.INSTRUCAO_VARIACAO) + len(corpo)
    entrada, saida, custo = motor.estimar(
        len(pedidos), caracteres, motor.VARIACOES_POR_QUESTAO
    )
    return {
        "pedidos": pedidos,
        "quantas": sum(p["quantas"] for p in pedidos),
        "modo": "do_zero" if sem_base and pedidos else "variacao",
        "modo_do_pedido": modo,
        "escopo": escopo,
        "sem_base": sem_base,
        "base_disponivel": len(reais),
        "do_alvo": sum(1 for _q, e in reais if e == "alvo"),
        "do_complementar": sum(1 for _q, e in reais if e == "complementar"),
        "ja_geradas": ja_geradas,
        "entrada": entrada,
        "saida": saida,
        "custo": custo,
        # O custo e estimativa, antes de gastar (Etapa 7A).
        "origem_do_custo": TENDENCIA,
    }


def _nomes_do_escopo(escopo) -> list[str]:
    from radar import conteudos as arvore

    return arvore.partes(escopo.caminhos[0])


def _exemplos_de_estilo(escopo) -> list:
    """Questoes reais da MATERIA, so como exemplo de estilo da banca.

    Elas nao sao a base da questao gerada - a base e a fonte oficial ou o item
    do edital, e e isso que fica gravado. Servem para a IA escrever no formato
    da FEPESE, e por isso vem da materia inteira, nao do no.
    """
    criar_tabelas()
    with sessao() as s:
        candidatas = _reais_do_alvo(s, escopo.materia) or _reais_do_alvo(s)
    return candidatas[: motor.EXEMPLOS_DO_ZERO]


def _pelo_peso_do_edital(candidatas: list, quantas: int) -> dict[str, int] | None:
    """{materia do edital: quantas}, para o simulado sem materia escolhida.

    A §8 pede que o modo simulado respeite "o edital, o peso das materias":
    as questoes se dividem pelo quadro do edital, com o `compilado.distribuir`
    - a mesma conta do simulado compilado e da composicao (decisao 67) -, so
    entre as materias que tem questao real do alvo para servir de base. None
    sem o quadro lido: ai vale o sorteio de antes, e a saida nao diz peso.
    """
    from radar.servico import compilado

    pesos, _edital, _arquivo = compilado._pesos(None)
    com_base = {m: p for m, p in pesos.items()
                if any(compilado.mesma_materia(m, q.materia) for q in candidatas)}
    if not com_base:
        return None
    return compilado.distribuir(com_base, quantas)


def modo_do_pedido(escopo, pedido: str | None = None) -> str:
    """O modo, escolhido ou deduzido do escopo (§8).

    Sem `--modo`: com assunto e TREINO, so com materia e SIMULADO. A saida
    escreve qual foi, porque "amplo" e "especifico" nao podem se confundir.
    """
    from radar.models import MODOS_DE_PEDIDO

    if pedido:
        if pedido not in MODOS_DE_PEDIDO:
            raise ValueError(
                f"modo {pedido!r} nao existe: escolha {', '.join(MODOS_DE_PEDIDO)}"
            )
        return pedido
    return "treino" if (escopo is not None and escopo.especifico) else "simulado"


def preparar(
    materia: str | None = None,
    quantas: int = QUANTIDADE_PADRAO,
    semente: int | None = None,
    escopo=None,
    modo: str | None = None,
) -> dict:
    """Monta a lista de pedidos e estima o custo. NAO gasta nada.

    Uma questao real rende `VARIACOES_POR_QUESTAO` variacoes, entao o numero
    de chamadas e o de questoes pedidas dividido por tres, arredondado para
    cima - a ultima chamada pede so o que falta.

    A escolha da questao de base prefere a que nunca foi variada. Variar de
    novo a mesma questao daria uma quarta versao da mesma pergunta, quando
    ainda ha pergunta que nunca virou treino nenhum.

    Com `escopo` (Etapa 5), as questoes de base saem da CLASSIFICACAO e nao da
    coluna `materia`: so as que estao dentro do escopo entram, alvo antes do
    complementar (§9). Sem escopo, o comportamento amplo de sempre - que a §7
    manda preservar, porque e dele que sai o simulado.
    """
    criar_tabelas()
    quantas = max(1, int(quantas))
    escolhido = modo_do_pedido(escopo, modo)
    if escolhido == "revisao":
        escopo = escopo_da_revisao(materia)

    # O SIMULADO e amplo por definicao (§8, modo 3): mesmo com a materia
    # escolhida, ele vai pelo caminho de sempre - a coluna `materia` -, e nao
    # pela classificacao. Restringir o simulado as questoes ja classificadas o
    # deixaria menor do que ele e, e a §7 manda preservar a consulta ampla.
    if escopo is not None and escolhido != "simulado":
        return _preparar_no_escopo(escopo, escolhido, quantas, semente)
    if escopo is not None:
        materia = escopo.materia

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
    distribuicao = None
    if escolhido == "simulado" and not materia and candidatas:
        distribuicao = _pelo_peso_do_edital(candidatas, quantas)
    if distribuicao:
        # Materia por materia, na ordem do quadro, cada uma com as bases dela
        # (a nunca variada antes da ja variada, como no caminho de sempre).
        from radar.servico.compilado import mesma_materia

        for do_edital, pedidas in distribuicao.items():
            da_materia = [q for q in ordenadas if mesma_materia(do_edital, q.materia)]
            for questao in da_materia:
                if pedidas <= 0:
                    break
                neste = min(motor.VARIACOES_POR_QUESTAO, pedidas)
                pedidos.append({"modo": "variacao", "questao": questao, "quantas": neste})
                pedidas -= neste
        faltam = quantas - sum(p["quantas"] for p in pedidos)
    else:
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
        "modo_do_pedido": escolhido,
        "escopo": None,
        # {materia: quantas} quando o simulado se dividiu pelo edital.
        "distribuicao": distribuicao,
        "sem_base": sem_base,
        "base_disponivel": len(candidatas),
        "ja_geradas": ja_geradas,
        "entrada": entrada,
        "saida": saida,
        "custo": custo,
        # O custo e estimativa, antes de gastar (Etapa 7A).
        "origem_do_custo": TENDENCIA,
    }


def gravar(questoes: list) -> int:
    """Guarda as questoes novas. Devolve quantas entraram.

    Enunciado repetido nao entra duas vezes: a impressao e unica na tabela, e
    e ela que diz que duas perguntas sao a mesma pergunta.

    **Questao sem `modelo` nao e gravada**, e o lote inteiro para: e a mesma
    trava do `gravar_assuntos`. Texto de IA sem procedencia e o que nao pode
    se repetir depois dos 93 assuntos de 24/09/2026.
    """
    if not questoes:
        return 0
    if any(not (nova.modelo or "").strip() for nova in questoes):
        raise ValueError(
            "questao gerada sem modelo nao e gravada: diga de onde ela veio"
        )

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
                origem_chave=getattr(nova, "origem_chave", None),
                modelo=nova.modelo,
                materia=nova.materia,
                assunto=nova.assunto,
                # O escopo e a base (Etapa 5). Nulos no pedido amplo e nas 50
                # geradas antes dela: nao houve escopo, e inventar um diria
                # que elas foram pedidas de um jeito que nao foram.
                conteudo=getattr(nova, "conteudo", None),
                modo_do_pedido=getattr(nova, "modo_do_pedido", None),
                escopo=getattr(nova, "escopo", None),
                base=getattr(nova, "base", None),
                evidencia_da_base=getattr(nova, "evidencia_da_base", None),
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

    Reconhecida pela CHAVE (enunciado e alternativas), a regra do projeto: a
    impressao, so do enunciado, pode ser de questoes diferentes da mesma
    prova, e o selo apontaria a errada. Sem a chave gravada (as variacoes de
    antes do F3), a impressao so serve quando todas as questoes dela sao a
    mesma questao, reaproveitada em mais de um caderno.

    None quando a questao foi escrita do zero, quando o acervo local ainda nao
    tem o caderno de origem, ou quando nao ha como saber qual das questoes foi
    a base - o selo entao diz so o que sabe.
    """
    if questao is None or not questao.origem_impressao:
        return None

    criar_tabelas()
    with sessao() as s:
        candidatas = s.scalars(
            select(QuestaoDeProva)
            .where(QuestaoDeProva.impressao == questao.origem_impressao)
            .order_by(QuestaoDeProva.id)
        )
        return _a_da_chave(candidatas, questao.origem_chave)


def _a_da_chave(candidatas, chave: str | None) -> QuestaoDeProva | None:
    """A questao com a chave pedida; sem chave, a unica que a impressao deixa.

    A mesma questao em dois cadernos tem a mesma chave: qualquer uma das duas
    serve, e fica a primeira.
    """
    por_chave: dict[str, QuestaoDeProva] = {}
    for questao in candidatas:
        por_chave.setdefault(chave_da_questao(questao.enunciado, questao.alternativas),
                             questao)
    if chave:
        return por_chave.get(chave)
    return next(iter(por_chave.values())) if len(por_chave) == 1 else None


def preencher_origem_chave() -> int:
    """Grava a chave da base nas variacoes que ainda nao a tem. Quantas.

    So quando a impressao da base aponta para uma questao so do acervo (ou
    para a mesma questao em mais de um caderno). Quando aponta para questoes
    diferentes, a chave fica nula: nao ha como saber qual foi a base, e
    escolher uma seria o mesmo erro do `limit(1)` que o F3 tirou.
    """
    criar_tabelas()
    preenchidas = 0
    with sessao() as s:
        variacoes = s.scalars(
            select(QuestaoGerada)
            .where(QuestaoGerada.origem_impressao.is_not(None))
            .where(QuestaoGerada.origem_chave.is_(None))
        ).all()
        for gerada in variacoes:
            candidatas = s.scalars(
                select(QuestaoDeProva)
                .where(QuestaoDeProva.impressao == gerada.origem_impressao)
                .order_by(QuestaoDeProva.id)
            )
            base = _a_da_chave(candidatas, None)
            if base is not None:
                gerada.origem_chave = chave_da_questao(base.enunciado, base.alternativas)
                preenchidas += 1
    return preenchidas


def rechavear(trocas_de_chave: dict[str, set[str]],
              trocas_de_impressao: dict[str, set[str]]) -> int:
    """A base de cada variacao acompanha a releitura do caderno (B.7).

    A gerada aponta a questao real de base pela chave e pela impressao, e as
    duas mudam quando o leitor consertado muda o texto. Com uma chave nova so,
    a gerada passa a ela. Com mais de uma (a mesma questao em dois cadernos,
    lida diferente), nao ha como saber qual: a gerada fica com a antiga, como
    a de 27/09 sem base achada (decisao 77). Devolve quantas mudaram.
    """
    criar_tabelas()
    mudaram = 0
    with sessao() as s:
        for gerada in s.scalars(select(QuestaoGerada)):
            novas = trocas_de_chave.get(gerada.origem_chave or "")
            if novas and len(novas) == 1:
                gerada.origem_chave = next(iter(novas))
                mudaram += 1
            novas = trocas_de_impressao.get(gerada.origem_impressao or "")
            if novas and len(novas) == 1:
                gerada.origem_impressao = next(iter(novas))
                mudaram += 1
    return mudaram


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


#: Ate onde a tela de treinar desce na arvore: materia, assunto, subassunto.
#: O elemento fica de fora - sao poucas geradas por elemento, e a lista
#: viraria um paredao de opcoes com 1 ou 2 questoes cada.
NIVEIS_PARA_TREINAR = 3


def conteudos_para_treinar() -> list[tuple[str, int, int]]:
    """[(caminho do no, nivel, quantas geradas valem nele e abaixo dele)].

    E o seletor do "Treinar com as que ja tenho": materia, e dentro dela os
    assuntos e subassuntos que tem gerada, na ordem da arvore. A gerada conta
    no no dela e em todos os de cima - treinar o assunto pega os subassuntos.
    """
    criar_tabelas()
    with sessao() as s:
        linhas = s.execute(
            select(QuestaoGerada.conteudo, QuestaoGerada.materia)
            .where(QuestaoGerada.rejeitada.is_(False))
            .where(QuestaoGerada.resposta.is_not(None))
        ).all()

    from radar.conteudos import SEPARADOR

    quantas: dict[tuple[str, ...], int] = {}
    for conteudo, materia in linhas:
        partes = tuple((conteudo or materia or "sem materia").split(SEPARADOR))
        for nivel in range(1, min(len(partes), NIVEIS_PARA_TREINAR) + 1):
            quantas[partes[:nivel]] = quantas.get(partes[:nivel], 0) + 1

    return [(SEPARADOR.join(partes), len(partes), n)
            for partes, n in sorted(quantas.items())]


def _sortear(
    quantidade: int,
    materia: str | None = None,
    impressoes: list[str] | None = None,
    conteudo: str | None = None,
) -> list[int]:
    """Ids de questoes geradas que valem para o sorteio."""
    from radar.conteudos import SEPARADOR

    consulta = (
        select(QuestaoGerada)
        .where(QuestaoGerada.rejeitada.is_(False))
        .where(QuestaoGerada.resposta.is_not(None))
    )
    if materia:
        consulta = consulta.where(QuestaoGerada.materia == materia)
    if conteudo:
        # O no e tudo que esta abaixo dele. A materia (sem separador) tambem
        # vale pela coluna `materia`, para a gerada que ficou sem no.
        dentro = [
            QuestaoGerada.conteudo == conteudo,
            QuestaoGerada.conteudo.startswith(conteudo + SEPARADOR, autoescape=True),
        ]
        if SEPARADOR not in conteudo:
            dentro.append(QuestaoGerada.materia == conteudo)
        consulta = consulta.where(or_(*dentro))
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
    conteudo: str | None = None,
) -> Simulado | None:
    """Uma rodada SO de questoes geradas, na mesma tela do simulado de sempre.

    Rodada so de geradas, e nunca misturada com as reais: assim o resultado
    daquela rodada ja e um dos dois numeros que a tela mostra separados, sem
    ninguem precisar separar depois.
    """
    criar_tabelas()

    ids = _sortear(quantidade, materia, impressoes, conteudo)
    if not ids:
        return None

    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(ids),
            "materia": materia,
            "conteudo": conteudo,
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
