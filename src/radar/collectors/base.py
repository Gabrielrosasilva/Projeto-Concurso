"""Contrato que todo coletor cumpre.

Para somar uma fonte (diario oficial, site de banca), crie um arquivo nesta
pasta com uma classe que herda de Coletor e implementa coletar(). Nada fora
desta pasta precisa saber de onde o dado veio.

A classe base cuida sozinha das tres boas maneiras de quem raspa site alheio:
identificar-se no User-Agent, respeitar o robots.txt e esperar entre uma
requisicao e outra.
"""
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
            leitor = RobotFileParser()
            leitor.set_url(f"{partes.scheme}://{host}/robots.txt")
            try:
                leitor.read()
            except Exception as erro:
                # Sem robots.txt legivel o padrao da web e "pode acessar".
                log.debug("robots.txt de %s indisponivel (%s)", host, erro)
                leitor = None
            self._robots[host] = leitor

        leitor = self._robots[host]
        if leitor is None:
            return True
        return leitor.can_fetch(config.USER_AGENT, url)

    def get(self, url: str) -> requests.Response:
        """Busca uma URL respeitando robots.txt e o atraso entre requisicoes."""
        if not self._robots_permite(url):
            raise ColetorBloqueadoPeloRobots(url)

        self._esperar_a_vez(urlsplit(url).netloc)
        resposta = self.http.get(url, timeout=config.TIMEOUT_REQUISICAO)
        resposta.raise_for_status()
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
