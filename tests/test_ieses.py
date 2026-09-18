"""Fonte 3: IESES, pela API JSON da listagem de projetos dela.

A fixture e a resposta real da API, com 5 projetos escolhidos para cobrir os
casos que importam: prefeitura (tem municipio), orgao estadual (nao tem),
processo seletivo, concurso publico e um de fora de SC.
"""
import json
from pathlib import Path

import pytest

from radar.collectors import ieses

FIXTURE = Path(__file__).parent / "fixtures" / "ieses_projetos.json"


class _RespostaFalsa:
    def __init__(self, dados):
        self._dados = dados

    def json(self):
        return self._dados


@pytest.fixture
def coletor(monkeypatch):
    """Um coletor que le a fixture em vez de ir a internet."""
    dados = json.loads(FIXTURE.read_text(encoding="utf-8"))
    chamadas = []

    def get_falso(self, url, **kwargs):
        chamadas.append(url)
        # a segunda pagina vem vazia, como a API faz quando acaba
        if "offset=0" in url:
            return _RespostaFalsa(dados)
        return _RespostaFalsa({"projetos": []})

    monkeypatch.setattr(ieses.Ieses, "get", get_falso)
    c = ieses.Ieses()
    c.chamadas = chamadas
    return c


# --- o municipio ------------------------------------------------------------

def test_prefeitura_tem_municipio():
    assert ieses.extrair_municipio("PREFEITURA MUNICIPAL DE BIGUAÇU") == "BIGUACU"


def test_camara_tambem():
    assert ieses.extrair_municipio("Câmara Municipal de Gaspar") == "Gaspar"


def test_orgao_que_nao_e_municipal_nao_tem_municipio():
    """SCGAS, tribunal e conselho nao trazem municipio no nome. Chutar um seria
    pior que nao ter."""
    for entidade in (
        "SCGÁS - Companhia de Gás de Santa Catarina",
        "TRIBUNAL DE JUSTIÇA DO ESTADO DO AMAZONAS",
        "Conselho Regional de Contabilidade",
    ):
        assert ieses.extrair_municipio(entidade) is None


# --- o tipo -----------------------------------------------------------------

def test_tipo_vem_do_evento_que_a_banca_escreveu():
    assert ieses.detectar_tipo("PROCESSO SELETIVO PÚBLICO – EDITAL 001") == "seletivo"
    assert ieses.detectar_tipo("Concurso Público - Edital 001/2026") == "concurso"


def test_evento_vazio_fica_como_concurso():
    """A IESES so publica concurso e seletivo: na duvida, o mais comum."""
    assert ieses.detectar_tipo("") == "concurso"


# --- a data -----------------------------------------------------------------

def test_data_no_formato_da_banca():
    data = ieses._data("10/08/2026 09:00:00")

    assert (data.year, data.month, data.day) == (2026, 8, 10)
    assert data.tzinfo is not None, "data sem fuso quebra a comparacao depois"


def test_data_estranha_nao_derruba_a_coleta():
    assert ieses._data("sem data") is None
    assert ieses._data(None) is None


# --- a coleta ---------------------------------------------------------------

def test_coleta_todos_os_projetos(coletor):
    itens = coletor.coletar()

    assert len(itens) == 5


def test_para_de_pedir_quando_a_pagina_vem_curta(coletor):
    """5 projetos numa pagina de 50: nao ha segunda pagina para pedir."""
    coletor.coletar()

    assert len(coletor.chamadas) == 1


def test_o_item_traz_a_banca_preenchida(coletor):
    """A banca ja e conhecida: nao precisa adivinhar lendo a pagina."""
    assert all(item.banca == "IESES" for item in coletor.coletar())


def test_o_titulo_comeca_com_o_ano(coletor):
    """A previsao de abertura tira o ano do titulo, como faz com a FEPESE."""
    de_biguacu = next(i for i in coletor.coletar() if "BIGUA" in i.titulo)

    assert de_biguacu.titulo.startswith("2024 - ")


def test_o_item_de_prefeitura_traz_municipio(coletor):
    de_biguacu = next(i for i in coletor.coletar() if "BIGUA" in i.titulo)

    assert de_biguacu.municipio == "BIGUACU"


def test_uf_nao_e_afirmada(coletor):
    """A IESES e de Florianopolis mas faz concurso fora - tribunal do Amazonas,
    gas do Mato Grosso do Sul. Afirmar SC mandaria esses para o anel errado."""
    assert all(item.uf is None for item in coletor.coletar())


def test_a_url_e_o_hotsite_do_concurso(coletor):
    """E dali que o acervo tira edital, prova e gabarito."""
    assert all(item.url.startswith("https://") for item in coletor.coletar())


def test_guarda_a_pasta_do_cdn(coletor):
    """A pasta e o que monta o endereco dos PDFs no CDN da banca."""
    de_biguacu = next(i for i in coletor.coletar() if "BIGUA" in i.titulo)

    assert de_biguacu.extra["pasta"]


def test_registro_sem_url_e_descartado(coletor, monkeypatch):
    assert coletor._para_item({"entidade": "Prefeitura de X"}) is None
    assert coletor._para_item({"url": "https://x.test"}) is None
