"""O cronograma: leitura, conferencia e a conta dos horarios."""
from datetime import date, time
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from radar import config, cronograma
from radar.cli import app

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
REAL = config.RAIZ / "config" / "cronograma.yml"


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


def _com_mudanca(tmp_path, mudar):
    """Grava uma copia do mini com uma alteracao, para testar a conferencia."""
    dados = yaml.safe_load(MINI.read_text(encoding="utf-8"))
    mudar(dados)
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return arquivo


# --- a conta dos horarios ----------------------------------------------------

def test_15_questoes_viram_40_minutos(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    primeira = dia.noite[0]
    assert primeira.duracao == 40          # 15 x 2,5 = 37,5, sobe para 40
    assert (primeira.inicio, primeira.fim) == (time(18, 0), time(18, 40))


def test_horarios_saem_da_soma_a_partir_do_bloco(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert [(f.inicio, f.fim) for f in dia.manha] == [
        (time(10, 15), time(11, 5)),
        (time(11, 5), time(11, 15)),
        (time(11, 15), time(11, 45)),
    ]
    # 40 + 10 + 25 (10 x 2,5) + 20
    assert dia.noite[-1].fim == time(19, 35)


def test_nivel_troca_a_rampa_e_empurra_os_horarios(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28), nivel=2)
    direito, pausa, portugues, correcao = dia.noite
    assert direito.questoes == 20
    assert (direito.inicio, direito.fim) == (time(18, 0), time(18, 50))
    assert pausa.inicio == time(18, 50)
    assert portugues.questoes == 10
    assert correcao.fim == time(19, 45)


def test_nivel_nao_mexe_no_plano_gravado(plano):
    cronograma.montar_dia(plano, date(2026, 9, 28), nivel=2)
    assert plano.dia(date(2026, 9, 28)).noite[0].questoes == 15


def test_nivel_que_nao_existe_da_erro(plano):
    with pytest.raises(cronograma.ErroNoCronograma, match="Nivel 7"):
        cronograma.montar_dia(plano, date(2026, 9, 28), nivel=7)


def test_min_por_questao_da_faixa_vence_o_padrao(plano):
    simulado = cronograma.montar_dia(plano, date(2026, 10, 3)).noite[0]
    assert (simulado.inicio, simulado.fim) == (time(18, 0), time(19, 30))
    assert simulado.cronometrado


def test_opcional_nao_entra_no_total(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert dia.pos22[-1].opcional
    assert dia.total_questoes == 25        # 15 + 10, sem as 10 do bonus


def test_minutos_de_estudo_sao_a_manha_sem_pausa(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert dia.minutos_de_estudo == 80


def test_campos_de_exibicao_chegam(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 29))
    assert dia.feriado == "Feriado de teste"
    revisao = dia.noite[0]
    assert (revisao.rotulo, revisao.origem) == ("R+7", "2026-09-22")
    assert plano.dia(date(2026, 9, 28)).manha[0].baralho == "[1] Direito Penal"


def test_domingo_e_fora_do_plano_devolvem_none(plano):
    assert cronograma.montar_dia(plano, date(2026, 10, 4)) is None   # domingo
    assert cronograma.montar_dia(plano, date(2026, 9, 1)) is None
    assert cronograma.montar_dia(plano, date(2026, 10, 1)) is None   # buraco


# --- faixa_atual -------------------------------------------------------------

def test_faixa_atual_no_meio_de_uma_faixa(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    atual, proxima = cronograma.faixa_atual(dia, time(10, 30))
    assert atual.titulo == "Aplicação da lei penal"
    assert proxima.tipo == "pausa"


def test_faixa_atual_entre_blocos(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    atual, proxima = cronograma.faixa_atual(dia, time(14, 0))
    assert atual is None
    assert proxima.inicio == time(18, 0)


def test_faixa_atual_depois_da_ultima(plano):
    dia = cronograma.montar_dia(plano, date(2026, 9, 28))
    assert cronograma.faixa_atual(dia, time(23, 30)) == (None, None)


# --- a conferencia do arquivo ------------------------------------------------

def test_data_repetida(tmp_path):
    def mudar(d):
        d["dias"][1]["data"] = "2026-09-28"
    with pytest.raises(cronograma.ErroNoCronograma, match="2026-09-28.*repetida"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_domingo_no_plano(tmp_path):
    def mudar(d):
        d["dias"][2]["data"] = "2026-10-04"
    with pytest.raises(cronograma.ErroNoCronograma, match="2026-10-04.*domingo"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_faixa_sem_duracao_nem_questoes(tmp_path):
    def mudar(d):
        del d["dias"][1]["manha"][0]["duracao"]
    with pytest.raises(cronograma.ErroNoCronograma,
                       match="2026-09-29.*nem questoes"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_tipo_desconhecido(tmp_path):
    def mudar(d):
        d["dias"][0]["manha"][0]["tipo"] = "teorai"
    with pytest.raises(cronograma.ErroNoCronograma, match="2026-09-28.*teorai"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_rampa_com_chave_que_nao_existe(tmp_path):
    def mudar(d):
        d["dias"][0]["noite"][0]["rampa"] = "constitucional"
    with pytest.raises(cronograma.ErroNoCronograma,
                       match="2026-09-28.*constitucional"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_horario_de_bloco_invalido(tmp_path):
    def mudar(d):
        d["blocos"]["noite"]["inicio"] = "18h"
    with pytest.raises(cronograma.ErroNoCronograma, match="noite.*18h"):
        cronograma.carregar(_com_mudanca(tmp_path, mudar))


def test_data_por_extenso():
    assert (cronograma.data_por_extenso(date(2026, 9, 28))
            == "segunda-feira, 28 de setembro de 2026")


# --- o arquivo de verdade ----------------------------------------------------

@pytest.fixture(scope="module")
def real():
    return cronograma.carregar(REAL)


def test_arquivo_real_cobre_o_ciclo(real):
    datas = [d.data for d in real.dias]
    assert len(datas) == 36
    assert datas[0] == date(2026, 9, 28)
    assert datas[-1] == date(2026, 11, 7)
    assert all(d.weekday() != cronograma.DOMINGO for d in datas)


def test_arquivo_real_total_de_questoes(real):
    total = sum(cronograma.montar_dia(real, d.data).total_questoes
                for d in real.dias)
    assert total == 1690


def test_arquivo_real_horarios_conferidos(real):
    assert cronograma.montar_dia(real, date(2026, 9, 28)).noite[-1].fim == time(19, 35)
    assert cronograma.montar_dia(real, date(2026, 10, 28)).noite[-1].fim == time(21, 15)
    simulado = cronograma.montar_dia(real, date(2026, 10, 10)).noite[0]
    assert simulado.tipo == "simulado"
    assert (simulado.inicio, simulado.fim) == (time(18, 0), time(19, 30))


# --- o comando ---------------------------------------------------------------

@pytest.fixture
def config_mini(tmp_path, monkeypatch):
    (tmp_path / "cronograma.yml").write_text(MINI.read_text(encoding="utf-8"),
                                             encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))


def test_comando_hoje_mostra_o_dia(config_mini):
    saida = CliRunner().invoke(app, ["hoje", "--data", "2026-09-28"])
    assert saida.exit_code == 0, saida.output
    assert "Segunda-feira, 28 de setembro de 2026" in saida.output
    assert "18:00-18:40" in saida.output
    assert "Total do dia: 25 questões" in saida.output
    assert "Mínima: Só o Anki." in saida.output


def test_comando_hoje_domingo_e_fora_do_ciclo(config_mini):
    runner = CliRunner()
    assert "Domingo é descanso total." in runner.invoke(
        app, ["hoje", "--data", "2026-10-04"]).output
    assert "começa em 28/09/2026" in runner.invoke(
        app, ["hoje", "--data", "2026-09-01"]).output
    assert "terminou em 03/10/2026" in runner.invoke(
        app, ["hoje", "--data", "2026-12-01"]).output
