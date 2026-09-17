"""Fonte 1: feed RSS do Concursos no Brasil.

Comecamos por um RSS de proposito. RSS e um formato publico, estavel e feito
para ser lido por programa; raspar HTML quebra toda vez que o site mexe no
layout. A troco disso, o feed so entrega os itens mais recentes - trazer o ano
inteiro e assunto da fase 1.6, com uma carga inicial pelas paginas de arquivo.

ATENCAO, ainda nao verificado contra o site real: o padrao de URL abaixo veio
do esboco do projeto e nao foi conferido numa coleta de verdade. Se ele nao
bater, a UF sai vazia e o filtro geografico nao funciona. Por isso existe o
segundo caminho, pela categoria do post ("Santa Catarina" -> SC).
"""
import re
from calendar import timegm
from datetime import datetime, timezone

import feedparser

from radar.collectors.base import Coletor, ItemColetado

FEED_URL = "https://www.concursosnobrasil.com.br/feed/"

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

    def coletar(self) -> list[ItemColetado]:
        xml = self.get(FEED_URL).text
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
