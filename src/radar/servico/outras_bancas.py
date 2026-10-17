"""O treino com questoes reais de OUTRAS BANCAS, dentro do radar (decisao 166).

A FEPESE nao tem questao bastante em varios temas (a aplicacao da lei penal,
por exemplo), e o simulado da semana manda fazer questoes que eu nao acho no
Qconcursos. As provas de outras bancas - baixadas do site oficial de cada uma
- entram aqui: "sobre este assunto, responda esta questao", no radar.

O que vale, e por que:

- **a questao e de evidencia `fora`** (o `servico/evidencia.py`: toda banca
  que nao e a FEPESE), classificada no no da arvore pela chave, como as
  outras. O estoque daqui nao mistura com o da FEPESE: as reais da FEPESE
  ficam para a faixa de Portugues do radar (decisao 107) e para as rodadas que
  medem, que nao repetem questao (decisao 145);
- **o que eu respondo aqui mede o MEU acerto no no**: a resposta e de questao
  real, e entra no `metricas` e no `desempenho_por_conteudo` como as outras,
  com a origem ao lado. **E nunca entra no que a FEPESE cobra**: a incidencia,
  os padroes e a composicao so leem o alvo e o complementar aceito;
- **so questao com gabarito, sem anulada e com as alternativas inteiras**: a
  menor prova de multipla escolha do acervo tem quatro (a IESES, de a a d).
  Menos que isso e caderno mal lido - ou Certo/Errado, que so treina e ainda
  nao tem leitura (pendencia O, etapa B);
- **as nunca feitas saem primeiro**, como nas geradas (decisao 142): refazer a
  mesma questao mede memoria, e nao o assunto;
- **a mesma questao em outro caderno e uma so** (`mesma_questao`): a IESES
  embaralha as alternativas entre os cargos, e o PDF parte a palavra em lugar
  diferente em cada um ("senti do"). A chave da classificacao leva a letra e o
  espaco, e cada versao seria uma questao nova no treino.

A rodada guarda a faixa de onde saiu (`da_faixa`), e o "Fiz hoje" ja conta o
que eu respondi nela: a faixa avisa para nao anotar de novo.
"""
from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import select

from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import evidencia, metricas
from radar.servico.classificacoes import PENDENTE, chave_de

#: O nome da rodada em `Simulado.filtros`.
RODADA = "outras_bancas"

#: A menor prova de multipla escolha do acervo: a IESES, de a a d.
MINIMO_DE_ALTERNATIVAS = 4

#: O teto de uma rodada, o mesmo do treino de geradas.
MAXIMO_DA_RODADA = 30


@dataclass
class Candidata:
    """Uma questao real de outra banca, que pode entrar no treino."""

    id: int
    chave: str
    conteudo: str
    banca: str
    #: A mesma questao em qualquer caderno (`mesma_questao`).
    mesma: str


def _so_letras(texto: str | None) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", texto)


def mesma_questao(questao: QuestaoDeProva) -> str:
    """A identidade da questao em qualquer caderno da banca: o texto sem
    espaco, sem acento e sem pontuacao, e as alternativas sem a letra e em
    ordem. Duas versoes embaralhadas, ou com a palavra partida em outro lugar,
    dao o mesmo valor; duas questoes diferentes, nao."""
    partes = [_so_letras(questao.enunciado)] + sorted(
        _so_letras(texto) for texto in (questao.alternativas or {}).values())
    return hashlib.sha256("|".join(partes).encode()).hexdigest()[:32]


def _dentro(conteudo: str, nos: list[str]) -> bool:
    return any(conteudo == no or conteudo.startswith(no + arvore.SEPARADOR) for no in nos)


def serve(questao: QuestaoDeProva) -> bool:
    """A questao pode ser respondida e corrigida: tem gabarito entre as
    alternativas, nao foi anulada e tem as alternativas inteiras."""
    alternativas = questao.alternativas or {}
    return (not questao.anulada and questao.resposta is not None
            and questao.resposta in alternativas
            and len(alternativas) >= MINIMO_DE_ALTERNATIVAS)


def estoque(nos: list[str]) -> list[Candidata]:
    """As questoes de outras bancas classificadas DENTRO dos nos, uma por
    questao (`mesma_questao`), na ordem do id. Sem no, nada: o treino e
    sempre de um tema."""
    nos = [n for n in nos if n]
    if not nos:
        return []
    criar_tabelas()
    with sessao() as s:
        principais = {c.chave: c.conteudo for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True))
            .where(Classificacao.status != PENDENTE))}
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.evidencia == evidencia.FORA)
            .order_by(QuestaoDeProva.id)))

    saida, vistas = [], set()
    for q in questoes:
        chave = chave_de(q)
        conteudo = principais.get(chave)
        if not conteudo or not _dentro(conteudo, nos) or not serve(q):
            continue
        mesma = mesma_questao(q)
        if mesma in vistas:
            continue
        vistas.add(mesma)
        saida.append(Candidata(id=q.id, chave=chave, conteudo=conteudo,
                               banca=q.banca or "sem banca", mesma=mesma))
    return saida


