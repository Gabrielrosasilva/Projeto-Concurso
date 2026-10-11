"""Fonte 7: os editais da SEJURI, pela API REST do WordPress dela.

A fixture e a resposta real de 11/10/2026 das categorias "Concurso Publico" e
"Processo Seletivo": 16 posts, os editais da carreira (2006 a 2022) e os
processos seletivos simplificados de 2024 a 2026.
"""
import json
from datetime import date
from pathlib import Path

import pytest
import requests

from radar.collectors import sejuri

FIXTURE = Path(__file__).parent / "fixtures" / "sejuri" / "posts.json"


@pytest.mark.parametrize("titulo,ano", [
    ("CONCURSO PÚBLICO EDITAL 001/SAP/2019 – AGENTE PENITENCIÁRIO", 2019),
    ("CONCURSO PUBLICO – EDITAL Nº 001/SEA-SSP/2006", 2006),
    ("PROCESSO SELETIVO SIMPLIFICADO EDITAL Nº 006/2026", 2026),
    ("Cronograma do curso", None),
])
def test_o_ano_do_edital(titulo, ano):
    assert sejuri.ano_do_edital(titulo) == ano


class _Resposta:
    def __init__(self, texto: str):
        self.text = texto

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def coletor(monkeypatch):
    pedidos = []

    def get_falso(self, url):
        pedidos.append(url)
        return _Resposta(FIXTURE.read_text(encoding="utf-8"))

    monkeypatch.setattr(sejuri.Sejuri, "get", get_falso)
    c = sejuri.Sejuri()
    c.pedidos = pedidos
    return c


def _por_post(itens) -> dict:
    return {i.extra["post_id"]: i for i in itens}


def _do_ano(itens, trecho):
    return next(i for i in itens if trecho in i.titulo)


def test_um_pedido_traz_os_dezesseis(coletor):
    itens = coletor.coletar()
    assert len(itens) == 16
    assert coletor.pedidos == [sejuri.API]


def test_os_campos_do_concurso(coletor):
    item = _do_ano(coletor.coletar(), "001/SAP/2019")

    assert item.titulo == ("2019 - Secretaria de Estado de Justiça e Reintegração Social - "
                           "CONCURSO PÚBLICO EDITAL 001/SAP/2019 – AGENTE PENITENCIÁRIO")
    assert item.url.startswith("https://www.sejuri.sc.gov.br/")
    assert item.tipo == "concurso"
    assert item.uf == "SC"
    assert item.municipio is None
    assert item.situacao == "desconhecida"
    assert (item.publicado_em.year, item.publicado_em.month, item.publicado_em.day) == (2019, 10, 9)
    assert item.resumo.startswith("O SECRETÁRIO DE ESTADO DA ADMINISTRAÇÃO PRISIONAL")
    assert 43 in item.extra["categorias"]


def test_o_processo_seletivo_e_seletivo(coletor):
    item = _do_ano(coletor.coletar(), "Nº 006/2026")
    assert item.tipo == "seletivo"
    assert item.titulo.startswith("2026 - Secretaria de Estado de Justiça e Reintegração Social - ")


def test_quem_separa_o_meu_concurso_e_o_alvo_yml(coletor):
    """O coletor traz o seletivo e o socioeducativo; o alvo.yml e que nao os
    marca como o alvo principal (decisao do pedido: nao duplicar)."""
    from radar.classificador import classificar

    itens = coletor.coletar()
    assert classificar(_do_ano(itens, "001/SAP/2019")).alvo == "principal"
    assert classificar(_do_ano(itens, "Nº 006/2026")).alvo is None
    assert classificar(_do_ano(itens, "001/SJC/2016")).alvo is None   # socioeducativo


def test_o_post_republicado_continua_da_edicao_de_2022(coletor):
    """Publicado em 27/01/2025, o edital e de 2022: o ano na frente e o que o
    cartao usa para nao toma-lo pela edicao de agora."""
    from radar.models import Concurso
    from radar.servico.acompanhamentos import _edicao_antiga

    item = _do_ano(coletor.coletar(), "001/SAP/2022")
    assert item.publicado_em.year == 2025
    assert _edicao_antiga(Concurso(titulo=item.titulo), date(2026, 10, 11))


def test_todo_item_e_de_sc(coletor):
    """A fonte e a propria secretaria: nao ha item de outro estado."""
    assert {i.uf for i in coletor.coletar()} == {"SC"}


def test_pagina_vazia(monkeypatch):
    monkeypatch.setattr(sejuri.Sejuri, "get", lambda self, url: _Resposta("[]"))
    assert sejuri.Sejuri().coletar() == []


def test_fonte_fora_do_ar_sobe_o_erro(monkeypatch):
    def get_fora(self, url):
        raise requests.ConnectionError("fora do ar")

    monkeypatch.setattr(sejuri.Sejuri, "get", get_fora)
    with pytest.raises(requests.ConnectionError):
        sejuri.Sejuri().coletar()


def test_esta_entre_os_coletores():
    from radar.servico.coleta import COLETORES
    assert sejuri.Sejuri in COLETORES
