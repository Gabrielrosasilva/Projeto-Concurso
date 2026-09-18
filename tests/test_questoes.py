"""Separar o caderno de prova em questoes.

A fixture e o texto REAL extraido do caderno de Guarda Patrimonial do processo
seletivo de 2024 de Palhoca (FEPESE). Guardamos o texto, e nao o PDF: pesa 25
KB em vez de 1,5 MB, e e exatamente o que o extrator entrega.

A prova tem 40 questoes, divididas pela propria banca em Lingua Portuguesa
(10), Conhecimentos Gerais (10) e Conhecimentos Especificos (20).
"""
import re
from pathlib import Path

import pytest

from radar import questoes

FIXTURE = (
    Path(__file__).parent / "fixtures" / "provas"
    / "guarda_patrimonial_palhoca_2024.txt"
)


@pytest.fixture(scope="module")
def texto() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def prova(texto) -> list[questoes.Questao]:
    return questoes.dividir_em_questoes(texto)


# --- a prova inteira --------------------------------------------------------

def test_le_as_quarenta_questoes(prova):
    assert len(prova) == 40
    assert [q.numero for q in prova] == list(range(1, 41))


def test_toda_questao_tem_cinco_alternativas(prova):
    assert all(len(q.alternativas) == 5 for q in prova)
    assert all(set(q.alternativas) == set("abcde") for q in prova)


def test_toda_questao_tem_gabarito(prova):
    """O caderno da FEPESE marca a correta no proprio texto: prova e gabarito
    no mesmo arquivo."""
    assert all(q.resposta in "abcde" for q in prova)


def test_a_materia_vem_da_banca(prova):
    from collections import Counter

    contagem = Counter(q.materia for q in prova)
    assert contagem == {
        "Língua Portuguesa": 10,
        "Conhecimentos Gerais": 10,
        "Conhecimentos Específicos": 20,
    }


def test_a_materia_segue_a_faixa_de_numeros(prova):
    por_numero = {q.numero: q.materia for q in prova}
    assert por_numero[1] == "Língua Portuguesa"
    assert por_numero[10] == "Língua Portuguesa"
    assert por_numero[11] == "Conhecimentos Gerais"
    assert por_numero[20] == "Conhecimentos Gerais"
    assert por_numero[21] == "Conhecimentos Específicos"
    assert por_numero[40] == "Conhecimentos Específicos"


# --- os dois casos que quebraram a primeira versao --------------------------

def test_ordem_embaralhada_pelas_duas_colunas(texto, prova):
    """O caderno e impresso em duas colunas, e o extrator leu 1..15, depois 21
    e 22, e so entao 16..20. A primeira versao exigia ordem e parou na 20."""
    marcas = [int(m.group(1)) for m in questoes.PADRAO_QUESTAO.finditer(texto)]
    posicao_21 = marcas.index(21)
    posicao_16 = marcas.index(16)
    assert posicao_21 < posicao_16, "a fixture precisa ter a ordem embaralhada"

    assert {16, 17, 18, 19, 20, 21, 22} <= {q.numero for q in prova}


def test_lista_numerada_dentro_do_enunciado(prova):
    """As questoes 5 e 9 tem lista numerada no enunciado ("1. ... 2. ...").
    Partir dos numeros quebrava a questao no meio e perdia as alternativas."""
    por_numero = {q.numero: q for q in prova}
    for numero in (5, 9):
        assert numero in por_numero
        assert len(por_numero[numero].alternativas) == 5


# --- conteudo de uma questao ------------------------------------------------

def test_enunciado_sem_o_numero_na_frente(prova):
    questao = next(q for q in prova if q.numero == 12)
    assert not questao.enunciado.startswith("12")
    assert "capital catarinense" in questao.enunciado


def test_gabarito_certo_numa_questao_conferivel(prova):
    """A 12 pergunta a capital de SC; a correta e Florianopolis."""
    questao = next(q for q in prova if q.numero == 12)
    assert questao.alternativas[questao.resposta] == "Florianópolis"


def test_palavra_quebrada_por_hifen_e_remontada(prova):
    """O caderno quebra palavra no fim da linha ("muni-\\ncipio"). Sem juntar,
    o enunciado fica com palavra partida e o hash nunca bate."""
    questao = next(q for q in prova if q.numero == 11)
    assert "município" in questao.enunciado
    assert "muni- cípio" not in questao.enunciado


# --- secoes -----------------------------------------------------------------

