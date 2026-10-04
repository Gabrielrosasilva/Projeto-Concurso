"""`radar sincronizar`: o que o robo sabe e o que eu sei, no mesmo lugar.

Quase todo teste aqui troca o `_git` por um falso que so anota o que teria
sido rodado: o que eles testam e a ORDEM, porque e ela que protege o dado:

    pull -> importar -> reclassificar -> exportar -> commit -> push

Importar antes de exportar nao e detalhe. Na ordem inversa, eu escreveria o
meu banco por cima do JSON antes de ler o que o robo ja avisou, e ele mandaria
tudo de novo no dia seguinte.

O fim do arquivo usa o git DE VERDADE, em repositorios dentro do tmp_path (sem
internet: a "origem" e uma pasta). Foi o git falso que deixou passar os dois
defeitos que derrubaram o backup das 23h30 de 27/09 a 03/10: o `pull
--rebase` se recusa a rodar com a pasta suja, e o `git add` com um arquivo que
nao existe nao adiciona nenhum.
"""
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sqlalchemy import select

from radar import acervo, cli, config, servico
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
    # O "pull" sao dois passos: buscar e avancar so para a frente.
    assert git.verbos == ["fetch", "merge", "add", "diff", "commit", "push"]
    assert ("merge", "--ff-only", "origin/main") in git.comandos


def test_so_os_json_do_radar_entram_no_commit(banco_temporario, git):
    """O resto do meu working tree fica como esta.

    Sao cinco: os concursos, a linha do tempo, o assunto e as questoes que a
    IA escreveu - esses dois porque custaram dinheiro - e, desde 25/09/2026,
    os simulados: o meu historico de treino, que nao tinha copia nenhuma. E
    os macetes e as explicacoes importados do Claude Code, que nao moram em
    tabela nenhuma. E, desde 26/09/2026, o diario do cronograma e os checks
    de cada faixa; desde 27/09/2026, o caderno de erros, o estudo extra e a
    reflexao de cada semana. Desde a Etapa 2 (01/10/2026), a arvore de
    conteudos e as classificacoes. Desde a Etapa 6B (02/10/2026), as fichas
    de estudo: a conferencia que eu marco na tela mora la.
    """
    # Os cinco que o sincronizar nao escreve - existem porque outro comando
    # os gravou antes.
    for nome in ("assuntos", "questoes_geradas", "macetes", "explicacoes", "fichas"):
        (config.diretorio_dados() / f"{nome}.json").write_text("[]", encoding="utf-8")

    runner.invoke(cli.app, ["sincronizar"])

    (add,) = [c for c in git.comandos if c[0] == "add"]
    (commit,) = [c for c in git.comandos if c[0] == "commit"]
    assert add[1] == "--"
    # O commit leva os caminhos no fim: so eles, mesmo com outra coisa no stage.
    assert commit[commit.index("--") + 1:] == add[2:]
    assert set(add[2:]) == {
        "data/concursos.json", "data/eventos.json", "data/assuntos.json",
        "data/questoes_geradas.json", "data/simulados.json",
        "data/macetes.json", "data/explicacoes.json",
        "data/registro_estudo.json", "data/estado_do_dia.json",
        "data/caderno_erros.json", "data/estudo_extra.json",
        "data/notas_semana.json",
        "data/conteudos.json", "data/classificacoes.json",
        "data/fichas.json",
    }


def test_arquivo_que_nao_existe_fica_fora_do_git_add(banco_temporario, git):
    """O defeito escondido atras do pull: um caminho que nao existe faz o `git
    add` parar com erro sem adicionar NENHUM, e o backup dizia "nada mudou".
    O data/macetes.json e o data/explicacoes.json ainda nao existem."""
    runner.invoke(cli.app, ["sincronizar"])

    (add,) = [c for c in git.comandos if c[0] == "add"]
    assert "data/macetes.json" not in add
    assert "data/explicacoes.json" not in add
    assert "data/simulados.json" in add          # este o sincronizar escreve


