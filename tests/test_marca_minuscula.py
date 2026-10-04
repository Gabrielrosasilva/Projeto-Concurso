"""A marca da alternativa em minusculas ("a. square texto").

Em alguns cadernos de 2023 e 2024 (Palhoca emergencial, Brusque educa) a
fonte das caixas sai como "square", e nao "SQUARE". O leitor so achava a
alternativa certa ("Check-square") e lia 14 de 39 questoes.
"""
from radar.questoes import dividir_em_questoes

CADERNO = """\
1. Assinale a alternativa que completa corretamente os espaços.
a. square a • À • a
b. square a • Há • a
c. square à • À • à
d. Check-square à • Há • a
e. square à • Há • à
2. Qual a função da linguagem que constitui o texto?
a. Check-square Função Referencial
b. square Função Poética
c. square Função Fática
d. square Função Conotativa
e. square Função Metalinguística
"""


def test_a_marca_minuscula_e_alternativa():
    questoes = {q.numero: q for q in dividir_em_questoes(CADERNO)}

    assert sorted(questoes) == [1, 2]
    assert questoes[1].resposta == "d" and questoes[2].resposta == "a"
    assert questoes[2].alternativas == {
        "a": "Função Referencial", "b": "Função Poética", "c": "Função Fática",
        "d": "Função Conotativa", "e": "Função Metalinguística"}
