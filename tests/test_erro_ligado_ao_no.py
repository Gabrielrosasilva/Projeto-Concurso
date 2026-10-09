"""O erro anotado chega ligado ao no (U21 · P36, decisao 144).

O que estes testes seguram:

  * cada erro do relatorio da rodada tem o seu "Anotar erro", com a materia e
    o no DA QUESTAO (a classificacao principal);
  * o "Anotar erro" da faixa leva o no que eu dei a ela (o `conteudo`, os
    `nos`, a ficha CONFERIDA) - nunca o da ficha por conferir (decisao 81);
  * a faixa mista (os Diagnosticos) nao preenche a materia;
  * o formulario marca o no quando ha um so, poe os da faixa no topo quando ha
    varios, e ignora no fora da arvore.
"""
from datetime import date
from html import escape, unescape
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import cronograma, edital_programa, fichas, servico
from radar.db import sessao
from radar.models import Conteudo, QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import classificacoes, conteudos, estudo
from radar.web.app import app, link_de_anotar_erro, link_de_anotar_erro_da_questao

FIXTURES = Path(__file__).parent / "fixtures"
PROGRAMA = edital_programa.ler_programa(
    (FIXTURES / "provas" / "edital_sap_2019_programa.txt").read_text(encoding="utf-8"))
PENAL = "Direito Penal"


def _questao(numero):
    return QuestaoDeProva(
        prova_url="https://fepese.test/2019.pdf", banca="FEPESE", ano=2019,
        numero=numero, materia=PENAL, assunto="Aplicação da lei penal",
        cargo="Agente Penitenciário", enunciado=f"Questão {numero} de 2019?",
        alternativas={letra: f"{letra}{numero}" for letra in "abcde"}, resposta="a",
        impressao=f"2019-{numero}", evidencia="alvo")


@pytest.fixture
def arvore(banco_temporario):
    """A arvore do edital de 2019; devolve os assuntos de Penal."""
    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        return sorted(s.scalars(select(Conteudo.caminho).where(Conteudo.pai == PENAL)))


def _parametros(link: str) -> dict:
    return parse_qs(urlparse(unescape(link)).query, keep_blank_values=True)


def _links_de_anotar(tela: str) -> list[dict]:
    return [_parametros("/erros/novo?" + trecho.split('"')[0])
            for trecho in tela.split('href="/erros/novo?')[1:]]


def _rodada_que_mede(*questoes) -> int:
    """Uma rodada de diagnostico (mede: o certo so aparece no fim), com a
    letra errada em todas."""
    with sessao() as s:
        for q in questoes:
            s.add(q)
        s.flush()
        simulado = Simulado(filtros={"quantidade": len(questoes), "rodada": "diagnostico"})
        s.add(simulado)
        s.flush()
        for ordem, q in enumerate(questoes, start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=q.id, ordem=ordem,
                                     escolhida="b", acertou=False))
        return simulado.id


def _classificar(numero: int, no: str):
    with sessao() as s:
        questao = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.numero == numero))
        chave = classificacoes.chave_de(questao)
    classificacoes.classificar(chave, no, "teste")


# --- o relatorio da rodada ------------------------------------------------------

def test_cada_erro_do_relatorio_leva_a_materia_e_o_no_da_questao(arvore):
    rodada = _rodada_que_mede(_questao(51), _questao(52))
    _classificar(51, arvore[0])

    tela = TestClient(app).get(f"/simulado/{rodada}").text

    links = _links_de_anotar(tela)
    assert len(links) == 2
    assert all(link["materia"] == [PENAL] and link["fonte"] == ["radar"] for link in links)
    assert [link.get("no") for link in links] == [[arvore[0]], None]
    # A q52 nao tem classificacao: vai sem no, e a tela diz.
    assert "questão sem nó na árvore" in tela


def test_o_item_da_revisao_traz_o_no_e_a_referencia(arvore):
    rodada = _rodada_que_mede(_questao(51))
    _classificar(51, arvore[1])

    [item] = servico.revisao(rodada)

    assert item.conteudo == arvore[1]
    assert item.referencia == "FEPESE 2019, questão 51"
    link = _parametros(link_de_anotar_erro_da_questao(
        rodada, item.materia, item.assunto, item.referencia, item.chutou, item.conteudo))
    assert link["no"] == [arvore[1]]
    assert link["volta"] == [f"/simulado/{rodada}"]


