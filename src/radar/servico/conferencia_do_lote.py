"""A amostra das provas novas e as pendentes delas, na tela de conferencia (decisao 173).

A segunda leitura as cegas (decisao 171) conferiu sozinha a maior parte das
640 classificacoes de 17/10. Duas leituras do mesmo modelo podem errar
juntas: por isso eu confiro uma AMOSTRA do que ela conferiu, como na decisao
87, e confiro uma a uma as que ficaram pendentes. As regras:

- **o lote e uma lista de chaves** (`data/lotes_de_classificacao.json`), e nao
  a procedencia: a regra b da 171 trocou a procedencia das que foram para o no
  em comum, e o lote de 18/10 (decisao 172) usou a mesma da reanalise. Cada
  item guarda o no que o Claude Code conferiu (`no_conferido`): e contra ele
  que se mede o erro;
- **a amostra de cada grupo** (FEPESE, NC-UFPR e Selecon, Cebraspe, IESES) e a
  do que a segunda leitura decidiu sozinha - o mesmo no, o no em comum, e a
  pendente nas duas leituras -, na ordem do hash da chave, sempre a mesma, uma
  por questao (a IESES poe a mesma questao em varios cadernos). Os tamanhos
  (10, e mais 10) moram no config/amostra.yml;
- **a regra**: confiro as 10 primeiras. Nenhum erro, o grupo passa; 2 ou mais,
  volta; 1, confiro as 10 seguintes, e o grupo so passa se nao houver outro.
  Erro e o no que muda a faixa de treino (outro assunto ou outro subassunto),
  a pendente que tinha lugar no programa de 2019, e o contrario. Descer no
  mesmo ramo (do subassunto para o artigo), ou subir sem sair do subassunto,
  e ajuste: eu corrijo, e nao conta como erro;
- **a questao reservada para uma rodada que mede** (`composicao.reserva_das_que_medem`)
  nao entra na amostra: ela pula a reservada, e a tela diz quantas;
- **o "Responder no radar"** abre so aquela questao, como treino: a letra do
  gabarito so aparece depois de eu responder (decisao 148).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select

from radar import amostra as regua
from radar import config
from radar import conteudos as arvore
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import metricas

#: O lote da decisao 171: as provas novas de 17/10.
LOTE_DE_17_10 = "2026-10-17"

#: O nome da rodada do "Responder no radar" em `Simulado.filtros`.
RODADA = "conferencia"

#: O que a minha conferencia de um item da amostra foi.
CONFIRMADA, AJUSTE, ERRO = "confirmada", "ajuste", "erro"

#: Em que pe esta um grupo da amostra.
EM_ANDAMENTO, CONFIRA_MAIS, PASSA, VOLTA = "em andamento", "confira mais", "passa", "volta"

#: O que a segunda leitura decidiu sozinha (decisao 171): o mesmo no (regra
#: a), o no em comum (regra b) e a pendente nas duas leituras. E o universo da
#: amostra: a pendente entra porque "a pendente que tinha lugar no programa"
#: tambem e erro.
CONFERIDAS_PELO_CLAUDE_CODE = ("a", "b", "pendente nas duas")
#: As que esperam a minha conferencia uma a uma: as duas leituras discordaram
#: (regra c), ou a lei mudou depois da prova (o passo 2 da 171).
PENDENTES_DO_LOTE = ("c", "fora do treino")


def caminho_do_arquivo() -> Path:
    return config.diretorio_dados() / "lotes_de_classificacao.json"


@dataclass
class ItemDoLote:
    chave: str
    grupo: str
    categoria: str
    no_conferido: str | None = None
    primeira: str | None = None
    segunda: str | None = None
    confianca: str | None = None
    motivo: str | None = None


@dataclass
class Lote:
    id: str
    nome: str
    grupos: list[str]
    itens: list[ItemDoLote]

    def do_grupo(self, grupo: str) -> list[ItemDoLote]:
        return [i for i in self.itens if i.grupo == grupo]

    def item(self, chave: str) -> ItemDoLote | None:
        return next((i for i in self.itens if i.chave == chave), None)


def carregar(lote_id: str = LOTE_DE_17_10, caminho: Path | None = None) -> Lote | None:
    """O lote do arquivo, ou None quando o arquivo (ou o lote) nao existe."""
    arquivo = caminho or caminho_do_arquivo()
    if not arquivo.exists():
        return None
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    bruto = next((l for l in dados.get("lotes") or [] if l.get("id") == lote_id), None)
    if bruto is None:
        return None
    campos = ItemDoLote.__dataclass_fields__
    itens = [ItemDoLote(**{k: v for k, v in i.items() if k in campos}) for i in bruto["itens"]]
    return Lote(id=bruto["id"], nome=bruto.get("nome", bruto["id"]),
                grupos=list(bruto.get("grupos") or sorted({i.grupo for i in itens})),
                itens=itens)


# --- o que eu fiz com cada item ---------------------------------------------------

def conferida_por_mim(principal: Classificacao | None) -> bool:
    """A minha conferencia: a data, sem a marca de quem nao sou eu."""
    return (principal is not None and principal.conferida_em is not None
            and not principal.conferida_por)


def tipo_da_conferencia(no_conferido: str | None,
                        principal: Classificacao | None) -> str | None:
    """CONFIRMADA, AJUSTE ou ERRO - ou None, quando eu ainda nao conferi.

    `no_conferido` None e a pendente nas duas leituras. Erro e o que muda a
    faixa de treino: outro assunto, outro subassunto, outra materia; a
    pendente que eu classifico (tinha lugar no programa) e a classificada que
    eu deixo pendente. Descer no mesmo ramo - do assunto para o subassunto, do
    subassunto para o artigo - e ajuste, e subir tambem, se nao sair do
    subassunto (do artigo para ele)."""
    if not conferida_por_mim(principal):
        return None
    eu_deixei_pendente = principal.status == "pendente"
    if not no_conferido or eu_deixei_pendente:
        return CONFIRMADA if (not no_conferido and eu_deixei_pendente) else ERRO
    if principal.conteudo == no_conferido:
        return CONFIRMADA
    meu, dele = arvore.partes(principal.conteudo), arvore.partes(no_conferido)
    if principal.conteudo.startswith(no_conferido + arvore.SEPARADOR) and len(dele) >= 2:
        return AJUSTE
    if no_conferido.startswith(principal.conteudo + arvore.SEPARADOR) and len(meu) >= 3:
        return AJUSTE
    return ERRO


@dataclass
class Resultado:
    estado: str
    texto: str


def resultado_do_grupo(tipos: list[str | None], primeiras: int, mais: int) -> Resultado:
    """A regra da amostra sobre os tipos, na ordem da amostra.

    As `primeiras`: sem erro, passa; 2 ou mais, volta; 1, as `mais` seguintes
    decidem - o grupo so passa se nao houver outro."""
    primeiro_bloco = tipos[:primeiras]
    feitas = sum(1 for t in primeiro_bloco if t is not None)
    erros = sum(1 for t in primeiro_bloco if t == ERRO)
    if erros >= 2:
        return Resultado(VOLTA, f"{erros} erros nas {primeiras} primeiras: o grupo volta.")
    if feitas < len(primeiro_bloco):
        return Resultado(EM_ANDAMENTO, f"{feitas} de {len(primeiro_bloco)} conferidas.")
    if erros == 0:
        return Resultado(PASSA, f"Nenhum erro nas {len(primeiro_bloco)} primeiras: o grupo passa.")
    segundo_bloco = tipos[primeiras:primeiras + mais]
    if any(t == ERRO for t in segundo_bloco):
        return Resultado(VOLTA, "1 erro nas primeiras e outro nas seguintes: o grupo volta.")
    feitas_2 = sum(1 for t in segundo_bloco if t is not None)
    if feitas_2 < len(segundo_bloco):
        return Resultado(CONFIRA_MAIS, f"1 erro nas {primeiras} primeiras: confira as "
                                       f"{len(segundo_bloco)} seguintes ({feitas_2} conferidas).")
    return Resultado(PASSA, "1 erro nas primeiras e nenhum nas seguintes: o grupo passa.")


# --- a amostra --------------------------------------------------------------------

@dataclass
class GrupoDaAmostra:
    grupo: str
    #: As que o Claude Code conferiu no grupo (o universo da amostra).
    conferidas_pelo_claude_code: int
    #: As chaves da amostra que a tela mostra, na ordem (10, ou 20 quando 1 erro
    #: pede as seguintes).
    chaves: list[str] = field(default_factory=list)
    #: As que a amostra pulou por estarem reservadas para uma rodada que mede.
    fora_por_reserva: int = 0
    conferidas: int = 0
    ajustes: int = 0
    erros: int = 0
    resultado: Resultado | None = None

    @property
    def volta(self) -> bool:
        return self.resultado is not None and self.resultado.estado == VOLTA


def por_hash(chave: str) -> str:
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


def amostra(lote: Lote, principais: dict, reservadas: set[str],
            mesma_de: dict[str, str] | None = None,
            primeiras: int | None = None, mais: int | None = None) -> list[GrupoDaAmostra]:
    """A amostra de cada grupo do lote.

    `principais` e {chave: Classificacao principal}; `reservadas`, as chaves que
    uma rodada que mede ainda vai usar; `mesma_de`, {chave: identidade da
    questao em qualquer caderno} - uma por questao na amostra."""
    minimos = regua.carregar()
    primeiras = minimos.amostra_do_lote if primeiras is None else primeiras
    mais = minimos.amostra_do_lote_extra if mais is None else mais
    mesma_de = mesma_de or {}
    grupos = []
    for nome in lote.grupos:
        candidatos = [i for i in lote.do_grupo(nome)
                      if i.categoria in CONFERIDAS_PELO_CLAUDE_CODE]
        grupo = GrupoDaAmostra(grupo=nome, conferidas_pelo_claude_code=len(candidatos))
        vistas, pool = set(), []
        for item in sorted(candidatos, key=lambda i: por_hash(i.chave)):
            mesma = mesma_de.get(item.chave, item.chave)
            if mesma in vistas:
                continue
            vistas.add(mesma)
            if item.chave in reservadas:
                grupo.fora_por_reserva += 1
                continue
            pool.append(item)
            if len(pool) == primeiras + mais:
                break
        tipos = [tipo_da_conferencia(i.no_conferido, principais.get(i.chave)) for i in pool]
        grupo.resultado = resultado_do_grupo(tipos, primeiras, mais)
        mostra = primeiras + (mais if grupo.resultado.estado == CONFIRA_MAIS
                              or any(t is not None for t in tipos[primeiras:]) else 0)
        grupo.chaves = [i.chave for i in pool[:mostra]]
        visiveis = tipos[:mostra]
        grupo.conferidas = sum(1 for t in visiveis if t is not None)
        grupo.ajustes = sum(1 for t in visiveis if t == AJUSTE)
        grupo.erros = sum(1 for t in visiveis if t == ERRO)
        grupos.append(grupo)
    return grupos


# --- o que eu ja respondi, e o que esta guardado --------------------------------------

def chaves_respondidas() -> set[str]:
    """As chaves das questoes reais que eu ja respondi no radar."""
    from radar.servico.classificacoes import chave_de

    criar_tabelas()
    with sessao() as s:
        ids = set(metricas.ultimas_respostas_reais(s))
        if not ids:
            return set()
        return {chave_de(q) for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.id.in_(ids)))}


def reservadas(hoje: date | None = None) -> set[str]:
    """As chaves que uma rodada que mede ainda vai usar (decisao 167)."""
    from radar.servico import composicao
    from radar.servico import cronograma as diario

    return composicao.reserva_das_que_medem(hoje or diario.hoje_local()).chaves


# --- o "Responder no radar" --------------------------------------------------------

class QuestaoGuardada(ValueError):
    """A questao esta reservada para uma rodada que mede: nao se abre."""


def criar_rodada_da_questao(chave: str, hoje: date | None = None) -> Simulado | None:
    """Uma rodada so com esta questao, como treino: corrige na hora, e a letra
    aparece depois da resposta. Recusa a reservada; None sem a questao."""
    from radar.servico.classificacoes import chave_de

    if chave in reservadas(hoje):
        raise QuestaoGuardada("Esta questão está guardada para uma rodada que mede.")
    criar_tabelas()
    with sessao() as s:
        questao = next((q for q in s.scalars(select(QuestaoDeProva).order_by(QuestaoDeProva.id))
                        if chave_de(q) == chave), None)
        if questao is None:
            return None
        simulado = Simulado(filtros={"rodada": RODADA, "quantidade": 1, "chave": chave})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=questao.id, ordem=1))
    return simulado