def test_git_add_que_falha_para_e_nao_diz_que_nada_mudou(banco_temporario,
                                                         monkeypatch):
    falso = GitFalso(falha_em=("add",))
    monkeypatch.setattr(cli, "_git", falso)

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 1
    assert "git add falhou" in resultado.output
    assert "Nada mudou" not in resultado.output


# --- quando da errado -------------------------------------------------------

def test_pull_que_falha_para_tudo(banco_temporario, monkeypatch):
    """Sem GitHub (sem rede, sem credencial), nada continua. O comando nao
    tenta adivinhar, e principalmente nao exporta por cima."""
    falso = GitFalso(falha_em=("fetch",))
    monkeypatch.setattr(cli, "_git", falso)

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 1
    assert "pull falhou" in resultado.output
    assert falso.verbos == ["fetch"]          # nao passou disso


def test_push_que_falha_avisa_que_o_commit_ficou_feito(banco_temporario,
                                                       monkeypatch):
    falso = GitFalso(falha_em=("push",))
    monkeypatch.setattr(cli, "_git", falso)

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 1
    assert "push falhou" in resultado.output
    assert "commit está feito" in resultado.output


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


# --- o reclassificar no meio (etapa 13) -------------------------------------

def test_a_grafia_velha_do_JSON_nao_volta(banco_temporario, git):
    """O caso que motivou o passo: eu reclassifico, sincronizo, e o importar
    traz de volta o JSON com a classificacao velha - desfazendo na hora o que
    eu tinha acabado de corrigir. Vale para qualquer mudanca no regioes.yml ou
    no alvo.yml, e nao so para o acento."""
    import json

    # o JSON como o robo deixou: grafia e motivo da regra ANTIGA
    acervo.caminho_padrao().parent.mkdir(parents=True, exist_ok=True)
    acervo.caminho_padrao().write_text(json.dumps([{
        "url": "https://exemplo.test/sao-jose",
        "fonte": "teste",
        "titulo": "Concurso Prefeitura de Sao Jose (SC) abre 300 vagas",
        "uf": "SC",
        "tipo": "concurso",
        "municipio": "Sao Jose",
        "relevancia": "nucleo",
        "motivo_relevancia": "Sao Jose (SC) esta no anel nucleo.",
    }]), encoding="utf-8")

    resultado = runner.invoke(cli.app, ["sincronizar"])
    assert resultado.exit_code == 0

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
    assert concurso.municipio == "São José"
    assert concurso.motivo_relevancia == "São José (SC) está no anel núcleo."

    # e o que vai para o robo ja leva a grafia nova
    linhas = json.loads(acervo.caminho_padrao().read_text(encoding="utf-8"))
    assert linhas[0]["municipio"] == "São José"


def test_o_reclassificar_roda_entre_importar_e_exportar(banco_temporario, git,
                                                        monkeypatch):
    """A posicao e a regra: antes do importar, o JSON velho passaria por cima;
    depois do exportar, o arquivo ja teria ido com a classificacao antiga."""
    passos = []
    monkeypatch.setattr(acervo, "importar", lambda: passos.append("importar") or 0)
    monkeypatch.setattr(
        acervo, "importar_eventos", lambda: passos.append("importar_eventos") or 0
    )
    monkeypatch.setattr(
        servico, "reclassificar", lambda: passos.append("reclassificar") or {}
    )
    monkeypatch.setattr(acervo, "exportar", lambda: passos.append("exportar") or 0)
    monkeypatch.setattr(
        acervo, "exportar_eventos", lambda: passos.append("exportar_eventos") or 0
    )

    runner.invoke(cli.app, ["sincronizar"])

    assert passos.index("importar") < passos.index("reclassificar")
    assert passos.index("reclassificar") < passos.index("exportar")


def test_a_contagem_por_anel_aparece_na_saida(banco_temporario, git):
    _favorito()

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert "reclassificar" in resultado.output


