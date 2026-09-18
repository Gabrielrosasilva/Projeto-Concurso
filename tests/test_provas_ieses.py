"""Acervo da IESES: onde a banca publica edital, prova e gabarito.

A fixture e a pagina real do hotsite de Biguacu 2024, com os 31 cadernos e os
31 gabaritos.
"""
from pathlib import Path

import pytest

from radar import provas_ieses

FIXTURE = Path(__file__).parent / "fixtures" / "ieses" / "hotsite_biguacu.html"
BASE = "https://www.act2025.bigua.ieses.org/"


@pytest.fixture
def documentos():
    return provas_ieses.ler_hotsite(FIXTURE.read_text(encoding="utf-8"), BASE)


def _por_tipo(documentos, tipo):
    return [d for d in documentos if d.tipo == tipo]


def test_acha_os_cadernos_de_prova(documentos):
    assert len(_por_tipo(documentos, "prova")) == 31


def test_acha_os_gabaritos(documentos):
    """Aqui o gabarito e um PDF a parte. Na FEPESE ele vem marcado dentro do
    proprio caderno."""
    assert len(_por_tipo(documentos, "gabarito")) == 31


def test_acha_o_edital_e_a_retificacao(documentos):
    editais = {d.arquivo for d in _por_tipo(documentos, "edital")}

    assert "edital.pdf" in editais
    assert "edital_ret001.pdf" in editais


def test_cada_prova_tem_o_gabarito_de_mesmo_codigo(documentos):
    """O codigo e o do cargo, e e por ele que a prova casa com o gabarito."""
    provas = {d.arquivo.removeprefix("prova_") for d in _por_tipo(documentos, "prova")}
    gabaritos = {d.arquivo.removeprefix("gabarito_")
                 for d in _por_tipo(documentos, "gabarito")}

    assert provas == gabaritos


def test_o_cargo_vem_do_texto_ao_lado_do_link(documentos):
    """O endereco do PDF so tem o codigo ("1016.pdf"); o nome do cargo esta na
    linha da pagina ("- 1016 - Assistente Social")."""
    cargos = {d.cargo for d in _por_tipo(documentos, "prova")}

    assert "Assistente Social" in cargos
    assert None not in cargos


def test_prova_e_gabarito_nao_se_atropelam_no_disco(documentos):
    """Os dois arquivos se chamam "1016.pdf" na origem, em pastas diferentes.
    Sem o tipo no nome, um sobrescreveria o outro."""
    nomes = [d.arquivo for d in documentos]

    assert len(nomes) == len(set(nomes))


def test_a_banca_ja_vem_preenchida(documentos):
    assert all(d.banca == "IESES" for d in documentos)


def test_resultado_e_classificacao_ficam_de_fora(documentos):
    """Nao ajudam a estudar e so ocupariam disco."""
    assert not [d for d in documentos if "resultado" in d.url or "class_" in d.url]


def test_pagina_sem_pdf_nenhum_nao_quebra():
    assert provas_ieses.ler_hotsite("<html><body><p>nada</p></body></html>", BASE) == []


def test_link_que_nao_e_pdf_e_ignorado():
    html = '<html><body><a href="/inscricao">Inscreva-se</a></body></html>'

    assert provas_ieses.ler_hotsite(html, BASE) == []
