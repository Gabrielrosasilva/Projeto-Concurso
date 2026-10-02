"""Meu desempenho por CONTEUDO, e o estado de cada no da arvore.

A tela Minhas materias responde "como eu vou em Direito Penal". Esta responde
um andar abaixo, onde o estudo de verdade acontece: "como eu vou na progressao
de regime". E so ela pode dizer, porque e ela que junta as duas origens do meu
treino (decisao 7 da Etapa 0):

  * **medido no radar** - cada questao real que eu respondi aqui dentro,
    pela ULTIMA resposta dela (decisao de 26/09), ligada ao no pela
    classificacao da Etapa 3A. O radar e sempre sem consulta: nao ha lei
    aberta ali;
  * **anotado** - as faixas do cronograma e o estudo extra, onde eu digito
    "fiz 15, acertei 11" depois de resolver no Qconcursos, no no que eu
    escolhi ao anotar.

**Os dois nunca sao somados num numero so.** A tela escreve sempre a divisao
"radar X% em N · anotado Y% em M": eles medem de maneiras diferentes (um e
questao a questao, o outro e a minha anotacao) e um numero unico esconderia
isso. O ESTADO, sim, olha as duas - e o meu desempenho naquele conteudo, e
ignorar metade dele seria pior.

**Questao de IA nunca entra**, em volume nem em acerto: ela treina e nao mede
(regra inviolavel do CLAUDE.md). O acerto nela e um segundo numero, no
`metricas`.

**So o que foi respondido SEM CONSULTA conta para o estado.** Com a lei aberta
eu acerto o que na prova eu nao acertaria, e o estado existe para falar da
prova. O que teve consulta continua no volume, e a tela diz isso.

A questao conta no no dela E em todos os nos acima: respondi uma de
"Direito Penal > Aplicacao da lei penal > Lei penal no tempo" e isso conta nos
tres. Sem o acumulado para cima, a materia inteira ficaria eternamente abaixo
do minimo enquanto cada subassunto tivesse duas respostas.

Recorte de tempo: o CICLO em andamento, por padrao (decisao E4), com a opcao
"desde o inicio".

**Por que o arquivo nao se chama `desempenho.py`**, como o roteiro propunha:
`servico.desempenho()` ja existe na fachada, e e o desempenho por MATERIA do
simulado. Duas coisas com o mesmo nome no mesmo lugar e exatamente o que esta
etapa veio consertar em outro canto. Escreva
`servico.desempenho_por_conteudo.tela()` - e fica dito na chamada que o
recorte e o no da arvore, e nao a materia.
"""
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select

from radar import amostra as regua
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import Classificacao, QuestaoDeProva
from radar.servico import conteudos as servico_conteudos
from radar.servico import metricas

#: Os nomes dos dois recortes, como a tela escreve. Os mesmos da decisao 4.
NO_RADAR = "medido no radar"
ANOTADO = "anotado"

#: O recorte de tempo. "ciclo" e o padrao (decisao E4).
CICLO, SEMPRE = "ciclo", "sempre"


@dataclass
class Metade:
    """Um dos dois recortes, num no. Nunca somado com o outro."""

    #: O que entra no estado: respondido sem consulta e com o acerto anotado.
    respostas: int = 0
    acertos: int = 0
    #: O que eu respondi COM a lei aberta: conta no volume, nao no estado.
    com_consulta: int = 0
    #: Fiz e nao anotei quantas acertei. Volume sim, acerto nao - nao e erro,
    #: foi o que aconteceu de verdade.
    sem_resultado: int = 0
    #: Em quantos dias diferentes eu respondi. Pesa no estado mais alto.
    dias: set = field(default_factory=set)

    @property
    def porcentagem(self) -> int | None:
        """None sem resposta - e nao zero, que diria que eu errei tudo."""
        if not self.respostas:
            return None
        return round(100 * self.acertos / self.respostas)

    @property
    def volume(self) -> int:
        """Tudo o que eu fiz ali, inclusive o que nao vale para o estado."""
        return self.respostas + self.com_consulta + self.sem_resultado

    @property
    def vazio(self) -> bool:
        return not self.volume

    def somar(self, respostas: int, acertos: int, dia: date | None) -> None:
        self.respostas += respostas
        self.acertos += acertos
        if dia is not None and respostas:
            self.dias.add(dia)