def test_o_historico_de_treino_vai_junto(banco_temporario, git):
    """O simulado feito aqui sai no arquivo que vai para o git."""
    import json

    from radar.models import Simulado

    with sessao() as s:
        s.add(Simulado(filtros={}))

    runner.invoke(cli.app, ["sincronizar"])

    linhas = json.loads(acervo.caminho_dos_simulados().read_text(encoding="utf-8"))
    assert len(linhas) == 1


def test_limpa_os_simulados_vazios_antes_de_exportar(banco_temporario, git):
    """Sem perguntar: o vazio e antigo nao vai para o arquivo, o de hoje vai."""
    import json
    from datetime import datetime, timedelta, timezone

    from radar.models import Simulado

    agora = datetime.now(timezone.utc)
    with sessao() as s:
        s.add(Simulado(filtros={}, criado_em=agora - timedelta(days=3)))
        s.add(Simulado(filtros={}, criado_em=agora - timedelta(hours=2)))

    saida = runner.invoke(cli.app, ["sincronizar"])
    assert "1 simulado(s) vazio(s) com mais de 1 dia apagado(s)" in saida.output

    linhas = json.loads(acervo.caminho_dos_simulados().read_text(encoding="utf-8"))
    assert len(linhas) == 1


# --- com o git de verdade (03/10/2026) --------------------------------------
#
# Tres repositorios no tmp_path: a "origem" (o GitHub, uma pasta bare), o
# "robo" (o Actions, que sobe a coleta) e o "local" (esta maquina). O teste
# so pula se a maquina nao tiver git - o runner do Actions tem.

@dataclass
class Repos:
    origem: Path
    robo: Path
    local: Path


