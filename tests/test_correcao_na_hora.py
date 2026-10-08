"""A correcao na hora e o "vou no chute" (decisao 142).

No treino, depois da letra, a mesma tela volta com a questao corrigida e o
"Proxima". Na rodada que mede (diagnostico, simulado no radar, R+7 dos
erros), nao: o certo e o errado so aparecem no relatorio do fim. O chute fica
gravado ao lado do acerto, e nao muda o acerto.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import acervo, servico
from radar.db import sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.web.app import app
from tests.test_simulado import _questao, _semear


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def _rodada(*questoes, filtros=None) -> int:
    """Uma rodada com estas questoes, na ordem dada."""
    _semear(*questoes)
    with sessao() as s:
        simulado = Simulado(filtros=filtros or {"quantidade": len(questoes)})
        s.add(simulado)
        s.flush()
        for ordem, q in enumerate(questoes, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=q.id,
                                     ordem=ordem))
        return simulado.id


def _ids(simulado_id: int) -> list[int]:
    with sessao() as s:
        return list(s.scalars(
            select(RespostaDeSimulado.questao_id)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .order_by(RespostaDeSimulado.ordem)))


# --- no treino: a correcao na hora --------------------------------------------

def test_no_treino_a_resposta_volta_para_a_questao_corrigida(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, _ = _ids(rodada)

    resposta = cliente.post(f"/simulado/{rodada}/responder",
                            data={"questao_id": primeira, "letra": "c"},
                            follow_redirects=False)

    assert resposta.headers["location"] == f"/simulado/{rodada}?ver={primeira}"
    tela = cliente.get(resposta.headers["location"]).text
    assert "✓ Acertou!" in tela
    assert "Próxima &rarr;" in tela
    assert 'class="bolinhas"' in tela and 'class="certa' in tela


def test_errar_mostra_a_certa_e_o_caderno_de_erros(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, _ = _ids(rodada)

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": primeira, "letra": "a"})
    tela = cliente.get(f"/simulado/{rodada}?ver={primeira}").text

    assert "✗ Errou: a certa é C)" in tela
    assert "✗ sua resposta" in tela and "✓ gabarito" in tela
    assert "Anotar no caderno de erros" in tela
    assert "fonte=radar" in tela


def test_a_letra_nao_muda_depois_da_correcao(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, _ = _ids(rodada)

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": primeira, "letra": "a"})
    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": primeira, "letra": "c"})

    tela = cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    assert "✗ Errou" in tela


def test_proxima_leva_a_questao_seguinte_e_a_ultima_ao_resultado(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, segunda = _ids(rodada)

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": primeira, "letra": "c"})
    seguinte = cliente.get(f"/simulado/{rodada}").text
    assert f'name="questao_id" value="{segunda}"' in seguinte

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": segunda, "letra": "c"})
    ultima = cliente.get(f"/simulado/{rodada}?ver={segunda}").text
    assert "Ver o resultado &rarr;" in ultima


def test_ver_questao_ainda_nao_respondida_mostra_a_questao(cliente):
    """O `ver` so mostra correcao de letra gravada - nunca a resposta antes."""
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)

    tela = cliente.get(f"/simulado/{rodada}?ver={primeira}").text

    assert "Acertou" not in tela and "Errou" not in tela
    assert 'name="letra" value="c"' in tela


# --- na rodada que mede: so no fim --------------------------------------------

@pytest.mark.parametrize("tipo", servico.simulado.RODADAS_QUE_MEDEM)
def test_a_rodada_que_mede_nao_corrige_na_hora(cliente, tipo):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"),
                     filtros={"rodada": tipo})
    primeira, segunda = _ids(rodada)

    resposta = cliente.post(f"/simulado/{rodada}/responder",
                            data={"questao_id": primeira, "letra": "a"},
                            follow_redirects=False)
    assert resposta.headers["location"] == f"/simulado/{rodada}"

    # Nem pedindo: o `ver` e ignorado, e a tela segue para a proxima.
    tela = cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    assert "Errou" not in tela
    assert f'name="questao_id" value="{segunda}"' in tela
    # A bolinha da respondida fica cinza: a cor entregaria o resultado.
    assert 'class="errada' not in tela and 'class="feita' in tela
    assert "rodada que mede" in tela


# --- o "vou no chute" ----------------------------------------------------------

def test_o_chute_fica_gravado_ao_lado_do_acerto(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, segunda = _ids(rodada)

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": primeira, "letra": "c", "chutei": "1"})
    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": segunda, "letra": "a"})

    resumo = servico.resumo_do_simulado(rodada)
    assert (resumo["acertos"], resumo["chutes"], resumo["acertos_no_chute"]) == (1, 1, 1)
    with sessao() as s:
        chutes = dict(s.execute(
            select(RespostaDeSimulado.questao_id, RespostaDeSimulado.chutou)
            .where(RespostaDeSimulado.simulado_id == rodada)).all())
    assert chutes == {primeira: True, segunda: False}


def test_a_correcao_e_o_relatorio_dizem_que_foi_no_chute(cliente):
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": primeira, "letra": "c", "chutei": "1"})

    assert "Foi no chute" in cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    relatorio = cliente.get(f"/simulado/{rodada}").text
    assert "1 no chute, 1 acertada" in relatorio


def test_errar_no_chute_abre_o_caderno_com_o_motivo_chutei(cliente):
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": primeira, "letra": "a", "chutei": "1"})
    tela = cliente.get(f"/simulado/{rodada}?ver={primeira}").text

    assert "motivo=chutei" in tela


def test_o_chute_vai_e_volta_no_backup(banco_temporario, tmp_path):
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)
    servico.responder(rodada, primeira, "c", chutou=True)
    arquivo = tmp_path / "simulados.json"
    acervo.exportar_simulados(arquivo)

    with sessao() as s:
        s.get(RespostaDeSimulado, 1).chutou = None
    acervo.importar_simulados(arquivo)

    with sessao() as s:
        assert s.get(RespostaDeSimulado, 1).chutou is True


# --- o andamento ---------------------------------------------------------------

def test_o_andamento_conta_os_acertos_seguidos(banco_temporario):
    questoes = [_questao(n, impressao=f"i{n}") for n in range(1, 6)]
    rodada = _rodada(*questoes)
    ids = _ids(rodada)
    for questao_id, letra in zip(ids[:4], "acccc"):
        servico.responder(rodada, questao_id, letra)

    andamento = servico.metricas.andamento_da_rodada(rodada)

    assert andamento["marcas"] == ["errada", "certa", "certa", "certa", None]
    assert andamento["seguidas"] == 3
