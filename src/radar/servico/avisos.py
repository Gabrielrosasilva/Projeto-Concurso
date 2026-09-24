"""Quem merece virar mensagem no Telegram, e quando.

A mensagem em si - o texto, o HTML, o envio - e do `radar.avisos`, que aqui
entra como `mensagens`. Este arquivo responde a outra pergunta, que e de
regra e nao de formato: **o que sai do banco para o meu celular**.

Sao dois avisos diferentes, e por isso duas funcoes:

- `avisar()` responde "apareceu algo que pode me interessar?", e por isso
  filtra por distancia e respeita o teto do dia;
- `avisar_favoritos()` responde "mudou algo no que eu JA sigo?", e para essa
  pergunta filtro nenhum faz sentido - eu marquei a estrela, eu quero saber.
"""
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select

from radar import acompanhando as meus_favoritos
from radar import alvo as alvos
from radar import avisos as mensagens
from radar import config
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, agora


# O que merece uma mensagem no celular. `indefinida` entra de proposito: e o
# concurso federal ou sem UF, que PODE aplicar prova em Florianopolis. Melhor
# receber dois avisos a toa do que perder o unico que interessava. `estadual`
# entra pelo motivo oposto - e concurso do estado, onde mora a Policia Penal
# SC, e para esse eu vou onde a prova for.
RELEVANCIA_AVISO = ("nucleo", "proximo", "estadual", "indefinida")

# Teto de mensagens por coleta. Nao e economia: e protecao. Se uma regra de
# classificacao quebrar, o estrago fica em 10 mensagens e um alerta, em vez de
# 200 notificacoes as 6h da manha.
LIMITE_DE_AVISOS = 10


@dataclass
class ResultadoAviso:
    enviados: int = 0
    pendentes: int = 0     # passaram no filtro mas ficaram fora do limite
    configurado: bool = True

    def __str__(self) -> str:
        if not self.configurado:
            return "Telegram nao configurado: nenhum aviso enviado."
        if not self.enviados and not self.pendentes:
            return "Nada novo para avisar."
        texto = f"{self.enviados} aviso(s) enviado(s)"
        if self.pendentes:
            texto += f", {self.pendentes} acima do limite"
        return texto


# Aviso e sobre NOVIDADE. Sem esta janela, ligar uma fonte nova enche a fila
# com o historico inteiro dela: a FEPESE entrou com 520 concursos, 464 deles ja
# encerrados, e o `radar avisar` seguinte mandaria mensagem sobre edital de
# anos atras mais o alerta de excesso, que soaria como erro de regra sem ser.
JANELA_DE_NOVIDADE_EM_DIAS = 30


def _e_novidade():
    """Condicao SQL de "isto merece uma mensagem no celular agora".

    Vale se foi publicado ha pouco, ou se a inscricao continua aberta - um
    edital de 40 dias atras com prazo em pe ainda e util. Nunca vale se ja
    encerrou. Sem data de publicacao entra, porque ai nao da para afirmar que
    e velho, e o teto de 10 mensagens segura o estrago.
    """
    recente = agora() - timedelta(days=JANELA_DE_NOVIDADE_EM_DIAS)
    return (Concurso.situacao != "encerrado") & (
        # a banca diz que da para se inscrever agora: isso basta, e a data de
        # publicacao nao importa. Foi assim que o concurso da Celesc quase
        # passou batido - aberto, mas publicado ha mais de 30 dias, e a FEPESE
        # nao informa prazo.
        (Concurso.situacao == "inscricoes_abertas")
        | Concurso.publicado_em.is_(None)
        | (Concurso.publicado_em >= recente)
        | (Concurso.inscricoes_ate >= agora())
    )


def _nao_avisados() -> list[Concurso]:
    """Concursos que interessam e que ainda nao viraram mensagem.

    Duas portas de entrada, e a segunda e a que importa. A primeira e a de
    sempre: concurso perto o bastante. A segunda e o alvo principal, que
    entra por fora - sem filtro de distancia, e valendo tambem para noticia.
    "Governo autoriza concurso da Policia Penal" nao e edital, nao tem
    municipio nenhum no titulo, e e exatamente o aviso que eu quero receber
    primeiro.

    A segunda porta e a mais larga das duas: ela vale para o cargo em
    QUALQUER estado (`principal_fora`), e nao so em SC. Um concurso de Policia
    Penal no Parana e prova que eu nao vou estudar - e continua sendo a
    noticia que eu quero na hora.

    A janela de novidade continua valendo para os dois: ela e o que impede
    que ligar uma fonte nova despeje o historico dela no meu celular.
    """
    perto = (Concurso.tipo != "noticia") & Concurso.relevancia.in_(RELEVANCIA_AVISO)

    consulta = (
        select(Concurso)
        .where(Concurso.avisado_em.is_(None))
        .where(perto | Concurso.alvo.in_(alvos.PRINCIPAIS))
        .where(_e_novidade())
        .order_by(Concurso.publicado_em.desc().nullslast())
    )
    with sessao() as s:
        return list(s.scalars(consulta))


