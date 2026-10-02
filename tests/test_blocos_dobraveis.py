"""Os blocos da aba Hoje dobram, e o "Depois das 22h" nasce fechado (B.11).

O que estes testes seguram:

  * cada bloco do dia e um <details> com o cabecalho de <summary>, e **so o
    sinal do canto direito** recebe o clique: um clique no titulo ou nos
    horarios nao pode recolher o bloco sem querer. Pelo teclado, Tab no
    cabecalho e Enter continuam dobrando;
  * "Manha" e "Noite" nascem abertos; "Depois das 22h" nasce FECHADO, e
    fechado mostra no proprio cabecalho que o ANKI esta desativado;
  * a dobra **funciona sem JavaScript** - o padrao vem do HTML. O `dobra.js`
    so LEMBRA o que eu deixei recolhido, e nao pode quebrar a tela quando o
    localStorage estiver bloqueado.

O relogio e parado em 02/10/2026 (o primeiro dia da rotina nova): nada aqui
depende do dia em que o teste roda.
"""
import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from radar import servico
from radar.util import fuso_local
from radar.web.app import app

DIA = "2026-10-02"
MOMENTO = datetime(2026, 10, 2, 9, 0, tzinfo=fuso_local())

#: A chave `anki` de verdade e a do comeco da linha: o mesmo texto tambem
#: aparece dentro dos comentarios do cabecalho do cronograma.yml.
LINHA_DO_ANKI = "\nanki: desativado"

#: O cabecalho de um bloco, como o template escreve. O `title` existe porque o
#: alvo de clique e pequeno: ele diz o que o canto faz.
SUMMARY = '<summary class="ds-cartao__cabeca" title="Recolher ou expandir este bloco">'


@pytest.fixture
def cliente_simples(banco_temporario):
    return TestClient(app)


@pytest.fixture
def tela(banco_temporario, monkeypatch):
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: MOMENTO)
    return TestClient(app).get(f"/hoje?data={DIA}").text


def _blocos(texto: str) -> dict[str, str]:
    """{chave do bloco: a abertura do <details> dele}."""
    achados = re.findall(
        r'<section class="ds-cartao bloco-dia bloco-(\w+)".*?'
        r'(<details class="bloco-dobra"[^>]*>)',
        texto, re.DOTALL)
    return dict(achados)


def _regras_do_sinal(texto: str) -> str:
    return re.search(r"\.bloco-dia \.dobra-sinal\{(.*?)\}", texto, re.DOTALL).group(1)


# --- a dobra --------------------------------------------------------------------

def test_cada_bloco_do_dia_e_um_details_com_o_cabecalho_de_summary(tela):
    blocos = _blocos(tela)

    assert set(blocos) >= {"manha", "noite", "pos22"}
    assert tela.count(SUMMARY) == len(blocos)


def test_os_horarios_e_o_sinal_ficam_dentro_do_cabecalho(tela):
    """O pedido foi dobrar "no canto direito, perto dos horarios": os dois
    estao no mesmo cabecalho, e o sinal vem depois dos horarios."""
    cabeca = re.search(re.escape(SUMMARY) + r"(.*?)</summary>", tela, re.DOTALL)

    assert cabeca is not None
    corpo = cabeca.group(1)
    assert 'class="horas"' in corpo and 'class="dobra-sinal"' in corpo
    assert corpo.index('class="horas"') < corpo.index('class="dobra-sinal"')


def test_a_lista_de_faixas_fica_dentro_do_details(tela):
    """Se a <ol> ficasse fora, fechar o bloco nao esconderia nada."""
    dentro = re.search(
        r'<details class="bloco-dobra".*?<ol class="linha-tempo">.*?</ol>\s*</details>',
        tela, re.DOTALL)

    assert dentro is not None


def test_o_sinal_vira_quando_o_bloco_abre(tela):
    """Fechado mostra ▾, aberto ▴ - os dois sentidos, so com CSS."""
    assert '.bloco-dia .dobra-sinal::after{content:"▾"}' in tela
    assert '.bloco-dobra[open] .dobra-sinal::after{content:"▴"}' in tela


# --- so o canto dobra ------------------------------------------------------------
#
# Pedido depois da primeira versao: um clique no titulo ou nos horarios nao pode
# recolher o bloco sem eu querer.

def test_so_o_sinal_do_canto_recebe_o_clique(tela):
    """O <summary> inteiro deixa o clique atravessar; so o sinal o recebe."""
    assert ".bloco-dobra > summary{list-style:none;cursor:default;pointer-events:none}" in tela
    assert "pointer-events:auto" in _regras_do_sinal(tela)


def test_o_cabecalho_continua_focavel_pelo_teclado(tela):
    """`pointer-events` nao vale para o teclado: Tab ate o cabecalho e Enter
    continuam dobrando, e o foco e visivel."""
    assert SUMMARY in tela
    assert ".bloco-dobra > summary:focus-visible{outline:" in tela


def test_o_sinal_tem_area_de_clique_de_verdade(tela):
    """Um glifo de dez pixels nao e botao: o sinal tem area minima."""
    regras = _regras_do_sinal(tela)

    assert "min-width:1.75rem" in regras and "min-height:1.75rem" in regras
    assert "cursor:pointer" in regras


def test_o_cabecalho_diz_o_que_o_canto_faz(tela):
    """O alvo e pequeno e o simbolo e discreto: o title explica."""
    assert 'title="Recolher ou expandir este bloco"' in tela


