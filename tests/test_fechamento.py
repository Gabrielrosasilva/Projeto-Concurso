"""O fechamento do dia da tela Hoje (decisao 189): onde mais errei e amanha.

O que estes testes seguram:

  * o "onde mais errei" agrupa o erro do radar pelo no da questao e o anotado
    pela faixa, em linhas proprias, e deixa o treino de IA de fora;
  * os motivos saem do `metricas.motivos_dos_erros`, por origem;
  * o "Refazer os erros" traz so o que eu errei NAQUELE dia e continua errado;
  * o amanha e o proximo dia do plano, com o aviso quando o tema volta.

As datas sao fixas: nada depende do dia em que o teste roda.
"""
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import cronograma
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado
from radar.servico import conteudos as servico_conteudos
from radar.servico import cronograma as diario
from radar.servico import fechamento, simulado
from radar.util import fuso_local
from radar.web.app import app

from tests.test_desempenho import (  # noqa: F401 - fixtures e ajudantes
    APLICACAO, HOJE, MINI, NO_TEMPO, PENAL, SEG, TER, _anotar, _responder, arvore, plano,
)
from tests.test_estudo import _responder_de_novo


def _id(numero: int) -> int:
    with sessao() as s:
        return s.scalars(select(QuestaoDeProva.id).where(QuestaoDeProva.numero == numero)).one()


# --- onde mais errei ------------------------------------------------------------

def test_o_radar_conta_pelo_no_e_o_anotado_pela_faixa(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, SEG, classificar_em=NO_TEMPO)
    _responder(3, True, SEG, classificar_em=NO_TEMPO)
    _responder(4, False, SEG, gerada=True)                  # treino de IA: fora
    _anotar(plano, "noite", 0, 10, 7)                       # 3 erros anotados

    errei = fechamento.onde_mais_errei(SEG, plano)

    assert [(e.nome, e.erros, e.origem) for e in errei] == [
        ("Aplicação da lei penal", 3, fechamento.ANOTADO),
        ("Lei penal no tempo", 2, fechamento.RADAR),
    ]
    assert errei[1].caminho == NO_TEMPO


def test_o_mesmo_tema_no_radar_e_no_anotado_fica_em_duas_linhas(plano):
    """Os dois recortes nunca sao somados no mesmo numero."""
    _responder(1, False, SEG, classificar_em=APLICACAO)
    _anotar(plano, "noite", 0, 10, 9)

    errei = fechamento.onde_mais_errei(SEG, plano)

    assert sorted((e.nome, e.erros, e.origem) for e in errei) == [
        ("Aplicação da lei penal", 1, fechamento.ANOTADO),
        ("Aplicação da lei penal", 1, fechamento.RADAR),
    ]


def test_mostra_so_os_tres_com_mais_erros(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, SEG, classificar_em=APLICACAO)
    _responder(3, False, SEG, classificar_em=PENAL)
    _responder(4, False, SEG, classificar_em=PENAL)
    _responder(5, False, SEG)                               # sem classificacao

    errei = fechamento.onde_mais_errei(SEG, plano)

    assert len(errei) == 3 and errei[0].nome == PENAL and errei[0].erros == 2


def test_os_motivos_vem_por_origem(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, SEG, classificar_em=NO_TEMPO)
    with sessao() as s:
        resposta = s.scalars(select(RespostaDeSimulado)
                             .where(RespostaDeSimulado.questao_id == _id(1))).one()
        resposta.motivo = "nao_sabia"

    (fepese,) = fechamento.motivos_do_dia(SEG)

    assert (fepese.origem, fepese.motivos, fepese.sem_motivo) == (
        "FEPESE no radar", [("Não sabia", 1)], 1)


# --- refazer os erros do dia ------------------------------------------------------

def test_refazer_traz_so_os_erros_do_dia_que_continuam_errados(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, SEG, classificar_em=NO_TEMPO)
    _responder(3, False, TER, classificar_em=NO_TEMPO)      # outro dia
    _responder_de_novo(2, True, TER, filtros={})            # ja acertei depois

    assert simulado.questoes_erradas(do_dia=SEG) == [_id(1)]
    rodada = simulado.criar_simulado_de_erros(quantidade=None, do_dia=SEG)
    assert rodada.filtros["erros"] is True and rodada.filtros["do_dia"] == "2026-09-28"


