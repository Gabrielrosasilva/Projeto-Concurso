"""A lacuna do texto-base que a leitura por colunas perdia (decisao 165).

O que estes testes seguram:

  * no texto de lacunas, o espaco duplo do meio da linha e o espaco do
    comeco da linha viram ____ - e o texto continua com os mesmos paragrafos;
  * o texto que nao e de lacunas fica como estava: o recuo de paragrafo e um
    espaco duplo solto nao viram lacuna;
  * a questao de completar diz quantas lacunas a leitura nao mostra, pela
    contagem dos itens da alternativa ("há • a • à"), e a tela avisa com o
    link do caderno; a questao inteira, sem texto, tambem avisa;
  * a questao que nao e de lacunas, e a gerada, nunca avisam.

A fixture e um caderno inventado: o texto real e de terceiros e mora so no
banco local.
"""
from pathlib import Path

from radar import questoes
from radar.db import sessao
from radar.fichas import QuestaoReal
from radar.models import QuestaoDeProva

from tests.test_foco import com_quadro_do_edital  # noqa: F401 - fixture

FIXTURES = Path(__file__).parent / "fixtures"
CADERNO = (FIXTURES / "caderno_texto_de_lacunas.txt").read_text(encoding="utf-8")
LACUNA = questoes.LACUNA
ALTERNATIVAS = {"a": "há • a • à • à • à", "b": "há • a • à • à • a",
                "c": "a • à • a • a • à", "d": "à • a • à • a • a",
                "e": "há • à • a • à • à"}
COMPLETE = "Assinale a alternativa que completa corretamente as lacunas do texto."


# --- a leitura ------------------------------------------------------------------

def test_o_espaco_duplo_e_o_espaco_do_comeco_viram_lacuna():
    texto = questoes.textos_base(CADERNO)["1"]

    assert texto.count(LACUNA) == 5
    assert f"reabriu {LACUNA} dez anos" in texto
    assert f"pertenceu {LACUNA} prefeitura" in texto      # a que abria a linha
    assert f"turistas {LACUNA} praia e {LACUNA} serra." in texto


def test_marcar_a_lacuna_nao_muda_os_paragrafos():
    texto = questoes.textos_base(CADERNO)["1"]

    assert texto.split("\n")[-1] == "SILVA, Ana. Revista de Teste, 2020. [Adaptado]"
    assert texto.split("\n")[0].endswith(f"turistas {LACUNA} praia e {LACUNA} serra.")
    assert texto.count("\n") == 1


def test_o_texto_sem_lacunas_fica_como_estava():
    texto = questoes.textos_base(CADERNO)["2"]

    assert LACUNA not in texto
    assert texto.startswith("A feira do sábado A feira volta")   # o recuo saiu
    assert "leva  a fruta" in texto                                # um duplo so


def test_a_regua_do_texto_de_lacunas():
    um_duplo = ["A feira  volta.", " Recuo de paragrafo."]
    dois_duplos = ["A feira  volta.", " Recuo de paragrafo.", "Quem  compra."]

    assert questoes._marcar_lacunas_do_texto(um_duplo) == um_duplo
    assert questoes._marcar_lacunas_do_texto(dois_duplos) == [
        f"A feira {LACUNA} volta.", f"{LACUNA} Recuo de paragrafo.", f"Quem {LACUNA} compra."]


# --- quantas a leitura perdeu ---------------------------------------------------

def test_a_questao_de_completar_conta_as_lacunas_que_faltam():
    inteiro = f"reabriu {LACUNA} dez, voltaram {LACUNA}, {LACUNA} praia, {LACUNA}, {LACUNA}"
    faltando = f"reabriu {LACUNA} dez, voltaram {LACUNA} frequentar, {LACUNA} praia"

    assert questoes.lacunas_perdidas(COMPLETE, ALTERNATIVAS, inteiro) == 0
    assert questoes.lacunas_perdidas(COMPLETE, ALTERNATIVAS, faltando) == 2
    assert questoes.lacunas_perdidas(COMPLETE, ALTERNATIVAS, None) == 5


