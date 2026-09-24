"""Quando aquele municipio costuma abrir concurso de novo.

E a unica parte do radar que olha para a frente, e por isso a que mais precisa
se conter. A conta e simples de proposito: o intervalo tipico entre as edicoes
que ja aconteceram, contado do ano da ultima. Municipio com uma edicao so nao
tem intervalo nenhum, e ai a resposta e que nao da para prever.

Nada aqui e promessa. A Constituicao da ao concurso validade de ate 2 anos,
prorrogavel uma vez, e e disso que sai a janela - nao de uma previsao que o
radar tenha como confirmar.
"""
from dataclasses import dataclass
from datetime import date
from statistics import median

from sqlalchemy import select

from radar.db import criar_tabelas, sessao
from radar.models import Concurso
from radar.servico.comum import ano_do_concurso as _ano_do_concurso


# A Constituicao da ao concurso validade de ate 2 anos, prorrogavel uma vez por
# igual periodo. Isso da o chao e o teto da previsao: antes de 2 anos o orgao
# ainda tem candidato aprovado na fila, e passados 4 quem precisa de gente tem
# de abrir outro. O historico so escolhe DENTRO dessa faixa.
#
# Sem a faixa, buraco de cobertura virava previsao absurda: de Tubarao eu so
# conheco 2011 e 2026, e a conta crua dizia "um a cada 15 anos, proximo em
# 2041". O buraco e o que eu nao coletei, nao concurso que deixou de existir.
VALIDADE_MINIMA = 2
VALIDADE_MAXIMA = 4

# Anos de folga aceitos antes de chamar de atrasado. Concurso escorrega:
# licitacao da banca, orcamento, ano eleitoral.
FOLGA = 1


@dataclass
class PrevisaoDeAbertura:
    municipio: str
    anos: list[int]
    ultimo_ano: int
    proximo_previsto: int
    situacao: str            # atrasado | esperado | em_dia
    motivo: str

    @property
    def anos_parado(self) -> int:
        return date.today().year - self.ultimo_ano


def _prever(municipio: str, anos: set[int]) -> PrevisaoDeAbertura:
    """Quando o proximo concurso deste municipio deve sair.

    Com dois ou mais concursos no historico, vale o RITMO do proprio orgao: se
    ele abre a cada tres anos, a conta e essa. Com um so, vale a validade legal
    de 4 anos - nao da para tirar ritmo de um ponto.
    """
    ordenados = sorted(anos)
    ultimo = ordenados[-1]
    este_ano = date.today().year

    if len(ordenados) >= 2:
        vaos = [b - a for a, b in zip(ordenados, ordenados[1:]) if b > a]
        # Mediana, e nao media: um unico buraco de cobertura no meio do
        # historico puxa a media inteira e nao mexe na mediana.
        bruto = round(median(vaos)) if vaos else VALIDADE_MAXIMA
        intervalo = min(VALIDADE_MAXIMA, max(VALIDADE_MINIMA, bruto))
        base = (f"{len(ordenados)} concursos conhecidos ({ordenados[0]} a "
                f"{ultimo}), um a cada {intervalo} ano(s)")
    else:
        intervalo = VALIDADE_MAXIMA
        base = f"um único concurso conhecido ({ultimo}), sem ritmo para medir"

    previsto = ultimo + intervalo
    if este_ano > previsto + FOLGA:
        situacao = "atrasado"
        conclusao = f"passou {este_ano - previsto} ano(s) do previsto"
    elif este_ano >= previsto - FOLGA:
        situacao = "esperado"
        conclusao = "e a janela de agora"
    else:
        situacao = "em_dia"
        conclusao = f"so em {previsto}"

    return PrevisaoDeAbertura(
        municipio=municipio,
        anos=ordenados,
        ultimo_ano=ultimo,
        proximo_previsto=previsto,
        situacao=situacao,
        motivo=f"{base}. O último foi há {este_ano - ultimo} ano(s), {conclusao}.",
    )


def previsao_de_abertura(
    aneis: tuple[str, ...] = ("nucleo", "proximo"),
) -> list[PrevisaoDeAbertura]:
    """Municipios perto de casa, do mais atrasado para o menos.

    Cuidado com o que isto NAO sabe: o historico vem da FEPESE (2006 a 2026) e
    do feed (so 2026). Municipio que contratou outra banca entre 2021 e 2025
    tem concurso que nao esta aqui, e vai aparecer mais atrasado do que e.
    """
    criar_tabelas()
    with sessao() as s:
        concursos = list(s.scalars(
            select(Concurso)
            .where(Concurso.relevancia.in_(aneis))
            .where(Concurso.tipo != "noticia")
            .where(Concurso.municipio.is_not(None))
        ))

    anos_por_municipio: dict[str, set[int]] = {}
    for concurso in concursos:
        ano = _ano_do_concurso(concurso)
        if ano:
            anos_por_municipio.setdefault(concurso.municipio, set()).add(ano)

    previsoes = [_prever(m, anos) for m, anos in anos_por_municipio.items()]
    # Atrasado primeiro, e dentro dele o que esta parado ha mais tempo.
    ordem = {"atrasado": 0, "esperado": 1, "em_dia": 2}
    previsoes.sort(key=lambda p: (ordem[p.situacao], -p.anos_parado))
    return previsoes
