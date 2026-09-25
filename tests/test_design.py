"""O design system: um arquivo de estilo, seis selos, modo escuro, e nada de JS.

A tela de Macetes e a primeira a usar. Estes testes seguram o contrato que as
proximas telas vao herdar - se alguem renomear uma variavel ou tirar um selo,
estoura aqui, e nao numa tela que eu so abro de vez em quando.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar.web.app import app, templates

CSS = Path(__file__).resolve().parent.parent / "src" / "radar" / "web" / "static" / "design.css"


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_o_arquivo_de_estilo_e_servido(cliente):
    resposta = cliente.get("/estatico/design.css")
    assert resposta.status_code == 200
    assert "text/css" in resposta.headers["content-type"]


@pytest.mark.parametrize("variavel", [
    # cor, espaco, tipografia - as tres familias que a especificacao pede
    "--cor-fundo", "--cor-superficie", "--cor-texto", "--cor-acao",
    "--esp-1", "--esp-4", "--esp-7",
    "--fonte", "--tam-base", "--peso-forte", "--linha",
    "--raio", "--selo-ia", "--selo-oficial", "--cor-aviso",
])
def test_as_variaveis_existem(variavel):
    assert re.search(rf"{variavel}\s*:", CSS.read_text(encoding="utf-8"))


def test_o_modo_escuro_segue_o_sistema_e_pode_ser_forcado():
    css = CSS.read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in css
    assert ':root[data-tema="escuro"]' in css
    # O claro forcado desliga o escuro do sistema.
    assert ':root:not([data-tema="claro"])' in css


def test_os_seis_selos_da_especificacao():
    """Os seis, com o emoji e o texto da tabela da especificacao."""
    modulo = templates.env.get_template("_componentes.html").module
    esperados = {
        "oficial": ("🟦", "Fonte oficial"),
        "prova": ("🟦", "Extraída da prova"),
        "calculado": ("🟩", "Calculado pelo sistema"),
        "classificacao": ("🟨", "Classificação automática"),
        "tendencia": ("🟨", "Tendência"),
        "ia": ("🟥", "Gerado por IA"),
    }
    for tipo, (emoji, texto) in esperados.items():
        html = str(modulo.selo(tipo))
        assert emoji in html and texto in html, tipo


def test_a_tela_de_macetes_usa_o_design_system(cliente):
    pagina = cliente.get("/macetes").text
    assert '/estatico/design.css' in pagina
    assert 'class="ds-pagina"' in pagina


def test_tema_escuro_pela_url(cliente):
    assert 'data-tema="escuro"' in cliente.get("/macetes?tema=escuro").text


def test_sem_javascript(cliente):
    """O CLAUDE.md pede sem JavaScript pesado; esta tela nao tem nenhum."""
    assert "<script" not in cliente.get("/macetes").text.lower()
