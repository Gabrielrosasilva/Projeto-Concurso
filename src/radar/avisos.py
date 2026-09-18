"""Avisos no Telegram.

Por que Telegram e nao WhatsApp: o WhatsApp oficial exige conta Meta Business,
um numero separado e template aprovado para mandar mensagem proativa - que e
exatamente o nosso caso. O nao oficial arrisca banir o numero pessoal.

Token e chat_id vem de variavel de ambiente, sempre. Nunca do codigo, nunca
do repositorio. Se nao estiverem configurados, o comando avisa e sai em paz:
coleta sem aviso e melhor que coleta quebrada.
"""
import html
import logging
import time

import requests

from radar import config
from radar.models import Concurso
from radar.util import formatar_data

log = logging.getLogger(__name__)

API = "https://api.telegram.org"

# O Telegram pede no maximo uma mensagem por segundo para o mesmo chat.
PAUSA_ENTRE_MENSAGENS = 1.0

EMOJI_DO_ANEL = {
    "nucleo": "\U0001F7E2",      # verde: e aqui do lado
    "proximo": "\U0001F7E1",     # amarelo: da para ir de carro
    "indefinida": "\U0001F535",  # azul: ainda nao sei, depende do edital
}


def _url(metodo: str) -> str:
    """Monta a URL da API. NUNCA logue o retorno: ele contem o token."""
    return f"{API}/bot{config.telegram_token()}/{metodo}"


def formatar(concurso: Concurso) -> str:
    """Monta a mensagem de um concurso, em HTML do Telegram.

    O link da fonte vai sempre junto, em linha propria: sem ele o aviso obriga
    a abrir o computador para descobrir do que se trata.
    """
    emoji = EMOJI_DO_ANEL.get(concurso.relevancia, "\U000026AA")
    # escape: titulo vem de site de terceiro e pode ter <, > ou &, que
    # quebrariam o HTML da mensagem
    linhas = [f"{emoji} <b>{html.escape(concurso.titulo)}</b>"]

    detalhes = []
    if concurso.salario:
        detalhes.append(f"R$ {concurso.salario:,.0f}".replace(",", "."))
    detalhes.append(concurso.relevancia)
    if concurso.tipo and concurso.tipo != "desconhecido":
        detalhes.append(concurso.tipo)
    linhas.append(" · ".join(detalhes))

    local = "/".join(p for p in (concurso.municipio, concurso.uf) if p)
    if local:
        linhas.append(html.escape(local))

    if concurso.publicado_em:
        linhas.append(f"Publicado em {formatar_data(concurso.publicado_em)}")

    if concurso.motivo_relevancia:
        linhas.append(f"\n<i>{html.escape(concurso.motivo_relevancia)}</i>")

    # O link fica fora de tag: o Telegram ja o torna clicavel sozinho.
    linhas.append(f"\n{concurso.url}")
    return "\n".join(linhas)


def enviar(texto: str) -> bool:
    """Manda uma mensagem. Devolve se deu certo.

    Erro aqui nunca sobe: perder um aviso e chato, derrubar a coleta diaria
    por causa do Telegram fora do ar seria pior.
    """
    if not config.telegram_configurado():
        log.warning("Telegram nao configurado: mensagem nao enviada.")
        return False

    try:
        resposta = requests.post(
            _url("sendMessage"),
            json={
                "chat_id": config.telegram_chat_id(),
                "text": texto,
                "parse_mode": "HTML",
                # sem previa: ela ocupa meia tela e some o resto do aviso
                "disable_web_page_preview": True,
            },
            timeout=config.TIMEOUT_REQUISICAO,
        )
        resposta.raise_for_status()
        return True
    except Exception as erro:  # noqa: BLE001 - de proposito: loga e segue
        # A mensagem de erro do requests pode trazer a URL, e a URL tem o
        # token dentro. Por isso so o tipo do erro vai para o log.
        log.warning("Falha ao enviar aviso no Telegram (%s)", type(erro).__name__)
        return False


def enviar_varios(textos: list[str]) -> int:
    """Manda uma mensagem por vez, respeitando o limite do Telegram."""
    enviadas = 0
    for indice, texto in enumerate(textos):
        if indice:
            time.sleep(PAUSA_ENTRE_MENSAGENS)
        if enviar(texto):
            enviadas += 1
    return enviadas
