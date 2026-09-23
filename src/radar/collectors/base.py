"""Contrato que todo coletor cumpre.

Para somar uma fonte (diario oficial, site de banca), crie um arquivo nesta
pasta com uma classe que herda de Coletor e implementa coletar(). Nada fora
desta pasta precisa saber de onde o dado veio.

A classe base cuida sozinha das tres boas maneiras de quem raspa site alheio:
identificar-se no User-Agent, respeitar o robots.txt e esperar entre uma
requisicao e outra.
"""
import codecs
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from radar import config

log = logging.getLogger(__name__)


class ColetorBloqueadoPeloRobots(RuntimeError):
    """O robots.txt do site proibe buscar esta URL. Nao insista."""


# --- codificacao da pagina ---------------------------------------------------
#
# Codificacao que aceita qualquer byte e por isso nunca da erro de leitura. E
# o palpite preguicoso de servidor mal configurado: ele declara isto no
# cabecalho e manda outra coisa, porque nada estoura.
CODIFICACOES_QUE_NUNCA_FALHAM = (
    "iso88591", "latin1", "latin_1", "cp1252", "windows1252",
)


def _byte_solto_como_latin1(erro: UnicodeDecodeError) -> tuple[str, int]:
    """O byte que nao forma UTF-8 valido e lido como latin-1, sozinho."""
    return erro.object[erro.start:erro.end].decode("latin-1"), erro.end


codecs.register_error("radar_latin1", _byte_solto_como_latin1)


def corrigir_codificacao(resposta: requests.Response) -> None:
    """Escolhe a codificacao olhando os BYTES, e nao so o cabecalho.

    O hotsite de 2016 da FEPESE declara `charset=iso-8859-1` e serve os dois
    no mesmo arquivo: "PROVISORIO" com O acentuado em latin-1 e "Seguranca"
    com C cedilha em UTF-8. Lido so como latin-1, o cargo virava "Agente de
    SeguranAga Socioeducativo" - e isso ia para o manifesto versionado e para
    o banco de questoes, nao so para a tela.

    Nao existe UMA codificacao certa para um arquivo assim, mas existe uma
    leitura certa POR BYTE: o que forma UTF-8 valido e UTF-8, e o byte que
    sobra e latin-1. Isso e determinado, e nao chute.

    So vale quando o cabecalho declarou latin-1 ou parente, que e onde ha
    ambiguidade para resolver: latin-1 aceita qualquer byte, entao ele nunca
    reclama nem quando esta errado. Servidor que diz UTF-8 fica como esta.

    Conferido nos tres hotsites de Policia Penal: o de 2013 e o de 2019 sao
    latin-1 honestos e saem IDENTICOS ao que saiam antes. So o de 2016 muda.
    """
    declarado = (resposta.encoding or "").lower().replace("-", "")
    if declarado not in CODIFICACOES_QUE_NUNCA_FALHAM:
        return

    texto = resposta.content.decode("utf-8", errors="radar_latin1")

    # Reescreve o corpo ja em UTF-8 e diz isso ao requests. E o unico jeito de
    # o `.text` - que todo coletor usa - enxergar o texto certo: ele decodifica
    # `.content` usando `.encoding`, e nao aceita tratador de erro proprio.
    # `_content` e atributo interno do requests, e esta e a razao de mexer nele.
    resposta._content = texto.encode("utf-8")
    resposta.encoding = "utf-8"


@dataclass
class ItemColetado:
    """Um concurso do jeito cru que a fonte entregou, antes de virar linha."""

    titulo: str
    url: str
    resumo: str | None = None
    orgao: str | None = None
    municipio: str | None = None
    uf: str | None = None
    banca: str | None = None
    situacao: str = "desconhecida"
    # Preenchido so pela fonte que tem certeza (a FEPESE publica os concursos
    # num tipo de post proprio). Nulo deixa o classificador decidir pelo texto.
    tipo: str | None = None
    escolaridade: str | None = None
    publicado_em: datetime | None = None
    extra: dict = field(default_factory=dict)


