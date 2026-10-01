"""Onde o radar conta questao, acerto e erro. O UNICO lugar.

Toda tela e todo comando que mostra "quantas fiz, quantas acertei" pede o
numero aqui. Antes, a tela Hoje, a de Semanas e a de Minhas materias faziam a
conta cada uma do seu jeito, e foi assim que o 28/09 mostrou "31 questoes, 13
acertos, 8 erros" - uma linha que nao fecha e nao dizia por que.

A regra, valendo para qualquer recorte e qualquer periodo:

    questoes = acertos + erros + sem acerto anotado + treino de IA

- **acerto e erro** saem de questao real: a resposta conferida pelo radar
  contra o gabarito, ou o "fiz N, acertei M" que eu anotei numa faixa ou num
  estudo extra (que vem do Qconcursos);
- **sem acerto anotado** e "fiz 15 e nao anotei quantas acertei": conta no
  volume, e nunca vira zero acerto;
- **treino de IA** e resposta a questao gerada: conta no volume, porque o
  tempo foi gasto, e o acerto dela e um SEGUNDO numero, nunca somado ao das
  reais (CLAUDE.md: questao gerada treina, nao mede).

Os recortes tem nome fixo, e cada tela escreve o que mostra (decisao 4 da
Etapa 0): *medido no radar*, *anotado*, *treino de IA* e *total*.

E ha duas contagens, com nome diferente porque respondem perguntas
diferentes:

- **respostas** - o volume do dia e da semana. A mesma questao respondida em
  duas rodadas sao duas respostas: eu fiz as duas;
- **questoes** - o acumulado, pela ULTIMA resposta de cada questao (decisao de
  26/09): o que eu sei hoje, e nao quantas vezes errei no caminho.

Fica de fora de tudo: questao de rodada que eu nao respondi (sem
`respondida_em`). O dia e o de Florianopolis, e nao o de UTC.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select

from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import EstadoDoDia, QuestaoDeProva, QuestaoGerada, RespostaDeSimulado
from radar.servico import cronograma as diario
from radar.servico import extra as estudo_extra
from radar.util import fuso_local, para_local

#: O nome de cada recorte, como a tela escreve.
RECORTES = {
    "radar": "medido no radar",
    "anotado": "anotado",
    "treino_ia": "treino de IA",
    "total": "total",
}

FAIXA = "faixa"
EXTRA = "extra"
RADAR = "radar"


class ContaInconsistente(ValueError):
    """Uma linha gravada diz mais acertos do que questoes.

    A conta antiga escondia isso com um `max(..., 0)` nos erros. Aqui ela
    para e diz onde: numero que nao fecha tem que ser corrigido, e nao
    arredondado para parecer certo.
    """


@dataclass
class Numeros:
    """Os quatro estados de um conjunto de questoes, e os minutos.

    O total nao e guardado: ele E a soma dos estados. Por isso nao ha como a
    linha "N questoes = acertos + erros + ..." deixar de fechar.
    """
    acertos: int = 0
    erros: int = 0
    #: Feitas, mas sem acerto anotado: volume sim, acerto nao.
    sem_resultado: int = 0
    #: Respostas a questao escrita por IA: volume sim, acerto nunca.
    ia: int = 0
    #: O acerto nessas de IA - o segundo numero, que nunca entra no primeiro.
    ia_acertos: int = 0
    minutos: int = 0

    @property
    def questoes(self) -> int:
        return self.acertos + self.erros + self.sem_resultado + self.ia

    @property
    def medidas(self) -> int:
        """As que contam para o acerto: questao real, com resultado."""
        return self.acertos + self.erros

    @property
    def porcentagem(self) -> int | None:
        return round(100 * self.acertos / self.medidas) if self.medidas else None

    @property
    def porcentagem_ia(self) -> int | None:
        return round(100 * self.ia_acertos / self.ia) if self.ia else None

    @property
    def vazio(self) -> bool:
        return not (self.questoes or self.minutos)

    def __add__(self, outro: "Numeros") -> "Numeros":
        return Numeros(
            acertos=self.acertos + outro.acertos,
            erros=self.erros + outro.erros,
            sem_resultado=self.sem_resultado + outro.sem_resultado,
            ia=self.ia + outro.ia,
            ia_acertos=self.ia_acertos + outro.ia_acertos,
            minutos=self.minutos + outro.minutos,
        )

    def anotar(self, questoes: int | None, acertos: int | None,
               minutos: int | None = 0, onde: str = "") -> None:
        """Soma uma linha que eu digitei: faixa do plano ou estudo extra."""
        questoes = questoes or 0
        self.minutos += minutos or 0
        if acertos is None:
            self.sem_resultado += questoes
            return
        if acertos > questoes:
            raise ContaInconsistente(
                f"{onde or 'Uma linha anotada'}: {acertos} acertos em "
                f"{questoes} questões. Corrija a anotação."
            )
        self.acertos += acertos
        self.erros += questoes - acertos

    def responder(self, acertou: bool, gerada: bool = False) -> None:
        """Soma uma resposta dada dentro do radar."""
        if gerada:
            self.ia += 1
            self.ia_acertos += 1 if acertou else 0
        elif acertou:
            self.acertos += 1
        else:
            self.erros += 1


def frase_da_conta(numeros: Numeros) -> str:
    """"31 questões = 13 acertos + 8 erros + 10 de treino de IA".

    Uma funcao so para a tela e o terminal escreverem a mesma linha. So
    aparece o estado que existe: "+ 0 sem acerto anotado" e ruido.
    """
    partes = [f"{numeros.acertos} acertos", f"{numeros.erros} erros"]
    if numeros.sem_resultado:
        partes.append(f"{numeros.sem_resultado} sem acerto anotado")
    if numeros.ia:
        partes.append(f"{numeros.ia} de treino de IA")
    return f"{numeros.questoes} questões = " + " + ".join(partes)


def frase_da_ia(numeros: Numeros) -> str | None:
    """O segundo numero: "treino de IA: 7 de 10 (70%), fora do acerto"."""
    if not numeros.ia:
        return None
    return (f"treino de IA: {numeros.ia_acertos} de {numeros.ia} "
            f"({numeros.porcentagem_ia}%), fora do acerto")


# --- de onde vem cada linha ----------------------------------------------------

@dataclass
class Lancamento:
    """Uma linha que conta: uma faixa marcada, um estudo extra ou uma resposta.

    Todas as telas somam a MESMA lista. Mesmo periodo, mesma lista, mesmo
    numero - e a garantia vem daqui, e nao de cada tela tomar cuidado.
    """
    data: date
    origem: str                       # faixa | extra | radar
    questoes: int = 0
    acertos: int | None = None
    minutos: int = 0
    consulta: bool = False
    gerada: bool = False
    materia: str | None = None
    assunto: str | None = None
    #: Para a mensagem de erro dizer onde a conta nao fecha.
    descricao: str = ""


def janela_do_dia(inicio: date, fim: date | None = None) -> tuple[datetime, datetime]:
    """Do comeco de `inicio` ao fim de `fim`, no dia de Florianopolis, em UTC.

    Sem isto, um simulado respondido as 22h daqui (1h do dia seguinte em UTC)
    cairia no dia errado.
    """
    fim = fim or inicio
    comeco = datetime.combine(inicio, time.min, tzinfo=fuso_local())
    termino = datetime.combine(fim + timedelta(days=1), time.min, tzinfo=fuso_local())
    return comeco.astimezone(timezone.utc), termino.astimezone(timezone.utc)


def dia_para_contar(plano, data: date, estado: EstadoDoDia | None,
                    metas: dict | None = None):
    """O dia do plano cujas faixas valem em `data`.

    Com o Plano B ativo, sao as faixas DELE - era aqui que a tela Hoje e a de
    Semanas divergiam: a Hoje contava o Plano B, e a Semanas montava o dia
    normal e nao achava check nenhum.
    """
    nivel = diario.nivel_do_dia(plano, data, metas)
    if nivel is None:
        return None
    if (estado is not None and estado.plano_b and plano.plano_b is not None
            and estado.plano_b in plano.plano_b.opcoes):
        return plano_de_estudo.montar_plano_b(plano, data, estado.plano_b,
                                              nivel.efetivo)
    return plano_de_estudo.montar_dia(plano, data, nivel.efetivo)


def lancamentos(inicio: date, fim: date, plano=None) -> list[Lancamento]:
    """Tudo o que conta entre as duas datas, inclusive.

    As faixas so existem em dia do plano; o extra e a resposta no radar podem
    estar em qualquer dia. Resposta a questao que saiu do acervo continua
    contando no volume e no acerto do dia - ela foi respondida -, so fica sem
    materia.
    """
    plano = plano or plano_de_estudo.carregar()
    criar_tabelas()
    linhas: list[Lancamento] = []

    # --- as faixas do plano que eu marquei --------------------------------
    with sessao() as s:
        estados = {e.data: e for e in s.scalars(
            select(EstadoDoDia).where(EstadoDoDia.data >= inicio,
                                      EstadoDoDia.data <= fim))}
    metas = diario.metas_do_plano(plano) if estados else {}
    for data in sorted(estados):
        if plano.dia(data) is None:
            continue
        estado = estados[data]
        montado = dia_para_contar(plano, data, estado, metas)
        for feita in diario.valores_das_faixas(montado, estado).values():
            linhas.append(Lancamento(
                data=data, origem=FAIXA,
                questoes=feita.questoes or 0, acertos=feita.acertos,
                minutos=feita.minutos or 0, consulta=feita.consulta,
                materia=feita.materia, assunto=feita.assunto,
                descricao=f"{data:%d/%m/%Y}, faixa {feita.titulo!r}",
            ))

    # --- o estudo extra ----------------------------------------------------
    for extra in estudo_extra.entre(inicio, fim):
        linhas.append(Lancamento(
            data=extra.data, origem=EXTRA,
            questoes=extra.questoes or 0, acertos=extra.acertos,
            minutos=extra.minutos or 0, consulta=bool(extra.consulta),
            materia=extra.materia, assunto=extra.assunto,
            descricao=f"{extra.data:%d/%m/%Y}, estudo extra #{extra.id}",
        ))

    # --- o que eu respondi dentro do radar ------------------------------------
    comeco, termino = janela_do_dia(inicio, fim)
    with sessao() as s:
        respostas = list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.respondida_em.is_not(None))
            .where(RespostaDeSimulado.respondida_em >= comeco)
            .where(RespostaDeSimulado.respondida_em < termino)
            .order_by(RespostaDeSimulado.respondida_em, RespostaDeSimulado.id)
        ))
        reais = {q.id: q for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.id.in_(
                [r.questao_id for r in respostas if not r.gerada] or [0])))}
        de_ia = {q.id: q for q in s.scalars(
            select(QuestaoGerada).where(QuestaoGerada.id.in_(
                [r.questao_id for r in respostas if r.gerada] or [0])))}

    for resposta in respostas:
        questao = (de_ia if resposta.gerada else reais).get(resposta.questao_id)
        linhas.append(Lancamento(
            data=para_local(resposta.respondida_em).date(), origem=RADAR,
            questoes=1, acertos=1 if resposta.acertou else 0,
            # O simulado do radar e sempre sem consulta: nao ha lei aberta ali.
            consulta=False, gerada=bool(resposta.gerada),
            materia=getattr(questao, "materia", None),
            assunto=getattr(questao, "assunto", None),
        ))
    return linhas


# --- a soma ---------------------------------------------------------------------

@dataclass
class Conta:
    """Um periodo somado, separado pelos recortes de nome fixo."""
    #: O que eu anotei nas faixas do plano.
    faixas: Numeros = field(default_factory=Numeros)
    #: O que eu anotei no estudo extra.
    extra: Numeros = field(default_factory=Numeros)
    #: Questao real respondida no radar: medida contra o gabarito.
    radar: Numeros = field(default_factory=Numeros)
    #: Questao de IA respondida no radar: so `ia` e `ia_acertos`.
    treino_ia: Numeros = field(default_factory=Numeros)
    #: O que vale para comparar com a meta: tudo menos o feito com consulta.
    sem_consulta: Numeros = field(default_factory=Numeros)

    def somar(self, linha: Lancamento) -> None:
        if linha.origem == RADAR:
            acertou = bool(linha.acertos)
            if linha.gerada:
                self.treino_ia.responder(acertou, gerada=True)
                return
            self.radar.responder(acertou)
            self.sem_consulta.responder(acertou)
            return
        destino = self.faixas if linha.origem == FAIXA else self.extra
        destino.anotar(linha.questoes, linha.acertos, linha.minutos, linha.descricao)
        if not linha.consulta:
            self.sem_consulta.anotar(linha.questoes, linha.acertos, 0, linha.descricao)

    @property
    def anotado(self) -> Numeros:
        """O que eu digitei: faixas e extras. Vem do Qconcursos."""
        return self.faixas + self.extra

    @property
    def total(self) -> Numeros:
        return self.anotado + self.radar + self.treino_ia

    @property
    def minutos(self) -> int:
        return self.faixas.minutos + self.extra.minutos

    @property
    def vazio(self) -> bool:
        return self.total.vazio


def contar(linhas) -> Conta:
    conta = Conta()
    for linha in linhas:
        conta.somar(linha)
    return conta


def do_dia(data: date, plano=None) -> Conta:
    """A conta de um dia: o "Fiz hoje" da tela e do `radar hoje`."""
    return contar(lancamentos(data, data, plano))
