"""Os conceitos associados (§14, item 7 do novo.md; decisao 86).

O que estes testes seguram:

  * o pedido leva cada questao do alvo com a classificacao principal, e a
    arvore inteira - o associado pode morar noutra materia;
  * a importacao grava o associado como NAO principal, com o trecho, e recusa
    no fora da arvore, a materia inteira, o ramo da principal e conceito sem
    trecho - sem gravar nada pela metade;
  * a incidencia nao muda: a contagem continua so com a principal;
  * a tela mostra os pares, com as questoes e o selo de "por conferir".
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import edital_programa
from radar.db import sessao
from radar.models import Classificacao, Conteudo, QuestaoDeProva
from radar.servico import classificacoes, conteudos, manual
from radar.servico import incidencia as servico_da_incidencia
from radar.web.app import app

FIXTURES = Path(__file__).parent / "fixtures"
PROGRAMA = edital_programa.ler_programa(
    (FIXTURES / "provas" / "edital_sap_2019_programa.txt").read_text(encoding="utf-8"))
PENAL = "Direito Penal"


def _questao(numero):
    return QuestaoDeProva(
        prova_url="https://fepese.test/2019.pdf", banca="FEPESE", ano=2019,
        numero=numero, materia=PENAL, cargo="Agente Penitenciário",
        enunciado=f"Questão {numero} de 2019 sobre {PENAL}?",
        alternativas={letra: f"{letra}{numero}" for letra in "abcde"}, resposta="a",
        impressao=f"2019-{numero}", evidencia="alvo")


@pytest.fixture
def alvo(banco_temporario):
    """A arvore do edital, duas questoes de Penal e a principal da q51."""
    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        s.add(_questao(51))
        s.add(_questao(52))
    principal, outro = _assuntos()[:2]
    classificacoes.classificar(_chave(51), principal, "teste")
    classificacoes.classificar(_chave(52), principal, "teste")
    return principal, outro


def _assuntos():
    with sessao() as s:
        return sorted(s.scalars(select(Conteudo.caminho).where(Conteudo.pai == PENAL)))


def _chave(numero):
    with sessao() as s:
        q = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.numero == numero))
    return classificacoes.chave_de(q)


def _importar(tmp_path, lote, nos, codigo="2019-q51"):
    manual.salvar_pedido(lote)
    arquivo = tmp_path / "resposta.json"
    resposta = {"lote": lote["lote"], "respostas": [
        {"id": lote["pedidos"][0]["id"], "associados": [{"questao": codigo, "nos": nos}]}]}
    arquivo.write_text(json.dumps(resposta), encoding="utf-8")
    return manual.importar(arquivo)


def _linhas(numero):
    with sessao() as s:
        return list(s.scalars(select(Classificacao).where(Classificacao.chave == _chave(numero))))


# --- o pedido ---------------------------------------------------------------------

def test_o_pedido_leva_a_principal_e_a_arvore_inteira(alvo):
    principal, _ = alvo

    lote = manual.pedido_de_associados()

    (pedido,) = lote["pedidos"]
    assert lote["tipo"] == "associados" and pedido["materia"] == PENAL
    assert set(pedido["questoes"]) == {"2019-q51", "2019-q52"}
    assert pedido["principais"]["2019-q51"] == principal
    assert f"PRINCIPAL: {principal}" in pedido["pedido"]
    # A arvore inteira, e nao so a da materia: o associado pode ser de outra.
    assert any(not c.startswith(PENAL) for c in pedido["arvore"])


# --- a importacao -------------------------------------------------------------------

def test_a_importacao_grava_o_associado_sem_mexer_na_principal(alvo, tmp_path):
    principal, outro = alvo

    resultado = _importar(tmp_path, manual.pedido_de_associados(),
                          [{"no": outro, "trecho": "a alternativa c fala disso"}])

    assert resultado["gravadas"] == 1 and resultado["recusas"] == []
    linhas = {c.conteudo: c for c in _linhas(51)}
    assert linhas[principal].principal
    assert not linhas[outro].principal
    assert linhas[outro].trecho == "a alternativa c fala disso"
    assert linhas[outro].procedencia


@pytest.mark.parametrize("no, trecho, motivo", [
    ("Direito Penal > Isto não existe", "x", "não está na árvore"),
    (PENAL, "x", "matéria inteira"),
    ("PRINCIPAL", "x", "ramo da principal"),
    ("OUTRO", "", "sem o trecho"),
])
def test_o_que_a_importacao_de_associados_recusa(alvo, tmp_path, no, trecho, motivo):
    principal, outro = alvo
    no = {"PRINCIPAL": principal, "OUTRO": outro}.get(no, no)

    # Junto com um associado bom: a questao inteira fica de fora, e nao pela
    # metade.
    resultado = _importar(tmp_path, manual.pedido_de_associados(),
                          [{"no": outro, "trecho": "bom"}, {"no": no, "trecho": trecho}])

    assert resultado["gravadas"] == 0
    assert any(motivo in r for r in resultado["recusas"]), resultado["recusas"]
    assert [c.conteudo for c in _linhas(51)] == [principal]


def test_questao_que_nao_estava_no_pedido_e_recusada(alvo, tmp_path):
    _, outro = alvo

    resultado = _importar(tmp_path, manual.pedido_de_associados(),
                          [{"no": outro, "trecho": "x"}], codigo="2013-q99")

    assert resultado["gravadas"] == 0
    assert "não estava no pedido" in resultado["recusas"][0]


# --- a incidencia e a tela ----------------------------------------------------------

def test_a_incidencia_nao_conta_o_associado_e_mostra_o_par(alvo, tmp_path):
    principal, outro = alvo
    _importar(tmp_path, manual.pedido_de_associados(), [{"no": outro, "trecho": "x"}])

    (mapa,) = servico_da_incidencia.mapa(PENAL)
    linhas = {linha.caminho: linha for linha in mapa.linhas}

    # So a principal conta: as duas questoes no principal, nenhuma no outro.
    assert len(linhas[principal].questoes) == 2
    assert len(linhas[outro].questoes) == 0
    (par,) = servico_da_incidencia.associacoes([mapa])[PENAL]
    assert (par.principal, par.associado, par.questoes) == (principal, outro, ("2019 q51",))


def test_a_pagina_mostra_os_conceitos_que_aparecem_juntos(alvo, tmp_path):
    principal, outro = alvo
    _importar(tmp_path, manual.pedido_de_associados(), [{"no": outro, "trecho": "x"}])

    html = " ".join(TestClient(app).get("/analises/incidencia").text.split())

    assert "Conceitos que aparecem juntos nas questões" in html
    assert "Classificação do Claude Code, por conferir" in html
    assert "1 questão (2019 q51)" in html
    assert principal.split(" > ")[-1] in html and outro.split(" > ")[-1] in html


def test_sem_associado_a_pagina_nao_mostra_o_bloco(alvo):
    assert "Conceitos que aparecem juntos" not in TestClient(app).get("/analises/incidencia").text


# --- a conferencia dos associados -----------------------------------------------------

def test_a_importacao_nova_tira_o_associado_que_saiu_e_guarda_o_conferido(alvo, tmp_path):
    """Refazer o pedido acrescentava e atualizava, mas nao apagava: o associado
    que a resposta nova nao traz sai - menos o que eu ja conferi."""
    principal, outro = alvo
    terceiro = _assuntos()[2]
    _importar(tmp_path, manual.pedido_de_associados(),
              [{"no": outro, "trecho": "um"}, {"no": terceiro, "trecho": "dois"}])
    classificacoes.conferir_associado(_chave(51), terceiro)

    _importar(tmp_path, manual.pedido_de_associados(), [])

    assert {c.conteudo for c in _linhas(51)} == {principal, terceiro}


def test_a_tela_de_conferencia_mostra_confirma_e_tira_o_associado(alvo, tmp_path):
    principal, outro = alvo
    _importar(tmp_path, manual.pedido_de_associados(),
              [{"no": outro, "trecho": "a alternativa c fala disso"}])
    cliente = TestClient(app)

    pagina = cliente.get("/analises/conferencia?associados=1").text
    assert "Conceitos associados (1 por conferir)" in pagina
    assert "a alternativa c fala disso" in pagina
    assert "0 de 1 conceitos associados" in pagina
    assert "2019-q52" not in pagina  # sem associado, fora do filtro

    cliente.post("/analises/conferencia", data={
        "chave": _chave(51), "conteudo": outro, "acao": "associado_confirmar"})
    assert "1 de 1 conceitos associados" in cliente.get("/analises/conferencia").text
    assert "2019-q51" not in cliente.get("/analises/conferencia?associados=1").text

    resposta = cliente.post("/analises/conferencia", data={
        "chave": _chave(51), "conteudo": outro, "acao": "associado_tirar",
        "associados": "1"}, follow_redirects=False)
    assert "associados=1" in resposta.headers["location"]
    linhas = _linhas(51)
    assert [c.conteudo for c in linhas] == [principal] and linhas[0].principal


def test_tirar_associado_que_nao_existe_nao_mexe_em_nada(alvo):
    principal, _ = alvo
    with pytest.raises(classificacoes.ClassificacaoInvalida):
        classificacoes.tirar_associado(_chave(51), principal)  # e a principal
    assert [c.conteudo for c in _linhas(51)] == [principal]
