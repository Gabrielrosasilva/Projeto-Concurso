"""O diario do cronograma: registrar o dia, recusar o que nao faz sentido, e
a copia em data/registro_estudo.json."""
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete
from typer.testing import CliRunner

from radar import acervo, cronograma, servico
from radar.cli import app
from radar.db import sessao
from radar.models import RegistroDoDia
from radar.servico.cronograma import RegistroInvalido, registrar, registros

from tests.test_espacada import _questao, _respondi
from tests.test_foco import _concurso

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
# O mini tem 28/09, 29/09 e 03/10. "Hoje", para os testes, e o ultimo deles.
HOJE = date(2026, 10, 3)
SEG = date(2026, 9, 28)


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


def _marcar(plano, data=SEG, meta="ideal", *args, **kwargs):
    return registrar(data, meta, *args, plano=plano, hoje=HOJE, **kwargs)


# --- criar e atualizar -------------------------------------------------------

def test_cria_o_registro(banco_temporario, plano):
    _marcar(plano, SEG, "ideal", "rendeu")
    (r,) = registros(SEG, SEG).values()
    assert (r.data, r.meta, r.anotacao) == (SEG, "ideal", "rendeu")
    # O registro nao guarda mais numero: o do dia e calculado (Etapa 1C).
    assert (r.questoes_feitas, r.acertos) == (None, None)
    assert r.anotado_em.tzinfo is not None


def test_salvar_a_meta_nao_apaga_a_copia_antiga(banco_temporario, plano):
    """O 28/09 tem "31 questoes, 13 acertos" gravado. Salvar a meta de novo
    nao pode apagar isso: a 1D confere essas copias antes de qualquer coisa."""
    with sessao() as s:
        s.add(RegistroDoDia(data=SEG, meta="reduzida", questoes_feitas=31,
                            acertos=13))
    _marcar(plano, SEG, "minima")
    (r,) = registros(SEG, SEG).values()
    assert (r.meta, r.questoes_feitas, r.acertos) == ("minima", 31, 13)


def test_marcar_de_novo_atualiza_em_vez_de_duplicar(banco_temporario, plano):
    _marcar(plano, SEG, "ideal", "primeira")
    _marcar(plano, SEG, "reduzida", "segunda")
    achados = registros(date(2026, 9, 1), date(2026, 12, 31))
    assert list(achados) == [SEG]
    assert achados[SEG].meta == "reduzida"
    assert achados[SEG].anotacao == "segunda"


def test_registros_respeita_o_intervalo(banco_temporario, plano):
    _marcar(plano, SEG)
    _marcar(plano, date(2026, 10, 3), "minima")
    assert list(registros(SEG, date(2026, 9, 30))) == [SEG]


def test_hoje_pode_ser_marcado(banco_temporario, plano):
    _marcar(plano, HOJE, "nao_fiz")
    assert registros(HOJE, HOJE)[HOJE].meta == "nao_fiz"


# --- as recusas --------------------------------------------------------------

def test_recusa_meta_que_nao_existe(banco_temporario, plano):
    with pytest.raises(RegistroInvalido, match="Meta 'otima'"):
        registrar(SEG, "otima", plano=plano, hoje=HOJE)


def test_recusa_data_futura(banco_temporario, plano):
    with pytest.raises(RegistroInvalido, match="03/10/2026 ainda não chegou"):
        registrar(date(2026, 10, 3), "ideal", plano=plano, hoje=SEG)


def test_recusa_data_fora_do_plano(banco_temporario, plano):
    with pytest.raises(RegistroInvalido, match="30/09/2026 não está no cronograma"):
        _marcar(plano, date(2026, 9, 30))


def test_recusa_nao_grava_nada(banco_temporario, plano):
    with pytest.raises(RegistroInvalido):
        _marcar(plano, SEG, "otima")
    assert registros(SEG, SEG) == {}


