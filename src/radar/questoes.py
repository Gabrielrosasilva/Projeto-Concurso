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
from functools import cache
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
# Em alguns cadernos de 2023 e 2024 (Palhoca emergencial, Brusque educa) a
# mesma fonte sai em minusculas: "a. square texto".
MARCA_ERRADA = "(?:SQUARE|square)"
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

# O comeco de um texto-base que vale para varias questoes: o cabecalho
# sozinho na linha ("Caso 3", "Texto 2") ou a frase que o anuncia ("Para
# responder as questoes 49 a 51, considere..."). Ele vem entre a ultima
# alternativa de uma questao e o numero da seguinte, e nao e de nenhuma das
# duas (S7 de Sao Jose 2024).
PADRAO_TEXTO_BASE = re.compile(
    r"^[ \t]*(?:(?:Caso|Texto)[ \t]+\d{1,2}[ \t]*$"
    r"|Para responder [àa]s? quest[õo]es?\b)",
    re.MULTILINE | re.IGNORECASE,
)

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


# Guardada em memoria: o mesmo texto da sempre a mesma impressao, e uma pagina
# do painel tira a chave das ~5 mil questoes do complementar - refazer a conta
# custava ~1 s por abertura. O que fica guardado e o acervo, que cabe folgado.
@cache
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


def chave_da_questao(enunciado: str, alternativas: dict | None) -> str:
    """Hash da questao INTEIRA: o enunciado e as cinco alternativas.

    A impressao, so do enunciado, nao serve para dizer QUAL questao e: a
    FEPESE repete enunciados genericos ("De acordo com o Codigo Penal
    Brasileiro, e correto") em questoes de alternativas diferentes - em 2019
    foram 4 de Penal com o mesmo. E esta chave que a classificacao usa (Etapa
    3A). Ela continua achando a mesma questao reaproveitada em outro caderno,
    porque normaliza do mesmo jeito que a impressao.
    """
    partes = [enunciado or ""] + [
        f"{letra} {texto or ''}" for letra, texto in sorted((alternativas or {}).items())
    ]
    return impressao_de(" | ".join(partes))


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
    r"|\(rascunho\)"
    # O fim do caderno da FEPESE grudava na "e" da ultima questao (B.7): a
    # grade de respostas (os numeros de 1 em diante, com ou sem o titulo), o
    # rodape com o endereco da fundacao e a coluna em branco.
    r"|\b1\s+2\s+3\s+4\s+5\s+6\s+7\s+8\s+9\s+10\b"
    r"|(?:\.\s+)?Utilize\s+a\s+grade\s+ao\s+lado"
    r"|GRADE\s+DE\s+RESPOSTAS"
    # O titulo de bloco entre parenteses, como o de 2013: "Conhecimentos
    # Especificos (40 questoes)". O PADRAO_SECAO nao o le como secao.
    r"|(?-i:[A-ZÁÉÍÓÚÂÊÔÃÕÇ]\w*(?:\s+\w+){0,6})\s*\(\s*\d{1,3}\s+quest[oõ]es\s*\)"
    r"|FEPESE\s*•\s*Funda[çc][ãa]o\s+de\s+Estudos"
    r"|Campus\s+Universit[áa]rio\s*•\s*UFSC"
    r"|Coluna\s+em\s+Branco"
    r").*$",
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
    """Tira cabecalho e rodape de pagina, que se repetem no caderno inteiro.

    Menos a linha que continua a palavra quebrada por hifen na linha de cima.
    Em 2019, "De acordo com o Codigo Penal Brasileiro, e cor-" / "reto
    afirmar:" abre quatro questoes, a segunda metade se repetia e era apagada
    como cabecalho, e o enunciado acabava em "e cor-" (B.7). Cabecalho de
    pagina nunca continua palavra, e nunca comeca em minuscula.
    """
    repetidas = _linhas_repetidas(texto)
    mantidas: list[str] = []
    for linha in texto.splitlines():
        if any(padrao.match(linha) for padrao in MOBILIA_DE_PAGINA):
            continue
        enxuta = linha.strip()
        continua_palavra = (enxuta[:1].islower() and mantidas
                            and re.search(r"\w-$", mantidas[-1].rstrip()))
        if enxuta in repetidas and not continua_palavra:
            continue
        mantidas.append(linha)
    return "\n".join(mantidas)


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