def respondidas() -> set[str]:
    """As questoes de outras bancas que eu ja respondi, em qualquer rodada e
    em qualquer versao do caderno (`mesma_questao`)."""
    criar_tabelas()
    with sessao() as s:
        ids = set(metricas.ultimas_respostas_reais(s))
        if not ids:
            return set()
        return {mesma_questao(q) for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.id.in_(ids))
            .where(QuestaoDeProva.evidencia == evidencia.FORA))}


def escolher(candidatas: list[Candidata], feitas_antes: set[str], quantidade: int,
             sorteio: random.Random | None = None) -> list[Candidata]:
    """As nunca feitas primeiro, cada grupo embaralhado; no maximo `quantidade`."""
    sorteio = sorteio or random.Random()
    novas = [c for c in candidatas if c.mesma not in feitas_antes]
    feitas = [c for c in candidatas if c.mesma in feitas_antes]
    sorteio.shuffle(novas)
    sorteio.shuffle(feitas)
    return (novas + feitas)[:max(quantidade, 0)]


@dataclass
class OutrasBancasDaFaixa:
    """O que a tela Hoje mostra numa faixa: quantas questoes de outras bancas
    o tema tem, quantas eu ja fiz, e de quais bancas."""

    nos: list[str]
    no_acervo: int
    feitas: int
    bancas: list[str] = field(default_factory=list)
    #: O numero da faixa, para a rodada ja vir do tamanho dela.
    questoes_da_faixa: int | None = None

    @property
    def novas(self) -> int:
        return max(self.no_acervo - self.feitas, 0)

    @property
    def sugeridas(self) -> int:
        """Quantas a rodada traz se eu nao mudar: o numero da faixa, sem passar
        do que existe nem do teto."""
        quantas = self.questoes_da_faixa or 10
        return max(min(quantas, self.no_acervo, MAXIMO_DA_RODADA), 1)


def da_faixa(nos: list[str], questoes_da_faixa: int | None = None,
             feitas_antes: set[str] | None = None) -> OutrasBancasDaFaixa | None:
    """O resumo de uma faixa, ou None quando o tema nao tem questao de outra
    banca: a faixa nao ganha linha nenhuma - so ruido."""
    candidatas = estoque(nos)
    if not candidatas:
        return None
    if feitas_antes is None:
        feitas_antes = respondidas()
    return OutrasBancasDaFaixa(
        nos=list(nos), no_acervo=len(candidatas),
        feitas=sum(1 for c in candidatas if c.mesma in feitas_antes),
        bancas=sorted({c.banca for c in candidatas}),
        questoes_da_faixa=questoes_da_faixa)


def das_faixas(geradas_das_faixas: dict) -> dict:
    """{(bloco, indice): OutrasBancasDaFaixa} das faixas de treino do dia,
    pelos nos que a faixa ja diz (os das geradas, `fichas.onde_na_arvore`)."""
    com_nos = {chave: gf for chave, gf in (geradas_das_faixas or {}).items()
               if not gf.sem_no and gf.nos}
    if not com_nos:
        return {}
    feitas_antes = respondidas()
    saida = {}
    for chave, gf in com_nos.items():
        resumo = da_faixa([n.no for n in gf.nos], gf.questoes, feitas_antes)
        if resumo is not None:
            saida[chave] = resumo
    return saida


def criar_rodada(nos: list[str], quantidade: int, da_faixa_do_dia: dict | None = None,
                 sorteio: random.Random | None = None) -> Simulado | None:
    """A rodada de treino com questoes de outras bancas dos nos. None sem
    questao nenhuma (a tela diz que o tema ainda nao tem)."""
    nos = [n for n in nos if n]
    candidatas = estoque(nos)
    if not candidatas:
        return None
    quantidade = max(1, min(quantidade, MAXIMO_DA_RODADA))
    escolhidas = escolher(candidatas, respondidas(), quantidade, sorteio)
    filtros = {
        "quantidade": len(escolhidas),
        "rodada": RODADA,
        "nos": nos,
        "bancas": sorted({c.banca for c in escolhidas}),
    }
    if da_faixa_do_dia:
        # A mesma chave das rodadas de geradas abertas pela faixa: e por ela
        # que o `metricas.no_radar_por_faixa` acha estas respostas.
        filtros["da_faixa"] = da_faixa_do_dia
    criar_tabelas()
    with sessao() as s:
        simulado = Simulado(filtros=filtros)
        s.add(simulado)
        s.flush()
        for ordem, candidata in enumerate(escolhidas, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id,
                                     questao_id=candidata.id, ordem=ordem))
    return simulado