def test_a_lacuna_escrita_no_enunciado_tambem_conta():
    enunciado = ("Assinale a alternativa que preenche os espaços em branco: "
                 "Fui ____ praia; cheguei ____ tempo; voltei .......... noite.")

    assert questoes.lacunas_perdidas(enunciado, {"a": "à • a • à"}, None) == 0


def test_a_lacuna_numerada_conta_e_as_reticencias_do_autor_nao():
    numeradas = ("Analise o texto: a avaliação (1) ____ , que aponta para uma "
                 "avaliação (2) , vai além do aspecto (3) . Assinale a alternativa que "
                 "completa corretamente as lacunas numeradas do texto.")
    alternativas = {"a": "(1) diagnóstica • (2) global • (3) quantitativo"}

    assert questoes.lacunas_perdidas(numeradas, alternativas, None) == 0
    assert questoes.lacunas_perdidas(COMPLETE, ALTERNATIVAS,
                                     f"{LACUNA} {LACUNA} {LACUNA} {LACUNA} e o autor… parou") == 1


def test_a_alternativa_de_2016_separa_os_itens_com_travessao():
    assert questoes.lacunas_perdidas("Há cinco lacunas no texto.",
                                     {"a": "a – a – à – a – à"}, None) == 5


def test_a_questao_que_nao_e_de_lacunas_nunca_avisa():
    assert questoes.lacunas_perdidas("De acordo com o texto, é correto afirmar:",
                                     ALTERNATIVAS, None) == 0
    # Sem os itens separados por "•" nao ha como contar.
    assert questoes.lacunas_perdidas(COMPLETE, {"a": "Alternativa um."}, None) == 0


def test_a_questao_inteira_da_ficha_sabe_o_que_faltou():
    questao = QuestaoReal("2024-q1", 2024, 1, "complementar", "Língua Portuguesa", "b",
                          COMPLETE, None, None, False,
                          alternativas=tuple(sorted(ALTERNATIVAS.items())),
                          prova="https://teste.invalid/AS.pdf",
                          texto_base=f"reabriu {LACUNA} dez, {LACUNA} praia")

    assert questao.lacunas_perdidas == 3


# --- a tela ---------------------------------------------------------------------

def test_a_gerada_nunca_avisa():
    from types import SimpleNamespace

    from radar.web.app import _lacunas_perdidas

    questao = SimpleNamespace(enunciado=COMPLETE, alternativas=ALTERNATIVAS)

    assert _lacunas_perdidas(SimpleNamespace(gerada=True), questao) == 0
    assert _lacunas_perdidas(SimpleNamespace(gerada=False), questao) == 5


def _rodada_de_lacunas(texto_base):
    from radar import servico

    from tests.test_home import _acervo

    _acervo()
    simulado = servico.criar_simulado(quantidade=3, materia="Direito Penal")
    with sessao() as s:
        for questao in s.query(QuestaoDeProva):
            questao.enunciado = COMPLETE
            questao.alternativas = ALTERNATIVAS
            questao.texto_base = texto_base
    return simulado


def test_a_tela_avisa_quantas_lacunas_a_leitura_nao_mostra(banco_temporario,
                                                            com_quadro_do_edital):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    simulado = _rodada_de_lacunas(f"reabriu {LACUNA} dez, {LACUNA} praia, {LACUNA} serra")
    with sessao() as s:
        url = s.query(QuestaoDeProva).first().prova_url

    texto = TestClient(app).get(f"/simulado/{simulado.id}").text

    assert "A leitura do caderno não mostra 2 lacunas desta questão" in texto
    assert f'href="{url}"' in texto


def test_a_tela_avisa_quando_o_texto_nao_veio(banco_temporario, com_quadro_do_edital):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    simulado = _rodada_de_lacunas(None)

    texto = TestClient(app).get(f"/simulado/{simulado.id}").text

    assert "A leitura do caderno não mostra 5 lacunas desta questão" in texto


def test_com_todas_as_lacunas_a_tela_nao_avisa(banco_temporario, com_quadro_do_edital):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    simulado = _rodada_de_lacunas(" ".join([f"x {LACUNA}"] * 5))

    texto = TestClient(app).get(f"/simulado/{simulado.id}").text

    assert "A leitura do caderno" not in texto
