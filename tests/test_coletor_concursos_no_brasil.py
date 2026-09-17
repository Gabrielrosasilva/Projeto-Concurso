"""O parser entende o formato do feed?

Usa um XML fixo em arquivo, entao roda rapido, funciona sem rede e nao quebra
quando o site sai do ar.
"""
from pathlib import Path

import pytest

from radar.collectors.concursos_no_brasil import ConcursosNoBrasil

FIXTURE = Path(__file__).parent / "fixtures" / "concursos_no_brasil.xml"


@pytest.fixture
def itens(monkeypatch):
    coletor = ConcursosNoBrasil()

    class RespostaFalsa:
        text = FIXTURE.read_text(encoding="utf-8")

    monkeypatch.setattr(coletor, "get", lambda url: RespostaFalsa())
    return coletor.coletar()


def test_le_todos_os_itens(itens):
    assert len(itens) == 3


def test_extrai_uf_pela_url(itens):
    assert itens[0].uf == "SC"


def test_extrai_uf_pela_categoria_quando_a_url_nao_tem(itens):
    # este link nao segue o padrao /concursos/sc/ANO/, entao a UF precisa vir
    # da categoria "Santa Catarina"
    assert "/concursos/sc/" not in itens[1].url
    assert itens[1].uf == "SC"


def test_data_vem_com_fuso(itens):
    publicado = itens[0].publicado_em
    assert publicado.year == 2026
    assert publicado.tzinfo is not None


def test_resumo_sem_html_e_sem_rodape(itens):
    resumo = itens[0].resumo
    assert "<p>" not in resumo
    assert "apareceu primeiro" not in resumo
    assert "nivel superior" in resumo


def test_guarda_as_categorias_no_extra(itens):
    assert itens[0].extra["categorias"] == ["Santa Catarina"]
