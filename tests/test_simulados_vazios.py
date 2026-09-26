"""Limpar os simulados vazios: sem nenhuma resposta e criados ha mais de 1 dia.

Cada clique em "Treinar" cria uma rodada; a abandonada fica com as questoes
sorteadas e nenhuma resposta. Uma resposta que seja e historico: nunca sai.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest
from typer.testing import CliRunner

from radar import acervo, servico
from radar.cli import app
from radar.db import sessao
from radar.models import RespostaDeSimulado, Simulado

from tests.test_espacada import _questao
from tests.test_foco import _concurso

AGORA = datetime.now(timezone.utc)


@pytest.fixture
def questoes(banco_temporario):
    with sessao() as s:
        s.add(_concurso())
    return [_questao(n) for n in range(1, 4)]


def _simulado(questoes, criado_ha: timedelta, respondidas: int = 0) -> int:
    """Uma rodada com as questoes sorteadas e `respondidas` delas respondidas."""
    with sessao() as s:
        sim = Simulado(filtros={}, criado_em=AGORA - criado_ha)
        s.add(sim)
        s.flush()
        for ordem, questao_id in enumerate(questoes, start=1):
            respondeu = ordem <= respondidas
            s.add(RespostaDeSimulado(
                simulado_id=sim.id, questao_id=questao_id, ordem=ordem,
                escolhida="a" if respondeu else None,
                acertou=True if respondeu else None,
                respondida_em=AGORA - criado_ha if respondeu else None,
            ))
        return sim.id


def _ids_no_banco():
    with sessao() as s:
        return {sim.id for sim in s.query(Simulado)}


def _criados_no_arquivo():
    return {linha["criado_em"]
            for linha in json.loads(acervo.caminho_dos_simulados().read_text(encoding="utf-8"))}


def test_vazio_e_antigo_sai(questoes):
    antigo = _simulado(questoes, timedelta(days=3))
    assert [i for i, _ in servico.simulados_vazios()] == [antigo]
    assert [i for i, _ in servico.descartar_vazios()] == [antigo]
    assert antigo not in _ids_no_banco()
    with sessao() as s:
        # As linhas das questoes sorteadas vao junto.
        assert s.query(RespostaDeSimulado).filter_by(simulado_id=antigo).count() == 0


def test_vazio_de_hoje_fica(questoes):
    hoje = _simulado(questoes, timedelta(hours=3))
    assert servico.descartar_vazios() == []
    assert hoje in _ids_no_banco()


def test_com_uma_resposta_nunca_sai(questoes):
    uma = _simulado(questoes, timedelta(days=30), respondidas=1)
    assert servico.descartar_vazios() == []
    assert uma in _ids_no_banco()


def test_some_do_banco_e_do_json(questoes):
    vazio = _simulado(questoes, timedelta(days=2))
    # Outra hora: o arquivo reconhece o simulado pelo `criado_em`.
    feito = _simulado(questoes, timedelta(days=2, hours=1), respondidas=3)
    acervo.exportar_simulados()
    assert len(_criados_no_arquivo()) == 2

    servico.descartar_vazios()
    assert _ids_no_banco() == {feito}
    assert len(_criados_no_arquivo()) == 1
    # E o importar nao traz de volta.
    acervo.importar_simulados()
    assert _ids_no_banco() == {feito}
    assert vazio not in _ids_no_banco()


# --- o comando -----------------------------------------------------------------

def test_comando_mostra_pergunta_e_apaga(questoes):
    antigo = _simulado(questoes, timedelta(days=3))
    runner = CliRunner()

    nao = runner.invoke(app, ["descartar", "--vazios"], input="n\n")
    assert nao.exit_code == 1
    assert "1 simulado(s) sem nenhuma resposta" in nao.output
    assert f"#{antigo}  criado em" in nao.output
    assert "Nada apagado." in nao.output
    assert antigo in _ids_no_banco()

    sim = runner.invoke(app, ["descartar", "--vazios"], input="s\n")
    assert sim.exit_code == 0, sim.output
    assert "1 simulado(s) vazio(s) apagado(s)" in sim.output
    assert antigo not in _ids_no_banco()


def test_comando_com_sim_nao_pergunta(questoes):
    _simulado(questoes, timedelta(days=3))
    saida = CliRunner().invoke(app, ["descartar", "--vazios", "--sim"])
    assert saida.exit_code == 0, saida.output
    assert "apagado(s)" in saida.output


def test_comando_sem_nada_para_limpar(questoes):
    saida = CliRunner().invoke(app, ["descartar", "--vazios", "--sim"])
    assert saida.exit_code == 0
    assert "Nada a limpar" in saida.output


def test_vazios_nao_combina_com_id_nem_todos(questoes):
    assert CliRunner().invoke(app, ["descartar", "1", "--vazios"]).exit_code == 1
    assert CliRunner().invoke(app, ["descartar", "--todos", "--vazios"]).exit_code == 1