def test_a_linha_da_capa_nao_vira_materia(texto):
    """A capa diz "8 as 11h 40 questoes", que nao e nome de materia."""
    nomes = [nome for _, nome, _ in questoes.achar_secoes(texto)]
    assert not any(any(c.isdigit() for c in nome) for nome in nomes)


def test_cabecalho_quebrado_em_duas_linhas_e_remontado():
    """Visto em prova real: "Conhecimentos" numa linha e "Gerais sobre
    Educacao 10 questoes" na seguinte. Sem juntar, a materia virava
    "Gerais sobre Educacao", que nao e nome de nada."""
    texto = "Conhecimentos\nGerais sobre Educação 10 questões\n"
    nomes = [nome for _, nome, _ in questoes.achar_secoes(texto)]
    assert nomes == ["Conhecimentos Gerais sobre Educação"]


def test_cabecalho_de_pagina_nao_entra_no_nome():
    texto = "Município de Palhoça • Edital 012\nLíngua Portuguesa 10 questões\n"
    nomes = [nome for _, nome, _ in questoes.achar_secoes(texto)]
    assert nomes == ["Língua Portuguesa"]


def test_erro_de_digitacao_do_caderno_e_corrigido():
    """Visto em prova real: "Conhecimento Gerais", no singular."""
    texto = "Conhecimento Gerais 10 questões\n"
    nomes = [nome for _, nome, _ in questoes.achar_secoes(texto)]
    assert nomes == ["Conhecimentos Gerais"]


# --- questao repetida entre provas ------------------------------------------

def test_mesma_questao_formatada_diferente_tem_a_mesma_impressao():
    """Banca reaproveita questao, e achar isso e o padrao mais forte que
    existe. O mesmo enunciado sai formatado de um jeito em cada caderno."""
    uma = questoes.Questao(numero=1, enunciado="Qual é a capital de Santa Catarina?")
    outra = questoes.Questao(numero=7, enunciado="Qual e  a CAPITAL de santa catarina ?")

    assert uma.impressao == outra.impressao


def test_enunciados_diferentes_tem_impressoes_diferentes():
    uma = questoes.Questao(numero=1, enunciado="Qual é a capital de Santa Catarina?")
    outra = questoes.Questao(numero=1, enunciado="Qual é a capital do Parana?")

    assert uma.impressao != outra.impressao


# --- quando o PDF nao colabora ----------------------------------------------

def test_texto_sem_questao_devolve_lista_vazia():
    assert questoes.dividir_em_questoes("Apenas um texto qualquer.") == []


def test_pdf_ilegivel_nao_derruba_a_execucao(tmp_path):
    ruim = tmp_path / "quebrado.pdf"
    ruim.write_bytes(b"isto nao e um PDF")

    assert questoes.ler_prova(ruim) == []


# --- guardar no banco e relatar ---------------------------------------------

def _prova_falsa(tmp_path, nome="p.pdf"):
    """Registra uma prova no manifesto, com um PDF de mentira no lugar."""
    from radar import provas

    arquivo = tmp_path / nome
    arquivo.write_bytes(b"%PDF-1.4 fingindo")
    provas.gravar_manifesto(provas.carregar_manifesto() + [{
        "tipo": "prova", "url": f"https://x.test/{nome}", "arquivo": nome,
        "caminho": nome, "banca": "FEPESE", "ano": 2024,
        "municipio": "Palhoca", "cargo": "Guarda Patrimonial",
        "concurso_url": "https://fepese.org.br/concurso/x",
    }])
    return arquivo


def test_grava_as_questoes_no_banco(banco_temporario, tmp_path, monkeypatch):
    from radar import servico

    _prova_falsa(tmp_path, "uma.pdf")
    monkeypatch.setattr(
        questoes, "extrair_texto", lambda caminho: FIXTURE.read_text(encoding="utf-8")
    )

    resultado = servico.extrair_questoes(limite=5)

    assert resultado.provas == 1
    assert resultado.questoes == 40
    assert servico.contar_questoes() == 40


def test_nao_le_a_mesma_prova_duas_vezes(banco_temporario, tmp_path, monkeypatch):
    from radar import servico

    _prova_falsa(tmp_path, "uma.pdf")
    monkeypatch.setattr(
        questoes, "extrair_texto", lambda caminho: FIXTURE.read_text(encoding="utf-8")
    )

    servico.extrair_questoes(limite=5)
    segunda = servico.extrair_questoes(limite=5)

    assert segunda.provas == 0
    assert servico.contar_questoes() == 40


