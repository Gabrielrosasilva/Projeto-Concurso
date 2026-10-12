"""A tela da traducao e as palavras dificeis (decisao 161, T3).

O que estes testes seguram: o termo do glossario casa por palavra inteira, sem
acento e sem caixa, e so a 1a vez em cada bloco; nunca na fonte; o corte nao
quebra o "2019-q55 (gabarito E)" que o `sem_gabarito` esconde; cada bloco de
artigo ganha o "🗣 Traduz pra mim" fechado, com as tres linhas, o selo e a
procedencia; o artigo traduzido sem frase ganha o bloco; a traducao orfa nao
aparece; o "⚖️ Nao confunda" so quando o tema tem; a ficha confere a traducao;
e a ficha sem traducao continua funcionando, ja enxuta.
"""
import copy
import json
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar import fichas, glossario
from radar.servico import cronograma as diario
from radar.servico import fichas as servico_fichas
from radar.web.app import app

FIXTURES = Path(__file__).parent / "fixtures"
TRADUCAO = json.loads((FIXTURES / "traducao_exemplo.json").read_text(encoding="utf-8"))
RESUMO = json.loads((FIXTURES / "resumo_enxuto.json").read_text(encoding="utf-8"))
PENAL, TEMA = RESUMO["materia"], RESUMO["tema"]
TERMOS = [
    {"termo": "inescusável", "variantes": [], "significado": "Que não tem desculpa.",
     "fontes": ["CP, art. 21"]},
    {"termo": "dolo", "variantes": [], "significado": "Quando a pessoa quis o resultado.",
     "fontes": ["CP, art. 18, I"]},
    {"termo": "dolo eventual", "variantes": [], "significado": "Quando a pessoa topou o risco.",
     "fontes": ["CP, art. 18, I"]},
    {"termo": "gabarito", "variantes": [], "significado": "A resposta oficial da prova.",
     "fontes": ["2019-q55"]},
]


def _marcados(trechos) -> list[str]:
    return [t.texto for t in trechos if t.significado]


# --- o corte em trechos ---------------------------------------------------------------

def test_o_termo_casa_por_palavra_inteira_sem_acento_e_sem_caixa():
    vistos: set = set()
    trechos = glossario.trechos("O desconhecimento da lei é INESCUSAVEL, e o dolorido não.",
                                TERMOS, vistos)
    assert _marcados(trechos) == ["INESCUSAVEL"]          # sem acento e sem caixa
    assert "".join(t.texto for t in trechos) == (
        "O desconhecimento da lei é INESCUSAVEL, e o dolorido não.")
    # "dolorido" nao e "dolo": palavra inteira.
    assert "dolo" not in vistos


def test_o_termo_mais_comprido_vence_e_so_a_primeira_vez_no_bloco():
    vistos: set = set()
    primeira = glossario.trechos("Assumiu o risco: dolo eventual, e não dolo direto.",
                                 TERMOS, vistos)
    assert _marcados(primeira) == ["dolo eventual", "dolo"]
    segunda = glossario.trechos("De novo o dolo eventual e o dolo.", TERMOS, vistos)
    assert _marcados(segunda) == []                        # ja visto neste bloco
    assert _marcados(glossario.trechos("O dolo de novo.", TERMOS, set())) == ["dolo"]


def test_o_corte_nao_quebra_o_gabarito_escondido():
    texto = "A pena cai de um a dois terços (2019-q55 (gabarito E)); confira o gabarito."
    trechos = glossario.trechos(texto, TERMOS, set(), fichas.GABARITO_CITADO)
    # O "gabarito" de dentro da citacao fica inteiro; o do fim e o marcado.
    assert _marcados(trechos) == ["gabarito"]
    assert trechos[-2].texto == "gabarito" and trechos[-1].texto == "."
    escondido = "".join(fichas.esconder_gabarito(t.texto, set()) for t in trechos)
    assert "2019-q55 (gabarito depois de responder no radar)" in escondido


# --- o resumo enxuto com a traducao ----------------------------------------------------

