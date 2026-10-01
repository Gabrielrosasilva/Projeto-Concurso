"""A fonte unica das metricas (Etapa 1C): uma conta, num lugar so.

O caso que motivou tudo e o 28/09: a tela mostrou "31 questoes, 13 acertos,
8 erros", e 13 + 8 nao da 31. Nao havia dado errado - as 10 que faltavam eram
de IA, e a linha nao dizia isso. Estes testes seguram a regra:

    questoes = acertos + erros + sem acerto anotado + treino de IA

O cronograma e o mini (tests/fixtures) e as datas sao fixas: nada aqui depende
do dia em que o teste roda.
"""
from datetime import date, datetime
from pathlib import Path

import pytest

from radar import cronograma
from radar.db import sessao
from radar.models import EstadoDoDia, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import extra as estudo_extra
from radar.servico import metricas
from radar.util import fuso_local

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
SEG = date(2026, 9, 28)
TER = date(2026, 9, 29)
HOJE = date(2026, 10, 3)


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


def _faixa(plano, bloco, indice, data=SEG):
    return getattr(cronograma.montar_dia(plano, data, 1), bloco)[indice]


def _anotar(plano, bloco, indice, questoes, acertos, consulta=False, data=SEG):
    faixa = _faixa(plano, bloco, indice, data)
    diario.anotar_faixa(data, bloco, indice, faixa.titulo, questoes=questoes,
                        acertos=acertos, consulta=consulta, plano=plano, hoje=HOJE)


def _responder(acertou, quando, gerada=False, questao_id=1, simulado_id=None):
    """Uma resposta dada no radar. `quando` None = rodada nao terminada."""
    with sessao() as s:
        if simulado_id is None:
            simulado = Simulado(filtros={})
            s.add(simulado)
            s.flush()
            simulado_id = simulado.id
        s.add(RespostaDeSimulado(
            simulado_id=simulado_id, questao_id=questao_id, gerada=gerada,
            ordem=1, escolhida="a" if quando else None,
            acertou=acertou if quando else None, respondida_em=quando,
        ))
    return simulado_id


def _as_21h(data=SEG, minuto=0):
    return datetime(data.year, data.month, data.day, 21, minuto, tzinfo=fuso_local())


def _fecha(numeros) -> bool:
    return numeros.questoes == (numeros.acertos + numeros.erros
                                + numeros.sem_resultado + numeros.ia)


# --- o 28/09 ------------------------------------------------------------------

def _o_dia_28(plano):
    """O dia como ele foi: Penal 11/6 e Portugues 10/7 anotados (Qconcursos),
    o Bonus marcado com 0 questoes, e 10 questoes de IA no radar (7 certas)."""
    _anotar(plano, "noite", 0, 11, 6)
    _anotar(plano, "noite", 2, 10, 7)
    _anotar(plano, "pos22", 1, 0, "")
    for n in range(10):
        _responder(n < 7, _as_21h(minuto=n), gerada=True, questao_id=n + 1)


def test_o_28_09_fecha_a_conta(banco_temporario, plano):
    _o_dia_28(plano)

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == 31
    assert (conta.total.acertos, conta.total.erros) == (13, 8)
    assert conta.total.ia == 10
    assert metricas.frase_da_conta(conta.total) == (
        "31 questões = 13 acertos + 8 erros + 10 de treino de IA")


def test_o_acerto_da_ia_e_um_segundo_numero(banco_temporario, plano):
    _o_dia_28(plano)

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.porcentagem == 62            # 13 de 21: so as reais
    assert conta.treino_ia.ia_acertos == 7
    assert metricas.frase_da_ia(conta.total) == (
        "treino de IA: 7 de 10 (70%), fora do acerto")


def test_o_bonus_com_zero_questoes_conta_os_minutos_e_nenhuma_questao(
        banco_temporario, plano):
    """A regra para a faixa marcada com 0 questoes e decidida na 1D; aqui so
    se garante que ela nao inventa questao."""
    _anotar(plano, "pos22", 1, 0, "")

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == 0
    assert conta.minutos > 0


# --- a regra do total, em todos os recortes -----------------------------------

