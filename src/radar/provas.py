"""Acervo de provas: descobrir, baixar e catalogar.

Cada concurso da FEPESE tem um hotsite proprio, e e nele que ficam os PDFs:

    ?go=edital   -> o edital de abertura
    ?go=provas   -> o caderno de prova de cada cargo, e os gabaritos

O caderno vem com o cargo no rotulo do link ("Monitor de Transporte Escolar",
"Supervisor Escolar"), que e justamente o que interessa: o que vale estudar e
o padrao da banca no SEU cargo, nao a media de todos.

## O que vai para o git e o que nao vai

Os PDFs NAO entram no repositorio. Git guarda uma copia inteira de cada
arquivo binario a cada commit, e algumas centenas de provas deixariam o
repositorio grande e lento.

O que entra e o **manifesto** (`data/provas.json`): link de origem, banca,
orgao, cargo, ano e o sha256 de cada arquivo. Com ele, `radar baixar-provas`
reconstroi o acervo inteiro em qualquer maquina, e o hash prova que o arquivo
e o mesmo. Versionar a receita em vez do artefato e a mesma logica de
Dockerfile e imagem.
"""
import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from radar import config

log = logging.getLogger(__name__)

EDITAL, PROVA, GABARITO = "edital", "prova", "gabarito"

# Rotulos que descrevem o documento, e portanto NAO sao nome de cargo.
ROTULOS_DE_DOCUMENTO = (
    "caderno de prova", "caderno", "gabarito", "prova escrita", "edital",
    "download", "clique aqui", "pdf",
)

# Nome de arquivo tipo "M1.pdf" ou "S12.pdf": e caderno de prova, por nivel.
PADRAO_CADERNO = re.compile(r"^[a-z]{1,2}\d+\.pdf$", re.IGNORECASE)


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", _sem_acento(texto)).strip().lower()


@dataclass
class Documento:
    """Um PDF do acervo, ainda nao baixado."""

    tipo: str                       # edital | prova | gabarito
    url: str
    arquivo: str                    # nome do arquivo na origem
    cargo: str | None = None
    concurso_url: str | None = None
    banca: str | None = None
    orgao: str | None = None
    municipio: str | None = None
    ano: int | None = None
    sha256: str | None = None
    caminho: str | None = None      # onde ficou no disco
    tamanho: int | None = None

    def chave(self) -> str:
        """O que identifica o documento. Usado para nao catalogar duas vezes."""
        return self.url


def _tipo_do_documento(arquivo: str, rotulos: list[str]) -> str | None:
    texto = _normalizar(" ".join([arquivo, *rotulos]))

    if "gabarito" in texto:
        return GABARITO
    if "caderno" in texto or "prova" in texto or PADRAO_CADERNO.match(arquivo):
        return PROVA
    return None


def _cargo(rotulos: list[str]) -> str | None:
    """O rotulo que nomeia o cargo, entre os que apontam para o mesmo PDF.

    A pagina repete o link: uma vez com o nome do cargo ("Supervisor
    Escolar") e outra descrevendo o arquivo ("Caderno de Prova (S1)"). O
    cargo e o que sobra depois de tirar os descritivos.
    """
    for rotulo in rotulos:
        normal = _normalizar(rotulo)
        if not normal or len(normal) < 4:
            continue
        if any(marca in normal for marca in ROTULOS_DE_DOCUMENTO):
            continue
        return re.sub(r"\s+", " ", rotulo).strip()
    return None


def _links_com_rotulo(html: str, base: str) -> dict[str, dict]:
    """{url do pdf: {arquivo, rotulos}} - agrupa os rotulos do mesmo arquivo."""
    sopa = BeautifulSoup(html, "lxml")
    achados: dict[str, dict] = {}

    for ancora in sopa.find_all("a", href=True):
        href = ancora["href"]
        if ".pdf" not in href.lower():
            continue

        url = urljoin(base, href)
        nome = re.search(r"arquivo=([^&]+\.pdf)", href, re.IGNORECASE)
        arquivo = nome.group(1) if nome else href.rsplit("/", 1)[-1].split("?")[0]

        registro = achados.setdefault(url, {"arquivo": arquivo, "rotulos": []})
        rotulo = ancora.get_text(" ", strip=True)
        if rotulo:
            registro["rotulos"].append(rotulo)

    return achados


