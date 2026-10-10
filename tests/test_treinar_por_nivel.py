"""Treinar por nivel: o seletor, o sorteio, o "so havia N" e o acerto por
nivel (decisao 151).

Um nivel so traz as daquele nivel, na ordem da decisao 142 (as nunca feitas
primeiro), e nunca completa com outro: com menos do que pedi, a rodada vem
com as que ha e a tela diz "so havia N dificeis", com os 3 passos daquele
nivel. A misturada traz todas, de qualquer nivel. O acerto por nivel e mais
um numero a parte, contado no metricas.
"""
import html
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import fichas, servico
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.web.app import app
from tests.test_geradas_da_faixa import em_05_10  # noqa: F401
from tests.test_treinar_pelo_no import DOLO, TENTATIVA, _gerada


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def _id(numero: int) -> int:
    with sessao() as s:
        return s.scalar(select(QuestaoGerada.id)
                        .where(QuestaoGerada.impressao == f"gerada{numero}"))


def _da_rodada(rodada) -> set[int]:
    with sessao() as s:
        return set(s.scalars(select(RespostaDeSimulado.questao_id)
                             .where(RespostaDeSimulado.simulado_id == rodada.id)))


def _estoque():
    """No do dolo: 2 faceis, 3 medias, 2 dificeis e 1 sem nivel."""
    niveis = ["facil", "facil", "media", "media", "media", "dificil", "dificil", None]
    for numero, nivel in enumerate(niveis, start=1):
        _gerada(numero, DOLO, nivel=nivel)


# --- o sorteio ----------------------------------------------------------------

def test_um_nivel_so_traz_so_as_daquele_nivel(banco_temporario):
    _estoque()

    rodada = servico.geradas.criar_simulado(quantidade=2, conteudo=DOLO, nivel="dificil")

    assert _da_rodada(rodada) == {_id(6), _id(7)}
    assert rodada.filtros["nivel"] == "dificil" and "faltou" not in rodada.filtros


def test_a_misturada_traz_todas_inclusive_as_sem_nivel(banco_temporario):
    _estoque()

    rodada = servico.geradas.criar_simulado(quantidade=8, conteudo=DOLO)

    assert _da_rodada(rodada) == {_id(n) for n in range(1, 9)}
    assert rodada.filtros["nivel"] == "misturada"


def test_dentro_do_nivel_as_nunca_feitas_saem_primeiro(banco_temporario):
    _estoque()
    with sessao() as s:
        antiga = Simulado(filtros={"geradas": True})
        s.add(antiga)
        s.flush()
        s.add(RespostaDeSimulado(simulado_id=antiga.id, questao_id=_id(3), ordem=1,
                                 gerada=True, escolhida="c", acertou=True,
                                 respondida_em=datetime(2026, 10, 1, tzinfo=timezone.utc)))

    for _ in range(10):
        rodada = servico.geradas.criar_simulado(quantidade=2, conteudo=DOLO, nivel="media")
        assert _da_rodada(rodada) == {_id(4), _id(5)}


def test_o_treinar_geral_tambem_respeita_o_nivel(banco_temporario):
    _estoque()
    _gerada(20, TENTATIVA, nivel="dificil")
    _gerada(21, TENTATIVA, nivel="facil")

    rodada = servico.geradas.criar_simulado(quantidade=10, conteudos=[DOLO, TENTATIVA],
                                            nivel="dificil")

    assert _da_rodada(rodada) == {_id(6), _id(7), _id(20)}


# --- o "so havia N" -------------------------------------------------------------

def test_com_menos_do_que_pedi_vem_as_que_ha_e_o_aviso(banco_temporario):
    _estoque()

    rodada = servico.geradas.criar_simulado(quantidade=10, conteudo=DOLO, nivel="dificil")
    falta = servico.geradas.falta_da_rodada(rodada)

    assert len(_da_rodada(rodada)) == 2                 # nunca completa com outro nivel
    assert falta.frase == "Só havia 2 difíceis neste assunto: a rodada veio com as que há."
    [comando] = falta.comandos
    assert comando.endswith("--quantas 8 --nivel dificil")
    assert '--subassunto "Dolo e culpa"' in comando


def test_o_aviso_pede_no_minimo_5(banco_temporario):
    _estoque()

    rodada = servico.geradas.criar_simulado(quantidade=3, conteudo=DOLO, nivel="dificil")
    falta = servico.geradas.falta_da_rodada(rodada)

    assert falta.frase.startswith("Só havia 2 difíceis")
    assert falta.comandos[0].endswith(f"--quantas {fichas.PEDIDO_MINIMO_DE_GERADAS} --nivel dificil")


def test_um_so_diz_no_singular():
    falta = fichas.FaltaDeGeradas(nivel="media", pedidas=5, havia=1, nos=(DOLO,))
    assert falta.frase == "Só havia 1 média neste assunto: a rodada veio com ela."