def test_a_regra_fecha_em_todos_os_recortes(banco_temporario, plano):
    """Um dia com os quatro estados: acerto, erro, sem acerto anotado e IA."""
    _anotar(plano, "noite", 0, 15, None, consulta=True)       # sem resultado
    _anotar(plano, "noite", 2, 10, 2)
    estudo_extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                        minutos=30, questoes=12, acertos=9, onde="qconcursos",
                        plano=plano, hoje=HOJE)
    _responder(True, _as_21h(minuto=1))
    _responder(False, _as_21h(minuto=2))
    _responder(True, _as_21h(minuto=3), gerada=True)

    conta = metricas.do_dia(SEG, plano)

    for nome in ("faixas", "extra", "radar", "treino_ia", "sem_consulta"):
        assert _fecha(getattr(conta, nome)), nome
    for numeros in (conta.anotado, conta.total):
        assert _fecha(numeros)
    assert metricas.frase_da_conta(conta.total) == (
        "40 questões = 12 acertos + 12 erros + 15 sem acerto anotado "
        "+ 1 de treino de IA")
    # A meta olha so o que foi feito sem consulta: a faixa de 15 fica fora.
    assert conta.sem_consulta.questoes == 24


def test_o_total_e_a_soma_dos_recortes(banco_temporario, plano):
    _o_dia_28(plano)
    _responder(True, _as_21h(minuto=30))

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == (conta.anotado.questoes + conta.radar.questoes
                                    + conta.treino_ia.questoes)
    assert conta.total.acertos == conta.anotado.acertos + conta.radar.acertos


# --- o que nao conta ----------------------------------------------------------

def test_ia_nunca_entra_no_acerto(banco_temporario, plano):
    _responder(True, _as_21h(), gerada=True)

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == 1
    assert conta.total.medidas == 0
    assert conta.total.porcentagem is None
    assert conta.radar.questoes == 0


def test_rodada_nao_terminada_nao_conta(banco_temporario, plano):
    simulado = _responder(True, _as_21h())
    _responder(None, None, simulado_id=simulado, questao_id=2)

    assert metricas.do_dia(SEG, plano).total.questoes == 1


def test_linha_que_nao_fecha_e_acusada_e_nao_arredondada(banco_temporario, plano):
    """A conta antiga fazia max(medidas - acertos, 0) e escondia isto."""
    faixa = _faixa(plano, "noite", 2)
    with sessao() as s:
        s.add(EstadoDoDia(data=SEG, faixas_feitas=[{
            "bloco": "noite", "indice": 2, "titulo": faixa.titulo,
            "questoes": 10, "acertos": 12}]))

    with pytest.raises(metricas.ContaInconsistente, match="12 acertos em 10"):
        metricas.do_dia(SEG, plano)


# --- o dia e o de Florianopolis -------------------------------------------------

def test_resposta_as_22h_cai_no_dia_certo(banco_temporario, plano):
    """22h30 aqui e 1h30 do dia seguinte em UTC."""
    _responder(True, datetime(2026, 9, 28, 22, 30, tzinfo=fuso_local()))

    assert metricas.do_dia(SEG, plano).total.questoes == 1
    assert metricas.do_dia(TER, plano).total.questoes == 0


def test_resposta_a_meia_noite_e_do_dia_seguinte(banco_temporario, plano):
    _responder(True, datetime(2026, 9, 29, 0, 5, tzinfo=fuso_local()))

    assert metricas.do_dia(SEG, plano).total.questoes == 0
    assert metricas.do_dia(TER, plano).total.questoes == 1


# --- respostas: o volume ---------------------------------------------------------

def test_a_mesma_questao_em_duas_rodadas_sao_duas_respostas(banco_temporario, plano):
    _responder(False, _as_21h(minuto=1), questao_id=7)
    _responder(True, _as_21h(minuto=2), questao_id=7)

    conta = metricas.do_dia(SEG, plano)

    assert conta.radar.questoes == 2
    assert (conta.radar.acertos, conta.radar.erros) == (1, 1)


# --- mesmo periodo, mesmo numero -------------------------------------------------

def test_o_dia_e_o_mesmo_dentro_de_um_periodo_maior(banco_temporario, plano):
    """A semana soma a mesma lista que o dia: filtrar o periodo pelo dia da o
    numero do dia, e nao um parecido."""
    _o_dia_28(plano)
    _responder(True, _as_21h(TER))

    linhas = metricas.lancamentos(SEG, HOJE, plano)
    do_periodo = metricas.contar(l for l in linhas if l.data == SEG)

    assert do_periodo == metricas.do_dia(SEG, plano)
    assert metricas.contar(linhas).total.questoes == 32
