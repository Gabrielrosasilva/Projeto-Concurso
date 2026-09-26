"""O Plano B: o dia corrido, so com o essencial e questoes de prova do tema.

Le o config/cronograma.yml de verdade, como os testes da tela Hoje: os
artigos-chave e o bloco `plano_b` sao dado do plano, e o arquivo real e o
dado fixo mais fiel que ha. As regras de validacao usam um YAML de teste.
"""
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import acervo, cronograma, servico
from radar.cli import app as cli
from radar.servico.cronograma import RegistroInvalido, ativar_plano_b, estado_do_dia
from radar.util import fuso_local
from radar.web.app import app

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
QUARTA = date(2026, 10, 28)
SABADO = date(2026, 10, 31)
DOMINGO = date(2026, 11, 1)
DEPOIS = date(2026, 11, 2)      # "hoje" nos testes do servico: 28/10 e 31/10 ja passaram


@pytest.fixture(scope="module")
def plano():
    return cronograma.carregar()


# --- a funcao pura --------------------------------------------------------------

def test_30_min_e_o_essencial_de_chave_e_8_questoes_sem_portugues(plano):
    dia = cronograma.montar_plano_b(plano, QUARTA, 30, 5)
    assert [f.tipo for f in dia.plano_b] == ["essencial", "questoes"]
    essencial, questoes = dia.plano_b
    assert [a.artigos for a in essencial.artigos] == ["LEP art. 112", "LEP art. 118"]
    assert essencial.duracao == 10
    assert essencial.link == "https://www.planalto.gov.br/ccivil_03/leis/l7210.htm"
    assert questoes.questoes == 8
    assert questoes.filtro == "Execução Penal > regimes de cumprimento, progressão e regressão"
    assert questoes.materia == "Lei de Execução Penal"
    assert dia.total_questoes == 8
    # Sem horario: o Plano B e "quando der".
    assert all(f.inicio is None for f in dia.plano_b)


def test_1_hora_soma_o_apoio_15_questoes_e_4_de_portugues_opcional(plano):
    dia = cronograma.montar_plano_b(plano, QUARTA, 60, 5)
    essencial, direito, portugues = dia.plano_b
    assert [a.artigos for a in essencial.artigos] == [
        "LEP art. 112", "LEP art. 118", "LEP arts. 110 e 111",
        "LEP arts. 113 a 115", "LEP art. 117"]
    assert essencial.duracao == 15
    assert direito.questoes == 15
    assert (portugues.questoes, portugues.opcional) == (4, True)
    assert portugues.materia == "Língua Portuguesa"
    # O Portugues e "se sobrar tempo": nao entra no total.
    assert dia.total_questoes == 15


def test_sabado_e_refazer_20_questoes_erradas(plano):
    (faixa,) = cronograma.montar_plano_b(plano, SABADO, 30).plano_b
    assert faixa.questoes == 20
    assert "erradas" in faixa.titulo
    assert faixa.detalhe == plano.plano_b.sabado


def test_o_aviso_do_essencial_vai_para_a_faixa(plano):
    com_aviso = [d for d in plano.dias if d.essencial and d.essencial.aviso]
    assert com_aviso
    (essencial, *_) = cronograma.montar_plano_b(plano, com_aviso[0].data, 30).plano_b
    assert essencial.aviso == com_aviso[0].essencial.aviso


def test_nenhum_anki_nem_pausa_no_plano_b(plano):
    for dia in plano.dias:
        for minutos in plano.plano_b.opcoes:
            for faixa in cronograma.montar_plano_b(plano, dia.data, minutos).plano_b:
                assert faixa.tipo not in ("anki", "pausa")
                assert "Anki" not in faixa.titulo
                assert "Anki" not in (faixa.detalhe or "")


def test_domingo_nao_tem_plano_b(plano):
    assert cronograma.montar_plano_b(plano, DOMINGO, 30) is None


def test_tempo_que_nao_existe(plano):
    with pytest.raises(cronograma.ErroNoCronograma, match="45 min"):
        cronograma.montar_plano_b(plano, QUARTA, 45)


