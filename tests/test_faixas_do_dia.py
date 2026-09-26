"""Os checks de cada faixa do cronograma, e o formulario que sugere a meta.

A faixa e reconhecida por bloco + indice + TITULO: o check cujo titulo nao
bate mais com o cronograma.yml e ignorado, e nao marca a faixa errada.
"""
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import acervo, cronograma, servico
from radar.cli import app as cli
from radar.db import sessao
from radar.models import EstadoDoDia
from radar.servico.cronograma import (
    RegistroInvalido,
    estado_do_dia,
    faixas_feitas,
    marcar_faixa,
    sugerir_meta,
)
from radar.util import fuso_local
from radar.web.app import app

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
# O mini tem 28/09, 29/09 e 03/10. "Hoje", para os testes, e o ultimo deles.
HOJE = date(2026, 10, 3)
SEG = date(2026, 9, 28)

# As faixas da segunda do mini, pela posicao. As pausas (manha 1, noite 1)
# e o bonus (pos22 1) ficam fora da conta da meta.
TEORIA = ("manha", 0, "Aplicação da lei penal")
PORTUGUES_MANHA = ("manha", 2, "Substantivo")
DIREITO_NOITE = ("noite", 0, "Aprendizagem: aplicação da lei penal")
PORTUGUES_NOITE = ("noite", 2, "Substantivo")
CORRECAO = ("noite", 3, "Correção")
ANKI = ("pos22", 0, "Anki")
BONUS = ("pos22", 1, "Bônus: lógica")
TODAS_QUE_CONTAM = [TEORIA, PORTUGUES_MANHA, DIREITO_NOITE, PORTUGUES_NOITE, CORRECAO, ANKI]


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


def _marcar(plano, faixa, data=SEG):
    bloco, indice, titulo = faixa
    return marcar_faixa(data, bloco, indice, titulo, plano=plano, hoje=HOJE)


def _feitas(plano, data=SEG, nivel=1):
    dia = cronograma.montar_dia(plano, data, nivel)
    return dia, faixas_feitas(dia, estado_do_dia(data))


# --- marcar e desmarcar -----------------------------------------------------

def test_marcar_e_desmarcar(banco_temporario, plano):
    assert _marcar(plano, TEORIA) is True
    assert _feitas(plano)[1] == {("manha", 0)}
    assert _marcar(plano, TEORIA) is False
    assert _feitas(plano)[1] == set()


def test_marcar_duas_faixas_guarda_as_duas(banco_temporario, plano):
    _marcar(plano, TEORIA)
    _marcar(plano, ANKI)
    assert _feitas(plano)[1] == {("manha", 0), ("pos22", 0)}
    (check_teoria, check_anki) = estado_do_dia(SEG).faixas_feitas
    assert check_teoria == {"bloco": "manha", "indice": 0, "titulo": "Aplicação da lei penal"}
    assert check_anki["titulo"] == "Anki"


def test_titulo_que_mudou_nao_conta(banco_temporario, plano):
    _marcar(plano, TEORIA)
    dia = cronograma.montar_dia(plano, SEG, 1)
    # O YAML mudou: a faixa 0 da manha agora e outra.
    dia.manha[0] = replace(dia.manha[0], titulo="Outro assunto")
    assert faixas_feitas(dia, estado_do_dia(SEG)) == set()


def test_marcar_com_titulo_velho_e_recusado(banco_temporario, plano):
    with pytest.raises(RegistroInvalido, match="mudou"):
        marcar_faixa(SEG, "manha", 0, "Titulo de antes", plano=plano, hoje=HOJE)
    assert estado_do_dia(SEG) is None


def test_dia_futuro_recusa(banco_temporario, plano):
    with pytest.raises(RegistroInvalido, match="ainda nao chegou"):
        marcar_faixa(SEG, "manha", 0, TEORIA[2], plano=plano, hoje=SEG - timedelta(days=1))


@pytest.mark.parametrize("bloco, indice, titulo", [
    ("manha", 1, "Pausa"),          # pausa nao se marca
    ("manha", 9, "Nada"),           # posicao que nao existe
    ("tarde", 0, "Nada"),           # bloco que nao existe
])
def test_faixa_que_nao_se_marca(banco_temporario, plano, bloco, indice, titulo):
    with pytest.raises(RegistroInvalido):
        marcar_faixa(SEG, bloco, indice, titulo, plano=plano, hoje=HOJE)


# --- a soma das questoes e a sugestao ---------------------------------------

