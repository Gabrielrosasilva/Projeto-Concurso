"""O mapa de incidencia do alvo e os padroes de cobranca (Etapa 3A).

O que estes testes seguram: anulada e pendente ficam fora da conta e
aparecem a parte; o denominador e o das provas que tinham a materia; toda
linha leva a amostra; abaixo do minimo, a frase exata; e nenhum texto com
cara de previsao.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import conteudos as arvore
from radar import edital_programa, incidencia
from radar.cli import app as cli
from radar.db import sessao
from radar.models import QuestaoDeProva
from radar.servico import classificacoes, conteudos
from radar.servico import incidencia as servico_da_incidencia
from radar.web.app import app

PROGRAMA = edital_programa.ler_programa(
    (Path(__file__).parent / "fixtures" / "provas" / "edital_sap_2019_programa.txt")
    .read_text(encoding="utf-8"))

PREVISAO = re.compile(r"(?i)vai cair|certamente|sempre cobra|cairá")


def _no(caminho, nivel):
    partes = arvore.partes(caminho)
    return arvore.No(caminho=caminho, pai=arvore.SEPARADOR.join(partes[:-1]) or None,
                     nivel=nivel, nome=partes[-1])


NOS = [
    _no("Direito Penal", "materia"),
    _no("Direito Penal > Imputabilidade penal", "assunto"),
    _no("Direito Penal > Imputabilidade penal > Menoridade", "subassunto"),
    _no("Direito Penal > Crimes contra a Administração Pública", "assunto"),
    _no("Lei de Execução Penal", "materia"),
    _no("Lei de Execução Penal > A lei", "assunto"),
]


def _oc(prova, conteudo, status="completa", anulada=False, materia=None, **mais):
    return incidencia.Ocorrencia(
        prova=prova, ano=int(prova), materia=materia or arvore.partes(conteudo)[0],
        conteudo=conteudo, status=status, anulada=anulada,
        enunciado=mais.pop("enunciado", f"Assinale a alternativa correta {prova}."),
        resposta=mais.pop("resposta", "a"), impressao=mais.pop("impressao", f"{prova}-{conteudo}-{status}"),
        **mais)


MENORIDADE = "Direito Penal > Imputabilidade penal > Menoridade"
OCORRENCIAS = [
    _oc("2013", MENORIDADE, tipo_de_questao="conceito", impressao="a",
        enunciado="Analise as afirmativas abaixo sobre a menoridade."),
    _oc("2019", MENORIDADE, tipo_de_questao="literalidade da lei", impressao="b"),
    _oc("2019", "Direito Penal > Imputabilidade penal", impressao="c"),
    _oc("2019", "Direito Penal", status="pendente", impressao="d"),
    _oc("2013", MENORIDADE, anulada=True, impressao="e"),
    _oc("2019", "Lei de Execução Penal > A lei", impressao="f"),
]


def _mapa():
    return {m.materia: m for m in incidencia.montar(NOS, OCORRENCIAS)}


def _linha(mapa, caminho):
    return next(l for m in mapa.values() for l in m.linhas if l.caminho == caminho)


# --- a conta -----------------------------------------------------------------------

def test_anuladas_e_pendentes_fora_da_conta_mas_mostradas():
    penal = _mapa()["Direito Penal"]
    assert len(penal.topo.questoes) == 3          # nem a anulada, nem a pendente
    assert (penal.anuladas, penal.pendentes) == (1, 1)
    assert len(_linha(_mapa(), MENORIDADE).questoes) == 2


def test_a_questao_conta_no_no_e_nos_de_cima():
    mapa = _mapa()
    assert len(_linha(mapa, "Direito Penal > Imputabilidade penal").questoes) == 3
    assert len(_linha(mapa, MENORIDADE).questoes) == 2


def test_o_denominador_segue_as_provas_que_tinham_a_materia():
    mapa = _mapa()
    # LEP so caiu em 2019: "1 de 2 provas" enganaria.
    assert mapa["Lei de Execução Penal"].provas == 1
    assert mapa["Lei de Execução Penal"].topo.rotulo == "apareceu na única prova que cobrava a matéria"
    assert _linha(mapa, MENORIDADE).rotulo == "apareceu nas 2 provas"
    assert _linha(mapa, "Direito Penal > Crimes contra a Administração Pública").rotulo == (
        "não apareceu nas provas analisadas")
    so_em_2019 = incidencia.montar(NOS, OCORRENCIAS[1:4])
    imput = next(l for m in so_em_2019 for l in m.linhas
                 if l.caminho == "Direito Penal > Imputabilidade penal")
    assert imput.rotulo == "apareceu na única prova que cobrava a matéria"
    com_as_duas = incidencia.montar(NOS, OCORRENCIAS + [_oc("2013", "Direito Penal > Crimes contra a Administração Pública")])
    crimes = next(l for m in com_as_duas for l in m.linhas
                  if l.caminho.endswith("Crimes contra a Administração Pública"))
    assert crimes.rotulo == "apareceu em 1 de 2 provas"


def test_toda_linha_leva_a_amostra():
    for m in _mapa().values():
        for l in m.linhas:
            assert re.fullmatch(r"\d+ quest(ão|ões) · \d+ provas?", l.amostra)
    assert incidencia.amostra(1, 1) == "1 questão · 1 prova"
    assert incidencia.amostra(8, 2) == "8 questões · 2 provas"


# --- os padroes --------------------------------------------------------------------

def test_abaixo_do_minimo_a_frase_exata():
    linha = _linha(_mapa(), MENORIDADE)              # 2 questoes, 2 provas
    p = incidencia.padroes(linha, incidencia.Minimos(questoes=3, provas=2))
    assert not p.suficiente
    assert p.frase == "Não há evidência suficiente no acervo para afirmar isso."
    assert p.amostra == "padrão identificado no acervo analisado: 2 questões · 2 provas · alvo"


def test_com_a_amostra_o_padrao_aparece():
    linha = _linha(_mapa(), "Direito Penal")
    p = incidencia.padroes(linha, incidencia.Minimos(questoes=3, provas=2))
    assert p.suficiente
    assert ("conceito", 1) in p.tipos
    assert sum(n for _, n, _ in p.gabarito) == 3
    assert [c.nome for c in p.comandos] == ["analise as frases e depois assinale"]


def test_os_minimos_vem_do_config():
    minimos = incidencia.carregar_minimos()
    assert (minimos.questoes, minimos.provas) == (3, 2)


# --- do banco, na tela e no terminal ------------------------------------------------

@pytest.fixture
def alvo(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        for ano, numero, materia in ((2013, 47, "Direito Penal"), (2019, 51, "Direito Penal"),
                                     (2019, 81, "Lei de Execução Penal")):
            s.add(QuestaoDeProva(
                prova_url=f"https://fepese.test/{ano}.pdf", banca="FEPESE", ano=ano,
                numero=numero, materia=materia, enunciado=f"Questão {numero}?",
                alternativas={"a": "x", "b": "y"}, resposta="a",
                impressao=f"{ano}-{numero}", evidencia="alvo"))
    with sessao() as s:
        questoes = {q.numero: q for q in s.query(QuestaoDeProva)}
    classificacoes.classificar(classificacoes.chave_de(questoes[47]),
                               "Direito Penal > Imputabilidade penal", "manual")
    classificacoes.classificar(classificacoes.chave_de(questoes[51]),
                               "Direito Penal > Imputabilidade penal", "manual")


def test_o_mapa_do_banco_so_conta_o_alvo(alvo):
    antes = {m.materia: m.topo.amostra for m in servico_da_incidencia.mapa()}
    with sessao() as s:
        s.add(QuestaoDeProva(prova_url="https://fepese.test/outra.pdf", banca="FEPESE",
                             ano=2024, numero=1, materia="Direito Penal", enunciado="Outra?",
                             alternativas={"a": "x"}, impressao="outra", evidencia="complementar"))
    depois = {m.materia: m.topo.amostra for m in servico_da_incidencia.mapa()}
    assert antes == depois
    assert depois["Direito Penal"] == "2 questões · 2 provas"
    lep = next(m for m in servico_da_incidencia.mapa() if m.materia == "Lei de Execução Penal")
    assert (lep.topo.amostra, lep.pendentes) == ("0 questões · 0 provas", 1)


def test_a_pagina_e_o_terminal_mostram_a_amostra_e_nao_preveem(alvo):
    texto = TestClient(app).get("/analises/incidencia").text
    assert "2 questões · 2 provas" in texto and "apareceu nas 2 provas" in texto
    assert "não apareceu nas provas analisadas" in texto
    assert "Não há evidência suficiente no acervo para afirmar isso." in texto
    assert not PREVISAO.search(texto)

    saida = CliRunner().invoke(cli, ["incidencia", "--padroes"], env={"COLUMNS": "200"})
    assert saida.exit_code == 0, saida.output
    assert "2 questões · 2 provas" in saida.output
    assert "Não há evidência suficiente no acervo para afirmar isso." in saida.output
    assert not PREVISAO.search(saida.output)
