"""O treino com questoes reais de outras bancas (decisao 166, etapa A).

O que estes testes seguram:
  - o estoque e so de questao de outra banca (`fora`), classificada dentro dos
    nos, uma por chave, com gabarito, sem anulada e com as alternativas
    inteiras; a FEPESE nunca entra nele;
  - as nunca feitas saem primeiro, e a rodada guarda a faixa de onde saiu;
  - respondida no radar, a questao de outra banca mede o meu acerto no no, e
    a divisao diz a origem ao lado ("1 FEPESE, 1 de outras bancas");
  - e nunca entra no que a FEPESE cobra: nem na incidencia, nem no estoque das
    rodadas que medem;
  - o pedido de classificacao aceita `--evidencia fora`, com a instrucao
    propria e um codigo que nunca aponta para duas questoes;
  - a tela Hoje mostra o botao so na faixa cujo tema tem questao de outra
    banca, e o botao abre a rodada.

Nada depende da data de hoje: o dia da tela e fixo, como no test_geradas_da_faixa.
"""
import random
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import classificacoes, composicao, conteudos
from radar.servico import cronograma as diario
from radar.servico import desempenho_por_conteudo as por_conteudo
from radar.servico import incidencia as servico_incidencia
from radar.servico import manual, outras_bancas
from radar.servico import simulado as servico_simulado
from radar.web.app import app
from tests.test_composicao import (ALVO_2019, INTERPRETACAO, ORTOGRAFIA,  # noqa: F401
                                   PORTUGUES, PROGRAMA, _questao)

PROVA_IESES = "https://ieses.test/2024/caderno-{}.pdf"
QUATRO = {"a": "um", "b": "dois", "c": "três", "d": "quatro"}


def _de_outra(numero, caminho, *, caderno=1, alternativas=None, anulada=False,
              resposta="a", banca="IESES", enunciado=None, pendente=False):
    """Grava a questao de outra banca e a classifica no no `caminho`."""
    with sessao() as s:
        q = QuestaoDeProva(
            prova_url=PROVA_IESES.format(caderno), banca=banca, ano=2024,
            numero=numero, materia=PORTUGUES,
            enunciado=enunciado or f"Questão de outra banca {numero} sobre {caminho}?",
            alternativas=dict(QUATRO if alternativas is None else alternativas),
            resposta=None if anulada else resposta, anulada=anulada,
            impressao=f"ieses-{numero}-{caderno}", evidencia="fora")
        s.add(q)
        s.flush()
        chave = classificacoes.chave_de(q)
        ident = q.id
    classificacoes.classificar(chave, caminho, "manual",
                               status="pendente" if pendente else None)
    return ident


@pytest.fixture
def acervo(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    # Da FEPESE, no mesmo no: nunca entra no estoque de outras bancas.
    _questao(1, PORTUGUES, INTERPRETACAO, ALVO_2019)
    # Tres de outra banca em Interpretacao; a de numero 12 se repete noutro
    # caderno (a IESES reaproveita): e uma questao so.
    _de_outra(11, INTERPRETACAO)
    _de_outra(12, INTERPRETACAO, enunciado="A mesma questão nos dois cadernos?")
    _de_outra(12, INTERPRETACAO, caderno=2, enunciado="A mesma questão nos dois cadernos?")
    # E numa terceira versao: alternativas embaralhadas e a palavra partida.
    _de_outra(12, INTERPRETACAO, caderno=3, enunciado="A mes ma questão nos dois cadernos?",
              alternativas={"a": "dois", "b": "um", "c": "três", "d": "quatro"},
              resposta="b")
    _de_outra(13, INTERPRETACAO)
    # As que nao servem: anulada, alternativas faltando, classificacao pendente.
    _de_outra(14, INTERPRETACAO, anulada=True)
    _de_outra(15, INTERPRETACAO, alternativas={"a": "um", "b": "dois"})
    _de_outra(16, INTERPRETACAO, pendente=True)
    # Outro no.
    _de_outra(17, ORTOGRAFIA)


def _ids_da_rodada(rodada):
    with sessao() as s:
        return list(s.scalars(select(RespostaDeSimulado.questao_id)
                              .where(RespostaDeSimulado.simulado_id == rodada.id)
                              .order_by(RespostaDeSimulado.ordem)))


# --- o estoque -----------------------------------------------------------------

def test_o_estoque_e_so_de_outra_banca_dentro_do_no_e_uma_por_chave(acervo):
    estoque = outras_bancas.estoque([INTERPRETACAO])
    with sessao() as s:
        numeros = sorted(s.get(QuestaoDeProva, c.id).numero for c in estoque)
    assert numeros == [11, 12, 13]
    assert {c.banca for c in estoque} == {"IESES"}


def test_sem_no_nao_ha_estoque(acervo):
    assert outras_bancas.estoque([]) == []
    assert outras_bancas.criar_rodada([], 5) is None


def test_o_no_de_cima_pega_o_que_esta_abaixo(acervo):
    assert len(outras_bancas.estoque([PORTUGUES])) == 4


def test_as_nunca_feitas_saem_primeiro():
    candidatas = [outras_bancas.Candidata(i, f"k{i}", INTERPRETACAO, "IESES", f"m{i}")
                  for i in range(1, 6)]
    escolhidas = outras_bancas.escolher(candidatas, {"m1", "m2"}, 4, random.Random(1))
    assert {c.mesma for c in escolhidas[:3]} == {"m3", "m4", "m5"}
    assert escolhidas[3].mesma in {"m1", "m2"}


def test_a_versao_embaralhada_e_a_mesma_questao(acervo):
    """As tres versoes da 12 (dois cadernos iguais e um embaralhado, com a
    palavra partida) sao uma questao so; responder uma faz das outras feitas."""
    with sessao() as s:
        versoes = list(s.scalars(select(QuestaoDeProva).where(QuestaoDeProva.numero == 12)))
        outra = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.numero == 13))
    assert len({classificacoes.chave_de(q) for q in versoes}) == 2
    assert len({outras_bancas.mesma_questao(q) for q in versoes}) == 1
    assert outras_bancas.mesma_questao(outra) != outras_bancas.mesma_questao(versoes[0])

    embaralhada = next(q for q in versoes if q.resposta == "b")
    _responder(embaralhada.id, "b")
    resumo = outras_bancas.da_faixa([INTERPRETACAO])
    assert resumo.no_acervo == 3 and resumo.feitas == 1


