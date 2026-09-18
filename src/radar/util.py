"""Funcoes pequenas usadas em mais de um lugar."""
from datetime import datetime, timezone
from functools import cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

NOME_DO_FUSO = "America/Sao_Paulo"


@cache
def fuso_local() -> ZoneInfo:
    """O fuso de Florianopolis, carregado na primeira vez que alguem pede.

    Nao fica em constante de modulo de proposito. Como constante, um fuso que
    nao carrega derruba o `import` inteiro, e ai TODO comando da CLI morre -
    ate os que nem mostram data. Foi exatamente o que aconteceu no Windows,
    que nao tem base de fusos no sistema (por isso o pacote tzdata).
    """
    try:
        return ZoneInfo(NOME_DO_FUSO)
    except ZoneInfoNotFoundError as erro:
        raise RuntimeError(
            f"Nao achei o fuso {NOME_DO_FUSO}. Instale a base de fusos com:\n"
            f"    pip install tzdata"
        ) from erro


def para_local(quando: datetime | None) -> datetime | None:
    """Converte para o horario de Florianopolis. Tudo e gravado em UTC."""
    if quando is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return quando.astimezone(fuso_local())


def formatar_data(quando: datetime | None, vazio: str = "--") -> str:
    local = para_local(quando)
    return local.strftime("%d/%m/%Y") if local else vazio


def dias_ate(quando: datetime | None) -> int | None:
    """Quantos dias faltam para essa data. Negativo quer dizer que ja passou."""
    if quando is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return (quando - datetime.now(timezone.utc)).days
