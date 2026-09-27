"""Deixar o radar de pe sozinho: subir sem janela, parar, e o Agendador.

Tres coisas moram aqui:

  - o servidor em segundo plano (`radar subir`, `radar parar`, `radar status`),
    com o numero do processo em data/radar_web.pid;
  - as duas tarefas do Agendador do Windows (`radar agendar`), criadas no MEU
    usuario, sem pedir administrador;
  - o backup das 23h30 e o log dele, que e o que a tela Mais le para dizer
    "o ultimo backup falhou".

NAO e servico do Windows, de proposito - o porque esta em docs/decisoes.md.

Este arquivo separa de proposito o que MONTA (o XML da tarefa, o texto do
.bat, o nome do log, a leitura do log) do que EXECUTA (schtasks, tasklist,
taskkill, Popen). O primeiro grupo tem teste com dado fixo; o segundo so roda
de verdade no Windows, e nenhum teste chama - o robo do GitHub e Linux.

Nada aqui imprime na tela: quem fala com o usuario e a CLI. O motivo nao e
gosto - a tarefa do Agendador chama este modulo pelo pythonw.exe, que nao tem
console nenhum, e um `print` ali dentro viraria erro invisivel.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as escapar_xml

from radar import config
from radar.util import fuso_local, porta_ocupada

# A porta de sempre e o endereco de sempre. O `radar subir` nao tem --rede: o
# servidor que sobe sozinho no logon fica so neste PC. Para o celular eu abro
# o `radar web --rede` na mao, e sabendo o que estou fazendo.
PORTA_PADRAO = 8000
HOST_PADRAO = "127.0.0.1"

# Como as tarefas se chamam no Agendador. Com o travessao porque e assim que eu
# vou achar as duas juntas, uma embaixo da outra, na lista do Agendador de
# Tarefas - que tem umas duzentas.
TAREFA_WEB = "Radar - web"
TAREFA_BACKUP = "Radar - backup"

# 23h30: depois do estudo do dia e antes de eu desligar o PC. Hora fixa porque
# o backup nao concorre com nada - ele so fala com o GitHub.
HORA_DO_BACKUP = "23:30"

# Quanto tempo o log do backup fica na pasta. Um mes e o que eu olharia para
# desconfiar de um padrao ("falhou nos tres domingos"); mais que isso e lixo.
DIAS_DE_LOG = 30

# A ultima linha do log do backup, e a unica coisa que a tela Mais le dele.
# Formato fixo de proposito: procurar a palavra "erro" no meio da saida do
# sincronizar seria adivinhar, e adivinhar erra calado.
MARCA_OK = "RESULTADO: ok"
MARCA_FALHOU = "RESULTADO: falhou - "

# Motivo maior que isso nao cabe na tela nem ajuda: o log inteiro esta ali ao
# lado para quem quiser o resto.
LIMITE_DO_MOTIVO = 200


# --- onde cada coisa mora ---------------------------------------------------

def caminho_do_pid() -> Path:
    return config.diretorio_dados() / "radar_web.pid"


def diretorio_de_logs() -> Path:
    """A pasta data/logs/. NAO cria nada - quem escreve chama `preparar_logs`.

    Ler nao pode criar pasta: a tela Mais le o ultimo backup a cada visita, e
    abrir uma pagina nao e motivo para aparecer pasta nova no disco.
    """
    return config.diretorio_dados() / "logs"


def preparar_logs() -> Path:
    caminho = diretorio_de_logs()
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def caminho_do_log(dia: date) -> Path:
    return diretorio_de_logs() / f"sincronizar-{dia:%Y-%m-%d}.log"


def caminho_do_log_da_web() -> Path:
    """O log do servidor. Um so, e nao um por dia: ele e para depurar agora."""
    return diretorio_de_logs() / "web.log"


# O log da web e REESCRITO a cada `radar subir`, e nao continuado. Dois
# motivos: o que eu quero dele e "por que o servidor que esta rodando agora
# nao subiu", e o uvicorn anota uma linha por requisicao - continuando, o
# arquivo cresceria para sempre a cada pagina aberta.
MODO_DO_LOG_DA_WEB = "w"


def hoje() -> date:
    """O dia de hoje em Florianopolis - o dia que da nome ao log."""
    return datetime.now(fuso_local()).date()


# --- o processo do servidor -------------------------------------------------

@dataclass
class Servidor:
    """O que o arquivo de PID guarda sobre o servidor que esta no ar."""

    pid: int
    porta: int
    subiu_em: datetime | None

    @property
    def endereco(self) -> str:
        return f"http://{HOST_PADRAO}:{self.porta}"


def ler_arquivo_do_pid() -> Servidor | None:
    """O que o arquivo diz, sem conferir se o processo ainda existe.

    E JSON dentro de um .pid porque o `radar status` precisa de mais que o
    numero: a porta, para montar o endereco, e a hora em que subiu, para
    dizer "no ar desde". Arquivo estragado vale como arquivo ausente - ele e
    rastro de processo, nao dado meu.
    """
    try:
        dados = json.loads(caminho_do_pid().read_text(encoding="utf-8"))
        pid = int(dados["pid"])
    except (OSError, ValueError, TypeError, KeyError):
        return None

    try:
        subiu_em = datetime.fromisoformat(dados["subiu_em"])
    except (KeyError, TypeError, ValueError):
        subiu_em = None

    try:
        porta = int(dados.get("porta") or PORTA_PADRAO)
    except (TypeError, ValueError):
        porta = PORTA_PADRAO

    return Servidor(pid=pid, porta=porta, subiu_em=subiu_em)


def gravar_arquivo_do_pid(servidor: Servidor) -> Path:
    caminho = caminho_do_pid()
    caminho.write_text(
        json.dumps(
            {
                "pid": servidor.pid,
                "porta": servidor.porta,
                "subiu_em": servidor.subiu_em.isoformat() if servidor.subiu_em else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return caminho


def apagar_arquivo_do_pid() -> None:
    caminho_do_pid().unlink(missing_ok=True)


def e_windows() -> bool:
    """Estou no Windows? Uma pergunta so, num lugar so.

    Existe para o teste poder responder "sim" sem mexer no `os.name`, que e
    global: trocar o `os.name` no meio de um teste mexe no tempfile, no
    pathlib e em tudo mais que pergunta a mesma coisa.
    """
    return os.name == "nt"


# Em que ordem tentar ler a saida de um programa do Windows. UTF-8 primeiro
# porque ele se denuncia: byte que nao e UTF-8 valido nao decodifica, e ai vale
# a proxima. Adivinhar na ordem inversa daria texto errado sem erro nenhum.
CODIFICACOES_DO_WINDOWS = ("utf-8", "oem", "cp1252")


def _decodificar(bruto: bytes) -> str:
    """Le a saida de um programa do Windows sem fixar a pagina de codigo.

    schtasks e tasklist escrevem na pagina do CONSOLE, e ela varia na mesma
    maquina: no Terminal novo e a 65001 (UTF-8), no prompt antigo e a 850.
    Fixar uma delas quebra na outra - e quebrava de dois jeitos: lido como
    UTF-8, o acento da 850 virava o caractere de substituicao e estourava na
    hora de imprimir; lida como 850, a saida em UTF-8 virava "pr├│xima".
    """
    for codificacao in CODIFICACOES_DO_WINDOWS:
        try:
            return bruto.decode(codificacao)
        except (UnicodeDecodeError, LookupError):
            continue      # LookupError: fora do Windows nao existe "oem"
    return bruto.decode("utf-8", errors="replace")


def _rodar(comando: list[str], sem_janela: bool = False) -> subprocess.CompletedProcess:
    """Roda um programa do Windows (schtasks, tasklist) e devolve o resultado.

    Nao estoura nunca: quem chamou decide o que fazer com o codigo de saida. E
    um ponto so, para o teste poder trocar por um falso que anota o comando.

    A saida vem em bytes e passa pelo `_decodificar` de proposito - o `text=True`
    obrigaria a escolher uma pagina de codigo aqui, e nao ha uma certa.

    `sem_janela` importa quando quem chama e a tarefa do Agendador: sem isso,
    todo processo filho abre uma janela preta que pisca na tela as 23h30.
    """
    bruto = subprocess.run(
        comando,
        capture_output=True,
        cwd=str(config.RAIZ),
        creationflags=_bandeira_sem_janela() if sem_janela else 0,
    )
    return subprocess.CompletedProcess(
        comando,
        bruto.returncode,
        stdout=_decodificar(bruto.stdout or b""),
        stderr=_decodificar(bruto.stderr or b""),
    )


def _rodar_python(argumentos: list[str], sem_janela: bool = False) -> subprocess.CompletedProcess:
    """Roda um comando do proprio radar num processo filho, e le a saida em UTF-8.

    O PYTHONIOENCODING existe para eu nao precisar adivinhar pagina de codigo:
    sem ele, o Python filho escreve na cp1252 do Windows, e o log do backup
    sairia com acento quebrado - justamente o arquivo que eu vou ler quando
    algo der errado.
    """
    return subprocess.run(
        [str(python_com_console()), "-m", "radar.cli", *argumentos],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(config.RAIZ),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        creationflags=_bandeira_sem_janela() if sem_janela else 0,
    )


def _bandeira_sem_janela() -> int:
    """CREATE_NO_WINDOW, quando existe. Fora do Windows nao ha janela nenhuma."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if e_windows() else 0


