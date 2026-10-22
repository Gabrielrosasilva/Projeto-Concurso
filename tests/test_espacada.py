"""A rodada da revisao espacada, a fila na home e o fator de tempo.

A fila de revisao e uma so, a do `servico/estudo.py` (decisao 128), e a regra
dela - os gatilhos, o 1-7-30, as pontas - e testada no test_estudo.py. As
datas sao fixas: nada aqui depende do dia em que o teste roda.
"""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from radar import amostra, foco, onde_estudar, servico
from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import classificacoes, espacada, estudo, inicio, metricas
from radar.servico import cronograma as diario

from tests.test_desempenho import (  # noqa: F401 - fixtures e ajudantes
    APLICACAO, HOJE, NO_TEMPO, PENAL, SEG, _responder, arvore, plano,
)
from tests.test_desempenho import _questao as _questao_real
from tests.test_foco import _classificar, _concurso, com_quadro_do_edital  # noqa: F401

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


# --- a rodada das revisoes de hoje ------------------------------------------
# A fila e a do `estudo` (decisao 128); a regra dela esta no test_estudo.py.
# Aqui, so a rodada que o botao da home monta com as pontas dessa fila.

def _no_acervo(numero: int, caminho: str, materia: str = PENAL) -> int:
    """Uma questao real classificada em `caminho`, que eu nunca respondi."""
    with sessao() as s:
        questao = _questao_real(numero, materia)
        s.add(questao)
        s.flush()
        questao_id, chave = questao.id, classificacoes.chave_de(questao)
    classificacoes.classificar(chave, caminho, "teste")
    return questao_id


def _questoes_da_rodada(rodada) -> list[int]:
    with sessao() as s:
        return [r.questao_id for r in s.scalars(
            select(RespostaDeSimulado).where(RespostaDeSimulado.simulado_id == rodada.id)
            .order_by(RespostaDeSimulado.ordem))]


def test_a_rodada_vai_pela_ponta_da_fila_e_comeca_pelo_erro(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    do_no = {_no_acervo(2, NO_TEMPO), _no_acervo(3, NO_TEMPO)}
    do_pai = _no_acervo(4, APLICACAO)

    rodada = espacada.criar_simulado_de_revisao(HOJE, plano=plano)

    ids = _questoes_da_rodada(rodada)
    with sessao() as s:
        errada = s.scalars(select(QuestaoDeProva.id).where(QuestaoDeProva.numero == 1)).one()
    assert ids[0] == errada
    assert set(ids[1:]) == do_no and do_pai not in ids
    # A ponta, e nao o assunto e a materia acima dela: e a mesma revisao.
    (revisao,) = rodada.filtros["revisao"]
    assert (revisao["no"], revisao["etapa"]) == (NO_TEMPO, 1)
    # E o `metricas` a conta como revisao (decisao 79).
    assert metricas.rodada_que_revisa(rodada.filtros)


def test_sem_nada_vencido_nao_ha_rodada(plano):
    assert espacada.criar_simulado_de_revisao(HOJE, plano=plano) is None


def test_no_vencido_sem_questao_no_acervo_nao_vira_rodada_vazia(plano):
    """Estudei a teoria e o prazo venceu, mas o acervo nao tem questao do no."""
    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano, hoje=HOJE)

    assert estudo.pontas(estudo.para_revisar(plano=plano, hoje=HOJE))
    assert espacada.criar_simulado_de_revisao(HOJE, plano=plano) is None


# --- o cartao "Revisar hoje" da tela Hoje (decisao 187) ----------------------

def test_o_cartao_conta_as_pontas_e_mostra_os_mais_atrasados(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, HOJE - timedelta(days=1), materia="Língua Portuguesa",
               classificar_em="Língua Portuguesa")

    cartao = estudo.revisar_hoje(plano=plano, hoje=HOJE, mostrar=1)

    assert cartao.vencidos == 2 and cartao.na_rodada == 2
    (primeiro,) = cartao.primeiros
    # O atraso conta do dia da tela, nao do relogio: 1a pratica na segunda,
    # o R+1 venceu na terca, e a tela e de sabado.
    assert (primeiro.caminho, primeiro.desde, primeiro.atraso) == (
        NO_TEMPO, SEG + timedelta(days=1), 4)


