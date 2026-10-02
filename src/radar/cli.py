"""Linha de comando do radar.

    radar coletar
    radar listar --uf SC --termo "guarda municipal"
    radar web
"""
import logging
import subprocess
from datetime import date, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from radar import acervo, alvo as alvos, automacao, avisos, config, cronograma, servico
from radar import provas as _provas
from radar.models import agora
from radar.util import (
    dias_ate,
    formatar_data,
    fuso_local,
    ip_local,
    para_local,
    porta_ocupada,
    primeira_porta_livre,
)


def _prazo(quando) -> str:
    """Data de fechamento com o aviso de urgencia junto."""
    if quando is None:
        return "--"
    faltam = dias_ate(quando)
    texto = formatar_data(quando)
    if faltam < 0:
        return f"[dim]{texto}[/]"
    if faltam <= 7:
        return f"[bold red]{texto} ({faltam}d)[/]"
    return f"{texto} ({faltam}d)"

app = typer.Typer(help="Radar de concursos publicos (uso pessoal)", no_args_is_help=True)
console = Console()
log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@app.command()
def coletar() -> None:
    """Busca nas fontes e grava os concursos novos e os que mudaram."""
    with console.status("Coletando..."):
        resultados = servico.coletar_tudo()

    houve_erro = False
    for resultado in resultados:
        if resultado.erro:
            houve_erro = True
            console.print(f"[red]{resultado}[/]")
        else:
            console.print(f"[green]{resultado}[/]")

    if houve_erro:
        console.print(
            "\n[yellow]Uma ou mais fontes falharam.[/] As demais foram gravadas "
            "normalmente."
        )


# O nome do campo e cru de proposito (vai para o banco); na tela vira gente.
SITUACAO_LEGIVEL = {
    "prevista": "previsto",
    "autorizado": "autorizado",
    "banca_definida": "banca contratada",
    "edital_publicado": "edital publicado",
    "inscricoes_abertas": "inscricoes abertas",
    "encerrado": "encerrado",
    "desconhecida": "-",
}

ROTULO_DO_ANEL = {
    "nucleo": "Perto",
    "proximo": "Proximo",
    "estadual": "Estadual SC",
    "remoto": "Longe",
    "indefinida": "A confirmar",
}

CORES_DO_ANEL = {
    "nucleo": "bold green",
    "proximo": "yellow",
    "estadual": "bold magenta",
    "remoto": "dim",
    "indefinida": "magenta",
}


@app.command()
def atualizar(
    completo: bool = typer.Option(
        False, "--completo",
        help="Tambem baixa provas novas e le as questoes delas (demora)",
    ),
    avisar_telegram: bool = typer.Option(
        False,
        "--avisar/--sem-avisar",
        help="Manda no Telegram (por padrao NAO manda: quem avisa e o robo)",
    ),
) -> None:
    """Roda a rotina inteira, na ordem certa. Sem mandar mensagem.

    Existe porque manter o radar em dia exigia seis comandos numa sequencia que
    so fazia sentido para quem a escreveu: coletar antes de detalhar, detalhar
    antes de baixar edital, edital antes de elegibilidade.

    **Nao avisa no Telegram por padrao.** Quem manda mensagem e o robo do
    GitHub, uma vez por dia, e ele e o unico - com os dois avisando, o mesmo
    concurso chegava duas vezes no celular, porque cada um guardava a sua
    propria lista do que ja tinha avisado. Para mandar daqui assim mesmo, use
    `--avisar`.

    Cada etapa que falha e registrada e a rotina segue - a mesma regra que vale
    para fonte fora do ar desde a primeira fase. O resumo no fim diz o que deu
    certo e o que nao.
    """
    etapas = [
        ("Coletando das fontes", lambda: str(_resumo_da_coleta())),
        ("Lendo a pagina dos concursos novos",
         lambda: str(servico.detalhar_pendentes(limite=15))),
        ("Baixando edital de concurso aberto",
         lambda: str(servico.montar_acervo(limite=5, abertos=True))),
        ("Lendo o que o edital exige",
         lambda: str(servico.ler_elegibilidade(limite=30))),
        ("Conferindo retificacao de edital",
         lambda: str(servico.conferir_retificacoes(limite=10))),
    ]

    if avisar_telegram:
        # Dois avisos, e nesta ordem: primeiro o que mudou no que eu JA sigo,
        # depois o que apareceu de novo. Se o teto do dia cortar alguma coisa,
        # que corte a descoberta, e nao a mudanca no meu favorito.
        etapas.append(
            ("Avisando mudanca nos favoritos",
             lambda: str(servico.avisar_favoritos()))
        )
        etapas.append(("Avisando no Telegram", lambda: str(servico.avisar())))

    if completo:
        etapas.append(
            ("Montando o acervo de provas", lambda: str(servico.montar_acervo(limite=10)))
        )
        etapas.append(
            ("Extraindo questoes dos cadernos",
             lambda: str(servico.extrair_questoes(limite=20)))
        )

    falhas = 0
    for numero, (titulo, acao) in enumerate(etapas, start=1):
        console.print(f"\n[bold cyan]{numero}/{len(etapas)}[/] {titulo}")
        try:
            with console.status(titulo + "..."):
                resumo = acao()
            console.print(f"   [green]{resumo}[/]")
        except Exception as erro:  # noqa: BLE001 - etapa quebrada nao para a rotina
            falhas += 1
            console.print(f"   [red]falhou: {type(erro).__name__}[/]")
            log.warning("etapa %r falhou", titulo, exc_info=True)

    console.print()
    if falhas:
        console.print(f"[yellow]Terminei com {falhas} etapa(s) com problema.[/]")
    else:
        console.print("[green]Tudo em dia.[/]")

    abertas = len(servico.listar(abertas=True, todas_relevancias=True))
    console.print(f"[bold]{abertas}[/] concurso(s) com inscricao aberta agora.")
    console.print("[dim]Veja na tela: radar web[/]")


def _resumo_da_coleta() -> str:
    """Uma linha com o que cada fonte trouxe."""
    return " | ".join(
        f"{r.fonte}: {r.novos} novo(s)" for r in servico.coletar_tudo()
    )


@app.command()
def listar(
    uf: str = typer.Option(None, help="Sigla do estado, ex: SC"),
    banca: str = typer.Option(None, help="Nome da banca, ex: FEPESE"),
    termo: str = typer.Option(None, help="Palavra no titulo ou no resumo"),
    situacao: str = typer.Option(None, help="Ex: edital_publicado, autorizado"),
    relevancia: str = typer.Option(
        None, help="nucleo, proximo, estadual, remoto ou indefinida"
    ),
    todos: bool = typer.Option(
        False, "--todos", help="Mostra todos os aneis, nao so o que e perto"
    ),
    noticias: bool = typer.Option(
        False, "--noticias", help="Inclui o que o filtro marcou como noticia"
    ),
    abertas: bool = typer.Option(
        False, "--abertas", help="So o que da para se inscrever hoje"
    ),
    favoritos: bool = typer.Option(
        False, "--favoritos", help="So os que eu marquei como favoritos"
    ),
    salario_min: float = typer.Option(
        None, "--salario-min", help="Remuneracao minima, ex: 5000"
    ),
    limite: int = typer.Option(30, help="Quantidade maxima de linhas"),
) -> None:
    """Mostra o que ja esta no banco.

    Por padrao so aparece o que esta perto (nucleo e proximo). Use --todos
    para ver o resto.
    """
    itens = servico.listar(
        uf=uf, banca=banca, termo=termo, situacao=situacao,
        relevancia=relevancia, todas_relevancias=todos,
        incluir_noticias=noticias, abertas=abertas, favoritos=favoritos,
        salario_min=salario_min, limite=limite,
    )

    tabela = Table(title=f"{len(itens)} concurso(s)")
    # O id aparece para dar para favoritar pelo terminal: radar favoritar <id>
    tabela.add_column("id", style="dim", no_wrap=True)
    tabela.add_column("Onde", no_wrap=True)
    tabela.add_column("Salario", justify="right", no_wrap=True)
    tabela.add_column("Inscricao ate", no_wrap=True)
    tabela.add_column("Status", no_wrap=True)
    tabela.add_column("Titulo")

    for c in itens:
        cor = CORES_DO_ANEL.get(c.relevancia, "")
        salario = f"{c.salario:,.0f}".replace(",", ".") if c.salario else "--"
        estrela = "*" if c.interesse == servico.FAVORITO else " "
        tabela.add_row(
            f"{estrela}{c.id}",
            f"[{cor}]{ROTULO_DO_ANEL.get(c.relevancia, c.relevancia)}[/]",
            salario,
            _prazo(c.inscricoes_ate),
            SITUACAO_LEGIVEL.get(c.situacao, c.situacao),
            c.titulo,
        )

    console.print(tabela)

    if not itens and not todos:
        contagem = servico.contar_por_relevancia()
        fora = contagem["remoto"] + contagem["indefinida"]
        if fora:
            console.print(
                f"\n[yellow]Nada perto de voce por enquanto.[/] Ha {fora} "
                f"concurso(s) em outras regioes: use [bold]radar listar --todos[/]"
            )


@app.command()
def carga_inicial(
    dias: int = typer.Option(90, help="Quantos dias de historico buscar"),
    sim: bool = typer.Option(False, "--sim", help="Nao perguntar antes de comecar"),
) -> None:
    """Traz o historico que a coleta diaria nao pegou.

    O RSS e um fluxo: mostra so o que e recente. Quem liga o radar hoje ve os
    concursos de hoje e nada de antes. Este comando anda para tras no feed,
    pagina por pagina, e preenche esse buraco.

    Roda uma vez so, na mao. Demora alguns minutos: ha uma pausa entre as
    requisicoes para nao sobrecarregar o site.
    """
    paginas = min(dias * servico.PAGINAS_POR_DIA, 400)
    minutos = paginas * 1.5 / 60

    console.print(
        f"Vou buscar [bold]{dias} dias[/] de historico: ate {paginas} paginas "
        f"do feed, com pausa de 1,5s entre elas.\n"
        f"Tempo estimado: [bold]{minutos:.0f} minuto(s)[/]. Ctrl+C para parar."
    )
    if not sim and not typer.confirm("Comecar?", default=True):
        raise typer.Abort()

    with console.status("Lendo o feed para tras..."):
        resultado = servico.carga_inicial(dias=dias)

    console.print(f"[red]{resultado}[/]" if resultado.erro else f"[green]{resultado}[/]")

    contagem = servico.contar_por_relevancia()
    console.print(
        f"\nNo banco agora: [bold green]{contagem['nucleo']}[/] perto, "
        f"[bold yellow]{contagem['proximo']}[/] proximo, "
        f"{contagem['remoto']} longe, {contagem['indefinida']} a confirmar."
    )


@app.command()
def provas(
    limite: int = typer.Option(20, help="Quantos concursos ler nesta rodada"),
    abertos: bool = typer.Option(
        False, "--abertos",
        help="Inclui concurso ainda em andamento, para pegar o edital dele",
    ),
    revisitar: bool = typer.Option(
        False, "--revisitar",
        help="Le de novo hotsite que ja esta no acervo, atras de documento novo",
    ),
) -> None:
    """Monta o acervo: le os hotsites e baixa edital, prova e gabarito.

    Comeca pelo alvo principal de config/alvo.yml, esteja ele onde estiver.
    Depois vem o concurso ja encerrado perto de casa - os que tem prova
    publicada e mostram o padrao da banca na minha regiao.

    Os PDFs ficam em data/provas/ e NAO vao para o git. O que e versionado e o
    manifesto data/provas.json, com o sha256 de cada arquivo.
    """
    console.print(
        f"Vou ler ate [bold]{limite}[/] concurso(s). Cada um custa 3 paginas "
        f"mais os PDFs, com pausa de 1,5s entre as requisicoes."
    )
    if revisitar:
        console.print(
            "[dim]Revisitando: hotsite ja lido entra de novo. E assim que "
            "gabarito definitivo publicado depois da prova aparece.[/]"
        )

    with console.status("Montando o acervo..."):
        resultado = servico.montar_acervo(
            limite=limite, abertos=abertos, revisitar=revisitar
        )

    console.print(f"[green]{resultado}[/]")

    if resultado.documentos:
        total = len(_provas.carregar_manifesto())
        console.print(
            f"\nAcervo agora: [bold]{total}[/] documento(s) em "
            f"[bold]{_provas.diretorio_provas()}[/]"
        )


@app.command()
def baixar_provas(
    forcar: bool = typer.Option(False, "--forcar", help="Rebaixa o que ja existe"),
) -> None:
    """Reconstroi o acervo em disco a partir do manifesto.

    E o que torna os PDFs descartaveis: eles nao vao para o git, mas qualquer
    maquina refaz a pasta inteira a partir de data/provas.json.
    """
    contagem = servico.baixar_do_manifesto(forcar=forcar)

    if not contagem["total"]:
        console.print(
            "[yellow]Manifesto vazio.[/] Rode [bold]radar provas[/] primeiro."
        )
        return

    console.print(
        f"[green]{contagem['baixados']}[/] baixado(s), "
        f"{contagem['ja_tinha']} ja estava(m) no disco"
        + (f", [red]{contagem['falhas']}[/] falhou/falharam" if contagem["falhas"] else "")
    )


@app.command()
def questoes(
    limite: int = typer.Option(30, help="Quantas provas ler nesta rodada"),
    refazer: bool = typer.Option(
        False, "--refazer", help="Le de novo os cadernos que ja viraram questao"
    ),
) -> None:
    """Separa os cadernos do acervo em questoes, com materia e gabarito.

    Nao vai a internet: trabalha nos PDFs que `radar provas` ja baixou.

    Use --refazer depois de melhorar a leitura do caderno: as questoes sao
    atualizadas no lugar, sem perder o id que o simulado guarda.
    """
    with console.status("Lendo os cadernos..."):
        resultado = servico.extrair_questoes(limite=limite, refazer=refazer)

    console.print(f"[green]{resultado}[/]")
    total = servico.contar_questoes()
    if total:
        console.print(f"\nBanco de questoes: [bold]{total}[/] questao(oes)")


@app.command()
def previsao() -> None:
    """Onde vale ficar de olho: municipio parado ha tempo demais.

    A conta usa o ritmo do proprio municipio, limitado pela validade legal do
    concurso: ate 2 anos, prorrogaveis por mais 2.
    """
    previsoes = servico.previsao_de_abertura()
    if not previsoes:
        console.print("[yellow]Nenhum municipio com historico ainda.[/]")
        return

    cores = {"atrasado": "red", "esperado": "yellow", "em_dia": "green"}
    rotulos = {"atrasado": "ATRASADO", "esperado": "JANELA  ", "em_dia": "em dia  "}

    for p in previsoes:
        cor = cores[p.situacao]
        console.print(
            f"[{cor}]{rotulos[p.situacao]}[/] [bold]{p.municipio}[/] "
            f"[dim]-> {p.proximo_previsto}[/]"
        )
        console.print(f"          [dim]{p.motivo}[/]")

    console.print()
    console.print(
        "[dim]O historico vem da FEPESE (2006-2026) e do feed (so 2026). "
        "Municipio que usou outra banca entre 2021 e 2025 aparece mais "
        "atrasado do que e.[/]"
    )


