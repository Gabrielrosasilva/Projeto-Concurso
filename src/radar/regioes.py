"""Os tres aneis de distancia, lidos de config/regioes.yml.

Editar o YAML basta: nenhum municipio fica escrito no codigo. O arquivo e
lido uma vez e guardado em memoria.
"""
import unicodedata
from functools import cache
from pathlib import Path

import yaml

from radar import config

NUCLEO, PROXIMO, REMOTO, INDEFINIDA = "nucleo", "proximo", "remoto", "indefinida"


def normalizar(nome: str) -> str:
    """Tira acento, caixa e espaco sobrando, para comparar nome de municipio.

    "Florianopolis", "Florianópolis" e "FLORIANOPOLIS" viram a mesma coisa.
    """
    sem_acento = unicodedata.normalize("NFKD", nome or "")
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


@cache
def _mapa() -> dict[str, str]:
    """{municipio normalizado: anel}. Lido do YAML uma unica vez."""
    arquivo = config.diretorio_config() / "regioes.yml"
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}

    mapa: dict[str, str] = {}
    for anel in (NUCLEO, PROXIMO):
        for municipio in dados.get(anel) or []:
            mapa[normalizar(municipio)] = anel
    return mapa


def recarregar() -> None:
    """Esquece o que foi lido. Usado pelos testes e se voce editar o YAML."""
    _mapa.cache_clear()


def anel_de(municipio: str | None) -> str | None:
    """Em qual anel esse municipio esta? None se nao estiver em nenhum.

    A comparacao e por nome INTEIRO, de proposito. "Sao Jose do Cerrito" nao
    pode virar "Sao Jose": o primeiro fica na serra, a ~3h de Florianopolis,
    e o segundo e vizinho de porta. Comparar por pedaco do nome erraria feio.
    """
    if not municipio:
        return None
    return _mapa().get(normalizar(municipio))


def municipios(anel: str) -> list[str]:
    return sorted(m for m, a in _mapa().items() if a == anel)
