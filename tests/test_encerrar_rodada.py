"""O "Encerrar aqui" e o que falta da faixa (decisao 185).

O que estes testes seguram:

  * encerrar a rodada de treino fica com as respondidas e devolve as outras ao
    estoque; o resultado passa a ser o delas, e nenhum numero ja contado muda;
  * a rodada que mede, o Simulado da semana e a rodada sem resposta nao se
    encerram;
  * o botao so aparece na rodada de treino, depois da primeira resposta;
  * o backup antigo nao traz de volta a questao que saiu;
  * os botoes da faixa trazem o que falta dela, e a faixa feita volta ao
    numero dela.
Datas fixas e o cronograma real, como os vizinhos.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import acervo, cronograma
from radar.db import sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import metricas
from radar.servico import simulado as rodadas
from radar.web.app import app
from tests.test_correcao_na_hora import _ids, _rodada
from tests.test_fiz_no_radar import SEG, _primeira_faixa_de_questoes
from tests.test_simulado import _questao


def _tres(filtros=None):
    return _rodada(_questao(1), _questao(2, impressao="i2"), _questao(3, impressao="i3"),
                   filtros=filtros)


def _respostas(rodada):
    with sessao() as s:
        return list(s.scalars(select(RespostaDeSimulado)
                              .where(RespostaDeSimulado.simulado_id == rodada)
                              .order_by(RespostaDeSimulado.ordem)))


# --- encerrar -------------------------------------------------------------------------

def test_encerrar_fica_com_as_respondidas_e_devolve_as_outras(banco_temporario):
    rodada = _tres()
    primeira, segunda, terceira = _ids(rodada)
    rodadas.responder(rodada, primeira, "c")       # certa
    rodadas.responder(rodada, segunda, "a")        # errada
    antes = (metricas.acumulado(), metricas.desempenho(rodada))

    assert rodadas.encerrar(rodada) == 2

    assert [r.questao_id for r in _respostas(rodada)] == [primeira, segunda]
    with sessao() as s:
        simulado = s.get(Simulado, rodada)
        assert simulado.finalizado_em is not None
        assert simulado.filtros["encerrada"] == {"respondidas": 2, "de": 3}
    resumo = metricas.resumo_do_simulado(rodada)
    assert (resumo["total"], resumo["acertos"], resumo["porcentagem"]) == (2, 1, 50.0)
    assert resumo["terminou"]
    # O acerto que ja contava continua o mesmo.
    assert (metricas.acumulado(), metricas.desempenho(rodada)) == antes
    # A que saiu volta ao estoque: o proximo treino pode traze-la.
    assert terceira not in {r.questao_id for r in _respostas(rodada)}


@pytest.mark.parametrize("filtros, recado", [
    ({"rodada": "composta", "quantidade": 3}, "mede"),
    ({"rodada": "erros_das_rodadas", "quantidade": 3}, "mede"),
    ({"rodada": "simulado_da_semana", "quantidade": 3}, "Simulado da semana"),
])
def test_a_rodada_que_mede_e_o_simulado_da_semana_vao_ate_o_fim(banco_temporario, filtros,
                                                                  recado):
    rodada = _tres(filtros)
    rodadas.responder(rodada, _ids(rodada)[0], "c")
    with pytest.raises(rodadas.EncerrarRecusado, match=recado):
        rodadas.encerrar(rodada)
    assert len(_respostas(rodada)) == 3


def test_sem_nenhuma_resposta_nao_se_encerra(banco_temporario):
    rodada = _tres()
    with pytest.raises(rodadas.EncerrarRecusado, match="ao menos uma"):
        rodadas.encerrar(rodada)


def test_o_backup_antigo_nao_traz_de_volta_a_que_saiu(banco_temporario):
    rodada = _tres()
    primeira = _ids(rodada)[0]
    rodadas.responder(rodada, primeira, "c")
    acervo.exportar_simulados()
    antigo = acervo.caminho_dos_simulados().read_text(encoding="utf-8")
    assert len(json.loads(antigo)[0]["respostas"]) == 3

    rodadas.encerrar(rodada)
    acervo.caminho_dos_simulados().write_text(antigo, encoding="utf-8")
    acervo.importar_simulados()

    assert [r.questao_id for r in _respostas(rodada)] == [primeira]


# --- a tela ---------------------------------------------------------------------------

def test_o_botao_so_aparece_no_treino_depois_da_primeira(banco_temporario):
    cliente = TestClient(app)
    rodada = _tres()
    primeira = _ids(rodada)[0]
    assert f'action="/simulado/{rodada}/encerrar"' not in cliente.get(f"/simulado/{rodada}").text

    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": primeira, "letra": "a"})
    assert "Encerrar aqui · salva 1" in cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    assert "Encerrar aqui · salva 1" in cliente.get(f"/simulado/{rodada}").text

    ida = cliente.post(f"/simulado/{rodada}/encerrar", follow_redirects=False)
    assert ida.status_code == 303 and ida.headers["location"] == f"/simulado/{rodada}"
    relatorio = cliente.get(ida.headers["location"]).text
    assert "Você encerrou a rodada com 1 de 3 questões" in relatorio
    assert f'action="/simulado/{rodada}/encerrar"' not in relatorio

    mede = _rodada(_questao(4, impressao="i4"), _questao(5, impressao="i5"),
                   _questao(6, impressao="i6"), filtros={"rodada": "composta", "quantidade": 3})
    cliente.post(f"/simulado/{mede}/responder", data={"questao_id": _ids(mede)[0], "letra": "a"})
    assert f'action="/simulado/{mede}/encerrar"' not in cliente.get(f"/simulado/{mede}").text
    assert cliente.post(f"/simulado/{mede}/encerrar").status_code == 400


# --- o que falta da faixa --------------------------------------------------------------

@pytest.fixture
def plano():
    return cronograma.carregar()


def _blocos(plano):
    dia = plano.dia(SEG)
    return [SimpleNamespace(chave=b, faixas=getattr(dia, b)) for b in cronograma.TODOS_OS_BLOCOS]


def test_o_botao_da_faixa_traz_o_que_falta_dela(plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    assert faixa.questoes > 2
    chave = (bloco, indice)
    no_radar = {(bloco, indice, faixa.titulo): SimpleNamespace(questoes=faixa.questoes - 2)}

    pedidas = diario.pedidas_das_faixas(_blocos(plano), set(), no_radar)
    assert pedidas[chave] == diario.PedidasDaFaixa(2, so_o_que_falta=True)
    # Nada no radar ainda: o numero da faixa.
    assert diario.pedidas_das_faixas(_blocos(plano), set(), {})[chave] == \
        diario.PedidasDaFaixa(faixa.questoes)
    # Feita (por mim ou pelo radar): volta ao numero dela, para treinar mais.
    assert diario.pedidas_das_faixas(_blocos(plano), {chave}, no_radar)[chave] == \
        diario.PedidasDaFaixa(faixa.questoes)
    # Passou do numero sem a faixa estar marcada: ao menos 1.
    passou = {(bloco, indice, faixa.titulo): SimpleNamespace(questoes=faixa.questoes + 3)}
    assert diario.pedidas_das_faixas(_blocos(plano), set(), passou)[chave].quantas == 1
    # Faixa sem questao (teoria, pausa) nao tem botao.
    assert all(f.questoes for b in _blocos(plano) for i, f in enumerate(b.faixas)
               if (b.chave, i) in pedidas)
