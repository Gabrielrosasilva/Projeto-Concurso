"""O relatorio de auditoria acessivel pela tela Mais.

O arquivo e fixo, escrito no tmp_path: o teste nao depende do docs/auditoria.md
de verdade existir, nem da data em que ele foi gerado.
"""
import pytest
from fastapi.testclient import TestClient

from radar import auditoria
from radar.web.app import app

RELATORIO = """# Auditoria dos dados de estudo

> Gerado por `radar auditar` em 03/10/2026. **Nao edite a mao**: rode o comando de novo.

## Onde os numeros nao batem

- nenhum lugar: contagem, gabarito e anuladas batem nas 3 provas.
"""


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


@pytest.fixture
def com_relatorio(tmp_path, monkeypatch):
    arquivo = tmp_path / "auditoria.md"
    arquivo.write_text(RELATORIO, encoding="utf-8")
    monkeypatch.setattr(auditoria, "caminho_padrao", lambda: arquivo)
    return arquivo


@pytest.fixture
def sem_relatorio(tmp_path, monkeypatch):
    monkeypatch.setattr(auditoria, "caminho_padrao", lambda: tmp_path / "nao_existe.md")


def test_a_data_sai_do_cabecalho_do_arquivo(com_relatorio):
    assert auditoria.data_do_relatorio() == "03/10/2026"


def test_o_cartao_mostra_a_data_e_o_link(cliente, com_relatorio):
    texto = cliente.get("/mais").text
    assert "Gerado em 03/10/2026" in texto
    assert 'href="/auditoria"' in texto


def test_a_pagina_mostra_o_texto_como_esta(cliente, com_relatorio):
    resposta = cliente.get("/auditoria")

    assert resposta.status_code == 200
    assert '<pre class="relatorio">' in resposta.text
    # Sem renderizar Markdown: o "##" e o "**" chegam como estao.
    assert "## Onde os numeros nao batem" in resposta.text
    assert "**Nao edite a mao**" in resposta.text
    assert "gerada em 03/10/2026" in resposta.text


def test_sem_arquivo_o_cartao_diz_como_gerar(cliente, sem_relatorio):
    texto = cliente.get("/mais").text
    assert "Ainda não gerado" in texto and "radar auditar" in texto
    assert 'href="/auditoria"' not in texto


def test_sem_arquivo_a_pagina_nao_da_erro(cliente, sem_relatorio):
    resposta = cliente.get("/auditoria")
    assert resposta.status_code == 200
    assert "Ainda não gerado" in resposta.text
    assert auditoria.data_do_relatorio() is None
