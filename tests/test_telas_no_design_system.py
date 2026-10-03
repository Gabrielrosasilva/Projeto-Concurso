"""As seis telas que faltavam no design system (Etapa 7B).

Cada uma abre com `body class="ds"`, na coluna `ds-pagina`, com o
design.css, e sem a paleta antiga - o `:root` proprio com --fundo, --cartao,
--azul... que cada tela antiga trazia, e que dava ao site duas caras. Os
testes de funcao de cada tela continuam nos arquivos dela.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar.web.app import app

#: (endereco, status esperado). A 404 responde 404 de proposito.
TELAS = [
    ("/isso-nao-existe", 404),
    ("/calendario", 200),
    ("/previsao", 200),
    ("/acompanhando", 200),
    ("/analises", 200),
    ("/concursos", 200),
]

#: A paleta que cada tela antiga definia para si.
PALETA_ANTIGA = re.compile(r"--(fundo|cartao|texto|suave|borda|azul|azul-fraco)\s*:")


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


@pytest.mark.parametrize("endereco, status", TELAS, ids=[e for e, _s in TELAS])
def test_a_tela_esta_no_design_system(cliente, endereco, status):
    resposta = cliente.get(endereco)
    assert resposta.status_code == status

    html = resposta.text
    assert re.search(r'<body class="ds\b', html)
    assert 'class="ds-pagina"' in html
    assert "/estatico/design.css" in html
    achado = PALETA_ANTIGA.search(html)
    assert not achado, achado and achado.group(0)


WEB = Path(__file__).resolve().parent.parent / "src" / "radar" / "web"


def test_toda_tela_marca_o_design_system():
    """Nenhuma tela com a cara antiga: todo template de pagina tem o body ds.
    Os parciais (_topo, _componentes...) vao dentro das paginas."""
    for arquivo in sorted((WEB / "templates").glob("*.html")):
        if arquivo.name.startswith("_"):
            continue
        assert re.search(r'<body class="ds\b', arquivo.read_text(encoding="utf-8")), arquivo.name


def test_a_ponte_dos_nomes_antigos_saiu():
    """A ponte (--cartao, --azul...) existia no design.css para a barra do
    topo e as telas antigas. Com a ultima tela migrada, ela saiu - e ninguem
    pode voltar a usar os nomes velhos, que nao apontam mais para nada."""
    velhos = re.compile(r"var\(--(fundo|cartao|texto|suave|borda|azul|azul-fraco)\)")
    arquivos = sorted((WEB / "templates").glob("*.html")) + [WEB / "static" / "design.css"]
    for arquivo in arquivos:
        achado = velhos.search(arquivo.read_text(encoding="utf-8"))
        assert not achado, (arquivo.name, achado and achado.group(0))
