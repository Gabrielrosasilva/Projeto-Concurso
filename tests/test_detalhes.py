"""Leitura da pagina do post: prazo de inscricao, banca e lotacao.

As tres fixtures em tests/fixtures/paginas/ sao paginas REAIS, baixadas em
18/09/2026 e salvas sem script nem style. Elas cobrem os tres jeitos que o
site escreve o prazo, e o caso chato do edital estadual que cita meio estado.

Nenhum teste vai a internet.
"""
from datetime import datetime
from pathlib import Path

import pytest

from radar import detalhes
from radar.util import fuso_local

PAGINAS = Path(__file__).parent / "fixtures" / "paginas"

# Os municipios que me interessam, como o regioes.yml entrega.
MUNICIPIOS = {
    "florianopolis": "Florianópolis",
    "sao jose": "São José",
    "sao jose do cerrito": "São José do Cerrito",
    "sao pedro de alcantara": "São Pedro de Alcântara",
    "palhoca": "Palhoça",
    "lages": "Lages",
}


def pagina(nome: str) -> str:
    return (PAGINAS / f"{nome}.html").read_text(encoding="utf-8")


def data(dia: int, mes: int, ano: int = 2026) -> datetime:
    """Meia-noite daqui, nao de Londres."""
    return datetime(ano, mes, dia, tzinfo=fuso_local())


def fim(dia: int, mes: int, ano: int = 2026) -> datetime:
    """O ultimo instante do dia: a inscricao vale o dia inteiro."""
    return datetime(ano, mes, dia, 23, 59, 59, tzinfo=fuso_local())


# --- prazo de inscricao -----------------------------------------------------

def test_sefaz_sc_o_concurso_em_que_estou_inscrito():
    """"das 10h do dia 04 de setembro ate as 23h59 do dia 05 de outubro"."""
    d = detalhes.extrair(pagina("sefaz_sc"), 2026, MUNICIPIOS)

    assert d.inscricoes_de == data(4, 9)
    assert d.inscricoes_ate == fim(5, 10)


def test_sao_jose_data_de_inicio_sem_ano_no_texto():
    """"do dia 16 de setembro ate as 16h do dia 16 de outubro de 2026".

    O primeiro dia nao repete o ano; ele herda o ano da publicacao.
    """
    d = detalhes.extrair(pagina("sao_jose"), 2026, MUNICIPIOS)

    assert d.inscricoes_de == data(16, 9)
    assert d.inscricoes_ate == fim(16, 10)


def test_ses_sc_intervalo_no_mesmo_mes():
    """"o prazo para se inscrever e de 14 a 25 de setembro de 2026".

    Aqui o primeiro dia nao repete nem mes nem ano.
    """
    d = detalhes.extrair(pagina("ses_sc"), 2026, MUNICIPIOS)

    assert d.inscricoes_de == data(14, 9)
    assert d.inscricoes_ate == fim(25, 9)


def test_pagina_sem_prazo_deixa_nulo():
    """Prazo errado e pior que prazo faltando: um some, o outro engana."""
    d = detalhes.extrair("<html><body>Sem nada aqui.</body></html>", 2026, MUNICIPIOS)

    assert d.inscricoes_de is None
    assert d.inscricoes_ate is None


# --- os formatos de data, isolados ------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("inscricoes de 1 de marco de 2026 ate 20 de marco de 2026", (data(1, 3), fim(20, 3))),
    ("inscricoes de 05/03/2026 ate 20/03/2026", (data(5, 3), fim(20, 3))),
    ("inscricoes de 05/03/26 ate 20/03/26", (data(5, 3), fim(20, 3))),
    ("prazo de inscricao e de 3 a 14 de abril de 2026", (data(3, 4), fim(14, 4))),
])
def test_formatos_de_data(texto, esperado):
    assert detalhes.achar_periodo_de_inscricao(texto, 2026) == esperado


def test_data_sem_ano_herda_o_ano_da_publicacao():
    inicio, fim = detalhes.achar_periodo_de_inscricao(
        "inscricoes de 10 de janeiro ate 30 de janeiro", 2025
    )
    assert inicio.year == 2025 and fim.year == 2025


def test_data_impossivel_e_ignorada():
    assert detalhes.achar_datas("31 de fevereiro de 2026", 2026) == []


def test_janela_absurda_e_descartada():
    """Dois anos entre abrir e fechar nao e prazo de inscricao."""
    inicio, fim = detalhes.achar_periodo_de_inscricao(
        "inscricao 01/01/2020 e a prova do concurso de 01/01/2026", 2026
    )
    assert fim is None


# --- banca ------------------------------------------------------------------

def test_banca_do_sefaz_e_fcc():
    """Bate com o edital: concursosfcc.com.br."""
    assert detalhes.extrair(pagina("sefaz_sc"), 2026, MUNICIPIOS).banca == "FCC"