# --- quem nasce aberto, e quem nasce fechado ------------------------------------

def test_manha_e_noite_nascem_abertos(tela):
    blocos = _blocos(tela)

    assert "open" in blocos["manha"]
    assert "open" in blocos["noite"]


def test_depois_das_22h_nasce_fechado(tela):
    """O pedido: o ANKI sempre minimizado, e abrir e acao minha."""
    assert "open" not in _blocos(tela)["pos22"]


def test_fechado_o_bloco_das_22h_mostra_que_o_anki_esta_desativado(tela):
    cabeca = re.search(
        r'<h2 class="ds-cartao__titulo" id="bloco-pos22">.*?</summary>',
        tela, re.DOTALL)

    assert cabeca is not None
    assert "ANKI temporariamente desativado" in cabeca.group(0)
    assert 'class="anki-dobrado"' in cabeca.group(0)


def test_aberto_a_frase_do_cabecalho_sai_e_a_da_faixa_fica(tela):
    """Sem isto a mesma frase apareceria duas vezes no bloco aberto."""
    assert ".bloco-dobra[open] .anki-dobrado{display:none}" in tela
    # A faixa minimizada, que a 6A criou, continua onde estava.
    assert 'class="faixa-desligada"' in tela


def test_com_o_anki_religado_o_cabecalho_nao_fala_de_desativado(
    banco_temporario, monkeypatch, tmp_path
):
    """A frase sai do cabecalho quando a faixa do Anki volta a valer: ela segue
    a faixa DESLIGADA, e nao o nome do bloco.

    A chave `anki` e aplicada na LEITURA do arquivo (`_sem_anki`), e nao ao
    montar o dia: por isso o teste religa num arquivo copiado, como a 6A fez,
    em vez de remontar o Plano em memoria. O config real nao e tocado.
    """
    from radar import config, cronograma

    original = (config.diretorio_config() / "cronograma.yml").read_text(encoding="utf-8")
    assert LINHA_DO_ANKI in original
    copia = tmp_path / "cronograma_religado.yml"
    copia.write_text(
        original.replace(LINHA_DO_ANKI, LINHA_DO_ANKI.replace("des", ""), 1),
        encoding="utf-8")
    religado = cronograma.carregar(copia)
    assert religado.anki is True

    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: MOMENTO)
    monkeypatch.setattr(cronograma, "carregar", lambda *a, **k: religado)

    texto = TestClient(app).get(f"/hoje?data={DIA}").text

    assert 'class="anki-dobrado"' not in texto
    # E o bloco continua nascendo fechado: ele e sobreaviso.
    assert "open" not in _blocos(texto)["pos22"]


# --- o JavaScript da dobra -------------------------------------------------------
#
# A dobra passou a ser LEMBRADA entre recarregamentos, e guardar estado no
# navegador e JavaScript. O que estes testes seguram e o LIMITE disso: a dobra
# funciona sem o arquivo, e o script so restaura e salva.

def test_a_tela_tem_os_dois_scripts_e_so_eles(tela):
    fontes = re.findall(r'<script src="([^"]+)"', tela)

    assert fontes == ["/estatico/cronometro.js", "/estatico/dobra.js"]
    # Nada embutido na pagina, e nenhum atributo de evento no HTML.
    assert re.findall(r"<script(?! src)", tela) == []
    assert "onclick=" not in tela and "onchange=" not in tela


def test_a_dobra_funciona_sem_o_javascript(tela):
    """O padrao vem do HTML: sem o dobra.js a dobra responde ao clique, so nao
    e lembrada. E o <details> que dobra, nao o script."""
    blocos = _blocos(tela)

    assert "open" in blocos["manha"] and "open" not in blocos["pos22"]
    assert tela.count(SUMMARY) == len(blocos)


def test_cada_bloco_leva_a_chave_que_o_script_guarda(tela):
    """Sem o `data-bloco` o script nao teria como lembrar qual e qual."""
    achados = set(re.findall(r'<details class="bloco-dobra" data-bloco="(\w+)"', tela))

    assert achados == {"manha", "noite", "pos22"}


def test_o_dobra_js_e_servido_e_protege_todo_acesso_ao_armazenamento(cliente_simples):
    fonte = cliente_simples.get("/estatico/dobra.js")

    assert fonte.status_code == 200
    corpo = fonte.text
    # Janela privada e dado do site limpo nao podem quebrar a tela.
    assert corpo.count("try {") >= 3
    assert "localStorage" in corpo
    # A chave e o BLOCO, e nao o dia: e uma preferencia minha.
    assert 'getAttribute("data-bloco")' in corpo


def test_o_script_nao_recolhe_o_bloco_da_ancora(cliente_simples):
    """Depois de anotar uma faixa a tela volta para a ancora dela. Recolher
    justo o bloco que eu acabei de anotar esconderia a resposta do meu clique."""
    corpo = cliente_simples.get("/estatico/dobra.js").text

    assert "blocoDaAncora" in corpo
    assert "window.location.hash" in corpo


def test_o_script_sai_de_fininho_onde_nao_ha_bloco(cliente_simples):
    """As outras telas tambem carregariam o arquivo se ele fosse global: ele
    para na primeira linha quando nao acha bloco nenhum."""
    corpo = cliente_simples.get("/estatico/dobra.js").text

    assert 'querySelectorAll("details.bloco-dobra[data-bloco]")' in corpo
    assert "if (!blocos.length)" in corpo
