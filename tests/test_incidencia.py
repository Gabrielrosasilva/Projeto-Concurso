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


def test_o_filtro_de_materia_do_mapa_ignora_acento_e_caixa(alvo):
    """F3: o mesmo filtro do `radar incidencia --materia`, digitado sem acento."""
    (penal,) = servico_da_incidencia.mapa("direito penal")
    (lep,) = servico_da_incidencia.mapa("Lei de Execucao Penal")

    assert (penal.materia, lep.materia) == ("Direito Penal", "Lei de Execução Penal")


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


# --- os padroes do acervo complementar (F4, decisao 78) -----------------------------

COMPLEMENTARES = [
    _oc("2021", MENORIDADE, impressao="x1",
        enunciado="Analise as afirmativas abaixo sobre a menoridade penal."),
    # A mesma questao em outro caderno: uma questao so.
    _oc("2022", MENORIDADE, impressao="x1",
        enunciado="Analise as afirmativas abaixo sobre a menoridade penal."),
    _oc("2022", MENORIDADE, impressao="x2", resposta="b"),
    _oc("2023", MENORIDADE, impressao="x3", resposta="c", tipo_de_questao="conceito",
        pegadinha="troca a idade da maioridade"),
]


def test_os_padroes_do_complementar_contam_questao_distinta_e_dizem_a_origem():
    p = incidencia.padroes_complementares(MENORIDADE, COMPLEMENTARES, incidencia.Minimos())

    assert p.suficiente
    assert p.amostra == ("padrão identificado no acervo analisado: 3 questões · 3 provas · "
                         "acervo complementar FEPESE, só das provas com gabarito definitivo")
    # A questao repetida entra uma vez so no gabarito.
    assert sum(n for _, n, _ in p.gabarito) == 3
    assert not PREVISAO.search(p.amostra + p.nota)


def test_tipo_e_pegadinha_do_complementar_so_da_classificacao_conferida():
    """A classificacao do complementar e automatica e ninguem a conferiu:
    texto que ninguem conferiu nao vira padrao do acervo."""
    sem_conferir = incidencia.padroes_complementares(
        MENORIDADE, COMPLEMENTARES, incidencia.Minimos())
    assert (sem_conferir.tipos, sem_conferir.pegadinhas) == ([], [])
    assert "nenhuma questão deste conteúdo foi conferida ainda" in sem_conferir.nota

    conferida = COMPLEMENTARES[:3] + [
        _oc("2023", MENORIDADE, impressao="x3", resposta="c", tipo_de_questao="conceito",
            pegadinha="troca a idade da maioridade", conferida=True)]
    com = incidencia.padroes_complementares(MENORIDADE, conferida, incidencia.Minimos())
    assert com.tipos == [("conceito", 1)]
    assert com.pegadinhas == ["troca a idade da maioridade"]
    assert "só da 1 questão com classificação conferida (de 3)" in com.nota


def test_abaixo_da_materia_o_padrao_do_complementar_so_conta_a_classificada():
    """Na materia conta a questao que o caderno poe nela; abaixo, so a
    classificada - as mesmas regras da linha complementar."""
    ocorrencias = COMPLEMENTARES + [_oc("2024", MENORIDADE, status="pendente", impressao="x4")]

    no_subassunto = incidencia.padroes_complementares(MENORIDADE, ocorrencias,
                                                      incidencia.Minimos())
    na_materia = incidencia.padroes_complementares("Direito Penal", ocorrencias,
                                                   incidencia.Minimos())

    assert "3 questões · 3 provas" in no_subassunto.amostra
    assert "4 questões · 4 provas" in na_materia.amostra


def test_abaixo_do_minimo_o_padrao_do_complementar_diz_a_frase_exata():
    # A mesma questao em dois cadernos: 1 questao, abaixo do minimo de 3.
    p = incidencia.padroes_complementares(MENORIDADE, COMPLEMENTARES[:2], incidencia.Minimos())

    assert not p.suficiente
    assert p.frase == "Não há evidência suficiente no acervo para afirmar isso."


