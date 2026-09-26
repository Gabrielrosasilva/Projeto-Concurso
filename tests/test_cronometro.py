"""O cronometro da tela Hoje, do lado do servidor.

O comportamento do cronometro.js (contagem, som, notificacao) e testado na
mao, no navegador. Aqui se segura o contrato com ele: o script vem, cada
faixa que nao e pausa leva os data-* certos e um botao ▶, e sem JavaScript
nada disso aparece (tudo sai com `hidden`).
"""
import re
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from radar import cronograma, servico
from radar.util import fuso_local
from radar.web.app import app

SEG = date(2026, 9, 28)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


@pytest.fixture(scope="module")
def dia():
    plano = cronograma.carregar()
    nivel = 1          # a semana 1 do plano, vista antes do ciclo
    return cronograma.montar_dia(plano, SEG, nivel)


def _li(texto, id_da_faixa):
    """A tag de abertura do <li> da faixa, com os data-*."""
    return re.search(r'<li[^>]*id="' + id_da_faixa + r'"[^>]*>', texto, re.S).group(0)


def test_o_script_e_servido(cliente):
    resposta = cliente.get("/estatico/cronometro.js")
    assert resposta.status_code == 200
    assert "javascript" in resposta.headers["content-type"]


def test_a_faixa_antes_da_pausa_diz_a_pausa_e_o_que_vem_depois(cliente, dia):
    texto = cliente.get("/hoje?data=2026-09-28").text
    teoria, pausa, depois = dia.manha[0], dia.manha[1], dia.manha[2]
    assert pausa.tipo == "pausa"
    li = _li(texto, "faixa-manha-0")
    assert f'data-duracao="{teoria.duracao}"' in li
    assert f'data-titulo="{teoria.titulo}"' in li
    assert 'data-proxima-pausa="sim"' in li
    assert f'data-proxima-duracao="{pausa.duracao}"' in li
    assert f'data-depois-titulo="{depois.titulo}"' in li


def test_a_ultima_da_manha_aponta_para_a_primeira_da_noite(cliente, dia):
    texto = cliente.get("/hoje?data=2026-09-28").text
    ultima = len(dia.manha) - 1
    li = _li(texto, f"faixa-manha-{ultima}")
    assert 'data-proxima-pausa="nao"' in li
    assert f'data-proxima-titulo="{dia.noite[0].titulo}"' in li
    assert 'data-depois-titulo=""' in li


def test_a_ultima_do_dia_nao_tem_proxima(cliente, dia):
    texto = cliente.get("/hoje?data=2026-09-28").text
    li = _li(texto, f"faixa-pos22-{len(dia.pos22) - 1}")
    assert 'data-proxima-titulo=""' in li


def test_pausa_nao_tem_botao_nem_data(cliente, dia):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "data-duracao" not in _li(texto, "faixa-manha-1")
    nao_pausas = sum(1 for f in dia.faixas() if f.tipo != "pausa")
    assert texto.count('class="play-faixa"') == nao_pausas


def test_sem_javascript_nada_do_cronometro_aparece(cliente):
    """Tudo sai escondido; so o cronometro.js tira o `hidden`."""
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert '<div class="lateral-cronometro" id="cronometro" hidden>' in texto
    assert re.search(r'<div class="aviso-cheio" id="aviso-cheio" hidden', texto)
    botoes = re.findall(r'<button type="button" class="play-faixa"[^>]*>', texto)
    assert botoes and all(" hidden" in b for b in botoes)
    # E o resto da tela continua ali, sem depender dele.
    assert "Como foi o dia" in texto and 'class="circulo"' not in texto  # 28/09 e futuro


def test_o_cartao_e_o_aviso_tem_o_texto_certo(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "⏱ Cronômetro" in texto
    assert "🔔 Testar aviso" in texto
    assert 'role="alertdialog"' in texto


def test_as_faixas_do_plano_b_tambem_tem_play(cliente, monkeypatch):
    momento = datetime(2026, 10, 30, 12, 0, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: momento)
    cliente.post("/hoje/plano-b", data={"data": "2026-10-28", "minutos": "30"})
    texto = cliente.get("/hoje?data=2026-10-28").text
    assert texto.count('class="play-faixa"') == 2
    essencial = _li(texto, "faixa-plano_b-0")
    assert 'data-duracao="10"' in essencial
    assert 'data-proxima-pausa="nao"' in essencial
    # 8 questoes a 2,5 min = 20 min: a faixa de questoes do Plano B tem duracao.
    assert 'data-duracao="20"' in _li(texto, "faixa-plano_b-1")
