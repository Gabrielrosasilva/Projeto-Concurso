"""Fonte 6: as noticias da Prefeitura de Balneario Camboriu.

Por que esta fonte: a Guarda Municipal de BC e um dos dois `de_olho` do
`config/alvo.yml`, e foi pela prefeitura que saiu o anuncio do concurso novo
(04/08/2026: "Balneario Camboriu anuncia novo concurso para Guarda
Municipal" - a comissao especial e o projeto de lei das 90 vagas). A banca, o
edital e as inscricoes vem depois, por outros caminhos; o anuncio vem daqui.

Como foi achada: o site (www.bc.sc.gov.br) e uma tela em React, e o
JavaScript dela pede as noticias a `sim.bc.sc.gov.br/portal-municipio/api/
noticias`, com o filtro `titulo` que a propria tela usa na busca. O
robots.txt desse host so proibe /public/ (as fotos e os anexos); o do
www nao existe (devolve a pagina da tela). O link de cada noticia e a rota
da tela: /noticia/<id>.

O recorte e o do pedido - so concurso e noticia de concurso: a busca por
"concurso" no titulo, e daqui so sai o titulo que fala de concurso publico.
De 03/2025 a 10/2026 foram 11 noticias com "concurso" no titulo, e uma era
de concurso publico; as outras eram de desenho, de bandas, de oratoria, de
cerveja. A lista de editais da mesma API ficou de fora: e convocacao e
nomeacao dos concursos de 2022, e nao novidade.
"""
import re
from datetime import datetime

from radar.collectors.base import Coletor, ItemColetado
from radar.regioes import normalizar

API = "https://sim.bc.sc.gov.br/portal-municipio/api/noticias?pagina=1&titulo=concurso"
LINK = "https://www.bc.sc.gov.br/noticia/{}"

# O titulo que fala de concurso publico: "anuncia novo concurso para Guarda
# Municipal". "Concurso de desenho para estudantes" e "Concurso Educacao para
# o Transito" nao casam: o "para" tem de vir colado no "concurso".
CONCURSO_PUBLICO = re.compile(
    r"\bconcursos? publicos?\b|\bnovo concurso\b|\bconcurso para\b"
)

MUNICIPIO = "Balneário Camboriú"
ORGAO = "Prefeitura de Balneário Camboriú"


def e_concurso_publico(titulo: str, subtitulo: str | None = None) -> bool:
    return bool(CONCURSO_PUBLICO.search(normalizar(f"{titulo} {subtitulo or ''}")))


def _data(texto: str | None) -> datetime | None:
    """"04/08/2026 - 11:54" -> datetime com o fuso daqui."""
    if not texto:
        return None
    from radar.util import fuso_local

    for formato in ("%d/%m/%Y - %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto.strip(), formato).replace(tzinfo=fuso_local())
        except ValueError:
            continue
    return None


class PrefeituraBc(Coletor):
    nome = "prefeitura_bc"

    def coletar(self) -> list[ItemColetado]:
        # Uma pagina basta: sao 20 por pagina, e a busca trouxe 11 noticias
        # em um ano e meio. A coleta e diaria.
        dados = self.get(API).json() or {}
        itens: list[ItemColetado] = []
        for noticia in dados.get("noticias") or []:
            item = self._para_item(noticia)
            if item:
                itens.append(item)
        return itens

    def _para_item(self, noticia: dict) -> ItemColetado | None:
        codigo = noticia.get("newsId")
        titulo = " ".join((noticia.get("title") or "").split())
        if codigo is None or not titulo:
            return None
        subtitulo = " ".join((noticia.get("subtitle") or "").split()).strip(" .") or None
        if not e_concurso_publico(titulo, subtitulo):
            return None

        return ItemColetado(
            titulo=titulo,
            url=LINK.format(codigo),
            resumo=subtitulo,
            orgao=ORGAO,
            # E a propria prefeitura: o municipio e o estado sao dela.
            municipio=MUNICIPIO,
            uf="SC",
            publicado_em=_data(noticia.get("published")),
            # Noticia da prefeitura, e nao edital: o tipo fica para o
            # classificador, como no site de noticias.
            extra={
                "categoria": noticia.get("category_name"),
                "news_id": codigo,
            },
        )
