"""O acerto acumulado conta QUESTAO, pela ultima resposta de cada uma.

Antes contava tentativa: refazer a mesma questao 4 vezes valia 4, e refazer
questao ja decorada inflava o acerto. As tentativas continuam gravadas: a
evolucao semanal conta toda resposta.
"""
from datetime import date, datetime, timezone

import pytest

from radar import servico
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado

CADERNO = "https://fepese.test/ap2019.pdf"
DIA = date(2026, 10, 1)


def _questao(materia="Direito Penal", enunciado="questao?") -> int:
    with sessao() as s:
        q = QuestaoDeProva(
            prova_url=CADERNO, banca="FEPESE", ano=2019, numero=1,
            materia=materia, enunciado=enunciado,
            alternativas={"a": "x", "b": "y"}, resposta="a", impressao="q1",
        )
        s.add(q)
        s.flush()
        return q.id


def _simulado_com(questao_id: int, acertou: bool, quando: datetime) -> int:
    """Um simulado de uma questao, respondida em `quando`."""
    with sessao() as s:
        sim = Simulado(filtros={})
        s.add(sim)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=sim.id, questao_id=questao_id, ordem=1,
            escolhida="a" if acertou else "b", acertou=acertou,
            respondida_em=quando,
        ))
        return sim.id


def _as(hora: int, dia: date = DIA) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, tzinfo=timezone.utc)


def _penal():
    (linha,) = servico.desempenho()
    return linha.respondidas, linha.acertos


# --- o acumulado por materia ------------------------------------------------

def test_errou_e_depois_acertou_conta_uma_questao_certa(banco_temporario):
    q = _questao()
    _simulado_com(q, False, _as(10))
    _simulado_com(q, True, _as(14))
    assert _penal() == (1, 1)


def test_acertou_e_depois_errou_conta_uma_questao_errada(banco_temporario):
    q = _questao()
    _simulado_com(q, True, _as(10))
    _simulado_com(q, False, _as(14))
    assert _penal() == (1, 0)


def test_empate_de_horario_vale_a_resposta_de_maior_id(banco_temporario):
    q = _questao()
    _simulado_com(q, False, _as(10))
    _simulado_com(q, True, _as(10))           # mesmo instante, gravada depois
    assert _penal() == (1, 1)


def test_nenhuma_tentativa_e_apagada(banco_temporario):
    q = _questao()
    for hora, acertou in ((9, False), (10, True), (11, True), (12, True)):
        _simulado_com(q, acertou, _as(hora))
    with sessao() as s:
        assert s.query(RespostaDeSimulado).count() == 4
    assert _penal() == (1, 1)


def test_o_relatorio_de_um_simulado_conta_as_respostas_dele(banco_temporario):
    q = _questao()
    primeiro = _simulado_com(q, False, _as(10))
    _simulado_com(q, True, _as(14))

    (linha,) = servico.desempenho(simulado_id=primeiro)
    assert (linha.respondidas, linha.acertos) == (1, 0)


# --- o acerto por assunto ---------------------------------------------------

@pytest.mark.parametrize("ordem, esperado", [
    ((False, True), (1, 1)),
    ((True, False), (1, 0)),
])
def test_o_acerto_por_assunto_segue_a_mesma_regra(banco_temporario, ordem, esperado):
    """O acerto por assunto do Onde estudar e o do desempenho por conteudo
    (decisao 74): a ultima resposta de cada questao, no no dela."""
    from radar.servico import desempenho_por_conteudo as por_conteudo
    from tests.test_foco import _classificar

    q = _questao(materia="Língua Portuguesa",
                 enunciado="Assinale a alternativa em que o uso da crase está correto.")
    _classificar(q, "Língua Portuguesa > Emprego da crase")
    _simulado_com(q, ordem[0], _as(10))
    _simulado_com(q, ordem[1], _as(14, date(2026, 10, 3)))

    no = por_conteudo.por_no(por_conteudo.SEMPRE, hoje=date(2026, 10, 4))[
        "Língua Portuguesa > Emprego da crase"]

    assert (no.respostas, no.acertos) == esperado
    # A data e a da tentativa mais recente, para o fator de tempo.
    assert max(no.radar.dias) == date(2026, 10, 3)
