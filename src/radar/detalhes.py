"""Le a pagina do post e tira o que o titulo nao conta.

O RSS entrega titulo, data e link. Tres coisas que ficam de fora e mudam tudo:

  1. **ate quando da para se inscrever** - e o unico prazo que doi perder, e
     e o que permite responder "o que esta aberto AGORA", em vez de so "o que
     foi publicado hoje";
  2. **a banca** - o titulo quase nunca diz, e e ela que define o padrao de
     prova que vale a pena estudar;
  3. **onde e a lotacao** - um concurso estadual como o da SEFAZ SC nao tem
     "Prefeitura de X" no titulo, entao o classificador nao acha municipio
     nenhum e marca `indefinida`. O corpo do texto diz "lotacao em
     Florianopolis", e isso resolve.

Buscar pagina custa uma requisicao cada, entao isto NAO roda para tudo: so
para o que ja interessa. Ver `servico.detalhar_pendentes`.

Regra da casa aqui tambem vale: na duvida, deixa nulo. Data de inscricao
errada e pior que data faltando - uma some do radar, a outra faz voce achar
que tem prazo quando nao tem.
"""
import html as html_lib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from radar.util import fuso_local

log = logging.getLogger(__name__)

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}

# "16 de outubro de 2026" e tambem "16 de outubro" (sem ano)
DATA_POR_EXTENSO = re.compile(
    r"(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")(?:\s+de\s+(\d{4}))?",
    re.IGNORECASE,
)
DATA_NUMERICA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")

# "de 14 a 25 de setembro de 2026": o primeiro dia nao repete mes nem ano.
# Sem tratar este caso, so a data final e encontrada, o trecho fica com uma
# data so e acaba descartado.
INTERVALO_NO_MESMO_MES = re.compile(
    r"(\d{1,2})\s+a\s+(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")"
    r"(?:\s+de\s+(\d{4}))?",
    re.IGNORECASE,
)

# Bancas que aparecem nos concursos que me interessam. FEPESE primeiro: e a
# que mais faz concurso em Santa Catarina.
BANCAS = {
    "FEPESE": ("fepese", "fundacao de estudos e pesquisas socioeconomicos"),
    "FCC": ("fundacao carlos chagas", "concursosfcc", " fcc "),
    "Cebraspe": ("cebraspe", "cespe"),
    "FGV": ("fundacao getulio vargas", " fgv "),
    "IBFC": ("ibfc",),
    "Instituto AOCP": ("instituto aocp", " aocp "),
    "FUNDATEC": ("fundatec",),
    "Consulplan": ("consulplan",),
    "IESES": ("ieses",),
    "ACAFE": ("acafe",),
    "FURB": ("furb",),
    "Instituto o Barriga Verde": ("barriga verde", "iobv"),
    "Instituto Aptus": ("instituto aptus",),
    "Vunesp": ("vunesp",),
    "IDECAN": ("idecan",),
    "Quadrix": ("quadrix",),
    "Instituto Access": ("instituto access",),
    "AMEOSC": ("ameosc",),
}


@dataclass
class Detalhes:
    inscricoes_de: datetime | None = None
    inscricoes_ate: datetime | None = None
    banca: str | None = None
    municipio: str | None = None
    hotsite: str | None = None


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def texto_da_pagina(html: str) -> str:
    """HTML vira texto corrido, em uma linha, sem acento e em minusculas."""
    sopa = BeautifulSoup(html, "lxml")
    for lixo in sopa(["script", "style", "nav", "footer", "header", "form"]):
        lixo.decompose()
    return re.sub(r"\s+", " ", _sem_acento(sopa.get_text(" ")).lower())


def _montar(dia: int, mes: int, ano: int) -> datetime | None:
    """Data do texto vira datetime no fuso DAQUI, nao em UTC.

    Montar em UTC parece inofensivo e nao e: "05 de outubro" viraria
    05/10 00:00 UTC, que no horario de Brasilia e 04/10 21:00 - a tela
    mostraria o prazo um dia mais cedo do que o edital diz.
    """
    try:
        return datetime(ano, mes, dia, tzinfo=fuso_local())
    except ValueError:                 # 31 de fevereiro e coisas do genero
        return None


def _fim_do_dia(quando: datetime | None) -> datetime | None:
    """O ultimo instante do dia.

    Inscricao que vai "ate 05 de outubro" fica aberta o dia 05 inteiro. Sem
    isto, o prazo venceria a 00:00 e o radar esconderia, no proprio dia do
    encerramento, um concurso em que ainda da para se inscrever.
    """
    if quando is None:
        return None
    return quando.replace(hour=23, minute=59, second=59, microsecond=0)


