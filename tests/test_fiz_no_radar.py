"""O que eu fiz no radar e o que eu fiz fora dele, cada um na sua linha
(decisao 138, 06/10/2026).

O caso que motivou: o 06/10. 12 geradas respondidas no radar e anotadas de
novo na faixa ("fiz 12, acertei 11"): o "Fiz hoje" mostrava 24, e no meio do
treino ja mostrava 5 - o treino de IA somado na mesma linha das reais. Estes
testes seguram o conserto:

  * a tela e o `radar hoje` mostram as reais, o treino de IA e o total em
    linhas proprias;
  * a faixa feita so no radar fecha com o "fiz" vazio, e guarda so o tempo -
    sem rodada da faixa, o vazio continua recusado (regra da 1D);
  * a conferencia nao chama essa faixa de "feita com 0 questoes";
  * o treino de IA de um tema conta as respostas as geradas dos nos dele.

As datas sao fixas: nada aqui depende do dia em que o teste roda.
"""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from radar import cronograma
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import conferencia, metricas
from radar.servico import cronograma as diario
from radar.util import fuso_local
from radar.web.app import app

SEG = date(2026, 9, 28)
DEPOIS = date(2026, 9, 30)
NO = "Língua Portuguesa > Vozes do verbo"


@pytest.fixture
def plano():
    return cronograma.carregar()


def _primeira_faixa_de_questoes(plano):
    dia = plano.dia(SEG)
    for bloco in cronograma.TODOS_OS_BLOCOS:
        for indice, faixa in enumerate(getattr(dia, bloco)):
            if cronograma.tem_acerto(faixa) and faixa.questoes:
                return bloco, indice, faixa
    raise AssertionError("o 28/09 do plano real nao tem faixa de questoes")


def _treino_da_faixa(bloco, indice, titulo, respostas):
    """Uma rodada de geradas aberta pelo botao da faixa: [acertou, ...]."""
    quando = datetime(2026, 9, 28, 10, 40, tzinfo=fuso_local())
    with sessao() as s:
        simulado = Simulado(filtros={"geradas": True, "da_faixa": {
            "data": SEG.isoformat(), "bloco": bloco, "indice": indice, "titulo": titulo}})
        s.add(simulado)
        s.flush()
        for ordem, acertou in enumerate(respostas, start=1):
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=ordem, gerada=True, ordem=ordem,
                escolhida="a", acertou=acertou, respondida_em=quando))


def test_a_faixa_feita_no_radar_fecha_com_o_fiz_vazio(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _treino_da_faixa(bloco, indice, faixa.titulo, [True] * 11 + [False])

    assert diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="",
                               plano=plano, hoje=DEPOIS)

    feita = diario.valores_das_faixas(plano.dia(SEG), diario.estado_do_dia(SEG))[(bloco, indice)]
    assert (feita.questoes, feita.acertos, feita.no_radar) == (0, None, True)
    # As 12 contam uma vez so, no treino de IA; a faixa da so o tempo.
    conta = metricas.do_dia(SEG, plano)
    assert (conta.reais.questoes, conta.treino_ia.ia, conta.treino_ia.ia_acertos) == (0, 12, 11)
    assert conta.total.questoes == 12
    assert feita.minutos and conta.minutos == feita.minutos


def test_sem_rodada_da_faixa_o_fiz_vazio_continua_recusado(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    # Treino da faixa de outro dia nao conta para esta.
    with pytest.raises(diario.RegistroInvalido, match="botão desta faixa"):
        diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="",
                            plano=plano, hoje=DEPOIS)
    with pytest.raises(diario.RegistroInvalido, match="0 questões"):
        diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="0",
                            plano=plano, hoje=DEPOIS)


def test_a_conferencia_nao_chama_a_feita_no_radar_de_zero(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _treino_da_faixa(bloco, indice, faixa.titulo, [True, False])
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, plano=plano, hoje=DEPOIS)

    (dia,) = conferencia.conferir(SEG, SEG, plano=plano, hoje=DEPOIS)

    assert conferencia.ZERO not in [a.tipo for a in dia.achados]


def test_a_tela_separa_as_reais_do_treino_de_ia(banco_temporario, plano, monkeypatch):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _treino_da_faixa(bloco, indice, faixa.titulo, [True] * 4 + [False])
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, plano=plano, hoje=DEPOIS)
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()))

    texto = TestClient(app).get("/hoje?data=2026-09-28").text

    assert "<b>Questões reais (Qconcursos e provas): nenhuma ainda</b>" in texto
    assert ("Treino de IA no radar: 5 questões = 4 acertos + 1 erro (80%), "
            "não entra no acerto.") in texto
    assert "Total do dia: 5 questões" in texto
    assert '<span class="resultado">feita no radar</span>' in texto
    assert "Fiz hoje" not in texto


def test_o_treino_de_ia_do_tema_conta_os_nos_dele(banco_temporario):
    with sessao() as s:
        no = QuestaoGerada(modo="do_zero", enunciado="a", impressao="g1", resposta="a",
                           conteudo=NO, materia="Língua Portuguesa")
        abaixo = QuestaoGerada(modo="do_zero", enunciado="b", impressao="g2", resposta="a",
                               conteudo=NO + " > Voz passiva", materia="Língua Portuguesa")
        fora = QuestaoGerada(modo="do_zero", enunciado="c", impressao="g3", resposta="a",
                             conteudo="Direito Penal > Crime", materia="Direito Penal")
        s.add_all([no, abaixo, fora])
        s.flush()
        quando = datetime(2026, 9, 28, 10, 0, tzinfo=fuso_local())
        # Uma rodada por resposta. A mesma gerada respondida duas vezes conta
        # uma no tema (a 1a vez) e uma na revisao (decisao 152).
        for questao, acertou, gerada in [(no, True, True), (no, False, True),
                                         (abaixo, True, True), (fora, True, True),
                                         # Real com o mesmo id da gerada: fica fora.
                                         (no, True, False)]:
            simulado = Simulado(filtros={"geradas": True})
            s.add(simulado)
            s.flush()
            s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=questao.id,
                                     gerada=gerada, ordem=1, escolhida="a",
                                     acertou=acertou, respondida_em=quando))

    treino = metricas.treino_ia_dos_nos([NO])
    assert (treino.respondidas, treino.acertos) == (2, 2)
    assert (treino.revisao, treino.revisao_acertos) == (1, 0)
    # O no de baixo junto com o de cima nao conta a resposta duas vezes.
    assert metricas.treino_ia_dos_nos([NO, NO + " > Voz passiva"]).respondidas == 2
    assert metricas.treino_ia_dos_nos([]).vazio
