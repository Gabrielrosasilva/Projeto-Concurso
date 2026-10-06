"""O texto-base das questoes de interpretacao (item 4, 06/10/2026).

O que estes testes seguram:

  * o texto vai do cabecalho "Texto N" ate a primeira questao depois dele, sem
    o cabecalho e o rodape da pagina, e com a palavra partida por hifen inteira;
  * a prova que nao numera os textos tem um so, entre o titulo da secao de
    Portugues e a questao 1;
  * a questao recebe o texto que ela cita ("texto 1", "textos 1 e 2"), e a que
    nao cita nao recebe nada;
  * so a questao de Portugues das provas do alvo ganha o texto, e o resto da
    questao (enunciado, chave) nao muda;
  * o texto vai junto no pedido da IA e aparece na tela da questao.

As fixtures sao cadernos inventados: o texto real e de terceiros e mora so no
banco local.
"""
from pathlib import Path

from radar import gerador, questoes
from radar.db import sessao
from radar.models import QuestaoDeProva

from tests.test_foco import com_quadro_do_edital  # noqa: F401 - fixture

FIXTURES = Path(__file__).parent / "fixtures"
COM_TEXTOS = (FIXTURES / "caderno_com_textos.txt").read_text(encoding="utf-8")
TEXTO_UNICO = (FIXTURES / "caderno_texto_unico.txt").read_text(encoding="utf-8")


# --- o recorte dos textos ---------------------------------------------------------

def test_cada_texto_vai_do_cabecalho_ate_a_primeira_questao():
    textos = questoes.textos_base(COM_TEXTOS)

    assert set(textos) == {"1", "2"}
    assert textos["1"].startswith("O farol da ilha O farol da ilha acende")
    assert textos["1"].endswith("SILVA, Ana. Revista de Teste, 2019. [Adaptado]")
    assert "Assinale" not in textos["1"]
    assert textos["2"].startswith("A ponte nova")


def test_o_texto_sai_sem_a_mobilia_da_pagina_e_com_a_palavra_inteira():
    textos = questoes.textos_base(COM_TEXTOS)

    assert "Página" not in textos["2"]
    assert "Concurso Público" not in textos["2"]
    assert "um menino" in textos["1"]          # "me-" / "nino" voltou inteiro


def test_o_paragrafo_termina_na_linha_curta_que_fecha_a_frase():
    paragrafos = questoes.textos_base(COM_TEXTOS)["1"].split("\n")

    assert "Os pescadores dizem que foi um menino, há muitos anos." in paragrafos
    assert paragrafos[-1] == "SILVA, Ana. Revista de Teste, 2019. [Adaptado]"


def test_a_prova_sem_texto_numerado_tem_um_texto_so():
    textos = questoes.textos_base(TEXTO_UNICO)

    assert set(textos) == {questoes.TEXTO_UNICO}
    assert textos[questoes.TEXTO_UNICO].startswith("Como funciona a biblioteca")
    assert "acesso em 20.10.2013" in textos[questoes.TEXTO_UNICO]


def test_caderno_sem_texto_de_apoio_nao_inventa_texto():
    assert questoes.textos_base("Direito Penal 10 questões\n1. Pergunta?\n") == {}


# --- qual questao recebe qual texto -----------------------------------------------

def test_a_questao_recebe_o_texto_que_ela_cita():
    textos = questoes.textos_base(COM_TEXTOS)

    um = questoes.texto_da_questao("Assinale a alternativa correta, com base no texto 1.", textos)
    os_dois = questoes.texto_da_questao("De acordo com os textos 1 e 2, é correto afirmar:",
                                        textos)

    assert um.startswith("Texto 1\n") and "A ponte nova" not in um
    assert os_dois.startswith("Texto 1\n") and "\n\nTexto 2\n" in os_dois


def test_a_questao_que_nao_cita_texto_fica_sem():
    textos = questoes.textos_base(COM_TEXTOS)

    assert questoes.texto_da_questao(
        "Assinale a alternativa em que todas as palavras são acentuadas.", textos) is None
    assert questoes.texto_da_questao("Conforme o texto 7, é correto:", textos) is None


def test_na_prova_de_texto_unico_basta_falar_em_texto():
    textos = questoes.textos_base(TEXTO_UNICO)

    assert questoes.texto_da_questao("Assinale a alternativa correta em relação ao texto.",
                                     textos).startswith("Como funciona")
    assert questoes.texto_da_questao("Assinale a frase correta.", textos) is None


# --- o banco ------------------------------------------------------------------------

ALVO = "https://alvo.test/AP.pdf"
OUTRA = "https://outra.test/AP.pdf"


def _questao(prova: str, numero: int, materia: str, enunciado: str) -> None:
    with sessao() as s:
        s.add(QuestaoDeProva(prova_url=prova, banca="FEPESE", ano=2019, numero=numero,
                             materia=materia, enunciado=enunciado,
                             alternativas={"a": "x", "b": "y"}, resposta="a",
                             impressao=f"i{prova[-12:]}{numero}"))


