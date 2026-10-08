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

from radar import amostra as regua
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import (
    EstadoDoDia,
    QuestaoDeProva,
    QuestaoGerada,
    RespostaDeSimulado,
    Simulado,
    agora,
)
from radar.questoes import chave_da_questao
from radar.servico import cronograma as diario
from radar.origem import AUTOMATICO, IA
from radar.servico import extra as estudo_extra
from radar.util import fuso_local, para_local

#: O nome de cada recorte, como a tela escreve.
RECORTES = {
    "radar": "medido no radar",
    "anotado": "anotado",
    "treino_ia": "treino de IA",
    "total": "total",
}

#: A origem de cada recorte, para o selo (Etapa 7A): o que eu fiz e conta do
#: sistema; o treino de IA leva o selo da IA, porque e resposta a questao que
#: a IA escreveu - e ela nunca pode parecer questao da banca.
ORIGEM_DO_RECORTE = {
    "radar": AUTOMATICO,
    "anotado": AUTOMATICO,
    "treino_ia": IA,
    "total": AUTOMATICO,
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
    #: A origem do selo: o sistema contou o que eu fiz.
    origem = AUTOMATICO

    acertos: int = 0
    erros: int = 0
    #: Feitas, mas sem acerto anotado: volume sim, acerto nao.
    sem_resultado: int = 0
    #: Respostas a questao escrita por IA: volume sim, acerto nunca.
    ia: int = 0
    #: O acerto nessas de IA - o segundo numero, que nunca entra no primeiro.
    ia_acertos: int = 0
    minutos: int = 0
    #: Respostas do radar marcadas "vou no chute" (decisao 142): ao lado das
    #: outras contas, nunca dentro - nao mudam acerto, erro nem total.
    chutes: int = 0

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
            chutes=self.chutes + outro.chutes,
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

    def responder(self, acertou: bool, gerada: bool = False,
                  chutou: bool = False) -> None:
        """Soma uma resposta dada dentro do radar."""
        self.chutes += 1 if chutou else 0
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
    partes = [_contado(numeros.acertos, "acerto", "acertos"),
              _contado(numeros.erros, "erro", "erros")]
    if numeros.sem_resultado:
        partes.append(f"{numeros.sem_resultado} sem acerto anotado")
    if numeros.ia:
        partes.append(f"{numeros.ia} de treino de IA")
    return _contado(numeros.questoes, "questão", "questões") + " = " + " + ".join(partes)


def _contado(n: int, um: str, varios: str) -> str:
    """"1 acerto", "2 acertos", "0 acertos": o plural que a frase pedia."""
    return f"{n} {um if n == 1 else varios}"


def frase_da_ia(numeros: Numeros) -> str | None:
    """O segundo numero: "Treino de IA no radar: 10 questões = 7 acertos + 3
    erros (70%), não entra no acerto".

    No mesmo molde da linha das reais, com os erros escritos: "7 de 10"
    deixava a conta dos erros para quem le. "No radar" porque e o unico lugar
    em que se responde questao gerada.
    """
    if not numeros.ia:
        return None
    erros = numeros.ia - numeros.ia_acertos
    return (f"Treino de IA no radar: {_contado(numeros.ia, 'questão', 'questões')} = "
            f"{_contado(numeros.ia_acertos, 'acerto', 'acertos')} + "
            f"{_contado(erros, 'erro', 'erros')} "
            f"({numeros.porcentagem_ia}%), não entra no acerto")


def frase_das_reais(numeros: Numeros) -> str:
    """A linha das questoes reais do dia (decisao 138): "Questões reais
    (Qconcursos e provas): 12 questões = 9 acertos + 3 erros".

    `numeros` e o `Conta.reais`: o anotado e o respondido no radar, sem o
    treino de IA - o "Fiz hoje" de antes somava os tres numa linha so, e o
    treino parecia questao feita (06/10).
    """
    rotulo = "Questões reais (Qconcursos e provas): "
    if not numeros.questoes:
        return rotulo + "nenhuma ainda"
    return rotulo + frase_da_conta(numeros)


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
    #: O no da arvore de conteudos, pelo caminho de nomes ("Direito Penal >
    #: Imputabilidade penal"). None quando o lancamento nao aponta para no
    #: nenhum: ele conta no dia e no desempenho por conteudo de nenhum no.
    #: E por aqui que o recorte "anotado" chega a arvore (Etapa 4).
    conteudo: str | None = None
    #: Para a mensagem de erro dizer onde a conta nao fecha.
    descricao: str = ""
    #: Foi uma REVISAO: faixa de revisao do plano, estudo extra de revisao, ou
    #: resposta numa rodada que revisa (`rodada_que_revisa`). Nao muda conta
    #: nenhuma; da a data da ultima revisao de cada no (decisao 79).
    revisao: bool = False
    #: A chave da questao REAL respondida no radar (enunciado + alternativas).
    #: A linha do radar nao tem `conteudo` - nao fui eu que escolhi o no -, e
    #: e por esta chave que ela chega a ele, pela classificacao da questao.
    chave: str | None = None
    #: O tipo da faixa no plano (teoria, questoes, revisao...) ou o "o que"
    #: do estudo extra (teoria, lei_seca...). Vazio no radar. E ele que diz
    #: se a linha deixa o no "estudado" (decisao 20).
    tipo: str = ""
    #: A faixa do plano, nas linhas de faixa. E por ela que a faixa sem
    #: `conteudo` chega ao que cobre - so para a situacao e as datas do no,
    #: nunca para o acerto (servico/estudo.py, decisao 81).
    faixa: object = None


def rodada_que_revisa(filtros: dict | None) -> bool:
    """A rodada do radar e uma revisao? A revisao espacada grava `revisao`;
    o "Refazer as erradas" e a revisao do sabado gravam `erros`."""
    filtros = filtros or {}
    return bool(filtros.get("revisao") or filtros.get("erros"))


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
                conteudo=feita.conteudo,
                descricao=f"{data:%d/%m/%Y}, faixa {feita.titulo!r}",
                revisao=feita.tipo in plano_de_estudo.TIPOS_DE_REVISAO,
                tipo=feita.tipo,
                faixa=getattr(montado, feita.bloco)[feita.indice],
            ))

    # --- o estudo extra ----------------------------------------------------
    for extra in estudo_extra.entre(inicio, fim):
        linhas.append(Lancamento(
            data=extra.data, origem=EXTRA,
            questoes=extra.questoes or 0, acertos=extra.acertos,
            minutos=extra.minutos or 0, consulta=bool(extra.consulta),
            materia=extra.materia, assunto=extra.assunto,
            conteudo=extra.conteudo,
            descricao=f"{extra.data:%d/%m/%Y}, estudo extra #{extra.id}",
            revisao=extra.o_que == "revisao",
            tipo=extra.o_que,
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
        que_revisam = {sid for sid, filtros in s.execute(
            select(Simulado.id, Simulado.filtros).where(Simulado.id.in_(
                {r.simulado_id for r in respostas} or {0})))
            if rodada_que_revisa(filtros)}

    for resposta in respostas:
        questao = (de_ia if resposta.gerada else reais).get(resposta.questao_id)
        real = questao is not None and not resposta.gerada
        linhas.append(Lancamento(
            data=para_local(resposta.respondida_em).date(), origem=RADAR,
            questoes=1, acertos=1 if resposta.acertou else 0,
            # O simulado do radar e sempre sem consulta: nao ha lei aberta ali.
            consulta=False, gerada=bool(resposta.gerada),
            materia=getattr(questao, "materia", None),
            assunto=getattr(questao, "assunto", None),
            revisao=resposta.simulado_id in que_revisam,
            chave=(chave_da_questao(questao.enunciado, questao.alternativas)
                   if real else None),
        ))
    return linhas


# --- a soma ---------------------------------------------------------------------

@dataclass
class Conta:
    """Um periodo somado, separado pelos recortes de nome fixo."""
    #: A origem de cada recorte, para a tela desenhar o selo de cada linha.
    origens = ORIGEM_DO_RECORTE

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
    def reais(self) -> Numeros:
        """As questoes reais: o anotado (Qconcursos, provas) e o respondido no
        radar. O treino de IA fica de fora - ele tem a linha dele."""
        return self.anotado + self.radar

    @property
    def total(self) -> Numeros:
        return self.reais + self.treino_ia

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


def no_radar_por_faixa(data: date) -> dict[tuple[str, int, str], Numeros]:
    """O que eu respondi no radar em rodada aberta por uma faixa do dia, pela
    chave (bloco, indice, titulo) - a mesma que reconhece o check da faixa.

    A rodada guarda de onde veio: `faixa` (a das reais de Portugues e a que
    mede, decisoes 67 e 107) ou `da_faixa` (a de geradas aberta pelo botao da
    faixa). Essas respostas ja contam sozinhas no "Fiz hoje"; anota-las de
    novo no "fiz X, acertei Y" conta a mesma questao duas vezes - foi o
    05/10. E isto que a faixa mostra para avisar.
    """
    criar_tabelas()
    dia = data.isoformat()
    por_faixa: dict[tuple[str, int, str], Numeros] = {}
    with sessao() as s:
        rodadas = {}
        for simulado_id, filtros in s.execute(select(Simulado.id, Simulado.filtros)):
            origem = (filtros or {}).get("faixa") or (filtros or {}).get("da_faixa")
            if isinstance(origem, dict) and origem.get("data") == dia:
                rodadas[simulado_id] = (origem.get("bloco"), origem.get("indice"),
                                        origem.get("titulo"))
        if not rodadas:
            return {}
        respostas = s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id.in_(rodadas))
            .where(RespostaDeSimulado.respondida_em.is_not(None))
        )
        for resposta in respostas:
            numeros = por_faixa.setdefault(rodadas[resposta.simulado_id], Numeros())
            numeros.responder(bool(resposta.acertou), gerada=bool(resposta.gerada),
                              chutou=bool(resposta.chutou))
    return por_faixa