@dataclass
class Desempenho:
    """Um no da arvore e o que eu fiz nele, pelos dois recortes."""

    caminho: str
    nivel: str
    nome: str
    #: A meta da materia deste no (config/cronograma.yml), ou None.
    meta: int | None = None
    radar: Metade = field(default_factory=Metade)
    anotado: Metade = field(default_factory=Metade)

    @property
    def respostas(self) -> int:
        """As duas origens, para o ESTADO. A tela nunca mostra este numero
        sozinho: ela mostra a divisao."""
        return self.radar.respostas + self.anotado.respostas

    @property
    def acertos(self) -> int:
        return self.radar.acertos + self.anotado.acertos

    @property
    def dias(self) -> int:
        return len(self.radar.dias | self.anotado.dias)

    @property
    def com_consulta(self) -> int:
        return self.radar.com_consulta + self.anotado.com_consulta

    @property
    def sem_resultado(self) -> int:
        return self.radar.sem_resultado + self.anotado.sem_resultado

    @property
    def volume(self) -> int:
        return self.radar.volume + self.anotado.volume

    @property
    def vazio(self) -> bool:
        return self.radar.vazio and self.anotado.vazio

    @property
    def materia(self) -> str:
        return arvore.partes(self.caminho)[0]

    def estado(self, minimos: regua.Minimos | None = None) -> regua.Estado:
        return regua.estado(self.respostas, self.acertos, nivel=self.nivel,
                            meta=self.meta, dias=self.dias, minimos=minimos)

    def divisao(self) -> str:
        """"radar 70% em 10 · anotado 73% em 15": a frase da decisao 7.

        Sempre as duas metades, mesmo vazias: ver "anotado -" ao lado de
        "radar 70%" diz que eu nao anotei nada ali, e some com a divisao
        esconderia de onde o numero veio.
        """
        def lado(nome: str, metade: Metade) -> str:
            if metade.porcentagem is None:
                return f"{nome} —"
            return f"{nome} {metade.porcentagem}% em {metade.respostas}"

        return f"{lado('radar', self.radar)} · {lado('anotado', self.anotado)}"


# --- de onde vem cada coisa -----------------------------------------------------

def nos_das_questoes() -> dict[str, str]:
    """{chave da questao: caminho do no}, pela classificacao PRINCIPAL.

    Pendente entra igual: o no dela e o mais fundo que se sabe (a materia), e
    e melhor contar a resposta na materia do que em lugar nenhum. Quem precisa
    separar o pendente olha o `radar conteudos --pendentes`.
    """
    criar_tabelas()
    with sessao() as s:
        return {c.chave: c.conteudo for c in s.scalars(
            select(Classificacao).where(Classificacao.principal.is_(True))
        )}


def _metas_das_materias(plano=None) -> dict[str, int]:
    """{materia: meta em porcentagem}, do config/cronograma.yml.

    A meta do no e a da MATERIA dele: nao existe meta por assunto no
    cronograma, e inventar uma seria dar ao sistema um alvo que eu nao
    escolhi.
    """
    plano = plano or plano_de_estudo.carregar()
    metas = {}
    for m in plano.materias:
        if m.questoes:
            metas[m.nome] = round(100 * m.meta / m.questoes)
    return metas


def _janela(recorte: str, plano=None, hoje: date | None = None):
    """(inicio, fim) do recorte de tempo. `None` de inicio = desde sempre."""
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or date.today()
    fim = min(plano.fim, hoje) if plano.fim else hoje
    if recorte == SEMPRE:
        return None, hoje
    return plano.inicio, fim


