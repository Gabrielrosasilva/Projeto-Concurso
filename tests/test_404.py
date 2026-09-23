"""A pagina que nao existe explica o que houve.

O erro cru do FastAPI e {"detail":"Not Found"}, que nao ajuda ninguem - e
menos ainda no caso mais comum aqui: o link aparece na tela e mesmo assim da
erro, porque o servidor esta rodando código antigo.
"""
import time

import pytest
from fastapi.testclient import TestClient

from radar.web import app as modulo_web
from radar.web.app import app


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_endereco_que_nao_existe_responde_em_html(cliente):
    resposta = cliente.get("/isso-nao-existe")

    assert resposta.status_code == 404
    assert "<html" in resposta.text
    assert "detail" not in resposta.text


def test_a_pagina_mostra_o_endereco_pedido(cliente):
    assert "/isso-nao-existe" in cliente.get("/isso-nao-existe").text


def test_com_o_codigo_parado_a_explicacao_e_endereco_errado(cliente, monkeypatch):
    """Nada mudou no disco desde que o servidor subiu: entao foi engano mesmo."""
    monkeypatch.setattr(modulo_web, "SUBIU_EM", time.time() + 3600)

    assert "Endereço errado" in cliente.get("/isso-nao-existe").text


def test_codigo_mais_novo_que_o_servidor_e_apontado(cliente, monkeypatch):
    """O caso real: rota nova no disco, servidor de antes na memoria. O link
    aparece porque a tela e lida do disco a cada visita; a rota nao existe
    porque o codigo so e lido na partida."""
    monkeypatch.setattr(modulo_web, "SUBIU_EM", 0)

    texto = cliente.get("/isso-nao-existe").text

    assert "código antigo" in texto
    assert "Ctrl+C" in texto


def test_a_pagina_leva_de_volta_para_as_abas(cliente):
    texto = cliente.get("/isso-nao-existe").text

    for destino in ('href="/"', 'href="/previsao"', 'href="/macetes"',
                    'href="/simulado"'):
        assert destino in texto


def test_as_abas_do_menu_respondem(cliente):
    """O que o 404 acusou: as tres abas precisam existir de verdade."""
    for rota in ("/", "/previsao", "/macetes", "/simulado"):
        assert cliente.get(rota, follow_redirects=False).status_code == 200
