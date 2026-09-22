"""Gera o relatorio do projeto em PDF."""
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DESTINO = "RELATORIO_DO_PROJETO.pdf"

AZUL = colors.HexColor("#1d4ed8")
CINZA = colors.HexColor("#5c6572")
VERDE = colors.HexColor("#047857")
VERMELHO = colors.HexColor("#be123c")
AMBAR = colors.HexColor("#b45309")
BORDA = colors.HexColor("#d8dce3")
FUNDO = colors.HexColor("#f4f6f9")

base = getSampleStyleSheet()

E = {
    "titulo": ParagraphStyle(
        "titulo", parent=base["Title"], fontSize=22, leading=26,
        textColor=colors.HexColor("#13161d"), spaceAfter=4,
    ),
    "subtitulo": ParagraphStyle(
        "subtitulo", parent=base["Normal"], fontSize=10.5, leading=14,
        textColor=CINZA, alignment=1, spaceAfter=16,
    ),
    "h1": ParagraphStyle(
        "h1", parent=base["Heading1"], fontSize=13.5, leading=17,
        textColor=AZUL, spaceBefore=12, spaceAfter=5,
    ),
    "h2": ParagraphStyle(
        "h2", parent=base["Heading2"], fontSize=11, leading=14,
        textColor=colors.HexColor("#13161d"), spaceBefore=8, spaceAfter=3,
    ),
    "p": ParagraphStyle(
        "p", parent=base["Normal"], fontSize=9.4, leading=13.1,
        alignment=TA_JUSTIFY, spaceAfter=5,
    ),
    "item": ParagraphStyle(
        "item", parent=base["Normal"], fontSize=9.2, leading=12.6,
    ),
    "nota": ParagraphStyle(
        "nota", parent=base["Normal"], fontSize=8.8, leading=12,
        textColor=CINZA, spaceAfter=6,
    ),
    "codigo": ParagraphStyle(
        "codigo", parent=base["Normal"], fontName="Courier", fontSize=8.6,
        leading=12, textColor=colors.HexColor("#13161d"),
        backColor=FUNDO, borderPadding=6, spaceBefore=4, spaceAfter=8,
    ),
}


def p(texto, estilo="p"):
    return Paragraph(texto, E[estilo])


def lista(itens, estilo="item"):
    return ListFlowable(
        [ListItem(Paragraph(i, E[estilo]), leftIndent=12) for i in itens],
        bulletType="bullet", bulletFontSize=6, bulletOffsetY=-1,
        leftIndent=14, bulletColor=AZUL, spaceAfter=8,
    )


# Estilos das celulas. Texto puro numa celula do reportlab NAO quebra linha:
# ele vaza pela margem direita da pagina. Por isso toda celula vira Paragraph.
E["celula"] = ParagraphStyle(
    "celula", parent=base["Normal"], fontSize=8.8, leading=12,
)
E["celula_cabecalho"] = ParagraphStyle(
    "celula_cabecalho", parent=E["celula"], fontName="Helvetica-Bold",
    textColor=CINZA,
)
E["celula_estado"] = ParagraphStyle(
    "celula_estado", parent=E["celula"], fontName="Helvetica-Bold",
)


def _celula(valor, estilo, cor=None):
    if hasattr(valor, "wrap"):
        return valor
    if cor is not None:
        estilo = ParagraphStyle("c", parent=estilo, textColor=cor)
    return Paragraph(str(valor), estilo)