def test_incidencia_por_materia(banco_temporario, tmp_path, monkeypatch):
    from radar import servico

    _prova_falsa(tmp_path, "uma.pdf")
    monkeypatch.setattr(
        questoes, "extrair_texto", lambda caminho: FIXTURE.read_text(encoding="utf-8")
    )
    servico.extrair_questoes(limite=5)

    linhas = dict(servico.incidencia_por_materia())
    assert linhas["Conhecimentos Específicos"] == 20
    assert linhas["Língua Portuguesa"] == 10


def test_incidencia_filtra_por_cargo(banco_temporario, tmp_path, monkeypatch):
    from radar import servico

    _prova_falsa(tmp_path, "uma.pdf")
    monkeypatch.setattr(
        questoes, "extrair_texto", lambda caminho: FIXTURE.read_text(encoding="utf-8")
    )
    servico.extrair_questoes(limite=5)

    assert servico.incidencia_por_materia(cargo="Guarda")
    assert servico.incidencia_por_materia(cargo="Nao existe") == []


def test_questao_repetida_entre_provas_e_encontrada(banco_temporario, tmp_path, monkeypatch):
    """Duas provas diferentes com o mesmo caderno: 40 questoes repetidas."""
    from radar import servico

    _prova_falsa(tmp_path, "uma.pdf")
    _prova_falsa(tmp_path, "outra.pdf")
    monkeypatch.setattr(
        questoes, "extrair_texto", lambda caminho: FIXTURE.read_text(encoding="utf-8")
    )

    resultado = servico.extrair_questoes(limite=5)

    assert resultado.provas == 2
    assert resultado.repetidas == 40
    assert len(servico.questoes_repetidas(minimo=2)) == 40


def test_ultima_alternativa_nao_engole_a_questao_seguinte(prova):
    """A alternativa "e" ficava com o enunciado da proxima questao colado:
    "F - F - V 2. Assinale a alternativa que completa..."."""
    for questao in prova:
        ultima = questao.alternativas["e"]
        assert not re.search(r"\d{1,2}\.\s+[A-Z]", ultima), (
            f"Q{questao.numero} tem a proxima questao dentro da alternativa e: "
            f"{ultima[:80]}"
        )


def test_rodape_colado_no_meio_da_linha_e_cortado():
    """O pypdf nem sempre quebra a linha antes do rodape, e ele vem grudado no
    fim da ultima alternativa."""
    sujo = "São corretas as afirmativas 1, 2 e 3. Página 7 Município de Brusque"
    assert questoes.cortar_mobilia(sujo) == "São corretas as afirmativas 1, 2 e 3."


def test_corte_nao_estraga_alternativa_limpa():
    limpo = "O Catupiry foi criado no século XX."
    assert questoes.cortar_mobilia(limpo) == limpo


def test_cabecalho_repetido_em_toda_pagina_e_removido():
    """Em vez de adivinhar mais um padrao de cabecalho, o que se repete em
    toda pagina e tratado como mobilia. Assim pega "AM2 Educador Social",
    o nome do municipio, e qualquer outro que o caderno invente."""
    texto = (
        "AM2 Educador Social\n1. Primeira questao\na. SQUARE uma\nb. SQUARE outra\n"
        "AM2 Educador Social\n2. Segunda questao\na. SQUARE uma\nb. SQUARE outra\n"
        "AM2 Educador Social\n3. Terceira questao\na. SQUARE uma\nb. SQUARE outra\n"
    )
    limpo = questoes.limpar_mobilia(texto)

    assert "AM2 Educador Social" not in limpo
    assert "Primeira questao" in limpo


def test_alternativa_repetida_nao_e_confundida_com_mobilia():
    """"Todas as anteriores" aparece em muita questao e continua sendo
    alternativa."""
    texto = "".join(
        f"{n}. Questao {n}\na. SQUARE Todas as anteriores\nb. SQUARE Outra\n"
        for n in range(1, 6)
    )
    limpo = questoes.limpar_mobilia(texto)

    assert limpo.count("Todas as anteriores") == 5


def test_rodape_no_fim_da_ultima_alternativa_saiu(prova):
    """Medido no acervo real: a sujeira caiu de 5,1% para 1,1% das questoes."""
    for questao in prova:
        assert "Página" not in questao.alternativas["e"]