def _na_ordem_do_caderno(secoes: list[tuple[int, str, int]],
                         texto: str) -> list[tuple[int, str, int]] | None:
    """As secoes na ordem do caderno, e nao na do texto extraido.

    O extrator le as duas colunas na ordem dele, e um titulo pode sair depois
    do da secao seguinte: no Socioeducativo de 2013 e de 2016, o de Direito
    Processual Penal (questoes 49 e 50) vinha depois do de Legislacao
    Estadual (51 a 60), e a conta pela ordem do texto trocava quatro questoes
    de materia em cada caderno (B.10). A pista e a primeira questao depois de
    cada titulo: ordenadas por ela, as secoes somam as faixas de novo.

    A pista nao e a fronteira - em Portugues o texto de apoio vem antes, e a
    primeira numerada pode ser a 3. Por isso ela so vale se cair dentro da
    faixa que a secao ganha; se alguma nao cair, devolve None e fica a ordem
    do texto, a de sempre.
    """
    pistas = []
    for indice, secao in enumerate(secoes):
        achado = PADRAO_QUESTAO.search(texto, secao[0])
        if not achado:
            return None
        pistas.append((int(achado.group(1)), indice))
    proximo = 1
    for numero, indice in sorted(pistas):
        if not proximo <= numero < proximo + secoes[indice][2]:
            return None
        proximo += secoes[indice][2]
    return [secoes[indice] for _, indice in sorted(pistas)]


def materias_por_numero(secoes: list[tuple[int, str, int]],
                        texto: str | None = None) -> dict[int, str]:
    """{numero da questao: materia}, montado pelas faixas que a banca declara.

    Cada cabecalho diz quantas questoes a secao tem ("Conhecimentos Gerais 10
    questoes"), e a numeracao e continua. Entao a primeira secao cobre 1..10, a
    segunda 11..20, e assim por diante.

    A conta e feita pelo NUMERO, e nao pela posicao no texto, justamente
    porque a ordem do texto e embaralhada pelas duas colunas do caderno - as
    questoes 21 e 22 aparecem antes das 16 a 20. Usar posicao colocava meia
    prova na materia errada.

    Com o `texto`, a ORDEM das secoes tambem sai do caderno, e nao do texto
    (`_na_ordem_do_caderno`).
    """
    mapa: dict[int, str] = {}
    proximo = 1
    ordem = (_na_ordem_do_caderno(secoes, texto) if texto else None) or secoes
    for _, nome, quantas in ordem:
        for numero in range(proximo, proximo + quantas):
            mapa[numero] = nome
        proximo += quantas
    return mapa


def _inicio_do_titulo(texto: str, achado: re.Match) -> int:
    """Onde comeca o titulo de secao achado: a linha dele, ou a de cima
    quando o titulo quebrou em duas (o criterio de `_juntar_com_a_linha_de_cima`)."""
    nome = re.split(r"\s{2,}|•", _limpar(achado.group(1)))[-1].strip()
    if _juntar_com_a_linha_de_cima(texto, achado.start(), nome) == nome:
        return achado.start()
    anterior = texto.rfind("\n", 0, achado.start())
    return texto.rfind("\n", 0, anterior) + 1


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
    rodada: list[re.Match], texto: str, fim: int, proxima: int | None = None
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
            if proxima is not None and achado.end() <= proxima <= fim:
                # O numero que a proxima questao ganhou (`_marcador_da_questao`):
                # a lista numerada de dentro desta alternativa nao a corta.
                limite = proxima
            else:
                seguinte = PADRAO_QUESTAO.search(texto, achado.end(), fim)
                if seguinte:
                    limite = seguinte.start()
            # Entre a ultima alternativa e a proxima questao pode estar o
            # titulo da secao seguinte ("Direitos Humanos 10 questoes"), as
            # vezes com o texto de apoio das questoes de baixo. Sem cortar
            # nele, os dois grudavam no fim da "e" (B.7).
            secao = PADRAO_SECAO.search(texto, achado.end(), limite)
            if secao:
                limite = _inicio_do_titulo(texto, secao)
            base = PADRAO_TEXTO_BASE.search(texto, achado.end(), limite)
            if base:
                limite = base.start()

        alternativas[letra] = cortar_mobilia(_limpar(texto[achado.end():limite]))
        if _e_a_marcada(achado.group(2)):
            resposta = letra

    return alternativas, resposta


