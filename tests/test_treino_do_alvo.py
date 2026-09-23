"""O simulado do alvo: treinar para a MINHA prova, e nao para uma qualquer.

O pedido da etapa 9: "primeiro as questoes das provas de 2013 e 2019; quando
acabarem, questoes da FEPESE das mesmas materias em outros concursos".

Duas regras de conteudo saem disso, e as duas sao testadas aqui:

- a ORDEM importa. As provas do proprio cargo sao a prova de verdade; a mesma
  banca em outro concurso e a segunda melhor coisa;
- a MATERIA limita. Conhecimentos Especificos da prova de Merendeira e da
  mesma banca e nao me serve de nada.

O cargo do alvo e lido de `config/alvo.yml`, o arquivo de verdade - e por isso
as questoes aqui sao catalogadas como "Agente Penitenciario", o nome que o
cargo tinha em 2013 e 2019.
"""
import pytest
from fastapi.testclient import TestClient

from radar import servico
from radar.db import sessao
from radar.models import QuestaoDeProva
from radar.web.app import app

DO_ALVO = "Agente Penitenciário"


def _questao(numero: int, **mudancas) -> QuestaoDeProva:
    base = dict(
        prova_url=f"https://fepese.test/prova{numero}.pdf",
        banca="FEPESE",
        ano=2019,
        municipio=None,
        cargo=DO_ALVO,
        numero=numero,
        materia="Direitos Humanos",
        enunciado=f"Enunciado {numero}?",
        alternativas={"a": "um", "b": "dois"},
        resposta="a",
        impressao=f"impressao{numero}",
    )
    base.update(mudancas)
    return QuestaoDeProva(**base)


def _semear(*questoes):
    with sessao() as s:
        for q in questoes:
            s.add(q)


def _responder_tudo(simulado_id: int) -> None:
    """Responde a rodada inteira, para as questoes contarem como vistas."""
    while True:
        atual = servico.questao_atual(simulado_id)
        if atual is None:
            return
        _resposta, questao = atual
        servico.responder(simulado_id, questao.id, "a")


def _cargos_da_rodada(simulado_id: int) -> list[str]:
    with sessao() as s:
        from radar.models import RespostaDeSimulado
        from sqlalchemy import select

        return [
            cargo for (cargo,) in s.execute(
                select(QuestaoDeProva.cargo)
                .join(RespostaDeSimulado,
                      RespostaDeSimulado.questao_id == QuestaoDeProva.id)
                .where(RespostaDeSimulado.simulado_id == simulado_id)
                .order_by(RespostaDeSimulado.ordem)
            )
        ]


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- a ordem de preferencia -------------------------------------------------

def test_as_provas_do_cargo_vem_primeiro(banco_temporario):
    """Elas sao a prova de verdade; nenhuma outra chega perto."""
    _semear(
        *[_questao(n) for n in range(1, 4)],
        *[_questao(50 + n, cargo="Merendeira") for n in range(1, 4)],
    )

    simulado = servico.criar_simulado_do_alvo(quantidade=3)

    assert _cargos_da_rodada(simulado.id) == [DO_ALVO] * 3
    assert simulado.filtros["proprias"] == 3
    assert simulado.filtros["da_banca"] == 0


def test_quando_as_do_cargo_acabam_entra_a_mesma_banca(banco_temporario):
    """O caso que a etapa 9 resolve: sao 160 questoes do cargo, e 8 rodadas de
    20 acabam com elas."""
    _semear(
        _questao(1),
        *[_questao(50 + n, cargo="Merendeira") for n in range(1, 4)],
    )

    simulado = servico.criar_simulado_do_alvo(quantidade=4)

    cargos = _cargos_da_rodada(simulado.id)
    assert cargos[0] == DO_ALVO             # a do cargo, primeiro
    assert cargos.count("Merendeira") == 3  # o resto completa
    assert simulado.filtros == {
        "quantidade": 4, "alvo": "Policia Penal SC",
        "proprias": 1, "da_banca": 3, "repetidas": 0,
    }