def achar_datas(trecho: str, ano_padrao: int) -> list[tuple[int, datetime]]:
    """Todas as datas do trecho, com a posicao onde apareceram.

    Data sem ano ("16 de setembro") herda `ano_padrao`, que e o ano em que o
    post foi publicado. E o palpite certo em quase todo caso, porque o post
    fala de inscricao que abre logo depois dele.
    """
    achadas: list[tuple[int, datetime]] = []

    for m in INTERVALO_NO_MESMO_MES.finditer(trecho):
        mes, ano = MESES[m.group(3).lower()], m.group(4)
        ano = int(ano) if ano else ano_padrao
        for posicao, dia in ((m.start(), int(m.group(1))), (m.start() + 1, int(m.group(2)))):
            data = _montar(dia, mes, ano)
            if data:
                achadas.append((posicao, data))

    for m in DATA_POR_EXTENSO.finditer(trecho):
        dia, mes, ano = int(m.group(1)), MESES[m.group(2).lower()], m.group(3)
        data = _montar(dia, mes, int(ano) if ano else ano_padrao)
        if data:
            achadas.append((m.start(), data))

    for m in DATA_NUMERICA.finditer(trecho):
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if ano < 100:                  # "26" quer dizer 2026
            ano += 2000
        data = _montar(dia, mes, ano)
        if data:
            achadas.append((m.start(), data))

    return sorted(achadas)


def achar_periodo_de_inscricao(
    texto: str, ano_padrao: int
) -> tuple[datetime | None, datetime | None]:
    """Procura o trecho que fala de inscricao e tira comeco e fim dele.

    Nao tenta entender a frase: junta as datas que aparecem perto da palavra
    "inscri" e assume que a primeira abre e a ultima fecha. Funciona para os
    tres jeitos que o site escreve:

        "das 10h do dia 04 de setembro ate as 23h59 do dia 05 de outubro"
        "a partir das 16h do dia 16 de setembro ate as 16h do dia 16 de outubro"
        "o prazo para se inscrever e de 14 a 25 de setembro de 2026"

    Sem pelo menos duas datas perto da palavra, devolve o que der e deixa o
    resto nulo.
    """
    melhor: tuple[datetime | None, datetime | None] = (None, None)

    for m in re.finditer(r"inscri", texto):
        trecho = texto[m.start() : m.start() + 320]
        # Corta no ponto final da ideia, para nao pegar data de prova
        trecho = re.split(r"\bprova(s)?\s+(sera|serao|acontece|ocorre)", trecho)[0]

        datas = [d for _, d in achar_datas(trecho, ano_padrao)]
        if len(datas) < 2:
            continue

        inicio, fim = datas[0], datas[-1]
        if inicio > fim:               # ordem invertida no texto: ignora
            continue
        if (fim - inicio).days > 180:  # janela absurda: provavelmente nao e inscricao
            continue

        # fica com a janela que termina mais tarde: prorrogacao costuma vir
        # depois no texto e e ela que vale
        if melhor[1] is None or fim > melhor[1]:
            melhor = (inicio, _fim_do_dia(fim))

    return melhor


def achar_banca(texto: str) -> str | None:
    for nome, pistas in BANCAS.items():
        if any(pista in texto for pista in pistas):
            return nome
    return None


# Palavras que anunciam onde o cargo fica ou onde a prova acontece. Um
# municipio citado logo depois de uma destas vale muito mais do que um citado
# de passagem no meio da materia.
PISTAS_DE_LOCAL = (
    "lotacao", "lotado", "lotados", "local de prova", "locais de prova",
    "local de trabalho", "sede", "com atuacao em", "para atuar em",
)


def _citados(texto: str, municipios_conhecidos: dict[str, str]) -> dict[str, int]:
    """{nome original: posicao da primeira citacao}, so dos que me interessam."""
    achados: dict[str, int] = {}
    for normalizado, original in municipios_conhecidos.items():
        # Limite de palavra dos dois lados, e recusa quando o nome continua:
        # "sao jose do cerrito" nao pode ser lido como "sao jose". A checagem
        # olha SO o que vem logo depois - varrer adiante rejeitaria "sao jose
        # abre 300 vagas do edital" por causa do "do" la na frente.
        m = re.search(
            rf"(?<![a-z]){re.escape(normalizado)}(?![a-z]|\s+d[oae]s?\s)", texto
        )
        if m:
            achados[original] = m.start()
    return achados