def _marcador_da_questao(regiao: str, anterior: int) -> re.Match | None:
    """O "N." que numera a questao: o primeiro da regiao, em regra.

    A regiao comeca logo depois do "e." da questao anterior, no texto da
    alternativa dela - e esse texto pode ser uma lista numerada ("1. silepse •
    2. comparacao •" / "3. eufemismo • 4. catacrese"). Ai o primeiro marcador e
    da lista: a questao 20 de Florianopolis 2023 virava a "1", batia com a 1
    de verdade e sumia (B.9, 26 cadernos). Marcador logo no comeco da regiao
    e sempre o texto da alternativa; os "N." da lista seguem em sequencia, e o
    numero da questao e o primeiro marcador de comeco de linha que vem depois
    dela. Fora disso, o primeiro - o caso de sempre, inclusive a ordem
    embaralhada pelas duas colunas.
    """
    achados = list(PADRAO_QUESTAO.finditer(regiao))
    if not achados:
        return None
    primeiro = achados[0]
    if primeiro.start() != 0 or int(primeiro.group(1)) > anterior:
        # Lista que comeca em "1." e segue em sequencia ANTES do numero e o
        # texto-base de um grupo de questoes ("Caso 3": "1. Lancamento...
        # 8. Arrecadacao...", e so entao "49."). A regiao tem uma questao so,
        # e ela e o primeiro marcador que quebra a sequencia. A lista de dentro
        # do enunciado vem depois do numero, e nao comeca em 1 colada nele.
        corrida = 1
        while (corrida < len(achados)
               and int(achados[corrida].group(1)) == int(achados[corrida - 1].group(1)) + 1):
            corrida += 1
        if int(primeiro.group(1)) == 1 and 2 <= corrida < len(achados) and anterior:
            return achados[corrida]
        return primeiro
    esperado, fim_da_lista = int(primeiro.group(1)), 0
    for item in re.finditer(r"(?<![\w.])(\d{1,3})\.(?=[ \t\xa0])", regiao):
        if int(item.group(1)) != esperado:
            break
        esperado += 1
        fim_da_lista = item.end()
    return next((a for a in achados[1:] if a.start() >= fim_da_lista), primeiro)


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
    materias = materias_por_numero(secoes, texto)
    rodadas = _blocos_de_alternativas(texto)

    # Primeiro o numero de cada questao, e so depois o texto: a ultima
    # alternativa de uma termina no marcador da seguinte.
    marcadores: list[int | None] = []      # onde comeca o "N.", no texto
    numeros: list[int | None] = []
    fim_anterior = anterior = 0
    for rodada in rodadas:
        regiao = texto[fim_anterior:rodada[0].start()]
        achado = _marcador_da_questao(regiao, anterior)
        marcadores.append(fim_anterior + achado.start() if achado else None)
        numeros.append(int(achado.group(1)) if achado else None)
        # O ponteiro avanca ate a ULTIMA alternativa desta rodada, e nao ate o
        # inicio da proxima: e entre um ponto e outro que mora o numero e o
        # enunciado da questao seguinte.
        fim_anterior = rodada[-1].end()
        if achado:
            anterior = numeros[-1]

    questoes: list[Questao] = []
    for indice, rodada in enumerate(rodadas):
        if marcadores[indice] is None:
            continue
        inicio_alternativas = rodada[0].start()
        fim_rodada = (rodadas[indice + 1][0].start()
                      if indice + 1 < len(rodadas) else len(texto))
        proxima = marcadores[indice + 1] if indice + 1 < len(marcadores) else None

        numero = numeros[indice]
        enunciado = _limpar(marcar_lacunas(
            # Tres digitos: com dois, o "100." ficava dentro do enunciado (B.7).
            re.sub(r"^[ \t]*\d{1,3}\.[ \t]*", "",
                   texto[marcadores[indice]:inicio_alternativas])
        ))
        alternativas, resposta = _ler_alternativas(rodada, texto, fim_rodada, proxima)

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


# --- o texto-base das questoes de interpretacao -----------------------------

# "Texto 2" sozinho na linha: o cabecalho do texto de apoio da prova.
PADRAO_CABECALHO_DO_TEXTO = re.compile(r"^[ \t]*Texto[ \t]+(\d{1,2})[ \t]*$",
                                       re.MULTILINE | re.IGNORECASE)
# "texto 1", "textos 2 e 3", "textos 1, 2 e 3" no enunciado.
PADRAO_TEXTO_CITADO = re.compile(r"\btextos?\s+(\d{1,2}(?:\s*(?:,|e)\s*\d{1,2})*)",
                                 re.IGNORECASE)
# Rotulo do texto da prova que nao numera os textos (2013: um texto so).
TEXTO_UNICO = "unico"
# Menos linhas que isso entre o titulo da secao e a questao 1 nao e texto:
# e sobra de cabecalho.
LINHAS_MINIMAS_DO_TEXTO = 5


