"""Fonte 3: IESES, pela API JSON que a propria listagem de projetos usa.

Por que esta banca vem depois da FEPESE: ela e catarinense, fica em
Florianopolis e faz concurso de prefeitura da regiao - Biguacu e Gaspar estao
na lista. E o acervo dela e completo: cada concurso tem hotsite proprio com
edital, caderno de prova e gabarito.

Como foi achada: a pagina ieses.org/projetos e uma tela que carrega a lista por
JavaScript, com botao "carregar mais". O arquivo /projetos-static/projetos.js
mostra de onde vem o dado - /projetos/api?offset=&limit= -, e essa API devolve
JSON limpo. Melhor que raspar a tela: nao quebra quando mudam o CSS.

Nao ha robots.txt no dominio (404), entao nada esta declarado como proibido. O
`Coletor` continua identificando-se no User-Agent e respeitando o atraso entre
requisicoes.

Dois limites conhecidos, medidos:

  1. **sao 26 projetos**, de 2021 a 2026. A API nao devolve o historico
     inteiro da banca, so o que esta publicado no site;
  2. **10 dos 26 hotsites ja sairam do ar** (erro de SSL ou de Cloudflare). Os
     de 2023 para tras quase todos. O que sobra ainda traz Biguacu 2024 e
     Gaspar 2024, que sao os que interessam aqui.
"""
import logging
import re
from datetime import datetime

from radar.collectors.base import Coletor, ItemColetado

log = logging.getLogger(__name__)

API = "https://ieses.org/projetos/api"

# A API pagina por offset. 50 por vez cobre os 26 projetos numa requisicao so,
# e o teto existe caso a banca publique muito mais um dia.
POR_PAGINA = 50
MAXIMO_DE_PAGINAS = 20

# "PREFEITURA MUNICIPAL DE BIGUACU" -> "BIGUACU". A IESES escreve a entidade em
# caixa alta e por extenso, sem o ano que a FEPESE poe na frente.
PADRAO_ORGAO = re.compile(
    r"^\s*(?:prefeitura\s+municipal\s+de\s+|prefeitura\s+de\s+|"
    r"camara\s+municipal\s+de\s+|camara\s+de\s+|municipio\s+de\s+)"
    r"(.+?)\s*$",
    re.IGNORECASE,
)

# O que o campo `evento` diz sobre o tipo. A IESES escreve "Concurso Publico -
# Edital 001/2026" ou "PROCESSO SELETIVO PUBLICO - EDITAL 001/2026".
TIPO_POR_EVENTO = (
    ("seletivo", ("processo seletivo", "seletivo simplificado")),
    ("concurso", ("concurso publico", "concurso")),
)


def _sem_acento(texto: str) -> str:
    import unicodedata

    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def extrair_municipio(entidade: str) -> str | None:
    """O municipio, quando a entidade e uma prefeitura ou camara.

    Orgao que nao e municipal (SCGAS, CRC-SC, tribunal) nao tem municipio no
    nome, e ai devolve None em vez de chutar.
    """
    achado = PADRAO_ORGAO.match(_sem_acento(entidade or "").strip())
    if not achado:
        return None
    return achado.group(1).strip(" -,.") or None


def detectar_tipo(evento: str) -> str:
    """concurso ou seletivo, pelo que a propria banca escreveu no evento."""
    limpo = _sem_acento(evento or "").lower()
    for tipo, marcas in TIPO_POR_EVENTO:
        if any(marca in limpo for marca in marcas):
            return tipo
    return "concurso"


def _data(texto: str | None) -> datetime | None:
    """"10/08/2026 09:00:00" -> datetime com o fuso daqui."""
    if not texto:
        return None
    from radar.util import fuso_local

    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto.strip(), formato).replace(tzinfo=fuso_local())
        except ValueError:
            continue
    return None


class Ieses(Coletor):
    nome = "ieses"

    def __init__(self, paginas: int = MAXIMO_DE_PAGINAS) -> None:
        super().__init__()
        self.paginas = max(1, min(paginas, MAXIMO_DE_PAGINAS))

    def coletar(self) -> list[ItemColetado]:
        itens: list[ItemColetado] = []
        vistos: set[str] = set()

        for pagina in range(self.paginas):
            offset = pagina * POR_PAGINA
            resposta = self.get(f"{API}?offset={offset}&limit={POR_PAGINA}")
            registros = (resposta.json() or {}).get("projetos") or []
            if not registros:
                break

            for registro in registros:
                item = self._para_item(registro)
                if item and item.url not in vistos:
                    vistos.add(item.url)
                    itens.append(item)

            if len(registros) < POR_PAGINA:
                break

        return itens

    def _para_item(self, registro: dict) -> ItemColetado | None:
        url = (registro.get("url") or "").strip()
        entidade = (registro.get("entidade") or "").strip()
        if not url or not entidade:
            return None

        evento = (registro.get("evento") or "").strip()
        orgao = (registro.get("orgao") or "").strip() or entidade
        publicado = _data(registro.get("dataInicial"))

        # O titulo do radar segue o padrao da FEPESE, com o ano na frente: e o
        # que a previsao de abertura usa para saber de que ano e o concurso.
        ano = publicado.year if publicado else None
        titulo = f"{ano} - {entidade}" if ano else entidade
        if evento:
            titulo = f"{titulo} - {evento}"

        return ItemColetado(
            titulo=titulo,
            url=url,
            resumo=evento or None,
            orgao=orgao,
            municipio=extrair_municipio(entidade),
            # A IESES e de Florianopolis e trabalha sobretudo em SC, mas faz
            # concurso fora (tribunal do Amazonas, gas do Mato Grosso do Sul).
            # Afirmar SC aqui mandaria esses para o anel errado.
            uf=None,
            banca="IESES",
            tipo=detectar_tipo(evento),
            publicado_em=publicado,
            extra={
                "pasta": registro.get("pasta"),
                "projectTokenKey": registro.get("projectTokenKey"),
            },
        )
