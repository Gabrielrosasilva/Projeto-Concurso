"""O caderno de multipla escolha do Cebraspe (decisao 169).

As fixtures sao o texto real (como o pypdf o le) de dois cadernos do Cebraspe,
que autoriza "a reproducao deste material apenas para fins didaticos, desde
que citada a fonte":
  - Policia Civil de Pernambuco 2023 (PC_PE_23), prova P1 com justificativas,
    questoes 1 a 5, e o gabarito definitivo dela;
    https://cdn.cebraspe.org.br/concursos/PC_PE_23/arquivos/MATRIZ_954PC_PECB1_00_COM_JUSTIFICATIVA.PDF
  - SERES/PE 2021, Policial Penal, questoes 50 a 53 com justificativas.
    https://cdn.cebraspe.org.br/concursos/SERES_PE_21/arquivos/671_SERESPE_NS_COM_JUSTIFICATIVA.PDF
"""
from pathlib import Path

import pytest

from radar import questoes_cebraspe

PASTA = Path(__file__).parent / "fixtures" / "cebraspe"


@pytest.fixture
def gabarito():
    return questoes_cebraspe.ler_gabarito(
        (PASTA / "pc_pe_23_p1_gabarito.txt").read_text(encoding="utf-8"))


@pytest.fixture
def pe(gabarito):
    texto = (PASTA / "pc_pe_23_p1.txt").read_text(encoding="utf-8")
    return questoes_cebraspe.dividir_em_questoes(texto, gabarito, ler=["1-20"])


def test_o_gabarito_le_os_numeros_colados_e_a_anulada(gabarito):
    """"1 23456789 1 0 ..." e "E CDXACBDDEE...": 20 letras, X na anulada."""
    assert len(gabarito) == 20
    assert [gabarito[n] for n in (1, 2, 3, 5)] == ["e", "c", "d", "a"]
    assert gabarito[4] is None and gabarito[14] is None


def test_le_as_questoes_com_a_resposta_e_a_anulada(pe):
    assert [(q.numero, q.resposta, q.anulada) for q in pe] == [
        (1, "e", False), (2, "c", False), (3, "d", False), (4, None, True), (5, "a", False)]
    for questao in pe:
        assert sorted(questao.alternativas) == list("abcde"), questao.numero


def test_a_justificativa_e_o_cabecalho_nao_entram_na_questao(pe):
    for questao in pe:
        textos = [questao.enunciado, *questao.alternativas.values()]
        assert not any("||" in t or "CORRETA" in t or "CEBRASPE" in t for t in textos)
    assert pe[0].alternativas["e"].endswith("destinadas à preservação de seus bens.")


def test_a_resposta_pela_justificativa_quando_o_gabarito_e_de_outra_versao():
    texto = (PASTA / "seres_pe_21_50a53.txt").read_text(encoding="utf-8")
    lidas = questoes_cebraspe.dividir_em_questoes(
        texto, {}, ler=["21-60"], resposta_das_justificativas=True, anuladas=[41, 52])
    assert [q.numero for q in lidas] == [50, 51, 52, 53]
    assert lidas[0].resposta == "d" and lidas[3].resposta == "c"
    # A anulada do documento de alteracoes fica sem resposta, mesmo marcada.
    assert lidas[2].anulada and lidas[2].resposta is None
    assert "ERRADO" not in lidas[0].alternativas["e"]


def test_o_enunciado_que_comeca_com_a_nao_vira_alternativa():
    texto = ("Questão 21\n"
             "A partir das ideias do texto, é correto inferir\n"
             "que\n"
             "A primeira opção.\nB segunda opção.\nC terceira opção.\n"
             "D quarta opção.\nE quinta opção.\n")
    (questao,) = questoes_cebraspe.dividir_em_questoes(texto, {21: "b"})
    assert questao.enunciado.startswith("A partir das ideias")
    assert questao.alternativas["a"] == "primeira opção." and questao.resposta == "b"


def test_so_le_as_questoes_pedidas_e_corta_o_rodape_colado():
    texto = ("Questão 1\nDe Português?\nA a\nB b\nC c\nD d\nE e\n"
             "Questão 2\nDe Direito Penal?\nA a\nB b\nC c\nD d\n"
             "E e 662001_01N27724 CEBRASPE – PC/RJ – Edital: 2021\n")
    (questao,) = questoes_cebraspe.dividir_em_questoes(texto, {}, ler=["2"])
    assert questao.numero == 2 and questao.alternativas["e"] == "e"


def test_quatro_alternativas_quando_a_prova_e_de_a_a_d():
    texto = "Questão 31\nGuarda Municipal?\nA a\nB b\nC c\nD d\n"
    (questao,) = questoes_cebraspe.dividir_em_questoes(texto, {31: "c"}, letras="ABCD")
    assert sorted(questao.alternativas) == list("abcd") and questao.resposta == "c"


def test_o_texto_de_apoio_vira_o_texto_base_de_quem_o_cita():
    texto = ("Situação hipotética 1A3-I\n"
             "João foi preso em flagrante.\n"
             "Questão 7\nNa situação hipotética 1A3-I, assinale a correta.\n"
             "A a\nB b\nC c\nD d\nE e\n"
             "Questão 8\nSem texto?\nA a\nB b\nC c\nD d\nE e\n")
    sete, oito = questoes_cebraspe.dividir_em_questoes(texto, {})
    assert sete.texto_base == "João foi preso em flagrante."
    assert oito.texto_base is None
    # O texto de apoio nao fica colado na ultima alternativa de antes.
    assert sete.alternativas["e"] == "e"


# --- o download que confere o PDF inteiro ------------------------------------

def test_o_pdf_cortado_e_baixado_de_novo(banco_temporario, monkeypatch):
    """O CDN do Cebraspe ja entregou um caderno pela metade com status 200."""
    from radar import provas, servico

    respostas = [b"%PDF-1.4 cortado", b"%PDF-1.4 inteiro\n%%EOF"]

    class BuscadorDoCdn:
        def get(self, url):
            class Resposta:
                text = ""
                content = respostas.pop(0) if respostas else b"%PDF-1.4 inteiro\n%%EOF"
            return Resposta()

    monkeypatch.setattr(servico.provas, "Buscador", BuscadorDoCdn)
    monkeypatch.setattr(servico.provas, "carregar_provas_de_outras_bancas", lambda: [{
        "banca": "Cebraspe", "ano": 2024, "orgao": "Polícia Civil de Pernambuco",
        "cargo": "Agente de Polícia",
        "caderno": "https://cdn.cebraspe.org.br/concursos/PC_PE_23/arquivos/P1.PDF"}])

    assert servico.montar_acervo_de_outras_bancas().provas == 1
    (registro,) = provas.carregar_manifesto()
    from radar import config
    assert (config.diretorio_dados() / registro["caminho"]).read_bytes().endswith(b"%%EOF")


def test_a_ultima_fileira_com_o_enchimento_colado():
    """A Guarda de Sao Cristovao 2023: "91 92 ... 100 0000000000" e
    "D BADCCACCD 0000000000"."""
    texto = ("71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90\n"
             "C ADDDBCBDBDABDCDABDA\n"
             "91 92 93 94 95 96 97 98 99 100 0000000000\n"
             "D BADCCACCD 0000000000\n")
    gabarito = questoes_cebraspe.ler_gabarito(texto)
    assert gabarito[90] == "a" and gabarito[91] == "d" and gabarito[100] == "d"
    assert 101 not in gabarito
