"""Teste de fumaca da CLI.

So carregar e rodar cada comando ja pega a classe de erro mais chata que
existe: a que estoura na importacao e derruba o programa antes de qualquer
coisa acontecer. Foi assim que o problema de fuso no Windows passou batido.
"""
from typer.testing import CliRunner

from radar.cli import app

runner = CliRunner()


def test_ajuda_funciona():
    resultado = runner.invoke(app, ["--help"])
    assert resultado.exit_code == 0
    assert "coletar" in resultado.output


def test_listar_com_banco_vazio(banco_temporario):
    resultado = runner.invoke(app, ["listar"])
    assert resultado.exit_code == 0
    assert "0 concurso" in resultado.output


def test_exportar_e_importar(banco_temporario, tmp_path):
    arquivo = str(tmp_path / "saida.json")

    assert runner.invoke(app, ["exportar", "--caminho", arquivo]).exit_code == 0
    assert runner.invoke(app, ["importar", "--caminho", arquivo]).exit_code == 0


def test_importar_arquivo_que_nao_existe_avisa_sem_quebrar(banco_temporario, tmp_path):
    resultado = runner.invoke(app, ["importar", "--caminho", str(tmp_path / "nada.json")])
    assert resultado.exit_code == 0
    assert "Nada a importar" in resultado.output