# --- a leitura e a validacao ----------------------------------------------------

def _yaml_com(tmp_path, mexer):
    dados = yaml.safe_load(MINI.read_text(encoding="utf-8"))
    dados["plano_b"] = {
        "opcoes": [{"minutos": 30, "essencial_minutos": 10, "questoes_direito": 8,
                    "questoes_portugues": 0, "com_apoio": False}],
        "sabado": "Refaça as erradas.", "sabado_questoes": 20,
    }
    for dia in dados["dias"]:
        if date.fromisoformat(dia["data"]).weekday() < 5:
            dia["essencial"] = {"chave": [{"artigos": "CP art. 1º", "porque": "Legalidade."}]}
    mexer(dados)
    arquivo = tmp_path / "cronograma.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return arquivo


def test_o_yaml_de_teste_completo_carrega(tmp_path):
    plano = cronograma.carregar(_yaml_com(tmp_path, lambda d: None))
    assert plano.plano_b.opcoes[30].questoes_direito == 8


@pytest.mark.parametrize("mexer, mensagem", [
    (lambda d: d["plano_b"]["opcoes"][0].pop("questoes_direito"), "questoes_direito"),
    (lambda d: d["plano_b"].pop("sabado_questoes"), "sabado_questoes"),
    (lambda d: d["dias"][0].pop("essencial"), "falta `essencial`"),
    (lambda d: d["dias"][0]["essencial"].pop("chave"), "falta a lista `chave`"),
    (lambda d: d["dias"][0]["essencial"]["chave"][0].pop("porque"), "sem `porque`"),
])
def test_campo_que_falta_e_erro_claro(tmp_path, mexer, mensagem):
    with pytest.raises(cronograma.ErroNoCronograma, match=mensagem):
        cronograma.carregar(_yaml_com(tmp_path, mexer))


def test_sem_bloco_plano_b_o_essencial_e_opcional():
    """O mini dos outros testes nao tem Plano B, e continua carregando."""
    assert cronograma.carregar(MINI).plano_b is None


# --- ativar, desativar, persistir -----------------------------------------------

def test_ativar_desativar_e_persistir(banco_temporario, plano):
    ativar_plano_b(QUARTA, 30, plano=plano, hoje=DEPOIS)
    assert estado_do_dia(QUARTA).plano_b == 30
    ativar_plano_b(QUARTA, 60, plano=plano, hoje=DEPOIS)
    assert estado_do_dia(QUARTA).plano_b == 60

    acervo.exportar_estados()
    ativar_plano_b(QUARTA, None, plano=plano, hoje=DEPOIS)
    assert estado_do_dia(QUARTA).plano_b is None
    # O arquivo guardou o 60; o banco, mais novo, diz "nenhum" - vale o banco.
    assert acervo.importar_estados() == 0
    assert estado_do_dia(QUARTA).plano_b is None


def test_futuro_e_recusado(banco_temporario, plano):
    with pytest.raises(RegistroInvalido, match="ainda nao chegou"):
        ativar_plano_b(QUARTA, 30, plano=plano, hoje=date(2026, 10, 27))
    assert estado_do_dia(QUARTA) is None


@pytest.mark.parametrize("data, minutos, mensagem", [
    (DOMINGO, 30, "Domingo"),
    (QUARTA, 45, "45 min"),
])
def test_o_que_nao_se_ativa(banco_temporario, plano, data, minutos, mensagem):
    with pytest.raises(RegistroInvalido, match=mensagem):
        ativar_plano_b(data, minutos, plano=plano, hoje=DEPOIS)


# --- a tela ------------------------------------------------------------------------

@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    momento = datetime(2026, 10, 30, 12, 0, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: momento)
    return TestClient(app)


def _bloco_do_plano_b(texto):
    return texto.split('class="ds-cartao bloco-dia bloco-plano_b"')[1].split("</section>")[0]


def test_o_botao_oferece_30_min_e_1_hora(cliente):
    texto = cliente.get("/hoje?data=2026-10-28").text
    assert "🆘 Ativar Plano B" in texto
    assert "Quanto tempo você tem?" in texto
    assert 'name="minutos" value="30">30 min</button>' in texto
    assert 'name="minutos" value="60">1 hora</button>' in texto


