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

from radar import acervo, alvo as alvos, avisos, config, servico
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
        True,
        "--avisar/--sem-avisar",
        help="Manda no Telegram o que mudou nos favoritos e os concursos novos",
    ),
) -> None:
    """Roda a rotina inteira, na ordem certa.

    Existe porque manter o radar em dia exigia seis comandos numa sequencia que
    so fazia sentido para quem a escreveu: coletar antes de detalhar, detalhar
    antes de baixar edital, edital antes de elegibilidade.

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
) -> None:
    """Monta o acervo: le os hotsites e baixa edital, prova e gabarito.

    Comeca pelo alvo principal de config/alvo.yml, esteja ele onde estiver.
    Depois vem o concurso ja encerrado perto de casa - os que tem prova
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
) -> None:
    """Classifica o assunto fino das questoes de Conhecimentos Especificos.

    Esta e a UNICA parte do radar que custa dinheiro. Por padrao ela so simula:
    para gastar de verdade e preciso passar --valendo.

    A chave vai em RADAR_ANTHROPIC_KEY, no .env - nunca no codigo.
    """
    from radar import assuntos as classificador, config as configuracao

    pendentes = servico.questoes_sem_assunto(limite)
    if not pendentes:
        console.print("[green]Nenhuma questao pendente de assunto.[/]")
        return

    entrada, saida, custo = classificador.estimar(pendentes)
    console.print(f"Questoes a classificar: [bold]{len(pendentes)}[/]")
    console.print(
        f"[dim]{entrada:,} tokens de entrada, {saida:,} de saida[/]".replace(",", ".")
    )
    console.print(
        f"Custo estimado: [bold]US$ {custo:.2f}[/] "
        f"[dim](~R$ {custo * 5.5:.2f}, a 5,50)[/]"
    )
    console.print(f"[dim]Modelo: {classificador.MODELO}[/]")

    if simular:
        console.print()
        console.print("[yellow]Isto foi so uma simulacao: nada foi gasto.[/]")
        console.print("Para valer, rode: [bold]radar assuntos --valendo[/]")
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
        resultado = servico.classificar_assuntos(limite=limite, teto_em_dolar=teto)

    console.print(
        f"[green]{resultado['classificados']} questao(oes) classificada(s)[/], "
        f"{resultado['gravados']} linha(s) do banco atualizada(s)"
    )
    console.print(
        f"Gasto real: [bold]US$ {resultado['custo']:.4f}[/] "
        f"[dim](~R$ {resultado['custo'] * 5.5:.2f}) em "
        f"{resultado['chamadas']} chamada(s)[/]"
    )
    if resultado.get("parou_no_teto"):
        console.print(
            "[yellow]Parei no teto de gasto.[/] Rode de novo para continuar."
        )
    if resultado.get("falhas"):
        console.print(f"[dim]{resultado['falhas']} lote(s) falharam.[/]")


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
