"""Os concursos que eu escolhi seguir, com o que aconteceu e o que fazer.

Isto substitui o mural lateral. O mural mostrava titulo, salario e prazo num
cartao apertado, visivel em qualquer aba - o que resolvia "nao me deixe perder
isso de vista", mas nao resolvia "e agora, o que eu faco?".

Aqui cada favorito ganha espaco: a linha do tempo inteira, a contagem de dias
ate o prazo, e **a proxima acao**. A proxima acao e o unico campo interpretado
deste arquivo, e ela e sempre derivada de fato - da situacao gravada e do
prazo lido no edital. Quando nem isso da para afirmar, ela diz que nao sabe.

Regra que vale aqui como vale em `foco.py`: **nunca inventar**. O favorito e
escolha minha, e uma tela que chuta sobre ele e pior do que uma tela vazia.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select

from radar import eventos as linha_do_tempo
from radar.db import criar_tabelas, sessao
from radar.models import Concurso, Evento, agora

log = logging.getLogger(__name__)

# A partir de quantos dias o prazo vira urgencia na tela. Uma semana e o que
# sobra para separar documento e pagar a taxa sem correria.
DIAS_DE_URGENCIA = 7


@dataclass
class ProximaAcao:
    """O que fazer com este concurso agora, e por que."""

    texto: str
    #: True quando ha prazo correndo contra mim.
    urgente: bool = False
    #: False quando nao da para afirmar nada - a tela mostra "nao sei ainda".
    sei: bool = True


@dataclass
class Bloco:
    """Um favorito, com tudo que a aba mostra dele."""

    concurso: Concurso
    eventos: list[Evento] = field(default_factory=list)
    acao: ProximaAcao | None = None
    #: Dias ate o fim da inscricao. Negativo = ja fechou. None = nao sei.
    dias_ate_fechar: int | None = None

    @property
    def fechou(self) -> bool:
        return self.dias_ate_fechar is not None and self.dias_ate_fechar < 0


def _dias_ate(quando: datetime | None) -> int | None:
    """Quantos dias faltam. None quando nao ha data conhecida."""
    if quando is None:
        return None
    return (quando - agora()).days


def proxima_acao(concurso: Concurso, dias: int | None) -> ProximaAcao:
    """O que fazer com este concurso agora.

    A ordem das perguntas e a ordem em que elas mandam: prazo correndo vence
    qualquer outra coisa, porque e a unica que tem hora para acabar.

    Nada aqui e adivinhado. Cada resposta sai de um campo que alguem gravou -
    a situacao, que vem da fonte ou das datas, e o prazo, que vem do edital
    lido. Situacao que nao diz nada vira "nao sei ainda", e nao um palpite.
    """
    situacao = concurso.situacao or "desconhecida"

    if situacao == "inscricoes_abertas":
        if dias is None:
            return ProximaAcao(
                "Inscrever-se. O prazo esta aberto, mas a data-limite eu nao sei"
                " - confira na pagina do concurso.",
                urgente=True,
            )
        if dias < 0:
            # A situacao diz aberta e a data ja passou: quem manda e a data.
            return ProximaAcao(
                "Conferir na fonte: o prazo que eu tenho ja venceu, mas o "
                "registro ainda diz aberto."
            )
        if dias == 0:
            return ProximaAcao("Inscrever-se HOJE: o prazo fecha hoje.", urgente=True)
        return ProximaAcao(
            f"Inscrever-se: faltam {dias} dia(s).", urgente=dias <= DIAS_DE_URGENCIA
        )

    if situacao == "edital_publicado":
        return ProximaAcao(
            "Ler o edital: conferir requisito, taxa e data de inscricao."
        )

    if situacao == "banca_definida":
        return ProximaAcao(
            "Estudar o padrao da banca. O edital costuma sair 2 a 4 meses "
            "depois de a banca ser contratada."
        )

    if situacao in ("prevista", "autorizado"):
        return ProximaAcao(
            "So acompanhar por enquanto: ainda nao ha edital nem banca."
        )

    if situacao == "encerrado":
        return ProximaAcao(
            "Inscricao encerrada. Acompanhar convocacao e prazo de validade."
        )

    return ProximaAcao("nao sei ainda", sei=False)


def blocos(limite: int = 50) -> list[Bloco]:
    """Um bloco por favorito, do que fecha primeiro para o que nao tem prazo.

    A ordem e a mesma da aba de favoritos que ja existia: o que tem prazo
    correndo vem antes, e quem nao tem data conhecida vai para o fim - some
    seria pior, porque e justamente o que falta descobrir.
    """
    criar_tabelas()

    from radar.servico import FAVORITO

    with sessao() as s:
        favoritos = list(s.scalars(
            select(Concurso)
            .where(Concurso.interesse == FAVORITO)
            .order_by(
                Concurso.inscricoes_ate.asc().nullslast(),
                Concurso.publicado_em.desc().nullslast(),
            )
            .limit(limite)
        ))

        montados = []
        for concurso in favoritos:
            dias = _dias_ate(concurso.inscricoes_ate)
            montados.append(Bloco(
                concurso=concurso,
                # Do mais novo para o mais velho: aqui eu quero saber o que
                # mudou por ultimo, ao contrario de `radar eventos`, que conta
                # a historia desde o comeco.
                eventos=list(reversed(linha_do_tempo.do_concurso(s, concurso.url))),
                acao=proxima_acao(concurso, dias),
                dias_ate_fechar=dias,
            ))

    return montados


# --- o que vira mensagem no Telegram ----------------------------------------

def eventos_a_avisar(limite: int = 20) -> list[tuple[Evento, Concurso]]:
    """Eventos importantes de concurso FAVORITO que ainda nao viraram mensagem.

    Duas condicoes, e as duas importam. Favorito, porque aviso sobre concurso
    que eu nao escolhi seguir e ruido. Importante, porque nem toda mudanca
    muda o que eu tenho que fazer - "apareceu" e "de prevista para autorizado"
    ficam na linha do tempo, sem tocar o celular.
    """
    criar_tabelas()

    from radar.servico import FAVORITO

    with sessao() as s:
        linhas = s.execute(
            select(Evento, Concurso)
            .join(Concurso, Concurso.url == Evento.concurso_url)
            .where(Evento.avisado_em.is_(None))
            .where(Evento.tipo.in_(linha_do_tempo.EVENTOS_IMPORTANTES))
            .where(Concurso.interesse == FAVORITO)
            .order_by(Evento.data.asc(), Evento.id.asc())
            .limit(limite)
        ).all()

    return [(evento, concurso) for evento, concurso in linhas]


def marcar_avisados(ids: list[int]) -> int:
    """Fecha a fila: evento avisado nao vira mensagem de novo amanha."""
    if not ids:
        return 0

    momento = agora()
    with sessao() as s:
        eventos = list(s.scalars(select(Evento).where(Evento.id.in_(ids))))
        for evento in eventos:
            evento.avisado_em = momento
        return len(eventos)
