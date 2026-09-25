"""Separa o caderno de prova em questoes.

O caderno da FEPESE tem uma estrutura regular, e e isso que torna a coisa
possivel sem adivinhacao:

    Lingua Portuguesa 10 questoes      <- a banca diz a materia e quantas sao
    1. Enunciado da questao...
    a. SQUARE alternativa errada
    b. Check-square alternativa CERTA  <- o gabarito vem embutido no texto
    ...

Dois achados que economizaram muito trabalho:

  1. **a materia vem da propria banca**, em cabecalho de secao. Nao precisa
     adivinhar se a questao e de portugues ou de conhecimentos especificos;
  2. **a alternativa correta esta marcada no texto**. O caderno usa um simbolo
     de caixa marcada que o extrator le como "Check-square", contra "SQUARE"
     nas demais. Ou seja, prova e gabarito num arquivo so.

Isto e extracao, nao interpretacao: nada aqui tenta entender o assunto da
questao. Classificar "isto e Direito Penal, aquilo e Nocoes de Primeiros
Socorros" e o passo seguinte.
"""
import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# Como o extrator de PDF representa a caixa marcada e a vazia.
#
# Sao DOIS formatos, porque o caderno da FEPESE mudou de desenho. Ate 2016 a
# caixa vinha escrita com parenteses - "( X )" na certa, "( )" nas outras. De
# 2019 em diante virou simbolo de uma fonte propria, que o extrator devolve
# como "Check-square" e "SQUARE".
#
# Os dois precisam funcionar: as duas provas de Agente Penitenciario de SC que
# existem estao uma em cada formato, a de 2013 na escrita e a de 2019 na de
# simbolo. Enquanto so o formato novo era lido, a de 2013 dava zero questao.
MARCA_CERTA = "Check-square"
MARCA_ERRADA = "SQUARE"
CAIXA_ESCRITA = r"\([ \t]*[Xx]?[ \t]*\)"

# "Lingua Portuguesa 10 questoes". O nome nao pode ter digito: isso descarta
# a linha da capa ("8 as 11h 40 questoes"), que nao e secao de materia.
PADRAO_SECAO = re.compile(
    r"^[ \t]*([^\d\n]{4,60}?)[ \t]+(\d{1,2})[ \t]+quest[oõ]es[ \t]*$",
    re.MULTILINE | re.IGNORECASE,
)

# "12. Qual o nome da capital catarinense?"
#
# Tres digitos, e nao dois: a prova de Agente Penitenciario de 2019 tem 100
# questoes, e com o teto em dois digitos a de numero 100 era lida como
# alternativa solta e jogada fora. O caderno so ficou com 99.
PADRAO_QUESTAO = re.compile(r"^[ \t]*(\d{1,3})\.[ \t]+(?=\S)", re.MULTILINE)

# "a. SQUARE texto", "b. Check-square texto" ou, no caderno antigo,
# "a. ( ) texto" e "b. ( X ) texto".
PADRAO_ALTERNATIVA = re.compile(
    rf"^[ \t]*([a-e])\.[ \t]+({MARCA_CERTA}|{MARCA_ERRADA}|{CAIXA_ESCRITA})[ \t]*",
    re.MULTILINE,
)


def _e_a_marcada(marca: str) -> bool:
    """Esta e a alternativa que o caderno aponta como certa?

    O "( V )" e o "( F )" do enunciado de verdadeiro/falso nao chegam aqui: o
    padrao exige a letra e o ponto na frente ("a. "), e a lista de V/F vem
    solta no meio do texto.
    """
    return marca == MARCA_CERTA or marca.strip("() \t").lower() == "x"

LETRAS = ("a", "b", "c", "d", "e")