def _bandeira_de_processo_solto() -> int:
    """DETACHED_PROCESS: o servidor nao morre junto com quem o subiu."""
    return getattr(subprocess, "DETACHED_PROCESS", 0) if e_windows() else 0


def processo_vivo(pid: int) -> bool:
    """Existe processo com esse numero, e ele e um Python?

    Conferir o nome nao e exagero: numero de processo se reaproveita. Se o PC
    desligou na tomada, o arquivo fica para tras apontando para um numero que
    amanha pode ser o Bloco de Notas - e `radar parar` mataria o Bloco de
    Notas do usuario.
    """
    if pid <= 0:
        return False

    if not e_windows():
        # Sinal 0 no POSIX nao envia nada: so pergunta se daria para enviar.
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    saida = _rodar(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], sem_janela=True)
    return "python" in (saida.stdout or "").lower()


def no_ar() -> Servidor | None:
    """O servidor que o `radar subir` deixou rodando, se ele ainda esta.

    Arquivo apontando para processo morto e limpo aqui mesmo: e o estado
    normal depois de um desligamento na tomada, e nao um erro para eu ver.
    """
    servidor = ler_arquivo_do_pid()
    if servidor is None:
        return None
    if not processo_vivo(servidor.pid):
        apagar_arquivo_do_pid()
        return None
    return servidor