# --- questoes: o acumulado, pela ultima resposta -----------------------------------
#
# O Meu foco, o Onde estudar e a home respondem "quanto eu sei hoje", e no
# recorte *medido no radar* (decisao 7 da Etapa 0: o anotado do Qconcursos
# entra nelas so na Etapa 4). Aqui cada questao conta UMA vez, pela minha
# resposta mais recente: refazer a mesma questao 4 vezes nao vale 4, e refazer
# questao ja decorada inflava o acerto sem eu ter aprendido nada. Nenhuma
# tentativa e apagada - elas seguem no banco, e contam como RESPOSTAS no
# volume do dia e na evolucao.

# A janela da variacao. E a da especificacao: "a variacao nos ultimos 30 dias".
DIAS_DA_EVOLUCAO = 30


@dataclass
class DesempenhoDaMateria:
    materia: str
    #: No acumulado, QUESTOES diferentes; numa rodada, as respostas dela.
    respondidas: int = 0
    acertos: int = 0
    #: Acerto em questao real e conta do sistema; o das geradas leva o selo
    #: da IA (`desempenho_das_geradas`), e os dois nunca se somam.
    origem: str = AUTOMATICO

    @property
    def porcentagem(self) -> float:
        return (self.acertos / self.respondidas * 100) if self.respondidas else 0.0