# Erro de digitacao que aparece nos proprios cadernos. Visto em prova real:
# "Conhecimento Gerais", no singular.
NOMES_CORRIGIDOS = {
    "conhecimento gerais": "Conhecimentos Gerais",
    "conhecimentos gerai": "Conhecimentos Gerais",
}


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def impressao_de(enunciado: str) -> str:
    """Hash do enunciado, para achar questao repetida entre provas.

    Banca reaproveita questao, e saber disso vale ouro: e o padrao mais forte
    que existe. Compara sem acento, sem caixa e sem espaco duplo, porque o
    mesmo enunciado sai formatado de um jeito em cada caderno.

    E funcao solta, e nao so um metodo, porque a questao escrita pela IA
    precisa da MESMA impressao: e por ela que se ve que a variacao saiu igual
    a uma pergunta que ja existe.
    """
    texto = unicodedata.normalize("NFKD", enunciado or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9 ]", " ", texto.lower())
    texto = re.sub(r"\s+", " ", texto).strip()
    return hashlib.sha256(texto.encode()).hexdigest()[:32]


@dataclass
class Questao:
    numero: int
    enunciado: str
    alternativas: dict[str, str] = field(default_factory=dict)
    resposta: str | None = None
    materia: str | None = None
    #: A banca anulou esta questao depois dos recursos. Quem liga e o
    #: `radar.gabarito`, lendo o gabarito definitivo - o caderno nunca sabe.
    anulada: bool = False

    @property
    def impressao(self) -> str:
        return impressao_de(self.enunciado)


def extrair_texto(caminho: Path, layout: bool = False) -> str:
    """Texto do PDF inteiro, pagina por pagina.

    `layout` troca o modo do pypdf. O modo normal e o que o caderno de prova
    precisa: ele junta as colunas na ordem de leitura. O modo `layout`
    preserva a posicao na pagina, e com isso resolve o defeito que atrapalha o
    ANEXO de programas do edital - texto justificado voltava com espaco no
    meio da palavra ("cidad ania", "envol vendo", "desp orto"), e assunto de
    edital com palavra partida no meio nao serve para nada.
    """
    from pypdf import PdfReader

    # O pypdf reclama de fonte e de cabecalho fora do padrao em quase todo
    # caderno, e nao muda nada no resultado - a extracao funciona. Sao dezenas
    # de linhas por prova poluindo a saida do comando.
    for ruidoso in ("pypdf", "pypdf._cmap", "pypdf._reader", "pypdf.generic"):
        logging.getLogger(ruidoso).setLevel(logging.ERROR)

    modo = {"extraction_mode": "layout"} if layout else {}
    leitor = PdfReader(str(caminho))
    return _tirar_simbolo_sem_desenho(
        "\n".join(pagina.extract_text(**modo) or "" for pagina in leitor.pages)
    )


def _tirar_simbolo_sem_desenho(texto: str) -> str:
    """Troca por espaco o caractere que nenhuma fonte sabe desenhar.

    O caderno usa simbolos de uma fonte propria, e o extrator devolve alguns
    deles como caractere de controle (0x84, 178 vezes no acervo) ou da area de
    uso privado. Na tela isso vira quadradinho no meio do enunciado. Vira
    espaco, e nao nada, para nao colar a palavra de antes na de depois.
    """
    marcado = "".join(
        caractere
        if caractere in "\n\t"
        or unicodedata.category(caractere) not in ("Cc", "Cf", "Co")
        else "\x00"
        for caractere in texto
    )
    # O simbolo e o espaco ao redor dele viram UM espaco so. Trocar por espaco
    # sem juntar criaria uma corrida de tres espacos onde o caderno tinha
    # " simbolo ", e marcar_lacunas leria ali uma lacuna que nao existe.
    return re.sub(r"[ \t]*\x00[ \t]*", " ", marcado)


# A lacuna do "complete as frases" nao vem escrita no caderno: a FEPESE
# desenha o tracinho como grafico, e o extrator devolve so espaco em branco.
# Sem marcar, "A medida que chegava a hora" vira "medida que chegava hora" e a
# questao perde o sentido. Conferido em 8 cadernos: 68 corridas de 3 espacos
# ou mais, e a unica que nao era lacuna foi "CADERNO   ", que a limpeza de
# mobilia ja tira antes daqui.
LACUNA = "____"