# --- a copia em JSON ---------------------------------------------------------

def _apagar_do_banco():
    with sessao() as s:
        s.execute(delete(RegistroDoDia))


def test_exportar_e_importar_ida_e_volta(banco_temporario, plano, tmp_path):
    arquivo = tmp_path / "registro_estudo.json"
    with sessao() as s:
        # Um registro antigo, com a copia do numero: ela continua indo e
        # voltando pelo JSON, mesmo sem aparecer mais na tela.
        s.add(RegistroDoDia(data=SEG, meta="ideal", questoes_feitas=25,
                            acertos=18, anotacao="rendeu"))
    _marcar(plano, HOJE, "minima")

    assert acervo.exportar_registros(arquivo) == 2
    linhas = json.loads(arquivo.read_text(encoding="utf-8"))
    assert [l["data"] for l in linhas] == ["2026-09-28", "2026-10-03"]
    assert linhas[0]["acertos"] == 18

    _apagar_do_banco()
    assert acervo.importar_registros(arquivo) == 2
    voltou = registros(SEG, HOJE)
    assert voltou[SEG].anotacao == "rendeu"
    assert voltou[HOJE].meta == "minima"
    # Rodar de novo nao muda nada.
    assert acervo.importar_registros(arquivo) == 0


def _linha(data: str, meta: str, anotado_em: datetime) -> dict:
    return {"data": data, "meta": meta, "questoes_feitas": None,
            "acertos": None, "anotacao": None,
            "anotado_em": anotado_em.isoformat()}


def test_importar_vale_o_mais_recente(banco_temporario, plano, tmp_path):
    _marcar(plano, SEG, "ideal")
    no_banco = registros(SEG, SEG)[SEG].anotado_em
    arquivo = tmp_path / "registro_estudo.json"

    # Arquivo mais velho que o banco: o banco fica.
    arquivo.write_text(json.dumps([_linha("2026-09-28", "nao_fiz",
                                          datetime(2020, 1, 1, tzinfo=timezone.utc))]),
                       encoding="utf-8")
    assert acervo.importar_registros(arquivo) == 0
    assert registros(SEG, SEG)[SEG].meta == "ideal"

    # Arquivo mais novo: ele vence.
    arquivo.write_text(json.dumps([_linha("2026-09-28", "minima",
                                          datetime(2099, 1, 1, tzinfo=timezone.utc))]),
                       encoding="utf-8")
    assert acervo.importar_registros(arquivo) == 1
    r = registros(SEG, SEG)[SEG]
    assert r.meta == "minima"
    assert r.anotado_em > no_banco


def test_exportar_vale_o_mais_recente_e_guarda_o_que_o_banco_nao_tem(
        banco_temporario, plano, tmp_path):
    arquivo = tmp_path / "registro_estudo.json"
    arquivo.write_text(json.dumps([
        _linha("2026-09-28", "minima", datetime(2099, 1, 1, tzinfo=timezone.utc)),
        _linha("2026-09-29", "reduzida", datetime(2020, 1, 1, tzinfo=timezone.utc)),
    ]), encoding="utf-8")
    _marcar(plano, SEG, "ideal")          # mais velho que o do arquivo
    _marcar(plano, HOJE, "nao_fiz")       # so o banco tem

    assert acervo.exportar_registros(arquivo) == 3
    por_data = {l["data"]: l["meta"]
                for l in json.loads(arquivo.read_text(encoding="utf-8"))}
    assert por_data == {"2026-09-28": "minima", "2026-09-29": "reduzida",
                        "2026-10-03": "nao_fiz"}


def test_apagar_tira_do_banco_e_do_arquivo(banco_temporario, plano):
    _marcar(plano, SEG)
    acervo.exportar_registros()
    assert servico.cronograma.apagar(SEG)
    assert registros(SEG, SEG) == {}
    assert json.loads(acervo.caminho_dos_registros().read_text(encoding="utf-8")) == []
    assert not servico.cronograma.apagar(SEG)


