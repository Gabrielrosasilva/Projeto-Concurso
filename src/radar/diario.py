"""O que saiu no diario oficial do municipio, pela API do Querido Diario.

Para que serve, e e o motivo de existir: o diario traz o **ato oficial**, e o
ato vem antes do edital. Quando a prefeitura contrata a banca - por licitacao
ou dispensa -, isso sai no diario tipicamente 2 a 4 meses antes de o edital
existir. E o sinal mais valioso do radar, porque da tempo de comecar a estudar
o padrao da banca.

Duas coisas que voce precisa saber antes de confiar nesta fonte:

**Ela cobre um municipio meu, e nao 35.** Medido na API: dos 35 municipios de
config/regioes.yml, so Florianopolis tem diario coletado - sao 4.255 edicoes
desde 2020. Sao Jose, Palhoca, Biguacu, Brusque, Blumenau e os demais dao zero.
Florianopolis e a capital e o centro do meu recorte, entao a fonte vale; mas
achar que ela cobre a regiao seria engano.

**O robots.txt de la proibe /api.** A decisao de usar mesmo assim foi minha, e
esta registrada: e a interface de maquina de um projeto de dados abertos, o
endereco e publico e documentado, e o uso aqui e de leitura, com atraso entre
requisicoes e User-Agent identificado. Por isso este arquivo NAO usa a classe
`Coletor` com robots ligado - ele desliga a checagem de proposito, e so para
este host.
"""
import logging
import time
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta

import requests

from radar import config

log = logging.getLogger(__name__)


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))

API = "https://queridodiario.ok.org.br/api"

# O que indica que o municipio esta MEXENDO num concurso, e nao so citando um.
# "concurso publico" sozinho aparece em ata de sessao, em nome de rua e em
# recurso administrativo; estes termos aparecem no ato.
TERMOS_DE_ATO = (
    "edital de concurso publico",
    "abertura de concurso publico",
    "homologacao do concurso",
    "contratacao de banca",
    "banca examinadora",
    "realizacao de concurso publico",
)

# Quanto tempo para tras vale procurar. O sinal util e recente: ato de 2019 nao
# muda o que eu estudo hoje.
DIAS_PARA_TRAS = 180

PAUSA_ENTRE_BUSCAS = 0.5


@dataclass
class Achado:
    """Uma edicao do diario que fala de concurso."""

    municipio: str
    data: str
    url: str
    termo: str
    trecho: str
    edicao: str | None = None


def _sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers["User-Agent"] = config.USER_AGENT
    return sessao


@dataclass
class Cidade:
    """Um municipio como o Querido Diario o conhece."""

    nome: str
    uf: str
    territorio: str
    desde: str | None = None

    @property
    def tem_diario(self) -> bool:
        """Conhecer o municipio nao e ter diario dele.

        A API lista os 5.570 municipios do pais, mas so alguns tem edicao
        coletada. Sem esta distincao, o comando gastaria seis requisicoes por
        municipio para receber zero.
        """
        return bool(self.desde)


def cidades(uf: str = "SC", sessao=None) -> list[Cidade]:
    """Os municipios daquela UF, com o codigo que a API usa.

    A lista inteira vem numa requisicao so (5.570 municipios, ~700 KB) e e
    filtrada aqui. Duas tentativas anteriores nao funcionaram e vale registrar:
    o parametro `state_code` e ignorado pela API, e a busca por `city_name` NAO
    ignora acento - procurar "Florianopolis" como esta no meu YAML devolvia
    lista vazia para a capital.
    """
    sessao = sessao or _sessao()
    try:
        resposta = sessao.get(
            f"{API}/cities", params={"state_code": uf},
            timeout=config.TIMEOUT_REQUISICAO,
        )
        resposta.raise_for_status()
    except Exception as erro:  # noqa: BLE001 - API fora do ar e rotina
        log.warning("nao consegui a lista de municipios (%s)", type(erro).__name__)
        return []

    achadas = []
    for cidade in (resposta.json() or {}).get("cities") or []:
        if (cidade.get("state_code") or "").upper() != uf.upper():
            continue
        achadas.append(Cidade(
            nome=cidade.get("territory_name") or "",
            uf=uf.upper(),
            territorio=cidade.get("territory_id") or "",
            desde=cidade.get("availability_date") or None,
        ))
    return achadas


def com_diario(nomes: list[str], uf: str = "SC", sessao=None) -> list[Cidade]:
    """Dos municipios que eu pedi, os que tem diario coletado.

    Medido: dos 35 municipios de config/regioes.yml, so Florianopolis tem.
    """
    procurados = {_sem_acento(n).lower().strip() for n in nomes}
    return [
        cidade for cidade in cidades(uf, sessao)
        if cidade.tem_diario and _sem_acento(cidade.nome).lower() in procurados
    ]


def buscar(
    territorio_id: str,
    municipio: str,
    desde: date | None = None,
    termos: tuple[str, ...] = TERMOS_DE_ATO,
    por_termo: int = 5,
    sessao=None,
) -> list[Achado]:
    """As edicoes recentes que trazem ato de concurso, uma busca por termo.

    Uma busca por termo, e nao um "OU" gigante, porque assim da para dizer QUAL
    termo trouxe cada achado - e o termo e o que me diz se aquilo e abertura,
    homologacao ou contratacao de banca.
    """
    # Sem territorio a API busca no Brasil inteiro. Na primeira versao isso
    # aconteceu calado e trouxe diario de Sergipe como se fosse daqui.
    if not territorio_id:
        log.warning("busca no diario sem territorio: ignorada (%s)", municipio)
        return []

    sessao = sessao or _sessao()
    desde = desde or (date.today() - timedelta(days=DIAS_PARA_TRAS))
    achados: dict[str, Achado] = {}

    for indice, termo in enumerate(termos):
        if indice:
            time.sleep(PAUSA_ENTRE_BUSCAS)
        try:
            resposta = sessao.get(
                f"{API}/gazettes",
                params={
                    "territory_ids": territorio_id,
                    "querystring": f'"{termo}"',
                    "published_since": desde.isoformat(),
                    "size": por_termo,
                    "sort_by": "descending_date",
                },
                timeout=config.TIMEOUT_REQUISICAO,
            )
            resposta.raise_for_status()
        except Exception as erro:  # noqa: BLE001 - API fora do ar e rotina
            log.warning("busca por %r falhou (%s)", termo, type(erro).__name__)
            continue

        for edicao in (resposta.json() or {}).get("gazettes") or []:
            url = edicao.get("url")
            if not url or url in achados:
                continue
            trechos = edicao.get("excerpts") or []
            achados[url] = Achado(
                municipio=edicao.get("territory_name") or municipio,
                data=edicao.get("date") or "",
                url=url,
                termo=termo,
                trecho=" ".join((trechos[0] if trechos else "").split())[:400],
                edicao=edicao.get("edition"),
            )

    return sorted(achados.values(), key=lambda a: a.data, reverse=True)