@app.command()
def elegibilidade(
    limite: int = typer.Option(50, help="Quantos concursos ler nesta rodada"),
    refazer: bool = typer.Option(
        False, "--refazer", help="Le de novo os que ja tem exigencias gravadas"
    ),
) -> None:
    """Le os editais do acervo e grava o que cada concurso exige.

    Escolaridade, idade, CNH e teste fisico. Nao vai a internet: trabalha nos
    PDFs que `radar provas` ja baixou.
    """
    with console.status("Lendo os editais..."):
        resultado = servico.ler_elegibilidade(limite=limite, refazer=refazer)

    console.print(f"[green]{resultado}[/]")


@app.command()
def calendario(
    arquivo: str = typer.Option("radar.ics", help="Onde gravar o arquivo"),
) -> None:
    """Exporta os prazos para o calendario, em .ics.

    Entra o que e favorito e o que esta perto de casa, com prazo conhecido e
    ainda em pe. O arquivo abre no Google Agenda, no calendario do iPhone e no
    Outlook.
    """
    from pathlib import Path as _Caminho

    eventos = servico.eventos_do_calendario()
    if not eventos:
        console.print("[yellow]Nenhum prazo em pe para exportar.[/]")
        return

    destino = _Caminho(arquivo)
    destino.write_text(servico.calendario_ics(), encoding="utf-8", newline="")
    console.print(
        f"[green]{len(eventos)} compromisso(s)[/] em [bold]{destino}[/]"
    )
    console.print("[dim]Abra o arquivo para importar no seu calendario.[/]")


@app.command()
def parecidas(
    cargo: str = typer.Argument(..., help="O cargo que eu quero prestar"),
    banca: str = typer.Option(None, help="Filtra por banca, ex: FEPESE"),
) -> None:
    """Qual prova do acervo mais se parece com o cargo que eu quero.

    Existe porque cargo que eu quero costuma nao ter prova no acervo -
    Guarda Municipal ainda nao tem nenhuma. A Policia Penal saiu dessa lista
    quando o alvo principal passou a entrar no acervo mesmo estando longe. A
    lista mostra o que existe e em cima de que a semelhanca foi medida -
    dividir uma palavra no nome nao faz duas profissoes serem a mesma coisa.
    """
    achadas = servico.provas_parecidas(cargo, banca=banca)

    if not achadas:
        console.print(f"[yellow]{servico.recado_sobre_o_cargo(cargo, achadas)}[/]")
        return

    for parecida in achadas:
        marca = "[green]=[/]" if parecida.exata else "[dim]~[/]"
        console.print(
            f"{marca} [bold]{parecida.cargo}[/] "
            f"[dim]{parecida.banca or '-'} / {parecida.municipio or '-'} / "
            f"{parecida.ano or '-'} / {parecida.questoes} questoes[/]"
        )
        console.print(f"    [dim]{parecida.motivo}[/]")


@app.command()
def retificacoes(
    limite: int = typer.Option(20, help="Quantos editais conferir nesta rodada"),
    avisar: bool = typer.Option(
        False, "--avisar", help="Manda o que mudou para o Telegram"
    ),
) -> None:
    """Confere se algum edital em pe mudou desde que eu baixei.

    Retificacao muda prazo, vaga e requisito. O manifesto ja guarda o sha256 de
    cada arquivo: se o mesmo endereco devolve bytes diferentes, o edital foi
    retificado.
    """
    with console.status("Reconferindo os editais..."):
        resultado = servico.conferir_retificacoes(limite=limite)

    console.print(f"[green]{resultado}[/]")
    for mudou in resultado.mudaram:
        console.print()
        console.print(f"[bold red]RETIFICADO[/] {mudou.titulo}")
        console.print(f"  [dim]{mudou.arquivo}[/]")
        console.print(f"  [dim]{mudou.url}[/]")

    if avisar and resultado.mudaram:
        from radar import avisos

        enviadas = sum(avisos.enviar_varios(
            [avisos.formatar_retificacao(m) for m in resultado.mudaram]
        ))
        console.print()
        console.print(f"[green]{enviadas} aviso(s) enviado(s).[/]")


@app.command()
def assuntos(
    limite: int = typer.Option(
        None, help="Quantas questoes classificar. Sem isso, todas as pendentes"
    ),
    teto: float = typer.Option(
        0.50, help="Teto de gasto em dolar. O comando para ao chegar nele"
    ),
    simular: bool = typer.Option(
        True, "--simular/--valendo",
        help="Simular NAO gasta nada: so mostra o custo. Use --valendo para rodar",
    ),
    so_alvo: bool = typer.Option(
        False, "--so-alvo",
        help="So as questoes das provas do meu cargo, no meu estado",
    ),
) -> None:
    """Classifica o assunto fino das questoes de Conhecimentos Especificos.

    Esta e a UNICA parte do radar que custa dinheiro. Por padrao ela so simula:
    para gastar de verdade e preciso passar --valendo.

    Com `--so-alvo` sao duas mudancas, e as duas importam. Entram so as
    questoes das provas do MEU cargo no MEU estado - 99 em vez de 2.802 - e a
    IA passa a ESCOLHER o assunto dentro do conteudo programatico do edital,
    em vez de inventar um nome. Assunto que nao esta na lista e descartado.

    A chave vai em RADAR_ANTHROPIC_KEY, no .env - nunca no codigo.
    """
    from radar import assuntos as classificador, config as configuracao

    pendentes = servico.questoes_sem_assunto(limite, so_alvo=so_alvo)
    permitidos = servico.assuntos_permitidos(so_alvo)

    if so_alvo and not permitidos:
        console.print(
            "[red]Nao li o conteudo programatico do edital do alvo.[/] "
            "Sem a lista, a IA voltaria a inventar nome de assunto - entao "
            "nao gasto."
        )
        raise typer.Exit(code=1)

    if not pendentes:
        console.print("[green]Nenhuma questao pendente de assunto.[/]")
        return

    entrada, saida, custo = classificador.estimar(pendentes, permitidos)
    console.print(f"Questoes a classificar: [bold]{len(pendentes)}[/]")
    if permitidos:
        quantos = sum(len(v) for v in permitidos.values())
        console.print(
            f"[dim]Escolhendo dentro de {quantos} assunto(s) do edital, "
            f"em {len(permitidos)} materia(s)[/]"
        )
    console.print(
        f"[dim]{entrada:,} tokens de entrada, {saida:,} de saida[/]".replace(",", ".")
    )
    console.print(
        f"Custo estimado: [bold]US$ {custo:.2f}[/] "
        f"[dim](~R$ {custo * config.CAMBIO_DE_REFERENCIA:.2f}, cambio fixo de {config.CAMBIO_DE_REFERENCIA:.2f})[/]"
    )
    console.print(f"[dim]Modelo: {classificador.MODELO}[/]")

    if simular:
        console.print()
        console.print("[yellow]Isto foi so uma simulacao: nada foi gasto.[/]")
        comando = "radar assuntos --valendo"
        if so_alvo:
            comando += " --so-alvo"
        console.print(f"Para valer, rode: [bold]{comando}[/]")
        return

    if not configuracao.chave_da_anthropic():
        console.print()
        console.print(
            "[red]Falta a chave.[/] Ponha RADAR_ANTHROPIC_KEY no .env "
            "e rode de novo."
        )
        console.print("[dim]Veja COMO_LIGAR_A_IA.txt para o passo a passo.[/]")
        raise typer.Exit(code=1)

    console.print()
    console.print(f"[dim]Teto de gasto: US$ {teto:.2f}[/]")
    with console.status("Classificando..."):
        resultado = servico.classificar_assuntos(
            limite=limite, teto_em_dolar=teto, so_alvo=so_alvo
        )

    console.print(
        f"[green]{resultado['classificados']} questao(oes) classificada(s)[/], "
        f"{resultado['gravados']} linha(s) do banco atualizada(s)"
    )
    console.print(
        f"Gasto real: [bold]US$ {resultado['custo']:.4f}[/] "
        f"[dim](~R$ {resultado['custo'] * config.CAMBIO_DE_REFERENCIA:.2f}) em "
        f"{resultado['chamadas']} chamada(s)[/]"
    )
    if resultado.get("parou_no_teto"):
        console.print(
            "[yellow]Parei no teto de gasto.[/] Rode de novo para continuar."
        )
    if resultado.get("guardados"):
        console.print(
            f"[dim]{resultado['guardados']} assunto(s) guardados em "
            f"data/assuntos.json - este arquivo e versionado, e e o que "
            f"impede eu pagar de novo pela mesma questao.[/]"
        )
    if resultado.get("falhas"):
        console.print(f"[dim]{resultado['falhas']} lote(s) falharam.[/]")

    _mostrar_cobertura(so_alvo)


# De onde sai o assunto de cada materia, na tela.
ROTULO_DA_ORIGEM = {
    "catalogo": "catalogo (de graca)",
    # "custa", e nao "pago": a coluna diz por qual caminho o assunto sai,
    # e nao que ele ja foi comprado. A diferenca ficou cara em 24/09.
    "edital": "edital (custa)",
    "fora": "fora do programa de hoje",
}


def _mostrar_cobertura(so_alvo: bool = True) -> None:
    """Quanto de cada materia ja tem assunto, da pior para a melhor."""
    cobertura = servico.cobertura_de_assunto(so_alvo=so_alvo)
    if not cobertura:
        return

    tabela = Table(
        title=("Cobertura de assunto nas provas do meu cargo" if so_alvo
               else "Cobertura de assunto no acervo inteiro"),
        box=None,
    )
    tabela.add_column("Materia")
    tabela.add_column("Com assunto", justify="right")
    tabela.add_column("Questoes", justify="right")
    tabela.add_column("%", justify="right")
    tabela.add_column("De onde")

    for linha in cobertura:
        tabela.add_row(
            linha.materia,
            str(linha.com_assunto),
            str(linha.questoes),
            f"{linha.porcentagem:.0f}%",
            ROTULO_DA_ORIGEM.get(linha.origem, linha.origem),
        )

    total = sum(c.questoes for c in cobertura)
    com = sum(c.com_assunto for c in cobertura)
    console.print()
    console.print(tabela)
    console.print(
        f"[bold]{com}[/] de [bold]{total}[/] questao(oes) com assunto "
        f"([bold]{(com / total * 100) if total else 0:.0f}%[/])"
    )


@app.command()
def cobertura(
    so_alvo: bool = typer.Option(
        True, "--so-alvo/--tudo",
        help="So as provas do meu cargo (padrao), ou o acervo inteiro",
    ),
) -> None:
    """Quantas questoes ja tem assunto, por materia.

    Duas origens na mesma tabela, com a coluna dizendo qual e qual: Portugues
    e Raciocinio Logico saem do catalogo de palavras-chave, de graca; as
    outras saem do conteudo programatico do edital, e foram pagas.
    """
    _mostrar_cobertura(so_alvo)


def _materias_curtas(materias: list[str], quantas: int = 3) -> str:
    """As tres primeiras materias e "+N": a lista inteira nao cabe na linha."""
    if not materias:
        return "-"
    texto = ", ".join(materias[:quantas])
    return texto + (f" +{len(materias) - quantas}" if len(materias) > quantas else "")


@app.command()
def simulados() -> None:
    """Lista as rodadas que existem: id, data, questoes, acerto e materias.

    E o que eu olho antes de `radar descartar`, para saber qual id apagar.
    """
    rodadas = servico.listar_simulados()
    if not rodadas:
        console.print("[yellow]Nenhum simulado.[/]")
        return

    tabela = Table(title=f"{len(rodadas)} simulado(s)")
    tabela.add_column("id", justify="right")
    tabela.add_column("Data")
    tabela.add_column("Questoes", justify="right")
    tabela.add_column("Respondidas", justify="right")
    tabela.add_column("Acerto", justify="right")
    tabela.add_column("Materias")
    for r in rodadas:
        acerto = f"{r.porcentagem:.0f}%" if r.porcentagem is not None else "-"
        materias = _materias_curtas(r.materias)
        if r.gerada:
            materias = "[red]IA[/] " + materias
        tabela.add_row(
            str(r.id), formatar_data(r.criado_em), str(r.questoes),
            str(r.respondidas), acerto, materias,
        )
    console.print(tabela)


@app.command()
def descartar(
    simulado_id: int = typer.Argument(None, help="O id, de `radar simulados`"),
    todos: bool = typer.Option(False, "--todos", help="Apaga TODAS as rodadas"),
    vazios: bool = typer.Option(
        False, "--vazios",
        help="Apaga so as rodadas sem nenhuma resposta, criadas ha mais de 1 dia",
    ),
    sim: bool = typer.Option(False, "--sim", help="Nao pergunta antes de apagar"),
) -> None:
    """Apaga um simulado e as respostas dele - de verdade, e sem volta.

    Para rodada de teste, chutada so para ver a tela: ela estraga a taxa de
    acerto, a prioridade da home e a revisao. Sai do banco e tambem do
    data/simulados.json, senao o proximo `importar` a traria de volta.
    """
    if sum((todos, vazios, simulado_id is not None)) != 1:
        console.print("[red]Diga um id, ou --todos, ou --vazios.[/] "
                      "Veja os ids em `radar simulados`.")
        raise typer.Exit(code=1)

    if vazios:
        _descartar_vazios(sim)
        return

    if todos:
        rodadas = servico.listar_simulados()
        if not rodadas:
            console.print("[yellow]Nenhum simulado para descartar.[/]")
            return
        respondidas = sum(r.respondidas for r in rodadas)
        # "s" de sim: o typer.confirm so entende "y", e eu respondo em portugues.
        resposta = "s" if sim else typer.prompt(
            f"Apagar {len(rodadas)} simulado(s) e {respondidas} resposta(s)? "
            f"Nao tem volta [s/N]", default="n", show_default=False,
        )
        if resposta.strip().lower() not in ("s", "sim", "y", "yes"):
            console.print("Nada apagado.")
            raise typer.Exit(code=1)
        quantos, respostas = servico.descartar_todos()
        console.print(f"[green]{quantos} simulado(s) e {respostas} resposta(s) apagados.[/]")
    else:
        respostas = servico.descartar_simulado(simulado_id)
        if respostas is None:
            console.print(f"[red]Nao existe simulado {simulado_id}.[/]")
            raise typer.Exit(code=1)
        console.print(f"[green]Simulado {simulado_id} apagado[/], com {respostas} resposta(s).")

    console.print(
        "[dim]Saiu do banco e do data/simulados.json. Rode `radar sincronizar` "
        "para a copia do GitHub esquecer tambem.[/]"
    )


@app.command()
def auditar(
    caminho: str = typer.Option(None, help="Onde gravar (padrao: docs/auditoria.md)"),
) -> None:
    """Confere o banco contra os PDFs: contagem por materia, gabarito, anuladas.

    Le de novo o quadro do edital e o ultimo gabarito definitivo de cada prova
    do alvo (e das de reforco), compara com o banco e escreve o resultado em
    docs/auditoria.md. Nada e conferido a mao nem digitado.
    """
    from radar import auditoria

    destino = Path(caminho) if caminho else auditoria.caminho_padrao()
    provas = auditoria.escrever(destino)
    problemas = sum(len(p.problemas) for p in provas)
    for p in provas:
        papel = "reforco" if p.reforco else "alvo"
        cor = "red" if p.problemas else "green"
        console.print(
            f"[{cor}]{p.ano} {p.cargo}[/] ({papel}): {p.questoes} questoes, "
            f"{len(p.anuladas_no_banco)} anuladas, "
            f"{len(p.divergencias)} divergencia(s) de gabarito"
        )
    # Materia fora da ordem do edital nao muda numero nenhum, mas e o sinal de
    # que a separacao do caderno pode ter trocado o rotulo de dois blocos.
    fora_de_ordem = sum(len(p.fora_de_ordem) for p in provas)
    if problemas:
        console.print(f"[red]{problemas} numero(s) nao batem[/] - veja {destino}")
    elif fora_de_ordem:
        console.print(
            f"[yellow]Os numeros batem, mas {fora_de_ordem} materia(s) estao "
            f"fora da ordem do edital[/] - veja {destino}"
        )
    else:
        console.print(f"[green]Tudo bate.[/] Relatorio em {destino}")