def test_soma_das_questoes_respeita_o_nivel(banco_temporario, plano):
    _marcar(plano, DIREITO_NOITE)
    _marcar(plano, PORTUGUES_NOITE)
    # Nivel 1 da rampa do mini: direito 15, portugues 10.
    dia, feitas = _feitas(plano, nivel=1)
    assert sugerir_meta(dia, feitas).questoes == 25
    # Nivel 2: direito 20 - o numero gravado (15) nao vale mais.
    dia, feitas = _feitas(plano, nivel=2)
    assert sugerir_meta(dia, feitas).questoes == 30


def test_sugestao_ideal_com_todas_as_faixas_que_contam(banco_temporario, plano):
    for faixa in TODAS_QUE_CONTAM:
        _marcar(plano, faixa)
    s = sugerir_meta(*_feitas(plano))
    # O bonus e opcional: nao precisa dele para ser Ideal.
    assert (s.meta, s.feitas, s.total) == ("ideal", 6, 6)


def test_sugestao_reduzida_manha_inteira_mais_direito(banco_temporario, plano):
    for faixa in (TEORIA, PORTUGUES_MANHA, DIREITO_NOITE):
        _marcar(plano, faixa)
    s = sugerir_meta(*_feitas(plano))
    assert (s.meta, s.feitas, s.total) == ("reduzida", 3, 6)


def test_manha_pela_metade_mais_direito_e_minima(banco_temporario, plano):
    for faixa in (TEORIA, DIREITO_NOITE):
        _marcar(plano, faixa)
    assert sugerir_meta(*_feitas(plano)).meta == "minima"


def test_sugestao_minima_com_uma_faixa_de_questoes(banco_temporario, plano):
    _marcar(plano, PORTUGUES_NOITE)
    assert sugerir_meta(*_feitas(plano)).meta == "minima"


def test_nada_marcado_nao_sugere(banco_temporario, plano):
    s = sugerir_meta(*_feitas(plano))
    assert (s.meta, s.feitas, s.questoes) == (None, 0, 0)


def test_so_teoria_ou_so_bonus_nao_sugere(banco_temporario, plano):
    _marcar(plano, TEORIA)
    assert sugerir_meta(*_feitas(plano)).meta is None
    _marcar(plano, TEORIA)                      # desmarca
    _marcar(plano, BONUS)
    s = sugerir_meta(*_feitas(plano))
    # O bonus e fora do total: nao faz Minima, mas as questoes dele contam.
    assert (s.meta, s.questoes) == (None, 10)


# --- o backup em data/estado_do_dia.json ------------------------------------

def test_exportar_e_importar_ida_e_volta(banco_temporario, plano):
    _marcar(plano, TEORIA)
    _marcar(plano, ANKI)
    with sessao() as s:
        s.get(EstadoDoDia, estado_do_dia(SEG).id).plano_b = 30
    assert acervo.exportar_estados() == 1

    (linha,) = json.loads(acervo.caminho_dos_estados().read_text(encoding="utf-8"))
    assert linha["data"] == "2026-09-28"
    assert linha["plano_b"] == 30
    assert [c["titulo"] for c in linha["faixas_feitas"]] == ["Aplicação da lei penal", "Anki"]

    with sessao() as s:
        s.delete(s.get(EstadoDoDia, estado_do_dia(SEG).id))
    assert estado_do_dia(SEG) is None

    assert acervo.importar_estados() == 1
    assert _feitas(plano)[1] == {("manha", 0), ("pos22", 0)}
    assert estado_do_dia(SEG).plano_b == 30
    assert acervo.importar_estados() == 0          # rodar de novo nao muda nada


def test_na_mescla_vale_o_mais_recente(banco_temporario, plano, tmp_path):
    arquivo = tmp_path / "estado_do_dia.json"
    arquivo.write_text(json.dumps([
        {"data": "2026-09-28", "plano_b": None, "atualizado_em": "2099-01-01T00:00:00+00:00",
         "faixas_feitas": [{"bloco": "pos22", "indice": 0, "titulo": "Anki"}]},
        {"data": "2026-09-29", "plano_b": 60, "atualizado_em": "2020-01-01T00:00:00+00:00",
         "faixas_feitas": []},
    ]), encoding="utf-8")
    _marcar(plano, TEORIA)                     # mais velho que o do arquivo

    assert acervo.exportar_estados(arquivo) == 2
    por_data = {l["data"]: l for l in json.loads(arquivo.read_text(encoding="utf-8"))}
    assert por_data["2026-09-28"]["faixas_feitas"][0]["titulo"] == "Anki"
    assert por_data["2026-09-29"]["plano_b"] == 60


