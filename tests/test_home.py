"""A home: tres blocos cheios, duas faixas, e bloco sem dado que convida.

Os testes olham os dois estados que importam: eu nunca treinei (tudo convida)
e eu ja errei alguma coisa (o Revisar aparece cheio, com o botao).
"""
import pytest
from fastapi.testclient import TestClient

from radar import foco, servico
from radar.db import sessao
from radar.models import QuestaoDeProva
from radar.servico import inicio
from radar.web.app import app

from tests.test_foco import _concurso, com_quadro_do_edital  # noqa: F401

CADERNO = "https://fepese.test/ap2019.pdf"


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def _acervo(n: int = 6, materia: str = "Direito Penal"):
    with sessao() as s:
        s.add(_concurso())
        for i in range(n):
            s.add(QuestaoDeProva(
                prova_url=CADERNO, banca="FEPESE",
                concurso_url=_concurso().url, ano=2019,
                cargo="Agente Penitenciário", numero=i + 1, materia=materia,
                enunciado=f"questao {i}?", alternativas={"a": "x", "b": "y"},
                resposta="a", impressao=f"q{i}",
            ))


def _responder(certas: int, erradas: int, materia="Direito Penal"):
    simulado = servico.criar_simulado(quantidade=certas + erradas, materia=materia)
    for n in range(certas + erradas):
        _r, questao = servico.questao_atual(simulado.id)
        servico.responder(simulado.id, questao.id, "a" if n < certas else "b")


# --- os blocos --------------------------------------------------------------

def test_tres_blocos_e_duas_faixas(cliente, com_quadro_do_edital):
    _acervo()
    texto = cliente.get("/").text

    for bloco in ("Policia Penal SC", "O que estudar agora", "Revisar"):
        assert bloco in texto, bloco
    for faixa in ("Sua evolução", "Concurso"):
        assert faixa in texto, faixa
    assert "Começar treino" in texto


def test_sem_treino_nada_nasce_vazio_tudo_convida(cliente, com_quadro_do_edital):
    """Nunca respondi: a evolucao pede 20 respostas, e o Revisar explica o que
    vai aparecer ali - nenhum zero, nenhum bloco em branco."""
    _acervo()
    texto = cliente.get("/").text

    assert "Responda mais <b>20</b> para eu medir sua evolução" in texto
    assert "ainda não respondi nenhuma questão" in texto
    assert "Revisar agora" not in texto
    assert "ainda não treinada" in texto


def test_com_erro_o_revisar_enche_e_o_botao_aparece(cliente, com_quadro_do_edital):
    _acervo()
    _responder(certas=2, erradas=3)

    texto = cliente.get("/").text

    assert "Revisar agora" in texto
    assert "Direito Penal · 40% em 5" in texto          # materia fraca
    assert "Responda mais <b>15</b>" in texto


def test_revisar_agora_monta_a_rodada_so_com_os_erros(cliente, com_quadro_do_edital):
    _acervo()
    _responder(certas=2, erradas=3)

    resposta = cliente.post("/revisar", follow_redirects=False)

    assert resposta.status_code == 303
    simulado_id = int(resposta.headers["location"].rsplit("/", 1)[1])
    assert servico.resumo_do_simulado(simulado_id)["total"] == 3


def test_errou_e_depois_acertou_sai_da_revisao(banco_temporario, com_quadro_do_edital):
    _acervo(n=1)
    _responder(certas=0, erradas=1)
    assert len(servico.questoes_erradas()) == 1
    _responder(certas=1, erradas=0)
    assert servico.questoes_erradas() == []


# --- a prioridade -----------------------------------------------------------

def test_prioridade_segue_o_peso_quando_nada_foi_treinado(banco_temporario,
                                                        com_quadro_do_edital):
    """As duas de 15 questoes do edital vem primeiro."""
    _acervo()
    nomes = [p.materia for p in inicio.prioridades(foco.montar())]
    assert set(nomes[:2]) == {"Língua Portuguesa", "Direitos Humanos"}


def test_com_5_respostas_o_acerto_entra_na_conta(banco_temporario,
                                                com_quadro_do_edital):
    """Direito Penal vale 5 questoes; com 0% de acerto em 5 ela vale 5, e
    continua abaixo das de 15 nao treinadas - a formula e peso x erro."""
    _acervo()
    _responder(certas=0, erradas=5)

    nomes = [p.materia for p in inicio.prioridades(foco.montar())]

    assert "Direito Penal" not in nomes           # 5 x 100% = 5, menos que 15 e 10


def test_o_porque_diz_os_numeros(banco_temporario, com_quadro_do_edital):
    p = inicio.Prioridade("Direito Penal", 5, 5.0, respondidas=25, acerto=32.0)
    assert p.porque == "5 questões no edital · 32% de acerto em 25 questões"
