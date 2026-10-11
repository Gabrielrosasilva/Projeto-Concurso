"""Fonte 8: IDIB, pela API REST do WordPress dela.

Por que esta banca: e a do concurso do Corpo de Bombeiros Militar de SC de
2026 (CFO e CFP; contrato 0327/2025/CBMSC no Diario Oficial do Estado). O
edital de abertura do CBMSC saiu escaneado no DOE, sem texto, e por isso nao
entra por la (decisao 154) - entra por aqui.

O robots.txt (o do Yoast) nao proibe nada, e o WordPress expoe
/wp-json/wp/v2/posts, como o da FEPESE. Cada post e um concurso, com o link
para concurso.idib.org.br/Concurso.aspx?ID=<n>; o post nao tem texto (o
resumo vem vazio), so o titulo.

O recorte e o do pedido, como o da AOCP: so as categorias "Inscricoes
Abertas" (32) e "Em andamento" (61). Os concluidos e os suspensos ficam de
fora. E banca nacional - quase tudo e prefeitura do Nordeste -, entao quem
separa SC e o titulo e o `config/alvo.yml`.
"""
import html
import re
from datetime import datetime

from radar.collectors.base import Coletor, ItemColetado
from radar.collectors.concursos_no_brasil import ESTADO_PARA_UF, UFS
from radar.regioes import normalizar

API = ("https://idib.org.br/wp-json/wp/v2/posts?categories=32,61&per_page=100"
       "&_fields=id,date,link,title,categories&page={}")

INSCRICOES_ABERTAS, EM_ANDAMENTO = 32, 61

# Teto de seguranca: sao 103 posts (2 paginas) em 11/10/2026.
MAXIMO_DE_PAGINAS = 10

BANCA = "IDIB"

# A UF como o IDIB escreve no titulo: colada no municipio ("ITAREMA/CE",
# "ARAGUAINA-TO") ou depois do travessao ("NISIA FLORESTA – RN").
# "002-2026/DP/CBMSC" nao e UF: "DP" nao e estado, e o "SC" de CBMSC esta
# grudado na sigla.
SIGLA = re.compile(r"(?:/|[–-]\s?)([A-Z]{2})\b")
# Ou o estado por extenso: "Policia Militar do Espirito Santo". Com o
# de/do/da na frente, do mais longo para o mais curto.
ESTADO_POR_EXTENSO = re.compile(
    r"\bd[eoa]\s+(?:estado\s+d[eoa]\s+)?("
    + "|".join(map(re.escape, sorted(ESTADO_PARA_UF, key=len, reverse=True))) + r")\b"
)

# "PREFEITURA MUNICIPAL DE ITAREMA/CE" -> "itarema". No meio do titulo tambem:
# "CONCURSO PUBLICO PREFEITURA MUNICIPAL DE NISIA FLORESTA – RN", e com a
# abreviacao "SENA MADUREIRA EDT. N.01/2025".
MUNICIPIO = re.compile(
    r"\b(?:prefeitura municipal|camara municipal|municipio) de ([a-z ]+?)"
    r"\s*(?:/|–|-|,|\.|\bedital\b|\bedt\b|$)"
)


def _limpar(texto: str | None) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", texto or "")).split())


def extrair_uf(titulo: str) -> str | None:
    """A UF que o titulo escreve. None quando nao escreve - nunca chute."""
    for achado in SIGLA.finditer(titulo or ""):
        if achado.group(1).lower() in UFS:
            return achado.group(1)
    achado = ESTADO_POR_EXTENSO.search(normalizar(titulo))
    return ESTADO_PARA_UF[achado.group(1)] if achado else None


def extrair_municipio(titulo: str) -> str | None:
    achado = MUNICIPIO.search(normalizar(titulo))
    return achado.group(1).strip().upper() if achado else None


def ano_do_edital(titulo: str) -> int | None:
    """"EDITAL 002-2026/DP/CBMSC" ou "EDITAL N. 01/2026" -> 2026."""
    achado = re.search(r"\d+\s*[/-]\s*(20\d{2})\b", titulo or "")
    return int(achado.group(1)) if achado else None


def _data(texto: str | None) -> datetime | None:
    if not texto:
        return None
    from radar.util import fuso_local

    try:
        return datetime.fromisoformat(texto).replace(tzinfo=fuso_local())
    except ValueError:
        return None


class Idib(Coletor):
    nome = "idib"

    def coletar(self) -> list[ItemColetado]:
        itens: list[ItemColetado] = []
        vistos: set[str] = set()
        for pagina in range(1, MAXIMO_DE_PAGINAS + 1):
            resposta = self.get(API.format(pagina))
            posts = resposta.json() or []
            for post in posts:
                item = self._para_item(post)
                if item and item.url not in vistos:
                    vistos.add(item.url)
                    itens.append(item)
            total = int(resposta.headers.get("X-WP-TotalPages", 0) or 0)
            if not posts or not total or pagina >= total:
                break
        return itens

    def _para_item(self, post: dict) -> ItemColetado | None:
        titulo = _limpar((post.get("title") or {}).get("rendered"))
        url = post.get("link")
        if not titulo or not url:
            return None

        publicado = _data(post.get("date"))
        categorias = post.get("categories") or []
        situacao = ("inscricoes_abertas" if INSCRICOES_ABERTAS in categorias
                    else "edital_publicado")
        # O ano do edital na frente, como nas outras bancas: e por ele que o
        # cartao reconhece a edicao velha.
        ano = ano_do_edital(titulo) or (publicado.year if publicado else None)

        return ItemColetado(
            titulo=f"{ano} - {titulo}" if ano else titulo,
            url=url,
            municipio=extrair_municipio(titulo),
            uf=extrair_uf(titulo),
            banca=BANCA,
            situacao=situacao,
            tipo="seletivo" if "processo seletivo" in normalizar(titulo) else "concurso",
            publicado_em=publicado,
            extra={"categorias": categorias, "post_id": post.get("id")},
        )