def test_a_questao_e_o_resultado_dizem_o_que_faltou(cliente):
    _estoque()
    rodada = servico.geradas.criar_simulado(quantidade=10, conteudo=DOLO, nivel="dificil")

    antes = html.unescape(cliente.get(f"/simulado/{rodada.id}").text)
    assert "Só havia 2 difíceis neste assunto" in antes
    assert "Nada foi completado com outro nível." in antes
    assert "--quantas 8 --nivel dificil" in antes
    assert "nível: Difícil" in antes

    for questao in _da_rodada(rodada):
        cliente.post(f"/simulado/{rodada.id}/responder",
                     data={"questao_id": questao, "letra": "c"})
    resultado = html.unescape(cliente.get(f"/simulado/{rodada.id}").text)
    assert "Resultado da rodada" in resultado
    assert "Só havia 2 difíceis neste assunto" in resultado


def test_sem_nenhuma_do_nivel_nao_ha_rodada_e_a_tela_diz_com_os_passos(cliente):
    _gerada(1, DOLO, nivel="facil")

    resposta = cliente.post("/geradas/treinar", data={
        "conteudo": DOLO, "quantidade": "6", "nivel": "dificil"}, follow_redirects=False)

    assert resposta.status_code == 303
    destino = resposta.headers["location"]
    assert destino.startswith("/geradas?recado=sem_do_nivel")
    tela = html.unescape(cliente.get(destino).text)
    assert "Não há nenhuma questão difícil neste assunto ainda." in tela
    assert "--quantas 6 --nivel dificil" in tela


def test_a_misturada_sem_nenhuma_continua_o_recado_de_sempre(cliente):
    resposta = cliente.post("/geradas/treinar", data={"conteudo": DOLO, "quantidade": "5"},
                            follow_redirects=False)
    assert resposta.headers["location"] == "/geradas?recado=nada_no_no"


# --- os seletores -------------------------------------------------------------

def test_o_treinar_com_as_que_tenho_tem_o_seletor_de_nivel(cliente):
    _gerada(1, DOLO, nivel="facil")

    tela = cliente.get("/geradas").text
    treinar = tela.split('id="treinar"')[1].split("</section>")[0]

    assert '<select name="nivel">' in treinar
    for rotulo in ("Misturada", "Fácil", "Média", "Difícil"):
        assert f">{rotulo}</option>" in treinar


def test_os_botoes_da_faixa_tem_o_seletor_pequeno(em_05_10):
    """O bonus de 05/10 tem nos do plano; com geradas em dois deles, a faixa
    mostra o "Treinar no radar" de cada um e o "Treinar geral"."""
    for numero, no in enumerate(("Raciocínio Lógico > Tabelas-verdade",
                                 "Raciocínio Lógico > Equivalências lógicas"), start=1):
        _gerada(numero, no, materia="Raciocínio Lógico")

    tela = TestClient(app).get("/hoje?data=2026-10-05").text
    formularios = tela.split('class="treinar-no-radar"')[1:]

    assert formularios, "a faixa deveria mostrar o Treinar no radar"
    for formulario in formularios:
        bloco = formulario.split("</form>")[0]
        assert '<select name="nivel" aria-label="Nível">' in bloco


def test_o_nivel_da_faixa_chega_a_rodada(cliente):
    _estoque()

    resposta = cliente.post("/geradas/treinar", data={
        "conteudo": DOLO, "quantidade": "2", "nivel": "facil", "data": "2026-10-05",
        "bloco": "manha", "indice": "0", "titulo": "Fixação"}, follow_redirects=False)

    rodada_id = int(resposta.headers["location"].rsplit("/", 1)[1])
    with sessao() as s:
        rodada = s.get(Simulado, rodada_id)
        assert rodada.filtros["nivel"] == "facil"
        assert rodada.filtros["da_faixa"]["titulo"] == "Fixação"


# --- o acerto por nivel ---------------------------------------------------------

def test_o_resultado_mostra_o_acerto_por_nivel(cliente):
    _gerada(1, DOLO, nivel="facil")
    _gerada(2, DOLO, nivel="dificil")
    _gerada(3, DOLO)                                    # sem nivel
    rodada = servico.geradas.criar_simulado(quantidade=3, conteudo=DOLO)
    for numero, letra in ((1, "c"), (2, "a"), (3, "c")):   # a certa e "c"
        cliente.post(f"/simulado/{rodada.id}/responder",
                     data={"questao_id": _id(numero), "letra": letra})

    por_nivel = servico.metricas.acerto_das_geradas_por_nivel(rodada.id)
    assert [(n.rotulo, n.acertos, n.respondidas) for n in por_nivel] == [
        ("Fácil", 1, 1), ("Difícil", 0, 1), ("sem nível", 1, 1)]

    tela = cliente.get(f"/simulado/{rodada.id}").text
    assert "Por nível" in tela
    parte = tela.split("Por nível")[1].split("</section>")[0]
    assert "<td>Fácil</td>" in parte and "<td>Difícil</td>" in parte
    assert "<td>sem nível</td>" in parte


def test_a_rodada_de_questoes_reais_nao_tem_acerto_por_nivel(banco_temporario):
    assert servico.metricas.acerto_das_geradas_por_nivel(999) == []