def python_sem_janela() -> Path:
    """O pythonw.exe do venv: o Python que nao abre janela de console nenhuma.

    E ele que o Agendador chama e ele que segura o servidor no ar. Onde nao
    existe pythonw (Linux, instalacao enxuta), sobra o proprio python - o
    resto do codigo funciona igual, so aparece uma janela.
    """
    atual = Path(sys.executable)
    sem_janela = atual.with_name("pythonw.exe")
    return sem_janela if sem_janela.exists() else atual


def python_com_console() -> Path:
    """O python.exe, para o processo filho cuja saida eu QUERO ler.

    O backup e assim: ele roda o sincronizar e guarda tudo que ele disse. Com
    o pythonw nao ha saida padrao para ler.
    """
    atual = Path(sys.executable)
    com_console = atual.with_name("python.exe")
    return com_console if com_console.exists() else atual


def subir(porta: int = PORTA_PADRAO) -> Servidor:
    """Sobe o `radar web` solto, sem janela, e grava o arquivo de PID.

    A saida vai para data/logs/web.log porque sem janela nao ha onde ler o
    erro: sem esse arquivo, um servidor que nao sobe e silencio puro.
    """
    preparar_logs()
    with caminho_do_log_da_web().open(MODO_DO_LOG_DA_WEB, encoding="utf-8") as saida:
        saida.write(
            f"\n--- subiu em {datetime.now(fuso_local()):%d/%m/%Y %H:%M:%S}, "
            f"porta {porta} ---\n"
        )
        saida.flush()
        processo = subprocess.Popen(
            [
                str(python_sem_janela()), "-m", "radar.cli", "web",
                "--porta", str(porta), "--host", HOST_PADRAO,
            ],
            cwd=str(config.RAIZ),
            stdin=subprocess.DEVNULL,
            stdout=saida,
            stderr=subprocess.STDOUT,
            creationflags=_bandeira_de_processo_solto(),
            close_fds=True,
        )

    servidor = Servidor(pid=processo.pid, porta=porta, subiu_em=datetime.now(fuso_local()))
    gravar_arquivo_do_pid(servidor)
    return servidor