@app.command()
def gerar(
    materia: str = typer.Option(
        None, help="So desta materia. Sem isso, de qualquer materia do cargo"
    ),
    assunto: str = typer.Option(
        None, help="Fecha o escopo no assunto daquela materia (modo treino)"
    ),
    subassunto: str = typer.Option(
        None, help="Desce mais um nivel, dentro do assunto"
    ),
    elemento: list[str] = typer.Option(
        None, "--elemento",
        help="Um dispositivo, regra ou tipo de problema do no. Repetivel",
    ),
    modo: str = typer.Option(
        None, "--modo",
        help="treino | revisao | simulado. Sem isso: com assunto e treino, "
             "so com materia e simulado",
    ),
    quantas: int = typer.Option(5, help="Quantas questoes gerar"),
    teto: float = typer.Option(
        None, help="Teto de gasto em dolar. O comando para ao chegar nele"
    ),
    simular: bool = typer.Option(
        True, "--simular/--valendo",
        help="Simular NAO gasta nada: so mostra o custo. Use --valendo para rodar",
    ),
    ver_pedido: bool = typer.Option(
        True, "--ver-pedido/--sem-pedido",
        help="Na simulacao, mostra o texto exato que iria para a IA",
    ),
    pedido: bool = typer.Option(
        False, "--pedido",
        help="Salva TODOS os pedidos em data/pedido_ia.json, para responder "
        "fora da API (no Claude Code). Nao gasta nada",
    ),
    macetes: bool = typer.Option(
        False, "--macetes",
        help="Com --pedido: pede macetes por materia em vez de questoes",
    ),
    explicacoes: bool = typer.Option(
        False, "--explicacoes",
        help="Com --pedido: pede a explicacao das questoes que eu errei",
    ),
    importar: str = typer.Option(
        None, "--importar",
        help="Le a resposta de um --pedido, confere e grava o que presta",
    ),
) -> None:
    """Escreve questoes novas com a IA, para TREINAR.

    Questao gerada nunca mede o que a banca cobra: ela nao entra na
    incidencia, no peso das materias, na aba Macetes nem nas questoes
    esperadas do "Onde estudar primeiro". Fica em tabela separada, e o acerto
    nelas aparece sempre como um segundo numero, do lado do das reais.

    O padrao e VARIAR uma questao real da FEPESE com gabarito conferido -
    muda o cenario e os numeros, mantem a regra juridica. O modo do zero so
    entra quando nao existe questao real na materia.

    Esta e a segunda parte do radar que custa dinheiro, e como a outra ela so
    SIMULA por padrao: para gastar de verdade e preciso passar --valendo.
    A chave vai em RADAR_ANTHROPIC_KEY, no .env - nunca no codigo.
    """
    from radar import config as configuracao, gerador

    if importar:
        _importar_resposta_da_ia(Path(importar))
        return

    escopo = _escopo_do_pedido(materia, assunto, subassunto, elemento)
    if pedido:
        _salvar_pedido_da_ia(materia, quantas, macetes, explicacoes,
                             escopo=escopo, modo=modo)
        return

    limite = gerador.TETO_PADRAO if teto is None else teto
    plano = servico.geradas.preparar(materia, quantas, escopo=escopo, modo=modo)

    if not plano["pedidos"]:
        console.print(
            "[red]Nao ha questao real do meu cargo para variar.[/] "
            "Rode [bold]radar provas[/] e [bold]radar questoes[/] primeiro."
        )
        raise typer.Exit(code=1)

    console.print(f"Questoes a gerar: [bold]{plano['quantas']}[/]")
    console.print(
        f"[dim]{len(plano['pedidos'])} chamada(s) a API, "
        f"ate {gerador.VARIACOES_POR_QUESTAO} questoes por chamada[/]"
    )
    if plano["sem_base"]:
        console.print(
            "[yellow]Modo do zero:[/] nao ha questao real desta materia no "
            "acervo, entao as reais entram so como exemplo de estilo."
        )
    else:
        console.print(
            f"[dim]Modo variacao, a partir de {plano['base_disponivel']} "
            f"questao(oes) real(is) do cargo com gabarito conferido[/]"
        )
    # Os numeros sao formatados um a um: trocar a virgula na frase inteira
    # comeria tambem a virgula do portugues.
    entrada = f"{plano['entrada']:,}".replace(",", ".")
    saida = f"{plano['saida']:,}".replace(",", ".")
    console.print(
        f"[dim]{entrada} tokens de entrada, {saida} de saida (estimados)[/]"
    )
    console.print(
        f"Custo estimado: [bold]US$ {plano['custo']:.2f}[/] "
        f"[dim](~R$ {plano['custo'] * config.CAMBIO_DE_REFERENCIA:.2f}, cambio fixo de {config.CAMBIO_DE_REFERENCIA:.2f})[/]"
    )
    console.print(f"[dim]Modelo: {gerador.MODELO}[/]")

    if simular:
        if ver_pedido:
            _mostrar_pedido(plano["pedidos"][0])
        console.print()
        console.print("[yellow]Isto foi so uma simulacao: nada foi gasto.[/]")
        console.print(
            "[dim]O texto das questoes nao aparece aqui porque ele ainda nao "
            "existe: quem escreve e a API, e sem chamada nao ha questao. O que "
            "da para ver antes de pagar e o pedido acima.[/]"
        )
        comando = "radar gerar --valendo"
        if materia:
            comando += f' --materia "{materia}"'
        if quantas != 5:
            comando += f" --quantas {quantas}"
        console.print(f"Para valer, rode: [bold]{comando}[/]")
        return

    if not configuracao.chave_da_anthropic():
        console.print()
        console.print(
            "[red]Falta a chave.[/] Ponha RADAR_ANTHROPIC_KEY no .env "
            "e rode de novo."
        )
        console.print("[dim]Veja COMO_LIGAR_A_IA.txt para o passo a passo.[/]")
        raise typer.Exit(code=1)

    console.print()
    console.print(f"[dim]Teto de gasto: US$ {limite:.2f}[/]")
    with console.status("Escrevendo..."):
        resultado = servico.geradas.gerar(
            materia=materia, quantas=quantas, teto_em_dolar=limite
        )

    if resultado.get("erro"):
        console.print(f"[red]Nao gerei nada:[/] {resultado['erro']}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]{resultado['geradas']} questao(oes) gerada(s)[/] em "
        f"{resultado['chamadas']} chamada(s)"
    )
    console.print(
        f"Gasto real: [bold]US$ {resultado['custo']:.4f}[/] "
        f"[dim](~R$ {resultado['custo'] * config.CAMBIO_DE_REFERENCIA:.2f})[/]"
    )
    if resultado.get("descartadas"):
        console.print(
            f"[dim]{resultado['descartadas']} descartada(s): vieram tortas ou "
            f"repetidas.[/]"
        )
    if resultado.get("parou_no_teto"):
        console.print(
            "[yellow]Parei no teto de gasto.[/] Rode de novo para continuar."
        )
    if resultado.get("guardadas"):
        console.print(
            f"[dim]{resultado['guardadas']} questao(oes) em "
            f"data/questoes_geradas.json - este arquivo e versionado, e e o "
            f"que impede eu pagar de novo pela mesma questao.[/]"
        )
    if resultado.get("falhas"):
        console.print(f"[dim]{resultado['falhas']} chamada(s) falharam.[/]")

    console.print()
    console.print(
        "Responda em [bold]radar web[/], na aba Estudar. O acerto nas geradas "
        "aparece separado do acerto nas reais."
    )


def _mostrar_o_escopo(lote: dict) -> None:
    """O modo e o escopo na saida. A §8 pede que amplo e especifico nao se
    confundam, e e esta linha que impede isso."""
    primeiro = (lote.get("pedidos") or [{}])[0]
    modo = primeiro.get("modo_do_pedido")
    if not modo:
        return
    escopo = primeiro.get("escopo")
    if escopo:
        console.print(f"Modo [bold]{modo}[/], escopo fechado em "
                      f"[bold]{escape(escopo)}[/]")
        restritos = primeiro.get("escopo_dispositivos") or []
        if restritos:
            nomes = [d.split(" > ")[-1] for d in restritos]
            # No modo revisao a lista NAO e de dispositivos: sao os conteudos
            # que eu ja estudei, e chama-los de dispositivo seria mentir sobre
            # o que o escopo tem dentro.
            rotulo = ("So os conteudos que eu ja estudei"
                      if modo == "revisao" else "So estes dispositivos")
            console.print(f"[dim]{rotulo}: {escape('; '.join(nomes))}[/]")
    else:
        console.print(f"Modo [bold]{modo}[/]: abrangencia ampla, pelo edital e "
                      f"pelo peso das materias. [dim]Nao e treino especifico - "
                      f"para isso, passe --assunto.[/]")

    bases = {}
    for p in lote.get("pedidos") or []:
        chave = (p.get("base"), p.get("evidencia_da_base"))
        bases[chave] = bases.get(chave, 0) + p.get("quantas", 0)
    for (base, evidencia), quantas in sorted(bases.items(), key=lambda i: str(i[0])):
        if not base:
            continue
        de_onde = (f"{base} ({evidencia})" if evidencia and evidencia != "nenhuma"
                   else f"{base}, sem questao real de referencia")
        console.print(f"[dim]  {quantas} questao(oes) de {de_onde}[/]")


def _escopo_do_pedido(materia, assunto, subassunto, elemento):
    """O escopo, conferido contra a arvore. Nome que nao existe PARA o comando.

    A §7 e explicita: filtro que nao existe no banco tem de me avisar e sugerir
    os nomes existentes, "em vez de gerar questoes de outra coisa". Por isso a
    saida e um erro com as sugestoes, e nunca um escopo mais largo.
    """
    from radar import conteudos as arvore

    try:
        return arvore.resolver_escopo(
            servico.conteudos.caminhos(), materia, assunto, subassunto,
            list(elemento or []),
        )
    except arvore.EscopoInvalido as erro:
        console.print(f"[red]{escape(str(erro))}[/]")
        console.print("[dim]Nada foi gerado: eu nao alargo o escopo sozinho. "
                      "Veja a arvore com [bold]radar conteudos[/].[/]")
        raise typer.Exit(code=1) from erro


def _salvar_pedido_da_ia(materia: str | None, quantas: int, macetes: bool,
                         explicacoes: bool = False, escopo=None,
                         modo: str | None = None) -> None:
    """O `--pedido`: todos os pedidos num arquivo, sem chamar a API."""
    if explicacoes:
        lote = servico.manual.pedido_de_explicacoes()
        if not lote["pedidos"]:
            console.print(
                "[yellow]Nenhuma questao errada sem explicacao.[/] Elas saem "
                "das questoes reais que eu errei na ultima vez que respondi."
            )
            return
    elif macetes:
        lote = servico.manual.pedido_de_macetes(materia)
    else:
        try:
            lote = servico.manual.pedido_de_questoes(
                materia, quantas, escopo=escopo, modo=modo)
        except Exception as erro:
            from radar.conteudos import EscopoInvalido

            if not isinstance(erro, (EscopoInvalido, ValueError)):
                raise
            console.print(f"[red]{escape(str(erro))}[/]")
            raise typer.Exit(code=1) from erro

    if not lote["pedidos"]:
        console.print(
            "[red]Nao ha questao real do meu cargo para montar o pedido.[/] "
            "Rode [bold]radar provas[/] e [bold]radar questoes[/] primeiro."
        )
        raise typer.Exit(code=1)

    destino = servico.manual.salvar_pedido(lote)
    o_que = ("explicacoes, uma por questao errada" if explicacoes
             else "macetes, um por materia" if macetes else "questoes")
    console.print(
        f"[green]{len(lote['pedidos'])} pedido(s) de {o_que}[/] em {destino}"
    )
    _mostrar_o_escopo(lote)
    console.print(f"[dim]Lote {lote['lote']}. Nada foi gasto.[/]")
    console.print(
        "Responda pelo Claude Code: peca para ele ler o arquivo e seguir o "
        "campo [bold]como_responder[/]. Depois:\n"
        "  [bold]radar gerar --importar data/resposta_ia.json[/]"
    )
    console.print(
        "[dim]Um pedido novo substitui o anterior: resposta de lote velho e "
        "recusada no importar.[/]"
    )


def _importar_resposta_da_ia(arquivo: Path) -> None:
    """O `--importar`: confere a resposta e diz em voz alta o que recusou."""
    if not arquivo.exists():
        console.print(f"[red]Nao achei {arquivo}.[/]")
        raise typer.Exit(code=1)
    try:
        resultado = servico.manual.importar(arquivo)
    except ValueError as erro:
        console.print(f"[red]Nada importado:[/] {erro}")
        raise typer.Exit(code=1) from erro

    o_que = {"macetes": "macete(s)", "explicacoes": "explicacao(oes)",
             "classificacao": "classificacao(oes)"}.get(resultado["tipo"], "questao(oes)")
    console.print(f"[green]{resultado['gravadas']} {o_que} gravado(s)[/]")
    console.print(f"[dim]Procedencia: {resultado['modelo']}[/]")
    if resultado["repetidas"]:
        console.print(f"[dim]{resultado['repetidas']} repetida(s), ignorada(s).[/]")
    fora = resultado.get("fora_do_edital") or []
    if fora:
        console.print(f"[dim]{len(fora)} questao(oes) de bloco generico nao sao de "
                      "materia nenhuma do meu edital: ficam sem linha, que ja e o "
                      "estado de quem nao tem classificacao.[/]")
    if resultado["recusas"]:
        console.print(f"[yellow]{len(resultado['recusas'])} recusada(s):[/]")
        for motivo in resultado["recusas"]:
            console.print(f"  - {motivo}")
    if resultado["tipo"] == "classificacao":
        console.print("[dim]Em data/classificacoes.json (versionado). Confira em "
                      "radar web, Analises > Conferencia.[/]")
    elif resultado["tipo"] == "macetes":
        console.print("[dim]Em data/macetes.json (versionado).[/]")
    elif resultado["tipo"] == "explicacoes":
        console.print("[dim]Em data/explicacoes.json (versionado). Aparecem no "
                      "relatorio do simulado, ao lado de cada erro.[/]")
    elif resultado["gravadas"]:
        console.print(
            "Responda em [bold]radar web[/], na aba Estudar - com o selo de "
            "gerada por IA, e o acerto separado do das reais."
        )


def _mostrar_pedido(pedido: dict) -> None:
    """O texto exato que iria para a IA, na simulacao.

    Existe porque "simular" nao pode significar "mostrar questao inventada":
    a questao so existe depois da chamada. O que da para conferir antes de
    gastar e isto - a instrucao e o pedido, palavra por palavra.
    """
    from radar import gerador

    if pedido.get("modo") == "do_zero":
        instrucao = gerador.INSTRUCAO_DO_ZERO
        corpo = gerador._montar_pedido_do_zero(
            pedido["materia"], pedido.get("assunto"),
            pedido.get("exemplos") or [], pedido["quantas"],
        )
    else:
        instrucao = gerador.INSTRUCAO_VARIACAO
        corpo = gerador._montar_pedido_variacao(
            pedido["questao"], pedido["quantas"]
        )

    console.print()
    console.print("[bold]O primeiro pedido, como ele sai daqui:[/]")
    console.print(Panel(instrucao, title="instrucao", border_style="dim"))
    console.print(Panel(corpo, title="pedido", border_style="dim"))


