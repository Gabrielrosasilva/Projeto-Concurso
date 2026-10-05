"""A faixa de Portugues que comeca no radar (decisao 107).

A faixa de questoes de Portugues continua no Qconcursos: o acervo aceito tem
251 questoes distintas de Portugues da FEPESE, e um tema chega a ter uma so,
enquanto o dia pede 21 dele. Mas ela COMECA pelas que o radar tem do tema e
que eu ainda nao respondi - reais, da FEPESE, do alvo primeiro e depois do
complementar aceito, uma por chave, sem anulada. O resto, no Qconcursos.

O que eu respondo aqui conta sozinho (o desempenho por tema e o 1-7-30); o
"fiz X, acertei Y" da faixa fica so para as do Qconcursos. A rodada nao mede:
nao entra na comparacao do fechamento, que so le diagnostico e simulado.

O tema e o no da arvore: os `nos` da ficha, ou o assunto e o subassunto que
ela escreveu, ou os `nos` do plano - a mesma ordem do `fichas.onde_na_arvore`
(decisao 71).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select

from radar import conteudos as arvore
from radar import fichas
from radar.db import criar_tabelas, sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.servico import composicao, evidencia
from radar.servico import fichas as servico_fichas

#: As materias em que a faixa comeca no radar. Portugues, por pedido de
#: 05/10: e a materia em que o complementar foi classificado inteiro.
MATERIAS = ("Língua Portuguesa",)
TIPOS = ("questoes", "revisao")
#: O nome da rodada em `Simulado.filtros`.
RODADA = "faixa_no_radar"


def aceita(faixa) -> bool:
    """A faixa de questoes de Portugues no Qconcursos, com numero de questoes."""
    return (faixa is not None and not getattr(faixa, "desligada", False)
            and faixa.tipo in TIPOS and faixa.onde == "qconcursos"
            and faixa.materia in MATERIAS and bool(faixa.questoes))


def nos_da_faixa(faixa, escrita: fichas.FichaEscrita | None) -> list[str]:
    """Os nos do tema: os da ficha; sem eles, o assunto e o subassunto que a
    ficha escreveu; sem ficha, os do plano. Vazio quando nada diz."""
    if escrita is not None and escrita.nos:
        return list(escrita.nos)
    if escrita is not None and escrita.assunto:
        no = arvore.caminho(escrita.materia, escrita.assunto)
        return [arvore.caminho(no, escrita.subassunto) if escrita.subassunto else no]
    nos = list(getattr(faixa, "nos", ()) or ())
    if not nos and getattr(faixa, "conteudo", None):
        nos = [faixa.conteudo]
    return nos


def _dentro(conteudo: str, nos: list[str]) -> bool:
    return any(conteudo == no or conteudo.startswith(no + arvore.SEPARADOR) for no in nos)


def candidatas(nos: list[str], estoque: dict, respondidas: set[str],
               semente: str, fora: set[int] = frozenset()) -> list[composicao.Candidata]:
    """As questoes reais do tema que eu ainda nao respondi: uma por chave, as
    do alvo primeiro, cada grupo numa ordem que nao muda no mesmo dia. `fora`
    sao as ja postas em outra faixa: a da manha e a da noite do mesmo tema
    nao repetem questao."""
    vistas: set[str] = set()
    saida = []
    for lista in estoque.values():
        for c in lista:
            if (c.chave in vistas or c.impressao in respondidas or c.id in fora
                    or not _dentro(c.conteudo, nos)):
                continue
            vistas.add(c.chave)
            saida.append(c)
    saida.sort(key=lambda c: c.id)
    random.Random(semente).shuffle(saida)
    # sort e estavel: o embaralhado continua dentro de cada evidencia.
    saida.sort(key=lambda c: c.evidencia != evidencia.ALVO)
    return saida


@dataclass
class FaixaNoRadar:
    """O que a tela Hoje mostra numa faixa de Portugues."""

    nos: list[str]
    do_radar: int                 # quantas a rodada tem, ou teria
    total: int                    # o numero do plano
    rodada_id: int | None = None
    #: As do tema que existem, ja respondidas ou nao (para a frase "voce ja
    #: respondeu todas").
    no_acervo: int = 0
    proprias: int = 0             # do alvo, entre as `do_radar`
    nomes: list[str] = field(default_factory=list)
    #: As questoes que a rodada teria (so no planejado).
    ids: list[int] = field(default_factory=list)

    @property
    def no_qconcursos(self) -> int:
        return max(self.total - self.do_radar, 0)


def _ja_postas() -> set[int]:
    """As questoes que ja estao numa rodada de faixa, respondidas ou nao."""
    criar_tabelas()
    with sessao() as s:
        ids = [simulado.id for simulado in s.scalars(select(Simulado))
               if (simulado.filtros or {}).get("rodada") == RODADA]
        return set(s.scalars(select(RespostaDeSimulado.questao_id)
                             .where(RespostaDeSimulado.simulado_id.in_(ids)))) if ids else set()


def _da_rodada(simulado: Simulado, nos: list[str], total: int) -> FaixaNoRadar:
    filtros = simulado.filtros or {}
    return FaixaNoRadar(nos=filtros.get("nos") or nos, do_radar=filtros.get("quantidade", 0),
                        total=total, rodada_id=simulado.id,
                        proprias=filtros.get("proprias", 0),
                        nomes=[arvore.partes(n)[-1] for n in (filtros.get("nos") or nos)])


def planejar(data: date, bloco: str, indice: int, faixa, escrita, estoque: dict,
             respondidas: set[str], fora: set[int] = frozenset()) -> FaixaNoRadar:
    """Quantas a faixa faria no radar. NAO cria nada; com a rodada criada,
    mostra a gravada."""
    nos = nos_da_faixa(faixa, escrita)
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return _da_rodada(existente, nos, faixa.questoes)
    escolhidas = candidatas(nos, estoque, respondidas,
                            composicao._semente(data, bloco, indice), fora)[:faixa.questoes]
    no_acervo = len(candidatas(nos, estoque, set(), "")) if nos else 0
    return FaixaNoRadar(nos=nos, do_radar=len(escolhidas), total=faixa.questoes,
                        no_acervo=no_acervo, ids=[c.id for c in escolhidas],
                        proprias=sum(1 for c in escolhidas if c.evidencia == evidencia.ALVO),
                        nomes=[arvore.partes(n)[-1] for n in nos])


def das_faixas(blocos, data: date) -> dict:
    """{(bloco, indice): FaixaNoRadar} das faixas de Portugues do dia. Dia sem
    elas nao le nada."""
    aceitas = [(bloco.chave, indice, faixa) for bloco in blocos
               for indice, faixa in enumerate(bloco.faixas) if aceita(faixa)]
    if not aceitas:
        return {}
    escritas = servico_fichas.carregar()
    estoque = composicao.estoque_real(list(MATERIAS))
    respondidas = composicao.ja_respondidas()
    # Na ordem do dia: a faixa da noite planeja com o que a da manha deixou.
    fora = _ja_postas()
    saida = {}
    for bloco, indice, faixa in aceitas:
        plano = planejar(data, bloco, indice, faixa, fichas.da_faixa(faixa, escritas),
                         estoque, respondidas, fora)
        fora = fora | set(plano.ids)
        saida[(bloco, indice)] = plano
    return saida


def criar_rodada(data: date, bloco: str, indice: int, faixa) -> Simulado | None:
    """A rodada com as do radar, ou a que ja existe. None sem questao nova do
    tema (ai e tudo no Qconcursos)."""
    if not aceita(faixa):
        return None
    existente = composicao.rodada_da_faixa(data, bloco, indice, faixa)
    if existente is not None:
        return existente
    nos = nos_da_faixa(faixa, fichas.da_faixa(faixa, servico_fichas.carregar()))
    if not nos:
        return None
    escolhidas = candidatas(nos, composicao.estoque_real(list(MATERIAS)),
                            composicao.ja_respondidas(),
                            composicao._semente(data, bloco, indice),
                            _ja_postas())[:faixa.questoes]
    if not escolhidas:
        return None
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros={
            "quantidade": len(escolhidas),
            "rodada": RODADA,
            "faixa": composicao.identidade_da_faixa(data, bloco, indice, faixa),
            "nos": nos,
            "do_plano": faixa.questoes,
            "proprias": sum(1 for c in escolhidas if c.evidencia == evidencia.ALVO),
            "da_banca": sum(1 for c in escolhidas if c.evidencia == evidencia.COMPLEMENTAR),
        })
        s.add(simulado)
        s.flush()
        for ordem, candidata in enumerate(escolhidas, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id,
                                     questao_id=candidata.id, ordem=ordem))
    return simulado
