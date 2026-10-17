"""O caderno da Selecon: as colunas fora de ordem e o gabarito em fileiras.

As fixtures sao o texto real (como o pypdf o le) do caderno A da SEJUSP/MG
2021, Agente de Seguranca Penitenciario / Policial Penal: as paginas 5 a 7
(questoes 15 a 35, com a pagina 6 embaralhada pelas colunas) e a pagina 9
(44 a 50, com a Lei 14.695 no meio do texto), e o gabarito oficial inteiro.
"""
from pathlib import Path

import pytest

from radar import questoes_selecon

PASTA = Path(__file__).parent / "fixtures" / "selecon"
FAIXAS = questoes_selecon.faixas_do_config({
    "1-10": "Língua Portuguesa", "11-15": "Raciocínio Lógico", "16-20": "Informática",
    "21-25": "Direito Constitucional", "26-30": "Direito Penal",
    "31-40": "Direitos Humanos", "41-60": "Legislação Especial"})


@pytest.fixture
def gabarito():
    return questoes_selecon.ler_gabarito(
        (PASTA / "sejusp_mg_2021_gabarito_A.txt").read_text(encoding="utf-8"))


@pytest.fixture
def lidas(gabarito):
    texto = (PASTA / "sejusp_mg_2021_A.txt").read_text(encoding="utf-8")
    return questoes_selecon.dividir_em_questoes(texto, gabarito, FAIXAS)


def _questao(lidas, numero):
    return next(q for q in lidas if q.numero == numero)


def test_o_gabarito_le_as_duas_fileiras_e_a_anulada(gabarito):
    assert len(gabarito) == 60
    assert gabarito[1] == "c" and gabarito[30] == "b" and gabarito[60] == "b"
    assert gabarito[12] is None


def test_a_pagina_embaralhada_sai_em_ordem_e_inteira(lidas):
    assert [q.numero for q in lidas] == [*range(15, 36), *range(44, 51)]
    for questao in lidas:
        assert sorted(questao.alternativas) == list("abcd"), questao.numero


def test_o_numero_colado_e_o_numero_sem_espaco_viram_questao(lidas):
    """A 32 vem colada no fim da 31 ("politico32. A luz"); a Lei 14.695 do
    meio do texto nao vira questao."""
    assert _questao(lidas, 32).enunciado.startswith("À luz das Regras Mínimas da ONU")
    assert not _questao(lidas, 31).alternativas["d"].endswith("32.")
    assert all(q.numero != 14 for q in lidas)


def test_a_resposta_vem_do_gabarito(lidas):
    assert [(_questao(lidas, n).resposta) for n in (21, 26, 32, 47, 50)] == [
        "c", "a", "d", "c", "d"]
    assert _questao(lidas, 26).alternativas["a"] == "corrupção passiva privilegiada"


def test_a_materia_vem_da_faixa_da_capa(lidas):
    assert _questao(lidas, 23).materia == "Direito Constitucional"
    assert _questao(lidas, 28).materia == "Direito Penal"
    assert _questao(lidas, 32).materia == "Direitos Humanos"
    assert _questao(lidas, 47).materia == "Legislação Especial"


def test_a_anulada_do_gabarito_fica_marcada():
    texto = "12. Questão da anulada?\nA) um\nB) dois\nC) três\nD) quatro\n"
    (questao,) = questoes_selecon.dividir_em_questoes(texto, {12: None}, FAIXAS)
    assert questao.anulada and questao.resposta is None