def _questoes_respondidas(inicio: date | None, fim: date):
    """As ultimas respostas reais, com a chave da questao e o dia.

    [(chave, acertou, dia)]. Questao de IA fica fora; rodada nao terminada
    fica fora (o `metricas` ja filtra as duas coisas).
    """
    criar_tabelas()
    with sessao() as s:
        ultimas = metricas.ultimas_respostas_reais(s)
        if not ultimas:
            return []
        questoes = {q.id: q for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.id.in_(list(ultimas)))
        )}

    from radar.servico.classificacoes import chave_de
    from radar.util import para_local

    saida = []
    for questao_id, resposta in ultimas.items():
        questao = questoes.get(questao_id)
        if questao is None or questao.anulada:
            # Anulada nao mede nada: a banca desfez a pergunta.
            continue
        dia = para_local(resposta.respondida_em).date()
        if inicio is not None and dia < inicio:
            continue
        if dia > fim:
            continue
        saida.append((chave_de(questao), bool(resposta.acertou), dia))
    return saida


# --- a conta --------------------------------------------------------------------

def _ancestrais(caminho: str) -> list[str]:
    """O no e todos os de cima: "A > B > C" da ["A", "A > B", "A > B > C"]."""
    nomes = arvore.partes(caminho)
    return [arvore.SEPARADOR.join(nomes[:n + 1]) for n in range(len(nomes))]


def por_no(recorte: str = CICLO, plano=None,
           hoje: date | None = None) -> dict[str, Desempenho]:
    """{caminho: Desempenho} de todo no que tem alguma resposta.

    O no sem resposta nenhuma nao entra: a tela lista a arvore por conta dela
    e mostra "ainda nao treinei" onde falta. Encher o dicionario com 300 nos
    zerados so faria a tela ter de filtrar de novo.
    """
    plano = plano or plano_de_estudo.carregar()
    inicio, fim = _janela(recorte, plano, hoje)
    metas = _metas_das_materias(plano)
    niveis = {no.caminho: no.nivel for no in servico_conteudos.nos()}
    nos: dict[str, Desempenho] = {}

    def achar(caminho: str) -> Desempenho | None:
        """O Desempenho daquele no, criado na hora. None se o no nao existe."""
        if caminho in nos:
            return nos[caminho]
        if caminho not in niveis:
            # No que a arvore nao tem: a classificacao aponta para um caminho
            # que nao existe mais. Nao se inventa no para caber a resposta.
            return None
        nomes = arvore.partes(caminho)
        nos[caminho] = Desempenho(
            caminho=caminho, nivel=niveis[caminho], nome=nomes[-1],
            meta=metas.get(nomes[0]),
        )
        return nos[caminho]

    # --- medido no radar ---------------------------------------------------
    de_quem = nos_das_questoes()
    for chave, acertou, dia in _questoes_respondidas(inicio, fim):
        caminho = de_quem.get(chave)
        if caminho is None:
            # Questao sem classificacao: conta no dia (o `metricas` ja a
            # contou) e em no nenhum. A tela diz quantas sao.
            continue
        for ancestral in _ancestrais(caminho):
            no = achar(ancestral)
            if no is not None:
                no.radar.somar(1, 1 if acertou else 0, dia)

    # --- anotado (faixas e estudo extra) ----------------------------------
    for linha in metricas.lancamentos(inicio or plano.inicio, fim, plano):
        if linha.origem == metricas.RADAR or not linha.conteudo:
            continue
        if not linha.questoes:
            continue
        for ancestral in _ancestrais(linha.conteudo):
            no = achar(ancestral)
            if no is None:
                continue
            if linha.consulta:
                no.anotado.com_consulta += linha.questoes
            elif linha.acertos is None:
                no.anotado.sem_resultado += linha.questoes
            else:
                no.anotado.somar(linha.questoes, linha.acertos, linha.data)
    return nos


@dataclass
class LinhaDaTela:
    """Um no na tela "Meu desempenho", com o estado e a amostra."""

    desempenho: Desempenho
    estado: regua.Estado

    @property
    def caminho(self) -> str:
        return self.desempenho.caminho

    @property
    def nivel(self) -> str:
        return self.desempenho.nivel

    @property
    def nome(self) -> str:
        return self.desempenho.nome

    @property
    def profundidade(self) -> int:
        return len(arvore.partes(self.caminho)) - 1

    @property
    def divisao(self) -> str:
        return self.desempenho.divisao()

    @property
    def frase(self) -> str | None:
        """O que escrever em vez de uma porcentagem em que nao se acredita."""
        if self.estado.suficiente:
            return None
        return regua.frase_da_amostra_pequena(self.estado)