def test_a_correcao_na_hora_tambem_leva_o_no(arvore):
    with sessao() as s:
        s.add(_questao(51))
        s.flush()
        simulado = Simulado(filtros={"quantidade": 1})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=1, ordem=1))
        rodada = simulado.id
    _classificar(51, arvore[0])
    cliente = TestClient(app)
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": 1, "letra": "b"})

    tela = cliente.get(f"/simulado/{rodada}?ver=1").text

    [link] = _links_de_anotar(tela)
    assert link["no"] == [arvore[0]]


# --- o formulario ------------------------------------------------------------------

def test_um_no_so_ja_vem_marcado(arvore):
    tela = TestClient(app).get("/erros/novo", params={"materia": PENAL, "no": arvore[0]}).text
    assert 'label="Desta faixa"' in tela
    assert f'<option value="{escape(arvore[0])}" selected>' in tela


def test_varios_nos_vem_no_topo_sem_marcar(arvore):
    tela = TestClient(app).get("/erros/novo",
                               params=[("no", arvore[0]), ("no", arvore[1])]).text
    topo = tela.split('label="Desta faixa"')[1].split("</optgroup>")[0]
    assert escape(arvore[0]) in topo and escape(arvore[1]) in topo
    assert "selected" not in topo


def test_no_fora_da_arvore_e_ignorado(arvore):
    tela = TestClient(app).get("/erros/novo", params={"no": "Matéria > Inventada"}).text
    assert "Desta faixa" not in tela
    assert "<option value=\"Matéria" not in tela


# --- a faixa -----------------------------------------------------------------------

def _faixa(**campos):
    base = dict(titulo="R+7: Aplicação da lei penal", materia=PENAL, conteudo=None,
                nos=(), desligada=False)
    base.update(campos)
    return SimpleNamespace(**base)


def _ficha(conferida: bool, nos):
    return fichas.FichaEscrita(tema="Aplicação da lei penal", materia=PENAL, nos=list(nos),
                               conferida_em="2026-10-09" if conferida else None)


def test_a_faixa_com_conteudo_liga_o_erro_a_ele():
    caminhos = {PENAL, "Direito Penal > A", "Direito Penal > A > a1"}
    faixa = _faixa(conteudo="Direito Penal > A")
    assert estudo.nos_do_erro(faixa, [], caminhos) == ["Direito Penal > A"]


def test_so_a_ficha_conferida_da_o_no():
    caminhos = {PENAL, "Direito Penal > A"}
    assert estudo.nos_do_erro(_faixa(), [_ficha(False, ["Direito Penal > A"])], caminhos) == []
    assert estudo.nos_do_erro(_faixa(), [_ficha(True, ["Direito Penal > A"])], caminhos) == \
        ["Direito Penal > A"]


def test_o_no_de_cima_sai_quando_o_de_baixo_esta_na_lista():
    caminhos = {PENAL, "Direito Penal > A", "Direito Penal > A > a1", "Direito Penal > B"}
    faixa = _faixa(nos=("Direito Penal > A", "Direito Penal > A > a1", "Direito Penal > B"))
    assert estudo.nos_do_erro(faixa, [], caminhos) == ["Direito Penal > A > a1",
                                                      "Direito Penal > B"]


def test_a_faixa_mista_nao_preenche_a_materia():
    plano = cronograma.carregar()
    mista = _parametros(link_de_anotar_erro(date(2026, 10, 17), "Diagnósticos",
                                            "R+7: refazer os erros dos diagnósticos",
                                            "/hoje", [], plano))
    assert mista["materia"] == [""]

    comum = _parametros(link_de_anotar_erro(date(2026, 10, 17), PENAL, "x", "/hoje",
                                            ["Direito Penal > A"], plano))
    assert comum["materia"] == [PENAL]
    assert comum["no"] == ["Direito Penal > A"]


def test_o_17_10_do_plano_real_nao_manda_diagnosticos(banco_temporario):
    tela = TestClient(app).get("/hoje?data=2026-10-17").text
    links = _links_de_anotar(tela)
    assert links
    assert not any("Diagn" in (link.get("materia") or [""])[0] for link in links)
