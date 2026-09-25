"""A home: tres blocos cheios e duas faixas finas.

A especificacao pede cinco blocos. Com pouco treino, dois deles - a evolucao
e as novidades - nasceriam vazios ou quase, e bloco vazio ocupando o mesmo
espaco de um cheio e ruido. Por isso ficam tres blocos (o alvo, o que estudar
agora, o que revisar) e duas faixas finas embaixo.

Regra de toda a home: **bloco sem dado nao aparece vazio, convida a acao** -
"responda 20 questoes para eu medir sua evolucao", e nao um zero.

A prioridade do "o que estudar agora" segue a formula da especificacao, sem
IA e explicavel na tela:

    prioridade = peso da materia no edital x (1 - meu acerto) x fator de tempo

  * o PESO e o do quadro do edital, e nao o do acervo: e o que a proxima prova
    promete cobrar;
  * com menos de `onde_estudar.MINIMO_NA_MATERIA` na materia, o acerto e "desconhecido"
    e a materia entra como "ainda nao treinada", valendo o peso inteiro - o
    maximo que ela poderia valer, a mesma regra do "Onde estudar primeiro";
  * o FATOR DE TEMPO e o de `onde_estudar.fator_de_tempo`: 1 no dia da
    ultima resposta na materia, 2 depois de um mes sem ela. **Sem treino ele
    e neutro (1)** - nao ha ultima revisao para contar dias - e o cartao diz
    "ainda nao treinada".
"""
from dataclasses import dataclass, field

from datetime import date, datetime, timezone

from sqlalchemy import func, select

from radar import foco, onde_estudar
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado
from radar.regioes import normalizar
from radar.servico import espacada
from radar.servico import simulado as treino
from radar.util import para_local

# O minimo de respostas e o de `onde_estudar.MINIMO_NA_MATERIA`: um so, para
# a home, o Meu foco e o Onde estudar primeiro nunca discordarem.

# Quantas materias o bloco mostra. Tres, como a especificacao pede.
QUANTAS_PRIORIDADES = 3

# Abaixo disto de acerto, a materia e "fraca" no bloco de revisar.
ACERTO_FRACO = 60


@dataclass
class Prioridade:
    materia: str
    questoes_no_edital: int
    peso: float                       # em % da prova
    respondidas: int = 0
    acerto: float | None = None       # None = ainda nao treinada
    valor: float = 0.0                # a conta da formula, para ordenar
    fator: float = 1.0                # o fator de tempo; 1 sem treino
    dias_sem_revisar: int | None = None

    @property
    def treinada(self) -> bool:
        return self.acerto is not None

    @property
    def porque(self) -> str:
        """A frase do cartao, montada dos numeros."""
        base = f"{self.questoes_no_edital} questões no edital"
        if not self.treinada:
            if self.respondidas:
                return (f"{base} · amostra pequena ({self.respondidas} de "
                        f"{onde_estudar.MINIMO_NA_MATERIA})")
            return f"{base} · ainda não treinada"
        texto = (f"{base} · {self.acerto:.0f}% de acerto em "
                 f"{self.respondidas} questões")
        if self.dias_sem_revisar:
            texto += (f" · {self.dias_sem_revisar} dia(s) sem revisar "
                      f"(×{self.fator:.1f})".replace(".", ","))
        return texto


@dataclass
class Revisar:
    erradas: int = 0
    #: [(materia, acerto %, respondidas)] com acerto abaixo de ACERTO_FRACO
    #: e base de pelo menos onde_estudar.MINIMO_NA_MATERIA.
    materias_fracas: list = field(default_factory=list)
    respondidas: int = 0


@dataclass
class Home:
    painel: foco.Painel
    prioridades: list[Prioridade] = field(default_factory=list)
    revisar: Revisar = field(default_factory=Revisar)
    #: As revisoes espacadas que vencem hoje ou ja venceram, e a proxima.
    revisoes_de_hoje: list = field(default_factory=list)
    proxima_revisao: object = None
    evolucao: treino.Evolucao = field(default_factory=treino.Evolucao)
    #: O sinal mais recente do alvo, para a faixa de novidades. None = nada.
    novidade: object = None
    #: Quantas questoes da minha prova existem para treinar - o botao so
    #: aparece com elas.
    questoes_para_treinar: int = 0