def esperar_subir(servidor: Servidor, segundos: float = 15.0) -> bool:
    """Espera o servidor responder na porta. False quando ele morreu no meio.

    Existe porque sem janela nao ha erro na tela. Se o uvicorn nao subir, o
    unico sinal e a porta que nunca abre - entao o comando confere em vez de
    confiar, e quem chama mostra o fim do web.log.
    """
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if porta_ocupada(HOST_PADRAO, servidor.porta):
            return True
        if not processo_vivo(servidor.pid):
            return False
        time.sleep(0.3)
    return False


def fim_do_log_da_web(linhas: int = 15) -> list[str]:
    """As ultimas linhas do web.log, para explicar um servidor que nao subiu."""
    try:
        texto = caminho_do_log_da_web().read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [linha for linha in texto.splitlines() if linha.strip()][-linhas:]


def parar() -> Servidor | None:
    """Desliga o que o `radar subir` subiu. None quando nao havia nada.

    Forca a parada (`taskkill /F`) porque o servidor nao tem janela nem
    console para receber pedido educado - e nao ha o que perder: o que a tela
    grava, ela grava na hora, dentro de transacao do SQLite.
    """
    servidor = no_ar()
    if servidor is None:
        apagar_arquivo_do_pid()      # limpa o arquivo orfao, se havia um
        return None

    _encerrar(servidor.pid)
    apagar_arquivo_do_pid()
    return servidor


def _encerrar(pid: int) -> None:
    """Mata o processo. O unico lugar daqui que sabe a diferenca de sistema."""
    if e_windows():
        _rodar(["taskkill", "/PID", str(pid), "/F"], sem_janela=True)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


# --- o backup das 23h30 -----------------------------------------------------

@dataclass
class Backup:
    """Como foi o ultimo backup, do jeito que a tela Mais precisa contar."""

    dia: date
    deu_certo: bool
    motivo: str | None
    caminho: Path


def _ultima_linha_util(saida: str) -> str:
    """A linha que explica a falha: a ultima que tem texto.

    O sincronizar imprime o titulo do passo que falhou e, embaixo, a mensagem
    crua do git - e e ela que diz "Could not resolve host: github.com" ou
    "CONFLICT (content)". E ela que eu quero ver na tela.
    """
    linhas = [linha.strip() for linha in (saida or "").splitlines() if linha.strip()]
    if not linhas:
        return "o comando nao disse nada"
    return linhas[-1][:LIMITE_DO_MOTIVO]


