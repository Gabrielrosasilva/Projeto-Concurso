"""Como eu fui em cada semana, agrupado pelos ciclos do mapa do ano.

Toda a conta mora aqui, e a tela so mostra: e o que deixa testar "a semana
fechou com 4 dias completos e 72% de acerto" sem abrir navegador nenhum.

Os numeros seguem as regras da etapa E2 (docs/decisoes.md), e as mesmas
funcoes:

  * VOLUME e ACERTO saem do `servico.metricas`, a fonte unica: a semana soma
    a MESMA lista de lancamentos que o "Fiz hoje" de cada dia dela (faixas,
    estudo extra, respostas no radar e treino de IA). Duas contas para a mesma
    pergunta divergem no dia em que uma delas muda;
  * a comparacao com a META usa so questao SEM CONSULTA;
  * "dias completos" e o `balanco_da_semana` do cronograma, o MESMO que o
    gatilho usa para decidir o nivel - incluindo o feriado cumprido na minima.

Nada daqui entra em acerto medido do radar: e o diario, e ele mora na tela Hoje
e nesta.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select

from radar import amostra as regua
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import EstadoDoDia, NotaDaSemana, agora
from radar.servico import cronograma as diario
from radar.servico import erros as caderno
from radar.servico import metricas

# Quantas casas a porcentagem tem na tela: nenhuma. "72%" responde; "71,875%"
# nao responde melhor.
SABADO = 5


@dataclass
class Comparacao:
    """A seta ao lado de um numero: quanto ele mudou da semana anterior.

    `melhor` decide a cor, e nao o sinal: em erros, menos e melhor.
    """
    diferenca: float
    melhor: bool

    @property
    def subiu(self) -> bool:
        return self.diferenca > 0

    @property
    def modulo(self) -> float:
        return abs(self.diferenca)


@dataclass
class ResumoDoCiclo:
    """A linha do ciclo fechado: o que sobrou dele em quatro numeros."""
    dias_completos: int = 0
    dias_no_plano: int = 0
    numeros: metricas.Numeros = field(default_factory=metricas.Numeros)

    @property
    def questoes(self) -> int:
        return self.numeros.questoes

    @property
    def porcentagem(self) -> int | None:
        return self.numeros.porcentagem

    @property
    def minutos(self) -> int:
        return self.numeros.minutos


@dataclass
class SemanaNaTela:
    """Uma semana do ciclo, com tudo o que o cartao dela mostra."""
    numero: int
    inicio: date                 # a segunda
    fim: date                    # o sabado
    em_andamento: bool
    pilulas: list = field(default_factory=list)
    dias_completos: int = 0
    dias_no_plano: int = 0
    zerados: int = 0
    sem_marcacao: int = 0
    #: Volume e acerto da semana, no recorte total: faixas + extras + radar +
    #: treino de IA (`numeros.ia`, que fica fora do acerto).
    numeros: object = None
    #: So o que vale para a meta (sem consulta).
    sem_consulta: object = None
    minutos: int = 0
    sequencia: int = 0
    nivel: object = None
    plano_b: int = 0
    erros_anotados: int = 0
    melhor: bool = False
    #: As setas, por nome: questoes, acerto, minutos, dias.
    comparacao: dict = field(default_factory=dict)
    nota: object = None

    @property
    def ruim(self) -> bool:
        """Semana em que eu zerei dia ou deixei dia sem marcar.

        E a mesma ideia do gatilho: a semana em que a maioria dos dias ficou
        abaixo da Ideal. Serve para a tela nao precisar repetir a conta.
        """
        return bool(self.zerados or self.sem_marcacao)


@dataclass
class CicloNaTela:
    """Um ciclo do mapa do ano, com as semanas que ele teve."""
    nome: str
    #: A etapa do `mapa` (D2), quando ha uma; None no ciclo do proprio arquivo.
    etapa: object = None
    atual: bool = False
    terminou: bool = False
    semanas: list = field(default_factory=list)
    resumo: ResumoDoCiclo = field(default_factory=ResumoDoCiclo)

    @property
    def tem_semanas(self) -> bool:
        return bool(self.semanas)

    @property
    def maior_volume(self) -> int:
        """O maior numero de questoes de uma semana: a escala do grafico."""
        return max((s.numeros.questoes for s in self.semanas), default=0)


# --- a reflexao da semana ------------------------------------------------------

def nota(inicio: date) -> NotaDaSemana | None:
    """A reflexao daquela semana, ou None se eu nao escrevi nada."""
    criar_tabelas()
    with sessao() as s:
        return s.scalar(select(NotaDaSemana).where(NotaDaSemana.inicio == inicio))


def notas(inicio: date, fim: date) -> dict[date, NotaDaSemana]:
    criar_tabelas()
    with sessao() as s:
        achadas = s.scalars(
            select(NotaDaSemana)
            .where(NotaDaSemana.inicio >= inicio, NotaDaSemana.inicio <= fim)
        )
        return {n.inicio: n for n in achadas}


def anotar(inicio: date, funcionou: str | None = None,
           ajustar: str | None = None) -> NotaDaSemana:
    """Grava (ou corrige) a reflexao da semana que comeca em `inicio`.

    A chave e a segunda-feira, e nao o numero da semana: numero e do ciclo, e
    ele reinicia no Ciclo 2 - a data nao reinicia nunca.

    Texto vazio APAGA o campo, de proposito: e assim que eu desfaco uma frase
    que escrevi errado, sem precisar de um botao a mais.
    """
    if inicio.weekday() != 0:
        raise diario.RegistroInvalido(
            f"{inicio:%d/%m/%Y} não é uma segunda-feira: a semana começa na segunda."
        )
    criar_tabelas()
    with sessao() as s:
        registro = s.scalar(select(NotaDaSemana).where(NotaDaSemana.inicio == inicio))
        if registro is None:
            registro = NotaDaSemana(inicio=inicio)
            s.add(registro)
        registro.funcionou = (funcionou or "").strip() or None
        registro.ajustar = (ajustar or "").strip() or None
        registro.atualizado_em = agora()
    return registro


# --- a conta -------------------------------------------------------------------

def semana_de(data: date) -> tuple[date, date]:
    """A segunda e o sabado da semana de `data`. Domingo nao esta no plano."""
    segunda = data - timedelta(days=data.weekday())
    return segunda, segunda + timedelta(days=SABADO)


def _estados(inicio: date, fim: date) -> dict[date, EstadoDoDia]:
    criar_tabelas()
    with sessao() as s:
        achados = s.scalars(
            select(EstadoDoDia).where(EstadoDoDia.data >= inicio,
                                      EstadoDoDia.data <= fim)
        )
        return {e.data: e for e in achados}


def _comparar(agora_: SemanaNaTela, antes: SemanaNaTela, minimo: int = 20) -> dict:
    """As setas do cartao: quanto mudou da semana anterior.

    Acerto compara PONTO a ponto (72% para 68% e -4), e nao a razao entre eles:
    e assim que eu leio "caiu 4 pontos". Semana sem acerto medido nao compara
    acerto nenhum - comparar com o nada daria uma flecha inventada.

    A semana em andamento nao tem seta nenhuma (U18): os numeros dela sao
    parciais. E o acerto e os erros so comparam com `minimo` respostas
    medidas de cada lado (P11, decisao 150; a `evolucao` do
    config/amostra.yml): "67% ↑ +27" com 3 respostas era sorteio.
    """
    setas = {}
    if antes is None or agora_.em_andamento:
        return setas

    def por(nome, valor, anterior, mais_e_melhor=True):
        if valor is None or anterior is None:
            return
        diferenca = valor - anterior
        if diferenca:
            setas[nome] = Comparacao(diferenca,
                                     diferenca > 0 if mais_e_melhor else diferenca < 0)

    por("questoes", agora_.numeros.questoes, antes.numeros.questoes)
    por("minutos", agora_.minutos, antes.minutos)
    por("dias", agora_.dias_completos, antes.dias_completos)
    if min(agora_.numeros.medidas, antes.numeros.medidas) >= minimo:
        por("acerto", agora_.numeros.porcentagem, antes.numeros.porcentagem)
        por("erros", agora_.numeros.erros, antes.numeros.erros, mais_e_melhor=False)
    return setas


def _melhor(semanas: list[SemanaNaTela]) -> None:
    """Marca a melhor semana do ciclo: mais dias completos, e no empate mais
    questoes feitas. Semana em andamento nao concorre - ela nao acabou."""
    fechadas = [s for s in semanas if not s.em_andamento and s.dias_completos]
    if not fechadas:
        return
    campea = max(fechadas, key=lambda s: (s.dias_completos, s.numeros.questoes))
    campea.melhor = True


def _ciclo_da_semana(plano, inicio: date, fim: date):
    """A etapa do mapa em que a semana cai, pelo primeiro dia dela que tem dono.

    Pelo primeiro dia, e nao pela segunda: a semana que comeca num vao entre
    dois ciclos (o domingo entre eles nao conta, mas um feriado no meio pode)
    continua pertencendo ao ciclo do resto dela.
    """
    dia = inicio
    while dia <= fim:
        etapa = plano.etapa_do_mapa(dia)
        if etapa is not None:
            return etapa
        dia += timedelta(days=1)
    return None


def montar(plano=None, hoje: date | None = None) -> list[CicloNaTela]:
    """Os ciclos com as semanas que ja aconteceram, na ordem do mapa do ano.

    Semana futura nao aparece: ela nao tem o que contar. A semana corrente
    aparece marcada "em andamento" - os numeros dela sao parciais, e dizer isso
    e mais honesto do que mostra-los como se a semana tivesse fechado.
    """
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or diario.hoje_local()

    metas = diario.metas_do_plano(plano)
    # O `hoje` vai direto para o gatilho: e ele que decide quais semanas ja
    # fecharam. Passar pelo `hoje_do_gatilho` aqui olharia o relogio de verdade
    # e deixaria todas as semanas como "futura" quando o teste para o tempo.
    niveis = plano_de_estudo.niveis(plano, metas, hoje)
    estados = _estados(plano.inicio, plano.fim)
    # Uma lista so, para o ciclo inteiro: cada semana soma o pedaco dela.
    linhas = metricas.lancamentos(plano.inicio, min(plano.fim, hoje), plano)
    reflexoes = notas(plano.inicio, plano.fim)
    do_caderno = caderno.listar(situacao="todos", hoje=hoje)

    por_semana: dict[int, list] = {}
    for dia in plano.dias:
        por_semana.setdefault(dia.semana, []).append(dia)

    montadas = []
    for numero in sorted(por_semana):
        dias = sorted(por_semana[numero], key=lambda d: d.data)
        inicio, fim = semana_de(dias[0].data)
        if inicio > hoje:
            continue          # semana futura: nao aparece

        nivel = niveis.get(numero)
        balanco = plano_de_estudo.balanco_da_semana(
            [d for d in dias if d.data <= hoje], metas)

        semana = SemanaNaTela(
            numero=numero,
            inicio=inicio,
            fim=fim,
            em_andamento=inicio <= hoje <= fim,
            dias_completos=balanco.na_ideal,
            dias_no_plano=len(dias),
            zerados=balanco.zerados,
            sem_marcacao=balanco.sem_marcacao,
            nivel=nivel,
            nota=reflexoes.get(inicio),
        )

        conta = metricas.contar(l for l in linhas if inicio <= l.data <= min(fim, hoje))
        semana.numeros = conta.total
        semana.sem_consulta = conta.sem_consulta
        semana.minutos = conta.minutos
        for dia in dias:
            estado = estados.get(dia.data)
            if dia.data <= hoje and estado is not None and estado.plano_b:
                semana.plano_b += 1

        # As pilulas dos seis dias do plano, na ordem da semana.
        for dia in dias:
            semana.pilulas.append(diario.Pilula(
                dia.data, plano_de_estudo.DIAS_CURTOS[dia.data.weekday()],
                metas.get(dia.data), dia.data > hoje, False,
            ))

        # A sequencia no FIM da semana: e o numero que aquela semana deixou.
        semana.sequencia = diario.sequencia(plano, metas, min(fim, hoje))
        semana.erros_anotados = sum(1 for e in do_caderno
                                    if inicio <= e.data_estudo <= fim)
        montadas.append(semana)

    return _agrupar(plano, montadas, hoje)


def _agrupar(plano, semanas: list[SemanaNaTela], hoje: date) -> list[CicloNaTela]:
    """Junta as semanas nos ciclos do mapa, na ordem dele."""
    etapa_atual = plano.etapa_do_mapa(hoje)
    por_etapa: dict[str, list] = {}
    for semana in semanas:
        etapa = _ciclo_da_semana(plano, semana.inicio, semana.fim)
        por_etapa.setdefault(etapa.nome if etapa else plano.titulo, []).append(semana)

    ciclos = []
    etapas = plano.mapa or []
    nomes = [e.nome for e in etapas]
    # As etapas do mapa, na ordem dele; e, no fim, as semanas que nao cairam em
    # etapa nenhuma (arquivo sem `mapa`, ou dia fora de todas as etapas).
    for etapa in etapas:
        das_semanas = por_etapa.get(etapa.nome, [])
        if not das_semanas:
            continue
        ciclos.append(_ciclo(etapa.nome, das_semanas, etapa=etapa,
                             atual=etapa_atual is not None and etapa.nome == etapa_atual.nome,
                             terminou=etapa.terminou(hoje)))
    for nome, das_semanas in por_etapa.items():
        if nome not in nomes:
            ciclos.append(_ciclo(nome, das_semanas, atual=True))
    return ciclos


def _ciclo(nome: str, semanas: list[SemanaNaTela], etapa=None, atual: bool = False,
           terminou: bool = False) -> CicloNaTela:
    semanas = sorted(semanas, key=lambda s: s.inicio)
    minimo = regua.carregar().evolucao
    anterior = None
    for semana in semanas:
        semana.comparacao = _comparar(semana, anterior, minimo)
        anterior = semana
    _melhor(semanas)

    resumo = ResumoDoCiclo()
    for semana in semanas:
        resumo.dias_completos += semana.dias_completos
        resumo.dias_no_plano += semana.dias_no_plano
        resumo.numeros = resumo.numeros + semana.numeros
    return CicloNaTela(nome=nome, etapa=etapa, atual=atual, terminou=terminou,
                       semanas=semanas, resumo=resumo)
