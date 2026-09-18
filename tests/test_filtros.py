"""Os filtros da pagina.

Este arquivo nasceu de um relato de que "nenhum filtro esta funcionando, todos
deram erro e estao quebrando a pagina". A causa era uma so, e derrubava todos:
o formulario HTML manda TODO campo, inclusive o vazio, e a rota declarava
`salario_min` como numero. Filtrar so pela banca enviava `salario_min=`, o
FastAPI tentava converter "" para float e devolvia 422.
"""
import pytest
from fastapi.testclient import TestClient

from radar import servico
from radar.db import sessao
from radar.models import Concurso
from radar.web.app import app


def _concurso(url: str, **mudancas) -> Concurso:
    base = dict(
        url=url,
        fonte="teste",
        titulo="Concurso Prefeitura de Palhoça (SC) para Guarda Municipal",
        uf="SC",
        municipio="Palhoça",
        tipo="concurso",
        relevancia="nucleo",
        banca="FEPESE",
        salario=5200.0,
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos):
    with sessao() as s:
        for c in concursos:
            s.add(c)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- o que quebrava a pagina inteira ----------------------------------------

@pytest.mark.parametrize("consulta", [
    "?banca=FEPESE&salario_min=",
    "?banca=FEPESE&salario_min=&salario_max=",
    "?uf=SC&banca=&termo=&salario_min=&salario_max=",
    "?termo=guarda&salario_min=",
    "?todos=true&salario_min=&salario_max=",
    "?abertas=true&salario_min=",
    "?favoritos=true&salario_min=",
    "?editar=&salario_min=",
])
def test_campo_vazio_no_formulario_nao_derruba_a_pagina(cliente, consulta):
    """Formulario HTML manda todo campo, inclusive o vazio."""
    _semear(_concurso("https://a.test/1"))
    assert cliente.get("/" + consulta).status_code == 200


@pytest.mark.parametrize("entrada", ["abc", "R$", "-", "1,2,3", "   "])
def test_texto_invalido_no_campo_de_salario_e_ignorado(cliente, entrada):
    """Quem digita errado ve a lista sem filtro, nao uma pagina de erro."""
    _semear(_concurso("https://a.test/1"))

    resposta = cliente.get(f"/?salario_min={entrada}")
    assert resposta.status_code == 200
    assert "Guarda Municipal" in resposta.text


def test_editar_vazio_nao_derruba(cliente):
    _semear(_concurso("https://a.test/1"))
    assert cliente.get("/?editar=").status_code == 200


# --- faixa de remuneracao ---------------------------------------------------

def _tres_faixas():
    return (
        _concurso("https://a.test/baixo", titulo="Ganha pouco", salario=1500),
        _concurso("https://a.test/medio", titulo="Ganha medio", salario=3000),
        _concurso("https://a.test/alto", titulo="Ganha bem", salario=7000),
        _concurso("https://a.test/altissimo", titulo="Ganha muito", salario=25000),
    )


@pytest.mark.parametrize("minimo,maximo,esperados", [
    (None, 2000, ["Ganha pouco"]),
    (2100, 5000, ["Ganha medio"]),
    (5000, 10000, ["Ganha bem"]),
    (10000, None, ["Ganha muito"]),
])
def test_faixas_de_remuneracao(banco_temporario, minimo, maximo, esperados):
    _semear(*_tres_faixas())

    titulos = [
        c.titulo for c in servico.listar(salario_min=minimo, salario_max=maximo)
    ]
    assert titulos == esperados


def test_so_o_teto_tambem_filtra(banco_temporario):
    """A faixa "ate R$ 2.000" nao tem minimo."""
    _semear(*_tres_faixas())
    assert len(servico.listar(salario_max=2000)) == 1


def test_sem_salario_fica_de_fora_de_qualquer_faixa(banco_temporario):
    _semear(_concurso("https://a.test/1", salario=None))
    assert servico.listar(salario_min=None, salario_max=2000) == []


def test_os_atalhos_de_faixa_aparecem_na_tela(cliente):
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/").text
    for rotulo in ("ate R$ 2.000", "R$ 2.100 a R$ 5.000",
                   "R$ 5.000 a R$ 10.000", "acima de R$ 10.000"):
        assert rotulo in texto


def test_o_atalho_preserva_a_aba(cliente):
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/?todos=true").text
    assert "todos=true&amp;salario_min=" in texto


def test_a_faixa_escolhida_fica_destacada(cliente):
    _semear(*_tres_faixas())

    texto = cliente.get("/?salario_min=5000&salario_max=10000").text
    assert 'class="faixa ativa"' in texto


# --- banca por abreviacao ---------------------------------------------------

@pytest.mark.parametrize("digitado", [
    "FCC", "fcc", "Fundação Carlos Chagas", "fundacao carlos chagas",
])
def test_banca_pelo_nome_curto_ou_por_extenso(banco_temporario, digitado):
    """Quem digita "Fundacao Carlos Chagas" quer o mesmo de quem digita FCC."""
    _semear(
        _concurso("https://a.test/1", titulo="Da FCC", banca="FCC"),
        _concurso("https://a.test/2", titulo="Da FEPESE", banca="FEPESE"),
    )

    titulos = [c.titulo for c in servico.listar(banca=digitado)]
    assert titulos == ["Da FCC"]


@pytest.mark.parametrize("digitado,esperado", [
    ("fepese", "FEPESE"),
    ("fundacao de estudos e pesquisas socioeconomicos", "FEPESE"),
    ("getulio vargas", "FGV"),
    ("cespe", "Cebraspe"),
    ("barriga verde", "Instituto o Barriga Verde"),
])
def test_apelidos_conhecidos(digitado, esperado):
    assert esperado in servico.expandir_banca(digitado)


def test_banca_desconhecida_cai_na_busca_por_pedaco(banco_temporario):
    """Banca que nao esta na tabela de apelidos ainda precisa ser encontrada."""
    _semear(_concurso("https://a.test/1", banca="Instituto Novo Qualquer"))

    assert servico.expandir_banca("Novo Qualquer") == []
    assert len(servico.listar(banca="Novo Qualquer")) == 1


# --- busca por palavra ------------------------------------------------------

@pytest.mark.parametrize("digitado", ["Palhoça", "Palhoca", "PALHOCA", "palhoça"])
def test_busca_ignora_acento_e_caixa(banco_temporario, digitado):
    """Quem digita no campo raramente poe cedilha."""
    _semear(_concurso("https://a.test/1"))
    assert len(servico.listar(termo=digitado)) == 1


def test_busca_tambem_olha_o_municipio(banco_temporario):
    _semear(_concurso(
        "https://a.test/1", titulo="Concurso sem cidade no titulo",
        municipio="Biguaçu",
    ))
    assert len(servico.listar(termo="biguacu")) == 1


def test_busca_sem_resultado_devolve_pagina_vazia_e_nao_erro(cliente):
    _semear(_concurso("https://a.test/1"))

    resposta = cliente.get("/?termo=coisaquenaoexiste")
    assert resposta.status_code == 200
    assert "Nenhum resultado" in resposta.text