def rodar_backup(dia: date | None = None) -> Backup:
    """O backup das 23h30: roda o `radar sincronizar` e guarda a saida dele.

    Nao reimplementa nada do sincronizar - chama o comando, que ja faz pull,
    importar, reclassificar, limpar simulado vazio, exportar, commit e push.
    O que este embrulho acrescenta e o que a tarefa do Agendador nao tem como
    fazer sozinha: o log do dia com nome previsivel (o `%date%` do cmd muda
    de formato com o idioma do Windows), a limpeza dos logs velhos, e a linha
    final dizendo se deu certo - que e o que a tela Mais le.
    """
    dia = dia or hoje()
    preparar_logs()
    caminho = caminho_do_log(dia)

    comeco = datetime.now(fuso_local())
    resultado = _rodar_python(["sincronizar"], sem_janela=True)
    saida = (resultado.stdout or "") + (resultado.stderr or "")
    deu_certo = resultado.returncode == 0
    motivo = None if deu_certo else _ultima_linha_util(saida)

    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(f"=== {comeco:%d/%m/%Y %H:%M:%S} · radar sincronizar\n")
        arquivo.write(saida.rstrip("\n") + "\n")
        arquivo.write((MARCA_OK if deu_certo else MARCA_FALHOU + (motivo or "")) + "\n")

    limpar_logs_velhos(dia_de_hoje=dia)
    return Backup(dia=dia, deu_certo=deu_certo, motivo=motivo, caminho=caminho)


def _dia_do_log(caminho: Path) -> date | None:
    try:
        return date.fromisoformat(caminho.stem.removeprefix("sincronizar-"))
    except ValueError:
        return None


def limpar_logs_velhos(dias: int = DIAS_DE_LOG, dia_de_hoje: date | None = None) -> list[Path]:
    """Apaga log de backup com mais de `dias`. Devolve os que sairam.

    Pela data no NOME, e nao pela data do arquivo: a data do nome e a que o
    backup promete, e ela nao muda quando eu copio a pasta data/ para outra
    maquina. O web.log nao entra - ele e um so e vive de sobrescrita.
    """
    limite = (dia_de_hoje or hoje()) - timedelta(days=dias)
    apagados = []
    for caminho in sorted(diretorio_de_logs().glob("sincronizar-*.log")):
        dia = _dia_do_log(caminho)
        if dia is None or dia >= limite:
            continue
        caminho.unlink(missing_ok=True)
        apagados.append(caminho)
    return apagados


def ultimo_backup() -> Backup | None:
    """Como foi o backup mais recente. None quando nunca rodou nenhum.

    O mais recente e o de maior data NO NOME - que, no formato AAAA-MM-DD, e
    o ultimo em ordem alfabetica. Ordenar pela data de modificacao daria
    outra resposta so por eu ter copiado a pasta.
    """
    logs = sorted(diretorio_de_logs().glob("sincronizar-*.log"))
    if not logs:
        return None

    caminho = logs[-1]
    dia = _dia_do_log(caminho) or hoje()
    try:
        # utf-8-sig e nao utf-8: se eu abrir o log no Bloco de Notas ou
        # reescrever com o PowerShell, ele volta com a marca de BOM na frente,
        # e ai a primeira linha nunca comeca com o que eu procuro.
        texto = caminho.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None

    marca = next(
        (linha.strip() for linha in reversed(texto.splitlines())
         if linha.strip().startswith("RESULTADO:")),
        None,
    )
    if marca is None:
        # Log sem a linha final: o backup comecou e o processo morreu no meio
        # (PC desligado na tomada as 23h31). Isso e falha, e sem motivo claro.
        return Backup(dia, False, "o backup nao terminou (o log nao tem a linha final)",
                      caminho)
    if marca == MARCA_OK:
        return Backup(dia, True, None, caminho)
    return Backup(dia, False, marca.removeprefix(MARCA_FALHOU).strip() or None, caminho)


# --- as duas tarefas do Agendador -------------------------------------------
#
# Por que XML e nao a linha de comando do schtasks: `schtasks /Create /SC
# DAILY /ST 23:30` nao tem opcao para "executar assim que possivel se o
# horario foi perdido". Esse StartWhenAvailable so entra por arquivo - e e
# exatamente ele que faz o backup rodar quando eu ligo o PC de manha depois de
# ter dormido com ele desligado.

MODELO_DA_TAREFA = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>{usuario}</Author>
    <Description>{descricao}</Description>
  </RegistrationInfo>
  <Triggers>
{gatilho}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{usuario}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>{limite}</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{comando}</Command>
      <Arguments>{argumentos}</Arguments>
      <WorkingDirectory>{pasta}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