def achar_municipio(texto: str, municipios_conhecidos: dict[str, str]) -> str | None:
    """Procura no corpo do texto um municipio que eu me importe.

    Serve para o caso do orgao estadual: "SEFAZ (SC)" nao tem municipio no
    titulo, mas o texto diz "lotacao em Florianopolis". So procuramos os
    municipios de config/regioes.yml - se nao for nenhum deles, nao interessa
    onde e, e continua `indefinida`.

    Quando a pagina cita VARIOS municipios - comum em edital de secretaria
    estadual, que lista vagas pelo estado inteiro - escolher um seria chute.
    Nesse caso so vale o que estiver colado numa pista de local ("lotacao
    em..."); sem pista, devolve None e o registro segue `indefinida`.
    """
    citados = _citados(texto, municipios_conhecidos)
    if not citados:
        return None

    # 1) o que aparece logo depois de uma pista de local
    for pista in PISTAS_DE_LOCAL:
        for m in re.finditer(re.escape(pista), texto):
            janela = texto[m.end() : m.end() + 80]
            perto = _citados(janela, municipios_conhecidos)
            if len(perto) == 1:
                return next(iter(perto))

    # 2) sem pista, so decide se a pagina citar um municipio de interesse so
    if len(citados) == 1:
        return next(iter(citados))

    log.debug("varios municipios na pagina (%s): nao da para decidir", list(citados))
    return None


# Caminho que e lista institucional da banca, e nao hotsite de um concurso. A
# pagina /concursos/ da FEPESE traz os 520 concursos dela; o edital de um so
# nao esta ali.
CAMINHOS_GENERICOS = ("", "/", "/concursos", "/concursos/", "/index.php", "/home")

# Arquivo no fim do endereco: e pagina dentro do hotsite, e nao o hotsite.
# href="..." com aspas simples ou duplas.
PADRAO_HREF = re.compile(r"""href=["']([^"']+)["']""")

PADRAO_ARQUIVO = re.compile(r"/[^/]+\.(?:html?|php|aspx?)$", re.IGNORECASE)


def achar_hotsite(html: str) -> str | None:
    """O endereco onde a banca publica os documentos deste concurso.

    A pagina do agregador linka o hotsite da banca - e dali que o acervo tira
    edital, prova e gabarito. Sem isto, concurso vindo do feed de noticias
    nunca chega ao acervo: so FEPESE e IESES trazem o hotsite no proprio dado.

    Cada banca identifica o concurso num lugar diferente do endereco, e os dois
    casos sao reais:

      * no SUBDOMINIO, e a FEPESE faz assim -
        "https://2026cpeducaeesj.fepese.org.br/?go=edital&mn=..." vira
        "https://2026cpeducaeesj.fepese.org.br";
      * no CAMINHO, e a FCC faz assim -
        "https://www.concursosfcc.com.br/concursos/sefsc126/index.html" vira
        "https://www.concursosfcc.com.br/concursos/sefsc126".

    Devolver so o dominio no segundo caso perderia justamente o pedaco que diz
    de que concurso se trata.
    """
    marcas = {marca.strip() for marcas in BANCAS.values() for marca in marcas}
    candidatos: list[str] = []

    for endereco in PADRAO_HREF.findall(html or ""):
        limpo = html_lib.unescape(endereco).strip()
        if not limpo.lower().startswith(("http://", "https://")):
            continue

        partes = urlsplit(limpo)
        dominio = _sem_acento(partes.netloc).lower()
        if not any(marca and marca in dominio for marca in marcas):
            continue

        caminho = PADRAO_ARQUIVO.sub("", partes.path).rstrip("/")
        if caminho.lower() in CAMINHOS_GENERICOS:
            # Sem caminho proprio, o concurso so pode estar no subdominio.
            if partes.path.rstrip("/").lower() in ("/concursos", "/index.php", "/home"):
                continue
            candidatos.append(f"{partes.scheme}://{partes.netloc}")
        else:
            candidatos.append(f"{partes.scheme}://{partes.netloc}{caminho}")

    # O mais curto vence. A mesma pagina costuma linkar varias telas do
    # mesmo hotsite - edital, inscricao, provas - e o acervo precisa da
    # RAIZ. De Sao Jose 2026 saiu ".../inscricao" na primeira versao,
    # so porque foi o primeiro link que apareceu no HTML.
    return min(candidatos, key=len) if candidatos else None


def extrair(html: str, ano_padrao: int, municipios: dict[str, str]) -> Detalhes:
    texto = texto_da_pagina(html)
    inicio, fim = achar_periodo_de_inscricao(texto, ano_padrao)
    return Detalhes(
        inscricoes_de=inicio,
        inscricoes_ate=fim,
        banca=achar_banca(texto),
        municipio=achar_municipio(texto, municipios),
        hotsite=achar_hotsite(html),
    )