def tabela(linhas, larguras, cabecalho=True, cor_primeira=None, cores_por_texto=None):
    montadas = []
    for indice, linha in enumerate(linhas):
        if cabecalho and indice == 0:
            montadas.append([_celula(v, E["celula_cabecalho"]) for v in linha])
            continue
        cor = cor_primeira
        if cores_por_texto:
            cor = cores_por_texto.get(str(linha[0]).strip(), cor_primeira)
        montadas.append([
            _celula(v, E["celula_estado"] if (c == 0 and cor) else E["celula"],
                    cor if c == 0 else None)
            for c, v in enumerate(linha)
        ])
    linhas = montadas

    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, BORDA),
    ]
    if cabecalho:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, BORDA),
        ]
    t = Table(linhas, colWidths=larguras, repeatRows=1 if cabecalho else 0)
    t.setStyle(TableStyle(estilo))
    return t


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2 * cm, 1.2 * cm, "Radar de Concursos - relatorio do projeto")
    canvas.drawRightString(19 * cm, 1.2 * cm, f"pagina {doc.page}")
    canvas.setStrokeColor(BORDA)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.6 * cm, 19 * cm, 1.6 * cm)
    canvas.restoreState()


historia = []
a = historia.append

# ---------------------------------------------------------------- capa ------
a(Spacer(1, 1.2 * cm))
a(p("Radar de Concursos", "titulo"))
a(p(f"Relatorio completo do projeto &middot; {date.today().strftime('%d/%m/%Y')}",
    "subtitulo"))
a(HRFlowable(width="100%", thickness=1, color=BORDA, spaceAfter=14))

a(p("<b>O que este sistema faz.</b> Acompanha concursos publicos que valem a "
    "pena para voce - primeiro pelo lugar onde a prova e aplicada (Grande "
    "Florianopolis e regiao), depois por voce poder prestar, depois pelo "
    "salario. Alem de achar o concurso, ele baixa as provas antigas da banca, "
    "separa em questoes e deixa voce treinar."))

a(p("Tudo roda na sua maquina, com um banco SQLite. A coleta diaria roda "
    "sozinha no GitHub Actions e avisa no Telegram. Sao <b>679 testes "
    "automaticos</b>, nenhum deles indo a internet."))

# --------------------------------------------------------- numeros ----------
a(p("1. Como esta o sistema hoje", "h1"))

a(tabela([
    ["Area", "Numeros de agora"],
    ["Concursos no banco",
     "2.775 no total - 2.229 do agregador, 520 da FEPESE, 26 da IESES"],
    ["Perto de casa", "121 no nucleo (Grande Florianopolis) e 62 no anel proximo"],
    ["Com inscricao aberta", "6 perto de casa, o mais urgente vencendo hoje"],
    ["Acervo de provas",
     "298 documentos - 176 provas, 68 editais, 54 gabaritos, de 2 bancas"],
    ["Banco de questoes",
     "5.928 questoes de 156 cadernos, 2.187 com enunciado diferente"],
    ["Exigencias lidas", "23 concursos com escolaridade, idade, CNH e teste fisico"],
    ["Favoritos", "2 no mural"],
], [4.2 * cm, 12.3 * cm]))

a(Spacer(1, 6))
a(p("O acervo cobre FEPESE (5.021 questoes) e IESES (907). Nao ha nenhuma "
    "prova de Guarda Municipal nem de Policia Penal - esse limite aparece "
    "varias vezes neste relatorio, porque muda o que o sistema consegue "
    "prometer.", "nota"))

# ------------------------------------------------- o erro do email ----------
a(p("2. O erro que voce recebeu por e-mail", "h1"))

a(p("<b>Sintoma:</b> 'run failed: coleta diaria', todo dia, no seu e-mail. "
    "Era real, e foi corrigido hoje."))

a(p("<b>Causa.</b> O arquivo que le e grava o JSON do banco tinha uma lista "
    "escrita a mao com as colunas que sao data, para converter texto de volta "
    "em data ao importar. Essa lista envelheceu calada: a coluna "
    "<font face='Courier'>avisado_em</font> entrou na fase 2 e "
    "<font face='Courier'>detalhado_em</font> na 2.5, e nenhuma das duas foi "
    "acrescentada ali. O primeiro passo da coleta quebrava com "
    "\"'str' object has no attribute 'tzinfo'\"."))

a(p("<b>Por que nunca apareceu na sua maquina.</b> Aqui o banco ja existe, e o "
    "comando <font face='Courier'>radar importar</font> quase nunca roda. No "
    "GitHub Actions ele e o PRIMEIRO passo de toda coleta, num servidor que "
    "comeca sem banco nenhum - entao falhava sempre."))

