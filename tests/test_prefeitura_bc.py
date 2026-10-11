"""Fonte 6: as noticias da Prefeitura de Balneario Camboriu.

A fixture e a resposta real da busca por "concurso" no titulo (10/10/2026):
11 noticias de 03/2025 a 09/2026, e so uma de concurso publico - o anuncio do
concurso da Guarda Municipal, de 04/08/2026.
"""
import json
from pathlib import Path

import pytest
import requests

from radar.collectors import prefeitura_bc

FIXTURE = Path(__file__).parent / "fixtures" / "prefeitura_bc" / "noticias_concurso.json"


@pytest.mark.parametrize("titulo", [
    "Balneário Camboriú anuncia novo concurso para Guarda Municipal",
    "Prefeitura abre concurso público com 40 vagas",          # escrito para o teste
])
def test_titulo_de_concurso_publico(titulo):
    assert prefeitura_bc.e_concurso_publico(titulo)


@pytest.mark.parametrize("titulo", [
    "Alunos do Programa Transitar são premiados no Concurso Educação para o Trânsito 2026",
    "Conselho Tutelar e Secretaria de Educação promovem concurso de desenho para "
    "estudantes da rede municipal",
    "Aluna da Rede Municipal de BC vence concurso de oratória",
    "Balneário Camboriú recebe Concurso Brasileiro de Cervejas e premiação das melhores do país",
])
def test_concurso_que_nao_e_publico(titulo):
    assert not prefeitura_bc.e_concurso_publico(titulo)


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

    monkeypatch.setattr(prefeitura_bc.PrefeituraBc, "get", get_falso)
    c = prefeitura_bc.PrefeituraBc()
    c.pedidos = pedidos
    return c


def test_das_onze_so_entra_a_da_guarda(coletor):
    itens = coletor.coletar()
    assert [i.url for i in itens] == ["https://www.bc.sc.gov.br/noticia/43608"]
    assert coletor.pedidos == [prefeitura_bc.API]


def test_os_campos(coletor):
    (item,) = coletor.coletar()

    assert item.titulo == "Balneário Camboriú anuncia novo concurso para Guarda Municipal"
    assert item.resumo == "Projeto de lei amplia 90 vagas para a corporação"
    assert item.municipio == "Balneário Camboriú"
    assert item.uf == "SC"
    assert item.orgao == "Prefeitura de Balneário Camboriú"
    assert item.banca is None
    assert item.situacao == "desconhecida"
    assert item.tipo is None                     # quem decide e o classificador
    data = item.publicado_em
    assert (data.year, data.month, data.day, data.hour, data.minute) == (2026, 8, 4, 11, 54)
    assert item.extra == {"categoria": "Segurança Pública", "news_id": 43608}


def test_toda_noticia_e_de_sc(coletor):
    """A fonte e a propria prefeitura: nao ha item de outro estado. O que fica
    de fora e o concurso que nao e publico."""
    assert {i.uf for i in coletor.coletar()} == {"SC"}


def test_cai_no_cartao_da_guarda_de_bc(banco_temporario, coletor):
    from radar import acompanhamentos as carreiras
    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        for item in coletor.coletar():
            servico._gravar(s, item, fonte="prefeitura_bc")
    with sessao() as s:
        concurso = s.query(Concurso).one()
        assert concurso.relevancia == "proximo"
        assert concurso.alvo == "secundario" and concurso.alvo_prioritario
        assert [c.nome for c in carreiras.de_quais(concurso)] == [
            "Guarda Municipal de Balneário Camboriú"
        ]


def test_pagina_vazia(monkeypatch):
    monkeypatch.setattr(prefeitura_bc.PrefeituraBc, "get",
                        lambda self, url: _Resposta('{"paginacao": {}, "noticias": []}'))
    assert prefeitura_bc.PrefeituraBc().coletar() == []


def test_fonte_fora_do_ar_sobe_o_erro(monkeypatch):
    def get_fora(self, url):
        raise requests.ConnectionError("fora do ar")

    monkeypatch.setattr(prefeitura_bc.PrefeituraBc, "get", get_fora)
    with pytest.raises(requests.ConnectionError):
        prefeitura_bc.PrefeituraBc().coletar()


def test_data_estranha_vira_nada():
    assert prefeitura_bc._data("ontem") is None
    assert prefeitura_bc._data(None) is None


def test_esta_entre_os_coletores():
    from radar.servico.coleta import COLETORES
    assert prefeitura_bc.PrefeituraBc in COLETORES
