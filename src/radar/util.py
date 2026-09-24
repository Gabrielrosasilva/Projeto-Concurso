"""Funcoes pequenas usadas em mais de um lugar."""
import re
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


# Uso "5.200" para cinco mil e duzentos, mas tambem posso digitar "5200.50"
# com o ponto decimal. O ponto e ambiguo, entao a regra e olhar o formato:
# ponto seguido de exatamente tres digitos, sem virgula na frase, e milhar.
SO_MILHAR = re.compile(r"^\d{1,3}(\.\d{3})+$")


def converter_valor(texto: str | None) -> float | None:
    """Le um valor em reais do jeito que a pessoa digitou.

    Aceita "5200", "R$ 5.200", "5.200,50" e "5200.50". Texto que nao vira
    numero devolve None, em vez de estourar - quem esta digitando errou, e
    isso nao pode derrubar a pagina.
    """
    if not texto:
        return None

    limpo = texto.strip().replace("R$", "").replace(" ", "").replace(" ", "")
    if not limpo:
        return None

    if "," in limpo:                       # virgula decidiu: ela e o decimal
        limpo = limpo.replace(".", "").replace(",", ".")
    elif SO_MILHAR.match(limpo):           # "5.200" e "1.234.567"
        limpo = limpo.replace(".", "")

    try:
        valor = float(limpo)
    except ValueError:
        return None
    return valor if valor >= 0 else None


def porta_ocupada(host: str, porta: int) -> bool:
    """Alguem ja esta escutando nesse endereco?

    Perguntar antes de subir o servidor permite explicar o problema em uma
    linha, em vez de deixar o uvicorn estourar com o erro 10048 do Windows,
    que nao diz o que fazer.
    """
    import socket

    # host 0.0.0.0 significa "todas as interfaces"; para TESTAR, vale o local
    alvo = "127.0.0.1" if host in ("0.0.0.0", "") else host

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tomada:
        tomada.settimeout(0.4)
        return tomada.connect_ex((alvo, porta)) == 0


def primeira_porta_livre(host: str, inicio: int, tentativas: int = 20) -> int | None:
    """A primeira porta livre a partir de `inicio`."""
    for porta in range(inicio, inicio + tentativas):
        if not porta_ocupada(host, porta):
            return porta
    return None


# A FEPESE monta o titulo colando campos do sistema dela, e as vezes sem
# separador nenhum: "... - Concurso PublicoConcurso Publico - Edital 001/2019",
# "Prefeitura Municipal de FlorianopolisSecretaria Municipal de Educacao".
#
# So duas palavras LONGAS coladas contam. A exigencia de tamanho dos dois lados
# e o que protege nome proprio escrito em CamelCase - IcaraPrev, ManausPrev,
# RioSaude, AgSUS sao 4 casos reais do feed, e nenhum deles pode ser separado.
CAMPOS_GRUDADOS = re.compile(r"([a-zà-ÿ]{4,})([A-ZÀ-Þ][a-zà-ÿ]{4,})")

# O mesmo travessao que o proprio titulo ja usa entre os campos.
SEPARADOR = " \u2013 "


def separar_campos_grudados(titulo: str | None) -> str:
    """O titulo como ele se le, com separador onde a fonte esqueceu.

    So para EXIBIR: o titulo gravado no banco continua o que a fonte mandou -
    e ele que casa com o que ja foi coletado, e mexer nele mudaria a
    classificacao e a marca de alvo sem eu pedir.
    """
    return CAMPOS_GRUDADOS.sub(rf"\1{SEPARADOR}\2", titulo or "")