a(p("<b>Como foi encontrado.</b> Clonei o repositorio numa pasta limpa, so com "
    "o que esta no git, e rodei os passos do workflow na mesma ordem. Os 679 "
    "testes passaram no clone; o que quebrou foi o importar."))

a(p("<b>Correcao.</b> A lista agora e perguntada ao proprio modelo do banco - "
    "nao ha mais nada para manter em dia a mao. Foram acrescentados 3 testes, "
    "e um deles compara a lista com o modelo e quebra se alguem acrescentar "
    "coluna de data sem atualizar. Depois da correcao, os cinco passos do "
    "workflow terminam com codigo 0."))

a(Spacer(1, 4))
a(p("<b>O que voce precisa fazer:</b> nada. A correcao ja esta no repositorio. "
    "A proxima coleta (amanha, 06:00) deve passar. Se quiser conferir antes, "
    "va na aba Actions do GitHub e clique em 'Run workflow'.", "nota"))

# ------------------------------------------------- o que foi feito ----------
a(p("3. O que foi construido, passo a passo", "h1"))

partes = [
    ("Coleta de concursos (3 fontes)",
     "O agregador Concursos no Brasil (feed RSS), a FEPESE (API do site dela) "
     "e a IESES (API da listagem de projetos). Cada fonte e um arquivo "
     "separado; nada fora dali sabe de onde o dado veio. A coleta faz upsert "
     "e nunca sobrescreve o que e seu (favorito e anotacao)."),
    ("Classificacao por distancia",
     "Tres aneis configurados em config/regioes.yml: nucleo, proximo e remoto. "
     "Concurso de SC e classificado pelo municipio; federal sem UF fica "
     "'a confirmar' em vez de chutar. Toda decisao guarda o motivo, para voce "
     "poder auditar."),
    ("Leitura da pagina do concurso",
     "De cada concurso relevante, le a pagina e tira prazo de inscricao, banca "
     "e municipio de lotacao - sem abrir PDF. E dali que sai tambem o endereco "
     "do hotsite da banca, que e a ponte para o acervo."),
    ("Avisos no Telegram",
     "Uma mensagem por concurso novo que interessa, sempre com o link junto. "
     "Cada concurso e avisado uma vez so, com teto de 10 por coleta."),
    ("Acervo de provas",
     "Baixa edital, caderno de prova e gabarito dos hotsites das bancas. Os "
     "PDFs nao vao para o git: vai um manifesto com o sha256 de cada arquivo, "
     "e 'radar baixar-provas' reconstroi a pasta noutra maquina."),
    ("Extracao de questoes",
     "Separa cada caderno em questoes, com materia e gabarito. Duas bancas, "
     "dois formatos: a FEPESE marca a resposta dentro do caderno; a IESES tem "
     "gabarito em PDF separado e nao diz a materia - essa vem do edital."),
    ("Simulado",
     "Voce responde questoes reais da banca, uma por tela, e ve o acerto por "
     "materia. Da para parar no meio e voltar depois: o lugar onde voce parou "
     "fica no banco, nao no navegador."),
    ("Macetes",
     "O costume da banca por contagem: o que mais cai, como ela pergunta, as "
     "questoes que ela repete, e a distribuicao do gabarito. Dois graficos de "
     "pizza. Nada e inventado - tudo da para conferir abrindo as provas."),
    ("Previsao de abertura",
     "Quando o proximo concurso de cada municipio deve sair, pelo ritmo do "
     "proprio municipio, limitado pela validade legal do concurso (2 a 4 anos)."),
    ("Elegibilidade e perfil",
     "Le o edital e grava escolaridade, idade, CNH e teste fisico; cruza com o "
     "seu perfil (config/perfil.yml) e diz se voce serve para a vaga, com o "
     "motivo junto."),
    ("Calendario",
     "Exporta os prazos em .ics para a agenda do celular, com lembrete dois "
     "dias antes do fim da inscricao."),
    ("Prova substituta",
     "Quando nao ha prova do cargo que voce quer, mostra a mais parecida que "
     "existe - e diz em cima de que a semelhanca foi medida."),
    ("Retificacao de edital",
     "Reconfere os editais em pe e acusa os que mudaram, pelo sha256 que o "
     "manifesto ja guardava. Avisa no Telegram."),
    ("Assunto fino (pago, desligado)",
     "Classifica o assunto de cada questao de Conhecimentos Especificos pela "
     "API da Claude. E a unica parte que custa dinheiro - US$ 0,26 uma vez - e "
     "simula por padrao: sem '--valendo' nao gasta nada."),
]

