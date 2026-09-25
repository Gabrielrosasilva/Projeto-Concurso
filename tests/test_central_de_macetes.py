"""A Central de Macetes: o cartao por materia, e os selos que nao se misturam.

O macete aqui e escrito pelo teste, do jeito que o `radar gerar --importar`
o gravaria - nenhum texto de IA de verdade. O que se testa e a tela: a parte
de contagem, a parte de IA com fonte e procedencia, o link para as questoes
reais, e o aviso de lei alterada so quando o YAML diz.
"""
import json
import re
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar import leis
from radar.servico import cartoes, manual
from radar.web.app import app

from tests.test_gerador import _concurso, _real, _semear

CONFIG = Path(__file__).resolve().parent.parent / "config"

LEP_81 = dict(
    enunciado="Sobre a progressao de regime na Lei de Execucao Penal, assinale.",
    impressao="lep81",
)


@pytest.fixture
def config_propria(tmp_path, monkeypatch):
    """Uma copia do config de verdade, para o teste poder mexer no leis.yml."""
    pasta = tmp_path / "config"
    shutil.copytree(CONFIG, pasta)
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(pasta))
    leis.recarregar()
    yield pasta
    leis.recarregar()


@pytest.fixture
def acervo(banco_temporario, config_propria):
    _semear(
        _concurso(),
        _real(81, **LEP_81),
        _real(82),
        _real(83, anulada=True, resposta=None),
    )


def _macete(**mudancas):
    base = {
        "materia": "Lei de Execução Penal", "assunto": "Progressão",
        "regra": "Progressao exige requisito objetivo e subjetivo, os dois.",
        "fonte": "art. 112 da Lei 7.210/1984",
        "pegadinha": "a banca cita so um dos requisitos",
        "questoes": [{"codigo": "2019-q81", "prova_url": "https://fepese.test/sap2019.pdf",
                      "numero": 81, "impressao": "lep81", "ano": 2019}],
        "modelo": "Claude Code, importado manualmente, em 25/09/2026",
        "criado_em": "2026-09-25T15:00:00+00:00",
        "impressao": "a" * 32,
    }
    base.update(mudancas)
    return base


def _gravar_arquivo(*macetes):
    manual.caminho_dos_macetes().write_text(json.dumps(list(macetes)), "utf-8")


def _mudanca_da_lep(pasta, anos=(2019,)):
    arquivo = pasta / "leis.yml"
    texto = arquivo.read_text(encoding="utf-8")
    texto += (
        "\nmudancas:\n"
        "  - tema: Progressao de regime\n"
        "    lei: Lei 13.964/2019\n"
        "    o_que_mudou: novas fracoes no art. 112\n"
        f"    anos: [{', '.join(str(a) for a in anos)}]\n"
        "    marcas: [progressao]\n"
    )
    arquivo.write_text(texto, encoding="utf-8")
    leis.recarregar()


# --- o cartao ---------------------------------------------------------------

def test_a_base_conta_so_as_validas_e_diz_de_onde(acervo):
    (cartao,) = cartoes.cartoes()

    assert cartao.materia == "Lei de Execução Penal"
    assert cartao.questoes == 2                  # a anulada nao entra
    assert cartao.de_onde == "prova 2019"
    assert cartao.base_pequena


def test_macete_sem_fonte_ou_sem_procedencia_nao_aparece(acervo):
    _gravar_arquivo(
        _macete(),
        _macete(fonte="", impressao="b" * 32),
        _macete(modelo="", impressao="c" * 32),
    )

    (cartao,) = cartoes.cartoes()

    assert [m.impressao for m in cartao.macetes] == ["a" * 32]


# --- o aviso de lei alterada ------------------------------------------------

def test_sem_a_lista_conferida_nao_ha_aviso(acervo):
    _gravar_arquivo(_macete())
    assert not leis.mudancas_conferidas()
    assert cartoes.cartoes()[0].com_lei_mudada == 0


def test_com_a_lista_a_questao_e_o_macete_ganham_o_aviso(acervo, config_propria):
    _mudanca_da_lep(config_propria)
    _gravar_arquivo(_macete())

    (cartao,) = cartoes.cartoes()

    assert cartao.com_lei_mudada == 1            # so a 81 fala de progressao
    assert cartao.macetes[0].mudancas[0].lei == "Lei 13.964/2019"


def test_prova_fora_dos_anos_da_lista_nao_ganha_aviso(acervo, config_propria):
    """O ano da prova e escrito no YAML, e nao deduzido: prova de 2019 fora
    da lista fica sem aviso."""
    _mudanca_da_lep(config_propria, anos=(2013,))
    assert cartoes.cartoes()[0].com_lei_mudada == 0


# --- a tela -----------------------------------------------------------------

@pytest.fixture
def cliente(acervo):
    return TestClient(app)


def test_o_cartao_mostra_os_selos_separados(cliente):
    _gravar_arquivo(_macete())

    pagina = cliente.get("/macetes").text

    assert "Central de macetes" in pagina
    # Cada parte dentro do bloco da sua origem, e nunca no do outro.
    assert 'ds-bloco--calculado' in pagina and "Padrão da banca" in pagina
    assert 'ds-bloco--ia' in pagina and "Macete (IA)" in pagina
    assert "Fonte citada: art. 112 da Lei 7.210/1984" in pagina
    assert "Pegadinha recorrente" in pagina
    assert "importado manualmente" in pagina
    assert "/macetes/" + "a" * 32 + "/questoes" in pagina


def test_sem_macete_a_tela_diz_como_trazer_sem_api(cliente):
    pagina = cliente.get("/macetes").text
    assert "radar gerar --pedido --macetes" in pagina


def test_a_tela_avisa_que_a_lista_de_leis_nao_foi_conferida(cliente):
    assert "ainda não foi" in cliente.get("/macetes").text


def test_ver_questoes_reais_mostra_a_prova_com_o_gabarito(cliente, config_propria):
    _mudanca_da_lep(config_propria)
    _gravar_arquivo(_macete())

    pagina = cliente.get("/macetes/" + "a" * 32 + "/questoes").text

    assert 'ds-selo--oficial' in pagina and "Extraída da prova" in pagina
    assert "progressao de regime" in pagina.lower()
    assert re.search(r"Gabarito definitivo</span>\s*<b>a</b>", pagina)
    assert "⚠ A lei mudou depois desta prova" in pagina


def test_macete_que_nao_existe_da_404(cliente):
    assert cliente.get("/macetes/" + "f" * 32 + "/questoes").status_code == 404