@app.command()
def padrao(
    cargo: str = typer.Option(None, help="Filtra por cargo, ex: Guarda"),
    banca: str = typer.Option(None, help="Filtra por banca, ex: FEPESE"),
    ano: int = typer.Option(None, help="Filtra por ano"),
) -> None:
    """O que a banca mais cobra: incidencia por materia.

    E a resposta que motivou montar o acervo.
    """
    linhas = servico.incidencia_por_materia(cargo=cargo, banca=banca, ano=ano)

    if not linhas:
        console.print(
            "[yellow]Sem questao no banco com esses filtros.[/] "
            "Rode [bold]radar provas[/] e depois [bold]radar questoes[/]."
        )
        return

    total = sum(n for _, n in linhas)
    titulo = "Incidencia por materia"
    if cargo:
        titulo += f" - cargo contendo \"{cargo}\""

    tabela = Table(title=f"{titulo} ({total} questoes)")
    tabela.add_column("Materia")
    tabela.add_column("Questoes", justify="right")
    tabela.add_column("Peso", justify="right")
    tabela.add_column("", width=22)

    for materia, quantas in linhas:
        fatia = quantas / total
        tabela.add_row(
            materia,
            str(quantas),
            f"{fatia*100:.1f}%",
            "#" * max(1, round(fatia * 20)),
        )

    console.print(tabela)


@app.command()
def repetidas(
    minimo: int = typer.Option(2, help="Aparecer em pelo menos N provas"),
    limite: int = typer.Option(15, help="Quantas mostrar"),
) -> None:
    """Questoes que a banca reaproveitou em mais de uma prova.

    Banca que repete entrega o padrao de graca: sao as que mais valem estudar.
    """
    achadas = servico.questoes_repetidas(minimo=minimo)

    if not achadas:
        console.print("Nenhuma questao repetida ate agora.")
        return

    console.print(f"[bold]{len(achadas)}[/] questao(oes) apareceram em {minimo}+ provas:\n")
    for _, vezes, enunciado in achadas[:limite]:
        console.print(f"[bold green]{vezes}x[/] {enunciado[:100]}")


@app.command()
def favoritar(
    concurso_id: int = typer.Argument(..., help="O id que aparece em `radar listar`"),
    remover: bool = typer.Option(False, "--remover", help="Tira dos favoritos"),
) -> None:
    """Marca um concurso como favorito, para acompanhar de perto.

    Favorito e escolha sua: a coleta nunca mexe nele, e nenhum filtro o
    esconde - nem distancia, nem salario.
    """
    concurso = servico.favoritar(concurso_id, favorito=not remover)

    if concurso is None:
        console.print(f"[red]Nao achei concurso com id {concurso_id}.[/]")
        raise typer.Exit(code=1)

    verbo = "removido dos" if remover else "adicionado aos"
    console.print(f"[green]{verbo} favoritos:[/] {concurso.titulo}")
    console.print(f"Agora sao {servico.contar_favoritos()} favorito(s).")


@app.command()
def salario(
    concurso_id: int = typer.Argument(..., help="O id que aparece em `radar listar`"),
    valor: float = typer.Argument(None, help="Deixe vazio para limpar"),
) -> None:
    """Anota a remuneracao de um concurso, quando o titulo nao traz.

    O valor digitado fica travado: a proxima coleta nao o sobrescreve.
    """
    concurso = servico.definir_salario(concurso_id, valor)

    if concurso is None:
        console.print(f"[red]Nao achei concurso com id {concurso_id}.[/]")
        raise typer.Exit(code=1)

    if valor is None:
        console.print(f"[green]Salario limpo:[/] {concurso.titulo[:60]}")
    else:
        formatado = f"{valor:,.0f}".replace(",", ".")
        console.print(f"[green]R$ {formatado}[/] gravado em: {concurso.titulo[:60]}")


@app.command()
def situacoes() -> None:
    """Recalcula o status de quem tem prazo conhecido.

    O tempo passa e "inscricoes abertas" vira "encerrado" sozinho. Roda
    automatico depois de coletar e de detalhar; este comando e para forcar.
    """
    contagem = servico.atualizar_situacoes()
    if not contagem:
        console.print("Nenhum status mudou.")
        return
    for situacao, quantos in sorted(contagem.items()):
        console.print(f"{SITUACAO_LEGIVEL.get(situacao, situacao)}: {quantos}")


@app.command()
def detalhar(
    limite: int = typer.Option(150, help="Quantas paginas ler nesta rodada"),
) -> None:
    """Le a pagina de cada concurso que interessa e completa o registro.

    Traz o prazo de inscricao (que e o que permite saber o que esta ABERTO
    hoje, e nao so o que foi publicado hoje), a banca, e o municipio de
    lotacao quando a pagina deixa claro.

    Nao le a pagina de todos: comeca pelo que ja esta perto, depois o orgao
    estadual de SC, depois os concursos de SC que ficaram indefinidos, e por
    fim os federais. O que e de outro estado fica de fora.
    """
    console.print(
        f"Vou ler ate [bold]{limite}[/] pagina(s), com pausa de 1,5s entre "
        f"elas. Tempo estimado: [bold]{limite * 1.5 / 60:.0f} minuto(s)[/]."
    )

    with console.status("Lendo as paginas..."):
        resultado = servico.detalhar_pendentes(limite=limite)

    console.print(f"[green]{resultado}[/]")

    abertas = servico.contar_abertas()
    if abertas:
        console.print(
            f"\n[bold green]{abertas}[/] concurso(s) com inscricao aberta agora: "
            f"[bold]radar listar --abertas[/]"
        )


@app.command()
def avisar(
    limite: int = typer.Option(
        servico.LIMITE_DE_AVISOS, help="Maximo de mensagens nesta rodada"
    ),
    favoritos: bool = typer.Option(
        True, "--favoritos/--sem-favoritos",
        help="Tambem manda o que mudou nos concursos que eu sigo",
    ),
) -> None:
    """Manda no Telegram o que mudou nos favoritos e os concursos novos.

    Nesta ordem, e a ordem importa: se o teto do dia cortar alguma coisa, que
    corte a descoberta, e nao a mudanca no concurso que eu ja escolhi seguir.

    O aviso de favorito nao passa por filtro de distancia - eu marquei a
    estrela, eu quero saber. O de concurso novo avisa nucleo, proximo e
    indefinida. Os dois marcam o que saiu, para nao repetir amanha.

    Precisa de RADAR_TELEGRAM_TOKEN e RADAR_TELEGRAM_CHAT_ID no .env.
    """
    if favoritos:
        mudancas = servico.avisar_favoritos(limite=limite)
        if not mudancas.configurado:
            _falta_configurar_o_telegram()
            return
        console.print(f"[green]Favoritos:[/] {mudancas}")

    resultado = servico.avisar(limite=limite)

    if not resultado.configurado:
        _falta_configurar_o_telegram()
        return

    console.print(f"[green]Concursos novos:[/] {resultado}")


def _falta_configurar_o_telegram() -> None:
    console.print(
        "[yellow]Telegram nao configurado.[/] Preencha no arquivo .env:\n"
        "  RADAR_TELEGRAM_TOKEN=...   (pegue com o @BotFather)\n"
        "  RADAR_TELEGRAM_CHAT_ID=... (pegue com o @userinfobot)"
    )


@app.command()
def testar_telegram() -> None:
    """Manda uma mensagem de teste, para conferir token e chat_id.

    Nao mexe no banco e nao marca nada como avisado.
    """
    if not config.telegram_configurado():
        console.print(
            "[red]Falta configurar.[/] No arquivo .env:\n"
            "  RADAR_TELEGRAM_TOKEN=...   (pegue com o @BotFather)\n"
            "  RADAR_TELEGRAM_CHAT_ID=... (pegue com o @userinfobot)"
        )
        raise typer.Exit(code=1)

    ok = avisos.enviar(
        "✅ <b>Radar de Concursos</b>\n"
        "Telegram configurado certo. Os avisos vao chegar aqui."
    )
    if ok:
        console.print("[green]Mensagem enviada.[/] Confira o Telegram.")
    else:
        console.print(
            "[red]Nao consegui enviar.[/] Confira se o token esta certo e se "
            "voce ja mandou /start para o seu bot."
        )
        raise typer.Exit(code=1)


@app.command()
def reclassificar() -> None:
    """Roda o classificador de novo no banco todo, sem ir a internet.

    Use depois de editar config/regioes.yml.
    """
    contagem = servico.reclassificar()
    for anel, quantos in sorted(contagem.items()):
        cor = CORES_DO_ANEL.get(anel, "")
        rotulo = ROTULO_DO_ANEL.get(anel, anel)
        console.print(f"[{cor}]{rotulo}[/]: {quantos}" if cor else f"{rotulo}: {quantos}")

    _mostrar_alvos()


# Quantos alvos principais listar depois de reclassificar. Sao poucos por
# natureza - se um dia forem muitos, e sinal de regra frouxa em
# config/alvo.yml, e ai eu quero justamente ver o corte.
ALVOS_A_LISTAR = 15


def _mostrar_alvos() -> None:
    """O que bateu em config/alvo.yml, para eu auditar a regra.

    O principal sai item por item porque e a lista que eu preciso conferir
    com o olho; o secundario sai so contado, porque sao dezenas.
    """
    contagem = servico.contar_por_alvo()
    if not contagem:
        return

    console.print()
    secundarios = contagem.get(alvos.SECUNDARIO, 0)
    if secundarios:
        console.print(f"[cyan]Alvo secundario[/]: {secundarios}")

    # O mesmo cargo em outro estado sai contado e separado: ele avisa como o
    # principal e nao entra em nada que seja estudo, e eu preciso ver essa
    # diferenca aqui para conferir se a regra continua fazendo sentido.
    fora = contagem.get(alvos.PRINCIPAL_FORA, 0)
    if fora:
        console.print(
            f"[yellow]Mesmo cargo, fora de SC[/]: {fora} "
            f"[dim](avisa; nao entra no estudo)[/]"
        )

    principais = servico.concursos_do_alvo(alvos.PRINCIPAL)
    if not principais:
        return

    console.print(f"[bold red]Alvo principal[/]: {len(principais)}")
    for c in principais[:ALVOS_A_LISTAR]:
        rotulo = ROTULO_DO_ANEL.get(c.relevancia, c.relevancia)
        console.print(f"  [bold red]*[/] {c.titulo}")
        console.print(f"    [dim]{rotulo} · {c.motivo_alvo}[/]")
    if len(principais) > ALVOS_A_LISTAR:
        console.print(f"  [dim]... e mais {len(principais) - ALVOS_A_LISTAR}[/]")


ROTULO_DO_EVENTO = {
    "apareceu": "apareceu",
    "mudou_situacao": "situacao",
    "inscricoes_abertas": "inscricao",
    "inscricoes_encerradas": "encerrou",
    "edital_retificado": "retificado",
    "prova_marcada": "prova",
}

CORES_DO_EVENTO = {
    "apareceu": "dim",
    "mudou_situacao": "cyan",
    "inscricoes_abertas": "bold green",
    "inscricoes_encerradas": "yellow",
    "edital_retificado": "bold red",
    "prova_marcada": "bold magenta",
}


@app.command()
def eventos(
    concurso_id: int = typer.Argument(..., help="O id do concurso, como na lista"),
) -> None:
    """A linha do tempo do concurso: o que aconteceu com ele, e quando.

    O resto do radar mostra so como o concurso esta hoje. Aqui esta o caminho
    ate aqui - quando ele apareceu, quando a inscricao abriu, quantas vezes o
    edital foi retificado.
    """
    achado = servico.eventos_do_concurso(concurso_id)
    if achado is None:
        console.print(f"[red]Nao achei concurso com id {concurso_id}.[/]")
        raise typer.Exit(code=1)

    concurso, linha = achado
    console.print(f"[bold]{concurso.titulo}[/]")
    console.print(f"[dim]{concurso.url}[/]\n")

    if not linha:
        console.print(
            "[yellow]Sem evento registrado.[/] A linha do tempo comeca a ser "
            "gravada na primeira coleta depois que o concurso entra no radar."
        )
        return

    tabela = Table(box=None, pad_edge=False)
    tabela.add_column("Quando", style="dim", no_wrap=True)
    tabela.add_column("O que")
    tabela.add_column("Detalhe")

    for evento in linha:
        cor = CORES_DO_EVENTO.get(evento.tipo, "")
        rotulo = ROTULO_DO_EVENTO.get(evento.tipo, evento.tipo)
        tabela.add_row(
            formatar_data(evento.data),
            f"[{cor}]{rotulo}[/]" if cor else rotulo,
            evento.descricao,
        )

    console.print(tabela)


@app.command()
def exportar(caminho: str = typer.Option(None, help="Destino do JSON")) -> None:
    """Grava o banco em data/concursos.json e data/eventos.json.

    Os dois arquivos sao o que vai para o git. O segundo e a linha do tempo:
    sem ele, o robo do GitHub reconstroi o banco todo dia sem historico
    nenhum, e nao tem como avisar mudanca de favorito.
    """
    destino = Path(caminho) if caminho else acervo.caminho_padrao()
    total = acervo.exportar(destino)
    console.print(f"[green]{total}[/] concurso(s) exportado(s) para {destino}")

    # O caminho dos eventos acompanha o do concurso quando alguem escolhe
    # onde salvar: os dois sao o mesmo par, e separa-los so confundiria.
    destino_eventos = (
        destino.with_name("eventos.json") if caminho else acervo.caminho_dos_eventos()
    )
    eventos = acervo.exportar_eventos(destino_eventos)
    console.print(f"[green]{eventos}[/] evento(s) exportado(s) para {destino_eventos}")

    # O terceiro arquivo e o unico que custou dinheiro: o assunto que a IA
    # classificou. Perder ele e pagar de novo pela mesma questao.
    destino_assuntos = (
        destino.with_name("assuntos.json") if caminho
        else acervo.caminho_dos_assuntos()
    )
    assuntos_gravados = acervo.exportar_assuntos(destino_assuntos)
    console.print(
        f"[green]{assuntos_gravados}[/] assunto(s) exportado(s) para "
        f"{destino_assuntos}"
    )

    # A arvore de conteudos e as classificacoes (Etapa 2): o banco e
    # reconstruivel, e elas so voltam pelo arquivo.
    nos = servico.conteudos.exportar()
    classificadas = servico.classificacoes.exportar()
    console.print(f"[green]{nos}[/] nó(s) da árvore e [green]{classificadas}[/] "
                  f"classificação(ões) exportados")

    # O quarto tambem custou dinheiro: as questoes que a IA escreveu. Elas
    # sao treino, e nao acervo - mas perde-las e paga-las de novo.
    destino_geradas = (
        destino.with_name("questoes_geradas.json") if caminho
        else acervo.caminho_das_geradas()
    )
    geradas_gravadas = acervo.exportar_geradas(destino_geradas)
    console.print(
        f"[green]{geradas_gravadas}[/] questao(oes) gerada(s) exportada(s) "
        f"para {destino_geradas}"
    )

    # O quinto e o unico que nao se reconstroi de lugar nenhum: o que eu
    # respondi em cada simulado. Sem ele, o historico de treino morria junto
    # com o radar.db.
    destino_simulados = (
        destino.with_name("simulados.json") if caminho
        else acervo.caminho_dos_simulados()
    )
    simulados_gravados = acervo.exportar_simulados(destino_simulados)
    console.print(
        f"[green]{simulados_gravados}[/] simulado(s) exportado(s) para "
        f"{destino_simulados}"
    )

    # O diario do cronograma, pelo mesmo motivo: so existe nesta maquina.
    destino_registros = (
        destino.with_name("registro_estudo.json") if caminho
        else acervo.caminho_dos_registros()
    )
    dias_gravados = acervo.exportar_registros(destino_registros)
    console.print(
        f"[green]{dias_gravados}[/] dia(s) do cronograma exportado(s) para "
        f"{destino_registros}"
    )

    # Os checks de cada faixa, pelo mesmo motivo.
    destino_estados = (
        destino.with_name("estado_do_dia.json") if caminho
        else acervo.caminho_dos_estados()
    )
    estados_gravados = acervo.exportar_estados(destino_estados)
    console.print(
        f"[green]{estados_gravados}[/] dia(s) de faixas marcadas exportado(s) "
        f"para {destino_estados}"
    )

    # O caderno de erros, pelo mesmo motivo: e a unica copia dele fora do
    # radar.db, e o que esta escrito nele sou eu que escrevi.
    destino_erros = (
        destino.with_name("caderno_erros.json") if caminho
        else acervo.caminho_dos_erros()
    )
    erros_gravados = acervo.exportar_erros(destino_erros)
    console.print(
        f"[green]{erros_gravados}[/] erro(s) anotado(s) exportado(s) para "
        f"{destino_erros}"
    )

    # O estudo extra, pelo mesmo motivo: o tempo que eu estudei fora do plano
    # nao esta em nenhum outro lugar.
    destino_extras = (
        destino.with_name("estudo_extra.json") if caminho
        else acervo.caminho_dos_extras()
    )
    extras_gravados = acervo.exportar_extras(destino_extras)
    console.print(
        f"[green]{extras_gravados}[/] estudo(s) extra(s) exportado(s) para "
        f"{destino_extras}"
    )

    # A reflexao de cada semana, pelo mesmo motivo de tudo isto: e texto que so
    # eu escrevi, e nao existe em lugar nenhum fora deste banco.
    destino_notas = (
        destino.with_name("notas_semana.json") if caminho
        else acervo.caminho_das_notas()
    )
    notas_gravadas = acervo.exportar_notas(destino_notas)
    console.print(
        f"[green]{notas_gravadas}[/] reflexao(oes) de semana exportada(s) para "
        f"{destino_notas}"
    )


