"""Fonte 8: o IDIB, pela API REST do WordPress dela.

A fixture e um recorte da resposta real de 11/10/2026 (categorias Inscricoes
Abertas e Em andamento): na pagina 1, um titulo de cada jeito que o IDIB
escreve - a sigla com barra, com hifen, com travessao, o estado por extenso,
nenhum estado, e os dois concursos do CBMSC; a pagina 2 e a real, inteira.
"""
import json
from pathlib import Path

import pytest
import requests

from radar.collectors import idib

PASTA = Path(__file__).parent / "fixtures" / "idib"


@pytest.mark.parametrize("titulo,uf", [
    ("PREFEITURA MUNICIPAL DE ITAREMA/CE EDITAL Nº 01/2026, DE 28 DE SETEMBRO DE 2026", "CE"),
    ("CONCURSO PÚBLICO PREFEITURA MUNICIPAL DE ARAGUAÍNA-TO EDITAL 01/2026", "TO"),
    ("CONCURSO PÚBLICO PREFEITURA MUNICIPAL DE NÍSIA FLORESTA – RN EDITAL Nº 02/2026", "RN"),
    ("Polícia Militar do Espírito Santo", "ES"),
    ("Prefeitura de Seabra – BA", "BA"),
    # O "SC" de CBMSC esta grudado na sigla, e "DP" nao e estado: sem UF.
    ("CONCURSO PÚBLICO PARA FORMAÇÃO DE OFICIAIS EDITAL 002-2026/DP/CBMSC – CFO", None),
    ("Prefeitura de Colinas do TO", None),
])
def test_a_uf_que_o_titulo_escreve(titulo, uf):
    assert idib.extrair_uf(titulo) == uf


@pytest.mark.parametrize("titulo,municipio", [
    ("PREFEITURA MUNICIPAL DE ITAREMA/CE EDITAL Nº 01/2026", "ITAREMA"),
    ("CONCURSO PÚBLICO PREFEITURA MUNICIPAL DE SENA MADUREIRA EDT. Nº01/2025 – SEC. MUN", "SENA MADUREIRA"),
    ("CÂMARA MUNICIPAL DE RIO BRANCO/AC – CONCURSO PÚBLICO PARA O CARGO DE PROCURADOR", "RIO BRANCO"),
    ("CONCURSO PÚBLICO PARA FORMAÇÃO DE PRAÇAS EDITAL 001-2026/DP/CBMSC – CFP", None),
])
def test_o_municipio(titulo, municipio):
    assert idib.extrair_municipio(titulo) == municipio


@pytest.mark.parametrize("titulo,ano", [
    ("CONCURSO PÚBLICO PARA FORMAÇÃO DE OFICIAIS EDITAL 002-2026/DP/CBMSC – CFO", 2026),
    ("PREFEITURA MUNICIPAL DE ITAREMA/CE EDITAL Nº 01/2026, DE 28 DE SETEMBRO DE 2026", 2026),
    ("Polícia Militar do Espírito Santo", None),
])
def test_o_ano_do_edital(titulo, ano):
    assert idib.ano_do_edital(titulo) == ano


class _Resposta:
    def __init__(self, texto: str, paginas: int = 2):
        self.text = texto
        self.headers = {"X-WP-TotalPages": str(paginas)}

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def coletor(monkeypatch):
    pedidos = []

    def get_falso(self, url):
        pedidos.append(url)
        pagina = url.rsplit("=", 1)[1]
        return _Resposta((PASTA / f"posts_pagina_{pagina}.json").read_text(encoding="utf-8"))

    monkeypatch.setattr(idib.Idib, "get", get_falso)
    c = idib.Idib()
    c.pedidos = pedidos
    return c


def _do(itens, trecho):
    return next(i for i in itens if trecho in i.titulo)


def test_le_as_duas_paginas_que_o_wordpress_diz(coletor):
    itens = coletor.coletar()
    assert len(itens) == 13
    assert [u.rsplit("=", 1)[1] for u in coletor.pedidos] == ["1", "2"]


def test_os_campos_do_cbmsc(coletor):
    item = _do(coletor.coletar(), "002-2026/DP/CBMSC")

    assert item.titulo == ("2026 - CONCURSO PÚBLICO PARA FORMAÇÃO DE OFICIAIS "
                           "EDITAL 002-2026/DP/CBMSC – CFO")
    assert item.url == "https://concurso.idib.org.br/Concurso.aspx?ID=336"
    assert item.banca == "IDIB"
    assert item.situacao == "edital_publicado"          # Em andamento
    assert item.tipo == "concurso"
    assert item.uf is None
    assert (item.publicado_em.year, item.publicado_em.month, item.publicado_em.day) == (2026, 1, 28)


def test_inscricao_aberta_e_seletivo(coletor):
    itens = coletor.coletar()
    assert _do(itens, "ITAREMA/CE").situacao == "inscricoes_abertas"
    assert _do(itens, "SÃO JOSÉ DE RIBAMAR").tipo == "seletivo"


def test_o_cbmsc_cai_no_cartao_dos_bombeiros_e_o_de_fora_em_nenhum(banco_temporario, coletor):
    """O "cbmsc" do `prova_de_sc` (config) e o que prova SC: o titulo nao diz."""
    from radar import acompanhamentos as carreiras
    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        for item in coletor.coletar():
            servico._gravar(s, item, fonte="idib")
    with sessao() as s:
        cfp = s.query(Concurso).filter_by(url="https://concurso.idib.org.br/Concurso.aspx?ID=335").one()
        assert [c.nome for c in carreiras.de_quais(cfp)] == ["Bombeiro Militar SC"]
        itarema = s.query(Concurso).filter(Concurso.titulo.contains("ITAREMA")).one()
        assert itarema.uf == "CE" and carreiras.de_quais(itarema) == []


def test_pagina_vazia(monkeypatch):
    pedidos = []

    def get_vazio(self, url):
        pedidos.append(url)
        return _Resposta("[]", paginas=0)

    monkeypatch.setattr(idib.Idib, "get", get_vazio)
    assert idib.Idib().coletar() == []
    assert len(pedidos) == 1


def test_fonte_fora_do_ar_sobe_o_erro(monkeypatch):
    def get_fora(self, url):
        raise requests.ConnectionError("fora do ar")

    monkeypatch.setattr(idib.Idib, "get", get_fora)
    with pytest.raises(requests.ConnectionError):
        idib.Idib().coletar()


def test_esta_entre_os_coletores():
    from radar.servico.coleta import COLETORES
    assert idib.Idib in COLETORES
