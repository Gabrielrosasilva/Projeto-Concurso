"""De que evidencia e cada prova: alvo, complementar ou fora. UMA regra.

Antes havia duas: o Meu foco (e a geracao, os cartoes e a auditoria) pedia o
cargo E o estado; o simulado pedia so o cargo. No acervo de hoje as duas dao
as mesmas 170 questoes, mas so por sorte - uma prova de Policia Penal do
Parana entraria numa e nao na outra. E o Socioeducativo 2016 era "reforco"
numa tela e "da banca" na outra.

A regra (secao 4 do pedido):

- **alvo**: a prova do cargo do alvo principal E do estado dele
  (config/alvo.yml). E a Policia Penal / Agente Penitenciario de SC: 2013 e
  2019 no acervo de hoje;
- **complementar**: outra prova de uma banca do alvo (a FEPESE). O
  Socioeducativo 2016 cai aqui;
- **fora**: o resto (a IESES). Nao entra em estatistica da FEPESE.

Os tres nunca se somam (regra inviolavel 1). A coluna `questoes.evidencia` e
a fotografia desta regra, para consulta e estatistica; quem precisa da
resposta na hora pergunta a `por_prova`, que e a mesma conta.
"""
from collections import Counter

from sqlalchemy import func, select, update

from radar import alvo
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, QuestaoDeProva
from radar.regioes import normalizar

ALVO = "alvo"
COMPLEMENTAR = "complementar"
FORA = "fora"
EVIDENCIAS = (ALVO, COMPLEMENTAR, FORA)


def da_prova(cargo: str | None, banca: str | None, uf: str | None,
             titulo: str | None = None, resumo: str | None = None) -> str:
    """A evidencia de uma prova, pelo cargo, pela banca e pelo concurso dela.

    O estado vem do concurso que originou a prova: sem ele nao ha como provar
    que e de SC, e a prova nao vira alvo por palpite - a mesma regra do anel
    de distancia.
    """
    # `sinonimos_do_cargo` ja aplica a lista `exclui` do alvo.yml: "Policial
    # Penal Federal" nao e o meu cargo.
    if (alvo.sinonimos_do_cargo(cargo or "")
            and alvo.e_do_estado_do_principal(uf, titulo, resumo)):
        return ALVO
    bancas = [normalizar(b) for b in alvo.bancas_do_principal()]
    if any(b and b in normalizar(banca or "") for b in bancas):
        return COMPLEMENTAR
    return FORA


def por_prova(s) -> dict[str, str]:
    """{endereco do caderno: evidencia}, de todas as provas do acervo.

    A pergunta e feita uma vez por prova (~200), e nao por questao (~8 mil).
    """
    linhas = s.execute(
        select(QuestaoDeProva.prova_url, QuestaoDeProva.cargo, QuestaoDeProva.banca,
               Concurso.uf, Concurso.titulo, Concurso.resumo)
        .join(Concurso, Concurso.url == QuestaoDeProva.concurso_url, isouter=True)
        .distinct()
    ).all()
    resultado: dict[str, str] = {}
    for url, cargo, banca, uf, titulo, resumo in linhas:
        evidencia = da_prova(cargo, banca, uf, titulo, resumo)
        # A mesma prova em duas linhas (o distinct separa por cargo ou banca
        # diferente) fica com a evidencia mais forte: alvo > complementar.
        atual = resultado.get(url)
        if atual is None or EVIDENCIAS.index(evidencia) < EVIDENCIAS.index(atual):
            resultado[url] = evidencia
    return resultado


def provas(s, evidencia: str) -> set[str]:
    """Os cadernos de uma evidencia."""
    return {url for url, e in por_prova(s).items() if e == evidencia}


def atualizar() -> Counter:
    """Grava a evidencia em toda questao. Devolve {evidencia: questoes}.

    Roda na migracao, depois de ler os cadernos (`radar extrair`) e no
    `importar`/`sincronizar`, porque o concurso de uma prova pode chegar
    depois dela - e e ele que diz o estado.
    """
    criar_tabelas()
    contagem: Counter = Counter()
    with sessao() as s:
        por_url = por_prova(s)
        for evidencia in EVIDENCIAS:
            urls = [u for u, e in por_url.items() if e == evidencia]
            if not urls:
                continue
            s.execute(update(QuestaoDeProva)
                      .where(QuestaoDeProva.prova_url.in_(urls))
                      .values(evidencia=evidencia))
        for evidencia, quantas in s.execute(
                select(QuestaoDeProva.evidencia, func.count())
                .group_by(QuestaoDeProva.evidencia)):
            contagem[evidencia] = quantas
    return contagem
