"""Linha de comando do radar.

    radar coletar
    radar listar --uf SC --termo "guarda municipal"
    radar web
"""
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from radar import acervo, avisos, config, servico
from radar import provas as _provas
from radar.util import (
    dias_ate,
    formatar_data,
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
    "remoto": "Longe",
    "indefinida": "A confirmar",
}

CORES_DO_ANEL = {
    "nucleo": "bold green",
    "proximo": "yellow",
    "remoto": "dim",
    "indefinida": "magenta",
}


@app.command()
def listar(
    uf: str = typer.Option(None, help="Sigla do estado, ex: SC"),
    banca: str = typer.Option(None, help="Nome da banca, ex: FEPESE"),
    termo: str = typer.Option(None, help="Palavra no titulo ou no resumo"),
    situacao: str = typer.Option(None, help="Ex: edital_publicado, autorizado"),
    relevancia: str = typer.Option(
        None, help="nucleo, proximo, remoto ou indefinida"
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
) -> None:
    """Monta o acervo: le os hotsites e baixa edital, prova e gabarito.

    Comeca pelos concursos ja encerrados perto de casa - sao os que tem prova
    publicada e mostram o padrao da banca na minha regiao.

    Os PDFs ficam em data/provas/ e NAO vao para o git. O que e versionado e o
    manifesto data/provas.json, com o sha256 de cada arquivo.
    """
    console.print(
        f"Vou ler ate [bold]{limite}[/] concurso(s). Cada um custa 2 paginas "
        f"mais os PDFs, com pausa de 1,5s entre as requisicoes."
    )

    with console.status("Montando o acervo..."):
        resultado = servico.montar_acervo(limite=limite, abertos=abertos)

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

    Existe porque Guarda Municipal e Policia Penal nao tem prova nenhuma no
    acervo. A lista mostra o que existe e em cima de que a semelhanca foi
    medida - dividir uma palavra no nome nao faz duas profissoes serem a
    mesma coisa.
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

        enviadas = avisos.enviar_varios(
            [avisos.formatar_retificacao(m) for m in resultado.mudaram]
        )
        console.print()
        console.print(f"[green]{enviadas} aviso(s) enviado(s).[/]")


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

    Nao le a pagina de todos: comeca pelo que ja esta perto, depois os
    concursos de SC que ficaram indefinidos, depois os federais. O que e de
    outro estado fica de fora.
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
) -> None:
    """Manda no Telegram os concursos novos que interessam.

    Avisa nucleo, proximo e indefinida. Cada concurso vira uma mensagem, com o
    link da fonte junto, e e marcado como avisado para nao repetir amanha.

    Precisa de RADAR_TELEGRAM_TOKEN e RADAR_TELEGRAM_CHAT_ID no .env.
    """
    resultado = servico.avisar(limite=limite)

    if not resultado.configurado:
        console.print(
            "[yellow]Telegram nao configurado.[/] Preencha no arquivo .env:\n"
            "  RADAR_TELEGRAM_TOKEN=...   (pegue com o @BotFather)\n"
            "  RADAR_TELEGRAM_CHAT_ID=... (pegue com o @userinfobot)"
        )
        return

    console.print(f"[green]{resultado}[/]")


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


@app.command()
def exportar(caminho: str = typer.Option(None, help="Destino do JSON")) -> None:
    """Grava o banco inteiro em data/concursos.json (o que vai para o git)."""
    destino = Path(caminho) if caminho else acervo.caminho_padrao()
    total = acervo.exportar(destino)
    console.print(f"[green]{total}[/] concurso(s) exportado(s) para {destino}")


@app.command()
def importar(caminho: str = typer.Option(None, help="Origem do JSON")) -> None:
    """Reconstroi o banco a partir do JSON. Seguro rodar quantas vezes quiser."""
    origem = Path(caminho) if caminho else acervo.caminho_padrao()
    total = acervo.importar(origem)
    if total == 0:
        console.print(f"[yellow]Nada a importar[/] (nao achei {origem})")
    else:
        console.print(f"[green]{total}[/] concurso(s) importado(s) de {origem}")


@app.command()
def web(
    porta: int = typer.Option(8000, help="Porta do servidor"),
    host: str = typer.Option(
        "127.0.0.1",
        help="Use 0.0.0.0 para abrir tambem no celular, na mesma rede wi-fi",
    ),
    recarregar: bool = typer.Option(
        False, help="Reinicia sozinho ao salvar arquivo (so para desenvolver)"
    ),
) -> None:
    """Sobe a interface web em http://localhost:8000"""
    import uvicorn

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
    if host == "0.0.0.0":  # noqa: S104 - escolha explicita do usuario
        console.print("Aberto na rede local: use o IP desta maquina no celular.")
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


if __name__ == "__main__":
    app()