def test_banca_de_sao_jose_e_fepese():
    """FEPESE e a banca que mais faz concurso em SC, como o CLAUDE.md diz."""
    assert detalhes.extrair(pagina("sao_jose"), 2026, MUNICIPIOS).banca == "FEPESE"


def test_sem_banca_conhecida_fica_nulo():
    assert detalhes.achar_banca("texto sem nome de banca nenhum") is None


# --- municipio de lotacao ---------------------------------------------------

def test_orgao_estadual_ganha_municipio_pela_lotacao():
    """O caso que motivou tudo isto.

    "Concurso SEFAZ (SC)" nao tem "Prefeitura de X" no titulo, entao o
    classificador nao acha municipio e marca `indefinida`. A pagina diz
    "lotacao em Florianopolis", e ai o concurso vai para o nucleo.
    """
    assert detalhes.extrair(pagina("sefaz_sc"), 2026, MUNICIPIOS).municipio == "Florianópolis"


def test_pagina_que_cita_varios_municipios_nao_escolhe_nenhum():
    """Edital de secretaria estadual lista vagas pelo estado inteiro.

    Escolher um seria chute. Melhor seguir `indefinida` e deixar a decisao
    para a leitura do edital.
    """
    d = detalhes.extrair(pagina("ses_sc"), 2026, MUNICIPIOS)
    assert d.municipio is None


def test_municipio_colado_na_pista_de_local_vence():
    texto = "vagas para todo o estado, com lotacao em palhoca conforme o edital"
    assert detalhes.achar_municipio(texto, MUNICIPIOS) == "Palhoça"


def test_a_pegadinha_sao_jose_do_cerrito():
    """Nome que comeca igual nao pode virar o municipio vizinho."""
    assert detalhes.achar_municipio(
        "concurso da prefeitura de sao jose do cerrito", MUNICIPIOS
    ) == "São José do Cerrito"


def test_nome_seguido_de_outra_palavra_ainda_e_reconhecido():
    """"sao jose abre vagas do edital" nao pode ser recusado pelo "do"."""
    assert detalhes.achar_municipio(
        "prefeitura de sao jose abre 300 vagas do edital novo", MUNICIPIOS
    ) == "São José"


def test_municipio_que_nao_interessa_e_ignorado():
    assert detalhes.achar_municipio("concurso em tunapolis sc", MUNICIPIOS) is None


# --- o hotsite da banca, que liga o concurso ao acervo ----------------------

def test_acha_o_hotsite_no_subdominio():
    """A FEPESE poe um subdominio por concurso. Foi assim que o concurso de
    Sao Jose 2026, vindo do feed de noticias, chegou ao acervo."""
    html = ('<a href="https://2026cpeducaeesj.fepese.org.br/?go=edital&amp;'
            'mn=abc&amp;edital=1">Edital</a>')

    assert detalhes.achar_hotsite(html) == "https://2026cpeducaeesj.fepese.org.br"


def test_acha_o_hotsite_no_caminho():
    """A FCC identifica o concurso no caminho. Devolver so o dominio perderia
    justamente o pedaco que diz de que concurso se trata."""
    html = '<a href="https://www.concursosfcc.com.br/concursos/sefsc126/index.html">FCC</a>'

    assert detalhes.achar_hotsite(html) == "https://www.concursosfcc.com.br/concursos/sefsc126"


def test_pagina_institucional_da_banca_nao_e_hotsite():
    """fepese.org.br/concursos/ lista os 520 concursos dela: o edital de um so
    nao esta ali."""
    assert detalhes.achar_hotsite('<a href="https://fepese.org.br/concursos/">lista</a>') is None


def test_link_que_nao_e_de_banca_e_ignorado():
    html = ('<a href="https://gmpg.org/xfn/11">perfil</a>'
            '<a href="https://static.dom.sc.gov.br/?r=site/atoView">diario</a>')

    assert detalhes.achar_hotsite(html) is None


def test_pagina_sem_link_nenhum():
    assert detalhes.achar_hotsite("<p>nada</p>") is None
    assert detalhes.achar_hotsite("") is None


def test_entre_varias_telas_do_hotsite_vale_a_raiz():
    """A mesma pagina linka edital, inscricao e provas do mesmo hotsite. O
    acervo precisa da raiz: de Sao Jose 2026 saiu ".../inscricao" na primeira
    versao, so porque foi o primeiro link do HTML."""
    html = ('<a href="https://2026cpeducaeesj.fepese.org.br/inscricao/#!/edital/abc">Inscrever</a>'
            '<a href="https://2026cpeducaeesj.fepese.org.br/?go=edital&amp;edital=1">Edital</a>')

    assert detalhes.achar_hotsite(html) == "https://2026cpeducaeesj.fepese.org.br"
