"""A barra do topo, a proxima faixa e o bloco completo fechado (decisao 181).

O que estes testes seguram:

  * a barra conta as faixas que contam (a mesma regra da sugestao da meta), as
    questoes do total do dia e os minutos das faixas marcadas;
  * a proxima e a primeira faixa que conta e nao esta feita, na ordem do dia;
  * o bloco com todas as faixas feitas nasce fechado, e marcar a ultima volta
    para o cabecalho dele, e nao para a faixa.

As datas sao fixas: nada aqui depende do dia em que o teste roda.
"""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from radar import cronograma
from radar.servico import cronograma as diario
from radar.web.app import app

SEG = date(2026, 9, 28)
DEPOIS = date(2026, 9, 30)


@pytest.fixture
def plano():
    return cronograma.carregar()


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: DEPOIS)


def _marcar(plano, bloco, indice):
    """Marca a faixa como o circulo marcaria."""
    faixa = diario._faixa_do_plano(plano, SEG, bloco, indice)
    if cronograma.tem_acerto(faixa):
        diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="",
                            plano=plano, hoje=DEPOIS)
    else:
        diario.marcar_faixa(SEG, bloco, indice, faixa.titulo, plano=plano, hoje=DEPOIS)


def test_sem_nada_feito_a_proxima_e_a_primeira_faixa_que_conta(banco_temporario, plano):
    tela = diario.tela_do_dia(SEG)
    contam = [p for b in cronograma.TODOS_OS_BLOCOS for p in diario.faixas_que_contam(tela.dia, b)]

    p = tela.progresso

    assert (p.feitas, p.total, p.porcentagem, p.completo) == (0, len(contam), 0, False)
    assert (p.proxima[0], p.proxima[1]) == contam[0]
    assert p.questoes_do_plano == tela.dia.total_questoes
    assert p.minutos_do_plano == sum(getattr(tela.dia, b)[i].duracao or 0 for b, i in contam)


def test_a_barra_anda_com_o_circulo_e_a_proxima_passa_para_a_seguinte(banco_temporario, plano):
    tela = diario.tela_do_dia(SEG)
    primeira, segunda = [p for b in cronograma.TODOS_OS_BLOCOS
                         for p in diario.faixas_que_contam(tela.dia, b)][:2]

    _marcar(plano, *primeira)
    p = diario.tela_do_dia(SEG).progresso

    assert p.feitas == 1
    assert (p.proxima[0], p.proxima[1]) == segunda
    assert p.minutos_feitos == getattr(tela.dia, primeira[0])[primeira[1]].duracao


def test_o_bloco_completo_nasce_fechado_e_a_ultima_volta_para_o_cabecalho(banco_temporario, plano):
    tela = diario.tela_do_dia(SEG)
    manha = diario.faixas_que_contam(tela.dia, "manha")
    *antes, ultima = manha
    for posicao in antes:
        _marcar(plano, *posicao)
    assert not diario.bloco_completo(SEG, "manha", plano=plano)

    faixa = diario._faixa_do_plano(plano, SEG, *ultima)
    rota = "/hoje/faixa/questoes" if cronograma.tem_acerto(faixa) else "/hoje/faixa"
    resposta = TestClient(app).post(rota, data={
        "data": SEG.isoformat(), "bloco": ultima[0], "indice": str(ultima[1]),
        "titulo": faixa.titulo}, follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"].endswith("#bloco-manha")
    texto = TestClient(app).get("/hoje?data=2026-09-28").text
    abertura = re.search(r'<details class="bloco-dobra" data-bloco="manha"[^>]*>', texto).group(0)
    assert "data-completo" in abertura and " open" not in abertura
    assert "✓ completo" in texto


def test_a_tela_mostra_a_barra_e_a_proxima(banco_temporario, plano):
    tela = diario.tela_do_dia(SEG)
    bloco, indice = diario.faixas_que_contam(tela.dia, "manha")[0]

    texto = TestClient(app).get("/hoje?data=2026-09-28").text

    assert 'class="ds-cartao progresso-do-dia"' in texto
    assert f"0 de {tela.progresso.total}</b> faixas" in texto
    assert "▶ Próxima" in texto
    assert f'href="#faixa-{bloco}-{indice}">Ir para a faixa' in texto
