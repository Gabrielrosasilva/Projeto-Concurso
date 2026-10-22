"""O fechamento do dia (decisao 189): onde mais errei e o que vem amanha.

O cartao "Como foi o dia" da tela Hoje tinha so o total. Desde a 189 ele olha
para o estudo:

- **onde mais errei**: os temas com mais erros no dia. O radar conta pelo no da
  questao; o anotado (o "fiz X, acertei Y" do Qconcursos), pela faixa. As duas
  origens ficam em linhas proprias, nunca somadas no mesmo tema, e os motivos
  vem do `metricas.motivos_dos_erros`, por origem;
- **amanha**: os temas novos, as revisoes e o simulado do proximo dia do
  plano, e o aviso quando o tema de amanha e do mesmo assunto do que eu mais
  errei hoje.

So agrupa o que o `metricas` ja conta: nenhuma conta nova de acerto, e o
treino de IA fica de fora (ele tem o numero dele).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, time, timedelta

from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar import fichas
from radar.regioes import normalizar
from radar.servico import conteudos as servico_conteudos
from radar.servico import cronograma as diario
from radar.servico import desempenho_por_conteudo as por_conteudo
from radar.servico import erros as caderno
from radar.servico import fichas as servico_fichas
from radar.servico import metricas
from radar.servico import simulado as treino

#: Quantos temas o "onde mais errei" mostra.
MOSTRAR = 3

RADAR = "radar"
ANOTADO = "anotado"

#: O nome curto de cada origem do motivo, na ordem do `metricas`.
ORIGEM_CURTA = {
    "fepese": "FEPESE no radar",
    "outras_bancas": "Outras bancas no radar",
    "geradas": "Treino de IA",
    "fora_do_radar": "Fora do radar",
}

#: O que conta como tema novo e como revisao no dia de amanha.
TIPOS_DE_ESTUDO = {"teoria", "lei_seca", "portugues", "raciocinio"}
TIPOS_QUE_MEDEM = {"simulado", "diagnostico"}


@dataclass
class OndeErrei:
    """Um tema do "onde mais errei": o no da questao, ou a faixa anotada."""

    nome: str
    erros: int
    origem: str                     # RADAR | ANOTADO
    #: O no da arvore, quando se sabe (a questao classificada, o anotado com
    #: `conteudo`). E por ele que o aviso de amanha acha o assunto.
    caminho: str | None = None


@dataclass
class MotivosDaOrigem:
    """Os motivos dos erros de uma origem, como o `metricas` contou."""

    origem: str
    motivos: list[tuple[str, int]]   # (rotulo, quantos), na ordem dos MOTIVOS
    sem_motivo: int


@dataclass
class Amanha:
    """O proximo dia do plano, em poucas linhas."""

    data: date
    #: "Amanhã · terça, 20/10", ou "Próximo dia · ..." depois do sabado.
    titulo: str = ""
    novos: list[str] = field(default_factory=list)
    revisoes: list[str] = field(default_factory=list)
    medem: list[str] = field(default_factory=list)
    questoes: int = 0
    inicio: time | None = None
    #: (o tema que eu mais errei hoje, o titulo da faixa de amanha do mesmo
    #: assunto), ou None.
    continua: tuple[str, str] | None = None


@dataclass
class Fechamento:
    errei: list[OndeErrei]
    motivos: list[MotivosDaOrigem]
    #: Quantas questoes reais erradas no dia, no radar, continuam erradas: o
    #: que o botao "Refazer os erros" traz.
    para_refazer: int
    amanha: Amanha | None

    @property
    def vazio(self) -> bool:
        return not (self.errei or self.motivos or self.amanha)


def do_dia(data: date, plano) -> Fechamento:
    errei = onde_mais_errei(data, plano)
    return Fechamento(
        errei=errei,
        motivos=motivos_do_dia(data),
        para_refazer=len(treino.questoes_erradas(do_dia=data)),
        amanha=amanha(data, plano, errei),
    )


# --- onde mais errei ------------------------------------------------------------

def onde_mais_errei(data: date, plano, mostrar: int = MOSTRAR) -> list[OndeErrei]:
    """Os temas com mais erros no dia, da questao real (radar e anotado)."""
    de_quem = por_conteudo.nos_das_questoes()
    nomes = {no.caminho: no.nome for no in servico_conteudos.nos()}
    no_radar: Counter = Counter()
    anotado: Counter = Counter()
    caminho_de: dict[tuple[str, str], str | None] = {}

    for linha in metricas.lancamentos(data, data, plano):
        if linha.gerada:
            continue
        if linha.origem == metricas.RADAR:
            if linha.acertos:
                continue
            caminho = de_quem.get(linha.chave) if linha.chave else None
            nome = nomes.get(caminho) or f"{linha.materia or 'Sem matéria'} (sem tema)"
            no_radar[nome] += 1
            caminho_de[(RADAR, nome)] = caminho
            continue
        if linha.acertos is None or not linha.questoes:
            continue
        erros = linha.questoes - linha.acertos
        if erros <= 0:
            continue
        if linha.conteudo:
            nome = nomes.get(linha.conteudo) or arvore.partes(linha.conteudo)[-1]
        elif linha.faixa is not None:
            nome = fichas.tema_da_faixa(linha.faixa.titulo, linha.materia)
        else:
            nome = linha.assunto or linha.materia or "Estudo extra"
        anotado[nome] += erros
        caminho_de[(ANOTADO, nome)] = linha.conteudo

    itens = [OndeErrei(nome, n, RADAR, caminho_de[(RADAR, nome)])
             for nome, n in no_radar.items()]
    itens += [OndeErrei(nome, n, ANOTADO, caminho_de[(ANOTADO, nome)])
              for nome, n in anotado.items()]
    itens.sort(key=lambda i: (-i.erros, i.origem != RADAR, i.nome))
    return itens[:mostrar]


def motivos_do_dia(data: date) -> list[MotivosDaOrigem]:
    """Os motivos do dia por origem, so as origens com erro (decisao 174)."""
    contas = metricas.motivos_dos_erros(data, data)
    saida = []
    for origem in metricas.ORIGENS_DO_ERRO:
        conta = contas.get(origem)
        if conta is None or not conta.erros:
            continue
        motivos = [(rotulo, conta.por_motivo[chave])
                   for chave, rotulo in caderno.MOTIVOS.items()
                   if conta.por_motivo.get(chave)]
        saida.append(MotivosDaOrigem(ORIGEM_CURTA.get(origem, origem), motivos,
                                     conta.sem_motivo))
    return saida


# --- amanha ---------------------------------------------------------------------

def proximo_dia(plano, data: date) -> date | None:
    """O proximo dia que o plano tem depois de `data` (o domingo nao tem)."""
    fim = plano.fim or data + timedelta(days=7)
    dia = data + timedelta(days=1)
    while dia <= fim:
        if plano.dia(dia) is not None:
            return dia
        dia += timedelta(days=1)
    return None


def amanha(data: date, plano, errei: list[OndeErrei] | None = None) -> Amanha | None:
    seguinte = proximo_dia(plano, data)
    if seguinte is None:
        return None
    nivel = diario.nivel_do_dia(plano, seguinte, diario.metas_do_plano(plano))
    if nivel is None:
        return None
    dia = plano_de_estudo.montar_dia(plano, seguinte, nivel.efetivo)
    faixas = [f for f in dia.faixas()
              if not f.desligada and f.tipo != "pausa"]
    quando = "Amanhã" if seguinte == data + timedelta(days=1) else "Próximo dia"
    semana = plano_de_estudo.DIAS_DA_SEMANA[seguinte.weekday()].split("-")[0]
    saida = Amanha(data=seguinte, titulo=f"{quando} · {semana}, {seguinte:%d/%m}")
    for faixa in faixas:
        if faixa.tipo in TIPOS_DE_ESTUDO:
            saida.novos.append(faixa.titulo)
        elif faixa.tipo in plano_de_estudo.TIPOS_DE_REVISAO:
            saida.revisoes.append(faixa.titulo)
        elif faixa.tipo in TIPOS_QUE_MEDEM:
            saida.medem.append(faixa.titulo)
        if not faixa.opcional:
            saida.questoes += faixa.questoes or 0
    if faixas:
        saida.inicio = faixas[0].inicio
    saida.continua = _continua(errei or [], faixas)
    return saida


def _continua(errei: list[OndeErrei], faixas) -> tuple[str, str] | None:
    """O tema que eu mais errei hoje volta amanha? Pelo assunto da arvore: o
    no do erro e o assunto que a faixa de amanha diz cobrir (o mesmo
    `onde_na_arvore` que a faixa mostra na tela). So um aviso: nao conta nada.
    """
    if not errei or errei[0].caminho is None:
        return None
    partes = arvore.partes(errei[0].caminho)
    if len(partes) < 2:
        return None
    materia, assunto = normalizar(partes[0]), normalizar(partes[1])
    escritas = servico_fichas.carregar()
    caminhos = set(servico_conteudos.caminhos())
    for faixa in faixas:
        if not faixa.materia or normalizar(faixa.materia) != materia:
            continue
        onde = fichas.onde_na_arvore(
            faixa, fichas.da_faixa_no_dia(faixa, faixas, escritas), caminhos)
        if onde and any(normalizar(a.nome) == assunto for a in onde.assuntos):
            return errei[0].nome, faixa.titulo
    return None
