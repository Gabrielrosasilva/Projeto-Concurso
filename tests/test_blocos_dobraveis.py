"""Os blocos da aba Hoje dobram, e o "Depois das 22h" nasce fechado (B.11).

O que estes testes seguram:

  * cada bloco do dia e um <details> com o cabecalho de <summary>: um clique no
    cabecalho - inclusive no canto direito, em cima dos horarios - recolhe a
    lista de faixas, e outro a traz de volta. Os DOIS sentidos, que e o que foi
    pedido;
  * "Manha" e "Noite" nascem abertos; "Depois das 22h" nasce FECHADO, e
    fechado mostra no proprio cabecalho que o ANKI esta desativado;
  * **nada de JavaScript**: o cronometro continua sendo o unico JS do projeto.

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


# --- a dobra --------------------------------------------------------------------

def test_cada_bloco_do_dia_e_um_details_com_o_cabecalho_de_summary(tela):
    blocos = _blocos(tela)

    assert set(blocos) >= {"manha", "noite", "pos22"}
    # O cabecalho e o botao: e ele que o clique recolhe e traz de volta.
    assert tela.count('<summary class="ds-cartao__cabeca">') == len(blocos)


def test_os_horarios_ficam_dentro_da_area_que_recolhe(tela):
    """O pedido foi clicar "no canto direito, perto dos horarios": os horarios
    e o sinal da dobra estao DENTRO do summary, e nao fora dele."""
    cabeca = re.search(
        r'<summary class="ds-cartao__cabeca">(.*?)</summary>', tela, re.DOTALL)

    assert cabeca is not None
    assert 'class="horas"' in cabeca.group(1)
    assert 'class="dobra-sinal"' in cabeca.group(1)


def test_o_sinal_da_dobra_vira_quando_o_bloco_abre(tela):
    """Fechado mostra ▾, aberto ▴ - os dois sentidos, so com CSS."""
    assert '.bloco-dia .dobra-sinal::after{content:"▾"}' in tela
    assert '.bloco-dobra[open] .dobra-sinal::after{content:"▴"}' in tela


def test_a_lista_de_faixas_fica_dentro_do_details(tela):
    """Se a <ol> ficasse fora, fechar o bloco nao esconderia nada."""
    dentro = re.search(
        r'<details class="bloco-dobra".*?<ol class="linha-tempo">.*?</ol>\s*</details>',
        tela, re.DOTALL)

    assert dentro is not None


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
    # A chave de verdade e a do comeco da linha: "anki: desativado" tambem
    # aparece dentro dos comentarios do cabecalho do arquivo.
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


# --- sem JavaScript -------------------------------------------------------------

def test_a_dobra_nao_usou_javascript(tela):
    """O cronometro e o unico JS da tela, e ele continua sendo o unico."""
    assert "onclick=" not in tela
    assert "onchange=" not in tela
    assert "bloco-dobra" not in _so_os_scripts(tela)


def _so_os_scripts(texto: str) -> str:
    return "\n".join(re.findall(r"<script.*?</script>", texto, re.DOTALL))


def test_o_unico_script_da_tela_continua_sendo_o_cronometro(tela):
    scripts = re.findall(r"<script.*?</script>", tela, re.DOTALL)

    assert len(scripts) == 1
    assert "cronometro" in scripts[0].lower() or "cronômetro" in scripts[0].lower()