def tela(recorte: str = CICLO, materia: str | None = None, plano=None,
         hoje: date | None = None) -> list[LinhaDaTela]:
    """As linhas da tela, em ordem de arvore: materia, e abaixo dela os filhos.

    `materia` filtra uma materia so. A ordem e a do caminho, e nao a do
    desempenho: a tela e um mapa do que eu estudei, e um mapa que se reordena
    sozinho nao se le.
    """
    minimos = regua.carregar()
    linhas = []
    for caminho, no in por_no(recorte, plano, hoje).items():
        if materia and no.materia != materia:
            continue
        linhas.append(LinhaDaTela(desempenho=no, estado=no.estado(minimos)))
    linhas.sort(key=lambda l: l.caminho)
    return linhas


def do_no(caminho: str, recorte: str = CICLO, plano=None,
          hoje: date | None = None) -> LinhaDaTela | None:
    """O desempenho de um no so. None quando eu nunca respondi nada nele."""
    no = por_no(recorte, plano, hoje).get(caminho)
    if no is None:
        return None
    return LinhaDaTela(desempenho=no, estado=no.estado(regua.carregar()))


# --- o anotado, para as telas que contam por materia e por assunto --------------
#
# O Meu foco, o Onde estudar e a home contavam so o radar (decisao E2). A
# decisao 7 da Etapa 0 os manda somar tambem o anotado do Qconcursos, a partir
# desta etapa. As duas funcoes abaixo entregam o anotado no vocabulario DELES -
# (materia, assunto) e materia -, e nao em caminho de no: quem converte e
# daqui, para nenhuma tela ter de saber como a arvore e escrita.
#
# So entra o que esta ligado a um no: anotacao sem conteudo escolhido continua
# contando no dia e em assunto nenhum. Nada e aproximado.

@dataclass
class Anotado:
    """O recorte anotado de uma materia ou de um assunto."""

    respostas: int = 0
    acertos: int = 0
    ultima: date | None = None

    @property
    def porcentagem(self) -> int | None:
        if not self.respostas:
            return None
        return round(100 * self.acertos / self.respostas)


def _anotado(chave_do_no, recorte: str, plano=None, hoje: date | None = None) -> dict:
    """{chave: Anotado}, com `chave_do_no(caminho)` dizendo onde cada no cai.

    `chave_do_no` devolve None quando aquele no nao tem lugar na tela que
    pediu - e ai a anotacao fica de fora, nunca aproximada.
    """
    plano = plano or plano_de_estudo.carregar()
    inicio, fim = _janela(recorte, plano, hoje)
    saida: dict[object, Anotado] = {}
    for linha in metricas.lancamentos(inicio or plano.inicio, fim, plano):
        if linha.origem == metricas.RADAR or not linha.conteudo:
            continue
        # Para o ESTADO e para o acerto, so o sem consulta com acerto anotado.
        if linha.consulta or not linha.questoes or linha.acertos is None:
            continue
        chave = chave_do_no(linha.conteudo)
        if chave is None:
            continue
        atual = saida.setdefault(chave, Anotado())
        atual.respostas += linha.questoes
        atual.acertos += linha.acertos
        if atual.ultima is None or linha.data > atual.ultima:
            atual.ultima = linha.data
    return saida


def anotado_por_materia(recorte: str = SEMPRE, plano=None,
                        hoje: date | None = None) -> dict[str, Anotado]:
    """{materia: Anotado}. A materia e o primeiro nome do caminho do no."""
    return _anotado(lambda caminho: arvore.partes(caminho)[0], recorte, plano, hoje)


def anotado_por_assunto(recorte: str = SEMPRE, plano=None,
                        hoje: date | None = None) -> dict[tuple, Anotado]:
    """{(materia, assunto): Anotado}, pelos dois primeiros nomes do caminho.

    No que para na materia ("Direito Penal", sem assunto) fica de fora: ele
    nao diz qual assunto, e distribui-lo seria inventar.
    """
    def par(caminho: str):
        nomes = arvore.partes(caminho)
        return (nomes[0], nomes[1]) if len(nomes) >= 2 else None

    return _anotado(par, recorte, plano, hoje)