@pytest.mark.parametrize("rodada, destino", [
    (SimpleNamespace(id=5), "/simulado/5"),
    (None, "/hoje?data=2026-09-28#como-foi"),
])
def test_o_botao_refazer_abre_a_rodada_do_dia(banco_temporario, monkeypatch, rodada, destino):
    from radar import servico

    pedido = {}

    def criar(**kw):
        pedido.update(kw)
        return rodada

    monkeypatch.setattr(servico, "criar_simulado_de_erros", criar)
    resposta = TestClient(app).post("/hoje/refazer-erros", data={"data": "2026-09-28"},
                                    follow_redirects=False)
    assert resposta.headers["location"] == destino
    assert pedido == {"quantidade": None, "do_dia": SEG}


# --- amanha -----------------------------------------------------------------------

@pytest.fixture
def plano_com_amanha(arvore, tmp_path):
    """O mini, com a lei seca de 29/09 de Direito Penal no no do tempo."""
    servico_conteudos.exportar()
    dados = yaml.safe_load(MINI.read_text(encoding="utf-8"))
    dados["dias"][1]["manha"][0].update(materia=PENAL, nos=[NO_TEMPO])
    arquivo = tmp_path / "cronograma_com_amanha.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return cronograma.carregar(arquivo)


def test_amanha_e_o_proximo_dia_do_plano(plano_com_amanha):
    amanha = fechamento.amanha(SEG, plano_com_amanha)

    assert amanha.data == TER and amanha.titulo == "Amanhã · terça, 29/09"
    assert amanha.novos == ["Lei seca"] and amanha.revisoes == ["R+7: revisão"]
    assert amanha.questoes == 10
    # Depois de 29/09 o mini so tem 03/10: e o "proximo dia", e nao amanha.
    assert fechamento.amanha(TER, plano_com_amanha).titulo == "Próximo dia · sábado, 03/10"


def test_amanha_avisa_quando_o_assunto_do_erro_volta(plano_com_amanha):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)

    errei = fechamento.onde_mais_errei(SEG, plano_com_amanha)
    amanha = fechamento.amanha(SEG, plano_com_amanha, errei)

    assert amanha.continua == ("Lei penal no tempo", "Lei seca")


def test_o_fim_do_plano_nao_tem_amanha(plano):
    assert fechamento.amanha(date(2026, 10, 3), plano) is None


# --- a tela ---------------------------------------------------------------------

def test_a_tela_mostra_o_fechamento(banco_temporario, monkeypatch):
    agora = datetime(2026, 10, 20, 22, 0, tzinfo=fuso_local())
    monkeypatch.setattr(diario, "agora_local", lambda: agora)
    monkeypatch.setattr(fechamento, "do_dia", lambda data, plano: fechamento.Fechamento(
        errei=[fechamento.OndeErrei("Emprego dos pronomes", 5, fechamento.RADAR)],
        motivos=[fechamento.MotivosDaOrigem("FEPESE no radar", [("Não sabia", 4)], 1)],
        para_refazer=5,
        amanha=fechamento.Amanha(data=date(2026, 10, 21), titulo="Amanhã · quarta, 21/10",
                                 novos=["Pronomes 2"], questoes=40,
                                 continua=("Emprego dos pronomes", "Pronomes 2"))))

    texto = TestClient(app).get("/hoje?data=2026-10-20").text

    como_foi = texto.split('id="como-foi"')[1]
    assert "Onde mais errei" in como_foi and "5 erros" in como_foi
    assert "Não sabia 4" in como_foi and "sem motivo 1" in como_foi
    assert "Refazer os 5 erros de hoje no radar" in como_foi
    assert "Amanhã · quarta, 21/10" in como_foi and "do mesmo assunto" in como_foi
    # Antes da meta: o fechamento e o que se le antes de marcar o dia.
    assert como_foi.index("Onde mais errei") < como_foi.index("Qual meta eu cumpri?")
