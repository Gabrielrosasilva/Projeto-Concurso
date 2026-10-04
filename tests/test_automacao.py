"""Tudo automatico: subir sem janela, parar, o Agendador e o backup das 23h30.

Nenhum teste aqui chama o schtasks, o tasklist, o taskkill nem sobe servidor:
o `_rodar` e o `Popen` sao trocados por falsos que so anotam o que teria sido
rodado. Dois motivos, e os dois valem: o robo do GitHub e Linux, e teste que
mexe no Agendador de verdade mexe na MINHA maquina.

O que da para testar de verdade e o que e so texto e conta - e e onde erro de
verdade se esconde: a hora no XML, o "executar se perdeu o horario", o comando
que a tarefa chama, o nome do log, a rotacao dos 30 dias e a leitura da linha
final do log.
"""
import subprocess
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import automacao, cli
from radar.web.app import app

runner = CliRunner()


def _rodar(*argumentos):
    """Roda o comando com terminal largo: o rich quebraria linha no meio do
    endereco, e ai o teste falharia por causa da largura da tela."""
    return runner.invoke(cli.app, list(argumentos), env={"COLUMNS": "200"})

# O namespace do Agendador. Toda etiqueta do XML vem prefixada com ele.
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


@pytest.fixture
def pasta_de_dados(tmp_path, monkeypatch):
    """Aponta o data/ para uma pasta descartavel: nada escreve no projeto."""
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    return tmp_path


class RodarFalso:
    """Anota os comandos e responde o que o teste mandar."""

    def __init__(self, codigo=0, stdout="", stderr=""):
        self.comandos = []
        self.codigo = codigo
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, comando, sem_janela=False):
        self.comandos.append(list(comando))
        return subprocess.CompletedProcess(
            comando, self.codigo, stdout=self.stdout, stderr=self.stderr
        )


# --- o XML das duas tarefas -------------------------------------------------

def _arvore(xml: str) -> ElementTree.Element:
    return ElementTree.fromstring(xml)


def test_o_xml_das_duas_tarefas_e_xml_valido():
    for xml in (automacao.xml_da_tarefa_web("PC\\eu"),
                automacao.xml_da_tarefa_backup("PC\\eu")):
        assert _arvore(xml).tag.endswith("Task")


def test_o_backup_e_diario_as_23h30():
    arvore = _arvore(automacao.xml_da_tarefa_backup("PC\\eu", dia=date(2026, 9, 27)))
    inicio = arvore.find(".//t:CalendarTrigger/t:StartBoundary", NS)
    assert inicio.text == "2026-09-27T23:30:00"
    assert arvore.find(".//t:ScheduleByDay/t:DaysInterval", NS).text == "1"


def test_a_web_sobe_no_logon_do_meu_usuario():
    arvore = _arvore(automacao.xml_da_tarefa_web("PC\\eu"))
    gatilho = arvore.find(".//t:LogonTrigger", NS)
    assert gatilho is not None
    assert gatilho.find("t:UserId", NS).text == "PC\\eu"
    # E nao tem gatilho de hora: quem tem hora marcada e o backup.
    assert arvore.find(".//t:CalendarTrigger", NS) is None


@pytest.mark.parametrize("xml", [
    automacao.xml_da_tarefa_web("PC\\eu"),
    automacao.xml_da_tarefa_backup("PC\\eu"),
])
def test_executa_assim_que_possivel_se_perdeu_o_horario(xml):
    """O StartWhenAvailable e o motivo de existir XML em vez de linha de comando."""
    assert _arvore(xml).find(".//t:StartWhenAvailable", NS).text == "true"


@pytest.mark.parametrize("xml", [
    automacao.xml_da_tarefa_web("PC\\eu"),
    automacao.xml_da_tarefa_backup("PC\\eu"),
])
def test_nao_pede_administrador_e_roda_no_meu_usuario(xml):
    arvore = _arvore(xml)
    principal = arvore.find(".//t:Principal", NS)
    assert principal.find("t:UserId", NS).text == "PC\\eu"
    assert principal.find("t:LogonType", NS).text == "InteractiveToken"
    assert principal.find("t:RunLevel", NS).text == "LeastPrivilege"