def placar(respostas) -> tuple[int, int]:
    """(respondidas, acertos) de uma lista de respostas. Nao respondida fica fora."""
    dadas = [r for r in respostas if r.escolhida is not None]
    return len(dadas), sum(1 for r in dadas if r.acertou)


def respostas_reais(s) -> list[RespostaDeSimulado]:
    """Toda resposta que eu dei a questao real, na ordem em que dei.

    O historico inteiro, e nao a ultima de cada questao: "quando eu vi isto
    pela primeira vez" se responde com a primeira resposta (o 1-7-30 do
    `servico/estudo.py`, decisao 85).
    """
    return list(s.scalars(
        select(RespostaDeSimulado)
        .where(RespostaDeSimulado.escolhida.is_not(None))
        .where(RespostaDeSimulado.gerada.is_(False))
        .order_by(RespostaDeSimulado.respondida_em, RespostaDeSimulado.id)
    ))


def ultimas_respostas_reais(s) -> dict[int, RespostaDeSimulado]:
    """{questao_id: a resposta mais recente que eu dei a ela}, so questao real.

    A mais recente e a de maior `respondida_em`; empate, a de maior id. A
    lista vem em ordem e o dict deixa a ultima sobrescrever - o volume e
    pequeno, e isto se le melhor que uma subconsulta.
    """
    return {r.questao_id: r for r in respostas_reais(s)}


def acumulado_por(chaves_da_questao, materias: list[str] | None = None) -> dict:
    """{chave: Numeros} pela ultima resposta de cada questao real.

    `chaves_da_questao(questao)` devolve as chaves em que a questao conta - um
    assunto, ou varios quando o enunciado cobre mais de um. `materias` limita
    as questoes as daquelas materias, pelo nome gravado.
    """
    criar_tabelas()
    with sessao() as s:
        ultimas = ultimas_respostas_reais(s)
        if not ultimas:
            return {}
        consulta = select(QuestaoDeProva).where(QuestaoDeProva.id.in_(list(ultimas)))
        if materias is not None:
            consulta = consulta.where(QuestaoDeProva.materia.in_(materias))
        questoes = list(s.scalars(consulta))

    conta: dict = {}
    for questao in questoes:
        resposta = ultimas[questao.id]
        for chave in chaves_da_questao(questao):
            conta.setdefault(chave, Numeros()).responder(bool(resposta.acertou))
    return conta


