"""Caderno da IESES: quatro alternativas, gabarito a parte, materia do edital.

As fixtures sao o texto real do concurso de Biguacu 2024: o caderno do cargo
1016 (Assistente Social), o gabarito dele e os anexos II e IV do edital.
"""
from pathlib import Path

import pytest

from radar import edital_ieses, questoes_ieses

PASTA = Path(__file__).parent / "fixtures" / "ieses"


@pytest.fixture
def caderno():
    return (PASTA / "caderno.txt").read_text(encoding="utf-8")


@pytest.fixture
def edital():
    return (PASTA / "edital_trechos.txt").read_text(encoding="utf-8")


@pytest.fixture
def gabarito():
    from radar.questoes_ieses import PADRAO_RESPOSTA

    texto = (PASTA / "gabarito.txt").read_text(encoding="utf-8")
    return {int(n): l.lower() for n, l in PADRAO_RESPOSTA.findall(texto)}


# --- o gabarito, que aqui e um arquivo a parte ------------------------------

def test_le_o_gabarito_inteiro(gabarito):
    assert len(gabarito) == 30


def test_a_letra_vem_em_minuscula(gabarito):
    """No PDF esta "1 A"; no banco tudo e minusculo."""
    assert gabarito[1] == "a"


def test_le_com_e_sem_espaco_entre_numero_e_letra(gabarito):
    """O PDF alterna "1 A" e "2B", sem criterio."""
    assert gabarito[2] == "b" and gabarito[5] == "a"


# --- o cargo, que liga o caderno ao edital ----------------------------------

def test_acha_o_codigo_e_o_cargo(caderno):
    assert questoes_ieses.codigo_e_cargo(caderno) == ("1016", "Assistente Social")


def test_cargo_com_dois_codigos_vale_o_primeiro():
    """Quando dois cargos dividem o caderno vem "Cargo: 1020/1033 - Auxiliar de
    Ensino". Os dois estao no mesmo nivel e fazem a mesma prova."""
    codigo, cargo = questoes_ieses.codigo_e_cargo(
        "Cargo: 1020/1033 - Auxiliar de Ensino (30h) / (40h)"
    )

    assert codigo == "1020"
    assert cargo.startswith("Auxiliar de Ensino")


def test_caderno_sem_cabecalho_de_cargo():
    assert questoes_ieses.codigo_e_cargo("qualquer texto") == (None, None)


# --- as questoes ------------------------------------------------------------

def test_le_o_caderno_inteiro(caderno):
    assert len(questoes_ieses.dividir_em_questoes(caderno)) == 30


def test_cada_questao_tem_quatro_alternativas(caderno):
    """A IESES usa a) ate d). A FEPESE usa cinco."""
    for questao in questoes_ieses.dividir_em_questoes(caderno):
        assert len(questao.alternativas) == 4, f"questao {questao.numero}"


def test_as_alternativas_sao_a_ate_d(caderno):
    primeira = questoes_ieses.dividir_em_questoes(caderno)[0]

    assert sorted(primeira.alternativas) == ["a", "b", "c", "d"]


def test_o_gabarito_entra_em_cada_questao(caderno, gabarito):
    lidas = questoes_ieses.dividir_em_questoes(caderno, gabarito=gabarito)

    assert all(q.resposta for q in lidas)
    assert lidas[0].resposta == gabarito[1]


def test_sem_gabarito_a_questao_fica_sem_resposta(caderno):
    """Nao inventa: sem o arquivo de gabarito, nao ha como saber a correta."""
    assert all(q.resposta is None for q in questoes_ieses.dividir_em_questoes(caderno))


def test_enunciado_com_lista_numerada_nao_quebra_a_questao(caderno):
    """A questao 8 tem "I.", "II.", "III." dentro do enunciado."""
    oitava = next(q for q in questoes_ieses.dividir_em_questoes(caderno)
                  if q.numero == 8)

    assert len(oitava.alternativas) == 4


# --- a materia, que vem do edital -------------------------------------------

def test_o_anexo_ii_liga_cargo_a_nivel(edital):
    assert edital_ieses.niveis_por_codigo(edital)["1016"] == "SUPERIOR"


def test_o_anexo_iv_diz_de_que_o_nivel_e_feito(edital):
    composicao = edital_ieses.composicao_por_nivel(edital)["SUPERIOR"]

    assert composicao[0] == ("Língua Portuguesa", 8)
    assert ("Informática", 3) in composicao


def test_as_materias_caem_na_ordem_do_edital(edital):
    """E so a ordem que permite dizer que a questao 13 e de Informatica: as 8
    de portugues e as 4 de matematica vieram antes."""
    materias = edital_ieses.materias_do_cargo(edital, "1016", total=30)

    assert materias[1] == "Língua Portuguesa"
    assert materias[8] == "Língua Portuguesa"
    assert materias[9] == "Matemática e Raciocínio Lógico"
    assert materias[13] == "Informática"


def test_o_que_passa_das_gerais_e_especificos(edital):
    """O edital escreve o numero de especificos de tres jeitos diferentes no
    mesmo arquivo. A ordem, essa sim, e sempre a mesma: gerais primeiro."""
    materias = edital_ieses.materias_do_cargo(edital, "1016", total=30)

    assert materias[21] == "Conhecimentos Específicos"
    assert materias[30] == "Conhecimentos Específicos"


def test_sem_saber_o_total_nao_inventa_especificos(edital):
    materias = edital_ieses.materias_do_cargo(edital, "1016")

    assert 21 not in materias


def test_cargo_fora_do_edital_fica_sem_materia(edital):
    """O cargo 1260 do concurso real nao esta no Anexo II nem na retificacao.
    Melhor sem materia que com materia chutada: o simulado filtra por ela."""
    assert edital_ieses.materias_do_cargo(edital, "9999", total=30) == {}


def test_o_nome_da_materia_nao_sai_gritando(edital):
    """O edital escreve tudo em caixa alta, e title() sozinho devolveria
    "Matemática E Raciocínio Lógico"."""
    composicao = edital_ieses.composicao_por_nivel(edital)["SUPERIOR"]
    nomes = [nome for nome, _ in composicao]

    assert "Matemática e Raciocínio Lógico" in nomes


def test_os_niveis_do_fundamental_se_juntam(edital):
    """O Anexo II fala em "FUNDAMENTAL ANOS INICIAIS" e o IV em "COMPLETO" e
    "INCOMPLETO". Sao o mesmo nivel para efeito de prova."""
    assert "FUNDAMENTAL" in edital_ieses.composicao_por_nivel(edital)


# --- tudo junto -------------------------------------------------------------

def test_caderno_com_materia_e_gabarito(caderno, edital, gabarito):
    lidas = questoes_ieses.dividir_em_questoes(caderno, gabarito=gabarito)
    materias = edital_ieses.materias_do_cargo(
        edital, "1016", total=max(q.numero for q in lidas)
    )
    for questao in lidas:
        questao.materia = materias.get(questao.numero)

    assert len(lidas) == 30
    assert all(q.resposta and q.materia for q in lidas)