# --- a rodada ------------------------------------------------------------------

def test_a_rodada_guarda_a_faixa_e_respeita_a_quantidade(acervo):
    da_faixa = {"data": "2026-10-05", "bloco": "manha", "indice": 0, "titulo": "Fixação"}
    rodada = outras_bancas.criar_rodada([INTERPRETACAO], 2, da_faixa)

    assert len(_ids_da_rodada(rodada)) == 2
    assert rodada.filtros["rodada"] == outras_bancas.RODADA
    assert rodada.filtros["da_faixa"] == da_faixa
    assert rodada.filtros["bancas"] == ["IESES"]
    # Treino: o certo e o errado aparecem na hora.
    assert servico_simulado.corrige_na_hora(rodada)


def test_a_rodada_nunca_passa_do_que_existe(acervo):
    rodada = outras_bancas.criar_rodada([INTERPRETACAO], 30)
    assert len(_ids_da_rodada(rodada)) == 3


# --- a medida ------------------------------------------------------------------

def _responder(questao_id, letra):
    with sessao() as s:
        rodada = Simulado(filtros={"rodada": "teste"})
        s.add(rodada)
        s.flush()
        s.add(RespostaDeSimulado(simulado_id=rodada.id, questao_id=questao_id, ordem=1))
        ident = rodada.id
    return servico_simulado.responder(ident, questao_id, letra)


def test_a_outra_banca_mede_o_no_com_a_origem_ao_lado(acervo):
    with sessao() as s:
        da_fepese = s.scalar(select(QuestaoDeProva.id).where(QuestaoDeProva.numero == 1))
        da_ieses = s.scalar(select(QuestaoDeProva.id).where(QuestaoDeProva.numero == 11))
    assert _responder(da_fepese, "a") is True
    assert _responder(da_ieses, "b") is False

    no = por_conteudo.por_no(por_conteudo.SEMPRE)[INTERPRETACAO]
    assert no.radar.respostas == 2 and no.radar.acertos == 1
    assert no.radar.de_outras_bancas == 1
    assert "radar 50% em 2 (1 FEPESE, 1 de outras bancas)" in no.divisao()


def test_sem_outra_banca_a_divisao_e_a_de_sempre(acervo):
    with sessao() as s:
        da_fepese = s.scalar(select(QuestaoDeProva.id).where(QuestaoDeProva.numero == 1))
    _responder(da_fepese, "a")
    no = por_conteudo.por_no(por_conteudo.SEMPRE)[INTERPRETACAO]
    assert no.divisao() == "radar 100% em 1 · anotado —"


def test_a_outra_banca_nunca_entra_no_que_a_fepese_cobra(acervo):
    # A incidencia do alvo so le o alvo.
    assert {o.prova for o in servico_incidencia.ocorrencias()} == {ALVO_2019}
    # O estoque das rodadas que medem (e da faixa de Portugues) so a FEPESE.
    estoque = composicao.estoque_real([PORTUGUES])
    assert {c.evidencia for lista in estoque.values() for c in lista} == {"alvo"}


# --- o pedido de classificacao -------------------------------------------------

def test_o_pedido_de_outras_bancas_tem_so_elas_e_a_instrucao_propria(acervo):
    lote = manual.pedido_de_classificacao(None, "fora")
    (pedido,) = lote["pedidos"]
    assert pedido["evidencia"] == "fora"
    assert pedido["instrucao"] == manual.INSTRUCAO_CLASSIFICACAO_OUTRAS_BANCAS
    assert "OUTRA BANCA" in pedido["instrucao"]
    assert "lei de outro estado" in pedido["instrucao"]
    # A repetida em dois cadernos vai uma vez so (a embaralhada e outra
    # chave, e vai tambem); a da FEPESE nao vai.
    assert len(pedido["questoes"]) == 8
    assert len(set(pedido["questoes"].values())) == 8