#: O rotulo da questao sem materia gravada, como a tela escreve.
SEM_MATERIA = "sem matéria"


def _nome_da_materia():
    """A materia de uma questao pelo nome do EDITAL: a grafia antiga de uma
    prova ("Direito Processo Penal", 2013) conta na mesma linha da nova
    (auditoria de 04/10, BUG-4). A taxonomia e lida uma vez por conta."""
    from radar import conteudos as arvore

    taxonomia = arvore.carregar_taxonomia()
    return lambda materia: taxonomia.nome_do_edital(materia) or SEM_MATERIA


def acumulado_por_materia() -> list[DesempenhoDaMateria]:
    """Acerto por materia no acumulado, pior primeiro. Questao que saiu do
    acervo fica fora: nao ha materia para ela."""
    nome = _nome_da_materia()
    por_materia = acumulado_por(lambda q: [nome(q.materia)])
    return _pior_primeiro([
        DesempenhoDaMateria(nome, numeros.medidas, numeros.acertos)
        for nome, numeros in por_materia.items()
    ])


def acumulado() -> DesempenhoDaMateria:
    """Todas as materias juntas: quantas questoes reais diferentes respondi."""
    numeros = acumulado_por(lambda q: ["todas"]).get("todas", Numeros())
    return DesempenhoDaMateria("todas", numeros.medidas, numeros.acertos)


def _pior_primeiro(linhas: list[DesempenhoDaMateria]) -> list[DesempenhoDaMateria]:
    # pior primeiro: e onde vale gastar tempo de estudo
    linhas.sort(key=lambda d: d.porcentagem)
    return linhas


def _por_materia_das_respostas(tabela, gerada: bool, simulado_id: int | None,
                               simulado_ids: list[int] | None = None):
    """Acerto por materia contando RESPOSTAS - de uma rodada, de varias, ou
    todas."""
    criar_tabelas()
    consulta = (
        select(tabela.materia, RespostaDeSimulado)
        .join(tabela, tabela.id == RespostaDeSimulado.questao_id)
        .where(RespostaDeSimulado.escolhida.is_not(None))
        .where(RespostaDeSimulado.gerada.is_(gerada))
    )
    if simulado_id is not None:
        consulta = consulta.where(RespostaDeSimulado.simulado_id == simulado_id)
    if simulado_ids is not None:
        consulta = consulta.where(RespostaDeSimulado.simulado_id.in_(simulado_ids))
    with sessao() as s:
        linhas = s.execute(consulta).all()

    nome = _nome_da_materia()
    por_materia: dict[str, list] = {}
    for materia, resposta in linhas:
        por_materia.setdefault(nome(materia), []).append(resposta)
    return _pior_primeiro([
        DesempenhoDaMateria(nome, *placar(respostas), origem=IA if gerada else AUTOMATICO)
        for nome, respostas in por_materia.items()
    ])


def desempenho(simulado_id: int | None = None) -> list[DesempenhoDaMateria]:
    """Acerto por materia nas questoes REAIS.

    **Sem id, e o acumulado, e ele conta QUESTAO, e nao tentativa** (a ultima
    resposta de cada questao). **Com id, e o relatorio daquela rodada**, e
    conta as respostas dela.

    Questao gerada nao entra aqui, e nunca vai entrar somada: acertar uma
    variacao que a IA escreveu nao e a mesma coisa que acertar o que a FEPESE
    cobrou. O numero delas sai em `desempenho_das_geradas`, do lado.
    """
    if simulado_id is None:
        return acumulado_por_materia()
    return _por_materia_das_respostas(QuestaoDeProva, False, simulado_id)


def desempenho_das_rodadas(simulado_ids: list[int]) -> list[DesempenhoDaMateria]:
    """Acerto por materia nas questoes REAIS de varias rodadas juntas: as que
    mediram num mesmo dia (os dois diagnosticos de 03/10). Conta as respostas
    delas, como o relatorio de uma rodada; nenhuma rodada, nenhuma linha."""
    if not simulado_ids:
        return []
    return _por_materia_das_respostas(QuestaoDeProva, False, None, list(simulado_ids))