def test_cada_bloco_ganha_a_traducao_e_o_termo_e_marcado_uma_vez_por_bloco():
    e = fichas.resumo_enxuto(RESUMO["partes"], PENAL, TRADUCAO, TERMOS)
    por_artigo = {b.rotulo: b for b in e.blocos}
    assert [n for n, _ in por_artigo["CP, art. 15"].traducao] == ["Na real", "Exemplo",
                                                                   "Na prova"]
    assert por_artigo["CP, art. 16"].traducao == []         # sem traducao, sem o botao
    # Art. 18: o "dolo" e marcado na frase, e nao de novo no mesmo bloco.
    marcados_18 = [t for f in por_artigo["CP, art. 18"].frases for t in _marcados(f.trechos)]
    assert marcados_18.count("dolo") <= 1
    # Art. 21: "inescusável" na frase dele; a fonte nunca e cortada.
    (frase_21,) = por_artigo["CP, art. 21"].frases
    assert _marcados(frase_21.trechos) == ["inescusável"]
    assert frase_21.fontes == ["CP, art. 21"]
    assert len(e.nao_confunda) == 2 and e.traduzido


def test_o_artigo_traduzido_sem_frase_ganha_o_bloco_so_com_a_traducao():
    item = copy.deepcopy(TRADUCAO["itens"][0])
    item["artigo"] = "CP, art. 12"
    for chave in ("na_real", "exemplo"):
        item[chave]["fontes"] = ["CP, art. 12"]
    e = fichas.resumo_enxuto(RESUMO["partes"], PENAL, {"itens": [item]}, [])
    (bloco,) = [b for b in e.blocos if b.rotulo == "CP, art. 12"]
    assert bloco.frases == [] and len(bloco.traducao) == 3
    assert e.blocos[0] is bloco                              # em ordem de numero


def test_a_materia_sem_lei_nao_mostra_traducao():
    e = fichas.resumo_enxuto(RESUMO["partes"], "Língua Portuguesa", TRADUCAO, [])
    assert not e.blocos and not e.nao_confunda and not e.traduzido


# --- a tela ------------------------------------------------------------------------------

@pytest.fixture
def ficha_na_tela(banco_temporario, monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: date(2026, 10, 12))

    def gravar(traducao=None):
        escrita = fichas.FichaEscrita(
            tema=TEMA, materia=PENAL, modelo="Claude Code, de teste",
            ler_exatamente="CP, arts. 14 a 21, no texto oficial.",
            criado_em="2026-10-02T12:00:00+00:00",
            resumo={"partes": RESUMO["partes"], "modelo": "Claude Code, resumo de teste",
                    "criado_em": "2026-10-05T12:00:00+00:00", "conferido_em": None},
            traducao=traducao)
        servico_fichas.gravar([escrita])
        servico_fichas.gravar_glossario([{**t, "modelo": "m", "criado_em": "x"}
                                         for t in TERMOS])
        return escrita
    return gravar


def _traducao_gravada(**mais):
    return {**copy.deepcopy(TRADUCAO),
            "modelo": "Claude Code (claude-opus-5-5), importado manualmente, em 12/10/2026",
            "criado_em": "2026-10-12T12:00:00+00:00", "conferido_em": None,
            "artigos_do_resumo": [{"lei": "CP", "inicio": [14, ""], "fim": [21, ""]}], **mais}


def test_a_ficha_sem_traducao_continua_funcionando_ja_enxuta(ficha_na_tela):
    escrita = ficha_na_tela()
    html = TestClient(app).get(f"/fichas/{escrita.id}?data=2026-10-12").text
    assert "📜 Os artigos" in html and "⚠ O que mais derruba" in html
    assert "Traduz pra mim" not in html and "Conferi a tradução" not in html
    assert "Não confunda" not in html
    assert "Conferi este resumo" in html


