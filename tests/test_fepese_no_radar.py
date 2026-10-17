"""O "Gerar questao real" da faixa e a reserva do fechamento (decisao 167).

O que estes testes seguram:
  - o estoque do tema e so questao real da FEPESE (alvo e complementar
    aceito), sem anulada e sem prova recusada; outra banca nunca;
  - a rodada que mede ainda por criar (o fechamento de 07/11 do plano real)
    reserva as questoes que escolheria, e a rodada que mede criada reserva as
    nao respondidas; depois do fim do ciclo, nada fica reservado;
  - o treino nunca usa questao reservada, e a tela diz para quando ela esta
    guardada;
  - o botao abre a rodada, que corrige na hora.

Os dias sao fixos (05/10 e 06/10 do plano real); nada depende de hoje.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import classificacoes, composicao, fepese_no_radar
from radar.servico import cronograma as diario
from radar.servico import simulado as servico_simulado
from radar.web.app import app
from tests.test_composicao import (CRASE, INTERPRETACAO, ORTOGRAFIA,  # noqa: F401
                                   PORTUGUES, _questao, acervo)

ANTES = date(2026, 10, 6)
DEPOIS_DO_CICLO = date(2026, 11, 8)
TABELAS = "Raciocínio Lógico > Tabelas-verdade"


def _sem_reserva(monkeypatch):
    monkeypatch.setattr(composicao, "reserva_das_que_medem",
                        lambda data, plano=None: composicao.Reserva())


def _numeros(candidatas):
    with sessao() as s:
        return sorted(s.get(QuestaoDeProva, c.id).numero for c in candidatas)


def test_o_tema_tem_so_a_fepese_aceita_sem_anulada(acervo):
    # Uma de outra banca no mesmo no nunca entra.
    with sessao() as s:
        q = QuestaoDeProva(prova_url="https://ieses.test/x.pdf", banca="IESES", ano=2024,
                           numero=99, materia=PORTUGUES, enunciado="De outra banca?",
                           alternativas={"a": "1", "b": "2", "c": "3", "d": "4"},
                           resposta="a", impressao="ieses-99", evidencia="fora")
        s.add(q)
        s.flush()
        chave = classificacoes.chave_de(q)
    classificacoes.classificar(chave, INTERPRETACAO, "manual")

    # Interpretacao: 1, 2 e 3 do alvo e 8 do complementar aceito; a 4 e anulada.
    assert _numeros(fepese_no_radar.do_tema([INTERPRETACAO])) == [1, 2, 3, 8]
    # Ortografia: a 5 do alvo; as 9 e 10 sao de prova recusada.
    assert _numeros(fepese_no_radar.do_tema([ORTOGRAFIA])) == [5]
    assert fepese_no_radar.do_tema([]) == []


def test_a_rodada_que_mede_por_criar_reserva_o_que_escolheria(acervo):
    """De 06/10, os diagnosticos de 10/10 do plano real ainda nao tem rodada
    neste banco: eles reservam o que escolheriam, com o dia de cada uma. (O
    fechamento de 07/11 divide as 50 pelo quadro do edital, que o banco de
    teste nao tem.)"""
    reserva = composicao.reserva_das_que_medem(ANTES)
    assert date(2026, 10, 10) in reserva.dias
    tema = {c.chave for c in fepese_no_radar.do_tema([PORTUGUES])}
    guardadas = reserva.chaves & tema
    assert guardadas
    assert reserva.dias_das(guardadas) == [date(2026, 10, 10)]


def test_depois_do_ciclo_nada_fica_reservado(acervo):
    assert composicao.reserva_das_que_medem(DEPOIS_DO_CICLO).chaves == set()


def test_a_rodada_que_mede_criada_reserva_as_nao_respondidas(acervo):
    (uma, outra) = fepese_no_radar.do_tema([INTERPRETACAO])[:2]
    with sessao() as s:
        rodada = Simulado(filtros={"rodada": "composta",
                                   "faixa": {"data": "2026-10-10", "bloco": "noite",
                                             "indice": 0, "titulo": "Diagnóstico"}})
        s.add(rodada)
        s.flush()
        s.add(RespostaDeSimulado(simulado_id=rodada.id, questao_id=uma.id, ordem=1))
        s.add(RespostaDeSimulado(simulado_id=rodada.id, questao_id=outra.id, ordem=2))
        ident = rodada.id
    servico_simulado.responder(ident, outra.id, "a")

    reserva = composicao.reserva_das_que_medem(DEPOIS_DO_CICLO)
    assert reserva.chaves == {uma.chave}


def test_o_treino_nunca_usa_a_reservada(acervo, monkeypatch):
    tema = fepese_no_radar.do_tema([INTERPRETACAO])
    guardada = tema[0]
    monkeypatch.setattr(composicao, "reserva_das_que_medem",
                        lambda data, plano=None: composicao.Reserva({guardada.chave},
                                                                    [date(2026, 11, 7)]))
    rodada = fepese_no_radar.criar_rodada([INTERPRETACAO], 30, ANTES)
    with sessao() as s:
        ids = set(s.scalars(select(RespostaDeSimulado.questao_id)
                            .where(RespostaDeSimulado.simulado_id == rodada.id)))
    assert guardada.id not in ids and len(ids) == len(tema) - 1
    assert rodada.filtros["rodada"] == fepese_no_radar.RODADA
    assert servico_simulado.corrige_na_hora(rodada)


def test_tudo_reservado_nao_cria_rodada(acervo):
    assert fepese_no_radar.criar_rodada([PORTUGUES], 10, ANTES) is None


def test_o_resumo_conta_as_livres_as_reservadas_e_as_feitas(acervo):
    tema = fepese_no_radar.do_tema([INTERPRETACAO])
    reserva = composicao.Reserva({tema[0].chave}, [date(2026, 11, 7)])
    resumo = fepese_no_radar.da_faixa([INTERPRETACAO], reserva, questoes_da_faixa=10,
                                      respondidas={tema[1].impressao})
    assert resumo.no_acervo == 4 and resumo.reservadas == 1
    assert resumo.disponiveis == 3 and resumo.feitas == 1 and resumo.novas == 2
    assert resumo.sugeridas == 3


# --- a tela --------------------------------------------------------------------

@pytest.fixture
def em_05_10(acervo, monkeypatch):
    """O bonus de 05/10 do plano real tem os nos de Raciocinio Logico; uma
    questao real do alvo em Tabelas-verdade."""
    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 5))
    _questao(30, "Raciocínio Lógico", TABELAS, "https://fepese.test/ap2019.pdf")


def test_a_tela_mostra_os_tres_botoes_e_o_gerar_questao_real_abre(em_05_10, monkeypatch):
    _sem_reserva(monkeypatch)
    cliente = TestClient(app)
    html = cliente.get("/hoje?data=2026-10-05").text
    assert "Gerar questão real" in html
    assert "questão real da FEPESE</b>" in html
    assert "Ainda não há questão de outra banca deste tema no radar." in html

    resposta = cliente.post("/fepese/treinar", data={
        "conteudos": [TABELAS], "quantidade": "5", "data": "2026-10-05",
        "bloco": "manha", "indice": "0", "titulo": "Bônus"}, follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/simulado/")


def test_a_tela_diz_quando_a_questao_esta_guardada(em_05_10, monkeypatch):
    """A unica de Tabelas-verdade guardada para 07/11: a faixa nao tem o
    botao e diz para quando ela esta guardada."""
    (unica,) = fepese_no_radar.do_tema([TABELAS])
    monkeypatch.setattr(composicao, "reserva_das_que_medem",
                        lambda data, plano=None: composicao.Reserva(
                            {unica.chave}, [date(2026, 11, 7)],
                            {unica.chave: date(2026, 11, 7)}))
    html = TestClient(app).get("/hoje?data=2026-10-05").text
    assert "ficam guardadas para a rodada que mede de 07/11: o treino não as usa" in html
    assert "Gerar questão real" not in html
