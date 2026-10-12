"""O resumo enxuto (decisao 161, T1): so a tela muda, nenhum dado.

O que estes testes seguram: a frase que cita SO um artigo vai para o bloco
dele e a de dois artigos fica no "dominar"; cada frase aparece uma vez; os
blocos saem em ordem de numero; as 3 pegadinhas abertas comecam pelas de
questao real (o alvo antes do complementar); a materia sem lei fica com as
regras-chave como estao; e o link da Noite cai em "Como a banca cobra" dentro
de um <details>, que o navegador abre pela ancora.
"""
import json
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar import artigos, fichas
from radar.servico import cronograma as diario
from radar.servico import fichas as servico_fichas
from radar.web.app import app

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "resumo_enxuto.json")
                     .read_text(encoding="utf-8"))
PARTES = FIXTURE["partes"]
PENAL = FIXTURE["materia"]
TEMA = FIXTURE["tema"]


def _textos(frases) -> list[str]:
    return [f.texto for f in frases]


def _todas(e) -> list[str]:
    return (_textos(f for b in e.blocos for f in b.frases) + _textos(e.regras_chave)
            + _textos(e.basico) + _textos(e.derruba) + _textos(e.dominar)
            + _textos(e.como_cobra) + _textos(e.outras_pegadinhas))


# --- o leitor de artigos ------------------------------------------------------------

@pytest.mark.parametrize("fonte, rotulo", [
    ("CP, art. 15", "CP, art. 15"),
    ("CP, art. 14, I e II", "CP, art. 14"),
    ("CP, art. 20, § 3º", "CP, art. 20"),
    ("LEP, art. 9º-A, caput", "LEP, art. 9º-A"),
    ("LEP, art. 24 e §§ 1º e 2º", "LEP, art. 24"),
    ("Regras de Mandela, regra 12.1", "Regras de Mandela, regra 12"),
    ("Declaração de Viena (1993), § 5", "Declaração de Viena (1993), § 5"),
    ("Convenção Americana, art. 7.5", "Convenção Americana, art. 7º"),
])
def test_a_fonte_de_um_artigo_so(fonte, rotulo):
    assert artigos.da_fonte(fonte).rotulo == rotulo


@pytest.mark.parametrize("fonte", [
    "CF, arts. 10 e 11", "LEP, arts. 187 a 192", "Regras de Mandela, regras 36 e 37",
    "2019-q53 (gabarito D)", "Súmula Vinculante 25", "doutrina (conceito analítico de crime)",
    "Convenção Americana sobre Direitos Humanos",
])
def test_a_fonte_de_varios_artigos_ou_de_nenhum(fonte):
    assert artigos.da_fonte(fonte) is None


def test_os_artigos_do_tema_pelo_titulo_e_pelo_ler_exatamente():
    tema = artigos.do_tema(TEMA, "CP, arts. 14 a 21, no texto oficial.", PENAL)
    assert artigos.do_tema_contem(tema, artigos.Artigo("CP", 19))
    assert not artigos.do_tema_contem(tema, artigos.Artigo("CP", 22))
    assert not artigos.do_tema_contem(tema, artigos.Artigo("CF", 15))
    # A lei depois da lista ("do CP", "da DUDH") vence a nomeada antes.
    lep = artigos.do_tema("Livramento (arts. 131 a 170)",
                          "LEP, arts. 131 a 170; leia junto os arts. 83 a 90 do CP.",
                          "Lei de Execução Penal")
    assert artigos.do_tema_contem(lep, artigos.Artigo("LEP", 146, "B"))
    assert artigos.do_tema_contem(lep, artigos.Artigo("CP", 83))
    assert not artigos.do_tema_contem(lep, artigos.Artigo("LEP", 83))
    dh = artigos.do_tema("Teoria geral", "Leia o § 5º da Declaração e Programa de Ação "
                         "de Viena (1993) e os arts. 1º, 2º e 5º da DUDH.", "Direitos Humanos")
    assert artigos.do_tema_contem(dh, artigos.Artigo("Declaração de Viena (1993)", 5))
    assert artigos.do_tema_contem(dh, artigos.Artigo("DUDH", 2))
    assert not artigos.do_tema_contem(dh, artigos.Artigo("DUDH", 3))


# --- o agrupamento ------------------------------------------------------------------

def test_a_frase_de_um_artigo_vai_para_o_bloco_e_a_de_dois_fica_no_dominar():
    e = fichas.resumo_enxuto(PARTES, PENAL)
    assert [b.rotulo for b in e.blocos] == [
        "CP, art. 14", "CP, art. 15", "CP, art. 16", "CP, art. 17", "CP, art. 18",
        "CP, art. 19", "CP, art. 20", "CP, art. 21"]
    bloco_14 = e.blocos[0]
    # As duas do art. 14: a do "dominar" (I e II) e a do "artigos" (p. único).
    assert [f.fontes for f in bloco_14.frases] == [["CP, art. 14, I e II"],
                                                    ["CP, art. 14, parágrafo único"]]
    # As de dois artigos ficam no "O que eu preciso dominar", e so elas.
    assert [f.fontes for f in e.dominar] == [
        ["CP, art. 18, parágrafo único", "CP, art. 19"], ["CP, art. 20, caput", "CP, art. 21"]]


def test_cada_frase_aparece_uma_vez_e_nenhuma_some():
    e = fichas.resumo_enxuto(PARTES, PENAL)
    gravadas = [f["texto"] for frases in PARTES.values() for f in frases]
    assert sorted(_todas(e)) == sorted(gravadas)
    assert len(set(_todas(e))) == len(_todas(e))


