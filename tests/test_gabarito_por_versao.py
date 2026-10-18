"""O gabarito de outra banca com mais de uma versao do caderno (decisao 172).

O texto dos testes e INVENTADO, no formato de cada banca: os termos da FGV
proibem reproduzir o material, e o repositorio e publico.
"""
import pytest

from radar import gabarito_por_versao as g

# A Selecon: "PROVA A" e "PROVA B", pares "01: D", X na anulada.
SELECON = """GABARITO OFICIAL
401 - SOLDADO PM
PROVA A
01: C 02: D 03: X 04: B
PROVA B
01: D 02: B 03: A 04: X
X - Questão Anulada.
"""

# A Access: "PROVA TIPO 1" e um par por linha, "anulada", "*" e "(alterado)".
ACCESS = """GABARITOS DEFINITIVOS DA PROVA APLICADA NO DIA 16/4/23
* = Questão anulada
PROVA TIPO 1 LÍNGUA
PORTUGUESA
1 – B
2 – C
3 – E (alterado)
4 – anulada
PROVA TIPO 2 LÍNGUA
1 – C
2 – *
3 – A
4 – D
"""

# A FGV: o nome do tipo e as fileiras, numeros numa linha e letras na outra.
FGV = """GABARITOS DEFINITIVOS DAS PROVAS APLICADAS EM 15/09/2024
Agente Penitenciário - TIPO 1
1 2 3 4 5
D D B A B
Agente Penitenciário - TIPO 2
1 2 3 4 5
E D D B A
"""


def test_a_selecon_le_o_bloco_da_prova_pedida():
    a = g.bloco_da_versao([SELECON], "PROVA A")
    assert a == {1: "c", 2: "d", 3: None, 4: "b"}
    assert g.bloco_da_versao([SELECON], "PROVA B")[4] is None


def test_a_access_marca_a_anulada_e_ignora_o_alterado():
    um = g.bloco_da_versao([ACCESS], "TIPO 1")
    assert um == {1: "b", 2: "c", 3: "e", 4: None}
    # A anulada de outro tipo e outra questao.
    assert g.bloco_da_versao([ACCESS], "TIPO 2") == {1: "c", 2: None, 3: "a", 4: "d"}


def test_a_fgv_le_as_fileiras():
    assert g.bloco_da_versao([FGV], "TIPO 2") == {1: "e", 2: "d", 3: "d", 4: "b", 5: "a"}


def test_o_nome_no_fim_da_pagina_nao_vale_pelo_pedaco():
    """A Idecan no modo comum: os blocos sem nome e, no fim, os nomes e as
    anuladas soltas. So o modo layout, com o nome no lugar, da o bloco."""
    comum = ("01: E 02: D 03: B\n01: A 02: E 03: C\n"
             "PROVA TIPO B\n02100 – ESCRIVÃO\nPROVA TIPO A\n02: X\n02: X\n")
    layout = ("02100 – ESCRIVÃO DE POLÍCIA CIVIL\nPROVA TIPO A\n01: E 02: X 03: B\n"
              "PROVA TIPO B\n01: A 02: X 03: C\n")
    assert g.bloco_da_versao([comum, layout], "TIPO A") == {1: "e", 2: None, 3: "b"}


def test_recusa_a_versao_que_nao_existe_e_os_modos_que_discordam():
    with pytest.raises(ValueError):
        g.bloco_da_versao([SELECON], "PROVA C")
    outro = SELECON.replace("01: C", "01: A")
    with pytest.raises(ValueError):
        g.bloco_da_versao([SELECON, outro], "PROVA A")


def test_so_o_bloco_do_cargo_quando_o_gabarito_junta_varios():
    texto = ("501 - ANALISTA TÉCNICO EM DIREITO\nPROVA A\n01: D 02: A\nPROVA B\n01: A 02: D\n"
             "502 - ANALISTA TÉCNICO EM ADMINISTRAÇÃO\nPROVA A\n01: B 02: B\n")
    assert g.bloco_da_versao([texto], "PROVA A", "ANALISTA TÉCNICO EM DIREITO") == {1: "d", 2: "a"}
    assert g.bloco_da_versao([texto], "PROVA A", "EM ADMINISTRAÇÃO") == {1: "b", 2: "b"}


def test_o_codigo_do_cargo_nao_vira_resposta():
    """ "02100 – ESCRIVÃO": o 100 nao e a questao 100 com letra E."""
    texto = "PROVA TIPO A\n02100 – ESCRIVÃO DE POLÍCIA CIVIL\n01: C 02: D\n"
    assert g.bloco_da_versao([texto], "TIPO A") == {1: "c", 2: "d"}


def test_a_versao_do_caderno_e_a_marca_que_ele_mais_cita():
    selecon = ("marque a letra que corresponde à prova (A ou B)\n"
               "A\nPROVA\n1. Enunciado\nA\nPROVA\n2. Enunciado\n")
    assert g.versao_do_caderno(selecon) == "PROVA A"
    assert g.versao_do_caderno("Caderno de prova tipo 1 - branco | Página - 1") == "TIPO 1"
    assert g.versao_do_caderno("02100 – ESCRIVÃO DE POLÍCIA CIVIL – TIPO A") == "TIPO A"
    # Empate (a capa que cita as duas) nao decide nada.
    assert g.versao_do_caderno("A\nPROVA\nB\nPROVA") is None
    assert g.versao_do_caderno("Identifique o TIPO de caderno de prova") is None