for titulo, texto in partes:
    a(KeepTogether([p(titulo, "h2"), p(texto)]))

# --------------------------------------------------------- checklist --------
a(p("4. Checklist: o que esta pronto", "h1"))

a(tabela([
    ["Estado", "Item", "Observacao"],
    ["PRONTO", "Fase 1 - coleta e banco", "3 fontes, upsert, 2.775 concursos"],
    ["PRONTO", "Fase 1.5 - filtro por distancia", "3 aneis, com motivo auditavel"],
    ["PRONTO", "Fase 1.55 - perfil e notas", "perfil.yml + campo de anotacao"],
    ["PRONTO", "Fase 1.6 - carga do historico", "feed paginado, ate 2020"],
    ["PRONTO", "Fase 2 - avisos no Telegram", "configurado e funcionando"],
    ["PRONTO", "Fase 2.2 - calendario .ics", "pagina explicativa + download"],
    ["PRONTO", "Fase 2.5 - elegibilidade", "escolaridade, idade, CNH, TAF"],
    ["PRONTO", "Fase 2.5 - retificacao", "pelo sha256, avisa no Telegram"],
    ["PRONTO", "Fase 3 - acervo de provas", "298 documentos, 2 bancas"],
    ["PRONTO", "Fase 3 - prova substituta", "com o motivo declarado"],
    ["PRONTO", "Fase 4 - questoes", "5.928, com materia e gabarito"],
    ["PRONTO", "Fase 4 - assunto fino", "codigo pronto; desligado por escolha"],
    ["PRONTO", "Fase 5 - simulado", "acerto por materia, revisao no fim"],
    ["PRONTO", "Fase 6 - previsao de abertura", "por municipio, com o motivo"],
    ["PRONTO", "Fase 7 - macetes", "a parte que sai de contagem"],
    ["PARCIAL", "Fase 1.7 - fontes federais", "3 testadas, nenhuma serve"],
    ["PARCIAL", "Fase 7 - pegadinhas", "depende da leitura por IA"],
], [2.1 * cm, 6.3 * cm, 8.1 * cm],
    cores_por_texto={"PRONTO": VERDE, "PARCIAL": AMBAR}))

a(Spacer(1, 10))
a(KeepTogether([p("5. O que ficou de fora, e por que", "h1"), p("Nada aqui esta 'esquecido' - cada item foi testado e descartado por um "
    "motivo concreto.", "nota")]))

a(tabela([
    ["Item", "Situacao"],
    ["Diario Oficial da Uniao",
     "Fora. O robots.txt proibe robo no site inteiro (Disallow: / para todos), "
     "igual ao DOM/SC."],
    ["Diario dos Municipios de SC",
     "Fora, mesmo motivo. O caminho legitimo e o alerta por e-mail do proprio "
     "site."],
    ["Portal Sigepe (federal)",
     "Testado e descartado: os 2.953 editais de la sao movimentacao interna de "
     "quem JA e servidor federal, e nao concurso aberto."],
    ["Querido Diario",
     "Entrou, mas rende pouco: cobre 1 dos seus 35 municipios (Florianopolis), "
     "e nao tem o ato de contratacao de banca."],
    ["Sinal 'contratou a banca'",
     "Sem fonte. Era o que daria 2 a 4 meses de antecedencia. Nenhuma das "
     "fontes disponiveis publica esse ato de forma acessivel."],
    ["Pegadinhas e macetes escritos",
     "Nao saem de contagem: alguem precisa ler as questoes. Fica para quando a "
     "leitura por IA entrar."],
    ["Assunto fino ligado",
     "Codigo pronto, desligado por escolha sua. Custa US$ 0,26 uma vez, mas "
     "classificaria provas de areas que nao sao a sua."],
], [4.4 * cm, 12.1 * cm], cor_primeira=AMBAR))

