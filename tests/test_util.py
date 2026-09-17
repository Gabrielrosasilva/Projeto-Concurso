"""Conversao de fuso horario.

Estes testes existem por causa de um bug real: a CLI inteira quebrava no
Windows porque o fuso era carregado na importacao do modulo e o Windows nao
tem base de fusos no sistema. Os 18 testes da epoca passaram assim mesmo,
porque nenhum deles encostava neste arquivo.
"""
from datetime import datetime, timedelta, timezone

from radar.util import formatar_data, fuso_local, para_local


def test_o_fuso_carrega():
    assert fuso_local() is not None


def test_utc_vira_horario_de_florianopolis():
    utc = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    local = para_local(utc)

    # o Brasil nao tem mais horario de verao: UTC-3 o ano inteiro
    assert local.utcoffset() == timedelta(hours=-3)
    assert local.hour == 9


def test_data_sem_fuso_e_tratada_como_utc():
    local = para_local(datetime(2026, 9, 17, 12, 0))
    assert local.hour == 9


def test_virada_de_dia_usa_a_data_local():
    """Um concurso publicado 01:00 UTC saiu dia 16 aqui, nao dia 17."""
    assert formatar_data(datetime(2026, 9, 17, 1, 0, tzinfo=timezone.utc)) == "16/09/2026"


def test_sem_data():
    assert para_local(None) is None
    assert formatar_data(None) == "--"
    assert formatar_data(None, vazio="sem data") == "sem data"