@app.command()
def importar(caminho: str = typer.Option(None, help="Origem do JSON")) -> None:
    """Reconstroi o banco a partir do JSON. Seguro rodar quantas vezes quiser.

    Le os dois arquivos: os concursos e a linha do tempo. O que e meu -
    favorito, anotacao, salario digitado - nunca e apagado por valor vazio do
    JSON, e evento que eu ja tenho nao entra duas vezes.
    """
    origem = Path(caminho) if caminho else acervo.caminho_padrao()
    total = acervo.importar(origem)
    if total == 0:
        console.print(f"[yellow]Nada a importar[/] (nao achei {origem})")
    else:
        console.print(f"[green]{total}[/] concurso(s) importado(s) de {origem}")

    origem_eventos = (
        origem.with_name("eventos.json") if caminho else acervo.caminho_dos_eventos()
    )
    novos = acervo.importar_eventos(origem_eventos)
    if origem_eventos.exists():
        console.print(f"[green]{novos}[/] evento(s) novo(s) de {origem_eventos}")

    # A arvore antes de tudo que se liga a ela: o assunto antigo e as
    # classificacoes procuram o no pelo caminho.
    nos = servico.conteudos.importar()
    if nos:
        console.print(f"[green]{nos}[/] nó(s) da árvore de conteúdos de volta")

    origem_assuntos = (
        origem.with_name("assuntos.json") if caminho
        else acervo.caminho_dos_assuntos()
    )
    if origem_assuntos.exists():
        mudadas = acervo.importar_assuntos(origem_assuntos)
        console.print(
            f"[green]{mudadas}[/] questao(oes) reganharam o assunto ja pago, "
            f"de {origem_assuntos}"
        )
        # Recusa em silencio seria o mesmo erro de novo: o arquivo importaria
        # menos do que tem e ninguem perguntaria por que.
        recusados = acervo.assuntos_sem_origem(origem_assuntos)
        if recusados:
            console.print(
                f"[red]{len(recusados)} assunto(s) recusados:[/] o arquivo nao "
                f"diz de que modelo e de quando eles vieram. Assunto sem "
                f"procedencia nao entra no banco."
            )

    entraram, recusadas = servico.classificacoes.importar()
    if entraram or recusadas:
        console.print(f"[green]{entraram}[/] classificação(ões) de volta")
    if recusadas:
        console.print(f"[red]{recusadas} classificação(ões) recusadas:[/] sem "
                      f"procedência ou com um nó que a árvore não tem.")

    origem_geradas = (
        origem.with_name("questoes_geradas.json") if caminho
        else acervo.caminho_das_geradas()
    )
    if origem_geradas.exists():
        voltaram = acervo.importar_geradas(origem_geradas)
        console.print(
            f"[green]{voltaram}[/] questao(oes) gerada(s) de volta, "
            f"de {origem_geradas}"
        )

    origem_simulados = (
        origem.with_name("simulados.json") if caminho
        else acervo.caminho_dos_simulados()
    )
    if origem_simulados.exists():
        _importar_simulados(origem_simulados)

    origem_registros = (
        origem.with_name("registro_estudo.json") if caminho
        else acervo.caminho_dos_registros()
    )
    if origem_registros.exists():
        dias = acervo.importar_registros(origem_registros)
        console.print(f"   {dias} dia(s) do cronograma de volta ao banco")

    origem_estados = (
        origem.with_name("estado_do_dia.json") if caminho
        else acervo.caminho_dos_estados()
    )
    if origem_estados.exists():
        estados = acervo.importar_estados(origem_estados)
        console.print(f"   {estados} dia(s) de faixas marcadas de volta ao banco")

    origem_erros = (
        origem.with_name("caderno_erros.json") if caminho
        else acervo.caminho_dos_erros()
    )
    if origem_erros.exists():
        erros_de_volta = acervo.importar_erros(origem_erros)
        console.print(f"   {erros_de_volta} erro(s) anotado(s) de volta ao banco")

    origem_extras = (
        origem.with_name("estudo_extra.json") if caminho
        else acervo.caminho_dos_extras()
    )
    if origem_extras.exists():
        extras_de_volta = acervo.importar_extras(origem_extras)
        console.print(f"   {extras_de_volta} estudo(s) extra(s) de volta ao banco")

    origem_notas = (
        origem.with_name("notas_semana.json") if caminho
        else acervo.caminho_das_notas()
    )
    if origem_notas.exists():
        notas_de_volta = acervo.importar_notas(origem_notas)
        console.print(f"   {notas_de_volta} reflexao(oes) de semana de volta ao banco")

    # O concurso de uma prova pode ter chegado agora, e e ele que diz o
    # estado: a evidencia de cada questao e refeita pela regra unica.
    contagem = servico.evidencia.atualizar()
    console.print("   evidência: " + ", ".join(
        f"{quantas} {ev or 'sem evidência'}" for ev, quantas in sorted(
            contagem.items(), key=lambda par: str(par[0]))))

    # Uma linha por execucao, principalmente para o log do robo: e ela que
    # responde "voce esta vendo os meus favoritos?". Eles chegam la pelo
    # `radar sincronizar`, e numero menor do que o esperado quer dizer que
    # faltou sincronizar - nao e erro.
    console.print(f"Conhece [bold]{servico.contar_favoritos()}[/] favorito(s).")


def _importar_simulados(origem: Path | None = None) -> None:
    """Traz o historico de treino e diz em voz alta o que ficou de fora."""
    novos, de_fora = acervo.importar_simulados(origem)
    console.print(f"   {novos} simulado(s) de volta ao banco")
    if de_fora:
        # Fica de fora quando a questao ainda nao foi extraida neste banco.
        # Ele continua no arquivo; o remedio e extrair e importar de novo.
        console.print(
            f"   [yellow]{de_fora} simulado(s) ficaram de fora:[/] as questoes "
            f"deles ainda nao estao neste banco. Rode `radar questoes` e "
            f"importe de novo - o arquivo nao perde nada enquanto isso."
        )


# Escutar em todas as placas de rede e o que deixa o celular chegar. So com
# --rede (ou --host explicito): o padrao continua sendo so este PC.
TODAS_AS_PLACAS = "0.0.0.0"  # noqa: S104 - so com --rede, escolha minha


def host_do_servidor(rede: bool, host: str) -> str:
    """Onde o servidor escuta: todas as placas com --rede, senao o --host."""
    return TODAS_AS_PLACAS if rede else host


@app.command()
def web(
    porta: int = typer.Option(8000, help="Porta do servidor"),
    host: str = typer.Option(
        "127.0.0.1",
        help="Endereco onde escutar. Para o celular, prefira --rede",
    ),
    rede: bool = typer.Option(
        False, "--rede",
        help="Abre tambem no celular, na mesma rede Wi-Fi (escuta em 0.0.0.0)",
    ),
    recarregar: bool = typer.Option(
        False, help="Reinicia sozinho ao salvar arquivo (so para desenvolver)"
    ),
) -> None:
    """Sobe a interface web em http://localhost:8000"""
    import uvicorn

    host = host_do_servidor(rede, host)

    if porta_ocupada(host, porta):
        # O erro cru do uvicorn (winerror 10048) nao diz o que fazer. Quase
        # sempre e um servidor que ficou aberto noutra janela.
        livre = primeira_porta_livre(host, porta + 1)
        console.print(
            f"[red]A porta {porta} ja esta em uso.[/]\n"
            f"Costuma ser um [bold]radar web[/] aberto em outra janela - "
            f"procure a janela e feche com Ctrl+C."
        )
        if livre:
            console.print(
                f"\nSe preferir subir outro agora, use uma porta livre:\n"
                f"  [bold]radar web --porta {livre}[/]"
            )
        raise typer.Exit(code=1)

    console.print(f"\nRadar no ar em [bold cyan]http://localhost:{porta}[/]")
    if host == TODAS_AS_PLACAS:
        ip = ip_local()
        if ip:
            console.print(f"Abra no celular (mesmo Wi-Fi): [bold cyan]http://{ip}:{porta}/hoje[/]")
        else:
            console.print(
                "Aberto na rede, mas nao achei o IP deste PC. Rode [bold]ipconfig[/] "
                f"e use o \"Endereco IPv4\" do Wi-Fi: http://<esse IP>:{porta}/hoje"
            )
        console.print("[dim]Sem senha: qualquer pessoa no seu Wi-Fi consegue abrir.[/]")
    console.print("Ctrl+C para parar.\n")

    # O modo recarregar fica DESLIGADO por padrao de proposito. Ele faz o
    # uvicorn subir um segundo processo que reimporta tudo, e isso quebra no
    # Windows quando o caminho da pasta tem espaco no nome - que e exatamente
    # o caso aqui ("C:\Projeto concurso claude\..."). Sem ele, o servidor e
    # um processo so e simplesmente funciona.
    if recarregar:
        uvicorn.run("radar.web.app:app", host=host, port=porta, reload=True)
    else:
        from radar.web.app import app as aplicacao_web

        uvicorn.run(aplicacao_web, host=host, port=porta)


# --- tudo automatico (etapa D1) ---------------------------------------------
#
# Quatro comandos para nunca mais precisar lembrar de nada: `subir` deixa a web
# no ar sem janela, `parar` desliga, `status` conta como esta, e `agendar` poe
# os dois no Agendador do Windows. O `backup` e o que a tarefa das 23h30 chama.
# A logica toda mora em radar/automacao.py; aqui so a conversa com a tela.


@app.command()
def subir(
    porta: int = typer.Option(automacao.PORTA_PADRAO, help="Porta do servidor"),
    abrir: bool = typer.Option(
        False, "--abrir", help="Abre a tela Hoje no navegador depois de subir",
    ),
) -> None:
    """Sobe a web em segundo plano, sem janela, e devolve o prompt.

    Diferente do `radar web`, que segura o terminal aberto: aqui o servidor
    fica rodando sozinho, sem janela nenhuma, e quem desliga e `radar parar`.
    """
    servidor = automacao.no_ar()
    if servidor:
        console.print(
            f"[green]Ja esta no ar[/] em [bold cyan]{servidor.endereco}[/] "
            f"(processo {servidor.pid}). Nao subi outro."
        )
    else:
        if porta_ocupada(automacao.HOST_PADRAO, porta):
            # Porta ocupada sem arquivo de PID meu: e um `radar web` aberto
            # em outra janela, e matar aquilo nao e tarefa deste comando.
            console.print(
                f"[red]A porta {porta} ja esta em uso[/], e nao fui eu que subi.\n"
                f"Costuma ser um [bold]radar web[/] aberto em outra janela - "
                f"feche com Ctrl+C, ou suba noutra porta: "
                f"[bold]radar subir --porta {porta + 1}[/]."
            )
            raise typer.Exit(code=1)

        servidor = automacao.subir(porta)
        if not automacao.esperar_subir(servidor):
            console.print(
                "[red]Subiu e morreu.[/] Sem janela nao ha erro na tela, "
                f"entao o que ele disse esta em [bold]{automacao.caminho_do_log_da_web()}[/]:"
            )
            for linha in automacao.fim_do_log_da_web():
                console.print(f"  [dim]{escape(linha)}[/]")
            automacao.apagar_arquivo_do_pid()
            raise typer.Exit(code=1)

        console.print(
            f"[green]No ar[/] em [bold cyan]{servidor.endereco}[/] "
            f"(processo {servidor.pid}), sem janela."
        )
        console.print("[dim]Para desligar: [bold]radar parar[/][/]")

    if abrir:
        import webbrowser

        endereco = f"{servidor.endereco}/hoje"
        console.print(f"Abrindo {endereco}")
        webbrowser.open(endereco)


@app.command()
def parar() -> None:
    """Desliga a web que o `radar subir` deixou rodando."""
    servidor = automacao.parar()
    if servidor is None:
        console.print("Nada para desligar: nenhum servidor do `radar subir` rodando.")
        console.print(
            "[dim]Um [bold]radar web[/] aberto numa janela nao entra aqui - "
            "esse para com Ctrl+C na propria janela.[/]"
        )
        return
    console.print(f"[green]Desligado[/] (processo {servidor.pid}).")


@app.command()
def status() -> None:
    """No ar ou nao, em que endereco, e como foi o ultimo backup."""
    servidor = automacao.no_ar()
    if servidor:
        console.print(f"Web: [green]no ar[/] em [bold cyan]{servidor.endereco}[/] "
                      f"(processo {servidor.pid})")
        if servidor.subiu_em:
            console.print(f"     [dim]desde {servidor.subiu_em:%d/%m/%Y às %H:%M}[/]")
    else:
        console.print("Web: [yellow]fora do ar.[/] Sobe com [bold]radar subir[/].")

    backup = automacao.ultimo_backup()
    if backup is None:
        console.print(
            "Backup: [yellow]nunca rodou.[/] O [bold]radar agendar[/] cria a "
            "tarefa que roda todo dia às 23:30."
        )
        return
    if backup.deu_certo:
        console.print(f"Backup: [green]deu certo[/] em {backup.dia:%d/%m/%Y}")
    else:
        console.print(f"Backup: [red]falhou[/] em {backup.dia:%d/%m/%Y} - "
                      f"{escape(backup.motivo or 'sem motivo no log')}")
    console.print(f"     [dim]{backup.caminho}[/]")


