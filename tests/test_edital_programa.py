"""O conteudo programatico do edital: o que cai dentro de cada materia.

A fixture e o texto REAL do ANEXO 1 do edital 001/SAP/2019, extraido no modo
`layout` - que e o modo que este leitor exige. Nenhum teste vai a internet.

O que estes testes protegem, mais do que a contagem: **o texto e o do edital**.
Nada e reescrito nem encurtado, porque o nome do assunto so serve se for o
mesmo que o edital usa - e dele que sai a lista fechada que a IA escolhe.
"""
from pathlib import Path

import pytest

from radar import edital_programa

PROGRAMA_2019 = (
    Path(__file__).parent / "fixtures" / "provas" / "edital_sap_2019_programa.txt"
).read_text(encoding="utf-8")


@pytest.fixture
def programa():
    return edital_programa.ler_programa(PROGRAMA_2019)


def test_le_as_onze_materias_do_programa(programa):
    """As mesmas onze do quadro de distribuicao de questoes."""
    assert len(programa) == 11


def test_o_nome_da_materia_sai_igual_ao_do_quadro(programa):
    """O anexo escreve "LEI DE EXECUÇÃO PENAL" e o quadro "Lei de Execução
    Penal". Os dois lados so se encontram porque passam pela mesma regra."""
    assert "Lei de Execução Penal" in programa
    assert "Direito Processual Penal" in programa
    assert "Língua Portuguesa" in programa


def test_cada_materia_tem_pelo_menos_um_assunto(programa):
    """Materia com lista vazia seria uma lista sem o que escolher - e o
    comando trataria isso como "pode inventar", que e o que a lista existe
    para impedir."""
    assert all(itens for itens in programa.values())


def test_o_assunto_sai_com_o_texto_do_edital(programa):
    """Copiado, nao resumido. E o nome que o edital usa que me deixa comparar
    o que caiu com o que vai cair."""
    assert "Regras mínimas da ONU para o tratamento de pessoas presas" in (
        programa["Direitos Humanos"]
    )
    assert "Ortografia oficial" in programa["Língua Portuguesa"]
    assert "Papel do agente penitenciário na ressocialização do preso" in (
        programa["Sociologia Aplicada"]
    )


def test_a_referencia_de_artigo_nao_vira_assunto(programa):
    """O edital escreve "Infração penal: elementos, espécies. (arts. 13 a 25)".
    A referencia diz onde ler, e nao do que a questao trata."""
    penal = programa["Direito Penal"]
    assert "Infração penal: elementos, espécies" in penal
    assert not any("art" in item.lower() and "13 a 25" in item for item in penal)


def test_a_lei_com_ponto_no_numero_nao_vira_tres_assuntos(programa):
    """"Lei n.º 7.210 de 11 de julho de 1984" tem tres pontos dentro, e nenhum
    deles fecha um assunto."""
    execucao = programa["Lei de Execução Penal"]
    assert len(execucao) == 1
    assert "7.210" in execucao[0]


def test_o_ponto_no_meio_da_frase_nao_corta_o_assunto(programa):
    """O edital digitou "Processos. dos crimes de responsabilidade dos
    funcionarios publicos" - o ponto ali e engano dele, e cortar criaria um
    assunto que comeca no meio."""
    assert "Processos dos crimes de responsabilidade dos funcionários públicos" in (
        programa["Direito Processual Penal"]
    )


def test_o_ponto_e_virgula_separa_a_lista_do_edital(programa):
    """Em Direito Constitucional o edital lista com ponto-e-virgula, e cada
    item dali e um assunto de verdade."""
    constitucional = programa["Direito Constitucional"]
    assert "direitos sociais" in constitucional
    assert "nacionalidade" in constitucional


def test_texto_sem_o_anexo_devolve_vazio():
    """Nunca chutar: edital sem programa nao vira lista inventada."""
    assert edital_programa.ler_programa("Edital de abertura. Sao 100 vagas.") == {}
    assert edital_programa.ler_programa("") == {}


def test_o_marco_precisa_estar_sozinho_na_linha():
    """O corpo do edital fala em "programa da prova escrita" no meio de
    paragrafo. Comecar por ali trazia o capitulo de prova de capacidade fisica
    inteiro para dentro da lista de assuntos."""
    texto = (
        "9.3 O candidato sera avaliado conforme o programa da prova escrita "
        "constante do Anexo 1.\nLINGUA PORTUGUESA\nOrtografia oficial.\n"
    )
    assert edital_programa.ler_programa(texto) == {}


def test_pdf_ilegivel_nao_quebra(tmp_path):
    """PDF ruim e rotina, e nao acidente: devolve {} em vez de excecao."""
    falso = tmp_path / "nao-e-pdf.pdf"
    falso.write_bytes(b"isto nao e um PDF")
    assert edital_programa.ler_programa_do_pdf(falso) == {}