def test_apagar_o_dia_leva_os_checks_junto(banco_temporario, plano):
    _marcar(plano, TEORIA)
    acervo.exportar_estados()
    assert servico.cronograma.apagar(SEG)
    assert estado_do_dia(SEG) is None
    assert json.loads(acervo.caminho_dos_estados().read_text(encoding="utf-8")) == []


def test_o_arquivo_entra_no_sincronizar():
    from radar.cli import ARQUIVOS_DO_RADAR
    assert "data/estado_do_dia.json" in ARQUIVOS_DO_RADAR


# --- a tela ------------------------------------------------------------------

@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    # O cronograma real: "hoje" parado em 30/09, para 28/09 ser dia passado.
    momento = datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: momento)
    return TestClient(app)


def _faixa_real(data, bloco, indice):
    return getattr(cronograma.carregar().dia(data), bloco)[indice]


def test_o_circulo_marca_e_volta_para_a_mesma_faixa(cliente):
    titulo = _faixa_real(SEG, "manha", 0).titulo
    resposta = cliente.post("/hoje/faixa", data={
        "data": "2026-09-28", "bloco": "manha", "indice": "0", "titulo": titulo},
        follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje?data=2026-09-28#faixa-manha-0"

    texto = cliente.get("/hoje?data=2026-09-28").text
    assert 'id="faixa-manha-0"' in texto
    assert "feita" in texto.split('id="faixa-manha-0"')[0].rsplit("<li", 1)[1]
    assert 'aria-pressed="true"' in texto


def test_dia_futuro_nao_tem_circulo_e_recusa(cliente):
    texto = cliente.get("/hoje?data=2026-10-01").text
    assert 'class="circulo"' not in texto
    titulo = _faixa_real(date(2026, 10, 1), "manha", 0).titulo
    resposta = cliente.post("/hoje/faixa", data={
        "data": "2026-10-01", "bloco": "manha", "indice": "0", "titulo": titulo})
    assert resposta.status_code == 400
    assert "ainda nao chegou" in resposta.text


def test_pausa_nao_tem_circulo(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    # Cada faixa que nao e pausa tem um circulo; as pausas, nenhum.
    dia = cronograma.carregar().dia(SEG)
    nao_pausas = sum(1 for f in dia.faixas() if f.tipo != "pausa")
    assert texto.count('class="circulo"') == nao_pausas


def test_o_formulario_sugere_e_soma_sem_marcar(cliente):
    noite = cronograma.carregar().dia(SEG).noite
    for indice, faixa in enumerate(noite):
        if faixa.questoes and not faixa.opcional:
            cliente.post("/hoje/faixa", data={
                "data": "2026-09-28", "bloco": "noite", "indice": str(indice),
                "titulo": faixa.titulo})
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "Sugestão: Mínima (" in texto
    assert 'class="opcao minima sugerida"' in texto
    # Sugere, mas nao marca: nenhuma das quatro opcoes vem com checked.
    assert "checked" not in texto.split('class="metas"')[1].split("</fieldset>")[0]
    # A soma e a do nivel 1 da semana 1: 15 de Direito + 10 de Portugues.
    assert 'name="questoes_feitas" min="0" inputmode="numeric" value="25"' in texto


def test_depois_de_salvo_vale_o_que_eu_salvei(cliente):
    faixa = _faixa_real(SEG, "noite", 0)
    cliente.post("/hoje/faixa", data={
        "data": "2026-09-28", "bloco": "noite", "indice": "0", "titulo": faixa.titulo})
    cliente.post("/hoje/registrar", data={
        "data": "2026-09-28", "meta": "nao_fiz", "questoes_feitas": "3"})
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert 'inputmode="numeric" value="3"' in texto


# --- o comando ---------------------------------------------------------------

def test_radar_hoje_mostra_o_check(banco_temporario, plano, tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "cronograma.yml").write_text(MINI.read_text(encoding="utf-8"),
                                               encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(config_dir))
    _marcar(plano, TEORIA)

    saida = CliRunner().invoke(cli, ["hoje", "--data", "2026-09-28"])
    assert saida.exit_code == 0, saida.output
    linhas = saida.output.splitlines()
    (teoria,) = [l for l in linhas if "Aplicação da lei penal" in l and "Aprendizagem" not in l]
    assert teoria.startswith("[✓]")
    (anki,) = [l for l in linhas if "22:00-" in l]
    assert "[✓]" not in anki