@pytest.mark.parametrize("xml", [
    automacao.xml_da_tarefa_web("PC\\eu"),
    automacao.xml_da_tarefa_backup("PC\\eu"),
])
def test_nao_desiste_no_notebook_na_bateria(xml):
    arvore = _arvore(xml)
    assert arvore.find(".//t:DisallowStartIfOnBatteries", NS).text == "false"
    assert arvore.find(".//t:StopIfGoingOnBatteries", NS).text == "false"


def test_a_tarefa_da_web_chama_o_python_sem_janela_neste_modulo():
    acao = _arvore(automacao.xml_da_tarefa_web("PC\\eu")).find(".//t:Exec", NS)
    # Compara com a funcao, e nao com "pythonw.exe": no Linux do Actions ele nao
    # existe e a funcao devolve o proprio python.
    assert acao.find("t:Command", NS).text == str(automacao.python_sem_janela())
    assert acao.find("t:Arguments", NS).text == "-m radar.automacao"
    assert acao.find("t:WorkingDirectory", NS).text == str(automacao.config.RAIZ)


def test_a_tarefa_do_backup_chama_o_mesmo_modulo_com_backup():
    acao = _arvore(automacao.xml_da_tarefa_backup("PC\\eu")).find(".//t:Exec", NS)
    assert acao.find("t:Arguments", NS).text == "-m radar.automacao --backup"


def test_a_web_nao_tem_limite_de_tempo_e_o_backup_tem():
    """Limite na tarefa da web mataria o servidor no meio do dia."""
    web = _arvore(automacao.xml_da_tarefa_web("PC\\eu"))
    assert web.find(".//t:ExecutionTimeLimit", NS).text == "PT0S"
    backup = _arvore(automacao.xml_da_tarefa_backup("PC\\eu"))
    assert backup.find(".//t:ExecutionTimeLimit", NS).text == "PT1H"


def test_o_nome_do_usuario_e_escapado_no_xml():
    """Nome com & quebraria o XML - e o schtasks recusaria o arquivo inteiro."""
    xml = automacao.xml_da_tarefa_web("CASA\\eu & voce")
    assert "eu &amp; voce" in xml
    assert _arvore(xml).find(".//t:Principal/t:UserId", NS).text == "CASA\\eu & voce"


def test_criar_tarefa_grava_utf16_e_chama_o_schtasks(monkeypatch):
    """UTF-8 faz o schtasks recusar o XML com uma mensagem que nao explica nada."""
    vistos = {}

    def falso(comando, sem_janela=False):
        vistos["comando"] = list(comando)
        arquivo = Path(comando[comando.index("/XML") + 1])
        vistos["bytes"] = arquivo.read_bytes()
        return subprocess.CompletedProcess(comando, 0)

    monkeypatch.setattr(automacao, "_rodar", falso)
    automacao.criar_tarefa("Radar - web", automacao.xml_da_tarefa_web("PC\\eu"))

    assert vistos["comando"][:4] == ["schtasks", "/Create", "/TN", "Radar - web"]
    assert "/F" in vistos["comando"]          # rodar `radar agendar` de novo funciona
    assert vistos["bytes"][:2] in (b"\xff\xfe", b"\xfe\xff")   # marca do UTF-16


def test_as_duas_tarefas_tem_os_nomes_que_eu_procuro_no_agendador():
    assert set(automacao.tarefas()) == {"Radar - web", "Radar - backup"}


# --- subir e parar, com processo fingido ------------------------------------

class PopenFalso:
    """Nao sobe nada: so guarda o comando e devolve um numero de processo."""

    def __init__(self, comando, **resto):
        self.comando = comando
        self.resto = resto
        self.pid = 4242