def _complementares_no_banco(*provas_e_padrao):
    """Grava uma questao por prova complementar e o registro da 3B."""
    import json

    from radar.servico import complementar

    with sessao() as s:
        for numero, (url, _) in enumerate(provas_e_padrao, start=1):
            s.add(QuestaoDeProva(
                prova_url=url, banca="FEPESE", ano=2024, numero=numero,
                materia="Direito Penal", enunciado=f"Questão complementar {numero}?",
                alternativas={"a": "x", "b": "y"}, resposta="a",
                impressao=f"comp{numero}", evidencia="complementar"))
    complementar.caminho_do_registro().write_text(json.dumps({"provas": [
        {"prova_url": url, "aceita": True, "entra_nos_padroes": padrao}
        for url, padrao in provas_e_padrao]}), encoding="utf-8")


def test_so_as_provas_com_gabarito_definitivo_entram_nos_padroes(alvo):
    """A 3B: o gabarito provisorio serve para classificar, mas o padrao se mede
    sobre a letra certa, que muda depois dos recursos."""
    _complementares_no_banco(("https://fepese.test/definitivo.pdf", True),
                             ("https://fepese.test/provisorio.pdf", False))

    provas = {o.prova for o in servico_da_incidencia.ocorrencias_dos_padroes()}

    assert provas == {"https://fepese.test/definitivo.pdf"}


def test_prova_complementar_nova_nao_muda_os_padroes_do_alvo(alvo):
    """Secao 4: os numeros do alvo nao mudam quando entra prova complementar."""
    minimos = incidencia.carregar_minimos()
    antes = {l.caminho: incidencia.padroes(l, minimos)
             for m in servico_da_incidencia.mapa() for l in m.linhas}

    _complementares_no_banco(*((f"https://fepese.test/c{n}.pdf", True) for n in range(4)))

    depois = {l.caminho: incidencia.padroes(l, minimos)
              for m in servico_da_incidencia.mapa() for l in m.linhas}
    assert depois == antes


def test_a_pagina_e_o_terminal_mostram_os_padroes_do_complementar_a_parte(alvo):
    texto = TestClient(app).get("/analises/incidencia").text
    assert "Acervo complementar FEPESE" in texto
    assert "acervo complementar FEPESE, só das provas com gabarito definitivo" in texto
    assert "Os dois blocos nunca se somam" in texto
    assert not PREVISAO.search(texto)

    saida = CliRunner().invoke(cli, ["incidencia", "--padroes"], env={"COLUMNS": "200"})
    assert saida.exit_code == 0, saida.output
    assert "complementar:" in saida.output


# --- a conta por no sem comparar cada questao com cada no (F6) ------------------

@pytest.mark.parametrize("caminho", [
    "Direito Penal",
    "Direito Penal > Aplicação da lei penal",
    "Direito Penal > Aplicação da lei penal > Lei penal no tempo",
    "Direito Penal Militar > Crimes militares",
])
def test_o_no_e_os_de_cima_sao_exatamente_os_nos_de_debaixo(caminho):
    """A lista nova tem de dar o MESMO que a pergunta antiga, no por no -
    inclusive para "Direito Penal Militar", que comeca com "Direito Penal" e
    nao esta debaixo dele."""
    nos = ["Direito Penal", "Direito Penal > Aplicação da lei penal",
           "Direito Penal > Aplicação da lei penal > Lei penal no tempo",
           "Direito Penal > Aplicação", "Direito Penal Militar",
           "Direito Penal Militar > Crimes militares", "Língua Portuguesa"]

    de_cima = incidencia._o_no_e_os_de_cima(caminho)

    for no in nos:
        assert incidencia._debaixo(caminho, no) == (no in de_cima), no
