"""A migracao da Etapa 2: copia antes, nenhuma linha perdida, e desfazer.

O banco "antigo" e montado aqui com o modelo de hoje e depois desmontado ate
o formato de antes da Etapa 2: sem as tabelas novas e sem as colunas novas.
O programa do edital vem da fixture, e nao do acervo (que o teste nao tem).
"""
import sqlite3
from datetime import date
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select

from radar import db, edital_programa, foco, migracoes
from radar.models import (
    Base,
    Classificacao,
    Concurso,
    ErroAnotado,
    QuestaoDeProva,
    QuestaoGerada,
)
from radar.servico import conteudos

from tests.test_foco import _concurso, _questao

PROGRAMA = edital_programa.ler_programa(
    (Path(__file__).parent / "fixtures" / "provas" / "edital_sap_2019_programa.txt")
    .read_text(encoding="utf-8"))

NOVAS_TABELAS = ("conteudos", "classificacoes", "versao_do_banco")
NOVAS_COLUNAS = (("questoes", "evidencia"), ("questoes_geradas", "conteudo"),
                 ("erros_anotados", "conteudo"), ("estudos_extras", "conteudo"))


@pytest.fixture
def banco_antigo(tmp_path, monkeypatch):
    """Um radar.db do jeito que estava antes da Etapa 2, com dado dentro."""
    arquivo = tmp_path / "radar.db"
    monkeypatch.setenv("RADAR_DATABASE_URL", f"sqlite:///{arquivo}")
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(foco, "programa_do_alvo", lambda: PROGRAMA)
    db.resetar_engine()

    motor = create_engine(f"sqlite:///{arquivo}")
    Base.metadata.create_all(motor)
    motor.dispose()
    # Com o banco ainda sem nada de versao, o `criar_tabelas` trataria isto
    # como banco velho e migraria antes da hora: os dados entram direto.
    db._versao_conferida = True
    with db.sessao() as s:
        s.add(_concurso())
        for n in range(1, 4):
            s.add(_questao(n, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(QuestaoGerada(modo="do_zero", materia="Aplicação da lei penal (arts. 1º a 12)",
                            enunciado="?", alternativas={"a": "x"}, resposta="a",
                            impressao="g1", modelo="m"))
        s.add(QuestaoGerada(modo="do_zero", materia="Algo que não existe",
                            enunciado="?", alternativas={"a": "x"}, resposta="a",
                            impressao="g2", modelo="m"))
        s.add(ErroAnotado(data_estudo=date(2026, 9, 28),
                          materia="Direito Processo Penal", motivo="nao_sabia",
                          regra="A regra certa."))
    db.resetar_engine()

    with closing(sqlite3.connect(arquivo)) as conexao:
        for tabela in NOVAS_TABELAS:
            conexao.execute(f"DROP TABLE {tabela}")
        conexao.execute("DROP INDEX ix_questoes_evidencia")
        for tabela, coluna in NOVAS_COLUNAS:
            conexao.execute(f"ALTER TABLE {tabela} DROP COLUMN {coluna}")
        conexao.commit()
    yield arquivo
    db.resetar_engine()


def _tabelas(arquivo) -> dict[str, int]:
    with closing(sqlite3.connect(arquivo)) as conexao:
        nomes = [n for (n,) in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        return {n: conexao.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
                for n in nomes}


def test_o_banco_antigo_esta_mesmo_no_formato_antigo(banco_antigo):
    assert not set(NOVAS_TABELAS) & set(_tabelas(banco_antigo))
    assert migracoes.versao(db.get_engine()) == 0


def test_migrar_mantem_as_contagens_e_cria_o_que_falta(banco_antigo):
    antes = _tabelas(banco_antigo)

    relatorio = migracoes.migrar()

    depois = _tabelas(banco_antigo)
    assert {t: depois[t] for t in antes} == antes          # nenhuma linha a menos
    assert relatorio.perdidas == {}
    assert (relatorio.de, relatorio.para) == (0, migracoes.VERSAO_ATUAL)
    assert relatorio.antes == antes
    assert depois["versao_do_banco"] == 1                    # uma linha so
    assert depois["conteudos"] == 11 + 85 + 2                # edital + fora dele
    with db.sessao() as s:
        assert set(s.scalars(select(QuestaoDeProva.evidencia))) == {"alvo"}
        ligadas = {g.impressao: g.conteudo for g in s.scalars(select(QuestaoGerada))}
        erro = s.scalar(select(ErroAnotado))
    # O titulo da faixa vale a materia da faixa; o que nao casa fica sem no.
    assert ligadas == {"g1": "Direito Penal", "g2": None}
    assert erro.conteudo == "Direito Processual Penal"      # pelo sinonimo
    assert erro.materia == "Direito Processo Penal"         # o texto ficou


def test_a_copia_e_feita_antes(banco_antigo):
    relatorio = migracoes.migrar()

    copia = relatorio.copia / banco_antigo.name
    assert relatorio.copia.parent == banco_antigo.parent / "copias"
    assert relatorio.copia.name.startswith(f"migracao-v0-para-v{migracoes.VERSAO_ATUAL}-")
    # A copia e o banco de ANTES: sem as tabelas novas.
    assert not set(NOVAS_TABELAS) & set(_tabelas(copia))


def test_migrar_duas_vezes_nao_duplica(banco_antigo):
    migracoes.migrar()
    uma_vez = _tabelas(banco_antigo)
    copias = list((banco_antigo.parent / "copias").iterdir())

    relatorio = migracoes.migrar()

    assert not relatorio.mudou
    assert _tabelas(banco_antigo) == uma_vez
    assert list((banco_antigo.parent / "copias").iterdir()) == copias


def test_qualquer_comando_migra_sozinho(banco_antigo):
    """O `criar_tabelas` confere a versao na primeira vez: lembrar de rodar
    `radar migrar` depois do pull nao e requisito."""
    db.criar_tabelas()
    assert migracoes.versao(db.get_engine()) == migracoes.VERSAO_ATUAL
    assert migracoes.ultima_copia() is not None


def test_desfazer_devolve_o_banco_como_era(banco_antigo):
    antes = _tabelas(banco_antigo)
    migracoes.migrar()

    usada = migracoes.desfazer()

    assert usada.name.startswith(f"migracao-v0-para-v{migracoes.VERSAO_ATUAL}-")
    assert _tabelas(banco_antigo) == antes
    # E o banco migrado tambem foi guardado: desfazer por engano tem volta.
    assert any(p.name.startswith("antes-de-desfazer-")
               for p in (banco_antigo.parent / "copias").iterdir())


def test_passo_que_apaga_linha_e_desfeito(banco_antigo, monkeypatch):
    antes = _tabelas(banco_antigo)

    def passo_ruim():
        with db.sessao() as s:
            s.delete(s.scalars(select(Concurso)).first())
    monkeypatch.setitem(migracoes.PASSOS, migracoes.VERSAO_ATUAL, ("apaga", passo_ruim))

    with pytest.raises(migracoes.MigracaoFalhou, match="concursos"):
        migracoes.migrar()
    assert _tabelas(banco_antigo) == antes


def test_banco_novo_nasce_na_versao_atual_sem_copia(banco_temporario, tmp_path):
    assert migracoes.versao(db.get_engine()) == migracoes.VERSAO_ATUAL
    assert not (tmp_path / "copias").exists()
    assert conteudos.nos() == []


def test_o_comando_mostra_o_antes_e_depois(banco_antigo):
    from typer.testing import CliRunner
    from radar.cli import app

    runner = CliRunner()
    saida = runner.invoke(app, ["migrar"], env={"COLUMNS": "200"})
    assert saida.exit_code == 0, saida.output
    assert f"Migração da versão 0 para a {migracoes.VERSAO_ATUAL}" in saida.output
    assert "Nenhuma linha perdida" in saida.output

    assert "Nada a migrar" in runner.invoke(app, ["migrar"]).output
    desfeito = runner.invoke(app, ["migrar", "--desfazer"], env={"COLUMNS": "200"})
    assert "Banco devolvido" in desfeito.output
    assert migracoes.versao(db.get_engine()) == 0


def test_a_classificacao_pela_impressao_vira_chave_no_passo_3(banco_temporario):
    """O banco da versao 2 guardava a classificacao pela impressao do
    enunciado. Na 3, cada linha vira a chave da questao inteira - e o
    enunciado repetido vira pendente em cada questao, sem chute."""
    from sqlalchemy import text

    from radar.servico import classificacoes

    conteudos.semear(programa=PROGRAMA)
    imputabilidade = "Direito Penal > Imputabilidade penal"
    with db.sessao() as s:
        s.add(QuestaoDeProva(prova_url="p.pdf", numero=1, enunciado="Único?",
                             alternativas={"a": "x"}, impressao="unica"))
        for n, letra in ((2, "x"), (3, "y")):
            s.add(QuestaoDeProva(prova_url="p.pdf", numero=n, enunciado="É correto",
                                 alternativas={"a": letra}, impressao="repetida"))
    with db.get_engine().begin() as conexao:
        conexao.execute(text("DROP TABLE classificacoes"))
        conexao.execute(text(
            "CREATE TABLE classificacoes (id INTEGER PRIMARY KEY, impressao VARCHAR(32), "
            "conteudo VARCHAR(800), principal BOOLEAN, status VARCHAR(10), trecho TEXT, "
            "item_do_edital TEXT, dispositivo VARCHAR(200), tipo_de_questao VARCHAR(60), "
            "pegadinha TEXT, procedencia VARCHAR(120), classificada_em DATETIME, "
            "conferida_em DATETIME)"))
        conexao.execute(text(
            "INSERT INTO classificacoes (impressao, conteudo, principal, status, "
            "procedencia, classificada_em) VALUES "
            "('unica', :no, 1, 'completa', 'manual', '2026-10-01 10:00:00'), "
            "('repetida', :no, 1, 'completa', 'manual', '2026-10-01 10:00:00')"),
            {"no": imputabilidade})
        conexao.execute(text("UPDATE versao_do_banco SET versao = 2"))

    relatorio = migracoes.migrar()

    assert (relatorio.de, relatorio.para) == (2, migracoes.VERSAO_ATUAL)
    assert (relatorio.antes["classificacoes"], relatorio.depois["classificacoes"]) == (2, 3)
    with db.sessao() as s:
        por_chave = {c.chave: c for c in s.scalars(select(Classificacao))}
    unica = por_chave[classificacoes.chave_da_questao("Único?", {"a": "x"})]
    assert (unica.conteudo, unica.status) == (imputabilidade, "completa")
    for letra in "xy":
        c = por_chave[classificacoes.chave_da_questao("É correto", {"a": letra})]
        assert (c.conteudo, c.status) == ("Direito Penal", "pendente")


def test_a_chave_da_base_das_geradas_chega_no_passo_5(banco_temporario):
    """F3: a variacao antiga ganha a chave da base quando a impressao aponta
    uma questao so, e o arquivo versionado leva a coluna nova."""
    import json

    from sqlalchemy import text

    from radar import acervo
    from radar.questoes import chave_da_questao

    with db.sessao() as s:
        s.add(QuestaoDeProva(prova_url="p.pdf", numero=1, enunciado="Única?",
                             alternativas={"a": "x"}, impressao="unica"))
        s.add(QuestaoGerada(modo="variacao", origem_impressao="unica",
                            modelo="Claude Code, importado manualmente, em 03/10/2026",
                            enunciado="Uma variação gerada.", alternativas={"a": "y"},
                            resposta="a", impressao="g1"))
    with db.get_engine().begin() as conexao:
        conexao.execute(text("UPDATE versao_do_banco SET versao = 4"))

    relatorio = migracoes.migrar()

    assert (relatorio.de, relatorio.para) == (4, migracoes.VERSAO_ATUAL)
    with db.sessao() as s:
        gerada = s.scalar(select(QuestaoGerada))
    assert gerada.origem_chave == chave_da_questao("Única?", {"a": "x"})
    linhas = json.loads(acervo.caminho_das_geradas().read_text(encoding="utf-8"))
    assert [l["origem_chave"] for l in linhas] == [gerada.origem_chave]