def _guardar(monkeypatch, tmp_path):
    from radar.servico import evidencia
    from radar.servico import provas as servico_provas

    pdf = tmp_path / "ap.pdf"
    pdf.write_bytes(b"%PDF de mentira")
    monkeypatch.setattr(servico_provas.arquivos_de_prova, "carregar_manifesto",
                        lambda: [{"url": ALVO, "caminho": "ap.pdf"},
                                 {"url": OUTRA, "caminho": "ap.pdf"}])
    monkeypatch.setattr(servico_provas, "_caminho", lambda registro: pdf)
    monkeypatch.setattr(evidencia, "provas", lambda s, qual: {ALVO})
    monkeypatch.setattr(servico_provas.leitor_de_questoes, "extrair_por_colunas",
                        lambda caminho: COM_TEXTOS)
    return servico_provas.guardar_textos_base()


def test_so_a_questao_de_portugues_do_alvo_guarda_o_texto(banco_temporario,
                                                         monkeypatch, tmp_path):
    _questao(ALVO, 1, "Língua Portuguesa", "Assinale a correta, com base no texto 1.")
    _questao(ALVO, 2, "Língua Portuguesa", "Assinale a palavra acentuada.")
    _questao(ALVO, 30, "Direito Penal", "Conforme o texto 1 da lei, é correto:")
    _questao(OUTRA, 1, "Língua Portuguesa", "Assinale a correta, com base no texto 1.")

    feito = _guardar(monkeypatch, tmp_path)

    with sessao() as s:
        por = {(q.prova_url, q.numero): q.texto_base for q in s.query(QuestaoDeProva)}
    assert (feito.provas, feito.questoes) == (1, 1)
    assert por[(ALVO, 1)].startswith("Texto 1\nO farol")
    assert por[(ALVO, 2)] is None
    assert por[(ALVO, 30)] is None            # em Direito, "texto da lei" nao e apoio
    assert por[(OUTRA, 1)] is None            # so o alvo


def test_guardar_o_texto_nao_muda_a_questao(banco_temporario, monkeypatch, tmp_path):
    from radar.servico.classificacoes import chave_de

    _questao(ALVO, 1, "Língua Portuguesa", "Assinale a correta, com base no texto 1.")
    with sessao() as s:
        antes = chave_de(s.query(QuestaoDeProva).one())

    _guardar(monkeypatch, tmp_path)

    with sessao() as s:
        assert chave_de(s.query(QuestaoDeProva).one()) == antes


# --- onde o texto aparece -----------------------------------------------------------

def test_o_pedido_da_ia_leva_o_texto_base():
    questao = QuestaoDeProva(enunciado="Com base no texto 1, é correto:",
                             alternativas={"a": "x"}, resposta="a",
                             texto_base="Texto 1\nO farol da ilha.")

    por_extenso = gerador._questao_por_extenso(questao, inteira=True)

    assert por_extenso.startswith("TEXTO-BASE (do caderno da prova):\nTexto 1\nO farol")
    assert por_extenso.index("O farol") < por_extenso.index("Com base no texto 1")
    # O exemplo de estilo nao leva o texto: ele mostra o jeito da banca, e o
    # texto inteiro so encareceria o pedido.
    assert "TEXTO-BASE" not in gerador._questao_por_extenso(questao)


def test_a_questao_a_resolver_vai_sem_corte():
    """Na V/F longa, o corte de 600 caracteres levava as ultimas afirmativas, e a
    explicacao de 2013-q4 e 2019-q4 nao tinha o que explicar."""
    longo = "Analise as afirmativas. " + " ".join(f"( ) Afirmativa {n} bem comprida."
                                                  for n in range(1, 40))
    questao = QuestaoDeProva(enunciado=longo, alternativas={"a": "x"}, resposta="a")

    assert "Afirmativa 39 bem comprida." in gerador._questao_por_extenso(questao, inteira=True)
    assert "Afirmativa 39" not in gerador._questao_por_extenso(questao)


def test_sem_texto_base_o_pedido_fica_como_era():
    questao = QuestaoDeProva(enunciado="Pergunta?", alternativas={"a": "x"}, resposta="a")

    assert gerador._questao_por_extenso(questao) == "Pergunta?\na) x\nGABARITO OFICIAL: a"
    assert gerador._questao_por_extenso(questao, inteira=True) == (
        "Pergunta?\na) x\nGABARITO OFICIAL: a")


def test_a_tela_da_questao_mostra_o_texto_base(banco_temporario, com_quadro_do_edital):
    from fastapi.testclient import TestClient

    from radar import servico
    from radar.web.app import app

    from tests.test_home import _acervo

    _acervo()
    simulado = servico.criar_simulado(quantidade=3, materia="Direito Penal")
    with sessao() as s:
        for questao in s.query(QuestaoDeProva):
            questao.texto_base = "Texto 1\nO farol da ilha acende quando a tarde cai."

    texto = TestClient(app).get(f"/simulado/{simulado.id}").text

    assert "Texto-base (do caderno da prova)" in texto
    assert "O farol da ilha acende quando a tarde cai." in texto
    assert texto.index("O farol da ilha") < texto.index('class="enunciado"', texto.index("O farol"))