def test_a_ficha_com_traducao_mostra_o_botao_o_selo_e_confere(ficha_na_tela):
    escrita = ficha_na_tela(_traducao_gravada())
    cliente = TestClient(app)
    html = cliente.get(f"/fichas/{escrita.id}?data=2026-10-12").text
    assert html.count("🗣 Traduz pra mim") == 2               # arts. 14 e 15
    assert re.search(r'<details class="ds-resumo__traduz">\s*<summary>🗣 Traduz pra mim', html)
    assert "<dt>Na real</dt>" in html and "<dt>Na prova</dt>" in html
    assert "Tradução escrita por Claude Code (claude-opus-5-5)" in html
    assert "⚖️ Não confunda" in html and "<th>O que acontece</th>" in html
    # O termo sublinhado com o significado, so com CSS (tabindex para o toque).
    assert ('<span class="ds-termo" tabindex="0">inescusável<span class="ds-termo__dica" '
            'role="tooltip"><b>inescusável:</b> Que não tem desculpa.</span></span>') in html
    # A letra do "na prova" fica escondida ate eu responder (decisao 148).
    assert "2019-q55 (gabarito depois de responder no radar)" in html
    assert "(gabarito E)" not in html
    # A conferencia da traducao e minha, e separada da do resumo.
    assert "Conferi a tradução" in html and "Ainda não conferida por você." in html
    volta = cliente.post(f"/fichas/{escrita.id}/traducao/conferir",
                         data={"data": "2026-10-12"}, follow_redirects=False)
    assert volta.status_code == 303 and volta.headers["location"].endswith("#resumo")
    gravada = servico_fichas.carregar()[0]
    assert gravada.traducao["conferido_em"] == "2026-10-12"
    assert gravada.resumo["conferido_em"] is None
    depois = cliente.get(f"/fichas/{escrita.id}?data=2026-10-12").text
    assert "Tradução conferida por você em 2026-10-12." in depois
    # Nenhum JavaScript na ficha.
    assert "<script" not in depois


def test_cada_frase_do_resumo_continua_aparecendo_uma_vez(ficha_na_tela):
    escrita = ficha_na_tela(_traducao_gravada())
    html = TestClient(app).get(f"/fichas/{escrita.id}?data=2026-10-12").text
    sem_tags = re.sub(r'<span class="ds-termo__dica"[^>]*>.*?</span></span>', "</span>", html)
    sem_tags = re.sub(r"<[^>]+>", "", sem_tags)
    for frases in RESUMO["partes"].values():
        for f in frases:
            texto = f["texto"].replace("'", "&#39;")
            assert sem_tags.count(texto) == 1, f["texto"]


def test_a_traducao_orfa_nao_aparece(ficha_na_tela):
    """O resumo refeito perdeu o art. 15: a traducao dele nao aparece (e o
    --verificar-resumos avisa, test_traducao)."""
    sem_15 = {chave: [f for f in frases if not any("art. 15" in x for x in f["fontes"])]
              for chave, frases in RESUMO["partes"].items()}
    escrita = ficha_na_tela(_traducao_gravada())
    escrita.resumo = {**escrita.resumo, "partes": sem_15}
    servico_fichas.gravar([escrita])
    html = TestClient(app).get(f"/fichas/{escrita.id}?data=2026-10-12").text
    assert html.count("🗣 Traduz pra mim") == 1 and "<h4>CP, art. 15</h4>" not in html


def test_a_janela_da_tela_hoje_mostra_a_traducao(ficha_na_tela):
    from types import SimpleNamespace

    from radar import cronograma

    escrita = ficha_na_tela(_traducao_gravada())
    teoria = SimpleNamespace(tipo="teoria", titulo=TEMA, materia=PENAL, desligada=False,
                             origem=None, materias_da_rodada=())
    resumos = servico_fichas.resumos_do_dia(
        [SimpleNamespace(chave="manha", faixas=[teoria])], date(2026, 10, 12),
        cronograma.carregar(), [escrita], [], [])
    from radar.web.app import templates

    janela = str(templates.env.get_template("_resumo.html").module.janelas(resumos))
    assert janela.count("🗣 Traduz pra mim") == 2 and "⚖️ Não confunda" in janela
    assert 'class="ds-termo"' in janela
