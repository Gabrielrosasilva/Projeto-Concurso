"""A pagina web renderiza?

Erro em template Jinja so aparece quando a pagina e pedida de verdade - nao
no import. Como a web e a unica interface visual do projeto, vale um teste
que realmente monte o HTML.
"""
import pytest
from fastapi.testclient import TestClient

from radar.db import sessao
from radar.models import Concurso
from radar.web.app import app


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_pagina_abre_vazia(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "Radar de Concursos" in resposta.text
    assert "Nada aqui ainda" in resposta.text


def test_pagina_mostra_concurso(cliente):
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/ascurra",
                fonte="concursosnobrasil",
                titulo="Edital Prefeitura de Ascurra (SC) oferta salarios",
                uf="SC",
                situacao="edital_publicado",
            )
        )

    texto = cliente.get("/").text
    assert "Ascurra" in texto
    assert "https://exemplo.test/ascurra" in texto   # o link original aparece
    assert "edital publicado" in texto               # situacao legivel, sem _


def test_filtro_por_uf(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="De SC", uf="SC"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="De Sao Paulo", uf="SP"))

    texto = cliente.get("/?uf=SC").text
    assert "De SC" in texto
    assert "De Sao Paulo" not in texto


def test_contagem_mostra_o_total_quando_filtra(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="De SC", uf="SC"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="De SP", uf="SP"))

    assert "de 2 no banco" in cliente.get("/?uf=SC").text
