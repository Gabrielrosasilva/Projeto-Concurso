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
from radar.origem import AUTOMATICO, TENDENCIA
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


def _este_ano() -> int:
    """O ano de hoje, num lugar so: e o que o teste troca para fingir a data."""
    return date.today().year


def _anos(n: int) -> str:
    return "1 ano" if n == 1 else f"{n} anos"


@dataclass
class PrevisaoDeAbertura:
    #: Toda data desta tela e previsao, e nao fato.
    origem = TENDENCIA

    municipio: str
    anos: list[int]
    ultimo_ano: int
    proximo_previsto: int
    situacao: str            # atrasado | esperado | em_dia
    motivo: str
    #: O ano previsto ja passou. Pode acontecer dentro da folga ("esperado"),
    #: e ai a tela nao pode dizer "previsto para" um ano que ja foi.
    vencido: bool = False
    #: O que a tela escreve ao lado do municipio.
    quando: str = ""

    @property
    def anos_parado(self) -> int:
        return _este_ano() - self.ultimo_ano


def _prever(municipio: str, anos: set[int]) -> PrevisaoDeAbertura:
    """Quando o proximo concurso deste municipio deve sair.

    Com dois ou mais concursos no historico, vale o RITMO do proprio orgao: se
    ele abre a cada tres anos, a conta e essa. Com um so, vale a validade legal
    de 4 anos - nao da para tirar ritmo de um ponto.
    """
    ordenados = sorted(anos)
    ultimo = ordenados[-1]
    este_ano = _este_ano()

    if len(ordenados) >= 2:
        vaos = [b - a for a, b in zip(ordenados, ordenados[1:]) if b > a]
        # Mediana, e nao media: um unico buraco de cobertura no meio do
        # historico puxa a media inteira e nao mexe na mediana.
        bruto = round(median(vaos)) if vaos else VALIDADE_MAXIMA
        intervalo = min(VALIDADE_MAXIMA, max(VALIDADE_MINIMA, bruto))
        base = (f"{len(ordenados)} concursos conhecidos ({ordenados[0]} a "
                f"{ultimo}), um a cada {_anos(intervalo)}")
    else:
        intervalo = VALIDADE_MAXIMA
        base = f"um único concurso conhecido ({ultimo}), sem ritmo para medir"

    previsto = ultimo + intervalo
    if este_ano > previsto + FOLGA:
        situacao = "atrasado"
        # Atrasado e passar da folga, entao aqui sao sempre 2 anos ou mais.
        conclusao = f"passaram {_anos(este_ano - previsto)} do previsto"
    elif este_ano >= previsto - FOLGA:
        situacao = "esperado"
        conclusao = "é a janela de agora"
    else:
        situacao = "em_dia"
        conclusao = f"o próximo só em {previsto}"

    parado = este_ano - ultimo
    ultimo_foi = "este ano" if parado == 0 else f"há {_anos(parado)}"

    # A conta nao muda; muda como ela aparece. Ano previsto que ja passou e
    # atraso, mesmo dentro da folga: "previsto para 2025" lido em 2026 soa
    # como algo que ainda vai acontecer.
    vencido = previsto < este_ano
    if vencido:
        quando = f"Atrasado: era esperado em {previsto}"
    elif situacao == "em_dia":
        quando = f"Próximo por volta de {previsto}"
    else:
        quando = f"Previsto para {previsto}"

    return PrevisaoDeAbertura(
        municipio=municipio,
        anos=ordenados,
        ultimo_ano=ultimo,
        proximo_previsto=previsto,
        situacao=situacao,
        motivo=f"{base}. O último foi {ultimo_foi}, {conclusao}.",
        vencido=vencido,
        quando=quando,
    )


def previsao_de_abertura(
    aneis: tuple[str, ...] = ("nucleo", "proximo"),
) -> list[PrevisaoDeAbertura]:
    """Municipios perto de casa, do mais atrasado para o menos.

    Cuidado com o que isto NAO sabe: o historico so tem o que as fontes
    coletadas publicaram - `cobertura_do_historico` diz quais anos cada uma
    cobre. Municipio que contratou banca fora delas tem concurso que nao esta
    aqui, e vai aparecer mais atrasado do que e.
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
    # Atrasado primeiro, e dentro dele o que esta parado ha mais tempo. Na
    # janela de agora, o que ja passou do ano previsto vem no topo.
    ordem = {"atrasado": 0, "esperado": 1, "em_dia": 2}
    previsoes.sort(key=lambda p: (ordem[p.situacao], not p.vencido, -p.anos_parado))
    return previsoes


@dataclass
class Cobertura:
    """De que anos uma fonte tem concurso no banco."""
    origem = AUTOMATICO


    fonte: str
    primeiro_ano: int
    ultimo_ano: int
    concursos: int


def cobertura_do_historico() -> list[Cobertura]:
    """Quais anos cada fonte cobre, contado do banco.

    Existe porque a tela de previsao dizia "FEPESE (2006 a 2026)" e "feed (so
    2026)" escrito a mao, e texto assim envelhece calado na primeira coleta.
    Aqui o intervalo e o que o banco tem hoje.
    """
    criar_tabelas()
    with sessao() as s:
        concursos = list(s.scalars(
            select(Concurso).where(Concurso.tipo != "noticia")
        ))

    anos_por_fonte: dict[str, list[int]] = {}
    for concurso in concursos:
        ano = _ano_do_concurso(concurso)
        if ano:
            anos_por_fonte.setdefault(concurso.fonte or "?", []).append(ano)

    return sorted(
        (Cobertura(fonte, min(anos), max(anos), len(anos))
         for fonte, anos in anos_por_fonte.items()),
        key=lambda c: -c.concursos,
    )