def marcar_lacunas(texto: str) -> str:
    """Troca por ____ a corrida de 3 espacos ou mais.

    Roda ANTES de juntar as linhas: a lacuna aparece tanto no meio da linha
    ("chegava    hora") quanto no comeco ("   medalha") e no fim ("contar    "
    com a frase seguindo na linha de baixo), e juntar as linhas primeiro
    apagaria as duas ultimas.
    """
    texto = re.sub(r"[ \t]{3,}", f" {LACUNA} ", texto)
    # Lacuna no fim de uma linha e comeco da seguinte e a MESMA lacuna.
    return re.sub(rf"(?:{LACUNA}\s*){{2,}}", f"{LACUNA} ", texto)


def _limpar(texto: str) -> str:
    """Junta linha quebrada por hifen e normaliza o espaco em branco.

    O caderno quebra palavra no fim da linha ("muni-\\ncipio"). Sem juntar, o
    enunciado fica com palavra partida e o hash de questao repetida nunca bate.
    """
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    texto = re.sub(r"[ \t]*\n[ \t]*", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


# Pedacos que sozinhos nao sao nome de materia: sao continuacao da linha de
# cima. Acontece quando o cabecalho quebra em duas linhas no caderno.
INICIOS_DE_CONTINUACAO = ("gerais ", "sobre ", "especificos ", "e ", "de ", "da ")

# Linha que e cabecalho de pagina, e nao parte do nome da materia.
CABECALHO_DE_PAGINA = re.compile(r"[•·]|p[aá]gina|edital|processo|concurso", re.I)


def _juntar_com_a_linha_de_cima(texto: str, inicio: int, nome: str) -> str:
    """Recupera o nome que ficou partido entre duas linhas.

    O caderno quebra "Conhecimentos Gerais sobre Educacao 10 questoes" em duas
    linhas, e a primeira ("Conhecimentos") fica de fora do padrao. Sem juntar,
    a materia vira "Gerais sobre Educacao", que nao e nome de nada.
    """
    if not _sem_acento(nome).lower().startswith(INICIOS_DE_CONTINUACAO):
        return nome

    anterior = texto.rfind("\n", 0, inicio)
    if anterior <= 0:
        return nome

    acima = texto[texto.rfind("\n", 0, anterior) + 1:anterior].strip()
    if (
        acima
        and len(acima) <= 40
        and not any(c.isdigit() for c in acima)
        and not CABECALHO_DE_PAGINA.search(acima)
    ):
        return f"{acima} {nome}"
    return nome


# Linhas que o caderno repete em toda pagina e nao fazem parte de questao
# nenhuma. Sem tirar, elas grudam no fim da ultima alternativa: a "e" saia
# como "Sao corretas as afirmativas 1, 2 e 3. Pagina 7 Municipio de Brusque
# - Concurso Publico - Edital 001/2024".
MOBILIA_DE_PAGINA = (
    re.compile(r"^\s*P[aá]gina\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*P[aá]gina\s+em\s+Branco.*$", re.IGNORECASE),
    re.compile(r"^.{0,120}[•·].{0,60}Edital\s*n?[ºo°]?\s*[\d/]+.*$", re.IGNORECASE),
    re.compile(r"^\s*\(rascunho\)\s*$", re.IGNORECASE),
)


# A mesma mobilia, mas para cortar no MEIO de uma linha. O pypdf nem sempre
# quebra a linha antes do rodape, e ai ele vem colado no fim da ultima
# alternativa: "Sao corretas as afirmativas 1, 2 e 3. Pagina 7 Municipio de..."
MOBILIA_NO_MEIO = re.compile(
    r"\s*(?:P[aá]gina\s+\d+"
    r"|P[aá]gina\s+em\s+Branco"
    r"|\(rascunho\)).*$",
    re.IGNORECASE | re.DOTALL,
)


# Sobra de rodape cujo numero ja foi embora na limpeza por linha. Comparado
# com endswith, e nao por regex, para nao depender de como o acento foi
# gravado no arquivo - isso ja custou tempo aqui.
SOBRAS_DE_RODAPE = ("P\u00e1gina", "Pagina", "(rascunho)")


def cortar_mobilia(texto: str) -> str:
    """Corta o texto no ponto onde comeca o rodape da pagina."""
    limpo = MOBILIA_NO_MEIO.sub("", texto).strip()

    mudou = True
    while mudou:
        mudou = False
        for sobra in SOBRAS_DE_RODAPE:
            if limpo.endswith(sobra):
                limpo = limpo[: -len(sobra)].strip()
                mudou = True
    return limpo


def _linhas_repetidas(texto: str, minimo: int = 3) -> set[str]:
    """Linhas curtas que se repetem no caderno inteiro.

    Em vez de adivinhar mais um padrao de cabecalho, esta funcao olha o fato:
    o que aparece igual em toda pagina e mobilia, seja "AM2 Educador Social"
    ou o nome do municipio. Questao nao se repete assim.
    """
    contagem: dict[str, int] = {}
    for linha in texto.splitlines():
        enxuta = linha.strip()
        if 3 <= len(enxuta) <= 80:
            contagem[enxuta] = contagem.get(enxuta, 0) + 1

    return {
        linha for linha, vezes in contagem.items()
        if vezes >= minimo
        # Nao pode tirar alternativa nem enunciado, por mais que se repitam.
        #
        # Quem decide isso e o proprio PADRAO_ALTERNATIVA, e nao o nome do
        # simbolo: ja foi uma busca por "SQUARE" e "Check-square", que so
        # existem no caderno novo. No caderno de 2013, cuja alternativa e
        # "a. ( ) Sao corretas apenas as afirmativas 1 e 3.", a frase se
        # repete em varias questoes e era apagada como se fosse rodape - a
        # questao chegava ao banco com tres alternativas e sem o gabarito.
        and not PADRAO_ALTERNATIVA.match(linha)
        and not PADRAO_QUESTAO.match(linha)
    }


def limpar_mobilia(texto: str) -> str:
    """Tira cabecalho e rodape de pagina, que se repetem no caderno inteiro."""
    repetidas = _linhas_repetidas(texto)
    return "\n".join(
        linha for linha in texto.splitlines()
        if linha.strip() not in repetidas
        and not any(padrao.match(linha) for padrao in MOBILIA_DE_PAGINA)
    )


def achar_secoes(texto: str) -> list[tuple[int, str, int]]:
    """[(posicao, materia, quantas questoes)], na ordem em que aparecem."""
    secoes = []
    for achado in PADRAO_SECAO.finditer(texto):
        nome = _limpar(achado.group(1))
        # sobra do cabecalho da pagina antes do nome da secao
        nome = re.split(r"\s{2,}|•", nome)[-1].strip()
        nome = _juntar_com_a_linha_de_cima(texto, achado.start(), nome)
        nome = NOMES_CORRIGIDOS.get(_sem_acento(nome).lower(), nome)
        if len(nome) >= 4:
            secoes.append((achado.start(), nome, int(achado.group(2))))
    return secoes


def materias_por_numero(secoes: list[tuple[int, str, int]]) -> dict[int, str]:
    """{numero da questao: materia}, montado pelas faixas que a banca declara.

    Cada cabecalho diz quantas questoes a secao tem ("Conhecimentos Gerais 10
    questoes"), e a numeracao e continua. Entao a primeira secao cobre 1..10, a
    segunda 11..20, e assim por diante.

    A conta e feita pelo NUMERO, e nao pela posicao no texto, justamente
    porque a ordem do texto e embaralhada pelas duas colunas do caderno - as
    questoes 21 e 22 aparecem antes das 16 a 20. Usar posicao colocava meia
    prova na materia errada.
    """
    mapa: dict[int, str] = {}
    proximo = 1
    for _, nome, quantas in secoes:
        for numero in range(proximo, proximo + quantas):
            mapa[numero] = nome
        proximo += quantas
    return mapa


def _blocos_de_alternativas(texto: str) -> list[list[re.Match]]:
    """Agrupa as alternativas em rodadas de a ate e.

    Uma rodada nova comeca quando a letra volta para tras ou reinicia em "a".
    E isso que delimita uma questao: toda questao objetiva termina num conjunto
    de alternativas, e o conjunto seguinte ja e de outra questao.
    """
    rodadas: list[list[re.Match]] = []
    atual: list[re.Match] = []

    for achado in PADRAO_ALTERNATIVA.finditer(texto):
        letra = achado.group(1)
        if atual and letra <= atual[-1].group(1):
            rodadas.append(atual)
            atual = []
        atual.append(achado)

    if atual:
        rodadas.append(atual)
    return [r for r in rodadas if len(r) >= 2]


def _ler_alternativas(
    rodada: list[re.Match], texto: str, fim: int
) -> tuple[dict[str, str], str | None]:
    """O texto de cada alternativa da rodada.

    A ultima merece cuidado: entre ela e a rodada seguinte esta o numero e o
    enunciado da proxima questao. Sem cortar no numero, a alternativa "e" da
    questao 1 saia carregando junto "2. Assinale a alternativa que...".
    """
    alternativas: dict[str, str] = {}
    resposta = None

    for indice, achado in enumerate(rodada):
        letra = achado.group(1)

        if indice + 1 < len(rodada):
            limite = rodada[indice + 1].start()
        else:
            limite = fim
            proxima = PADRAO_QUESTAO.search(texto, achado.end(), fim)
            if proxima:
                limite = proxima.start()

        alternativas[letra] = cortar_mobilia(_limpar(texto[achado.end():limite]))
        if _e_a_marcada(achado.group(2)):
            resposta = letra

    return alternativas, resposta


def dividir_em_questoes(texto: str) -> list[Questao]:
    """As questoes do caderno, com materia, alternativas e gabarito.

    A leitura parte das ALTERNATIVAS, e nao dos numeros. Duas razoes, as duas
    vindas de prova de verdade:

      1. a ordem do texto nao e a ordem das questoes - o caderno e impresso em
         duas colunas, e o extrator leu 1..15, depois 21, 22, e so entao 16..20;
      2. o enunciado pode ter lista numerada dentro ("1. ... 2. ... 3."), e
         partir dos numeros quebrava a questao no meio, perdendo as
         alternativas dela. Foi o que aconteceu com as questoes 5 e 9.

    Partindo das alternativas, cada rodada de a ate e fecha uma questao, e o
    numero e o PRIMEIRO marcador depois da rodada anterior - a lista numerada
    de dentro do enunciado vem depois dele, entao nao atrapalha.
    """
    texto = limpar_mobilia(texto)
    secoes = achar_secoes(texto)
    materias = materias_por_numero(secoes)
    rodadas = _blocos_de_alternativas(texto)

    questoes: list[Questao] = []
    fim_anterior = 0

    for indice, rodada in enumerate(rodadas):
        inicio_alternativas = rodada[0].start()
        fim_rodada = (rodadas[indice + 1][0].start()
                      if indice + 1 < len(rodadas) else len(texto))

        regiao = texto[fim_anterior:inicio_alternativas]
        marcador = PADRAO_QUESTAO.search(regiao)
        # O ponteiro avanca ate a ULTIMA alternativa desta rodada, e nao ate o
        # inicio da proxima: e entre um ponto e outro que mora o numero e o
        # enunciado da questao seguinte.
        fim_anterior = rodada[-1].end()

        if not marcador:
            continue

        numero = int(marcador.group(1))
        enunciado = _limpar(marcar_lacunas(
            re.sub(r"^[ \t]*\d{1,2}\.[ \t]*", "", regiao[marcador.start():])
        ))
        alternativas, resposta = _ler_alternativas(rodada, texto, fim_rodada)

        questoes.append(Questao(
            numero=numero,
            enunciado=enunciado,
            alternativas=alternativas,
            resposta=resposta,
            materia=materias.get(numero),
        ))

    # Numero repetido fica com o bloco de enunciado mais completo.
    melhores: dict[int, Questao] = {}
    for questao in questoes:
        anterior = melhores.get(questao.numero)
        if anterior is None or len(questao.enunciado) > len(anterior.enunciado):
            melhores[questao.numero] = questao

    return [melhores[numero] for numero in sorted(melhores)]


def ler_prova(caminho: Path) -> list[Questao]:
    """Abre o PDF e devolve as questoes. Erro de leitura devolve lista vazia."""
    try:
        return dividir_em_questoes(extrair_texto(caminho))
    except Exception as erro:  # noqa: BLE001 - PDF ruim e rotina, nao acidente
        log.warning("nao consegui ler %s (%s)", caminho.name, type(erro).__name__)
        return []
