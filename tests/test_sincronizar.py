"""`radar sincronizar`: o que o robo sabe e o que eu sei, no mesmo lugar.

Nenhum teste aqui chama o git de verdade: o `_git` e trocado por um falso que
so anota o que teria sido rodado. O que importa testar nao e o git - e a
ORDEM, porque e ela que protege o dado:

    pull -> importar -> exportar -> commit -> push

Importar antes de exportar nao e detalhe. Na ordem inversa, eu escreveria o
meu banco por cima do JSON antes de ler o que o robo ja avisou, e ele mandaria
tudo de novo no dia seguinte.
"""
import subprocess

import pytest
from typer.testing import CliRunner

from radar import acervo, cli
from radar.db import sessao
from radar.models import Concurso

runner = CliRunner()


class GitFalso:
    """Anota os comandos e responde o que o teste mandar."""

    def __init__(self, falha_em=None, tem_mudanca=True):
        self.comandos = []
        self.falha_em = falha_em or ()
        self.tem_mudanca = tem_mudanca

    def __call__(self, *argumentos):
        self.comandos.append(argumentos)

        if argumentos[:1] == ("diff",):
            # `git diff --staged --quiet` sai 1 quando HA o que commitar
            return subprocess.CompletedProcess(argumentos, 1 if self.tem_mudanca else 0)

        if argumentos[0] in self.falha_em:
            return subprocess.CompletedProcess(
                argumentos, 1, stdout="", stderr="deu ruim no git"
            )
        return subprocess.CompletedProcess(argumentos, 0, stdout="", stderr="")

    @property
    def verbos(self):
        return [c[0] for c in self.comandos]


@pytest.fixture
def git(monkeypatch):
    falso = GitFalso()
    monkeypatch.setattr(cli, "_git", falso)
    return falso


def _favorito():
    with sessao() as s:
        s.add(Concurso(
            url="https://exemplo.test/palhoca", fonte="teste",
            titulo="Guarda Municipal de Palhoca", interesse="favorito",
        ))


# --- a ordem ----------------------------------------------------------------

def test_importa_antes_de_exportar(banco_temporario, git, monkeypatch):
    """A regra que o comando existe para garantir: na ordem inversa, o meu
    banco escreveria por cima do que o robo ja avisou."""
    passos = []
    monkeypatch.setattr(acervo, "importar", lambda: passos.append("importar") or 0)
    monkeypatch.setattr(
        acervo, "importar_eventos", lambda: passos.append("importar_eventos") or 0
    )
    monkeypatch.setattr(acervo, "exportar", lambda: passos.append("exportar") or 0)
    monkeypatch.setattr(
        acervo, "exportar_eventos", lambda: passos.append("exportar_eventos") or 0
    )

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 0
    assert passos.index("importar") < passos.index("exportar")
    assert passos.index("importar_eventos") < passos.index("exportar_eventos")


def test_a_sequencia_do_git(banco_temporario, git):
    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 0
    assert git.verbos == ["pull", "add", "diff", "commit", "push"]


def test_so_os_dois_json_entram_no_commit(banco_temporario, git):
    """O resto do meu working tree fica como esta."""
    runner.invoke(cli.app, ["sincronizar"])

    (add,) = [c for c in git.comandos if c[0] == "add"]
    assert set(add[1:]) == {"data/concursos.json", "data/eventos.json"}


# --- quando da errado -------------------------------------------------------

def test_pull_que_falha_para_tudo(banco_temporario, monkeypatch):
    """Conflito de rebase e coisa para eu resolver a mao. O comando nao tenta
    adivinhar, e principalmente nao exporta por cima."""
    falso = GitFalso(falha_em=("pull",))
    monkeypatch.setattr(cli, "_git", falso)

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 1
    assert "pull falhou" in resultado.output
    assert falso.verbos == ["pull"]          # nao passou disso


def test_push_que_falha_avisa_que_o_commit_ficou_feito(banco_temporario,
                                                       monkeypatch):
    falso = GitFalso(falha_em=("push",))
    monkeypatch.setattr(cli, "_git", falso)

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 1
    assert "push falhou" in resultado.output
    assert "commit esta feito" in resultado.output


# --- quando nao ha o que fazer ----------------------------------------------

def test_sem_mudanca_nao_commita(banco_temporario, monkeypatch):
    falso = GitFalso(tem_mudanca=False)
    monkeypatch.setattr(cli, "_git", falso)

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 0
    assert "Em dia com o GitHub" in resultado.output
    assert "commit" not in falso.verbos
    assert "push" not in falso.verbos


def test_sem_empurrar_para_antes_do_push(banco_temporario, git):
    resultado = runner.invoke(cli.app, ["sincronizar", "--sem-empurrar"])

    assert resultado.exit_code == 0
    assert "falta `git push`" in resultado.output
    assert "push" not in git.verbos


# --- o que ele conta --------------------------------------------------------

def test_diz_quantos_favoritos_o_robo_passa_a_conhecer(banco_temporario, git):
    """E a resposta da pergunta que me faz rodar o comando."""
    _favorito()

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert "1 favorito(s)" in resultado.output


def test_o_json_sai_com_o_meu_favorito_dentro(banco_temporario, git, tmp_path):
    """De ponta a ponta, sem git: o favorito que esta no banco aparece no
    arquivo que o robo vai ler."""
    import json

    _favorito()
    runner.invoke(cli.app, ["sincronizar"])

    linhas = json.loads(acervo.caminho_padrao().read_text(encoding="utf-8"))
    assert [l["interesse"] for l in linhas] == ["favorito"]
    assert acervo.caminho_dos_eventos().exists()