def _rodar(pasta: Path, *argumentos: str) -> str:
    resultado = subprocess.run(["git", *argumentos], cwd=pasta,
                               capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    return resultado.stdout.strip()


def _identidade(pasta: Path) -> None:
    _rodar(pasta, "config", "user.name", "teste")
    _rodar(pasta, "config", "user.email", "teste@exemplo.test")
    _rodar(pasta, "config", "commit.gpgsign", "false")


def _escrever(arquivo: Path, texto: str) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(texto, encoding="utf-8")


@pytest.fixture
def repos(banco_temporario, tmp_path, monkeypatch):
    if shutil.which("git") is None:
        pytest.skip("sem git nesta maquina")

    origem = tmp_path / "origem.git"
    _rodar(tmp_path, "init", "--bare", "-b", "main", str(origem))

    robo = tmp_path / "robo"
    _rodar(tmp_path, "clone", str(origem), str(robo))
    _identidade(robo)
    _escrever(robo / "data" / "concursos.json", "[]\n")
    _escrever(robo / "data" / "eventos.json", "[]\n")
    _escrever(robo / "codigo.py", "x = 1\n")
    _rodar(robo, "add", ".")
    _rodar(robo, "commit", "-m", "inicio")
    _rodar(robo, "push", "origin", "HEAD:main")

    local = tmp_path / "local"
    _rodar(tmp_path, "clone", str(origem), str(local))
    _identidade(local)

    monkeypatch.setattr(cli, "_pasta_do_git", lambda: local)
    monkeypatch.setenv("RADAR_DATA_DIR", str(local / "data"))
    return Repos(origem=origem, robo=robo, local=local)


def _coleta_do_robo(repos: Repos) -> None:
    """O Actions sobe a coleta do dia: so data/eventos.json muda."""
    _escrever(repos.robo / "data" / "eventos.json", "[ ]\n")
    _rodar(repos.robo, "commit", "-am", "coleta: 2026-10-03")
    _rodar(repos.robo, "push", "origin", "HEAD:main")


def _assuntos(pasta: Path) -> list[str]:
    return _rodar(pasta, "log", "--format=%s").splitlines()


def test_com_a_pasta_suja_o_backup_traz_a_coleta_e_commita_so_o_radar(repos):
    """O caso de todo dia desde 27/09: uma etapa pela metade na pasta, e a
    coleta do robo no GitHub. Antes, o `pull --rebase` recusava."""
    _coleta_do_robo(repos)
    _escrever(repos.local / "codigo.py", "x = 2  # pela metade\n")
    _escrever(repos.local / "rascunho.txt", "nao versionado\n")

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 0, resultado.output
    assert "Sincronizado" in resultado.output
    assert _assuntos(repos.local)[1:] == ["coleta: 2026-10-03", "inicio"]
    assert _assuntos(repos.local)[0].startswith("sincronizar: ")
    # Subiu: o GitHub esta no mesmo commit que a pasta.
    assert _rodar(repos.origem, "rev-parse", "main") == \
        _rodar(repos.local, "rev-parse", "HEAD")
    # O commit levou so o data/, e a etapa pela metade ficou como estava.
    levados = _rodar(repos.local, "show", "--name-only", "--format=", "HEAD").split()
    assert levados and all(nome.startswith("data/") for nome in levados)
    assert "data/simulados.json" in levados
    assert (repos.local / "codigo.py").read_text(encoding="utf-8") == \
        "x = 2  # pela metade\n"
    pendentes = _rodar(repos.local, "status", "--porcelain").splitlines()
    assert "M codigo.py" in [linha.strip() for linha in pendentes]


def test_sem_nada_novo_no_github_o_backup_tambem_roda(repos):
    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 0, resultado.output
    assert _assuntos(repos.local)[0].startswith("sincronizar: ")


def test_historias_separadas_com_a_pasta_suja_param_sem_tocar_em_nada(repos):
    """Commit meu que nao subiu, a coleta do robo no GitHub, e a pasta suja: so
    o rebase juntaria, e ele nao roda com a pasta suja. O comando para ANTES
    de importar, e a pasta fica exatamente como estava."""
    _escrever(repos.local / "codigo.py", "x = 3\n")
    _rodar(repos.local, "commit", "-am", "meu commit que nao subiu")
    _coleta_do_robo(repos)
    _escrever(repos.local / "data" / "concursos.json", "[]  \n")   # pela metade
    antes = _rodar(repos.local, "rev-parse", "HEAD")

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 1
    assert "commite ou guarde" in resultado.output
    assert _rodar(repos.local, "rev-parse", "HEAD") == antes
    assert (repos.local / "data" / "concursos.json").read_text(encoding="utf-8") \
        == "[]  \n"
    assert not (repos.local / "data" / "simulados.json").exists()   # nao exportou
    assert _rodar(repos.local, "stash", "list") == ""
    assert not (repos.local / ".git" / "rebase-merge").exists()


def test_historias_separadas_com_a_pasta_limpa_viram_rebase(repos):
    _escrever(repos.local / "codigo.py", "x = 3\n")
    _rodar(repos.local, "commit", "-am", "meu commit que nao subiu")
    _coleta_do_robo(repos)

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 0, resultado.output
    assert _assuntos(repos.local)[1:] == [
        "meu commit que nao subiu", "coleta: 2026-10-03", "inicio"]
    assert _rodar(repos.origem, "rev-parse", "main") == \
        _rodar(repos.local, "rev-parse", "HEAD")


def test_a_coleta_que_cai_num_arquivo_mudado_aqui_nao_passa_por_cima(repos):
    """O robo mexeu no data/eventos.json, e o meu tambem esta mudado sem
    commit: o git recusa avancar, e o arquivo continua o meu."""
    _coleta_do_robo(repos)
    _escrever(repos.local / "data" / "eventos.json", "[]\n\n")

    resultado = runner.invoke(cli.app, ["sincronizar"])

    assert resultado.exit_code == 1
    assert "data/eventos.json" in resultado.output
    assert (repos.local / "data" / "eventos.json").read_text(encoding="utf-8") \
        == "[]\n\n"
