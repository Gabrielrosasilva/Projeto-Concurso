"""Funcoes pequenas usadas em mais de um lugar."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Tudo e gravado em UTC no banco; so na hora de mostrar vira horario daqui.
FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")


def para_local(quando: datetime | None) -> datetime | None:
    if quando is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return quando.astimezone(FUSO_LOCAL)


def formatar_data(quando: datetime | None, vazio: str = "--") -> str:
    local = para_local(quando)
    return local.strftime("%d/%m/%Y") if local else vazio
