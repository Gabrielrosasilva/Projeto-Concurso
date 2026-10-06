"""O "Treinar geral no radar" da faixa (06/10/2026).

Os botoes de cada no continuam; o geral junta todos os nos da faixa numa
rodada so, embaralhada, para eu nao saber de qual assunto vem a proxima. O
sorteio divide a quantidade por igual entre os nos (o puro traria quase tudo
do no com mais geradas), e a rodada guarda a faixa como as outras.

As datas sao fixas: nada aqui depende do dia em que o teste roda.
"""
from collections import Counter
from datetime import datetime

from fastapi.testclient import TestClient
from markupsafe import escape
from sqlalchemy import select

from radar import cronograma, fichas
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import fichas as servico_fichas
from radar.servico import geradas
from radar.util import fuso_local
from radar.web.app import app

CRIME = "Direito Penal > Teoria do crime"
DOLO = "Direito Penal > Teoria do crime > Dolo e culpa"
TENTATIVA = "Direito Penal > Teoria do crime > Tentativa"
PENAS = "Direito Penal > Penas"
FAIXA = {"data": "2026-09-28", "bloco": "manha", "indice": 2, "titulo": "Teoria do crime"}


def _geradas(conteudo: str, quantas: int, materia: str = "Direito Penal"):
    with sessao() as s:
        for i in range(quantas):
            s.add(QuestaoGerada(
                modo="do_zero", materia=materia, conteudo=conteudo,
                enunciado=f"{conteudo} {i}", impressao=f"{conteudo}#{i}", resposta="a"))


def _por_no(rodada) -> Counter:
    with sessao() as s:
        ids = s.scalars(select(RespostaDeSimulado.questao_id)
                        .where(RespostaDeSimulado.simulado_id == rodada.id))
        return Counter(s.get(QuestaoGerada, i).conteudo for i in ids)


def test_divide_por_igual_entre_os_nos(banco_temporario):
    _geradas(DOLO, 10)
    _geradas(TENTATIVA, 10)

    rodada = geradas.criar_simulado(quantidade=4, conteudos=[DOLO, TENTATIVA])

    assert _por_no(rodada) == Counter({DOLO: 2, TENTATIVA: 2})


def test_o_no_que_acaba_passa_a_vez(banco_temporario):
    _geradas(DOLO, 10)
    _geradas(TENTATIVA, 1)

    rodada = geradas.criar_simulado(quantidade=5, conteudos=[DOLO, TENTATIVA])

    assert _por_no(rodada) == Counter({DOLO: 4, TENTATIVA: 1})


def test_no_dentro_do_outro_nao_repete_questao(banco_temporario):
    _geradas(DOLO, 2)
    _geradas(TENTATIVA, 1)

    # O assunto ja contem o subassunto: as 3 do Dolo e da Tentativa, uma vez so.
    rodada = geradas.criar_simulado(quantidade=30, conteudos=[CRIME, DOLO])

    assert _por_no(rodada) == Counter({DOLO: 2, TENTATIVA: 1})
    assert rodada.filtros["quantidade"] == 3


def test_a_rodada_guarda_os_nos_e_a_faixa(banco_temporario):
    _geradas(DOLO, 2)
    _geradas(PENAS, 2)

    rodada = geradas.criar_simulado(quantidade=4, conteudos=[DOLO, PENAS], da_faixa=FAIXA)

    assert rodada.filtros["conteudos"] == [DOLO, PENAS]
    assert rodada.filtros["da_faixa"] == FAIXA
    assert rodada.filtros["geradas"] is True
    # O botao de um no so continua sem a chave nova.
    assert "conteudos" not in geradas.criar_simulado(quantidade=1, conteudo=DOLO).filtros


def test_o_post_com_os_nos_repetidos(banco_temporario):
    _geradas(DOLO, 3)
    _geradas(PENAS, 3)

    resposta = TestClient(app).post("/geradas/treinar", data={
        "conteudos": [DOLO, PENAS], "quantidade": "4", "data": FAIXA["data"],
        "bloco": FAIXA["bloco"], "indice": str(FAIXA["indice"]), "titulo": FAIXA["titulo"],
    }, follow_redirects=False)

    assert resposta.status_code == 303
    with sessao() as s:
        (simulado,) = s.scalars(select(Simulado))
        assert simulado.filtros["da_faixa"] == FAIXA
    assert _por_no(simulado) == Counter({DOLO: 2, PENAS: 2})


def _faixa(nos_e_geradas: list[tuple[str, int]], questoes: int) -> fichas.GeradasDaFaixa:
    return fichas.GeradasDaFaixa(
        tema="Teoria do crime", materia="Direito Penal", questoes=questoes, filtro=None,
        nos=tuple(fichas.GeradasDoNo(no=no, geradas=g, cota=0, pedir=0)
                  for no, g in nos_e_geradas))


def test_quantas_o_geral_sugere():
    # As do plano, sem passar das geradas nem de 30.
    assert _faixa([(DOLO, 5), (PENAS, 5)], questoes=8).geral == 8
    assert _faixa([(DOLO, 2), (PENAS, 1)], questoes=8).geral == 3
    assert _faixa([(DOLO, 40), (PENAS, 40)], questoes=50).geral == 30
    # Com um no so com gerada, o geral seria o botao de cima: nao aparece.
    assert _faixa([(DOLO, 5), (PENAS, 0)], questoes=8).geral == 0
    assert _faixa([(DOLO, 5)], questoes=8).geral == 0
    assert _faixa([(DOLO, 5), (PENAS, 0)], questoes=8).nos_com_geradas == [DOLO]


def _faixa_do_plano_com_dois_nos(plano):
    """A primeira faixa de treino do plano real com 2 nos ou mais."""
    escritas = servico_fichas.carregar()
    for dia in plano.dias:
        do_dia = dia.faixas()
        for faixa in do_dia:
            if not geradas._faixa_de_treino(faixa, plano):
                continue
            g = fichas.geradas_da_faixa(faixa, fichas.da_faixa_no_dia(faixa, do_dia, escritas), {})
            if len(g.nos) >= 2:
                return dia.data, faixa, [n.no for n in g.nos]
    raise AssertionError("o plano real nao tem faixa de treino com 2 nos")


def test_a_tela_mostra_o_geral_em_cada_faixa_com_dois_nos(banco_temporario, monkeypatch):
    plano = cronograma.carregar()
    data, faixa, nos = _faixa_do_plano_com_dois_nos(plano)
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()))
    cliente = TestClient(app)

    # Um no so com gerada: so os botoes de cada no.
    _geradas(nos[0], 3, materia=faixa.materia)
    antes = cliente.get(f"/hoje?data={data.isoformat()}").text
    assert "Treinar no radar" in antes

    _geradas(nos[1], 3, materia=faixa.materia)
    depois = cliente.get(f"/hoje?data={data.isoformat()}").text

    assert "Treinar geral no radar" in depois
    for no in nos[:2]:
        assert f'name="conteudos" value="{escape(no)}"' in depois
    # Mesma faixa, os dois estados: o geral so aparece com o segundo no.
    assert depois.count("Treinar geral no radar") > antes.count("Treinar geral no radar")