def test_a_rodada_seguinte_nao_repete_o_que_eu_ja_respondi(banco_temporario):
    """Sem isso, "quando acabarem" nunca aconteceria: a mesma questao voltaria
    para sempre e eu nunca chegaria nas da banca."""
    _semear(
        *[_questao(n) for n in range(1, 3)],
        *[_questao(50 + n, cargo="Merendeira") for n in range(1, 3)],
    )

    primeira = servico.criar_simulado_do_alvo(quantidade=2)
    _responder_tudo(primeira.id)

    segunda = servico.criar_simulado_do_alvo(quantidade=2)

    assert _cargos_da_rodada(segunda.id) == ["Merendeira"] * 2
    assert segunda.filtros["da_banca"] == 2


def test_com_tudo_respondido_a_rodada_repete_e_avisa(banco_temporario):
    """Repetir e melhor que tela vazia - mas a rodada registra que repetiu,
    senao o resultado diria uma coisa que nao e."""
    _semear(_questao(1), _questao(2))

    primeira = servico.criar_simulado_do_alvo(quantidade=2)
    _responder_tudo(primeira.id)

    segunda = servico.criar_simulado_do_alvo(quantidade=2)

    assert segunda.filtros["repetidas"] == 2
    assert segunda.filtros["proprias"] == 0


def test_a_questao_do_cargo_repetida_vem_antes_da_banca_repetida(banco_temporario):
    """Entre duas questoes ja respondidas, a do meu cargo ainda vale mais."""
    _semear(_questao(1), _questao(50, cargo="Merendeira"))

    primeira = servico.criar_simulado_do_alvo(quantidade=2)
    _responder_tudo(primeira.id)

    segunda = servico.criar_simulado_do_alvo(quantidade=1)

    assert _cargos_da_rodada(segunda.id) == [DO_ALVO]


# --- o que a materia deixa entrar -------------------------------------------

def test_materia_que_nao_caiu_na_minha_prova_fica_de_fora(banco_temporario):
    """Conhecimentos Especificos de Merendeira e da mesma banca e nao me serve
    de nada. E o filtro que separa "a segunda melhor coisa" de "qualquer
    coisa"."""
    _semear(
        _questao(1),
        _questao(50, cargo="Merendeira", materia="Conhecimentos Específicos"),
    )

    simulado = servico.criar_simulado_do_alvo(quantidade=5)

    assert _cargos_da_rodada(simulado.id) == [DO_ALVO]


def test_a_materia_casa_sem_acento_e_sem_caixa(banco_temporario):
    """Cada caderno escreve o cabecalho do jeito dele."""
    _semear(
        _questao(1, materia="Direitos Humanos"),
        _questao(50, cargo="Merendeira", materia="DIREITOS HUMANOS"),
    )

    simulado = servico.criar_simulado_do_alvo(quantidade=5)

    assert len(_cargos_da_rodada(simulado.id)) == 2


def test_outra_banca_nao_entra_mesmo_na_mesma_materia(banco_temporario):
    """A banca do meu concurso sai de `config/alvo.yml`: a IESES cobra
    Direitos Humanos de outro jeito, e o ponto do treino e o jeito DELA."""
    _semear(
        _questao(1),
        _questao(50, cargo="Merendeira", banca="IESES"),
    )

    simulado = servico.criar_simulado_do_alvo(quantidade=5)

    assert _cargos_da_rodada(simulado.id) == [DO_ALVO]


def test_sem_prova_do_cargo_nao_ha_simulado_do_alvo(banco_temporario):
    """None, e nao "sorteia qualquer coisa": chamar de treino do alvo o que
    nao e seria a mesma mentira que a tela de foco evita."""
    _semear(_questao(50, cargo="Merendeira"))

    assert servico.criar_simulado_do_alvo(quantidade=5) is None