def extrair_por_colunas(caminho: Path) -> str:
    """O PDF lido coluna por coluna: a esquerda inteira, depois a direita.

    O `extrair_texto` segue a ordem em que o PDF guardou os trechos, e no
    caderno de 2019 isso pos o fim do "Texto 2" (a fonte, a ultima resposta da
    entrevista) antes do cabecalho dele, no meio das alternativas da questao 6.
    Para as questoes isso nao importa; para o texto-base, que precisa sair
    inteiro e na ordem, a posicao de cada trecho na pagina resolve.
    """
    from pypdf import PdfReader

    for ruidoso in ("pypdf", "pypdf._cmap", "pypdf._reader", "pypdf.generic"):
        logging.getLogger(ruidoso).setLevel(logging.ERROR)

    paginas = []
    for pagina in PdfReader(str(caminho)).pages:
        meio = float(pagina.mediabox.width) / 2
        trechos: list[tuple[int, int, float, str]] = []

        def guardar(texto, cm, tm, _fonte, _tamanho):
            if texto.strip():
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                trechos.append((0 if x < meio else 1, -round(y), x, texto))

        pagina.extract_text(visitor_text=guardar)
        linhas: list[str] = []
        anterior = None
        for coluna, altura, _x, texto in sorted(trechos):
            if (coluna, altura) != anterior:
                linhas.append("")
                anterior = (coluna, altura)
            linhas[-1] += texto
        paginas.append("\n".join(linha.rstrip() for linha in linhas))
    return _tirar_simbolo_sem_desenho("\n".join(paginas))


def _desfazer_quebras(linhas: list[str]) -> str:
    """As linhas da coluna viram paragrafos: a palavra partida por hifen volta
    inteira, e o paragrafo termina na linha curta que fecha frase."""
    largura = max((len(linha) for linha in linhas), default=0)
    texto = ""
    for linha in linhas:
        enxuta = linha.strip()
        if not enxuta:
            continue
        if not texto:
            texto = enxuta
        elif texto.endswith("\n"):
            texto += enxuta
        elif re.search(r"\w-$", texto) and enxuta[:1].islower():
            texto = texto[:-1] + enxuta
        else:
            texto += " " + enxuta
        if len(enxuta) < 0.8 * largura and re.search(r"[.!?:”\"\]]$", enxuta):
            texto += "\n"
    return texto.strip()


def textos_base(texto: str) -> dict[str, str]:
    """{rotulo: texto} dos textos de apoio do caderno ja lido por colunas.

    O texto comeca no cabecalho "Texto N" e vai ate a primeira questao depois
    dele. A prova que nao numera os textos (2013) tem um so, entre o titulo da
    secao de Lingua Portuguesa e a questao 1: ele vira o `TEXTO_UNICO`.
    """
    limpo = limpar_mobilia(texto)
    textos: dict[str, str] = {}
    for cabecalho in PADRAO_CABECALHO_DO_TEXTO.finditer(limpo):
        fim = PADRAO_QUESTAO.search(limpo, cabecalho.end())
        corpo = limpo[cabecalho.end(): fim.start() if fim else len(limpo)]
        textos.setdefault(cabecalho.group(1), _desfazer_quebras(corpo.splitlines()))
    if textos:
        return textos

    for secao in PADRAO_SECAO.finditer(limpo):
        if "portugu" not in _sem_acento(secao.group(1)).lower():
            continue
        fim = PADRAO_QUESTAO.search(limpo, secao.end())
        linhas = [l for l in limpo[secao.end(): fim.start() if fim else len(limpo)]
                  .splitlines() if l.strip()]
        if len(linhas) >= LINHAS_MINIMAS_DO_TEXTO:
            textos[TEXTO_UNICO] = _desfazer_quebras(linhas)
        break
    return textos


def texto_da_questao(enunciado: str, textos: dict[str, str]) -> str | None:
    """O texto-base que a questao cita, com o rotulo; None quando ela nao cita.

    "considerando o texto 1" leva o Texto 1; "de acordo com os textos 2 e 3",
    os dois. Na prova de texto unico, basta o enunciado falar em "texto".
    Quem chama garante que a questao e da secao de Portugues: em Direito,
    "o texto da lei" nao e texto de apoio.
    """
    citados: list[str] = []
    for achado in PADRAO_TEXTO_CITADO.finditer(enunciado or ""):
        for numero in re.findall(r"\d{1,2}", achado.group(1)):
            if numero in textos and numero not in citados:
                citados.append(numero)
    if citados:
        return "\n\n".join(f"Texto {n}\n{textos[n]}" for n in citados)
    if TEXTO_UNICO in textos and re.search(r"\btexto\b", enunciado or "", re.IGNORECASE):
        return textos[TEXTO_UNICO]
    return None


def ler_prova(caminho: Path) -> list[Questao]:
    """Abre o PDF e devolve as questoes. Erro de leitura devolve lista vazia."""
    try:
        return dividir_em_questoes(extrair_texto(caminho))
    except Exception as erro:  # noqa: BLE001 - PDF ruim e rotina, nao acidente
        log.warning("nao consegui ler %s (%s)", caminho.name, type(erro).__name__)
        return []
