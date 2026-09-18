"""O que o edital exige de quem se inscreve.

Os textos vem de editais reais do acervo, recortados. A regra que vale para o
arquivo inteiro: cada achado guarda o trecho que o embasa, porque o veredito
sozinho nao da para conferir.
"""
import pytest

from radar import elegibilidade

# Um edital precisa ter tamanho para ser considerado legivel.
ENCHIMENTO = "Texto do edital. " * 200


def _edital(*trechos: str) -> str:
    return ENCHIMENTO + " ".join(trechos) + ENCHIMENTO


# --- escolaridade -----------------------------------------------------------

def test_acha_vaga_de_nivel_superior():
    achado = elegibilidade.ler(_edital("Habilitação de nível superior em Serviço Social."))

    assert achado.tem_superior


def test_acha_os_tres_niveis():
    achado = elegibilidade.ler(_edital(
        "nível superior completo.", "ensino médio completo.",
        "ensino fundamental completo."
    ))

    assert achado.niveis == ["superior", "medio", "fundamental"]


def test_edital_so_de_nivel_medio_nao_tem_superior():
    achado = elegibilidade.ler(_edital("Certificado de ensino médio."))

    assert achado.niveis == ["medio"]
    assert not achado.tem_superior


def test_graduacao_e_licenciatura_contam_como_superior():
    for jeito in ("Graduação em Pedagogia", "Licenciatura plena", "Bacharelado em Direito"):
        assert elegibilidade.ler(_edital(jeito)).tem_superior, jeito


# --- CNH --------------------------------------------------------------------

def test_acha_a_categoria_da_cnh():
    """A categoria e o que muda o custo: B quase todo mundo tem, D exige curso
    e tempo de habilitacao."""
    achado = elegibilidade.ler(_edital(
        "Possuir Carteira Nacional de Habilitação - CNH - Categoria D."
    ))

    assert achado.cnh == "D"


def test_categoria_dupla_sai_legivel():
    """No PDF vem "Categoria A ou B", com o espacamento que o extrator der."""
    achado = elegibilidade.ler(_edital(
        "Carteira Nacional de Habilitação - CNH - Categoria A ou B."
    ))

    assert achado.cnh == "A OU B"


def test_cnh_sem_categoria_dita_fica_como_sim():
    achado = elegibilidade.ler(_edital("Possuir Carteira Nacional de Habilitação."))

    assert achado.cnh == "sim"


def test_edital_sem_cnh():
    assert elegibilidade.ler(_edital("Nada sobre dirigir.")).cnh is None


# --- teste fisico -----------------------------------------------------------

def test_acha_o_teste_de_aptidao_fisica():
    """E a barreira que mais elimina em concurso policial."""
    achado = elegibilidade.ler(_edital(
        "2. Teste de Aptidão Física de caráter eliminatório."
    ))

    assert achado.taf


def test_aptidao_fisica_e_mental_da_junta_medica_nao_e_taf():
    """Quase todo edital diz "aptidao fisica e mental verificada por junta
    medica" - isso e exame admissional, e nao teste de corrida."""
    achado = elegibilidade.ler(_edital(
        "A aptidão física e mental, que será verificada por junta médica oficial."
    ))

    assert not achado.taf


# --- idade ------------------------------------------------------------------

def test_acha_idade_minima_e_maxima():
    achado = elegibilidade.ler(_edital(
        "Ter idade mínima de 18 anos e idade máxima de 75 anos."
    ))

    assert achado.idade_minima == 18
    assert achado.idade_maxima == 75


def test_idade_maxima_por_outra_redacao():
    achado = elegibilidade.ler(_edital("Não ter completado 30 anos até a posse."))

    assert achado.idade_maxima == 30


# --- o trecho que embasa ----------------------------------------------------

def test_cada_achado_guarda_o_trecho():
    """O veredito sozinho nao vale: eu preciso poder conferir de onde ele veio,
    principalmente quando parece errado - "idade maxima 75" e aposentadoria
    compulsoria, e nao barreira de carreira."""
    achado = elegibilidade.ler(_edital(
        "Ter idade máxima de 75 anos (Lei Complementar nº 152/2015)."
    ))

    assert "152/2015" in achado.trechos["idade_maxima"]


def test_o_trecho_vem_do_texto_original_com_acento():
    achado = elegibilidade.ler(_edital("Habilitação de nível superior."))

    assert "nível superior" in achado.trechos["superior"]


# --- edital que nao da para ler ---------------------------------------------

def test_edital_digitalizado_como_imagem_e_apontado():
    """Medido no acervo: um dos 32 editais tem 2,5 MB e 34 caracteres de texto.
    Dizer que nao exige nada seria mentira."""
    achado = elegibilidade.ler("EDITAL 001/2024")

    assert not achado.legivel
    assert "imagem" in elegibilidade.resumir(achado)


def test_edital_vazio_nao_quebra():
    assert not elegibilidade.ler("").legivel
    assert not elegibilidade.ler(None).legivel


# --- o resumo ---------------------------------------------------------------

def test_o_resumo_junta_tudo_numa_linha():
    achado = elegibilidade.ler(_edital(
        "nível superior completo.", "ensino médio.",
        "Carteira Nacional de Habilitação - CNH - Categoria D.",
        "Teste de Aptidão Física eliminatório.",
    ))
    resumo = elegibilidade.resumir(achado)

    assert "superior" in resumo and "categoria D" in resumo and "teste fisico" in resumo


def test_edital_que_nao_diz_nada_admite_isso():
    assert "Nada identificado" in elegibilidade.resumir(elegibilidade.ler(ENCHIMENTO))