def test_ativado_a_tela_mostra_so_o_plano_b(cliente):
    resposta = cliente.post("/hoje/plano-b", data={"data": "2026-10-28", "minutos": "30"},
                            follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje?data=2026-10-28"

    texto = cliente.get("/hoje?data=2026-10-28").text
    assert "🆘 Plano B ativado — dia corrido: sem teoria, só o essencial" in texto
    assert "O dia conta como Mínima e a sua sequência continua." in texto
    assert "Plano B — o mínimo de hoje" in texto
    assert "~30 min" in texto and "quando der" in texto
    assert "↩ Voltar ao plano completo" in texto
    assert "Se o dia apertar" not in texto
    assert "Manhã — estudo" not in texto
    bloco = _bloco_do_plano_b(texto)
    assert "LEP art. 112" in bloco and "1º" in bloco and "2º" in bloco
    assert "8 questões" in bloco
    assert "Anki" not in bloco
    # A Minima vem marcada - ainda sugestao: nada foi salvo.
    assert 'value="minima" checked' in texto
    assert servico.cronograma.registros(QUARTA, QUARTA) == {}


def test_os_checks_valem_no_plano_b(cliente):
    cliente.post("/hoje/plano-b", data={"data": "2026-10-28", "minutos": "30"})
    plano = cronograma.carregar()
    faixa = cronograma.montar_plano_b(plano, QUARTA, 30).plano_b[1]
    resposta = cliente.post("/hoje/faixa", data={
        "data": "2026-10-28", "bloco": "plano_b", "indice": "1", "titulo": faixa.titulo},
        follow_redirects=False)
    assert resposta.headers["location"] == "/hoje?data=2026-10-28#faixa-plano_b-1"
    texto = cliente.get("/hoje?data=2026-10-28").text
    assert "Sugestão: Mínima (1 de 2 faixas)" in texto
    assert 'inputmode="numeric" value="8"' in texto


def test_voltar_ao_plano_completo(cliente):
    cliente.post("/hoje/plano-b", data={"data": "2026-10-28", "minutos": "60"})
    cliente.post("/hoje/plano-b", data={"data": "2026-10-28", "minutos": ""})
    texto = cliente.get("/hoje?data=2026-10-28").text
    assert "Plano B ativado" not in texto
    assert "Manhã — estudo" in texto
    assert "🆘 Ativar Plano B" in texto


def test_dia_futuro_nao_tem_botao_e_recusa(cliente):
    assert "Ativar Plano B" not in cliente.get("/hoje?data=2026-10-31").text
    resposta = cliente.post("/hoje/plano-b", data={"data": "2026-10-31", "minutos": "30"})
    assert resposta.status_code == 400
    assert "ainda nao chegou" in resposta.text


def test_domingo_nao_tem_botao(cliente):
    assert "Ativar Plano B" not in cliente.get("/hoje?data=2026-10-25").text


def test_o_cartao_da_home_diz_plano_b(cliente, monkeypatch):
    momento = datetime(2026, 10, 28, 12, 0, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: momento)
    cliente.post("/hoje/plano-b", data={"data": "2026-10-28", "minutos": "30"})
    assert "Hoje: Plano B (30 min)" in cliente.get("/").text


# --- o comando -----------------------------------------------------------------

def test_radar_hoje_plano_b(banco_temporario):
    saida = CliRunner().invoke(cli, ["hoje", "--data", "2026-10-28", "--plano-b", "30"])
    assert saida.exit_code == 0, saida.output
    assert "Plano B (30 min)" in saida.output
    assert "LEP art. 112" in saida.output and "8 questões" in saida.output
    assert "Anki" not in saida.output
    assert "Acentuação" not in saida.output          # Portugues so no de 1 hora

    recusa = CliRunner().invoke(cli, ["hoje", "--data", "2026-10-28", "--plano-b", "45"])
    assert recusa.exit_code == 1
