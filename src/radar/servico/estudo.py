"""O controle que o ANKI fazia: o que eu estudei, o que falta, o que revisar.

O novo.md pede isto na secao 19, e por um motivo concreto: sem ANKI nao ha
mais nada dizendo "este conteudo voltou a hora". Este modulo responde, para
cada no da arvore:

  * **estudado** - eu passei por ele. Uma faixa de ESTUDO ligada ao no (ou a
    um no abaixo dele) foi marcada como feita, ou ha estudo extra de teoria ou
    de lei seca nele. Faixa de questoes nao faz um conteudo "estudado": fazer
    questao e praticar, e eu posso praticar o que nunca li;
  * **praticado** - eu respondi questao dele, aqui ou anotada;
  * **nao estudado** - nenhum dos dois.

E, por no: a data do primeiro e do ultimo estudo, a da ultima revisao, a taxa
de acerto (do `desempenho_por_conteudo`) e a evolucao semana a semana, com as
MESMAS contas da tela Semanas.

**Nada disso e gravado numa tabela.** Tudo sai do historico - dos checks do
dia, do estudo extra, das respostas - pela mesma escolha do `espacada.py`: nao
ha estado para dessincronizar, e descartar um simulado de teste apaga sozinho
o que ele tinha agendado.

**A revisao por no tem tres gatilhos**, e a tela diz qual disparou:

  1. **erro recente** - errei questao do no na ultima vez que a respondi, ou
     ha erro aberto no caderno ligado a ele;
  2. **estado "precisa revisar"** - o acerto esta abaixo do corte do
     config/amostra.yml, com amostra que sustente a conta;
  3. **prazo vencido** - o 1-7-30 do `espacada.py`, contado do ultimo estudo
     ou da ultima pratica.

Um no pode disparar por mais de um; a lista guarda todos os motivos. "Questoes
a refazer" sao as erradas no radar mais as do caderno de erros - as duas
listas que ja existem, nunca uma terceira.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from radar import amostra as regua
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar.servico import conteudos as servico_conteudos
from radar.servico import desempenho_por_conteudo as por_conteudo
from radar.servico import erros as caderno
from radar.servico import espacada
from radar.servico import metricas

#: Os tipos de faixa que fazem um conteudo "estudado". `questoes`, `revisao`,
#: `simulado` e `bonus` ficam de fora de proposito: eles praticam o conteudo,
#: e praticar nao e ter estudado.
TIPOS_DE_ESTUDO = {"teoria", "lei_seca", "portugues", "raciocinio"}

#: O mesmo, no estudo extra (`servico.extra.O_QUE`).
EXTRA_DE_ESTUDO = {"teoria", "lei_seca"}

#: Os nomes dos tres gatilhos de revisao, como a tela escreve.
POR_ERRO = "erro recente"
POR_DESEMPENHO = "precisa revisar"
POR_PRAZO = "prazo de revisão vencido"

#: Os intervalos do 1-7-30. Os mesmos do `espacada.py`: uma regra, um lugar.
INTERVALOS = espacada.INTERVALOS

#: Nao estudado | estudado | praticado. Um no pode ser os dois ultimos.
NAO_ESTUDADO = "não estudado"
ESTUDADO = "estudado"
PRATICADO = "praticado"


@dataclass
class Situacao:
    """Em que pe esta um no: o que eu fiz nele e quando."""

    caminho: str
    nivel: str
    nome: str

    #: Faixa de estudo feita ou estudo extra de teoria/lei neste no ou abaixo.
    estudado: bool = False
    #: Tem resposta: no radar ou anotada.
    praticado: bool = False

    primeiro_estudo: date | None = None
    ultimo_estudo: date | None = None
    #: A primeira e a ultima vez que eu respondi questao dele (radar ou
    #: anotado). A PRIMEIRA e a ancora do 1-7-30 quando nao houve estudo: o
    #: prazo conta do primeiro contato, e cada acerto no vencimento o empurra
    #: para a etapa seguinte. Ancorar na ULTIMA reiniciaria a conta a cada
    #: questao, e a etapa nunca andaria.
    primeira_pratica: date | None = None
    ultima_pratica: date | None = None
    #: A ultima revisao: faixa de tipo `revisao`, estudo extra de revisao, ou
    #: uma rodada de revisao do `espacada`. None = nunca revisei.
    ultima_revisao: date | None = None

    minutos: int = 0
    #: O desempenho do no, quando ele tem resposta. None quando nao tem.
    desempenho: object = None
    estado: regua.Estado | None = None
    #: [(semana, porcentagem|None, respostas)] - as mesmas contas da Semanas.
    semanal: list = field(default_factory=list)

    @property
    def rotulo(self) -> str:
        """"estudado e praticado", "praticado", "estudado", "nao estudado"."""
        if self.estudado and self.praticado:
            return f"{ESTUDADO} e {PRATICADO}"
        if self.estudado:
            return ESTUDADO
        if self.praticado:
            return PRATICADO
        return NAO_ESTUDADO

    @property
    def materia(self) -> str:
        return arvore.partes(self.caminho)[0]

    @property
    def profundidade(self) -> int:
        return len(arvore.partes(self.caminho)) - 1

    @property
    def ultima_vez(self) -> date | None:
        """A data mais recente de qualquer coisa que eu fiz neste no."""
        datas = [d for d in (self.ultimo_estudo, self.ultima_pratica,
                             self.ultima_revisao) if d is not None]
        return max(datas) if datas else None

    def dias_desde(self, hoje: date) -> int | None:
        ultima = self.ultima_vez
        return None if ultima is None else (hoje - ultima).days


@dataclass
class ParaRevisar:
    """Um no que voltou para a fila, e por que."""

    caminho: str
    nome: str
    nivel: str
    motivos: list = field(default_factory=list)
    #: Quando o prazo venceu, quando o gatilho foi o prazo.
    vence_em: date | None = None
    #: Que etapa do 1-7-30 e a de agora.
    etapa: int | None = None
    #: As questoes reais erradas deste no, para a rodada comecar por elas.
    erradas: list = field(default_factory=list)
    #: Os erros do caderno ligados a este no.
    erros_do_caderno: list = field(default_factory=list)
    estado: regua.Estado | None = None

    @property
    def atraso(self) -> int:
        return 0 if self.vence_em is None else max(
            0, (date.today() - self.vence_em).days)

    @property
    def porque(self) -> str:
        """A frase da tela, montada dos motivos. Nunca inventada."""
        return " · ".join(self.motivos)


# --- o que aconteceu em cada no -------------------------------------------------

def _ancestrais(caminho: str) -> list[str]:
    nomes = arvore.partes(caminho)
    return [arvore.SEPARADOR.join(nomes[:n + 1]) for n in range(len(nomes))]


def _semana_de(plano, data: date) -> int | None:
    dia = plano.dia(data)
    return dia.semana if dia is not None else None


def situacoes(recorte: str = por_conteudo.SEMPRE, plano=None,
              hoje: date | None = None) -> dict[str, Situacao]:
    """{caminho: Situacao} de TODO no da arvore, inclusive o nao estudado.

    Aqui a arvore inteira entra, e nao so o que tem resposta: a pergunta
    "o que eu ainda nao estudei" so se responde com a lista completa.

    O recorte de tempo e "desde o inicio" por padrao, ao contrario do
    desempenho: "eu ja estudei isto?" e uma pergunta sobre a minha vida, e nao
    sobre o ciclo - ter lido a LEP no ciclo 1 nao desaprende quando o ciclo 2
    comeca. O desempenho DENTRO da situacao segue o recorte pedido.
    """
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or date.today()

    situacao = {
        no.caminho: Situacao(caminho=no.caminho, nivel=no.nivel, nome=no.nome)
        for no in servico_conteudos.nos()
    }

    # --- as faixas e o estudo extra, pelo que eu marquei -------------------
    inicio = plano.inicio
    fim = min(plano.fim, hoje) if plano.fim else hoje
    semanal: dict[str, dict[int, list]] = {}
    for linha in metricas.lancamentos(inicio, fim, plano):
        if linha.origem == metricas.RADAR or not linha.conteudo:
            continue
        for caminho in _ancestrais(linha.conteudo):
            atual = situacao.get(caminho)
            if atual is None:
                continue
            atual.minutos += linha.minutos
            if linha.questoes:
                atual.praticado = True
                atual.primeira_pratica = _mais_velha(atual.primeira_pratica, linha.data)
                atual.ultima_pratica = _mais_nova(atual.ultima_pratica, linha.data)
            else:
                # Faixa ou extra sem questao: foi leitura. E isto que faz o
                # conteudo "estudado".
                atual.estudado = True
                atual.primeiro_estudo = _mais_velha(atual.primeiro_estudo, linha.data)
                atual.ultimo_estudo = _mais_nova(atual.ultimo_estudo, linha.data)
            if linha.questoes and linha.acertos is not None and not linha.consulta:
                semana = _semana_de(plano, linha.data)
                if semana is not None:
                    semanal.setdefault(caminho, {}).setdefault(semana, [0, 0])
                    semanal[caminho][semana][0] += linha.questoes
                    semanal[caminho][semana][1] += linha.acertos

    # --- as respostas do radar --------------------------------------------
    de_quem = por_conteudo.nos_das_questoes()
    for chave, acertou, dia in por_conteudo._questoes_respondidas(None, hoje):
        caminho_da_questao = de_quem.get(chave)
        if caminho_da_questao is None:
            continue
        for caminho in _ancestrais(caminho_da_questao):
            atual = situacao.get(caminho)
            if atual is None:
                continue
            atual.praticado = True
            atual.primeira_pratica = _mais_velha(atual.primeira_pratica, dia)
            atual.ultima_pratica = _mais_nova(atual.ultima_pratica, dia)
            semana = _semana_de(plano, dia)
            if semana is not None:
                semanal.setdefault(caminho, {}).setdefault(semana, [0, 0])
                semanal[caminho][semana][0] += 1
                semanal[caminho][semana][1] += 1 if acertou else 0

    # --- o desempenho e o estado ------------------------------------------
    minimos = regua.carregar()
    medido = por_conteudo.por_no(recorte, plano, hoje)
    for caminho, atual in situacao.items():
        no = medido.get(caminho)
        if no is not None:
            atual.desempenho = no
            atual.estado = no.estado(minimos)
        semanas = semanal.get(caminho, {})
        atual.semanal = [
            (semana, (round(100 * acertos / questoes) if questoes else None), questoes)
            for semana, (questoes, acertos) in sorted(semanas.items())
        ]
    return situacao


def _mais_nova(atual: date | None, nova: date) -> date:
    return nova if atual is None or nova > atual else atual


def _mais_velha(atual: date | None, nova: date) -> date:
    return nova if atual is None or nova < atual else atual


def nao_estudados(plano=None, hoje: date | None = None) -> list[Situacao]:
    """Os nos em que eu nunca encostei, de cima para baixo na arvore.

    Materia inteira nao estudada aparece como materia: listar os 20 assuntos
    dela um por um nao e informacao, e lista telefonica. Por isso o filho de
    um nao estudado nao entra.
    """
    todas = situacoes(plano=plano, hoje=hoje)
    virgens = {c for c, s in todas.items()
               if not s.estudado and not s.praticado}
    saida = [todas[c] for c in sorted(virgens)
             if not any(pai in virgens for pai in _ancestrais(c)[:-1])]
    return saida


# --- a revisao ------------------------------------------------------------------

def _etapa_e_vencimento(desde: date, respostas_certas: list[date],
                        hoje: date) -> tuple[int, date]:
    """A etapa do 1-7-30 e quando ela vence, contando de `desde`.

    A mesma regra do `espacada.py`: acertar NA data do vencimento ou depois
    passa para a proxima etapa; acertar antes e treino, nao revisao.
    """
    etapa, vence = 1, desde + timedelta(days=INTERVALOS[0])
    for dia in sorted(respostas_certas):
        if dia >= vence and etapa < len(INTERVALOS):
            etapa += 1
            vence = dia + timedelta(days=INTERVALOS[etapa - 1])
    return etapa, vence


def para_revisar(plano=None, hoje: date | None = None,
                 recorte: str = por_conteudo.CICLO) -> list[ParaRevisar]:
    """Os nos que voltaram para a fila hoje, do mais atrasado ao mais novo.

    So no que eu ja estudei ou pratiquei entra: "revisar" o que eu nunca vi
    nao e revisao, e a lista de nao estudados existe para isso.
    """
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or date.today()
    todas = situacoes(recorte=recorte, plano=plano, hoje=hoje)
    erradas_por_no = _erradas_por_no()
    caderno_por_no = _caderno_por_no(hoje)
    # Os dias de acerto por no, calculados UMA vez: dentro do laco isto seria
    # uma varredura do banco por no da arvore.
    acertos_por_no = _dias_de_acerto_por_no(hoje)

    fila: list[ParaRevisar] = []
    for caminho, atual in sorted(todas.items()):
        if not (atual.estudado or atual.praticado):
            continue

        motivos, vence_em, etapa = [], None, None

        if erradas_por_no.get(caminho) or caderno_por_no.get(caminho):
            motivos.append(POR_ERRO)

        if atual.estado is not None and atual.estado.nome == regua.PRECISA_REVISAR:
            motivos.append(
                f"{POR_DESEMPENHO}: {atual.estado.porcentagem}% em "
                f"{atual.estado.respostas}")

        # A ancora do 1-7-30: o ultimo estudo (li a teoria de novo, a conta
        # recomeca) ou, sem estudo nenhum, o PRIMEIRO contato pratico.
        desde = atual.ultimo_estudo or atual.primeira_pratica
        if desde is not None:
            certas = acertos_por_no.get(caminho, [])
            etapa, vence_em = _etapa_e_vencimento(desde, certas, hoje)
            if vence_em <= hoje:
                motivos.append(f"{POR_PRAZO} ({INTERVALOS[etapa - 1]} dia(s))")
            else:
                vence_em, etapa = None, None

        if not motivos:
            continue
        fila.append(ParaRevisar(
            caminho=caminho, nome=atual.nome, nivel=atual.nivel,
            motivos=motivos, vence_em=vence_em, etapa=etapa,
            erradas=list(erradas_por_no.get(caminho, [])),
            erros_do_caderno=list(caderno_por_no.get(caminho, [])),
            estado=atual.estado,
        ))

    # Mais atrasado primeiro; depois o no mais fundo, que e o mais acionavel.
    fila.sort(key=lambda r: (-r.atraso, -len(arvore.partes(r.caminho)), r.caminho))
    return fila


def _dias_de_acerto_por_no(hoje: date) -> dict[str, list[date]]:
    """{caminho: dias em que eu acertei questao dele}. Faz o 1-7-30 andar."""
    de_quem = por_conteudo.nos_das_questoes()
    saida: dict[str, list[date]] = {}
    for chave, acertou, dia in por_conteudo._questoes_respondidas(None, hoje):
        if not acertou:
            continue
        caminho = de_quem.get(chave)
        if not caminho:
            continue
        for ancestral in _ancestrais(caminho):
            saida.setdefault(ancestral, []).append(dia)
    return saida


def _erradas_por_no() -> dict[str, list[int]]:
    """{caminho: [ids das questoes reais erradas na ultima resposta]}."""
    from sqlalchemy import select

    from radar.db import criar_tabelas, sessao
    from radar.models import QuestaoDeProva
    from radar.servico import simulado as treino
    from radar.servico.classificacoes import chave_de

    ids = treino.questoes_erradas()
    if not ids:
        return {}
    criar_tabelas()
    with sessao() as s:
        questoes = list(s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.id.in_(ids))))
    de_quem = por_conteudo.nos_das_questoes()
    saida: dict[str, list[int]] = {}
    for questao in questoes:
        caminho = de_quem.get(chave_de(questao))
        if not caminho:
            continue
        for ancestral in _ancestrais(caminho):
            saida.setdefault(ancestral, []).append(questao.id)
    return saida


def _caderno_por_no(hoje: date) -> dict[str, list]:
    """{caminho: [erros do caderno ligados ao no e ainda para rever]}."""
    saida: dict[str, list] = {}
    for erro in caderno.para_rever(hoje):
        if not erro.conteudo:
            continue
        for ancestral in _ancestrais(erro.conteudo):
            saida.setdefault(ancestral, []).append(erro)
    return saida


# --- questoes a refazer ---------------------------------------------------------

@dataclass
class Refazer:
    """O que refazer: as erradas no radar e as do caderno de erros.

    As duas listas ficam separadas de proposito. A questao errada no radar eu
    refaco respondendo; o erro do caderno eu refaco relendo a regra que eu
    escrevi. Somar as duas daria um numero que nao corresponde a nenhuma acao.
    """

    #: [ids] das questoes reais erradas na ultima resposta.
    do_radar: list = field(default_factory=list)
    #: Os erros do caderno que estao para rever hoje.
    do_caderno: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.do_radar) + len(self.do_caderno)

    @property
    def vazio(self) -> bool:
        return not self.total


def refazer(caminho: str | None = None, hoje: date | None = None) -> Refazer:
    """O que refazer, de um no (e dos abaixo dele) ou de tudo."""
    hoje = hoje or date.today()
    from radar.servico import simulado as treino

    if caminho is None:
        return Refazer(do_radar=treino.questoes_erradas(),
                       do_caderno=caderno.para_rever(hoje))
    return Refazer(do_radar=_erradas_por_no().get(caminho, []),
                   do_caderno=_caderno_por_no(hoje).get(caminho, []))


def refazer_do_escopo(dentro, hoje: date | None = None) -> Refazer:
    """O que refazer num escopo de VARIOS nos (a ficha de estudo, Etapa 6B).

    As mesmas duas listas do `refazer`, juntando os nos do escopo. Como cada
    lista ja traz o no e os de cima dele, uma questao aparece em mais de um
    no: aqui ela entra uma vez so.
    """
    hoje = hoje or date.today()
    do_radar: list = []
    for caminho, ids in _erradas_por_no().items():
        if dentro(caminho):
            do_radar.extend(i for i in ids if i not in do_radar)
    do_caderno: list = []
    for caminho, erros_do_no in _caderno_por_no(hoje).items():
        if dentro(caminho):
            do_caderno.extend(e for e in erros_do_no
                              if all(e.id != j.id for j in do_caderno))
    return Refazer(do_radar=do_radar, do_caderno=do_caderno)
