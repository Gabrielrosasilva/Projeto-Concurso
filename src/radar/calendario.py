"""Exporta os prazos para o calendario, no formato .ics.

Por que existe: o prazo de inscricao e a unica coisa do radar que nao pode ser
vista tarde demais. O aviso do Telegram chega uma vez; o calendario do celular
lembra de novo na vespera.

O formato iCalendar e texto puro, entao nao entra biblioteca nova por causa
disto. A especificacao e a RFC 5545, e o pedaco dela que importa aqui cabe em
um arquivo: linhas `CHAVE:valor`, dobradas em 75 bytes, terminadas em CRLF.
"""
import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

PRODUTO = "-//Radar de Concursos//PT-BR"

# Quantos dias antes o calendario avisa. Dois, porque um dia antes ja e tarde
# para juntar documento e pagar boleto.
DIAS_DE_AVISO = 2

# Caracteres que tem significado no formato e precisam de barra invertida.
ESCAPES = ((chr(92), chr(92) * 2), (";", r"\;"), (",", r"\,"), ("\n", r"\n"))


@dataclass
class Evento:
    """Uma data do concurso que vai para o calendario."""

    identificador: str
    titulo: str
    quando: date
    descricao: str = ""
    url: str = ""


def _escapar(texto: str) -> str:
    for de, para in ESCAPES:
        texto = (texto or "").replace(de, para)
    return texto


def _dobrar(linha: str) -> list[str]:
    """Quebra a linha em 75 bytes, como o formato exige.

    A continuacao comeca com um espaco. Sem isto, um titulo longo de concurso
    faz o Google Agenda recusar o arquivo inteiro.
    """
    bruto = linha.encode("utf-8")
    if len(bruto) <= 75:
        return [linha]

    pedacos, atual = [], ""
    for caractere in linha:
        limite = 74 if pedacos else 75
        if len((atual + caractere).encode("utf-8")) > limite:
            pedacos.append(atual)
            atual = " " + caractere
        else:
            atual += caractere
    if atual:
        pedacos.append(atual)
    return pedacos


def _uid(identificador: str) -> str:
    """Identificador estavel do evento.

    O mesmo concurso precisa gerar o mesmo UID em toda exportacao: e assim que
    o calendario ATUALIZA o compromisso em vez de criar um duplicado quando o
    prazo e retificado.
    """
    digest = hashlib.sha256(identificador.encode("utf-8")).hexdigest()[:24]
    return f"{digest}@radar-de-concursos"


def montar(eventos: list[Evento], agora: datetime | None = None) -> str:
    """O arquivo .ics inteiro, pronto para salvar ou servir."""
    carimbo = (agora or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")

    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODUTO}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Radar de Concursos",
    ]

    for evento in eventos:
        dia = evento.quando.strftime("%Y%m%d")
        # Evento de dia inteiro: DTEND e o dia seguinte, por definicao do
        # formato. Com o mesmo dia nos dois, o compromisso some da agenda.
        fim = (evento.quando + timedelta(days=1)).strftime("%Y%m%d")

        linhas += [
            "BEGIN:VEVENT",
            f"UID:{_uid(evento.identificador)}",
            f"DTSTAMP:{carimbo}",
            f"DTSTART;VALUE=DATE:{dia}",
            f"DTEND;VALUE=DATE:{fim}",
            f"SUMMARY:{_escapar(evento.titulo)}",
        ]
        if evento.descricao:
            linhas.append(f"DESCRIPTION:{_escapar(evento.descricao)}")
        if evento.url:
            linhas.append(f"URL:{_escapar(evento.url)}")

        linhas += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"TRIGGER:-P{DIAS_DE_AVISO}D",
            f"DESCRIPTION:{_escapar(evento.titulo)}",
            "END:VALARM",
            "END:VEVENT",
        ]

    linhas.append("END:VCALENDAR")

    dobradas = [pedaco for linha in linhas for pedaco in _dobrar(linha)]
    return "\r\n".join(dobradas) + "\r\n"
