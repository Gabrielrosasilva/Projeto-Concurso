"""Coletor da FEPESE, pela API REST do WordPress dela.

As fixtures sao respostas REAIS da API, baixadas em 18/09/2026. Nenhum teste
vai a internet.

Por que esta fonte existe: o plano original desta fase era o Diario Oficial dos
Municipios de SC, mas o robots.txt dele proibe robo ("User-agent: * /
Disallow: /"). A FEPESE e a banca que mais faz concurso em SC, libera robo, e
ainda entrega o status e a escolaridade prontos - coisas que no agregador so
saem lendo a pagina, e mesmo assim por aproximacao.
"""
import json
from pathlib import Path

import pytest

from radar.classificador import classificar
from radar.collectors.fepese import Fepese, extrair_municipio

FIXTURES = Path(__file__).parent / "fixtures" / "fepese"


def carregar(nome: str):
    return json.loads((FIXTURES / f"{nome}.json").read_text(encoding="utf-8"))


class RespostaFalsa:
    """Imita o que o requests devolve, com o cabecalho de paginacao junto."""

    def __init__(self, dados, cabecalhos=None):
        self._dados = dados
        self.headers = cabecalhos or {}

    def json(self):
        return self._dados


@pytest.fixture
def coletor(monkeypatch):
    concursos = carregar("concursos")

    def responder(self, url: str):
        if "tax_concurso_status" in url:
            return RespostaFalsa(carregar("tax_concurso_status"))
        if "tax_escolaridade" in url:
            return RespostaFalsa(carregar("tax_escolaridade"))
        if "page=1" in url:
            return RespostaFalsa(concursos, {"X-WP-TotalPages": "1"})
        return RespostaFalsa([])

    monkeypatch.setattr(Fepese, "get", responder)
    monkeypatch.setattr("radar.config.ATRASO_ENTRE_REQUISICOES", 0)
    return Fepese()


# --- municipio a partir do titulo -------------------------------------------

@pytest.mark.parametrize("titulo,esperado", [
    ("2026 – Prefeitura Municipal de São José", "Sao Jose"),
    ("2026 – Prefeitura Municipal de Concórdia", "Concordia"),
    ("2025 – Prefeitura de Palhoça", "Palhoca"),
    ("Câmara Municipal de Biguaçu", "Biguacu"),
    ("2026 – Município de Antônio Carlos", "Antonio Carlos"),
])
def test_extrai_municipio(titulo, esperado):
    assert extrair_municipio(titulo) == esperado


def test_orgao_que_nao_e_municipal_nao_tem_municipio():
    """Celesc, UFSC e governo do estado nao trazem municipio no titulo.
    Inventar um seria pior que admitir que nao sei."""
    assert extrair_municipio("2026 – Celesc") is None
    assert extrair_municipio("Concurso UFSC 2026") is None


def test_subtitulo_depois_do_municipio_e_descartado():
    assert extrair_municipio(
        "2026 – Prefeitura Municipal de São José – Processo Seletivo"
    ) == "Sao Jose"


# --- a coleta ----------------------------------------------------------------

def test_le_os_concursos(coletor):
    itens = coletor.coletar()
    assert len(itens) == len(carregar("concursos"))


def test_a_banca_ja_vem_preenchida(coletor):
    """No agregador a banca so sai lendo a pagina. Aqui e o site dela."""
    assert all(item.banca == "FEPESE" for item in coletor.coletar())


def test_titulo_sem_entidade_html(coletor):
    """O WordPress devolve "2026 &#8211; Prefeitura", com o traco escapado."""
    for item in coletor.coletar():
        assert "&#" not in item.titulo
        assert "&amp;" not in item.titulo


def test_situacao_vem_da_taxonomia_da_banca(coletor):
    """Status dito pela propria banca vale mais que deduzido de data em texto."""
    situacoes = {item.situacao for item in coletor.coletar()}
    assert situacoes <= {
        "inscricoes_abertas", "edital_publicado", "encerrado", "desconhecida"
    }
    # na fixture ha concurso com inscricao aberta
    assert "inscricoes_abertas" in situacoes


def test_inscricoes_abertas_vence_em_andamento(coletor):
    """A FEPESE marca os dois no mesmo concurso; o estado mais adiantado vale,
    senao um concurso com inscricao aberta apareceria so como "em andamento"."""
    com_ambos = [
        i for i in coletor.coletar()
        if {"inscricoes abertas", "em andamento"} <= set(i.extra["status_fepese"])
    ]
    assert com_ambos, "a fixture precisa ter um caso com os dois status"
    assert all(i.situacao == "inscricoes_abertas" for i in com_ambos)


