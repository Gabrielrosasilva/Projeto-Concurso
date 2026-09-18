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
    nomes_originais.cache_clear()


def anel_de(municipio: str | None) -> str | None:
    """Em qual anel esse municipio esta? None se nao estiver em nenhum.

    A comparacao e por nome INTEIRO, de proposito. "Sao Jose do Cerrito" nao
    pode virar "Sao Jose": o primeiro fica na serra, a ~3h de Florianopolis,
    e o segundo e vizinho de porta. Comparar por pedaco do nome erraria feio.
    """
    if not municipio:
        return None
    return _mapa().get(normalizar(municipio))


@cache
def nomes_originais() -> dict[str, str]:
    """{normalizado: como esta escrito no YAML}, do mais longo para o mais curto.

    A ordem importa: procurando "sao jose" antes de "sao jose do cerrito" num
    texto, o nome curto casaria dentro do longo e mandaria a serra para a
    Grande Florianopolis.
    """
    arquivo = config.diretorio_config() / "regioes.yml"
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}

    mapa: dict[str, str] = {}
    for anel in (NUCLEO, PROXIMO):
        for municipio in dados.get(anel) or []:
            mapa[normalizar(municipio)] = municipio
    return dict(sorted(mapa.items(), key=lambda kv: -len(kv[0])))


def nome_canonico(municipio: str | None) -> str | None:
    """A grafia de config/regioes.yml para um municipio conhecido.

    Cada fonte escreve de um jeito: a FEPESE manda "Palhoca" e o feed manda
    "Palhoca" com cedilha, e o banco acabava com os dois como se fossem cidades
    diferentes. Qualquer conta por municipio saia errada - e a previsao de
    abertura e toda por municipio.

    Municipio que nao esta no YAML volta como veio: e de fora de SC, e inventar
    grafia para ele seria pior que manter a da fonte.
    """
    if not municipio:
        return None
    return nomes_originais().get(normalizar(municipio), municipio)


def municipios(anel: str) -> list[str]:
    return sorted(m for m, a in _mapa().items() if a == anel)