def avisar(limite: int = LIMITE_DE_AVISOS) -> ResultadoAviso:
    """Manda no Telegram os concursos novos que interessam.

    Cada concurso vira uma mensagem e e marcado como avisado, para a coleta de
    amanha nao repetir o aviso de hoje.
    """
    criar_tabelas()

    if not config.telegram_configurado():
        return ResultadoAviso(configurado=False)

    candidatos = _nao_avisados()
    if not candidatos:
        return ResultadoAviso()

    # Quem eu escolhi a dedo nao disputa vaga com o resto. O teto existe para
    # segurar regra de classificacao quebrada, e estes sao os casos que eu nao
    # quero que ele segure: se sairem 30 avisos da Policia Penal no mesmo dia,
    # eu quero os 30.
    #
    # Sao dois furos, e eles vem de lugares diferentes do config/alvo.yml: o
    # cargo do alvo principal, em qualquer estado, e a lista `de_olho` - hoje
    # a Guarda Municipal de Florianopolis e a de Balneario Camboriu.
    def _fura_o_teto(c: Concurso) -> bool:
        return c.alvo in alvos.PRINCIPAIS or bool(c.alvo_prioritario)

    principais = [c for c in candidatos if _fura_o_teto(c)]
    demais = [c for c in candidatos if not _fura_o_teto(c)]

    escolhidos = principais + demais[:limite]
    sobraram = len(demais) - min(len(demais), limite)

    saiu = mensagens.enviar_varios([mensagens.formatar(c) for c in escolhidos])
    enviados = sum(saiu)

    # So marca como avisado o que realmente saiu - uma a uma, e nao as N
    # primeiras: com o Telegram falhando no meio, a que falhou ficava marcada
    # como enviada e a seguinte voltava amanha.
    urls = [c.url for c, ok in zip(escolhidos, saiu) if ok]
    if urls:
        with sessao() as s:
            for concurso in s.scalars(select(Concurso).where(Concurso.url.in_(urls))):
                concurso.avisado_em = agora()

    if sobraram:
        mensagens.enviar(
            f"⚠️ Mais {sobraram} concurso(s) passaram no filtro nesta "
            f"coleta.\n\nIsso costuma indicar erro de regra de "
            f"classificacao. Veja todos com <code>radar listar --todos</code>."
        )

    return ResultadoAviso(enviados=enviados, pendentes=sobraram)


def avisar_favoritos(limite: int = LIMITE_DE_AVISOS) -> ResultadoAviso:
    """Manda no Telegram as mudancas importantes dos concursos que eu sigo.

    E um aviso diferente do outro, e por isso vive numa funcao propria. O
    `avisar()` responde "apareceu algo que pode me interessar?" e por isso
    passa por filtro de distancia e por teto. Este aqui responde "mudou algo
    no que eu JA escolhi seguir?" - e para essa pergunta filtro nenhum faz
    sentido: eu marquei a estrela, eu quero saber.

    O teto continua valendo, pelo mesmo motivo de sempre: protecao contra
    regra quebrada virar 200 notificacoes. Mas ele nunca deveria ser
    alcancado aqui - sao poucos favoritos, e poucos eventos por favorito.
    """
    criar_tabelas()

    if not config.telegram_configurado():
        return ResultadoAviso(configurado=False)

    # A fila inteira, e nao `limite + 1`: com o teto de seguranca cortando, eu
    # quero saber QUANTOS ficaram de fora - um numero que so existe se eu
    # tiver contado todos. Sao poucos favoritos; a lista nao cresce.
    pendentes = meus_favoritos.eventos_a_avisar()
    if not pendentes:
        return ResultadoAviso()

    escolhidos = pendentes[:limite]
    sobraram = len(pendentes) - len(escolhidos)

    saiu = mensagens.enviar_varios(
        [mensagens.formatar_evento(evento, concurso) for evento, concurso in escolhidos]
    )
    enviados = sum(saiu)

    # So marca o que realmente saiu: Telegram fora do ar deixa a fila em pe
    # para a proxima coleta, como ja acontece com o aviso de concurso novo.
    meus_favoritos.marcar_avisados(
        [evento.id for (evento, _), ok in zip(escolhidos, saiu) if ok]
    )

    return ResultadoAviso(enviados=enviados, pendentes=sobraram)