def test_nao_repete_enunciado_dentro_da_rodada(banco_temporario):
    """A banca reaproveita muito: a mesma pergunta aparece em varios cadernos,
    e duas vezes na mesma rodada e uma rodada menor do que parece."""
    _semear(
        _questao(1, impressao="mesma"),
        _questao(2, impressao="mesma"),
        _questao(3, impressao="outra"),
    )

    simulado = servico.criar_simulado_do_alvo(quantidade=3)

    assert servico.resumo_do_simulado(simulado.id)["total"] == 2


# --- a conta que a tela mostra ----------------------------------------------

def test_a_conta_separa_as_duas_fontes(banco_temporario):
    _semear(
        _questao(1), _questao(2),
        _questao(50, cargo="Merendeira"),
    )

    conta = servico.contar_questoes_do_alvo()

    assert conta == {
        "proprias": 2, "proprias_novas": 2,
        "da_banca": 1, "da_banca_novas": 1,
    }


def test_a_conta_desconta_o_que_eu_ja_respondi(banco_temporario):
    _semear(_questao(1), _questao(2))

    _responder_tudo(servico.criar_simulado_do_alvo(quantidade=1).id)

    conta = servico.contar_questoes_do_alvo()
    assert conta["proprias"] == 2
    assert conta["proprias_novas"] == 1


# --- a tela -----------------------------------------------------------------

def test_o_botao_da_home_monta_a_rodada_do_alvo(cliente):
    _semear(_questao(1))

    resposta = cliente.post("/foco/treinar", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/simulado/")


def test_sem_questao_do_cargo_o_botao_leva_para_o_simulado_comum(cliente):
    _semear(_questao(50, cargo="Merendeira"))

    resposta = cliente.post("/foco/treinar", follow_redirects=False)

    assert resposta.headers["location"] == "/simulado"


def test_a_home_diz_de_onde_a_proxima_rodada_sai(cliente):
    _semear(_questao(1), _questao(50, cargo="Merendeira"))

    texto = cliente.get("/").text

    assert "das provas do cargo" in texto
    assert "1 da mesma banca nas mesmas materias" in texto


def test_a_home_avisa_quando_as_provas_do_cargo_acabaram(cliente):
    _semear(_questao(1), _questao(50, cargo="Merendeira"))
    _responder_tudo(servico.criar_simulado_do_alvo(quantidade=1).id)

    assert "as provas do cargo acabaram" in cliente.get("/").text


def test_a_rodada_diz_de_onde_as_questoes_vieram(cliente):
    """Acertar 70% nas questoes da minha prova nao e a mesma coisa que acertar
    70% em prova de outro cargo: a tela nao pode confundir as duas."""
    _semear(_questao(1), _questao(50, cargo="Merendeira"))

    simulado = servico.criar_simulado_do_alvo(quantidade=2)
    texto = cliente.get(f"/simulado/{simulado.id}").text

    assert "Treino de Policia Penal SC" in texto
    assert "1 das provas do cargo" in texto
    assert "1 da mesma banca, mesmas materias" in texto


def test_o_simulado_comum_nao_ganha_o_rotulo_do_alvo(cliente):
    _semear(_questao(1))

    simulado = servico.criar_simulado(quantidade=1)
    texto = cliente.get(f"/simulado/{simulado.id}").text

    assert "Treino de" not in texto
    assert "Questoes reais" in texto


def test_caderno_sem_gabarito_nao_promete_rodada(cliente):
    """O painel conta toda questao do cargo; o sorteio so usa as que tem
    gabarito. Quando as duas discordavam - caderno no acervo sem o gabarito ao
    lado - o botao aparecia dizendo "ja respondi todas" e o clique caia no
    simulado comum."""
    _semear(_questao(1, resposta=None))

    texto = cliente.get("/").text
    assert "Treinar 20 questoes" not in texto      # o botao, nao o titulo
    assert "ja respondi todas" not in texto
    assert "Nenhuma questao do cargo no acervo ainda" in texto

    resposta = cliente.post("/foco/treinar", follow_redirects=False)
    assert resposta.headers["location"] == "/simulado"