def test_a_rodada_do_cartao_traz_uma_por_tema_ate_o_limite(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _no_acervo(2, NO_TEMPO)
    _responder(3, False, HOJE - timedelta(days=1), materia="Língua Portuguesa",
               classificar_em="Língua Portuguesa")

    rodada = espacada.criar_simulado_de_revisao(HOJE, plano=plano, limite=1, por_tema=1)

    with sessao() as s:
        errada = s.scalars(select(QuestaoDeProva.id).where(QuestaoDeProva.numero == 1)).one()
    assert _questoes_da_rodada(rodada) == [errada]
    assert [r["no"] for r in rodada.filtros["revisao"]] == [NO_TEMPO]


def test_o_tema_sem_questao_cede_o_lugar_ao_seguinte(plano):
    """O mais atrasado venceu so pelo prazo e o acervo nao tem questao dele."""
    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano, hoje=HOJE)
    _responder(1, False, HOJE - timedelta(days=1), materia="Língua Portuguesa",
               classificar_em="Língua Portuguesa")

    rodada = espacada.criar_simulado_de_revisao(HOJE, plano=plano, limite=1, por_tema=1)

    assert [r["no"] for r in rodada.filtros["revisao"]] == ["Língua Portuguesa"]
    assert len(_questoes_da_rodada(rodada)) == 1


def _cartao(vencidos=2):
    return estudo.RevisarHoje(
        vencidos=vencidos, na_rodada=min(vencidos, espacada.TEMAS_DO_CARTAO),
        primeiros=[estudo.TemaParaRevisar(
            nome="Abolitio criminis", caminho="Direito Penal > Abolitio criminis",
            desde=date(2026, 9, 29), atraso=23, porque="prazo vencido")])


def _relogio(monkeypatch):
    """A tela Hoje acha que hoje e 20/10, meio-dia: nada depende do dia real."""
    from radar.util import fuso_local

    agora = datetime(2026, 10, 20, 12, 0, tzinfo=fuso_local())
    monkeypatch.setattr(diario, "agora_local", lambda: agora)
    monkeypatch.setattr(diario, "hoje_local", lambda: agora.date())


