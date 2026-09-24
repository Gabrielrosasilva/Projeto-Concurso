"""O gabarito definitivo, e as questoes que a banca anulou.

As fixtures sao o texto REAL dos PDFs que a FEPESE publicou:

  * `gabarito_definitivo_sap_2019.txt` - o do meu concurso de 2019, com
    quatro anuladas e quatro letras trocadas em relacao ao caderno;
  * `gabarito_definitivo_sjc_2013.txt` - o de 2013, que traz DOIS cargos no
    mesmo PDF, e por isso e o teste que importa para a separacao.

O que estes testes protegem: o caderno da FEPESE carrega o gabarito
PROVISORIO dentro do proprio PDF, porque e publicado no dia seguinte a prova,
antes dos recursos. Sem o definitivo eu treinaria marcando como erro quatro
respostas certas minhas, e perseguindo cinco questoes que nao tem resposta.
"""
from dataclasses import dataclass
from pathlib import Path

import pytest

from radar import gabarito

FIXTURES = Path(__file__).parent / "fixtures" / "provas"
SAP_2019 = (FIXTURES / "gabarito_definitivo_sap_2019.txt").read_text(encoding="utf-8")
SJC_2013 = (FIXTURES / "gabarito_definitivo_sjc_2013.txt").read_text(encoding="utf-8")


@dataclass
class QuestaoFalsa:
    """O bastante do objeto que o leitor de caderno devolve."""

    numero: int
    resposta: str | None = None
    anulada: bool = False


# --- ler a grade ------------------------------------------------------------

def test_le_a_grade_de_cem_questoes():
    grade, = gabarito.ler_grades(SAP_2019)
    assert grade.total == 100


def test_o_x_da_banca_vira_anulada():
    """"x" na grade quer dizer questao anulada, e ela fica SEM resposta -
    guardar uma seria inventar."""
    grade, = gabarito.ler_grades(SAP_2019)

    assert grade.anuladas == {11, 22, 63, 100}
    assert not any(n in grade.respostas for n in grade.anuladas)


def test_a_letra_certa_vem_da_grade():
    grade, = gabarito.ler_grades(SAP_2019)

    assert grade.respostas[1] == "c"
    assert grade.respostas[66] == "b"
    assert grade.respostas[87] == "e"


def test_o_cargo_e_a_sigla_saem_do_cabecalho():
    grade, = gabarito.ler_grades(SAP_2019)

    assert grade.sigla == "AP"
    assert "Agente Penitenciário" in grade.cargo


def test_um_pdf_com_dois_cargos_vira_duas_grades():
    """O de 2013 tem "AP - Agente Penitenciario" e "AS - Agente de Seguranca
    Socioeducativo", cada um numerado de 1 a 70. Lendo tudo junto, as duas
    viravam uma grade de 73 questoes que nao era de cargo nenhum."""
    grades = gabarito.ler_grades(SJC_2013)

    assert len(grades) == 2
    assert [g.sigla for g in grades] == ["AP", "AS"]
    assert all(g.total == 70 for g in grades)


def test_os_dois_cargos_tem_gabaritos_diferentes():
    ap, as_ = gabarito.ler_grades(SJC_2013)
    assert ap.respostas[1] == "b"
    assert as_.respostas[1] == "c"


def test_texto_sem_grade_nenhuma_devolve_lista_vazia():
    assert gabarito.ler_grades("Comunicado de retificacao. Nada aqui.") == []
    assert gabarito.ler_grades("") == []


def test_linha_de_numeros_sem_letras_e_descartada():
    """Meia grade aplicada e pior do que nenhuma: ela trocaria a resposta de
    umas e deixaria as outras com a do provisorio, sem ninguem notar."""
    assert gabarito.ler_grades("1 2 3 4 5 6 7 8\nvalor da questao: 0,10") == []


def test_contagem_diferente_entre_numeros_e_letras_e_descartada():
    assert gabarito.ler_grades("1 2 3 4 5 6\na b c d e") == []


# --- e desta prova? ---------------------------------------------------------

def test_a_sigla_amarra_a_grade_ao_caderno():
    """O caderno de 2019 se chama AP.pdf, e a grade diz "AP". E o laco mais
    forte que existe quando o concurso tem varios cargos."""
    grade, = gabarito.ler_grades(SAP_2019)
    assert gabarito.e_deste_caderno(
        grade, "Agente Penitenciário - Feminino (AP)", "AP.pdf", 100
    )


def test_numero_de_questoes_diferente_recusa():
    """Aplicar a grade errada trocaria as 100 respostas de uma vez."""
    grade, = gabarito.ler_grades(SAP_2019)
    assert not gabarito.e_deste_caderno(grade, "Agente Penitenciário", "AP.pdf", 70)


def test_a_grade_do_outro_cargo_e_recusada():
    ap, as_ = gabarito.ler_grades(SJC_2013)
    assert gabarito.e_deste_caderno(ap, "Agente Penitenciário", "AP.pdf", 70)
    assert not gabarito.e_deste_caderno(as_, "Agente Penitenciário", "AP.pdf", 70)


def test_grade_vazia_nunca_e_de_caderno_nenhum():
    assert not gabarito.e_deste_caderno(gabarito.Grade(), "Qualquer", "X.pdf", 0)


# --- aplicar ----------------------------------------------------------------

def test_aplicar_troca_a_letra_errada_e_marca_a_anulada():
    """Os numeros sao os reais: o caderno de 2019 traz o provisorio, e o
    definitivo anulou a 11 e trocou a 66 de "c" para "b"."""
    grade, = gabarito.ler_grades(SAP_2019)
    questoes = [
        QuestaoFalsa(numero=11, resposta="b"),
        QuestaoFalsa(numero=66, resposta="c"),
        QuestaoFalsa(numero=1, resposta="c"),
    ]

    trocadas, anuladas = gabarito.aplicar(questoes, grade)

    assert (trocadas, anuladas) == (1, 1)
    assert questoes[0].anulada and questoes[0].resposta is None
    assert questoes[1].resposta == "b" and not questoes[1].anulada
    assert questoes[2].resposta == "c"      # ja estava certa


def test_uma_grade_depois_da_outra_desmarca_a_anulacao():
    """A retificacao substitui o definitivo, e nas duas pontas: se ela devolver
    a questao, ela deixa de estar anulada."""
    questao = QuestaoFalsa(numero=5, resposta=None, anulada=True)

    devolvida = gabarito.Grade(respostas={5: "d"})
    gabarito.aplicar([questao], devolvida)

    assert questao.resposta == "d"
    assert questao.anulada is False


def test_questao_fora_da_grade_fica_como_esta():
    """Nunca chutar: o que a grade nao menciona continua com o que o caderno
    dizia."""
    questao = QuestaoFalsa(numero=999, resposta="a")
    gabarito.aplicar([questao], gabarito.Grade(respostas={1: "b"}))
    assert questao.resposta == "a"


def test_pdf_ilegivel_nao_quebra(tmp_path):
    falso = tmp_path / "nao-e-pdf.pdf"
    falso.write_bytes(b"isto nao e um PDF")
    assert gabarito.ler_grades_do_pdf(falso) == ()
