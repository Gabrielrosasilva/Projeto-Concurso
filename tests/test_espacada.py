"""Revisao espacada 1-7-30 e o fator de tempo da prioridade.

As respostas sao gravadas com a data escolhida pelo teste: a agenda sai do
historico, e o que se testa e a regra em cima dele - sem esperar dias.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from radar import foco, onde_estudar, servico
from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import espacada, inicio

from tests.test_foco import _concurso, com_quadro_do_edital  # noqa: F401

CADERNO = "https://fepese.test/ap2019.pdf"
DIA = date(2026, 10, 1)


def _questao(numero: int, materia="Direito Penal", **mais) -> int:
    with sessao() as s:
        q = QuestaoDeProva(
            prova_url=CADERNO, banca="FEPESE", concurso_url=_concurso().url,
            ano=2019, cargo="Agente Penitenciário", numero=numero,
            materia=materia, enunciado=f"questao {numero}?",
            alternativas={"a": "x", "b": "y"}, resposta="a",
            impressao=f"q{numero}", **mais,
        )
        s.add(q)
        s.flush()
        return q.id


def _respondi(questao_id: int, acertou: bool, dia: date, gerada=False):
    """Uma resposta gravada ao meio-dia de `dia`, fora do horario-limite."""
    with sessao() as s:
        sim = Simulado(filtros={})
        s.add(sim)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=sim.id, questao_id=questao_id, ordem=1, gerada=gerada,
            escolhida="a" if acertou else "b", acertou=acertou,
            respondida_em=datetime(dia.year, dia.month, dia.day, 15, tzinfo=timezone.utc),
        ))


@pytest.fixture
def acervo(banco_temporario):
    with sessao() as s:
        s.add(_concurso())
    return [_questao(n) for n in range(1, 6)]


# --- a agenda ---------------------------------------------------------------

def test_errou_volta_amanha(acervo):
    _respondi(acervo[0], False, DIA)

    (r,) = espacada.agenda()
    assert (r.etapa, r.vence_em) == (1, DIA + timedelta(days=1))
    assert not r.pendente(DIA)
    assert r.pendente(DIA + timedelta(days=1))


def test_acertou_na_data_passa_para_7_e_depois_30(acervo):
    _respondi(acervo[0], False, DIA)
    _respondi(acervo[1], True, DIA + timedelta(days=1))
    (r,) = espacada.agenda()
    assert (r.etapa, r.vence_em) == (2, DIA + timedelta(days=8))

    _respondi(acervo[2], True, DIA + timedelta(days=8))
    (r,) = espacada.agenda()
    assert (r.etapa, r.vence_em) == (3, DIA + timedelta(days=38))


def test_passou_da_de_30_sai_da_agenda(acervo):
    _respondi(acervo[0], False, DIA)
    _respondi(acervo[1], True, DIA + timedelta(days=1))
    _respondi(acervo[2], True, DIA + timedelta(days=8))
    _respondi(acervo[3], True, DIA + timedelta(days=38))
    assert espacada.agenda() == []


def test_acertar_antes_do_vencimento_nao_conta(acervo):
    """No mesmo dia do erro e treino, nao revisao."""
    _respondi(acervo[0], False, DIA)
    _respondi(acervo[1], True, DIA)
    (r,) = espacada.agenda()
    assert r.etapa == 1


def test_errar_de_novo_volta_ao_comeco(acervo):
    _respondi(acervo[0], False, DIA)
    _respondi(acervo[1], True, DIA + timedelta(days=1))
    _respondi(acervo[2], False, DIA + timedelta(days=3))
    (r,) = espacada.agenda()
    assert (r.etapa, r.vence_em) == (1, DIA + timedelta(days=4))


def test_sem_assunto_revisa_a_materia(acervo):
    """Toda questao de Direito esta sem assunto hoje: agenda a materia."""
    _respondi(acervo[0], False, DIA)
    (r,) = espacada.agenda()
    assert r.assunto is None and r.nome == "Direito Penal (sem assunto)"


def test_gerada_e_anulada_nao_agendam(acervo):
    with sessao() as s:
        s.add(QuestaoGerada(modo="variacao", enunciado="gerada?", resposta="a",
                            impressao="g1", modelo="teste", materia="Direito Penal"))
    _respondi(1, False, DIA, gerada=True)
    anulada = _questao(99, anulada=True)
    _respondi(anulada, False, DIA)
    assert espacada.agenda() == []


def test_descartar_limpa_a_agenda(acervo):
    """A agenda sai das respostas: apagou a rodada, apagou o agendamento."""
    _respondi(acervo[0], False, DIA)
    assert espacada.agenda()
    servico.descartar_todos()
    assert espacada.agenda() == []


def test_a_rodada_de_revisao_comeca_pelo_erro(acervo):
    _respondi(acervo[0], False, DIA)
    assert espacada.criar_simulado_de_revisao(DIA) is None     # ainda nao venceu

    rodada = espacada.criar_simulado_de_revisao(DIA + timedelta(days=1))

    with sessao() as s:
        ids = [r.questao_id for r in s.scalars(
            select(RespostaDeSimulado).where(RespostaDeSimulado.simulado_id == rodada.id)
            .order_by(RespostaDeSimulado.ordem))]
    assert ids[0] == acervo[0]
    assert len(ids) == espacada.POR_ASSUNTO
    assert rodada.filtros["revisao"][0]["etapa"] == 1


# --- o fator de tempo -------------------------------------------------------

def test_fator_de_tempo():
    assert onde_estudar.fator_de_tempo(None, DIA) == 1.0          # sem treino
    assert onde_estudar.fator_de_tempo(DIA, DIA) == 1.0
    assert onde_estudar.fator_de_tempo(DIA - timedelta(days=15), DIA) == 1.5
    assert onde_estudar.fator_de_tempo(DIA - timedelta(days=90), DIA) == 2.0


def test_sem_treino_o_fator_e_neutro_e_o_cartao_diz(banco_temporario,
                                                    com_quadro_do_edital):
    with sessao() as s:
        s.add(_concurso())
    for p in inicio.prioridades(foco.montar()):
        assert p.fator == 1.0
        assert "ainda não treinada" in p.porque


def test_com_treino_o_tempo_sem_revisar_entra_na_conta(banco_temporario,
                                                       com_quadro_do_edital):
    with sessao() as s:
        s.add(_concurso())
    ids = [_questao(n, materia="Língua Portuguesa") for n in range(1, 6)]
    quinze_dias = date.today() - timedelta(days=15)
    for i in ids:
        _respondi(i, False, quinze_dias)

    lp = next(p for p in inicio.prioridades(foco.montar())
              if p.materia == "Língua Portuguesa")

    assert lp.fator == 1.5 and lp.dias_sem_revisar == 15
    assert "×1,5" in lp.porque
    assert lp.valor == pytest.approx(15.0 * 1.0 * 1.5)   # peso x erro x fator


def test_resposta_de_gerada_nao_conta_no_acerto_do_assunto(banco_temporario,
                                                           com_quadro_do_edital):
    """As duas tabelas numeram do 1: sem o filtro, errar a gerada 1 contava
    como erro na questao real 1."""
    with sessao() as s:
        s.add(_concurso())
    real = _questao(1, materia="Língua Portuguesa")
    with sessao() as s:
        s.add(QuestaoGerada(modo="variacao", enunciado="gerada?", resposta="a",
                            impressao="g1", modelo="teste"))
    _respondi(real, False, DIA, gerada=True)

    with sessao() as s:
        acertos, ultimas = foco._acerto_por_assunto(
            s, {"Língua Portuguesa": "Língua Portuguesa"}
        )
    assert acertos == {} and ultimas == {}


def test_a_home_mostra_a_revisao_vencida_com_o_botao(acervo, com_quadro_do_edital):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    _respondi(acervo[0], False, date.today() - timedelta(days=1))
    cliente = TestClient(app)
    texto = cliente.get("/").text

    assert "revisão(ões) para hoje" in texto
    assert "Direito Penal (sem assunto)" in texto
    resposta = cliente.post("/revisao/hoje", follow_redirects=False)
    assert resposta.headers["location"].startswith("/simulado/")