def test_subir_grava_o_pid_a_porta_e_a_hora(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", PopenFalso)

    servidor = automacao.subir(porta=8123)

    assert servidor.pid == 4242
    assert servidor.porta == 8123
    gravado = automacao.ler_arquivo_do_pid()
    assert (gravado.pid, gravado.porta) == (4242, 8123)
    assert gravado.subiu_em is not None
    assert automacao.caminho_do_pid().name == "radar_web.pid"


def test_subir_chama_o_radar_web_sem_janela_na_porta_pedida(pasta_de_dados, monkeypatch):
    guardado = {}

    def espiao(comando, **resto):
        guardado["comando"] = comando
        guardado["resto"] = resto
        return PopenFalso(comando, **resto)

    monkeypatch.setattr(subprocess, "Popen", espiao)
    automacao.subir(porta=8000)

    comando = guardado["comando"]
    assert comando[1:5] == ["-m", "radar.cli", "web", "--porta"]
    assert comando[5] == "8000"
    assert "127.0.0.1" in comando
    # A saida vai para arquivo: sem janela, erro sem log e erro invisivel.
    assert automacao.caminho_do_log_da_web().exists()


def test_no_ar_e_none_quando_nao_ha_arquivo(pasta_de_dados):
    assert automacao.no_ar() is None


def test_no_ar_limpa_o_arquivo_de_processo_morto(pasta_de_dados, monkeypatch):
    """O arquivo sobra quando o PC desliga na tomada. Isso nao e erro meu."""
    automacao.gravar_arquivo_do_pid(automacao.Servidor(999, 8000, datetime.now()))
    monkeypatch.setattr(automacao, "processo_vivo", lambda pid: False)

    assert automacao.no_ar() is None
    assert not automacao.caminho_do_pid().exists()


def test_no_ar_acha_o_processo_vivo(pasta_de_dados, monkeypatch):
    automacao.gravar_arquivo_do_pid(automacao.Servidor(999, 8080, datetime.now()))
    monkeypatch.setattr(automacao, "processo_vivo", lambda pid: True)

    servidor = automacao.no_ar()
    assert servidor.pid == 999
    assert servidor.endereco == "http://127.0.0.1:8080"


def test_arquivo_de_pid_estragado_vale_como_arquivo_ausente(pasta_de_dados):
    automacao.caminho_do_pid().write_text("isto nao e json", encoding="utf-8")
    assert automacao.ler_arquivo_do_pid() is None
    assert automacao.no_ar() is None


def test_parar_mata_o_processo_e_apaga_o_arquivo(pasta_de_dados, monkeypatch):
    automacao.gravar_arquivo_do_pid(automacao.Servidor(4242, 8000, datetime.now()))
    monkeypatch.setattr(automacao, "processo_vivo", lambda pid: True)
    mortos = []
    monkeypatch.setattr(automacao, "_encerrar", mortos.append)

    servidor = automacao.parar()

    assert servidor.pid == 4242
    assert mortos == [4242]
    assert not automacao.caminho_do_pid().exists()


def test_parar_sem_nada_rodando_nao_mata_ninguem(pasta_de_dados, monkeypatch):
    mortos = []
    monkeypatch.setattr(automacao, "_encerrar", mortos.append)

    assert automacao.parar() is None
    assert mortos == []


def test_parar_nao_mata_pid_reaproveitado_por_outro_programa(pasta_de_dados, monkeypatch):
    """Numero de processo se reaproveita: o de ontem pode ser o Bloco de Notas."""
    automacao.gravar_arquivo_do_pid(automacao.Servidor(4242, 8000, datetime.now()))
    monkeypatch.setattr(automacao, "processo_vivo", lambda pid: False)
    mortos = []
    monkeypatch.setattr(automacao, "_encerrar", mortos.append)

    assert automacao.parar() is None
    assert mortos == []


def test_processo_vivo_confere_que_e_python(monkeypatch):
    """No Windows a checagem e por nome: PID que existe mas nao e Python nao conta."""
    monkeypatch.setattr(automacao, "e_windows", lambda: True)
    monkeypatch.setattr(automacao, "_rodar",
                        RodarFalso(stdout='"notepad.exe","4242",...'))
    assert automacao.processo_vivo(4242) is False
    monkeypatch.setattr(automacao, "_rodar",
                        RodarFalso(stdout='"pythonw.exe","4242",...'))
    assert automacao.processo_vivo(4242) is True


# --- o log do backup e a rotacao --------------------------------------------

def _log(pasta: Path, dia: str, texto: str) -> Path:
    caminho = automacao.preparar_logs() / f"sincronizar-{dia}.log"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def test_o_log_do_dia_tem_a_data_no_nome(pasta_de_dados):
    assert automacao.caminho_do_log(date(2026, 9, 27)).name == "sincronizar-2026-09-27.log"


def test_log_com_mais_de_30_dias_e_apagado(pasta_de_dados):
    velho = _log(pasta_de_dados, "2026-08-01", "x")
    limite = _log(pasta_de_dados, "2026-08-28", "x")     # 30 dias atras: fica
    novo = _log(pasta_de_dados, "2026-09-27", "x")

    apagados = automacao.limpar_logs_velhos(dia_de_hoje=date(2026, 9, 27))

    assert apagados == [velho]
    assert not velho.exists()
    assert limite.exists() and novo.exists()


def test_a_rotacao_nao_mexe_no_log_da_web(pasta_de_dados):
    web = automacao.preparar_logs() / "web.log"
    web.write_text("x", encoding="utf-8")
    _log(pasta_de_dados, "2020-01-01", "x")

    automacao.limpar_logs_velhos(dia_de_hoje=date(2026, 9, 27))

    assert web.exists()


def test_sem_log_nenhum_o_ultimo_backup_e_none(pasta_de_dados):
    assert automacao.ultimo_backup() is None


def test_ultimo_backup_que_deu_certo(pasta_de_dados):
    _log(pasta_de_dados, "2026-09-26", f"saida velha\n{automacao.MARCA_FALHOU}sem rede\n")
    _log(pasta_de_dados, "2026-09-27", f"tudo bem\n{automacao.MARCA_OK}\n")

    backup = automacao.ultimo_backup()

    assert backup.deu_certo is True
    assert backup.dia == date(2026, 9, 27)
    assert backup.motivo is None


def test_ultimo_backup_que_falhou_guarda_o_motivo(pasta_de_dados):
    _log(pasta_de_dados, "2026-09-27",
         f"6/6 Empurrando\n{automacao.MARCA_FALHOU}fatal: Could not resolve host: github.com\n")

    backup = automacao.ultimo_backup()

    assert backup.deu_certo is False
    assert backup.motivo == "fatal: Could not resolve host: github.com"


def test_log_sem_a_linha_final_conta_como_falha(pasta_de_dados):
    """PC desligado as 23h31: o log comecou e nao terminou."""
    _log(pasta_de_dados, "2026-09-27", "1/6 Trazendo o que o robo coletou\n")

    backup = automacao.ultimo_backup()

    assert backup.deu_certo is False
    assert "nao terminou" in backup.motivo


def test_o_motivo_da_falha_e_a_ultima_linha_com_texto():
    saida = (
        "1/6 Trazendo o que o robo coletou\n"
        "O pull falhou. Resolva a mao e rode de novo:\n"
        "\n"
        "CONFLICT (content): Merge conflict in data/concursos.json\n"
        "\n"
    )
    assert automacao._ultima_linha_util(saida) == (
        "CONFLICT (content): Merge conflict in data/concursos.json"
    )


def test_rodar_backup_escreve_a_saida_e_a_linha_final(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(automacao, "_rodar_python",
                        RodarFalso(codigo=0, stdout="6/6 Empurrando\nSincronizado.\n"))

    backup = automacao.rodar_backup(dia=date(2026, 9, 27))

    texto = backup.caminho.read_text(encoding="utf-8")
    assert backup.deu_certo is True
    assert "Sincronizado." in texto
    assert texto.strip().endswith(automacao.MARCA_OK)
    assert backup.caminho.name == "sincronizar-2026-09-27.log"


def test_rodar_backup_que_falhou_guarda_o_porque(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(automacao, "_rodar_python", RodarFalso(
        codigo=1, stdout="6/6 Empurrando\nO push falhou.\n",
        stderr="fatal: Authentication failed\n",
    ))

    backup = automacao.rodar_backup(dia=date(2026, 9, 27))

    assert backup.deu_certo is False
    assert backup.motivo == "fatal: Authentication failed"
    assert automacao.MARCA_FALHOU in backup.caminho.read_text(encoding="utf-8")


def test_rodar_backup_chama_o_sincronizar_e_nao_reimplementa_nada(pasta_de_dados, monkeypatch):
    falso = RodarFalso()
    monkeypatch.setattr(automacao, "_rodar_python", falso)

    automacao.rodar_backup(dia=date(2026, 9, 27))

    assert falso.comandos == [["sincronizar"]]


def test_rodar_backup_tambem_limpa_os_logs_velhos(pasta_de_dados, monkeypatch):
    velho = _log(pasta_de_dados, "2020-01-01", "x")
    monkeypatch.setattr(automacao, "_rodar_python", RodarFalso())

    automacao.rodar_backup(dia=date(2026, 9, 27))

    assert not velho.exists()


def test_ler_o_ultimo_backup_nao_cria_pasta_nenhuma(pasta_de_dados):
    """A tela Mais le isso a cada visita: abrir pagina nao cria pasta no disco."""
    assert automacao.ultimo_backup() is None
    assert not automacao.diretorio_de_logs().exists()


# --- os dois atalhos na Area de Trabalho ------------------------------------

def test_o_atalho_chama_o_radar_bat_do_projeto():
    texto = automacao.texto_do_atalho("subir --abrir", "Sobe o Radar.")
    assert "radar.bat" in texto
    assert "subir --abrir" in texto
    assert texto.startswith("@echo off")
    # Janela que fica aberta so quando deu errado.
    assert "if errorlevel 1 pause" in texto


def test_os_dois_atalhos_sao_subir_e_parar():
    assert set(automacao.ATALHOS) == {"Radar.bat", "Parar o Radar.bat"}
    assert automacao.ATALHOS["Radar.bat"][0] == "subir --abrir"
    assert automacao.ATALHOS["Parar o Radar.bat"][0] == "parar"


def test_criar_e_apagar_atalhos(tmp_path, monkeypatch):
    monkeypatch.setattr(automacao, "diretorio_da_area_de_trabalho", lambda: tmp_path)

    criados = automacao.criar_atalhos()

    assert sorted(c.name for c in criados) == ["Parar o Radar.bat", "Radar.bat"]
    assert (tmp_path / "Radar.bat").read_text(encoding="utf-8").startswith("@echo off")

    assert len(automacao.apagar_atalhos()) == 2
    assert not (tmp_path / "Radar.bat").exists()
    # Apagar duas vezes nao estoura: `radar agendar --remover` e repetivel.
    assert automacao.apagar_atalhos() == []


# --- os comandos ------------------------------------------------------------

def test_status_diz_fora_do_ar_e_que_nunca_houve_backup(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(automacao, "no_ar", lambda: None)
    resultado = _rodar("status")
    assert resultado.exit_code == 0
    assert "fora do ar" in resultado.output
    assert "nunca rodou" in resultado.output


def test_status_mostra_endereco_e_a_falha_do_ultimo_backup(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(
        automacao, "no_ar",
        lambda: automacao.Servidor(4242, 8000, datetime(2026, 9, 27, 8, 30)),
    )
    _log(pasta_de_dados, "2026-09-27", f"{automacao.MARCA_FALHOU}sem rede\n")

    resultado = _rodar("status")

    assert "http://127.0.0.1:8000" in resultado.output
    assert "4242" in resultado.output
    assert "27/09/2026" in resultado.output
    assert "sem rede" in resultado.output


def test_parar_sem_nada_no_ar_avisa_e_sai_em_paz(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(automacao, "parar", lambda: None)
    resultado = _rodar("parar")
    assert resultado.exit_code == 0
    assert "Nada para desligar" in resultado.output


def test_subir_com_a_web_ja_no_ar_nao_sobe_outra(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(
        automacao, "no_ar",
        lambda: automacao.Servidor(4242, 8000, datetime(2026, 9, 27, 8, 30)),
    )
    subiu = []
    monkeypatch.setattr(automacao, "subir", lambda porta: subiu.append(porta))

    resultado = _rodar("subir")

    assert subiu == []
    assert "Já está no ar" in resultado.output


def test_subir_recusa_porta_ocupada_por_outro(pasta_de_dados, monkeypatch):
    monkeypatch.setattr(automacao, "no_ar", lambda: None)
    monkeypatch.setattr(cli, "porta_ocupada", lambda host, porta: True)
    subiu = []
    monkeypatch.setattr(automacao, "subir", lambda porta: subiu.append(porta))

    resultado = _rodar("subir")

    assert resultado.exit_code == 1
    assert subiu == []
    assert "já está em uso" in resultado.output


def test_subir_que_nao_responde_mostra_o_fim_do_log(pasta_de_dados, monkeypatch):
    """Sem janela, servidor que morre e silencio. O comando tem que falar."""
    monkeypatch.setattr(automacao, "no_ar", lambda: None)
    monkeypatch.setattr(cli, "porta_ocupada", lambda host, porta: False)
    monkeypatch.setattr(automacao, "subir",
                        lambda porta: automacao.Servidor(4242, porta, datetime.now()))
    monkeypatch.setattr(automacao, "esperar_subir", lambda servidor: False)
    monkeypatch.setattr(automacao, "fim_do_log_da_web",
                        lambda: ["ModuleNotFoundError: No module named 'uvicorn'"])

    resultado = _rodar("subir")

    assert resultado.exit_code == 1
    assert "ModuleNotFoundError" in resultado.output


def test_agendar_fora_do_windows_diz_que_nao_da(monkeypatch):
    monkeypatch.setattr(automacao, "e_windows", lambda: False)
    resultado = _rodar("agendar")
    assert resultado.exit_code == 1
    assert "do Windows" in resultado.output


def test_agendar_cria_as_duas_tarefas_e_os_dois_atalhos(monkeypatch, tmp_path):
    monkeypatch.setattr(automacao, "e_windows", lambda: True)
    criadas = []
    monkeypatch.setattr(automacao, "criar_tarefa",
                        lambda nome, xml: criadas.append(nome)
                        or subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(automacao, "diretorio_da_area_de_trabalho", lambda: tmp_path)

    resultado = _rodar("agendar")

    assert resultado.exit_code == 0
    assert criadas == ["Radar - web", "Radar - backup"]
    assert (tmp_path / "Radar.bat").exists()
    assert (tmp_path / "Parar o Radar.bat").exists()


def test_agendar_remover_apaga_tarefas_e_atalhos(monkeypatch, tmp_path):
    monkeypatch.setattr(automacao, "e_windows", lambda: True)
    monkeypatch.setattr(automacao, "diretorio_da_area_de_trabalho", lambda: tmp_path)
    automacao.criar_atalhos()
    apagadas = []
    monkeypatch.setattr(automacao, "remover_tarefa",
                        lambda nome: apagadas.append(nome)
                        or subprocess.CompletedProcess([], 0))

    resultado = _rodar("agendar", "--remover")

    assert resultado.exit_code == 0
    assert apagadas == ["Radar - web", "Radar - backup"]
    assert not (tmp_path / "Radar.bat").exists()


def test_agendar_status_nao_mexe_em_nada(monkeypatch, tmp_path):
    monkeypatch.setattr(automacao, "e_windows", lambda: True)
    monkeypatch.setattr(automacao, "diretorio_da_area_de_trabalho", lambda: tmp_path)
    monkeypatch.setattr(automacao, "criar_tarefa", lambda nome, xml: pytest.fail("mexeu"))
    monkeypatch.setattr(automacao, "consultar_tarefa",
                        lambda nome: {"Próxima Execução": "27/09/2026 23:30:00"}
                        if nome == "Radar - backup" else None)

    resultado = _rodar("agendar", "--status")

    assert resultado.exit_code == 0
    assert "não está criada" in resultado.output       # a da web
    assert "23:30:00" in resultado.output              # a do backup
    assert not (tmp_path / "Radar.bat").exists()


# --- o aviso na tela Mais ---------------------------------------------------

@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_a_tela_mais_avisa_o_backup_que_falhou(cliente, tmp_path):
    _log(tmp_path, "2026-09-27",
         f"{automacao.MARCA_FALHOU}fatal: Could not resolve host: github.com\n")

    pagina = cliente.get("/mais").text

    assert "O último backup falhou em 27/09" in pagina
    assert "Could not resolve host" in pagina
    assert "ds-alerta" in pagina


def test_o_aviso_sai_quando_o_proximo_backup_da_certo(cliente, tmp_path):
    _log(tmp_path, "2026-09-26", f"{automacao.MARCA_FALHOU}sem rede\n")
    _log(tmp_path, "2026-09-27", f"{automacao.MARCA_OK}\n")

    pagina = cliente.get("/mais").text

    assert "falhou" not in pagina
    assert "27/09/2026" in pagina and "deu certo" in pagina


def test_sem_backup_nenhum_a_tela_mais_ensina_o_comando(cliente):
    pagina = cliente.get("/mais").text
    assert "Nenhum backup rodou ainda" in pagina
    assert "radar agendar" in pagina


def test_log_reescrito_com_bom_continua_legivel(pasta_de_dados):
    """Abrir o log no Bloco de Notas e salvar poe um BOM na frente da 1a linha."""
    caminho = automacao.preparar_logs() / "sincronizar-2026-09-27.log"
    caminho.write_text(f"{automacao.MARCA_OK}\n", encoding="utf-8-sig")

    assert automacao.ultimo_backup().deu_certo is True


def test_o_log_da_web_e_reescrito_e_nao_cresce_para_sempre(pasta_de_dados, monkeypatch):
    """O uvicorn anota uma linha por requisicao: continuar o arquivo nao teria fim."""
    monkeypatch.setattr(subprocess, "Popen", PopenFalso)

    automacao.subir(porta=8000)
    automacao.subir(porta=8000)

    texto = automacao.caminho_do_log_da_web().read_text(encoding="utf-8")
    assert texto.count("--- subiu em") == 1


# --- ler a saida do Windows sem adivinhar pagina de codigo ------------------

def test_saida_em_utf8_e_lida_certo():
    assert automacao._decodificar("Próxima Execução".encode("utf-8")) == (
        "Próxima Execução"
    )


def test_saida_que_nao_e_utf8_nao_estoura_nem_vira_caractere_perdido():
    """Era o defeito: lida como UTF-8, a saida da pagina 850 virava U+FFFD - e
    o U+FFFD estourava depois, na hora de imprimir na tela."""
    texto = automacao._decodificar(b"Pr\xa2xima Execu\x87\xe3o")
    assert "\ufffd" not in texto
    assert texto.startswith("Pr")