# --- o diario nao mede nada --------------------------------------------------

def test_registrar_o_dia_nao_muda_o_desempenho(banco_temporario, plano):
    with sessao() as s:
        s.add(_concurso())
    certa, errada = _questao(1), _questao(2)
    _respondi(certa, True, date(2026, 9, 20))
    _respondi(errada, False, date(2026, 9, 20))

    antes = servico.desempenho()
    evolucao_antes = servico.evolucao()
    _marcar(plano, SEG, "ideal")
    assert servico.desempenho() == antes
    assert servico.evolucao() == evolucao_antes
    assert antes[0].respondidas == 2


# --- o comando ---------------------------------------------------------------

def test_comando_marca_e_mostra(banco_temporario, tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "cronograma.yml").write_text(MINI.read_text(encoding="utf-8"),
                                               encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(servico.cronograma, "hoje_local", lambda: HOJE)

    runner = CliRunner()
    saida = runner.invoke(app, ["hoje", "--data", "2026-09-28", "--marcar", "ideal",
                                "--feitas", "25", "--acertos", "18",
                                "--minutos", "50"], env={"COLUMNS": "200"})
    assert saida.exit_code == 0, saida.output
    assert "Anotado como estudo extra." in saida.output
    assert "Marcado." in saida.output
    # O numero digitado virou estudo extra, e o "Fiz hoje" o conta como anotado.
    assert "Fiz hoje: 25 questões = 18 acertos + 7 erros" in saida.output
    (extra,) = servico.extra.do_dia(SEG)
    assert (extra.questoes, extra.acertos, extra.minutos, extra.onde) == (
        25, 18, 50, "qconcursos")
    (r,) = registros(SEG, SEG).values()
    assert (r.meta, r.questoes_feitas, r.acertos) == ("ideal", None, None)

    # Sem --marcar, mostra o que ja esta anotado.
    assert "Como foi:" in runner.invoke(app, ["hoje", "--data", "2026-09-28"]).output

    recusa = runner.invoke(app, ["hoje", "--data", "2026-09-28", "--marcar", "otima"])
    assert recusa.exit_code == 1
    assert "Não marquei" in recusa.output

    # Questao sem minutos nao vira estudo extra: a regra do extra continua.
    sem_tempo = runner.invoke(app, ["hoje", "--data", "2026-09-28", "--feitas", "10"])
    assert sem_tempo.exit_code == 1
    assert "Faltou --minutos" in sem_tempo.output
    assert len(servico.extra.do_dia(SEG)) == 1


def test_tabela_nova_entra_em_banco_antigo(tmp_path, monkeypatch):
    """Banco criado antes da tabela existir: criar_tabelas a cria sozinho."""
    from sqlalchemy import create_engine, inspect, text

    from radar import db

    arquivo = tmp_path / "antigo.db"
    motor = create_engine(f"sqlite:///{arquivo}")
    with motor.begin() as c:
        c.execute(text("CREATE TABLE simulados (id INTEGER PRIMARY KEY)"))
    motor.dispose()

    monkeypatch.setenv("RADAR_DATABASE_URL", f"sqlite:///{arquivo}")
    # O banco sem versao migra sozinho, e a migracao exporta os JSON versionados
    # e copia o banco para <dados>/copias. Sem apontar os dados para o tmp_path,
    # este teste sobrescrevia data/questoes_geradas.json com o [] do banco
    # vazio - foi assim que as 50 geradas sumiram do arquivo duas vezes.
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    db.resetar_engine()
    try:
        db.criar_tabelas()
        colunas = {c["name"] for c in inspect(db.get_engine()).get_columns(
            "registros_de_estudo")}
        assert {"data", "meta", "questoes_feitas", "acertos", "anotacao",
                "anotado_em"} <= colunas
    finally:
        db.resetar_engine()