GATILHO_NO_LOGON = """    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{usuario}</UserId>
    </LogonTrigger>"""

GATILHO_DIARIO = """    <CalendarTrigger>
      <StartBoundary>{inicio}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""


def usuario_do_windows() -> str:
    """DOMINIO\\usuario, do jeito que o Agendador escreve o dono da tarefa.

    Tarefa do proprio usuario qualquer um cria: nao ha UAC, nao ha "executar
    como administrador". Era metade do motivo de nao ser servico do Windows.
    """
    nome = os.environ.get("USERNAME") or os.environ.get("USER") or "usuario"
    dominio = os.environ.get("USERDOMAIN") or os.environ.get("COMPUTERNAME")
    return f"{dominio}\\{nome}" if dominio else nome


def xml_da_tarefa_web(usuario: str | None = None) -> str:
    """A tarefa que sobe o radar quando eu faco logon.

    Chama o pythonw.exe deste modulo, e nao o `radar.bat`: o .bat abriria uma
    janela preta em todo logon. O limite de execucao e PT0S - ou seja,
    nenhum: o Agendador considera a tarefa rodando enquanto o servidor viver,
    e qualquer limite mataria o radar no meio do dia.
    """
    usuario = escapar_xml(usuario or usuario_do_windows())
    return MODELO_DA_TAREFA.format(
        usuario=usuario,
        descricao="Sobe o Radar de Concursos em segundo plano, sem janela, ao fazer logon.",
        gatilho=GATILHO_NO_LOGON.format(usuario=usuario),
        limite="PT0S",
        comando=escapar_xml(str(python_sem_janela())),
        argumentos=escapar_xml("-m radar.automacao"),
        pasta=escapar_xml(str(config.RAIZ)),
    )


def xml_da_tarefa_backup(usuario: str | None = None, dia: date | None = None) -> str:
    """A tarefa do backup diario as 23h30.

    O StartBoundary precisa de uma data para comecar a contar; vale a de hoje,
    e o que manda no dia a dia e o ScheduleByDay. Uma hora de limite: um
    sincronizar que travou numa credencial nao pode ficar pendurado ate amanha.
    """
    usuario = escapar_xml(usuario or usuario_do_windows())
    dia = dia or hoje()
    return MODELO_DA_TAREFA.format(
        usuario=usuario,
        descricao=(
            f"Backup do Radar de Concursos: roda o `radar sincronizar` todo dia as "
            f"{HORA_DO_BACKUP} e guarda a saida em data/logs/."
        ),
        gatilho=GATILHO_DIARIO.format(inicio=f"{dia:%Y-%m-%d}T{HORA_DO_BACKUP}:00"),
        limite="PT1H",
        comando=escapar_xml(str(python_sem_janela())),
        argumentos=escapar_xml("-m radar.automacao --backup"),
        pasta=escapar_xml(str(config.RAIZ)),
    )


def tarefas() -> dict[str, str]:
    """As duas tarefas, nome -> XML. A CLI percorre e vai criando."""
    return {TAREFA_WEB: xml_da_tarefa_web(), TAREFA_BACKUP: xml_da_tarefa_backup()}


def criar_tarefa(nome: str, xml: str) -> subprocess.CompletedProcess:
    """Registra a tarefa no Agendador, a partir do XML.

    O arquivo sai em UTF-16 porque o schtasks nao le UTF-8: com UTF-8 ele
    responde "o XML da tarefa contem um valor formatado incorretamente", que
    nao ajuda ninguem a descobrir que o problema era a codificacao. O /F
    sobrescreve a tarefa que ja existe, para eu poder rodar `radar agendar`
    de novo depois de mudar de pasta ou de recriar o venv.
    """
    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "tarefa.xml"
        caminho.write_text(xml, encoding="utf-16")
        return _rodar(["schtasks", "/Create", "/TN", nome, "/XML", str(caminho), "/F"])


def remover_tarefa(nome: str) -> subprocess.CompletedProcess:
    return _rodar(["schtasks", "/Delete", "/TN", nome, "/F"])


def consultar_tarefa(nome: str) -> dict[str, str] | None:
    """O que o Agendador diz da tarefa, ou None quando ela nao existe.

    Devolve os campos como o Windows os escreve, sem traduzir nem procurar
    nome de campo: o schtasks fala no idioma do sistema, e um `if campo ==
    "Next Run Time"` quebraria justamente nesta maquina, que esta em portugues.
    """
    saida = _rodar(["schtasks", "/Query", "/TN", nome, "/FO", "LIST"])
    if saida.returncode != 0:
        return None
    campos = {}
    for linha in (saida.stdout or "").splitlines():
        if ":" in linha:
            chave, _, valor = linha.partition(":")
            if chave.strip() and valor.strip():
                campos[chave.strip()] = valor.strip()
    return campos or None


# --- os dois atalhos na Area de Trabalho ------------------------------------

ATALHOS = {
    "Radar.bat": ("subir --abrir", "Sobe o Radar e abre a tela Hoje no navegador."),
    "Parar o Radar.bat": ("parar", "Desliga o Radar que esta rodando em segundo plano."),
}


def diretorio_da_area_de_trabalho() -> Path:
    """A Area de Trabalho de verdade, mesmo quando o OneDrive a mudou de lugar.

    Pergunta ao registro do Windows em vez de montar %USERPROFILE%\\Desktop:
    com o OneDrive ligado, a pasta real e OneDrive\\Desktop, e um atalho
    escrito no caminho antigo simplesmente nao aparece na tela.
    """
    if e_windows():
        try:
            import winreg

            chave = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, chave) as aberta:
                valor, _ = winreg.QueryValueEx(aberta, "Desktop")
            if valor:
                return Path(valor)
        except OSError:
            pass
    return Path(os.environ.get("USERPROFILE") or Path.home()) / "Desktop"


def texto_do_atalho(argumentos: str, descricao: str) -> str:
    """O .bat da Area de Trabalho: uma linha util e nada de esperto.

    Chama o radar.bat da pasta do projeto, que e quem sabe achar o venv - o
    mesmo atalho que eu uso no terminal. O `pause` so no erro: no caminho
    normal a janela abre e fecha sozinha, e no ruim ela fica aberta com a
    mensagem na tela em vez de piscar e desaparecer.
    """
    return (
        "@echo off\r\n"
        f"REM {descricao}\r\n"
        "REM Criado por `radar agendar`. Apagar este arquivo nao quebra nada.\r\n"
        f'call "{config.RAIZ / "radar.bat"}" {argumentos}\r\n'
        "if errorlevel 1 pause\r\n"
    )


def criar_atalhos() -> list[Path]:
    """Escreve os dois .bat na Area de Trabalho e devolve onde ficaram."""
    pasta = diretorio_da_area_de_trabalho()
    pasta.mkdir(parents=True, exist_ok=True)
    criados = []
    for nome, (argumentos, descricao) in ATALHOS.items():
        caminho = pasta / nome
        caminho.write_text(texto_do_atalho(argumentos, descricao),
                           encoding="utf-8", newline="")
        criados.append(caminho)
    return criados


def apagar_atalhos() -> list[Path]:
    """Apaga os dois .bat. Devolve so os que existiam de verdade."""
    pasta = diretorio_da_area_de_trabalho()
    apagados = []
    for nome in ATALHOS:
        caminho = pasta / nome
        if caminho.exists():
            caminho.unlink()
            apagados.append(caminho)
    return apagados


if __name__ == "__main__":
    # E por aqui que as duas tarefas do Agendador entram. Elas chamam o
    # pythonw.exe, que nao tem console: nada aqui pode imprimir - nem um
    # print, nem o rich da CLI, que estouraria escrevendo num stdout que nao
    # existe. Quem quiser ler o que aconteceu le o log em data/logs/.
    if "--backup" in sys.argv[1:]:
        rodar_backup()
    elif not no_ar():
        subir()