def test_escolaridade_vem_junto(coletor):
    """Criterio meu de elegibilidade que o agregador nao entrega."""
    itens = coletor.coletar()
    assert any(i.escolaridade for i in itens)


def test_guarda_o_hotsite_para_a_fase_de_provas(coletor):
    """E no hotsite que a FEPESE publica edital, prova e gabarito."""
    com_hotsite = [i for i in coletor.coletar() if i.extra.get("hotsite")]
    assert com_hotsite
    assert com_hotsite[0].extra["hotsite"].startswith("http")


def test_para_quando_o_wordpress_diz_que_acabou(coletor, monkeypatch):
    """O cabecalho X-WP-TotalPages evita pedir pagina que nao existe."""
    pedidas = []
    original = Fepese.get

    def contar(self, url):
        pedidas.append(url)
        return original(self, url)

    monkeypatch.setattr(Fepese, "get", contar)
    Fepese(paginas=20).coletar()

    paginas = [u for u in pedidas if "concurso?" in u]
    assert len(paginas) == 1


def test_teto_de_paginas():
    assert Fepese(paginas=9999).paginas <= 20
    assert Fepese(paginas=0).paginas == 1


# --- integracao com o classificador -----------------------------------------

def test_municipio_conhecido_vale_mesmo_sem_uf_declarada(coletor):
    """A API da FEPESE nao diz a UF. Mas config/regioes.yml so tem municipio
    catarinense, entao achar "Sao Jose" ali ja prova que e SC."""
    item = next(i for i in coletor.coletar() if i.municipio == "Sao Jose")
    assert item.uf is None

    resultado = classificar(item)
    assert resultado.relevancia == "nucleo"


def test_municipio_fora_dos_aneis_nao_vira_palpite(coletor):
    """Concordia fica no oeste de SC, longe. Sem UF declarada e sem anel, o
    honesto e `indefinida` ate alguem ler o edital."""
    item = next(i for i in coletor.coletar() if i.municipio == "Concordia")
    assert classificar(item).relevancia == "indefinida"


def test_uf_de_outro_estado_impede_o_atalho():
    """"Sao Jose" existe em varios estados. Se a fonte disser SP, o atalho
    pelo nome nao pode valer."""
    from radar.collectors.base import ItemColetado

    item = ItemColetado(
        titulo="Concurso Prefeitura de Sao Jose do Rio Preto",
        url="https://exemplo.test/x",
        municipio="Sao Jose",
        uf="SP",
    )
    assert classificar(item).relevancia != "nucleo"


# --- orgao estadual ----------------------------------------------------------
#
# Bug real: a API da FEPESE nao manda UF, e o titulo de orgao estadual nao tem
# municipio. "2019 - Secretaria de Estado da Administracao Prisional e
# Socioeducativa" - o concurso da Policia Penal SC - chegava sem UF e com o
# motivo "pode ser federal". Os tres titulos abaixo sao reais, e estao na
# fixture exatamente como a API os devolve.

TITULO_2013 = (
    "2013 – Secretaria de Estado da Justiça e CidadaniaAgente Penitenciário "
    "(masculino)Agente Penitenciário (feminino)Agente de Segurança "
    "Socioeducativo (masculino)Agente de Segurança Socioeducativo (feminino)"
)
TITULO_2019 = "2019 – Secretaria de Estado da Administração Prisional e Socioeducativa"
TITULO_2025 = "2025 – Polícia Científica do Estado de Santa Catarina – PCISC"


@pytest.mark.parametrize("titulo", [TITULO_2013, TITULO_2019, TITULO_2025])
def test_orgao_estadual_recebe_uf_sc(coletor, titulo):
    """A UF e dedutivel da fonte: a FEPESE so faz concurso estadual em SC."""
    item = next(i for i in coletor.coletar() if i.titulo == titulo)
    assert item.uf == "SC"
    assert item.municipio is None


@pytest.mark.parametrize("titulo", [TITULO_2013, TITULO_2019, TITULO_2025])
def test_orgao_estadual_vira_relevancia_estadual(coletor, titulo):
    """O que o bug pedia: sair de "pode ser federal" para "estadual de SC"."""
    item = next(i for i in coletor.coletar() if i.titulo == titulo)
    resultado = classificar(item)

    assert resultado.relevancia == "estadual"
    assert resultado.motivo == (
        "Órgão estadual de SC; polos de prova a confirmar no edital."
    )


def test_prefeitura_continua_sem_uf(coletor):
    """A UF so e preenchida onde ela e dedutivel. No concurso municipal quem
    decide o anel e o nome do municipio, e o atalho ja funcionava."""
    item = next(i for i in coletor.coletar() if i.municipio == "Sao Jose")
    assert item.uf is None
    assert classificar(item).relevancia == "nucleo"