def erros_das_rodadas(simulado_ids: list[int]) -> list[RespostaDeSimulado]:
    """As respostas ERRADAS a questao real nestas rodadas, rodada por rodada
    na ordem da lista e, dentro dela, na ordem das questoes.

    Nao respondida nao e erro - a mesma regra do `placar`. E o que o R+7 dos
    diagnosticos refaz (servico/sabado.py).
    """
    if not simulado_ids:
        return []
    criar_tabelas()
    with sessao() as s:
        respostas = list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id.in_(list(simulado_ids)))
            .where(RespostaDeSimulado.gerada.is_(False))
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .where(RespostaDeSimulado.acertou.is_(False))))
    posicao = {simulado_id: i for i, simulado_id in enumerate(simulado_ids)}
    return sorted(respostas, key=lambda r: (posicao[r.simulado_id], r.ordem))


def treino_ia_dos_nos(nos) -> Numeros:
    """O treino de IA de um tema: toda resposta a questao gerada que aponta
    para um destes nos ou para um no abaixo deles. So `ia` e `ia_acertos`.

    E o sinal de que eu estou treinando o tema, na faixa e na ficha - um
    numero a parte, que nunca entra no acerto do tema (decisao 138). Conta
    resposta, como o volume do dia: refazer a mesma gerada conta de novo.
    """
    from radar.conteudos import SEPARADOR

    nos = [n for n in dict.fromkeys(nos or ()) if n]
    numeros = Numeros()
    if not nos:
        return numeros
    criar_tabelas()
    with sessao() as s:
        linhas = s.execute(
            select(RespostaDeSimulado.acertou, QuestaoGerada.conteudo)
            .join(QuestaoGerada, QuestaoGerada.id == RespostaDeSimulado.questao_id)
            .where(RespostaDeSimulado.gerada.is_(True))
            .where(RespostaDeSimulado.escolhida.is_not(None))
        )
        for acertou, conteudo in linhas:
            # Um no dentro do outro nao conta a resposta duas vezes: basta
            # cair em um deles.
            if conteudo and any(conteudo == no or conteudo.startswith(no + SEPARADOR)
                                for no in nos):
                numeros.responder(bool(acertou), gerada=True)
    return numeros


def ultimas_das_geradas() -> dict[int, RespostaDeSimulado]:
    """{id da gerada: a ultima resposta que eu dei a ela}.

    E o que o sorteio das geradas olha (decisao 142): a que nao esta aqui eu
    nunca fiz, e vem primeiro; das repetidas, a errada da ultima vez vem antes
    da acertada, e a mais antiga antes da mais nova.
    """
    criar_tabelas()
    with sessao() as s:
        respostas = s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.gerada.is_(True))
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .order_by(RespostaDeSimulado.respondida_em, RespostaDeSimulado.id))
        # Em ordem de quando respondi: a ultima de cada uma fica por cima.
        return {r.questao_id: r for r in respostas}


def geradas_feitas_por_no(nos) -> dict[str, int]:
    """{no: quantas geradas DIFERENTES dele (e de baixo dele) eu ja fiz}.

    Questao, e nao resposta: refazer a mesma nao conta de novo - e o "ja fiz
    X das Y" da faixa, contra as mesmas Y do `geradas.contagem_por_no` (nao
    rejeitada, com resposta, com no).
    """
    from radar.conteudos import SEPARADOR

    nos = list(dict.fromkeys(n for n in (nos or ()) if n))
    if not nos:
        return {}
    feitas = set(ultimas_das_geradas())
    criar_tabelas()
    with sessao() as s:
        linhas = s.execute(
            select(QuestaoGerada.id, QuestaoGerada.conteudo)
            .where(QuestaoGerada.rejeitada.is_(False))
            .where(QuestaoGerada.resposta.is_not(None))
            .where(QuestaoGerada.conteudo.is_not(None))).all()
    do_no = [conteudo for gerada_id, conteudo in linhas if gerada_id in feitas]
    return {no: sum(1 for c in do_no if c == no or c.startswith(no + SEPARADOR))
            for no in nos}


def desempenho_das_geradas(simulado_id: int | None = None) -> list[DesempenhoDaMateria]:
    """O mesmo, para as questoes escritas pela IA. Sempre um numero a parte.

    Existe como funcao propria, e nao como parametro de `desempenho`, porque
    o parametro convidaria alguem a somar os dois um dia. Sao duas perguntas
    diferentes: "quanto eu acerto do que a banca cobrou" e "quanto eu acerto
    no treino que eu mandei escrever".
    """
    return _por_materia_das_respostas(QuestaoGerada, True, simulado_id)


