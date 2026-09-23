"""Modo simulado: responder questoes reais e ver o acerto por materia.

O objetivo que fecha o projeto: o radar acha o concurso, o acervo traz as
provas, e aqui eu treino com elas.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import servico
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado
from radar.web.app import app


def _questao(numero: int, **mudancas) -> QuestaoDeProva:
    base = dict(
        prova_url=f"https://x.test/prova{numero}.pdf",
        banca="FEPESE",
        ano=2024,
        municipio="Palhoca",
        cargo="Guarda Patrimonial",
        numero=numero,
        materia="Língua Portuguesa",
        enunciado=f"Enunciado da questao {numero}?",
        alternativas={"a": "um", "b": "dois", "c": "tres", "d": "quatro", "e": "cinco"},
        resposta="c",
        impressao=f"impressao{numero}",
    )
    base.update(mudancas)
    return QuestaoDeProva(**base)


def _semear(*questoes):
    with sessao() as s:
        for q in questoes:
            s.add(q)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- montar a rodada --------------------------------------------------------

def test_monta_uma_rodada(banco_temporario):
    _semear(*[_questao(n) for n in range(1, 11)])

    simulado = servico.criar_simulado(quantidade=5)

    assert simulado is not None
    assert servico.resumo_do_simulado(simulado.id)["total"] == 5


def test_nao_repete_a_mesma_questao_na_rodada(banco_temporario):
    """A banca reaproveita muito: das 5.021 questoes so 1.815 tem enunciado
    diferente, e uma aparece em 44 cadernos. Sortear sem cuidado daria a mesma
    pergunta varias vezes na mesma rodada."""
    _semear(*[
        _questao(n, impressao="sempre-a-mesma", prova_url=f"https://x.test/{n}.pdf")
        for n in range(1, 21)
    ])

    simulado = servico.criar_simulado(quantidade=10)
    assert servico.resumo_do_simulado(simulado.id)["total"] == 1


def test_pede_mais_do_que_existe_e_traz_o_que_tem(banco_temporario):
    _semear(_questao(1), _questao(2))
    simulado = servico.criar_simulado(quantidade=20)

    assert servico.resumo_do_simulado(simulado.id)["total"] == 2


def test_sem_questao_nenhuma_nao_cria_rodada(banco_temporario):
    assert servico.criar_simulado(quantidade=5) is None


def test_filtra_por_materia(banco_temporario):
    _semear(
        _questao(1, materia="Língua Portuguesa"),
        _questao(2, materia="Raciocínio Lógico", impressao="outra"),
    )

    simulado = servico.criar_simulado(quantidade=10, materia="Raciocínio Lógico")
    _, questao = servico.questao_atual(simulado.id)
    assert questao.materia == "Raciocínio Lógico"


def test_sem_materia_escolhida_usa_as_universais(banco_temporario):
    """Portugues, raciocinio, informatica e conhecimentos gerais caem em
    qualquer concurso - servem mesmo sem haver prova do meu cargo no acervo."""
    _semear(
        _questao(1, materia="Língua Portuguesa"),
        _questao(2, materia="Conhecimentos Específicos", impressao="especifica"),
    )

    simulado = servico.criar_simulado(quantidade=10, universais=True)
    assert servico.resumo_do_simulado(simulado.id)["total"] == 1


def test_questao_sem_gabarito_fica_de_fora(banco_temporario):
    """Sem saber a correta nao da para corrigir."""
    _semear(_questao(1, resposta=None))
    assert servico.criar_simulado(quantidade=5) is None


# --- responder --------------------------------------------------------------

def test_acertar_e_errar(banco_temporario):
    _semear(_questao(1))
    simulado = servico.criar_simulado(quantidade=1)
    _, questao = servico.questao_atual(simulado.id)

    assert servico.responder(simulado.id, questao.id, "c") is True

    _semear(_questao(2, impressao="segunda"))
    outro = servico.criar_simulado(quantidade=10)
    _, segunda = servico.questao_atual(outro.id)
    assert servico.responder(outro.id, segunda.id, "a") is False


def test_a_rodada_avanca_para_a_proxima(banco_temporario):
    _semear(_questao(1), _questao(2, impressao="b"))
    simulado = servico.criar_simulado(quantidade=2)

    _, primeira = servico.questao_atual(simulado.id)
    servico.responder(simulado.id, primeira.id, "a")

    _, segunda = servico.questao_atual(simulado.id)
    assert segunda.id != primeira.id


def test_responder_duas_vezes_nao_conta_de_novo(banco_temporario):
    """Recarregar a pagina nao pode mudar o resultado."""
    _semear(_questao(1))
    simulado = servico.criar_simulado(quantidade=1)
    _, questao = servico.questao_atual(simulado.id)

    assert servico.responder(simulado.id, questao.id, "c") is True
    assert servico.responder(simulado.id, questao.id, "a") is None
    assert servico.resumo_do_simulado(simulado.id)["acertos"] == 1


def test_letra_invalida_e_recusada(banco_temporario):
    _semear(_questao(1))
    simulado = servico.criar_simulado(quantidade=1)
    _, questao = servico.questao_atual(simulado.id)

    assert servico.responder(simulado.id, questao.id, "z") is None
    assert servico.resumo_do_simulado(simulado.id)["respondidas"] == 0


def test_questao_de_outra_rodada_e_recusada(banco_temporario):
    _semear(_questao(1), _questao(2, impressao="b"))
    uma = servico.criar_simulado(quantidade=1)
    outra = servico.criar_simulado(quantidade=1)

    _, questao_da_outra = servico.questao_atual(outra.id)
    if questao_da_outra.id not in [
        r.questao_id for r in servico._respostas(uma.id)
    ]:
        assert servico.responder(uma.id, questao_da_outra.id, "c") is None


def test_a_rodada_termina_sozinha(banco_temporario):
    _semear(_questao(1))
    simulado = servico.criar_simulado(quantidade=1)
    _, questao = servico.questao_atual(simulado.id)
    servico.responder(simulado.id, questao.id, "c")

    assert servico.questao_atual(simulado.id) is None
    assert servico.resumo_do_simulado(simulado.id)["terminou"] is True
    assert servico.buscar_simulado(simulado.id).finalizado_em is not None


def test_da_para_parar_no_meio_e_voltar(banco_temporario):
    """O lugar onde eu parei fica no banco, nao na sessao do navegador."""
    _semear(_questao(1), _questao(2, impressao="b"), _questao(3, impressao="c"))
    simulado = servico.criar_simulado(quantidade=3)

    _, primeira = servico.questao_atual(simulado.id)
    servico.responder(simulado.id, primeira.id, "c")

    # "fecha o navegador" - nada e guardado em memoria
    atual = servico.questao_atual(simulado.id)
    assert atual is not None
    assert atual[1].id != primeira.id


# --- desempenho -------------------------------------------------------------

def test_acerto_por_materia(banco_temporario):
    _semear(
        _questao(1, materia="Língua Portuguesa"),
        _questao(2, materia="Língua Portuguesa", impressao="b"),
        _questao(3, materia="Raciocínio Lógico", impressao="c"),
    )
    simulado = servico.criar_simulado(quantidade=3)

    for _ in range(3):
        atual = servico.questao_atual(simulado.id)
        _, questao = atual
        # acerta portugues, erra raciocinio
        letra = "c" if questao.materia == "Língua Portuguesa" else "a"
        servico.responder(simulado.id, questao.id, letra)

    por_materia = {d.materia: d for d in servico.desempenho(simulado.id)}
    assert por_materia["Língua Portuguesa"].porcentagem == 100
    assert por_materia["Raciocínio Lógico"].porcentagem == 0


def test_a_materia_com_pior_acerto_vem_primeiro(banco_temporario):
    """E onde vale gastar tempo de estudo."""
    _semear(
        _questao(1, materia="Boa"),
        _questao(2, materia="Ruim", impressao="b"),
    )
    simulado = servico.criar_simulado(quantidade=2, materia=None)

    for _ in range(2):
        _, questao = servico.questao_atual(simulado.id)
        servico.responder(simulado.id, questao.id, "c" if questao.materia == "Boa" else "a")

    assert servico.desempenho(simulado.id)[0].materia == "Ruim"


def test_desempenho_geral_soma_todas_as_rodadas(banco_temporario):
    _semear(_questao(1), _questao(2, impressao="b"))

    for _ in range(2):
        simulado = servico.criar_simulado(quantidade=1)
        _, questao = servico.questao_atual(simulado.id)
        servico.responder(simulado.id, questao.id, "c")

    geral = servico.desempenho()
    assert sum(d.respondidas for d in geral) == 2


def test_questao_nao_respondida_nao_entra_na_conta(banco_temporario):
    _semear(_questao(1), _questao(2, impressao="b"))
    servico.criar_simulado(quantidade=2)

    assert servico.desempenho() == []


# --- revisao ----------------------------------------------------------------

def test_a_revisao_mostra_o_que_eu_marquei_e_a_correta(banco_temporario):
    """Errar sem ver a correta nao ensina nada."""
    _semear(_questao(1))
    simulado = servico.criar_simulado(quantidade=1)
    _, questao = servico.questao_atual(simulado.id)
    servico.responder(simulado.id, questao.id, "a")

    item = servico.revisao(simulado.id)[0]
    assert item.escolhida == "a"
    assert item.texto_escolhido == "um"
    assert item.correta == "c"
    assert item.texto_correto == "tres"
    assert item.acertou is False


def test_a_revisao_poe_os_erros_primeiro(banco_temporario):
    _semear(_questao(1), _questao(2, impressao="b"))
    simulado = servico.criar_simulado(quantidade=2)

    _, primeira = servico.questao_atual(simulado.id)
    servico.responder(simulado.id, primeira.id, "c")     # acerta
    _, segunda = servico.questao_atual(simulado.id)
    servico.responder(simulado.id, segunda.id, "a")      # erra

    assert servico.revisao(simulado.id)[0].acertou is False


# --- a tela -----------------------------------------------------------------

def test_a_tela_de_comecar_abre(cliente):
    _semear(_questao(1))
    resposta = cliente.get("/simulado")

    assert resposta.status_code == 200
    assert "Comecar" in resposta.text


def test_sem_questao_a_tela_explica_o_que_fazer(cliente):
    texto = cliente.get("/simulado").text
    assert "radar provas" in texto and "radar questoes" in texto


def test_fluxo_inteiro_pela_tela(cliente):
    _semear(_questao(1), _questao(2, impressao="b"))

    criacao = cliente.post(
        "/simulado/novo", data={"materia": "", "quantidade": "2"},
        follow_redirects=False,
    )
    assert criacao.status_code == 303
    destino = criacao.headers["location"]

    for _ in range(2):
        pagina = cliente.get(destino)
        assert pagina.status_code == 200

        import re
        achado = re.search(r'name="questao_id" value="(\d+)"', pagina.text)
        assert achado, "a tela precisa mostrar uma questao"

        cliente.post(
            f"{destino}/responder",
            data={"questao_id": achado.group(1), "letra": "c"},
            follow_redirects=False,
        )

    resultado = cliente.get(destino)
    assert "100%" in resultado.text
    assert "Fazer outro" in resultado.text


def test_simulado_que_nao_existe_volta_para_o_inicio(cliente):
    resposta = cliente.get("/simulado/9999", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/simulado"


def test_o_radar_tem_link_para_o_simulado(cliente):
    """O simulado saiu da barra de filtros de concurso e virou uma das duas
    faces de Estudar. O caminho ficou mais longo por um clique, e mais claro:
    Macetes e Simulado sao a mesma tarefa em dois passos."""
    _semear(_questao(1))

    assert 'href="/estudar"' in cliente.get("/").text
    assert cliente.get("/estudar", follow_redirects=False).headers["location"] == (
        "/macetes"
    )
    assert 'href="/simulado"' in cliente.get("/macetes").text
