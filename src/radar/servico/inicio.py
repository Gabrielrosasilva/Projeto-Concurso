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
  * com menos de `MINIMO_DE_RESPOSTAS` na materia, o acerto e "desconhecido"
    e a materia entra como "ainda nao treinada", valendo o peso inteiro - o
    maximo que ela poderia valer, a mesma regra do "Onde estudar primeiro";
  * o FATOR DE TEMPO e 1 por enquanto: ele depende de saber quando eu revisei
    a materia pela ultima vez, e a revisao espacada e a ultima fase da
    especificacao. A tela diz isso, em vez de fingir que o fator existe.
"""
from dataclasses import dataclass, field

from radar import foco
from radar.regioes import normalizar
from radar.servico import simulado as treino

# A regra 5 da especificacao: abaixo disto, a taxa de acerto e desconhecida.
MINIMO_DE_RESPOSTAS = 5

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

    @property
    def treinada(self) -> bool:
        return self.acerto is not None

    @property
    def porque(self) -> str:
        """A frase do cartao, montada dos numeros."""
        base = f"{self.questoes_no_edital} questões no edital"
        if not self.treinada:
            quanto = (f", {self.respondidas} respondida(s)" if self.respondidas
                      else "")
            return f"{base} · ainda não treinada{quanto}"
        return (f"{base} · {self.acerto:.0f}% de acerto em "
                f"{self.respondidas} questões")


@dataclass
class Revisar:
    erradas: int = 0
    #: [(materia, acerto %, respondidas)] com acerto abaixo de ACERTO_FRACO
    #: e base de pelo menos MINIMO_DE_RESPOSTAS.
    materias_fracas: list = field(default_factory=list)
    respondidas: int = 0


@dataclass
class Home:
    painel: foco.Painel
    prioridades: list[Prioridade] = field(default_factory=list)
    revisar: Revisar = field(default_factory=Revisar)
    evolucao: treino.Evolucao = field(default_factory=treino.Evolucao)
    #: O sinal mais recente do alvo, para a faixa de novidades. None = nada.
    novidade: object = None
    #: Quantas questoes da minha prova existem para treinar - o botao so
    #: aparece com elas.
    questoes_para_treinar: int = 0


def prioridades(painel: foco.Painel) -> list[Prioridade]:
    """As materias do edital, da que mais vale estudar agora a que menos vale."""
    total = painel.total_do_edital
    if not painel.materias_do_edital or not total:
        return []

    medido = {normalizar(d.materia): d for d in treino.desempenho() if d.respondidas}
    lista = []
    for m in painel.materias_do_edital:
        peso = m.questoes / total * 100
        d = medido.get(normalizar(m.nome))
        respondidas = d.respondidas if d else 0
        if respondidas >= MINIMO_DE_RESPOSTAS:
            acerto = d.porcentagem
            valor = peso * (1 - acerto / 100)
        else:
            acerto = None
            valor = peso              # o maximo que ela poderia valer
        lista.append(Prioridade(
            materia=m.nome, questoes_no_edital=m.questoes, peso=peso,
            respondidas=respondidas, acerto=acerto, valor=valor,
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
            if d.respondidas >= MINIMO_DE_RESPOSTAS and d.porcentagem < ACERTO_FRACO
        ],
        respondidas=sum(d.respondidas for d in desempenho),
    )


def montar() -> Home:
    painel = foco.montar()
    return Home(
        painel=painel,
        prioridades=prioridades(painel),
        revisar=_revisar(),
        evolucao=treino.evolucao(),
        novidade=painel.sinais[0] if painel.sinais else None,
        questoes_para_treinar=painel.questoes_para_treinar,
    )