@app.command()
def backup() -> None:
    """Roda o `radar sincronizar` e guarda a saida em data/logs/.

    E o que a tarefa das 23h30 chama. Rodar na mao serve para conferir que o
    backup automatico funciona sem esperar a meia-noite.
    """
    console.print("Rodando o sincronizar e guardando a saída...")
    resultado = automacao.rodar_backup()
    if resultado.deu_certo:
        console.print(f"[green]Backup em dia.[/] Log em {resultado.caminho}")
    else:
        console.print(f"[red]O backup falhou:[/] {escape(resultado.motivo or '')}")
        console.print(f"[dim]A saída inteira esta em {resultado.caminho}[/]")
        raise typer.Exit(code=1)


@app.command()
def agendar(
    mostrar: bool = typer.Option(
        False, "--status", help="So mostra o que esta criado, sem mexer em nada",
    ),
    remover: bool = typer.Option(
        False, "--remover", help="Apaga as duas tarefas e os dois atalhos",
    ),
) -> None:
    """Poe o radar no Agendador do Windows: web no logon, backup às 23:30.

    Duas tarefas no MEU usuario, sem pedir administrador, e dois atalhos .bat
    na Area de Trabalho. Nao e servico do Windows de proposito - o porque esta
    em docs/decisoes.md.
    """
    if not automacao.e_windows():
        console.print(
            "[red]Este comando e do Windows.[/] O Agendador de Tarefas nao "
            "existe aqui; no Linux o equivalente seria cron ou systemd --user."
        )
        raise typer.Exit(code=1)

    if mostrar:
        _mostrar_agendamento()
        return

    if remover:
        for nome in (automacao.TAREFA_WEB, automacao.TAREFA_BACKUP):
            resultado = automacao.remover_tarefa(nome)
            if resultado.returncode == 0:
                console.print(f"[green]Tarefa apagada:[/] {nome}")
            else:
                console.print(f"[dim]Nada a apagar em \"{nome}\".[/]")
        apagados = automacao.apagar_atalhos()
        for caminho in apagados:
            console.print(f"[green]Atalho apagado:[/] {caminho}")
        if not apagados:
            console.print("[dim]Nenhum atalho na Área de Trabalho.[/]")
        console.print(
            "\nO servidor que estiver no ar continua no ar: "
            "[bold]radar parar[/] desliga."
        )
        return

    for nome, xml in automacao.tarefas().items():
        resultado = automacao.criar_tarefa(nome, xml)
        if resultado.returncode == 0:
            console.print(f"[green]Tarefa criada:[/] {nome}")
        else:
            console.print(f"[red]Nao consegui criar \"{nome}\".[/]")
            console.print(f"[dim]{escape((resultado.stderr or resultado.stdout).strip())}[/]")
            raise typer.Exit(code=1)

    for caminho in automacao.criar_atalhos():
        console.print(f"[green]Atalho criado:[/] {caminho}")

    console.print(
        f"\nPronto. A web sobe sozinha no próximo logon, e o backup roda todo "
        f"dia às {automacao.HORA_DO_BACKUP}.\n"
        f"Confira com [bold]radar agendar --status[/] e [bold]radar status[/]."
    )


def _mostrar_agendamento() -> None:
    """O `radar agendar --status`: o que o Agendador responde das duas tarefas.

    Mostra os campos como o Windows os escreve, sem traduzir: o schtasks fala
    no idioma do sistema, e procurar "Next Run Time" quebraria justamente
    nesta maquina, que esta em portugues.
    """
    for nome in (automacao.TAREFA_WEB, automacao.TAREFA_BACKUP):
        campos = automacao.consultar_tarefa(nome)
        if campos is None:
            console.print(f"[yellow]{nome}[/]: não está criada. "
                          f"Rode [bold]radar agendar[/].")
            continue
        console.print(f"[bold green]{nome}[/]")
        for chave, valor in campos.items():
            console.print(f"  [dim]{escape(chave)}:[/] {escape(valor)}")
        console.print()

    pasta = automacao.diretorio_da_area_de_trabalho()
    for atalho in automacao.ATALHOS:
        caminho = pasta / atalho
        marca = "[green]está lá[/]" if caminho.exists() else "[yellow]não está[/]"
        console.print(f"Atalho \"{atalho}\": {marca}")


def _descartar_vazios(sim: bool) -> None:
    """O `radar descartar --vazios`: mostra quais, pergunta, apaga."""
    candidatos = servico.simulados_vazios()
    if not candidatos:
        console.print("Nenhum simulado vazio com mais de 1 dia. Nada a limpar.")
        return
    console.print(f"{len(candidatos)} simulado(s) sem nenhuma resposta, criados ha mais de 1 dia:")
    for ident, criado in candidatos:
        console.print(f"  #{ident}  criado em {para_local(criado):%d/%m/%Y às %H:%M}")
    resposta = "s" if sim else typer.prompt(
        "Apagar? Nao tem volta [s/N]", default="n", show_default=False,
    )
    if resposta.strip().lower() not in ("s", "sim", "y", "yes"):
        console.print("Nada apagado.")
        raise typer.Exit(code=1)
    sairam = servico.descartar_vazios()
    console.print(f"[green]{len(sairam)} simulado(s) vazio(s) apagado(s)[/], "
                  f"do banco e do data/simulados.json.")


# --- sincronizar com o GitHub (etapa 11) ------------------------------------
#
# Um comando para o que antes eram cinco passos na ordem certa. A ordem e o
# que protege o dado, e por isso ela esta escrita aqui e nao na minha cabeca:
#
#   pull   - traz a coleta do robo e o que ele ja avisou
#   importar - o JSON entra no banco. ANTES de exportar, senao eu escreveria
#              por cima das marcas de aviso do robo e ele mandaria tudo de novo
#   exportar - o meu banco volta para o JSON, agora com os meus favoritos
#   commit + push - o robo passa a conhece-los na proxima execucao


def _git(*argumentos: str) -> subprocess.CompletedProcess:
    """Roda um comando git na pasta do projeto e devolve o resultado."""
    return subprocess.run(
        ["git", *argumentos],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )


ARQUIVOS_DO_RADAR = ("data/concursos.json", "data/eventos.json",
                     "data/assuntos.json", "data/questoes_geradas.json",
                     "data/simulados.json", "data/macetes.json",
                     "data/explicacoes.json", "data/registro_estudo.json",
                     "data/estado_do_dia.json", "data/caderno_erros.json",
                     "data/estudo_extra.json", "data/notas_semana.json",
                     "data/conteudos.json", "data/classificacoes.json")


@app.command()
def sincronizar(
    empurrar: bool = typer.Option(
        True, "--empurrar/--sem-empurrar",
        help="Faz o push no fim. Desligado, para antes e so mostra o que mudou",
    ),
) -> None:
    """Troca com o GitHub o que cada lado sabe, e aplica a regra de hoje.

    Existe porque as duas pontas sabem coisas diferentes. O robo sabe o que
    apareceu na coleta e o que ele ja avisou; eu sei quais concursos marquei
    com a estrela e o que anotei neles. Sem este comando, nenhum dos dois
    ficava sabendo do outro - e o mesmo concurso chegava duas vezes no
    celular, enquanto o favorito que eu marquei aqui nunca virava aviso la.

    Os cinco passos, e a ordem e o que protege o dado:

        pull -> importar -> RECLASSIFICAR -> exportar -> commit e push

    O reclassificar no meio nao e enfeite. Sem ele, mudar `config/regioes.yml`
    ou `config/alvo.yml` nao adianta nada: eu reclassifico, sincronizo, e o
    importar do passo 2 traz de volta o JSON com a classificacao velha -
    desfazendo na hora o que eu tinha acabado de corrigir. Com ele dentro,
    todo sincronizar aplica a regra ATUAL e leva o resultado ate o robo.

    So mexe nos arquivos de `ARQUIVOS_DO_RADAR` - entre eles o
    `data/simulados.json`, a unica copia do meu historico de treino fora do
    radar.db. O que mais estiver mudado na pasta fica como esta.
    """
    console.print("[bold]1/6[/] Trazendo o que o robo coletou")
    pull = _git("pull", "--rebase", "origin", "main")
    if pull.returncode != 0:
        console.print("[red]O pull falhou.[/] Resolva a mao e rode de novo:\n")
        console.print(f"[dim]{(pull.stderr or pull.stdout).strip()}[/]")
        raise typer.Exit(code=1)

    console.print("[bold]2/6[/] Lendo o JSON para dentro do banco")
    concursos = acervo.importar()
    eventos_novos = acervo.importar_eventos()
    console.print(
        f"   {concursos} concurso(s) lido(s), {eventos_novos} evento(s) novo(s)"
    )
    _importar_simulados()
    servico.conteudos.importar()
    servico.classificacoes.importar()
    dias = acervo.importar_registros()
    estados = acervo.importar_estados()
    erros_de_volta = acervo.importar_erros()
    extras_de_volta = acervo.importar_extras()
    notas_de_volta = acervo.importar_notas()
    console.print(f"   {dias} dia(s) do cronograma, {estados} dia(s) de faixas "
                  f"marcadas, {erros_de_volta} erro(s) anotado(s), "
                  f"{extras_de_volta} estudo(s) extra(s) e {notas_de_volta} "
                  f"reflexao(oes) de volta ao banco")

    # Depois de importar e ANTES de exportar: e a unica posicao que funciona.
    # Antes do importar, o JSON velho passaria por cima; depois do exportar, o
    # arquivo ja teria ido com a regra antiga.
    console.print("[bold]3/6[/] Aplicando a regra de hoje (reclassificar)")
    servico.evidencia.atualizar()
    contagem = servico.reclassificar()
    console.print(
        "   " + ", ".join(
            f"{quantos} {anel}" for anel, quantos in sorted(contagem.items())
        )
    )

    # Antes de exportar: o simulado vazio e antigo sai do banco e do arquivo,
    # sem perguntar - nao tem resposta nenhuma, entao nao ha o que perder.
    vazios = servico.descartar_vazios()
    if vazios:
        console.print(f"   {len(vazios)} simulado(s) vazio(s) com mais de 1 dia apagado(s)")

    console.print("[bold]4/6[/] Escrevendo o meu banco de volta no JSON")
    total = acervo.exportar()
    total_eventos = acervo.exportar_eventos()
    # O historico de treino vive so nesta maquina - o robo nunca faz
    # simulado. E aqui que ele ganha a copia que o radar.db nao tem.
    total_simulados = acervo.exportar_simulados()
    total_dias = acervo.exportar_registros()
    acervo.exportar_estados()
    total_erros = acervo.exportar_erros()
    total_extras = acervo.exportar_extras()
    total_notas = acervo.exportar_notas()
    servico.conteudos.exportar()
    servico.classificacoes.exportar()
    favoritos = servico.contar_favoritos()
    console.print(
        f"   {total} concurso(s), {total_eventos} evento(s), "
        f"{total_simulados} simulado(s), {total_dias} dia(s) do cronograma, "
        f"{total_erros} erro(s) anotado(s), {total_extras} estudo(s) extra(s) e "
        f"{total_notas} reflexao(oes), com [bold]{favoritos}[/] favorito(s)"
    )

    console.print("[bold]5/6[/] Commitando")
    _git("add", *ARQUIVOS_DO_RADAR)
    mudou = _git("diff", "--staged", "--quiet").returncode != 0
    if not mudou:
        console.print("   [dim]Nada mudou: nao ha o que commitar.[/]")
        console.print("\n[green]Em dia com o GitHub.[/]")
        return

    data = agora().strftime("%Y-%m-%d")
    commit = _git("commit", "-m", f"sincronizar: {data}")
    if commit.returncode != 0:
        console.print("[red]O commit falhou.[/]")
        console.print(f"[dim]{(commit.stderr or commit.stdout).strip()}[/]")
        raise typer.Exit(code=1)

    if not empurrar:
        console.print("[bold]6/6[/] [yellow]Sem empurrar, a pedido.[/]")
        console.print("   O commit esta feito; falta `git push`.")
        return

    console.print("[bold]6/6[/] Empurrando")
    push = _git("push", "origin", "HEAD:main")
    if push.returncode != 0:
        console.print("[red]O push falhou.[/] O commit esta feito aqui:\n")
        console.print(f"[dim]{(push.stderr or push.stdout).strip()}[/]")
        raise typer.Exit(code=1)

    console.print(
        f"\n[green]Sincronizado.[/] O robo passa a conhecer {favoritos} "
        f"favorito(s) na proxima coleta."
    )