# ------------------------------------------------------ dia a dia -----------
a(p("6. Como usar no dia a dia", "h1"))

a(p("<b>Um comando so, e depois a tela:</b>"))
a(Paragraph("radar atualizar<br/>radar.bat web", E["codigo"]))

a(p("O primeiro roda a rotina inteira na ordem certa - coletar, ler as paginas "
    "novas, baixar edital de concurso aberto, ler o que ele exige, conferir "
    "retificacao e avisar no Telegram. Etapa que falha nao derruba as outras, "
    "e no fim ele diz quantos concursos estao com inscricao aberta."))

a(p("O segundo abre a tela em localhost:8000.", "nota"))

a(p("Comandos separados, quando precisar de um so", "h2"))
a(tabela([
    ["Comando", "O que faz"],
    ["radar coletar", "so busca concursos novos nas 3 fontes"],
    ["radar listar --abertas", "lista no terminal o que esta com inscricao aberta"],
    ["radar previsao", "onde vale ficar de olho, por municipio"],
    ["radar calendario", "gera o arquivo .ics dos prazos"],
    ["radar parecidas \"Guarda Municipal\"", "prova do acervo mais parecida com o cargo"],
    ["radar provas --completo", "baixa provas novas (demora)"],
    ["radar questoes", "separa os cadernos baixados em questoes"],
    ["radar retificacoes", "confere se algum edital em pe mudou"],
    ["radar assuntos", "SIMULA o custo da classificacao por IA (nao gasta)"],
], [6.3 * cm, 10.2 * cm]))

a(Spacer(1, 8))
a(p("Na tela", "h2"))
a(lista([
    "<b>Perto de mim</b> - o que interessa por distancia, que e seu filtro principal",
    "<b>Inscricoes abertas</b> - o que da para se inscrever agora",
    "<b>Noticias e andamento</b> - busca livre por 'PM', 'policia civil', etc.",
    "<b>Previsao de abertura</b> - municipios atrasados e na janela",
    "<b>Macetes</b> - o costume da banca, com graficos",
    "<b>Calendario</b> - leva os prazos para a agenda do celular",
    "<b>Simulado</b> - treinar com questoes reais",
]))

a(p("O mural da esquerda mostra seus favoritos em qualquer aba, e nenhum "
    "filtro os esconde - nem distancia, nem salario, nem prazo vencido.", "nota"))

# --------------------------------------------------- o que falta ------------
a(p("7. O que voce pode fazer agora (opcional)", "h1"))

a(tabela([
    ["Acao", "Por que", "Esforco"],
    ["Completar config/perfil.yml",
     "Faltam seu ano de nascimento e sua CNH. Com eles, edital que poe idade "
     "maxima passa a ser avaliado de verdade em vez de 'a confirmar'.",
     "2 minutos"],
    ["Usar o simulado",
     "Estao la 2.187 questoes reais com gabarito, e nenhuma rodada foi feita "
     "ainda. O acerto por materia so aparece depois da primeira.",
     "10 minutos"],
    ["Ligar a IA (opcional)",
     "COMO_LIGAR_A_IA.txt tem o passo a passo. Custa ~R$ 1,43 uma vez. Vale "
     "pouco hoje: classificaria provas de areas que nao sao a sua.",
     "15 minutos"],
    ["Rodar o workflow manualmente",
     "Para confirmar que a correcao de hoje resolveu, sem esperar ate amanha. "
     "Aba Actions do GitHub, botao 'Run workflow'.",
     "1 minuto"],
], [4.0 * cm, 9.4 * cm, 3.1 * cm]))