def test_o_codigo_nunca_aponta_para_duas_questoes(banco_temporario):
    """Muitos cadernos no mesmo ano: o sufixo da prova pode repetir, e o
    contador desempata."""
    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        for caderno in range(40):
            s.add(QuestaoDeProva(
                prova_url=PROVA_IESES.format(caderno), banca="IESES", ano=2024,
                numero=1, materia=PORTUGUES, enunciado=f"Questão do caderno {caderno}?",
                alternativas=dict(QUATRO), resposta="a", impressao=f"i{caderno}",
                evidencia="fora"))
    (pedido,) = manual.pedido_de_classificacao(None, "fora")["pedidos"]
    assert len(pedido["questoes"]) == 40
    assert len(set(pedido["questoes"].values())) == 40


def test_evidencia_desconhecida_e_recusada(banco_temporario):
    with pytest.raises(ValueError):
        manual.pedido_de_classificacao(None, "qconcursos")


# --- a tela --------------------------------------------------------------------

def test_das_faixas_toda_faixa_com_no_e_a_sem_estoque_com_zero(acervo):
    """A faixa sem questao de outra banca tambem volta, com zero, e a tela
    diz "ainda nao ha" (pedido de 17/10); a sem no, nao."""
    com = SimpleNamespace(sem_no=False, questoes=6, nos=(SimpleNamespace(no=INTERPRETACAO),))
    sem = SimpleNamespace(sem_no=False, questoes=6,
                          nos=(SimpleNamespace(no=f"{PORTUGUES} > Emprego da crase"),))
    sem_no = SimpleNamespace(sem_no=True, questoes=6, nos=())
    resumo = outras_bancas.das_faixas({("manha", 0): com, ("manha", 1): sem,
                                       ("noite", 0): sem_no})
    assert sorted(resumo) == [("manha", 0), ("manha", 1)]
    assert resumo[("manha", 1)].no_acervo == 0
    assert resumo[("manha", 0)].no_acervo == 3
    assert resumo[("manha", 0)].sugeridas == 3
    assert resumo[("manha", 0)].bancas == ["IESES"]


@pytest.fixture
def em_05_10(acervo, monkeypatch):
    """O cronograma real em 05/10: o bonus tem os nos de Raciocinio Logico no
    plano. Uma questao de outra banca em Tabelas-verdade acende o botao."""
    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 5))


def test_a_tela_hoje_mostra_o_botao_e_o_botao_abre_a_rodada(em_05_10):
    tabelas = "Raciocínio Lógico > Tabelas-verdade"
    with sessao() as s:
        q = QuestaoDeProva(
            prova_url=PROVA_IESES.format(99), banca="IESES", ano=2024, numero=50,
            materia="Matemática e Raciocínio Lógico",
            enunciado="Qual a tabela-verdade da conjunção?",
            alternativas=dict(QUATRO), resposta="b", impressao="rl-50", evidencia="fora")
        s.add(q)
        s.flush()
        chave = classificacoes.chave_de(q)
    classificacoes.classificar(chave, tabelas, "manual")

    cliente = TestClient(app)
    html = cliente.get("/hoje?data=2026-10-05").text
    assert "Gerar questões outras bancas" in html
    assert "1 questão real</b>" in html or "1 questão real de outras bancas" in html
    assert "(IESES)" in html

    resposta = cliente.post("/outras-bancas/treinar", data={
        "conteudos": [tabelas], "quantidade": "5", "data": "2026-10-05",
        "bloco": "manha", "indice": "0", "titulo": "Bônus"}, follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/simulado/")
    pagina = cliente.get(resposta.headers["location"]).text
    assert "outras bancas" in pagina and "IESES" in pagina


def test_o_botao_sem_estoque_volta_para_o_dia(acervo):
    resposta = TestClient(app).post("/outras-bancas/treinar", data={
        "conteudos": [f"{PORTUGUES} > Emprego da crase"], "data": "2026-10-05"},
        follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje?data=2026-10-05"


def test_so_novas_pede_so_a_questao_sem_classificacao(acervo):
    """As provas novas do acervo (decisao 167) se pedem sem refazer o que ja
    foi classificado e espera a minha conferencia."""
    with sessao() as s:
        s.add(QuestaoDeProva(
            prova_url=PROVA_IESES.format(77), banca="IESES", ano=2024, numero=1,
            materia=PORTUGUES, enunciado="Questão nova, ainda sem classificação?",
            alternativas=dict(QUATRO), resposta="a", impressao="nova-1", evidencia="fora"))
    (todas,) = manual.pedido_de_classificacao(None, "fora")["pedidos"]
    (novas,) = manual.pedido_de_classificacao(None, "fora", so_novas=True)["pedidos"]
    assert len(todas["questoes"]) == 9
    assert len(novas["questoes"]) == 1