@app.command()
def hoje(
    data: str = typer.Option(None, help="Outro dia, em AAAA-MM-DD (padrao: hoje)"),
    marcar: str = typer.Option(
        None, help="Como foi o dia: ideal, reduzida, minima ou nao_fiz",
    ),
    feitas: int = typer.Option(
        None, help="Questoes feitas fora do radar (vira estudo extra; pede --minutos)",
    ),
    acertos: int = typer.Option(None, help="Acertos nessas questoes"),
    minutos: int = typer.Option(None, help="Minutos gastos nessas questoes"),
    materia: str = typer.Option(None, help="Materia dessas questoes (opcional)"),
    anotacao: str = typer.Option(None, help="Um recado sobre o dia"),
    plano_b: int = typer.Option(
        None, "--plano-b", help="Mostra o Plano B do dia: 30 ou 60 (minutos)",
    ),
) -> None:
    """O que estudar no dia, com horario, materia e questoes.

    Com --marcar, anota a meta do dia. Com --feitas (e --minutos), anota
    questoes feitas fora do radar como estudo extra: elas entram no "Fiz hoje"
    como anotado, e em acerto medido nenhum do radar.
    """
    try:
        quando = (date.fromisoformat(data) if data
                  else datetime.now(fuso_local()).date())
    except ValueError:
        console.print(f"[red]Data invalida: {data!r}.[/] Use AAAA-MM-DD.")
        raise typer.Exit(code=1)

    try:
        plano = cronograma.carregar()
    except cronograma.ErroNoCronograma as erro:
        console.print(f"[red]Problema no config/cronograma.yml:[/] {erro}")
        raise typer.Exit(code=1)

    # O numero digitado nao vai mais para o registro do dia (Etapa 1C): ele
    # vira um estudo extra, e entra na conta do dia pela mesma porta da tela.
    if feitas is not None or acertos is not None:
        if minutos is None:
            console.print("[red]Faltou --minutos:[/] questao anotada vira estudo "
                          "extra, e estudo sem tempo nao e estudo.")
            raise typer.Exit(code=1)
        try:
            servico.extra.anotar(data=quando, o_que="questoes", materia=materia,
                                 minutos=minutos, questoes=feitas, acertos=acertos,
                                 onde="qconcursos", plano=plano)
        except servico.extra.RegistroInvalido as erro:
            console.print(f"[red]Nao anotei:[/] {erro}")
            raise typer.Exit(code=1)
        console.print("[green]Anotado como estudo extra.[/]")

    if marcar:
        try:
            servico.cronograma.registrar(quando, marcar, anotacao, plano=plano)
        except servico.cronograma.RegistroInvalido as erro:
            console.print(f"[red]Nao marquei:[/] {erro}")
            raise typer.Exit(code=1)
        console.print("[green]Marcado.[/]")
    elif anotacao:
        console.print("[red]Faltou --marcar[/] (ideal, reduzida, minima ou nao_fiz).")
        raise typer.Exit(code=1)

    console.print(f"[bold]{cronograma.data_por_extenso(quando).capitalize()}[/]")

    if quando.weekday() == cronograma.DOMINGO:
        console.print("Domingo é descanso total.")
        return
    if quando < plano.inicio:
        faltam = (plano.inicio - quando).days
        console.print(
            f"O {plano.titulo} começa em {plano.inicio.strftime('%d/%m/%Y')} "
            f"(daqui a {faltam} dia(s))."
        )
        return
    if quando > plano.fim:
        console.print(
            f"O {plano.titulo} terminou em {plano.fim.strftime('%d/%m/%Y')}."
        )
        return

    gravado = plano.dia(quando)
    if gravado is None:
        console.print("[yellow]Esse dia esta dentro do ciclo, mas nao esta no "
                      "cronograma.[/]")
        return

    # A mesma conta da tela: dia passado mostra a carga que valia naquele
    # dia, e semana que ainda nao chegou fica na carga do plano.
    nivel = servico.cronograma.nivel_do_dia(plano, quando)
    if plano_b is not None:
        _mostrar_plano_b(plano, quando, plano_b, nivel.efetivo)
        return
    dia = cronograma.montar_dia(plano, quando, nivel.efetivo)

    cabecalho = f"Semana {dia.semana}"
    if dia.semana in plano.semanas:
        cabecalho += f" — {plano.semanas[dia.semana]}"
    console.print(escape(cabecalho))
    console.print(f"[bold]Nível {nivel.efetivo}[/] · {escape(nivel.motivo)}")
    if dia.feriado:
        console.print(f"[bold dark_orange]{escape(dia.feriado)}[/]")

    # As faixas que eu risquei na tela, pela mesma regra dela: check cujo
    # titulo nao bate mais com o cronograma.yml nao conta.
    estado = servico.cronograma.estado_do_dia(quando)
    feitas = servico.cronograma.faixas_feitas(dia, estado)
    anotado = servico.cronograma.valores_das_faixas(dia, estado)

    for chave in cronograma.BLOCOS:
        faixas = getattr(dia, chave)
        if not faixas:
            continue
        console.print(f"\n[bold cyan]{escape(plano.blocos[chave].nome)}[/]")
        for indice, faixa in enumerate(faixas):
            if faixa.desligada:
                console.print(f"[dim]{cronograma.FRASE_DO_ANKI_DESATIVADO}[/]")
                continue
            partes = [cronograma.TIPO_LEGIVEL[faixa.tipo]]
            if faixa.rotulo:
                partes[0] = faixa.rotulo
            if faixa.materia:
                partes.append(faixa.materia)
            if faixa.titulo != partes[0]:     # evita "Pausa · Pausa"
                partes.append(faixa.titulo)
            linha = (f"{faixa.inicio:%H:%M}-{faixa.fim:%H:%M}  "
                     + escape(" · ".join(partes)))
            if faixa.questoes:
                linha += f"  [bold]{faixa.questoes} questões[/]"
            if faixa.cronometrado:
                linha += "  [magenta]⏱ cronometrado[/]"
            if faixa.opcional:
                linha += "  [dim](bônus, fora do total)[/]"
            if faixa.tipo == "pausa":
                linha = f"[dim]{linha}[/]"
            if (chave, indice) in feitas:
                linha = f"[green]{escape('[✓]')}[/] {linha}"
                feita = anotado.get((chave, indice))
                if feita and feita.questoes:
                    resultado = (f"{feita.acertos}/{feita.questoes}"
                                 if feita.acertos is not None
                                 else f"{feita.questoes} feitas")
                    if feita.porcentagem is not None:
                        resultado += f" · {feita.porcentagem}%"
                    if feita.consulta:
                        resultado += " · com consulta"
                    linha += f"  [green]{escape(resultado)}[/]"
            console.print(linha)

    console.print(f"\nTotal do dia: [bold]{dia.total_questoes} questões[/] "
                  f"e {dia.minutos_de_estudo} min de estudo de manhã")
    if dia.reduzida:
        console.print(f"[yellow]Reduzida:[/] {escape(dia.reduzida)}")
    if dia.minima:
        console.print(f"[yellow]Mínima:[/] {escape(dia.minima)}")

    extras = servico.extra.do_dia(quando)
    if extras:
        console.print("\n[bold cyan]➕ Estudo extra[/]")
        for linha_extra in extras:
            console.print("  " + escape(_extra_legivel(linha_extra)))

    conta = servico.metricas.do_dia(quando, plano)
    if not conta.vazio:
        console.print(f"\n[bold]Fiz hoje:[/] {escape(_totais_legiveis(conta))}")

    registro = servico.cronograma.registros(quando, quando).get(quando)
    if registro:
        console.print(f"\n[bold]Como foi:[/] {_registro_legivel(registro)}")


META_LEGIVEL = {"ideal": "Ideal", "reduzida": "Reduzida", "minima": "Mínima",
                "nao_fiz": "Não fiz"}


def _mostrar_plano_b(plano, quando, minutos: int, nivel: int) -> None:
    """O Plano B do dia no terminal: na ordem, sem horario. So mostra - quem
    ativa e a tela (ou o dia fica como estava)."""
    try:
        dia = cronograma.montar_plano_b(plano, quando, minutos, nivel)
    except cronograma.ErroNoCronograma as erro:
        console.print(f"[red]Sem Plano B:[/] {erro}")
        raise typer.Exit(code=1)

    console.print(f"[bold red]🆘 Plano B ({minutos} min) — o mínimo de hoje[/]")
    console.print("[dim]Dia corrido: sem teoria, só o essencial e questões de "
                  "prova do tema. Conta como Mínima.[/]")
    for ordem, faixa in enumerate(dia.plano_b, start=1):
        linha = f"{ordem}º  " + escape(faixa.titulo)
        if faixa.duracao:
            linha += f"  [dim]({faixa.duracao} min)[/]"
        if faixa.questoes:
            linha += f"  [bold]{faixa.questoes} questões[/]"
        if faixa.opcional:
            linha += "  [dim](se sobrar tempo)[/]"
        console.print(linha)
        for artigo in faixa.artigos:
            console.print(f"     • [bold]{escape(artigo.artigos)}[/] — {escape(artigo.porque)}")
        if faixa.aviso:
            console.print(f"     [dark_orange]⚠ {escape(faixa.aviso)}[/]")
        if faixa.filtro:
            console.print(f"     [dim]Filtro: {escape(faixa.filtro)}[/]")
        if faixa.detalhe and faixa.tipo != "essencial":
            console.print(f"     {escape(faixa.detalhe)}")
        if faixa.link:
            console.print(f"     [dim]{faixa.link}[/]")


def _extra_legivel(extra) -> str:
    """"Questoes · LEP · Progressao · 30 min · 12/15 · Qconcursos"."""
    partes = [servico.extra.O_QUE.get(extra.o_que, extra.o_que)]
    if extra.materia:
        partes.append(extra.materia)
    if extra.assunto:
        partes.append(extra.assunto)
    partes.append(cronograma.duracao_legivel(extra.minutos))
    if extra.questoes:
        feitas = (f"{extra.acertos}/{extra.questoes}" if extra.acertos is not None
                  else f"{extra.questoes} questões")
        if extra.consulta:
            feitas += " (com consulta)"
        partes.append(feitas)
    partes.append(servico.extra.ONDE.get(extra.onde, extra.onde))
    return " · ".join(partes)


def _totais_legiveis(conta) -> str:
    """A mesma linha da tela, pelas mesmas frases do `servico.metricas`."""
    partes = [servico.metricas.frase_da_conta(conta.total)]
    if conta.minutos:
        de_onde = []
        if conta.faixas.minutos:
            de_onde.append(f"{cronograma.duracao_legivel(conta.faixas.minutos)} do plano")
        if conta.extra.minutos:
            de_onde.append(f"{cronograma.duracao_legivel(conta.extra.minutos)} extra")
        tempo = cronograma.duracao_legivel(conta.minutos) + " de estudo"
        if len(de_onde) > 1:
            tempo += " (" + " + ".join(de_onde) + ")"
        partes.append(tempo)
    linha = " · ".join(partes)
    if conta.radar.medidas and conta.anotado.medidas:
        linha += (f"\n  medido no radar: {conta.radar.porcentagem}% em "
                  f"{conta.radar.medidas} · anotado: "
                  f"{conta.anotado.porcentagem}% em {conta.anotado.medidas}")
    if conta.total.ia:
        linha += f"\n  {servico.metricas.frase_da_ia(conta.total)}: conta no volume"
    return linha


def _registro_legivel(registro) -> str:
    """A meta e o recado. O numero do dia e o "Fiz hoje", calculado: a copia
    que o registro antigo guardava nao aparece mais (Etapa 1C)."""
    partes = [META_LEGIVEL.get(registro.meta, registro.meta)]
    partes.append(f"anotado em {formatar_data(registro.anotado_em)}")
    texto = escape(" · ".join(partes))
    if registro.anotacao:
        texto += f"\n  [dim]{escape(registro.anotacao)}[/]"
    return texto


@app.command()
def classificar(
    pedido: bool = typer.Option(
        False, "--pedido", help="Escreve data/pedido_ia.json com as questoes do alvo"),
    materia: list[str] = typer.Option(
        None, help="So estas materias, pelo caminho do no (pode repetir)"),
    evidencia: str = typer.Option(
        "alvo", help="De onde vem a questao: alvo ou complementar"),
    catalogo: bool = typer.Option(
        False, "--catalogo",
        help="No complementar: propoe o assunto pelo catalogo de palavras-chave "
             "(automatico, 🟡, para conferir por amostra)"),
    genericos: bool = typer.Option(
        False, "--genericos",
        help="No complementar: as questoes de bloco generico (Conhecimentos "
             "Especificos), agrupadas pela materia que o termo sugere"),
    importar: Path = typer.Option(
        None, "--importar", help="Le a resposta (data/resposta_ia.json) e grava"),
) -> None:
    """Classifica questoes na arvore de conteudos, pelo Claude Code.

    --pedido escreve o pedido (um por materia, com a arvore e as regras); a
    resposta volta com --importar, que recusa assunto fora do edital, tipo fora
    da lista, falta de justificativa e questao que nao estava no pedido.

    --evidencia complementar pede as provas FEPESE aceitas no acervo
    complementar, em vez das do alvo. Prova fora do acervo nao e classificada,
    e o que sai dai nunca entra na incidencia da Policia Penal.
    """
    if importar is not None:
        _importar_resposta_da_ia(importar)
        return
    if catalogo:
        if evidencia != "complementar" or not materia:
            console.print("[red]--catalogo pede --evidencia complementar e ao menos "
                          "uma --materia[/] (ex.: --materia \"Língua Portuguesa\").")
            raise typer.Exit(code=1)
        for nome in materia:
            r = servico.complementar.classificar_pelo_catalogo(nome)
            console.print(f"[green]{escape(nome)}: {r.propostas} proposta(s)[/] "
                          f"(automaticas, para conferir por amostra)")
            console.print(f"  [dim]sem linha: {r.sem_assunto} sem palavra do catalogo, "
                          f"{r.ambiguas} com mais de um assunto, {r.sem_par_no_edital} "
                          f"sem par no edital; {r.ja_classificadas} ja tinham "
                          f"classificacao[/]")
            for assunto, quantas in sorted(r.por_assunto.items(), key=lambda x: -x[1]):
                console.print(f"    {escape(assunto)}: {quantas}")
        return
    if not pedido:
        console.print("Use --pedido para escrever o pedido, ou --importar ARQUIVO.")
        raise typer.Exit(code=1)
    try:
        lote = servico.manual.pedido_de_classificacao(
            list(materia or []), evidencia, genericos=genericos)
    except ValueError as erro:
        console.print(f"[red]{erro}[/]")
        raise typer.Exit(code=1)
    if not lote["pedidos"]:
        onde = " em " + ", ".join(materia) if materia else ""
        console.print(f"[yellow]Nada a pedir:[/] nenhuma questao do {evidencia} "
                      f"sem conferencia{onde}.")
        return
    destino = servico.manual.salvar_pedido(lote)
    total = sum(len(p["questoes"]) for p in lote["pedidos"])
    console.print(f"[green]{len(lote['pedidos'])} pedido(s), {total} questao(oes)[/] "
                  f"em {destino}")
    for p in lote["pedidos"]:
        if p.get("bloco_generico"):
            marca = " [dim](bloco generico: a materia e suspeita do termo)[/]"
        else:
            marca = " [dim](fora do edital atual)[/]" if p["fora_do_edital"] else ""
        console.print(f"  {p['id']}: {escape(p['materia'])} - {len(p['questoes'])}{marca}")


@app.command()
def desempenho(
    materia: str = typer.Option(None, help="So uma materia, pelo nome do no"),
    desde_o_inicio: bool = typer.Option(
        False, "--desde-o-inicio",
        help="Tudo, e nao so o ciclo em andamento (o padrao)"),
    revisar: bool = typer.Option(
        False, "--revisar", help="So o que voltou para revisao hoje"),
) -> None:
    """O meu desempenho por no da arvore, com o estado e a amostra de cada um.

    Duas origens, NUNCA somadas num numero so: "radar" e questao real
    respondida aqui dentro, pela ultima resposta de cada; "anotado" e o que eu
    digitei das faixas e dos extras do Qconcursos. So o respondido sem consulta
    conta para o estado. Questao escrita por IA nao entra em nada disto.
    """
    from radar import amostra as regua
    from radar.servico import desempenho_por_conteudo as por_conteudo

    recorte = por_conteudo.SEMPRE if desde_o_inicio else por_conteudo.CICLO
    rotulo = "desde o inicio" if desde_o_inicio else "o ciclo em andamento"

    if revisar:
        fila = servico.estudo.para_revisar(recorte=recorte)
        if not fila:
            console.print("[green]Nada vencido.[/] Conteudo que eu nunca "
                          "estudei nao entra: revisar o que eu nao vi nao e "
                          "revisao.")
            return
        tabela = Table(title=f"Para revisar hoje ({len(fila)})", title_justify="left")
        for coluna in ("Conteudo", "Por que", "Atraso", "A refazer"):
            tabela.add_column(coluna)
        for r in fila:
            refazer = []
            if r.erradas:
                refazer.append(f"{len(r.erradas)} errada(s) no radar")
            if r.erros_do_caderno:
                refazer.append(f"{len(r.erros_do_caderno)} no caderno")
            tabela.add_row(escape(r.caminho), escape(r.porque),
                           f"{r.atraso} dia(s)" if r.atraso else "-",
                           escape(" · ".join(refazer)) or "-")
        console.print(tabela)
        return

    linhas = por_conteudo.tela(recorte, materia)
    if not linhas:
        console.print(f"[yellow]Nada respondido em {rotulo}[/], ou o que eu "
                      f"respondi nao esta classificado em conteudo nenhum.")
        raise typer.Exit(code=1)

    minimos = regua.carregar()
    tabela = Table(title=f"Meu desempenho — {rotulo}", title_justify="left")
    for coluna in ("Conteudo", "Estado", "Acerto", "Radar x anotado", "Amostra"):
        tabela.add_column(coluna)
    for linha in linhas:
        recuo = "  " * linha.profundidade
        taxa = (f"{linha.estado.porcentagem}%"
                if linha.estado.porcentagem is not None else "-")
        tabela.add_row(escape(recuo + linha.nome), escape(linha.estado.nome),
                       taxa, escape(linha.divisao), escape(linha.estado.amostra))
    console.print(tabela)
    console.print(
        f"[dim]Minimos do config/amostra.yml: {minimos.do_nivel('materia')} na "
        f"materia, {minimos.do_nivel('assunto')} no assunto, "
        f"{minimos.do_nivel('subassunto')} no subassunto ou elemento. Abaixo do "
        f"minimo o numero aparece e nao entra em ordenacao nem em projecao.[/]")

    refazer = servico.estudo.refazer()
    console.print(f"[dim]A refazer: {len(refazer.do_radar)} errada(s) no radar · "
                  f"{len(refazer.do_caderno)} no caderno de erros (as duas listas "
                  f"nunca se somam).[/]")