def test_a_tela_hoje_mostra_o_cartao_so_no_dia_de_hoje(banco_temporario, monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    _relogio(monkeypatch)
    monkeypatch.setattr(estudo, "revisar_hoje", lambda plano=None, hoje=None: _cartao())
    cliente = TestClient(app)

    texto = cliente.get("/hoje?data=2026-10-20").text
    assert "🔁 Revisar hoje" in texto
    assert "Abolitio criminis" in texto and "vencido desde 29/09 (23 dias)" in texto
    assert 'action="/hoje/revisar"' in texto and "(2 questões)" in texto
    # O cartao vem logo abaixo da barra do dia, antes das faixas.
    assert texto.index("🔁 Revisar hoje") < texto.index('id="faixa-manha-0"')

    assert "🔁 Revisar hoje" not in cliente.get("/hoje?data=2026-10-19").text


def test_o_cartao_some_com_a_fila_vazia_e_o_caderno_em_dia(banco_temporario, monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    _relogio(monkeypatch)
    monkeypatch.setattr(estudo, "revisar_hoje", lambda plano=None, hoje=None: _cartao(0))

    assert "🔁 Revisar hoje" not in TestClient(app).get("/hoje?data=2026-10-20").text


@pytest.mark.parametrize("rodada, destino", [
    (SimpleNamespace(id=9), "/simulado/9"),
    (None, "/hoje"),
])
def test_o_botao_do_cartao_abre_dez_temas_uma_de_cada(banco_temporario, monkeypatch,
                                                     rodada, destino):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    pedido = {}

    def criar(**kw):
        pedido.update(kw)
        return rodada

    monkeypatch.setattr(espacada, "criar_simulado_de_revisao", criar)
    resposta = TestClient(app).post("/hoje/revisar", follow_redirects=False)
    assert resposta.headers["location"] == destino
    assert pedido == {"limite": 10, "por_tema": 1}


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
    # 20 questoes: o minimo do nivel "materia" no config/amostra.yml (Etapa 4).
    # Com menos que isso a materia conta como nao treinada, e o fator de tempo
    # fica neutro - e e justamente o que o minimo existe para fazer.
    quantas = amostra.carregar().do_nivel("materia")
    ids = [_questao(n, materia="Língua Portuguesa")
           for n in range(1, quantas + 1)]
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
    como erro na questao real 1. O acerto por assunto do Onde estudar e o do
    desempenho por conteudo (decisao 74)."""
    from radar.servico import desempenho_por_conteudo as por_conteudo

    with sessao() as s:
        s.add(_concurso())
    real = _questao(1, materia="Língua Portuguesa")
    _classificar(real, "Língua Portuguesa > Emprego da crase")
    with sessao() as s:
        s.add(QuestaoGerada(modo="variacao", enunciado="gerada?", resposta="a",
                            impressao="g1", modelo="teste"))
    _respondi(real, False, DIA, gerada=True)

    assert por_conteudo.por_no(por_conteudo.SEMPRE, hoje=DIA) == {}


def test_a_home_mostra_as_pontas_da_fila_do_meu_desempenho(banco_temporario,
                                                         com_quadro_do_edital,
                                                         monkeypatch):
    """A home e o Meu desempenho mostram a mesma fila (decisao 128); a home,
    so as pontas. A fila e fixa aqui: a regra dela esta no test_estudo.py."""
    from fastapi.testclient import TestClient

    from radar.web.app import app

    with sessao() as s:
        s.add(_concurso())
    fila = [
        estudo.ParaRevisar(NO_TEMPO, "Lei penal no tempo", "subassunto",
                           motivos=[estudo.POR_ERRO]),
        estudo.ParaRevisar(APLICACAO, "Aplicação da lei penal", "assunto",
                           motivos=[estudo.POR_ERRO]),
    ]
    monkeypatch.setattr(inicio.estudo, "situacoes", lambda **_: {})
    monkeypatch.setattr(inicio.estudo, "para_revisar", lambda **_: fila)
    monkeypatch.setattr(inicio.estudo, "proxima_revisao", lambda **_: None)

    texto = TestClient(app).get("/").text

    assert "conteúdo(s) para revisar hoje" in texto
    assert "Lei penal no tempo · erro recente" in texto
    assert "Aplicação da lei penal ·" not in texto        # o assunto acima dela


def test_a_home_diz_a_proxima_revisao_com_a_fila_vazia(banco_temporario,
                                                       com_quadro_do_edital,
                                                       monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    with sessao() as s:
        s.add(_concurso())
    proxima = estudo.ParaRevisar(NO_TEMPO, "Lei penal no tempo", "subassunto",
                                 vence_em=date(2026, 10, 6), etapa=2)
    monkeypatch.setattr(inicio.estudo, "situacoes", lambda **_: {})
    monkeypatch.setattr(inicio.estudo, "para_revisar", lambda **_: [])
    monkeypatch.setattr(inicio.estudo, "proxima_revisao", lambda **_: proxima)

    texto = TestClient(app).get("/").text

    assert "Próxima revisão: <b>Lei penal no tempo</b> em 06/10." in texto


@pytest.mark.parametrize("rodada, destino", [
    (SimpleNamespace(id=7), "/simulado/7"),
    (None, "/"),
])
def test_o_botao_da_home_abre_a_rodada(banco_temporario, monkeypatch, rodada, destino):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    monkeypatch.setattr(espacada, "criar_simulado_de_revisao", lambda: rodada)
    resposta = TestClient(app).post("/revisao/hoje", follow_redirects=False)
    assert resposta.headers["location"] == destino
