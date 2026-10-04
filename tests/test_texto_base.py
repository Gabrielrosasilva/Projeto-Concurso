"""O texto-base compartilhado entre questoes ("Caso 3", "Para responder...").

No S7 de Sao Jose 2024 o enunciado do Caso 3 traz uma lista "1." a "8." antes
da questao 49. O leitor tomava o "1." pelo numero da questao, a 49 sumia, e a
alternativa "e" da questao de cima levava o Caso 3 inteiro junto.
"""
from radar.questoes import dividir_em_questoes

CADERNO = """\
46. Em relação ao Caso 2, o total inscrito em restos a pagar foi de:
a. SQUARE R$ 5.000.
b. SQUARE R$ 10.000.
c. Check-square R$ 25.000.
d. SQUARE R$ 35.000.
e. SQUARE R$ 40.000.
Caso 3
Para responder às questões 49 a 51, considere o seguinte Balanço Patrimonial.
No decorrer do mês de janeiro, ocorreram somente as seguintes operações:
1. Lançamento e recolhimento da receita com taxas, no valor de R$ 5.000.
2. Recebimento, em doação, de medicamentos, no valor de R$ 7.000.
3. Empenho, liquidação e pagamento da despesa com pessoal, de R$ 15.000.
49. Considerando o Caso 3, o valor do total do ativo do município foi de:
a. SQUARE R$ 750.000.
b. SQUARE R$ 758.000.
c. Check-square R$ 762.000.
d. SQUARE R$ 777.000.
e. SQUARE R$ 783.000.
50. Analise as afirmativas abaixo sobre o Caso 3.
1. A operação 2 gerou variação patrimonial aumentativa.
2. A operação 3 é despesa orçamentária.
Assinale a alternativa correta.
a. SQUARE É correta apenas a afirmativa 1.
b. Check-square É correta apenas a afirmativa 2.
c. SQUARE São corretas as afirmativas 1 e 2.
d. SQUARE Nenhuma é correta.
e. SQUARE Não se pode afirmar.
"""


def _por_numero():
    return {q.numero: q for q in dividir_em_questoes(CADERNO)}


def test_a_lista_do_texto_base_nao_e_o_numero_da_questao():
    questoes = _por_numero()

    assert sorted(questoes) == [46, 49, 50]
    assert questoes[49].enunciado.startswith("Considerando o Caso 3")
    assert questoes[49].resposta == "c"


def test_a_ultima_alternativa_para_no_texto_base():
    assert _por_numero()[46].alternativas["e"] == "R$ 40.000."


def test_a_lista_de_dentro_do_enunciado_continua_no_enunciado():
    """A lista que vem DEPOIS do numero e do enunciado, como sempre foi."""
    questao = _por_numero()[50]

    assert "1. A operação 2" in questao.enunciado
    assert "2. A operação 3" in questao.enunciado
    assert questao.resposta == "b"
