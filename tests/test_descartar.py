"""Descartar simulado: apaga de verdade, e nada do que mede fica para tras.

O caso real: rodadas feitas so para ver se a tela funcionava, chutadas sem
ler. Elas estragam a taxa de acerto, a prioridade da home e a revisao. O que
estes testes seguram e que, depois de descartar, o radar volta a dizer
"ainda nao treinada" - e que o backup nao traz a rodada de volta.
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from typer.testing import CliRunner

from radar import acervo, cli, foco, servico
from radar.db import sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.servico import inicio
from radar.web.app import app

from tests.test_home import _acervo, _responder
from tests.test_foco import com_quadro_do_edital  # noqa: F401

runner = CliRunner()


def _contar(modelo) -> int:
    with sessao() as s:
        return s.scalar(select(func.count()).select_from(modelo))


@pytest.fixture
def chutado(banco_temporario, com_quadro_do_edital):
    """Duas rodadas de teste, chutadas: 1 certa e 5 erradas em Direito Penal."""
    _acervo()
    _responder(certas=1, erradas=2)
    _responder(certas=0, erradas=3)
    acervo.exportar_simulados()          # o backup ja as tem, como na vida real


# --- o que sobra depois ------------------------------------------------------

def test_descartar_tudo_volta_a_ainda_nao_treinada(chutado):
    servico.descartar_todos()

    assert _contar(Simulado) == 0 and _contar(RespostaDeSimulado) == 0
    assert servico.desempenho() == []
    assert servico.evolucao().respondidas == 0
    prioridades = inicio.prioridades(foco.montar())
    assert all(not p.treinada and p.respondidas == 0 for p in prioridades)


def test_nada_fica_para_revisar(chutado):
    assert servico.questoes_erradas()            # antes: havia erro em aberto
    servico.descartar_todos()
    assert servico.questoes_erradas() == []
    assert servico.criar_simulado_de_erros() is None


def test_o_backup_nao_traz_a_rodada_de_volta(chutado):
    """O exportar so deixa o arquivo crescer. Sem limpar o arquivo, o proximo
    importar ressuscitaria o que eu acabei de apagar."""
    servico.descartar_todos()

    assert json.loads(acervo.caminho_dos_simulados().read_text("utf-8")) == []
    acervo.importar_simulados()
    acervo.exportar_simulados()
    assert _contar(Simulado) == 0


def test_descartar_um_so_deixa_os_outros(chutado):
    primeiro, segundo = sorted(r.id for r in servico.listar_simulados())

    assert servico.descartar_simulado(primeiro) == 3
    assert [r.id for r in servico.listar_simulados()] == [segundo]
    linhas = json.loads(acervo.caminho_dos_simulados().read_text("utf-8"))
    assert len(linhas) == 1


def test_descartar_o_que_nao_existe_devolve_none(banco_temporario):
    assert servico.descartar_simulado(999) is None


def test_a_lista_diz_questoes_acerto_e_materias(chutado):
    rodada = servico.listar_simulados()[-1]          # a mais velha
    assert (rodada.questoes, rodada.respondidas, rodada.acertos) == (3, 3, 1)
    assert rodada.materias == ["Direito Penal"]


# --- a CLI ------------------------------------------------------------------

def test_radar_simulados_lista(chutado):
    resultado = runner.invoke(cli.app, ["simulados"])
    assert resultado.exit_code == 0
    assert "2 simulado(s)" in resultado.output
    assert "33%" in resultado.output


def test_radar_descartar_id(chutado):
    alvo = servico.listar_simulados()[0].id
    resultado = runner.invoke(cli.app, ["descartar", str(alvo)])
    assert resultado.exit_code == 0
    assert _contar(Simulado) == 1


def test_descartar_todos_pergunta_antes(chutado):
    """Sem --sim, pergunta; responder nao apaga nada."""
    resultado = runner.invoke(cli.app, ["descartar", "--todos"], input="n\n")
    assert resultado.exit_code == 1
    assert _contar(Simulado) == 2

    resultado = runner.invoke(cli.app, ["descartar", "--todos"], input="s\n")
    assert resultado.exit_code == 0
    assert _contar(Simulado) == 0


def test_descartar_todos_com_sim_nao_pergunta(chutado):
    resultado = runner.invoke(cli.app, ["descartar", "--todos", "--sim"])
    assert resultado.exit_code == 0
    assert "2 simulado(s) e 6 resposta(s) apagados" in resultado.output


def test_descartar_sem_id_nem_todos_nao_faz_nada(chutado):
    assert runner.invoke(cli.app, ["descartar"]).exit_code == 1
    assert _contar(Simulado) == 2


# --- a tela -----------------------------------------------------------------

def test_a_tela_tem_descartar_com_confirmacao(chutado):
    cliente = TestClient(app)
    texto = cliente.get("/simulado").text

    assert "Suas rodadas" in texto
    assert '<details class="descartar">' in texto   # a pergunta vem antes
    assert "Sim, apagar" in texto


def test_o_botao_da_tela_apaga(chutado):
    cliente = TestClient(app)
    alvo = servico.listar_simulados()[0].id

    resposta = cliente.post(f"/simulado/{alvo}/descartar", follow_redirects=False)

    assert resposta.status_code == 303
    assert _contar(Simulado) == 1
    assert "Rodada descartada" in cliente.get(resposta.headers["location"]).text


def test_rodada_abandonada_conta_zero_respostas(banco_temporario,
                                              com_quadro_do_edital):
    """Rodada aberta e largada tem linhas, mas nenhuma resposta dada - e o
    numero que o descartar diz e o de respostas dadas."""
    _acervo()
    abandonada = servico.criar_simulado(quantidade=5, materia="Direito Penal")

    assert servico.descartar_simulado(abandonada.id) == 0
    assert _contar(RespostaDeSimulado) == 0