def _ultima_resposta_por_materia() -> dict[str, date]:
    """{materia normalizada: dia da ultima resposta minha em questao real}."""
    with sessao() as s:
        linhas = s.execute(
            select(QuestaoDeProva.materia, func.max(RespostaDeSimulado.respondida_em))
            .join(RespostaDeSimulado, RespostaDeSimulado.questao_id == QuestaoDeProva.id)
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .where(RespostaDeSimulado.gerada.is_(False))
            .group_by(QuestaoDeProva.materia)
        ).all()
    ultimas: dict[str, date] = {}
    for materia, quando in linhas:
        if materia and quando:
            # O max() do SQLite pode devolver texto em vez de data.
            if isinstance(quando, str):
                quando = datetime.fromisoformat(quando)
                if quando.tzinfo is None:
                    quando = quando.replace(tzinfo=timezone.utc)
            dia = para_local(quando).date()
            chave = normalizar(materia)
            ultimas[chave] = max(dia, ultimas.get(chave, dia))
    return ultimas


def prioridades(painel: foco.Painel, hoje: date | None = None) -> list[Prioridade]:
    """As materias do edital, da que mais vale estudar agora a que menos vale."""
    total = painel.total_do_edital
    if not painel.materias_do_edital or not total:
        return []

    hoje = hoje or date.today()
    ultimas = _ultima_resposta_por_materia()
    medido = {normalizar(d.materia): d for d in treino.desempenho() if d.respondidas}
    lista = []
    for m in painel.materias_do_edital:
        peso = m.questoes / total * 100
        d = medido.get(normalizar(m.nome))
        respondidas = d.respondidas if d else 0
        if respondidas >= onde_estudar.MINIMO_NA_MATERIA:
            acerto = d.porcentagem
            ultima = ultimas.get(normalizar(m.nome))
            fator = onde_estudar.fator_de_tempo(ultima, hoje)
            dias = (hoje - ultima).days if ultima else None
            valor = peso * (1 - acerto / 100) * fator
        else:
            # Sem treino: acerto desconhecido e fator NEUTRO. A materia vale
            # o peso inteiro - o maximo que poderia valer.
            acerto, fator, dias = None, 1.0, None
            valor = peso
        lista.append(Prioridade(
            materia=m.nome, questoes_no_edital=m.questoes, peso=peso,
            respondidas=respondidas, acerto=acerto, valor=valor,
            fator=fator, dias_sem_revisar=dias,
        ))

    # Empate de valor: a de mais questoes primeiro - e a que decide a prova.
    lista.sort(key=lambda p: (-p.valor, -p.questoes_no_edital, p.materia))
    return lista[:QUANTAS_PRIORIDADES]


def _revisar() -> Revisar:
    desempenho = treino.desempenho()
    return Revisar(
        erradas=len(treino.questoes_erradas()),
        materias_fracas=[
            (d.materia, d.porcentagem, d.respondidas) for d in desempenho
            if d.respondidas >= onde_estudar.MINIMO_NA_MATERIA
            and d.porcentagem < ACERTO_FRACO
        ],
        respondidas=sum(d.respondidas for d in desempenho),
    )


def montar() -> Home:
    painel = foco.montar()
    return Home(
        painel=painel,
        prioridades=prioridades(painel),
        revisar=_revisar(),
        revisoes_de_hoje=espacada.pendentes(),
        proxima_revisao=next(
            (r for r in espacada.agenda() if not r.pendente(date.today())), None
        ),
        evolucao=treino.evolucao(),
        novidade=painel.sinais[0] if painel.sinais else None,
        questoes_para_treinar=painel.questoes_para_treinar,
    )