def test_o_texto_e_a_fonte_ficam_exatamente_como_estao():
    e = fichas.resumo_enxuto(PARTES, PENAL)
    (frase,) = [f for f in PARTES["artigos"] if f["fontes"] == ["CP, art. 16"]]
    (na_tela,) = [f for b in e.blocos if b.rotulo == "CP, art. 16" for f in b.frases]
    assert (na_tela.texto, na_tela.fontes) == (frase["texto"], frase["fontes"])
    assert [t.texto for t in na_tela.trechos] == [frase["texto"]]


def test_as_3_pegadinhas_abertas_comecam_pelas_de_questao_real():
    e = fichas.resumo_enxuto(PARTES, PENAL)
    assert fichas.PEGADINHAS_EM_DESTAQUE == 3 and len(e.derruba) == 3
    # A do complementar esta em primeiro no arquivo, e vai depois das do alvo.
    assert all(re.search(r"(?<!FEPESE-)20\d\d-q\d+", " ".join(f.fontes)) for f in e.derruba)
    resto = [" ".join(f.fontes) for f in e.outras_pegadinhas]
    assert "FEPESE-2016-q21" in resto[-2]
    assert "sem questão real" in resto[-1]


def test_a_materia_sem_lei_fica_com_as_regras_chave_como_estao():
    partes = {"dominar": [{"texto": "Passiva sintética: VTD + se.", "fontes": ["regra - Pestana"]}],
              "artigos": [{"texto": "VTD + se + sujeito plural = plural.",
                           "fontes": ["regra de concordância - Pestana"]}],
              "como_cobra": PARTES["como_cobra"], "pegadinhas": PARTES["pegadinhas"][:2]}
    e = fichas.resumo_enxuto(partes, "Língua Portuguesa")
    assert not e.de_lei and not e.blocos
    assert _textos(e.regras_chave) == ["VTD + se + sujeito plural = plural."]
    assert _textos(e.dominar) == ["Passiva sintética: VTD + se."]
    assert len(e.derruba) == 2 and not e.outras_pegadinhas


def test_o_basico_fica_aberto_quando_existe():
    basico = [{"texto": "Leia o art. 17 inteiro.", "fontes": ["CP, art. 17"]}]
    e = fichas.resumo_enxuto({**PARTES, "basico": basico}, PENAL)
    assert _textos(e.basico) == ["Leia o art. 17 inteiro."]
    # O basico nao vai para o bloco do art. 17: ele e outra parte.
    assert "Leia o art. 17 inteiro." not in _textos(
        f for b in e.blocos for f in b.frases)


# --- a tela -------------------------------------------------------------------------

@pytest.fixture
def com_resumo(banco_temporario, monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 5))
    escrita = fichas.FichaEscrita(
        tema=TEMA, materia=PENAL, modelo="Claude Code, de teste",
        criado_em="2026-10-02T12:00:00+00:00",
        resumo={"partes": PARTES, "modelo": "Claude Code (claude-opus-5-5), em teste",
                "criado_em": "2026-10-05T12:00:00+00:00", "conferido_em": None})
    servico_fichas.gravar([escrita])
    return escrita


def _uma_vez(html: str, texto: str) -> int:
    return html.count(texto)


def test_a_ficha_mostra_o_resumo_enxuto_com_cada_frase_uma_vez(com_resumo):
    html = TestClient(app).get(f"/fichas/{com_resumo.id}?data=2026-10-05").text
    assert "📜 Os artigos" in html and "<h4>CP, art. 15</h4>" in html
    assert "⚠ O que mais derruba" in html
    for nome in ("O que eu preciso dominar", "Como a banca cobra", "As outras pegadinhas"):
        assert re.search(r"<summary>" + nome, html)
    for frases in PARTES.values():
        for f in frases:
            assert _uma_vez(html, f["texto"].replace("'", "&#39;")) == 1, f["texto"]
    assert "Conferi este resumo" in html


def test_o_link_da_noite_cai_em_como_cobra_dentro_do_details(com_resumo):
    """O link e "#<id>-cobra", e a ancora fica DENTRO do <details> de "Como a
    banca cobra": o navegador abre o <details> que contem o alvo do link (o
    algoritmo de revelar ancestrais do HTML), e a janela abre pelo :has(:target)."""
    from types import SimpleNamespace

    from radar import cronograma

    plano = cronograma.carregar()
    teoria = SimpleNamespace(tipo="teoria", titulo=TEMA, materia=PENAL, desligada=False,
                             origem=None, materias_da_rodada=())
    blocos = [SimpleNamespace(chave="noite", faixas=[teoria])]
    resumos = servico_fichas.resumos_do_dia(blocos, date(2026, 10, 5), plano,
                                            [com_resumo], [], [])
    from radar.web.app import templates

    modulo = templates.env.get_template("_resumo.html").module
    ident = "resumo-" + com_resumo.id
    assert f'href="#{ident}-cobra"' in str(modulo.botao(resumos.da_faixa("noite", 0),
                                                        "noite", 0, True))
    janela = str(modulo.janelas(resumos))
    dobra = re.search(r"<details[^>]*>\s*<summary>Como a banca cobra.*?</details>", janela,
                      re.DOTALL)
    assert dobra and f'id="{ident}-cobra"' in dobra.group(0)
    assert janela.count(f'id="{ident}-cobra"') == 1
