"""Fonte 1: feed RSS do Concursos no Brasil.

Comecamos por um RSS de proposito. RSS e um formato publico, estavel e feito
para ser lido por programa; raspar HTML quebra toda vez que o site mexe no
layout.

O feed aceita ?paged=N e devolve os itens mais antigos, com exatamente a mesma
estrutura da primeira pagina. E isso que permite a carga inicial: em vez de
raspar pagina de arquivo em HTML, andamos para tras no proprio RSS, com o
mesmo parser e os mesmos campos - titulo completo, data e categoria. Medido
no site real: 15 itens por pagina, e paged=60 chega a uns 38 dias atras.

O padrao de URL foi conferido contra o site real em 17/09/2026:
    https://concursosnobrasil.com/concursos/sc/2026/09/17/nome-do-post/
Ainda assim existe o segundo caminho, pela categoria ("Santa Catarina" -> SC),
porque nem todo post segue o padrao.
"""
import re
from calendar import timegm
from datetime import datetime, timezone

import feedparser

from radar.collectors.base import Coletor, ItemColetado

FEED_URL = "https://www.concursosnobrasil.com.br/feed/"

# Teto de seguranca para a carga inicial. Cada pagina e uma requisicao ao site
# de alguem: 400 paginas ja passam de um ano de historico.
MAXIMO_DE_PAGINAS = 400

# Links no formato /concursos/sc/2026/09/17/titulo-do-post/
PADRAO_UF_NA_URL = re.compile(r"/concursos/([a-z]{2})/\d{4}/", re.IGNORECASE)

UFS = {
    "ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
}

# Caminho 2: o feed marca o post com o nome do estado por extenso.
ESTADO_PARA_UF = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM",
    "bahia": "BA", "ceara": "CE", "distrito federal": "DF",
    "espirito santo": "ES", "goias": "GO", "maranhao": "MA",
    "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG",
    "para": "PA", "paraiba": "PB", "parana": "PR", "pernambuco": "PE",
    "piaui": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondonia": "RO", "roraima": "RR",
    "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE",
    "tocantins": "TO",
}


def _sem_acento(texto: str) -> str:
    """Compara nome de estado sem depender de acentuacao do feed."""
    import unicodedata

    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c)).lower().strip()


def _uf_da_url(url: str) -> str | None:
    achado = PADRAO_UF_NA_URL.search(url or "")
    if not achado:
        return None
    uf = achado.group(1).lower()
    return uf.upper() if uf in UFS else None


def _uf_das_categorias(categorias: list[str]) -> str | None:
    for categoria in categorias:
        uf = ESTADO_PARA_UF.get(_sem_acento(categoria))
        if uf:
            return uf
    return None


def _data(entrada) -> datetime | None:
    """feedparser ja devolve a data em struct_time UTC; so falta virar datetime."""
    marcado = entrada.get("published_parsed") or entrada.get("updated_parsed")
    if not marcado:
        return None
    return datetime.fromtimestamp(timegm(marcado), tz=timezone.utc)


def _resumo(entrada) -> str | None:
    bruto = entrada.get("summary") or entrada.get("description") or ""
    if not bruto:
        return None
    # feedparser ja entrega o texto limpo quando o tipo e text/plain; quando
    # vem HTML, tiramos as tags na mao para nao carregar o BeautifulSoup aqui.
    texto = re.sub(r"<[^>]+>", " ", bruto)
    texto = re.sub(r"\s+", " ", texto).strip()
    # o feed repete "O post ... apareceu primeiro em ..." no fim de cada item
    texto = re.split(r"O post\s", texto)[0].strip()
    return texto or None


class ConcursosNoBrasil(Coletor):
    nome = "concursosnobrasil"

    def __init__(self, paginas: int = 1, desde: datetime | None = None) -> None:
        """paginas=1 e a coleta do dia a dia; mais que isso e carga inicial.

        `desde` faz a leitura parar assim que a pagina inteira ficar mais
        antiga que essa data - assim a carga inicial nao varre o site todo
        so para descobrir que ja passou do periodo pedido.
        """
        super().__init__()
        self.paginas = max(1, min(paginas, MAXIMO_DE_PAGINAS))
        self.desde = desde

    def _url_da_pagina(self, numero: int) -> str:
        return FEED_URL if numero == 1 else f"{FEED_URL}?paged={numero}"

    def coletar(self) -> list[ItemColetado]:
        itens: list[ItemColetado] = []

        for numero in range(1, self.paginas + 1):
            da_pagina = self._ler_pagina(self._url_da_pagina(numero))
            if not da_pagina:
                break                      # acabou o feed
            itens.extend(da_pagina)

            if self._passou_do_periodo(da_pagina):
                break

        return itens

    def _passou_do_periodo(self, itens: list[ItemColetado]) -> bool:
        """Para quando a pagina INTEIRA ja e mais antiga que o periodo pedido."""
        if not self.desde:
            return False
        datas = [i.publicado_em for i in itens if i.publicado_em]
        return bool(datas) and all(d < self.desde for d in datas)

    def _ler_pagina(self, url: str) -> list[ItemColetado]:
        xml = self.get(url).text
        feed = feedparser.parse(xml)

        itens: list[ItemColetado] = []
        for entrada in feed.entries:
            titulo = (entrada.get("title") or "").strip()
            link = (entrada.get("link") or "").strip()
            if not titulo or not link:
                continue

            categorias = [t.get("term", "") for t in entrada.get("tags", []) if t.get("term")]

            itens.append(
                ItemColetado(
                    titulo=titulo,
                    url=link,
                    resumo=_resumo(entrada),
                    uf=_uf_da_url(link) or _uf_das_categorias(categorias),
                    situacao="edital_publicado",
                    publicado_em=_data(entrada),
                    extra={"categorias": categorias},
                )
            )
        return itens