def resumo_do_simulado(simulado_id: int) -> dict:
    """Quantas questoes a rodada tem, quantas respondi e quantas acertei."""
    criar_tabelas()
    with sessao() as s:
        respostas = list(s.scalars(
            select(RespostaDeSimulado).where(RespostaDeSimulado.simulado_id == simulado_id)
        ))
    respondidas, acertos = placar(respostas)
    no_chute = [r for r in respostas if r.escolhida is not None and r.chutou]
    return {
        # O resultado da rodada de questao gerada leva o selo da IA.
        "origem": IA if any(r.gerada for r in respostas) else AUTOMATICO,
        "total": len(respostas),
        "respondidas": respondidas,
        "acertos": acertos,
        "erros": respondidas - acertos,
        # Sobre o total da rodada: a que nao respondi conta como nao acertada.
        "porcentagem": acertos / len(respostas) * 100 if respostas else 0.0,
        "terminou": bool(respostas) and respondidas == len(respostas),
        # O "vou no chute" (decisao 142): ao lado do acerto, nunca dentro dele.
        "chutes": len(no_chute),
        "acertos_no_chute": sum(1 for r in no_chute if r.acertou),
    }


def andamento_da_rodada(simulado_id: int) -> dict:
    """A fileira da tela da questao: uma marca por questao, na ordem, e
    quantos acertos seguidos terminam na ultima respondida.

    Marca: "certa", "errada" ou None (falta responder). A sequencia para no
    primeiro erro para tras, e a que ainda nao respondi nao a quebra.
    """
    criar_tabelas()
    with sessao() as s:
        respostas = list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.simulado_id == simulado_id)
            .order_by(RespostaDeSimulado.ordem)
        ))
    marcas = [None if r.escolhida is None else ("certa" if r.acertou else "errada")
              for r in respostas]
    seguidas = 0
    for marca in reversed([m for m in marcas if m is not None]):
        if marca != "certa":
            break
        seguidas += 1
    return {"marcas": marcas, "seguidas": seguidas}


@dataclass
class Evolucao:
    """Quanto eu acerto, e se isso mudou nos ultimos 30 dias."""
    origem = AUTOMATICO

    #: RESPOSTAS a questao real, e nao questoes: a evolucao e o historico.
    respondidas: int = 0
    acertos: int = 0
    #: Acerto nos ultimos 30 dias e antes deles. None quando a janela nao
    #: tem resposta suficiente para dizer alguma coisa.
    recente: float | None = None
    anterior: float | None = None
    #: Abaixo disto de respostas nao ha evolucao para medir: a tela convida
    #: a responder, em vez de mostrar a porcentagem de meia duzia de
    #: questoes. Vem do config/amostra.yml (`desempenho.evolucao`).
    minimo: int = regua.PADRAO.evolucao

    @property
    def porcentagem(self) -> float:
        return (self.acertos / self.respondidas * 100) if self.respondidas else 0.0

    @property
    def mensuravel(self) -> bool:
        return self.respondidas >= self.minimo

    @property
    def faltam(self) -> int:
        return max(0, self.minimo - self.respondidas)

    @property
    def variacao(self) -> float | None:
        if self.recente is None or self.anterior is None:
            return None
        return self.recente - self.anterior


def evolucao() -> Evolucao:
    """Acerto geral em questao real, e a variacao dos ultimos 30 dias.

    Conta TODAS as respostas, e nao so a ultima de cada questao: a evolucao e
    o meu historico, e errar e depois acertar a mesma questao e justamente o
    que ela tem que mostrar. Cada metade da comparacao precisa do minimo de
    respostas, senao a variacao e sorteio.
    """
    criar_tabelas()
    with sessao() as s:
        respostas = list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .where(RespostaDeSimulado.gerada.is_(False))
        ))

    respondidas, acertos = placar(respostas)
    minimo = regua.carregar().evolucao
    resultado = Evolucao(respondidas=respondidas, acertos=acertos, minimo=minimo)
    corte = agora() - timedelta(days=DIAS_DA_EVOLUCAO)
    recentes = [r for r in respostas if r.respondida_em and r.respondida_em >= corte]
    antigas = [r for r in respostas if r.respondida_em and r.respondida_em < corte]

    def taxa(lista):
        if len(lista) < minimo:
            return None
        feitas, certas = placar(lista)
        return certas / feitas * 100

    resultado.recente = taxa(recentes)
    resultado.anterior = taxa(antigas)
    return resultado