# ------------------------------------------------- limites ------------------
a(p("8. Limites conhecidos - leia antes de confiar", "h1"))

a(p("Estes nao sao defeitos a corrigir: sao limites dos dados, e estao aqui "
    "para voce nao concluir demais a partir do que a tela mostra.", "nota"))

a(lista([
    "<b>Nao ha prova de Guarda Municipal nem de Policia Penal no acervo.</b> "
    "Sao 134 cargos catalogados e nenhum e esse. O que serve para esses cargos "
    "sao as materias que caem em qualquer concurso - e elas valem 20 das 30 "
    "questoes de uma prova da IESES.",

    "<b>Salario so aparece quando vem no titulo do post.</b> 1.115 dos "
    "concursos nao trazem valor nenhum. O filtro de salario exclui esses, e a "
    "tela avisa quantos ficaram de fora.",

    "<b>Elegibilidade e por concurso, nao por cargo.</b> 'Elegivel' quer dizer "
    "que HA vaga de nivel superior naquele concurso - nao que voce sirva para "
    "todas as vagas dele.",

    "<b>O mesmo concurso pode aparecer duas vezes</b>, uma pelo agregador e "
    "outra pela banca. Sao 5 casos em 183 perto de casa. Nao junto "
    "automaticamente porque unir dois concursos diferentes seria pior que "
    "mostrar dois cartoes.",

    "<b>3 editais do acervo nao podem ser lidos</b> - foram digitalizados como "
    "imagem. A tela diz isso, em vez de fingir que o concurso nao exige nada.",

    "<b>A previsao de abertura so conhece o que foi coletado.</b> Municipio "
    "que contratou outra banca entre 2021 e 2025 aparece mais atrasado do que "
    "e, e a tela avisa isso.",

    "<b>O Querido Diario cobre so Florianopolis</b> entre os seus 35 "
    "municipios, e nao traz o ato de contratacao de banca.",
]))

a(Spacer(1, 10))
a(p("9. Como o projeto se protege", "h1"))

a(lista([
    "<b>679 testes automaticos</b>, e nenhum vai a internet - todos usam "
    "arquivo fixo. Rodam antes de cada coleta no GitHub Actions.",

    "<b>Nada e apagado.</b> Concurso irrelevante fica marcado, nao sumido - "
    "assim da para revisar e corrigir a regra.",

    "<b>Senhas so em variavel de ambiente</b> (.env na maquina, Secrets no "
    "GitHub). O log nunca imprime a URL da API do Telegram, porque ela carrega "
    "o token dentro.",

    "<b>robots.txt e respeitado</b>, com atraso entre requisicoes e "
    "User-Agent identificado. As duas excecoes sao decisao registrada, nao "
    "descuido.",

    "<b>A parte paga simula por padrao.</b> Sem '--valendo', nao gasta nada. "
    "O teto de gasto e conferido antes de cada chamada, com o custo real que a "
    "API informou.",

    "<b>Toda decisao guarda o motivo.</b> Distancia, elegibilidade, previsao e "
    "prova parecida vem sempre com a explicacao do porque - para voce poder "
    "discordar.",
]))

a(Spacer(1, 14))
a(HRFlowable(width="100%", thickness=0.6, color=BORDA, spaceAfter=8))
a(p("Documentos do projeto: <b>README.md</b> (como tudo funciona e o porque de "
    "cada decisao), <b>CLAUDE.md</b> (contexto permanente) e "
    "<b>COMO_LIGAR_A_IA.txt</b> (passo a passo da unica parte paga).", "nota"))

documento = SimpleDocTemplate(
    DESTINO, pagesize=A4,
    leftMargin=2 * cm, rightMargin=2 * cm,
    topMargin=1.8 * cm, bottomMargin=2 * cm,
    title="Radar de Concursos - relatorio do projeto",
    author="Radar de Concursos",
)
documento.build(historia, onFirstPage=rodape, onLaterPages=rodape)
print("gerado:", DESTINO)
