"""Treinar as geradas pelo no da arvore: materia, assunto ou subassunto.

Antes o "Treinar com as que ja tenho" so filtrava pela materia, e a ficha do
tema mandava para la - misturando os temas da materia, inclusive os que eu
ainda nao estudei.
"""
from html import escape
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from radar import servico
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado

DP = "Direito Penal"
CRIME = "Direito Penal > Teoria do crime"
DOLO = "Direito Penal > Teoria do crime > Dolo e culpa"
TENTATIVA = "Direito Penal > Teoria do crime > Tentativa"
PENAS = "Direito Penal > Penas"


@pytest.fixture
def cliente(banco_temporario):
    from radar.web.app import app

    return TestClient(app)


def _gerada(numero: int, conteudo: str | None, materia: str = DP, **mudancas):
    base = dict(
        modo="variacao",
        materia=materia,
        conteudo=conteudo,
        enunciado=f"Enunciado gerado numero {numero}, com tamanho bastante.",
        alternativas={l: f"texto {l}" for l in "abcde"},
        resposta="c",
        impressao=f"gerada{numero}",
        rejeitada=False,
    )
    base.update(mudancas)
    with sessao() as s:
        s.add(QuestaoGerada(**base))


def _semear():
    _gerada(1, DOLO)
    _gerada(2, DOLO)
    _gerada(3, TENTATIVA)
    _gerada(4, PENAS)
    # Elemento abaixo do subassunto: conta no subassunto, mas nao vira opcao.
    _gerada(5, DOLO + " > Dolo eventual")
    # Gerada antiga sem no: entra so pela materia.
    _gerada(6, None)
    _gerada(7, "Direitos Humanos > Mandela", materia="Direitos Humanos")
    # Rejeitada e sem gabarito nunca entram.
    _gerada(8, DOLO, rejeitada=True)
    _gerada(9, DOLO, resposta=None)


def _sorteadas(rodada) -> set[str]:
    with sessao() as s:
        ids = s.query(RespostaDeSimulado.questao_id).filter_by(simulado_id=rodada.id)
        return {s.get(QuestaoGerada, i).impressao for (i,) in ids}


def test_o_seletor_lista_materia_assunto_e_subassunto_com_a_contagem(banco_temporario):
    _semear()

    linhas = servico.geradas.conteudos_para_treinar()

    assert (DP, 1, 6) in linhas  # a 6, sem no, entra pela materia
    assert (CRIME, 2, 4) in linhas
    assert (DOLO, 3, 3) in linhas  # inclusive o elemento de baixo
    assert (TENTATIVA, 3, 1) in linhas
    assert (PENAS, 2, 1) in linhas
    # O elemento nao vira opcao; a gerada sem no fica na materia.
    assert all(nivel <= 3 for _, nivel, _ in linhas)
    caminhos = [c for c, _, _ in linhas]
    # Na ordem da arvore: a materia antes dos filhos dela.
    assert caminhos.index(DP) < caminhos.index(CRIME) < caminhos.index(DOLO)


def test_treinar_o_subassunto_sorteia_so_dele_e_de_baixo(banco_temporario):
    _semear()

    rodada = servico.geradas.criar_simulado(quantidade=30, conteudo=DOLO)

    assert _sorteadas(rodada) == {"gerada1", "gerada2", "gerada5"}
    with sessao() as s:
        assert s.get(Simulado, rodada.id).filtros["conteudo"] == DOLO


def test_treinar_o_assunto_pega_os_subassuntos(banco_temporario):
    _semear()

    rodada = servico.geradas.criar_simulado(quantidade=30, conteudo=CRIME)

    assert _sorteadas(rodada) == {"gerada1", "gerada2", "gerada3", "gerada5"}


def test_treinar_a_materia_pega_tambem_a_gerada_sem_no(banco_temporario):
    _semear()

    rodada = servico.geradas.criar_simulado(quantidade=30, conteudo=DP)

    assert _sorteadas(rodada) == {f"gerada{n}" for n in range(1, 7)}


def test_nome_que_e_comeco_de_outro_nao_mistura(banco_temporario):
    """"Teoria do crime" nao pode pegar "Teoria do crimeX": o filtro e pelo
    separador, e nao pelo comeco do texto."""
    _gerada(1, CRIME + "s impossiveis > Algo")
    _gerada(2, CRIME + " > Algo")

    rodada = servico.geradas.criar_simulado(quantidade=30, conteudo=CRIME)

    assert _sorteadas(rodada) == {"gerada2"}


def test_o_post_treina_pelo_no(cliente):
    _semear()

    resposta = cliente.post(
        "/geradas/treinar", data={"conteudo": TENTATIVA, "quantidade": "5"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    rodada_id = int(resposta.headers["location"].rsplit("/", 1)[1])
    with sessao() as s:
        ids = [i for (i,) in s.query(RespostaDeSimulado.questao_id)
               .filter_by(simulado_id=rodada_id)]
        assert [s.get(QuestaoGerada, i).impressao for i in ids] == ["gerada3"]


def test_no_sem_gerada_volta_com_recado(cliente):
    _semear()

    resposta = cliente.post(
        "/geradas/treinar", data={"conteudo": "Direito Penal > Nada", "quantidade": "5"},
        follow_redirects=False,
    )

    assert resposta.headers["location"] == "/geradas?recado=nada_no_no"
    assert "Não há questão gerada para treinar neste conteúdo" in cliente.get(
        resposta.headers["location"]).text


def test_a_tela_mostra_o_seletor_e_vem_com_o_no_da_ficha_escolhido(cliente):
    _semear()

    pagina = cliente.get(f"/geradas?treinar={quote(DOLO)}").text

    assert 'name="conteudo"' in pagina
    # O ">" do caminho sai escapado no atributo.
    assert f'<option value="{escape(DOLO)}" selected>' in pagina
    assert "↳ Dolo e culpa (3)" in pagina
    assert f'<option value="{escape(CRIME)}">' in pagina