def ler_pagina_de_provas(html: str, base: str) -> list[Documento]:
    """Cadernos de prova e gabaritos de um hotsite."""
    documentos: list[Documento] = []

    for url, dados in _links_com_rotulo(html, base).items():
        tipo = _tipo_do_documento(dados["arquivo"], dados["rotulos"])
        if tipo is None:
            continue
        documentos.append(Documento(
            tipo=tipo,
            url=url,
            arquivo=dados["arquivo"],
            cargo=_cargo(dados["rotulos"]) if tipo == PROVA else None,
        ))

    return documentos


def ler_pagina_de_edital(html: str, base: str) -> list[Documento]:
    """O edital de abertura. E um PDF so, mas a pagina pode ter retificacoes."""
    return [
        Documento(tipo=EDITAL, url=url, arquivo=dados["arquivo"])
        for url, dados in _links_com_rotulo(html, base).items()
    ]


# --- disco e manifesto ------------------------------------------------------

def diretorio_provas() -> Path:
    caminho = config.diretorio_dados() / "provas"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def caminho_do_manifesto() -> Path:
    return config.diretorio_dados() / "provas.json"


def _nome_seguro(texto: str) -> str:
    """Nome de pasta que funciona no Windows e no Linux."""
    limpo = re.sub(r"[^a-z0-9]+", "-", _normalizar(texto or "sem-nome"))
    return limpo.strip("-") or "sem-nome"


def destino(documento: Documento) -> Path:
    """data/provas/<banca>/<ano>/<municipio>/<arquivo>"""
    partes = [
        _nome_seguro(documento.banca or "sem-banca"),
        str(documento.ano or "sem-ano"),
        _nome_seguro(documento.municipio or documento.orgao or "sem-orgao"),
    ]
    pasta = diretorio_provas().joinpath(*partes)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / _nome_seguro(documento.arquivo).replace("-pdf", ".pdf")


def _caminho_relativo(caminho: Path) -> str:
    """Caminho com barra normal, sempre.

    No Windows o str() de um Path sai com contrabarra, e isso iria para o
    manifesto versionado - que a outra maquina, possivelmente Linux, leria
    como nome de arquivo com contrabarra dentro. O manifesto precisa ser
    portatil; ele existe justamente para reconstruir o acervo em qualquer
    lugar.
    """
    return caminho.relative_to(config.diretorio_dados()).as_posix()


def sha256_do_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for pedaco in iter(lambda: arquivo.read(65536), b""):
            resumo.update(pedaco)
    return resumo.hexdigest()


def carregar_manifesto() -> list[dict]:
    caminho = caminho_do_manifesto()
    if not caminho.exists():
        return []
    return json.loads(caminho.read_text(encoding="utf-8"))


def gravar_manifesto(registros: list[dict]) -> int:
    """Escreve o manifesto ordenado, para o diff do commit ficar estavel."""
    caminho = caminho_do_manifesto()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    ordenados = sorted(registros, key=lambda r: (r.get("url") or ""))
    caminho.write_text(
        json.dumps(ordenados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(ordenados)


def baixar(documento: Documento, buscador, forcar: bool = False) -> Documento | None:
    """Salva o PDF no disco e preenche hash, caminho e tamanho.

    Arquivo que ja existe nao e baixado de novo - o acervo cresce sem repetir
    requisicao. `forcar` serve para reconferir um arquivo suspeito.
    """
    caminho = destino(documento)

    if caminho.exists() and not forcar:
        documento.caminho = _caminho_relativo(caminho)
        documento.sha256 = sha256_do_arquivo(caminho)
        documento.tamanho = caminho.stat().st_size
        return documento

    try:
        resposta = buscador.get(documento.url)
    except Exception as erro:  # noqa: BLE001 - PDF fora do ar e rotina
        log.warning("nao baixei %s (%s)", documento.arquivo, type(erro).__name__)
        return None

    conteudo = resposta.content
    # O que importa e ser PDF mesmo: pagina de erro devolvida com HTTP 200 e
    # comum e nao pode entrar no acervo como se fosse prova.
    #
    # O cabecalho %PDF nao precisa estar no byte zero - o servidor da FEPESE
    # manda linhas em branco antes, e o arquivo abre normalmente. Por isso a
    # busca e no comeco do arquivo, e nao um startswith.
    if b"%PDF" not in conteudo[:1024]:
        log.warning("%s nao parece PDF (comeca com %r)", documento.arquivo,
                    conteudo[:16])
        return None

    caminho.write_bytes(conteudo)
    documento.caminho = _caminho_relativo(caminho)
    documento.sha256 = hashlib.sha256(conteudo).hexdigest()
    documento.tamanho = len(conteudo)
    return documento


def para_registro(documento: Documento) -> dict:
    return {k: v for k, v in asdict(documento).items() if v is not None}
