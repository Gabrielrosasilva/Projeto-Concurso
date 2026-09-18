"""Como achar edital, prova e gabarito no hotsite da IESES.

A FEPESE e a IESES publicam de jeitos diferentes, e por isso a leitura mora em
arquivos separados. O que e igual nas duas - baixar, dar nome ao arquivo,
conferir o sha256, gravar no manifesto - continua em `provas.py`.

O hotsite da IESES e uma pagina so, com os PDFs num CDN e o endereco em um
formato regular:

    .../{ano}/{pasta}/edital.pdf
    .../{ano}/{pasta}/edital_ret001.pdf     (retificacao)
    .../{ano}/{pasta}/provas/{codigo}.pdf
    .../{ano}/{pasta}/gabaritos/{codigo}.pdf

O codigo e o do cargo, e o mesmo nas duas pastas: e por ele que a prova casa
com o gabarito dela. O nome do cargo nao esta no endereco, e sim no texto ao
lado do link ("- 1016 - Assistente Social").

Uma diferenca que muda o trabalho depois: aqui o gabarito e um PDF a parte. Na
FEPESE ele vem marcado dentro do proprio caderno.
"""
import re

from bs4 import BeautifulSoup

from radar.provas import EDITAL, GABARITO, PROVA, Documento

# O texto ao lado do link traz o codigo e o cargo: "- 1016 - Assistente Social"
# ou "- 1020/1033 - Auxiliar de Ensino" quando dois codigos dividem o caderno.
PADRAO_CARGO = re.compile(r"-\s*(\d{3,5}(?:/\d{3,5})*)\s*-\s*([^|]+)")

# Onde o PDF mora no CDN diz o que ele e, sem depender do texto da pagina.
PASTA_POR_TIPO = (("/provas/", PROVA), ("/gabaritos/", GABARITO))


def _texto_ao_redor(marca) -> str:
    """O texto da linha que contem o link, para achar o nome do cargo."""
    linha = marca.find_parent("tr") or marca.find_parent("li") or marca.parent
    if linha is None:
        return ""
    return " | ".join(t.strip() for t in linha.stripped_strings if t.strip())


def _tipo_e_codigo(url: str) -> tuple[str | None, str | None]:
    for pasta, tipo in PASTA_POR_TIPO:
        if pasta in url:
            return tipo, url.rsplit("/", 1)[-1].removesuffix(".pdf")

    arquivo = url.rsplit("/", 1)[-1].lower()
    if arquivo.startswith("edital"):
        return EDITAL, None
    return None, None


def ler_hotsite(html: str, base: str) -> list[Documento]:
    """Os documentos que a pagina do concurso oferece.

    Devolve edital, cadernos de prova e gabaritos. O que nao for nenhum dos
    tres - resultado, classificacao, convocacao - fica de fora: nao ajuda a
    estudar e so ocuparia disco.
    """
    sopa = BeautifulSoup(html, "lxml")
    achados: dict[str, Documento] = {}

    for marca in sopa.find_all("a", href=True):
        url = marca["href"].strip()
        if not url.lower().endswith(".pdf"):
            continue

        tipo, codigo = _tipo_e_codigo(url)
        if tipo is None or url in achados:
            continue

        cargo = None
        if tipo in (PROVA, GABARITO):
            encontrado = PADRAO_CARGO.search(_texto_ao_redor(marca))
            if encontrado:
                cargo = re.sub(r"\s+", " ", encontrado.group(2)).strip()

        achados[url] = Documento(
            tipo=tipo,
            url=url,
            # O nome na origem e so o codigo do cargo ("1016.pdf"), igual nas
            # duas pastas. O tipo entra no nome para prova e gabarito nao se
            # atropelarem no disco.
            arquivo=f"{tipo}_{codigo}.pdf" if codigo else url.rsplit("/", 1)[-1],
            cargo=cargo,
            banca="IESES",
        )

    return list(achados.values())
