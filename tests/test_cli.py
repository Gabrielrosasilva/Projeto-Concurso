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


def test_importar_diz_quantos_favoritos_o_banco_conhece(banco_temporario,
                                                        tmp_path):
    """E a linha que o log do robo mostra a cada execucao: ela responde
    "voce esta vendo os meus favoritos?"."""
    from radar.db import sessao
    from radar.models import Concurso

    with sessao() as s:
        s.add(Concurso(url="https://x.test/1", fonte="teste", titulo="Guarda",
                       interesse="favorito"))

    arquivo = str(tmp_path / "saida.json")
    runner.invoke(app, ["exportar", "--caminho", arquivo])
    resultado = runner.invoke(app, ["importar", "--caminho", arquivo])

    assert resultado.exit_code == 0
    assert "Conhece 1 favorito(s)" in resultado.output


def test_exportar_escreve_os_dois_arquivos(banco_temporario, tmp_path):
    """O segundo e a linha do tempo: sem ele o robo nasce sem historico."""
    arquivo = tmp_path / "saida.json"

    resultado = runner.invoke(app, ["exportar", "--caminho", str(arquivo)])

    assert resultado.exit_code == 0
    assert arquivo.exists()
    assert (tmp_path / "eventos.json").exists()


def test_a_linha_do_tempo_mostra_a_frase_e_nao_a_chave(banco_temporario):
    """A descricao gravada e chave de deduplicacao ("Situacao: a -> b"); o
    terminal mostra a mesma frase do site, com acento."""
    from radar.db import sessao
    from radar.models import Concurso, Evento

    with sessao() as s:
        concurso = Concurso(url="https://exemplo.test/c", fonte="teste",
                            titulo="Concurso de teste", uf="SC")
        s.add(concurso)
        s.flush()
        s.add(Evento(concurso_url=concurso.url, tipo="mudou_situacao",
                     descricao="Situacao: edital_publicado -> inscricoes_abertas"))
        concurso_id = concurso.id

    resultado = runner.invoke(app, ["eventos", str(concurso_id)], env={"COLUMNS": "200"})

    assert resultado.exit_code == 0, resultado.output
    assert "As inscrições abriram" in resultado.output
    assert "Situacao:" not in resultado.output
