"""Fonte 7: os editais da SEJURI, pela API REST do WordPress dela.

Por que esta fonte: a Secretaria de Estado de Justica e Reintegracao Social
(antes SAP e SJC) e o orgao do alvo principal. Os editais da carreira - 2006,
2013, 2016, 2019 e 2022 - estao no site dela, na categoria "Concurso
Publico"; o proximo deve sair la tambem. A autorizacao e a comissao saem no
Diario Oficial do Estado (decisao 154), e as noticias da secretaria nao
ficam neste site (vao para estado.sc.gov.br/noticias).

O robots.txt so proibe /wp-admin/, e o WordPress expoe os posts em
/wp-json/wp/v2/posts, como o da FEPESE.

O recorte: as categorias "Concurso Publico" (43) e "Processo Seletivo" (65,
a mae das de cada ano). O seletivo entra de proposito: a SEJURI tambem
contrata temporario de outros cargos (enfermagem, socioeducativo), e quem
separa isso do meu concurso e o `config/alvo.yml` (`orgao_exclui`), nao o
coletor. Ficam de fora o concurso interno de remocao (71), os cursos de
capacitacao, o credenciamento e o chamamento publico. Sao 16 posts nas duas
categorias, numa pagina so.
"""
import html
import re
from datetime import datetime

from radar.collectors.base import Coletor, ItemColetado

API = ("https://www.sejuri.sc.gov.br/wp-json/wp/v2/posts?categories=43,65"
       "&per_page=100&_fields=id,date,link,title,categories,excerpt")

CONCURSO_PUBLICO, PROCESSO_SELETIVO = 43, 65

ORGAO = "Secretaria de Estado de Justiça e Reintegração Social"


def _limpar(texto: str | None) -> str:
    """Tira tag e entidade do que o WordPress devolve."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", texto or "")).split())


def ano_do_edital(titulo: str) -> int | None:
    """"CONCURSO PUBLICO EDITAL 001/SAP/2019 - AGENTE PENITENCIARIO" -> 2019."""
    anos = re.findall(r"/\s*(\d{4})\b", titulo or "")
    return int(anos[-1]) if anos else None


def _data(texto: str | None) -> datetime | None:
    if not texto:
        return None
    from radar.util import fuso_local

    try:
        return datetime.fromisoformat(texto).replace(tzinfo=fuso_local())
    except ValueError:
        return None


class Sejuri(Coletor):
    nome = "sejuri"

    def coletar(self) -> list[ItemColetado]:
        resposta = self.get(API)
        itens: list[ItemColetado] = []
        for post in resposta.json() or []:
            item = self._para_item(post)
            if item:
                itens.append(item)
        return itens

    def _para_item(self, post: dict) -> ItemColetado | None:
        titulo = _limpar((post.get("title") or {}).get("rendered"))
        url = post.get("link")
        if not titulo or not url:
            return None

        publicado = _data(post.get("date"))
        # O titulo como a FEPESE escreve o mesmo orgao: o ano do edital e a
        # secretaria na frente. O ano e por onde o cartao reconhece a edicao
        # velha - o post do concurso de 2022 foi republicado em 27/01/2025, e
        # sem o "2022 - " passaria por novo. A secretaria e o que diz de quem
        # e "PROCESSO SELETIVO SIMPLIFICADO EDITAL N. 006/2026", e o que faz o
        # classificador reconhecer o orgao estadual.
        ano = ano_do_edital(titulo) or (publicado.year if publicado else None)
        categorias = post.get("categories") or []
        partes = [str(ano)] if ano else []

        return ItemColetado(
            titulo=" - ".join(partes + [ORGAO, titulo]),
            url=url,
            resumo=_limpar((post.get("excerpt") or {}).get("rendered")) or None,
            orgao=ORGAO,
            # Secretaria de estado: o edital e que diz os polos de prova.
            uf="SC",
            tipo="concurso" if CONCURSO_PUBLICO in categorias else "seletivo",
            publicado_em=publicado,
            extra={"categorias": categorias, "post_id": post.get("id")},
        )