@app.command()
def incidencia(
    materia: str = typer.Option(None, help="So uma materia, pelo nome do no"),
    padroes: bool = typer.Option(
        False, "--padroes", help="Mostra os padroes de cobranca de cada no"),
) -> None:
    """O mapa de incidencia do concurso-alvo, por no da arvore, com a amostra.

    So o alvo (2013 e 2019): o complementar nunca entra nesta conta. Anuladas
    e pendentes ficam fora da contagem e aparecem a parte, com o numero.
    """
    from radar import incidencia as regra

    mapas = servico.incidencia.mapa(materia)
    if not mapas:
        console.print("[yellow]Nada no mapa[/] (a arvore esta vazia ou a materia nao existe).")
        raise typer.Exit(code=1)
    minimos = regra.carregar_minimos()
    # A linha do acervo complementar anda ao lado da do alvo, e nunca somada
    # a ela (secao 4 do pedido).
    complementares = servico.incidencia.linhas_complementares()
    for m in mapas:
        tabela = Table(title=f"{m.materia} — {m.topo.amostra} · {m.topo.rotulo}",
                       title_justify="left")
        for coluna in ("Conteudo", "Policia Penal SC", "O que aconteceu",
                       "Complementar FEPESE", "Anos", "Tipo"):
            tabela.add_column(coluna)
        for linha in m.linhas[1:]:
            recuo = "  " * (linha.profundidade - 1)
            tipos = ", ".join(f"{t} ({n})" for t, n in linha.tipos[:2])
            do_acervo = complementares.get(linha.caminho)
            tabela.add_row(escape(recuo + linha.nome), linha.amostra, linha.rotulo,
                           do_acervo.amostra if do_acervo and do_acervo.questoes else "—",
                           ", ".join(map(str, linha.anos)) or "—", escape(tipos) or "—")
        console.print(tabela)
        topo = complementares.get(m.topo.caminho)
        console.print(f"   Policia Penal SC: {m.topo.amostra} · "
                      f"{topo.frase if topo else 'Acervo complementar FEPESE: nada no acervo'}"
                      " (as duas nunca se somam)")
        console.print(f"   fora da conta: {m.anuladas} anulada(s) · {m.pendentes} pendente(s)"
                      f" · provas da materia: {m.provas}")
        if padroes:
            abaixo = 0
            for linha in m.linhas:
                p = regra.padroes(linha, minimos)
                if not p.suficiente:
                    abaixo += 1
                    continue
                console.print(f"   [bold]{escape(linha.nome)}[/]: {p.amostra}")
                if p.comandos:
                    console.print("     comando: " + ", ".join(
                        f"{c.nome} ({c.quantas})" for c in p.comandos))
                if p.tipos:
                    console.print("     tipo: " + ", ".join(f"{t} ({n})" for t, n in p.tipos))
                if p.termos:
                    console.print("     termos: " + ", ".join(t.palavra for t in p.termos))
            if abaixo:
                console.print(f"   {abaixo} no(s) abaixo do minimo ({minimos.questoes} questoes "
                              f"em {minimos.provas} provas): {regra.FRASE_SEM_EVIDENCIA}")
        console.print()


@app.command()
def complementar(
    caminho: str = typer.Option(None, help="Onde gravar (padrao: docs/complementar.md)"),
    aplicar: bool = typer.Option(
        False, "--aplicar",
        help="Grava quais provas entram em data/acervo_complementar.json"),
) -> None:
    """Levanta o acervo complementar FEPESE: o que ha, e o que esta pronto.

    Sem --aplicar, so LE o banco e o manifesto e escreve o relatorio: nenhuma
    prova entra em estatistica. Com --aplicar, grava a lista das que entram -
    as que tem materia do edital de 2019 e passam na validacao minima. O
    complementar nunca se soma a incidencia do alvo.
    """
    from radar import complementar as regra

    destino = Path(caminho) if caminho else servico.complementar.caminho_do_relatorio()
    levantado = servico.complementar.escrever(destino)
    por_materia, validadas, cadernos = levantado
    if not cadernos:
        console.print("[yellow]Nenhuma prova complementar no banco.[/] Rode "
                      "`radar extrair` ou confira a evidencia das provas.")
        raise typer.Exit(code=1)

    tabela = Table(title="Acervo complementar FEPESE, por materia do meu edital",
                   title_justify="left")
    for coluna in ("Materia", "Pelo nome", "Provas", "Por termo (indicio)", "Provas"):
        tabela.add_column(coluna)
    for m in por_materia:
        tabela.add_row(escape(m.materia), str(m.pelo_nome), str(m.provas_pelo_nome),
                       str(m.por_termo), str(m.provas_por_termo))
    console.print(tabela)

    validadas_de_vez = sum(1 for v in validadas.values() if v.entra_nos_padroes)
    so_classificar = sum(1 for v in validadas.values()
                         if v.pode_classificar and not v.entra_nos_padroes)
    recusadas = sum(1 for v in validadas.values() if not v.pode_classificar)
    console.print(
        f"{len(cadernos)} prova(s) complementar(es): [green]{validadas_de_vez} "
        f"validada(s)[/] (extracao inteira e gabarito {regra.DEFINITIVO}), "
        f"[yellow]{so_classificar} so para classificar[/] (gabarito provisorio "
        f"ou ausente: fora dos padroes de cobranca), "
        f"[red]{recusadas} recusada(s)[/]."
    )
    console.print("A incidencia do alvo NAO muda com nada disto: as duas "
                  "evidencias nunca se somam.")
    console.print(f"Relatorio em {destino}")

    if not aplicar:
        decididas = servico.complementar.decidir_todas(levantado=levantado)
        entram = sum(1 for r in decididas if r.aceita)
        console.print(f"[dim]Pela regra do edital de 2019, {entram} prova(s) "
                      f"entrariam. Nada foi gravado: rode com --aplicar.[/]")
        return

    registros, mudanca = servico.complementar.aplicar(levantado=levantado)
    aceitas = [r for r in registros if r.aceita]
    nos_padroes = sum(1 for r in registros if r.entra_nos_padroes)
    console.print(f"[green]{len(aceitas)} prova(s) no acervo complementar[/] "
                  f"({nos_padroes} também nos padroes de cobranca), "
                  f"{len(registros) - len(aceitas)} fora, cada uma com o motivo. "
                  f"Gravado em {servico.complementar.caminho_do_registro()}")
    if mudanca["entraram"]:
        console.print(f"  entraram agora: {len(mudanca['entraram'])}")
    if mudanca["sairam"]:
        console.print(f"  [yellow]sairam: {len(mudanca['sairam'])}[/]")


@app.command()
def migrar(
    desfazer: bool = typer.Option(
        False, "--desfazer",
        help="Devolve o banco à cópia da última migração (data/copias/)",
    ),
) -> None:
    """Leva o banco à estrutura atual, com cópia antes e "antes x depois".

    Qualquer comando do radar já migra sozinho na primeira vez; este mostra a
    conta. Rodar de novo num banco migrado não faz nada.
    """
    from radar import migracoes
    from radar.db import get_engine

    if desfazer:
        try:
            copia = migracoes.desfazer()
        except FileNotFoundError as erro:
            console.print(f"[red]{erro}[/]")
            raise typer.Exit(code=1)
        console.print(f"[green]Banco devolvido à cópia de {copia}[/] (versão "
                      f"{migracoes.versao(get_engine())}). Para ficar nela, volte "
                      f"também o código: o próximo comando do radar novo migra de novo.")
        return

    # Sem passar pelo `criar_tabelas`, que migraria em silêncio antes da conta.
    relatorio = migracoes.migrar(get_engine())
    if not relatorio.mudou:
        console.print(f"[green]Banco já está na versão {relatorio.para}.[/] Nada a migrar.")
        return
    tabela = Table(title=f"Migração da versão {relatorio.de} para a {relatorio.para}")
    for coluna in ("Tabela", "Antes", "Depois"):
        tabela.add_column(coluna)
    for nome in sorted(set(relatorio.antes) | set(relatorio.depois)):
        tabela.add_row(nome, str(relatorio.antes.get(nome, "—")),
                       str(relatorio.depois.get(nome, "—")))
    console.print(tabela)
    console.print(f"Nenhuma linha perdida. Cópia de antes em {relatorio.copia}")


@app.command()
def conteudos(
    pendentes: bool = typer.Option(
        False, "--pendentes", help="Lista as questões sem classificação, por prova"),
    semear: bool = typer.Option(
        False, "--semear", help="Põe na árvore o que o edital tem e ela ainda não"),
) -> None:
    """A árvore de conteúdos: matéria > assunto > subassunto > elemento."""
    from rich.tree import Tree

    from radar import conteudos as arvore_de_conteudos
    from radar import foco

    if semear:
        entraram = servico.conteudos.semear(programa=foco.programa_do_alvo())
        console.print(f"[green]{entraram}[/] nó(s) novo(s) do edital")

    nos = servico.conteudos.nos()
    if not nos:
        console.print("[yellow]A árvore está vazia.[/] Rode `radar conteudos "
                      "--semear` com o edital do alvo no acervo.")
        raise typer.Exit(code=1)

    raiz = Tree("[bold]Conteúdos[/]")
    galhos = {None: raiz}
    for no in nos:
        rotulo = escape(no.nome)
        if no.fora_do_edital:
            rotulo += " [dim](fora do edital atual)[/]"
        if no.tipo_elemento:
            rotulo += f" [dim]· {escape(no.tipo_elemento)}[/]"
        galhos[no.caminho] = galhos[no.pai].add(rotulo)
    console.print(raiz)
    do_edital = sum(1 for no in nos if no.nivel == "materia" and not no.fora_do_edital)
    fora = sum(1 for no in nos if no.fora_do_edital)
    partes = [f"{do_edital} matéria(s) do edital"]
    if fora:
        partes.append(f"{fora} fora do edital atual")
    for nivel in arvore_de_conteudos.NIVEIS[1:]:
        quantos = sum(1 for no in nos if no.nivel == nivel)
        if quantos:
            partes.append(f"{quantos} {nivel}(s)")
    console.print("   " + " · ".join(partes))

    if pendentes:
        situacao = servico.conteudos.pendentes()
        console.print("\n[bold]Sem classificação (pendentes)[/], fora as anuladas")
        console.print("   " + " · ".join(
            f"{n} {ev}" for ev, n in sorted(situacao.por_evidencia.items())))
        # Prova a prova so o alvo: o complementar sao ~200 cadernos, e a lista
        # inteira esconderia as duas linhas que importam.
        tabela = Table(title="Provas do alvo")
        for coluna in ("Ano", "Cargo", "Pendentes"):
            tabela.add_column(coluna)
        complementares = []
        for ev, ano, cargo, n in situacao.por_prova:
            if ev == servico.evidencia.ALVO:
                tabela.add_row(str(ano or "—"), escape(cargo or "—"), str(n))
            else:
                complementares.append(n)
        console.print(tabela)
        if complementares:
            console.print(f"   complementar: {sum(complementares)} pendente(s) em "
                          f"{len(complementares)} prova(s) (cargo e ano)")


@app.command()
def conferir_dias(
    de: str = typer.Option(None, help="Primeiro dia, AAAA-MM-DD (padrao: inicio do ciclo)"),
    ate: str = typer.Option(None, help="Ultimo dia, AAAA-MM-DD (padrao: hoje)"),
    aplicar: bool = typer.Option(
        False, "--aplicar",
        help="Corrige o que a conferencia propoe, com copia de seguranca antes",
    ),
) -> None:
    """Confere os dias gravados contra a regra de contagem. So le.

    Uma linha por achado: o que esta gravado, o que a regra diz e o que fazer.
    Com --aplicar, e so depois de aprovar o relatorio: copia o banco e os JSON
    do diario, corrige o que a conferencia marcou e confere de novo.
    """
    try:
        inicio = date.fromisoformat(de) if de else None
        fim = date.fromisoformat(ate) if ate else None
    except ValueError:
        console.print("[red]Data invalida.[/] Use AAAA-MM-DD.")
        raise typer.Exit(code=1)
    try:
        plano = cronograma.carregar()
    except cronograma.ErroNoCronograma as erro:
        console.print(f"[red]Problema no config/cronograma.yml:[/] {erro}")
        raise typer.Exit(code=1)

    antes = servico.conferencia.conferir(inicio, fim, plano=plano)
    _mostrar_conferencia(antes)
    a_corrigir = sum(len(dia.a_corrigir) for dia in antes)
    if not aplicar:
        if a_corrigir:
            console.print(f"\n{a_corrigir} correcao(oes) proposta(s). Nada mudou: "
                          "para aplicar, rode de novo com --aplicar.")
        else:
            console.print("\n[green]Nada a corrigir.[/]")
        return

    pasta = servico.conferencia.aplicar(antes)
    if pasta is None:
        console.print("\n[green]Nada a corrigir:[/] nada foi gravado.")
        return
    console.print(f"\n[green]{a_corrigir} correcao(oes) aplicada(s).[/] "
                  f"Copia de seguranca em {pasta}")
    depois = servico.conferencia.conferir(inicio, fim, plano=plano)
    console.print("\n[bold]Depois da correcao[/]")
    _mostrar_conferencia(depois)
    _mostrar_antes_e_depois(antes, depois)


def _mostrar_conferencia(dias) -> None:
    tabela = Table(title="Conferencia dos dias gravados", show_lines=True)
    for coluna in ("Dia", "O que", "O que esta gravado", "O que a regra diz", "Proposta"):
        tabela.add_column(coluna)
    for dia in dias:
        rotulo = f"{dia.data:%d/%m}"
        if not dia.gravado and not dia.achados:
            tabela.add_row(rotulo, "-", "nada gravado", "-", "-")
            continue
        for achado in dia.achados:
            proposta = escape(achado.proposta)
            if achado.corrige:
                proposta = f"[yellow]{proposta}[/]"
            tabela.add_row(rotulo, escape(achado.tipo), escape(achado.gravado),
                           escape(achado.regra), proposta)
        tabela.add_row(rotulo, "conta do dia", "-",
                       escape(f"{dia.conta} · "
                              f"{cronograma.duracao_legivel(dia.minutos)} de estudo"),
                       "-")
    console.print(tabela)


def _mostrar_antes_e_depois(antes, depois) -> None:
    tabela = Table(title="Totais antes x depois")
    for coluna in ("Dia", "Antes", "Depois"):
        tabela.add_column(coluna)
    for a, d in zip(antes, depois):
        if not (a.gravado or d.gravado):
            continue
        tabela.add_row(
            f"{a.data:%d/%m}",
            escape(f"{a.conta} · {cronograma.duracao_legivel(a.minutos)}"),
            escape(f"{d.conta} · {cronograma.duracao_legivel(d.minutos)}"),
        )
    console.print(tabela)


if __name__ == "__main__":
    app()
