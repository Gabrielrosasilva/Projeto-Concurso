"""As geradas que eu nunca fiz saem primeiro, e a faixa avisa do estoque.

Decisao 142: o sorteio poe as nunca respondidas na frente; so quando acabam
ele repete, comecando pelas que eu errei da ultima vez. Com metade feita, a
faixa diz "vamos fazer mais algumas"; com todas, "esta na hora de criar mais"
- e nos dois casos os 3 passos para gerar vem junto.
"""
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import fichas, servico
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from tests.test_treinar_pelo_no import DOLO, TENTATIVA, _gerada


@pytest.fixture
def cliente(banco_temporario):
    from radar.web.app import app

    return TestClient(app)


def _id(numero: int) -> int:
    with sessao() as s:
        return s.scalar(select(QuestaoGerada.id)
                        .where(QuestaoGerada.impressao == f"gerada{numero}"))


def _ja_fiz(numero: int, acertou: bool = True, dia: int = 1):
    """Uma resposta a gerada `numero`, numa rodada propria."""
    with sessao() as s:
        rodada = Simulado(filtros={"geradas": True})
        s.add(rodada)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=rodada.id, questao_id=_id(numero), ordem=1, gerada=True,
            escolhida="c" if acertou else "a", acertou=acertou,
            respondida_em=datetime(2026, 10, dia, 20, tzinfo=timezone.utc)))


def _sorteadas(quantidade: int, no: str = DOLO) -> set[int]:
    rodada = servico.geradas.criar_simulado(quantidade=quantidade, conteudo=no)
    with sessao() as s:
        return set(s.scalars(select(RespostaDeSimulado.questao_id)
                             .where(RespostaDeSimulado.simulado_id == rodada.id)))


# --- o sorteio -----------------------------------------------------------------

def test_as_nunca_feitas_saem_primeiro(banco_temporario):
    for n in range(1, 7):
        _gerada(n, DOLO)
    for n in (1, 2, 3, 4):
        _ja_fiz(n)

    # Varias vezes: o sorteio e aleatorio dentro do grupo, nunca entre grupos.
    for _ in range(10):
        assert _sorteadas(2) == {_id(5), _id(6)}


def test_quando_acabam_as_novas_repete_comecando_pelas_erradas(banco_temporario):
    for n in range(1, 5):
        _gerada(n, DOLO)
    _ja_fiz(1, acertou=True, dia=1)
    _ja_fiz(2, acertou=False, dia=2)
    _ja_fiz(3, acertou=True, dia=3)

    for _ in range(10):
        # A 4 nunca foi feita; depois dela, a 2, que errei.
        assert _sorteadas(2) == {_id(4), _id(2)}


def test_das_acertadas_repete_a_mais_antiga(banco_temporario):
    for n in range(1, 4):
        _gerada(n, DOLO)
    _ja_fiz(1, dia=5)
    _ja_fiz(2, dia=1)
    _ja_fiz(3, dia=3)

    assert _sorteadas(1) == {_id(2)}


def test_o_que_conta_e_a_ultima_resposta(banco_temporario):
    """Errei e depois acertei: ja revisei, nao e mais "errada"."""
    for n in range(1, 3):
        _gerada(n, DOLO)
    _ja_fiz(1, acertou=False, dia=1)
    _ja_fiz(1, acertou=True, dia=4)
    _ja_fiz(2, acertou=False, dia=2)

    assert _sorteadas(1) == {_id(2)}


def test_o_treinar_geral_tambem_poe_as_novas_na_frente(banco_temporario):
    for n in range(1, 4):
        _gerada(n, DOLO)
    for n in range(4, 7):
        _gerada(n, TENTATIVA)
    for n in (1, 2, 4, 5):
        _ja_fiz(n)

    rodada = servico.geradas.criar_simulado(quantidade=2, conteudos=[DOLO, TENTATIVA])
    with sessao() as s:
        ids = set(s.scalars(select(RespostaDeSimulado.questao_id)
                            .where(RespostaDeSimulado.simulado_id == rodada.id)))
    assert ids == {_id(3), _id(6)}


# --- a conta e o aviso ---------------------------------------------------------

def test_conta_questoes_diferentes_e_nao_respostas(banco_temporario):
    for n in range(1, 5):
        _gerada(n, DOLO)
    _ja_fiz(1)
    _ja_fiz(1, dia=2)
    _gerada(9, DOLO, rejeitada=True)
    _ja_fiz(9)

    assert servico.metricas.geradas_feitas_por_no([DOLO]) == {DOLO: 1}


@pytest.mark.parametrize("feitas, aviso", [(0, None), (1, None), (2, "metade"),
                                           (3, "metade"), (4, "todas")])
def test_o_aviso_pela_metade_e_por_todas(feitas, aviso):
    [no] = fichas.geradas_por_no(10, [DOLO], {DOLO: 4}, {DOLO: feitas})
    assert no.aviso == aviso


def test_com_aviso_vem_o_pedido_para_gerar_mais(banco_temporario):
    """O no tinha o bastante (nada a pedir); com metade feita, pede."""
    [sem_ter_feito] = fichas.geradas_por_no(5, [DOLO], {DOLO: 10}, {})
    [metade] = fichas.geradas_por_no(5, [DOLO], {DOLO: 10}, {DOLO: 5})

    assert sem_ter_feito.comando is None
    assert metade.pedir == fichas.PEDIDO_MINIMO_DE_GERADAS
    assert "gerar --pedido" in metade.comando
    assert metade.frase_do_aviso == fichas.FRASE_FEZ_METADE


def test_o_relatorio_da_rodada_diz_o_estoque_e_os_passos(cliente):
    for n in range(1, 3):
        _gerada(n, DOLO)
    rodada = servico.geradas.criar_simulado(quantidade=2, conteudo=DOLO)
    for questao_id in (_id(1), _id(2)):
        servico.responder(rodada.id, questao_id, "c")

    texto = cliente.get(f"/simulado/{rodada.id}").text

    assert "você já fez 2 de 2" in texto
    assert fichas.FRASE_FEZ_TODAS in texto
    assert "gerar --pedido" in texto


def test_a_faixa_da_hoje_avisa_e_traz_os_passos(cliente, monkeypatch):
    """O cronograma real de 05/10: o bonus tem o no das tabelas-verdade."""
    from radar.servico import cronograma as diario

    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 5))
    tabelas = "Raciocínio Lógico > Tabelas-verdade"
    for n in (1, 2):
        _gerada(n, tabelas, materia="Raciocínio Lógico")
        _ja_fiz(n)

    html = cliente.get("/hoje?data=2026-10-05").text

    assert "você já fez 2" in html
    assert fichas.FRASE_FEZ_TODAS in html
    assert '--assunto "Tabelas-verdade"' in html or "--assunto &#34;Tabelas-verdade&#34;" in html
