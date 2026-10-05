"""A faixa de Portugues que comeca pelas do radar (decisao 107).

O que estes testes seguram:
  - so a faixa de questoes de Portugues no Qconcursos ganha o comeco no radar;
  - a rodada tem so questao real da FEPESE do tema, do alvo primeiro, sem
    anulada e sem prova recusada, no maximo o numero do plano, e nao e
    recriada;
  - a questao que ja esta numa rodada de faixa, ou ja respondida, nao volta: a
    faixa da manha e a da noite do mesmo tema nao repetem;
  - a tela diz quantas no radar e quantas no Qconcursos.

Nenhum teste depende da data de hoje: a tela e conferida pelo texto que
aparece em qualquer dia, e nao pelo botao.
"""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from radar.cronograma import Faixa
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado
from radar.servico import faixa_no_radar
from radar.servico import simulado as servico_simulado
from radar.web.app import app
from tests.test_composicao import (CRASE, INTERPRETACAO, PORTUGUES,  # noqa: F401
                                   RACIOCINIO, acervo)

DIA = date(2026, 10, 6)


def _faixa(nos, questoes=6, bloco="manha", titulo="Questões de teste", **mais):
    campos = dict(bloco=bloco, tipo="questoes", titulo=titulo, materia=PORTUGUES,
                  questoes=questoes, onde="qconcursos", nos=nos)
    campos.update(mais)
    return Faixa(**campos)


def _questoes(rodada):
    with sessao() as s:
        ids = list(s.scalars(select(RespostaDeSimulado.questao_id)
                             .where(RespostaDeSimulado.simulado_id == rodada.id)
                             .order_by(RespostaDeSimulado.ordem)))
        return [s.get(QuestaoDeProva, i) for i in ids]


def test_so_a_faixa_de_questoes_de_portugues_no_qconcursos():
    assert faixa_no_radar.aceita(_faixa([INTERPRETACAO]))
    assert faixa_no_radar.aceita(_faixa([INTERPRETACAO], tipo="revisao"))
    assert not faixa_no_radar.aceita(_faixa([INTERPRETACAO], onde="radar"))
    assert not faixa_no_radar.aceita(_faixa([INTERPRETACAO], tipo="simulado"))
    assert not faixa_no_radar.aceita(_faixa([INTERPRETACAO], materia=RACIOCINIO))
    assert not faixa_no_radar.aceita(_faixa([INTERPRETACAO], questoes=None, duracao=30))


def test_a_rodada_tem_as_reais_do_tema_do_alvo_primeiro_e_nao_e_recriada(acervo):
    faixa = _faixa([INTERPRETACAO])

    rodada = faixa_no_radar.criar_rodada(DIA, "manha", 0, faixa)
    de_novo = faixa_no_radar.criar_rodada(DIA, "manha", 0, faixa)

    assert rodada.id == de_novo.id
    questoes = _questoes(rodada)
    # 3 do alvo e 1 do complementar aceito; a anulada fica de fora.
    assert len(questoes) == 4
    assert [q.evidencia for q in questoes] == ["alvo", "alvo", "alvo", "complementar"]
    assert not any(q.anulada for q in questoes)
    assert rodada.filtros["rodada"] == faixa_no_radar.RODADA
    assert rodada.filtros["do_plano"] == 6 and rodada.filtros["proprias"] == 3


def test_no_maximo_o_numero_do_plano(acervo):
    rodada = faixa_no_radar.criar_rodada(DIA, "manha", 0, _faixa([INTERPRETACAO], questoes=2))
    assert len(_questoes(rodada)) == 2


def test_a_manha_e_a_noite_do_mesmo_tema_nao_repetem(acervo):
    manha = faixa_no_radar.criar_rodada(DIA, "manha", 0, _faixa([INTERPRETACAO], questoes=3))
    noite = faixa_no_radar.criar_rodada(DIA, "noite", 0,
                                        _faixa([INTERPRETACAO], bloco="noite", titulo="Outra"))

    assert not {q.id for q in _questoes(manha)} & {q.id for q in _questoes(noite)}
    assert len(_questoes(noite)) == 1
    # Acabou o tema: a proxima faixa e toda no Qconcursos.
    assert faixa_no_radar.criar_rodada(DIA, "noite", 1,
                                       _faixa([INTERPRETACAO], bloco="noite",
                                              titulo="Mais uma")) is None


def test_a_respondida_nao_volta(acervo):
    rodada = faixa_no_radar.criar_rodada(DIA, "manha", 0, _faixa([CRASE]))
    for q in _questoes(rodada):
        servico_simulado.responder(rodada.id, q.id, q.resposta)

    outro_dia = faixa_no_radar.criar_rodada(date(2026, 10, 13), "manha", 0, _faixa([CRASE]))

    assert outro_dia is None


def test_a_tela_diz_quantas_no_radar_e_quantas_no_qconcursos(acervo):
    # 08/10 no plano real: a noite e "Interpretação de texto (cronometrada)",
    # no assunto inteiro - no acervo do teste, 4 questoes reais; o plano pede 10.
    pagina = TestClient(app).get("/hoje?data=2026-10-08").text

    assert "Comece pelas <b>4</b> questões reais da FEPESE" in pagina
    assert "as outras 6 no Qconcursos" in pagina
    assert "anote só as do Qconcursos" in pagina