class Coletor(ABC):
    #: nome curto, gravado na coluna `fonte`
    nome: str = "base"

    #: se False, o coletor ignora o robots.txt (use so em feed proprio/publico)
    respeitar_robots: bool = True

    def __init__(self) -> None:
        self.http = requests.Session()
        self.http.headers.update({"User-Agent": config.USER_AGENT})
        # ultimo acesso por host: e por host que o atraso faz sentido, nao por
        # coletor. Dois coletores no mesmo site continuam sendo dois visitantes.
        self._ultimo_acesso: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    # --- boas maneiras ------------------------------------------------------

    def _esperar_a_vez(self, host: str) -> None:
        anterior = self._ultimo_acesso.get(host)
        if anterior is not None:
            faltam = config.ATRASO_ENTRE_REQUISICOES - (time.monotonic() - anterior)
            if faltam > 0:
                time.sleep(faltam)
        self._ultimo_acesso[host] = time.monotonic()

    def _robots_permite(self, url: str) -> bool:
        if not self.respeitar_robots:
            return True

        partes = urlsplit(url)
        host = partes.netloc

        if host not in self._robots:
            self._robots[host] = self._ler_robots(f"{partes.scheme}://{host}")

        leitor = self._robots[host]
        if leitor is None:
            return True
        return leitor.can_fetch(config.USER_AGENT, url)

    def _ler_robots(self, origem: str) -> RobotFileParser | None:
        """O robots.txt do site, ou None quando nao ha regra que valha.

        A busca e feita aqui, e nao pelo RobotFileParser.read(), por causa de
        um detalhe que custou uma tarde: o leitor do Python trata resposta 403
        como "proibido tudo". So que o 403 costuma significar o contrario -
        que o arquivo nao existe. O CDN da IESES e um balde de arquivos que
        responde 403 a qualquer caminho inexistente, inclusive /robots.txt, e
        com isso o acervo inteiro dela ficava bloqueado por um arquivo que
        nunca existiu.

        A regra do padrao atual (RFC 9309) e a que vale aqui: resposta 4xx
        quer dizer que nao ha robots.txt, e o site pode ser acessado. So o
        conteudo que eu consegui LER de fato vira restricao.
        """
        endereco = f"{origem}/robots.txt"
        try:
            resposta = self.http.get(endereco, timeout=config.TIMEOUT_REQUISICAO)
        except Exception as erro:  # noqa: BLE001 - site fora do ar e rotina
            log.debug("robots.txt de %s indisponivel (%s)", origem, erro)
            return None

        if resposta.status_code != 200 or not resposta.text.strip():
            log.debug("sem robots.txt em %s (HTTP %s)", origem, resposta.status_code)
            return None

        leitor = RobotFileParser()
        leitor.set_url(endereco)
        leitor.parse(resposta.text.splitlines())
        return leitor

    def get(self, url: str) -> requests.Response:
        """Busca uma URL respeitando robots.txt e o atraso entre requisicoes."""
        if not self._robots_permite(url):
            raise ColetorBloqueadoPeloRobots(url)

        self._esperar_a_vez(urlsplit(url).netloc)
        resposta = self.http.get(url, timeout=config.TIMEOUT_REQUISICAO)
        resposta.raise_for_status()
        corrigir_codificacao(resposta)
        return resposta

    # --- o que cada fonte precisa implementar -------------------------------

    @abstractmethod
    def coletar(self) -> list[ItemColetado]:
        """Busca na fonte e devolve os itens encontrados."""
        raise NotImplementedError


class Buscador(Coletor):
    """Busca uma pagina avulsa, herdando robots.txt, User-Agent e o atraso.

    Existe porque ler a pagina de um post nao e "coletar uma fonte": e ir
    atras de detalhe de algo que ja esta no banco. Mas as boas maneiras sao
    as mesmas, e elas moram no Coletor.
    """

    nome = "buscador"

    def coletar(self) -> list[ItemColetado]:
        return []
