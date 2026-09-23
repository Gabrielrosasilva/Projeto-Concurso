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

from radar import alvo as alvos
from radar import config
from radar.models import Concurso, agora
from radar.util import formatar_data

log = logging.getLogger(__name__)

API = "https://api.telegram.org"

# O Telegram pede no maximo uma mensagem por segundo para o mesmo chat.
PAUSA_ENTRE_MENSAGENS = 1.0

EMOJI_DO_ANEL = {
    "nucleo": "\U0001F7E2",      # verde: e aqui do lado
    "proximo": "\U0001F7E1",     # amarelo: da para ir de carro
    "estadual": "\U0001F7E3",    # roxo: concurso do estado, e eu presto onde for
    "indefinida": "\U0001F535",  # azul: ainda nao sei, depende do edital
}

# O alvo principal abre a mensagem com sirene. E o unico aviso que eu nao
# posso deixar passar batido na tela cheia de notificacao do celular.
SIRENE = "\U0001F6A8"


def _url(metodo: str) -> str:
    """Monta a URL da API. NUNCA logue o retorno: ele contem o token."""
    return f"{API}/bot{config.telegram_token()}/{metodo}"


def formatar(concurso: Concurso) -> str:
    """Monta a mensagem de um concurso, em HTML do Telegram.

    O link da fonte vai sempre junto, em linha propria: sem ele o aviso obriga
    a abrir o computador para descobrir do que se trata.
    """
    emoji = EMOJI_DO_ANEL.get(concurso.relevancia, "\U000026AA")
    if concurso.alvo == alvos.PRINCIPAL:
        # A sirene vem na frente do emoji do anel, e nao no lugar dele: o
        # anel continua sendo informacao util mesmo quando nao decide nada.
        emoji = f"{SIRENE} {emoji}"

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

    # O motivo do alvo vem antes do motivo do anel: quando os dois existem, e
    # o cargo que explica por que a mensagem chegou.
    motivos = [m for m in (concurso.motivo_alvo, concurso.motivo_relevancia) if m]
    if motivos:
        linhas.append(f"\n<i>{html.escape(' '.join(motivos))}</i>")

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


def enviar_varios(textos: list[str]) -> list[bool]:
    """Manda uma mensagem por vez, respeitando o limite do Telegram.

    Devolve UMA resposta por texto, na ordem, e nao a contagem de quantas
    sairam. A diferenca aparece quando falha uma do meio: com a contagem, quem
    chama marcava como avisadas as N primeiras: a que falhou ficava marcada
    como enviada, e a ultima - que saiu - voltava amanha.
    """
    saiu = []
    for indice, texto in enumerate(textos):
        if indice:
            time.sleep(PAUSA_ENTRE_MENSAGENS)
        saiu.append(enviar(texto))
    return saiu


# Como cada mudanca de favorito abre a mensagem. O emoji e o rotulo dizem, na
# primeira linha, o que mudou - e o que decide se vale abrir o celular agora.
AVISO_DO_EVENTO = {
    "edital_publicado": ("\U0001F4C4", "Edital publicado"),
    "edital_retificado": ("\U0000270F", "Edital retificado"),
    "inscricoes_abertas": ("\U0001F7E2", "Inscricoes abertas"),
    "inscricoes_encerradas": ("\U0001F534", "Inscricoes encerradas"),
    "prova_marcada": ("\U0001F4C5", "Prova marcada"),
}


def formatar_evento(evento, concurso) -> str:
    """A mensagem de uma mudanca num concurso que eu acompanho.

    A estrela vem sempre: ela e o que separa este aviso do aviso de concurso
    novo. Este aqui e sobre algo que EU escolhi seguir, e por isso ele passa
    por filtro nenhum.
    """
    emoji, rotulo = AVISO_DO_EVENTO.get(evento.tipo, ("\U000026AA", evento.tipo))

    linhas = [
        f"{emoji} <b>{rotulo}</b> \u2605",
        html.escape(concurso.titulo),
        f"\n<i>{html.escape(evento.descricao)}</i>",
    ]

    if concurso.inscricoes_ate:
        faltam = (concurso.inscricoes_ate - agora()).days
        if faltam >= 0:
            linhas.append(
                f"Inscricao ate {formatar_data(concurso.inscricoes_ate)}"
                f" \u00b7 faltam {faltam}d"
            )

    # O link do evento aponta para o que mudou - o PDF retificado, por exemplo.
    # Sem ele, vale a pagina do concurso.
    linhas.append(f"\n{evento.link or concurso.url}")
    return "\n".join(linhas)


def formatar_retificacao(retificacao) -> str:
    """A mensagem de um edital que mudou.

    Curta de proposito: o que importa e eu abrir o edital e ver o que mudou.
    Dizer QUANTO mudou seria mentira - o sha256 so diz que mudou.
    """
    return (
        "<b>Edital retificado</b>\n"
        f"{retificacao.titulo}\n\n"
        f"Arquivo: {retificacao.arquivo}\n"
        "Retificacao muda prazo, vaga e requisito. Vale reler.\n\n"
        f"{retificacao.url}"
    )