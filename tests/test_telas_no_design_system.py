"""As seis telas que faltavam no design system (Etapa 7B).

Cada uma abre com `body class="ds"`, na coluna `ds-pagina`, com o
design.css, e sem a paleta antiga - o `:root` proprio com --fundo, --cartao,
--azul... que cada tela antiga trazia, e que dava ao site duas caras. Os
testes de funcao de cada tela continuam nos arquivos dela.
"""
import re

import pytest
from fastapi.testclient import TestClient

from radar.web.app import app

#: (endereco, status esperado). A 404 responde 404 de proposito.
TELAS = [
    ("/isso-nao-existe", 404),
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
