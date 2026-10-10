"""Minhas materias: quanto eu ja fiz em cada uma, e o quanto falta para a meta.

O recorte e o CICLO que esta no config/cronograma.yml, e nao a vida inteira:
misturar o meu acerto de hoje com o da primeira semana responderia outra
pergunta. A tela diz isso em voz alta.

As regras sao as da etapa E2 (docs/decisoes.md), e as mesmas funcoes:

  * VOLUME e ACERTO saem do `servico.metricas`, a fonte unica: a mesma lista
    de lancamentos do "Fiz hoje" e da tela de Semanas, separada por materia;
  * a barra "voce x meta" usa so questao SEM CONSULTA - na prova nao ha lei
    aberta;
  * questao escrita por IA aparece a parte ("treino IA"), e em acerto nenhum;
  * o nome da materia casa pela regra que o radar ja usa
    (`compilado.mesma_materia`): o caderno de 2013 escreve "Direito Processo
    Penal" e o edital de 2019 "Direito Processual Penal", e os dois sao a
    mesma materia.

Tudo aqui e conta: a tela so mostra.
"""
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select

from radar import amostra as regua
from radar import cronograma as plano_de_estudo
from radar.db import sessao
from radar.models import EstadoDoDia
from radar.regioes import normalizar
from radar.servico import cronograma as diario
from radar.servico import erros as caderno
from radar.origem import TENDENCIA
from radar.servico import metricas
from radar.servico.compilado import mesma_materia

#: Abaixo do minimo, a porcentagem nao e leitura: e sorte. O numero vem do
#: config/amostra.yml, nivel "materia" (Etapa 4) - o mesmo que a home, o Meu
#: foco e o Onde estudar primeiro usam. Antes havia um 20 escrito aqui e um 5
#: no onde_estudar: duas reguas para a mesma duvida.

#: Quantos assuntos o cartao lista. O resto vira "e mais N".
ASSUNTOS_NO_CARTAO = 6

#: As faixas que contam como "aula vista" no programa da materia: as da manha,
#: uma por materia por dia. `lei_seca` fica de fora de proposito - ela e ler a
#: lei do MESMO tema da teoria daquele dia, e contar as duas faria o programa
#: de Direito andar em dobro.
TIPOS_DE_AULA = {"teoria", "portugues", "raciocinio"}


@dataclass
class AssuntoNaMateria:
    """Um tema dentro da materia: o que eu fiz nele e quanto acertei."""
    nome: str
    numeros: metricas.Numeros = field(default_factory=metricas.Numeros)

    @property
    def questoes(self) -> int:
        return self.numeros.questoes

    @property
    def medidas(self) -> int:
        return self.numeros.medidas

    @property
    def acertos(self) -> int:
        return self.numeros.acertos

    @property
    def porcentagem(self) -> int | None:
        return self.numeros.porcentagem


@dataclass
class PontoDaSemana:
    """Um ponto do grafico: o acerto sem consulta daquela semana."""
    semana: int
    porcentagem: int | None
    questoes: int
    #: As respostas com acerto (a base da porcentagem): o n do ponto (P11).
    medidas: int = 0


@dataclass
class MateriaNaTela:
    """Um cartao da tela: a materia do edital com tudo o que eu fiz nela."""
    nome: str
    questoes_na_prova: int
    meta: int
    # Os recortes do `servico.metricas`, so desta materia.
    geral: object = field(default_factory=metricas.Numeros)         # total, com o treino de IA
    radar: object = field(default_factory=metricas.Numeros)         # medido no radar
    anotado: object = field(default_factory=metricas.Numeros)       # faixas + extras
    sem_consulta: object = field(default_factory=metricas.Numeros)  # o que vale para a meta
    # O treino de IA pela 1a vez em cada gerada (decisao 152): o NIVEL, e nao
    # o volume do `geral`. Nunca entra no acerto da materia.
    treino_ia: object = field(default_factory=metricas.TreinoDeIA)
    minutos: int = 0
    ultima_vez: date | None = None
    aulas_vistas: int = 0
    aulas_no_plano: int = 0
    assuntos: list = field(default_factory=list)
    erros_no_caderno: int = 0
    motivo_mais_comum: str | None = None
    semanal: list = field(default_factory=list)
    #: Em que ciclo do mapa ela entra, quando eu ainda nao estudei nada dela.
    ciclo_de_entrada: str | None = None
    #: O minimo de respostas sem consulta deste nivel, do config/amostra.yml.
    minimo: int = regua.PADRAO.do_nivel("materia")

    @property
    def meta_em_porcentagem(self) -> int:
        return round(100 * self.meta / self.questoes_na_prova) if self.questoes_na_prova else 0

    @property
    def nunca_estudei(self) -> bool:
        """Nao encostei nesta materia neste ciclo.

        O treino de IA conta aqui (ele esta no `geral.questoes`): ele nao mede
        acerto nenhum, mas dizer "ainda nao estudei" depois de eu ter feito 20
        questoes geradas seria falso - e o cartao cinza some.
        """
        return not (self.geral.questoes or self.minutos or self.aulas_vistas)

    @property
    def amostra_pequena(self) -> bool:
        return self.sem_consulta.medidas < self.minimo

    @property
    def na_meta(self) -> bool:
        """Ja bati a meta desta materia? So com amostra que sustente a conta."""
        return (not self.amostra_pequena
                and self.sem_consulta.porcentagem >= self.meta_em_porcentagem)

    @property
    def dias_desde_a_ultima_vez(self) -> int | None:
        return None if self.ultima_vez is None else (date.today() - self.ultima_vez).days

    @property
    def acertos_projetados(self) -> float | None:
        """Quantas eu acertaria desta materia na prova, no ritmo de agora."""
        if self.amostra_pequena:
            return None
        return self.sem_consulta.porcentagem * self.questoes_na_prova / 100


@dataclass
class Projecao:
    """Se a prova fosse hoje. E leitura, nao fato - e a tela diz isso."""
    origem = TENDENCIA

    acertos: int = 0
    meta: int = 0
    questoes_da_prova: int = 0
    com_dado: list = field(default_factory=list)
    sem_dado: list = field(default_factory=list)

    @property
    def tem_dado(self) -> bool:
        return bool(self.com_dado)


def _dias_do_ciclo(plano, hoje: date) -> list[date]:
    return [dia.data for dia in plano.dias if dia.data <= hoje]


def _achar(nome: str, materias: list[str]) -> str | None:
    """A materia do edital que casa com este nome, pela regra do radar."""
    if not nome:
        return None
    for do_edital in materias:
        if mesma_materia(do_edital, nome):
            return do_edital
    return None


def _palavras(texto: str) -> list[str]:
    return [p for p in normalizar(texto or "").split() if len(p) >= 4]


#: Quantas letras duas palavras precisam ter em comum, do comeco, para serem a
#: mesma: "processo" e "processual" compartilham sete, e sao. Com menos que
#: isso "especial" e "estadual" virariam a mesma palavra, e sao duas materias.
COMECO_IGUAL = 6


def _mesma_palavra(uma: str, outra: str) -> bool:
    if uma.startswith(outra) or outra.startswith(uma):
        return True
    comum = 0
    for a, b in zip(uma, outra):
        if a != b:
            break
        comum += 1
    return comum >= COMECO_IGUAL


def _mencao_bate(mencao: str, materia: str) -> bool:
    """A mencao do mapa ("Processo Penal") fala desta materia?

    Palavra a palavra, e nao pela regra do `mesma_materia`: o mapa cita a
    materia pelo apelido ("Processo Penal" para "Direito Processual Penal", e
    "Sociologia" para "Sociologia Aplicada"), e apelido nao passa na distancia
    de texto que aquela regra exige. Aqui basta que toda palavra da mencao
    apareca no nome - por isso "Penal" sozinho bate em tres materias, e quem
    chama trata isso como ambiguidade.
    """
    do_nome = _palavras(materia)
    da_mencao = _palavras(mencao)
    if not do_nome or not da_mencao:
        return False
    return all(any(_mesma_palavra(p, m) for p in do_nome) for m in da_mencao)


def ciclo_de_entrada(plano, materia: str, hoje: date) -> str | None:
    """Em que etapa do mapa esta materia entra.

    Primeiro pelo PLANO: se ela tem faixa nos dias gravados, ela entra no ciclo
    daqueles dias - isso e fato, e nao leitura de texto. Sem faixa nenhuma,
    vale a primeira etapa cujo `foco` cita a materia sem ambiguidade. Mencao
    que serve para mais de uma materia ("Penal", que e de tres) nao decide
    nada: melhor nao dizer do que dizer o ciclo errado.
    """
    for dia in plano.dias:
        for faixa in dia.faixas():
            if faixa.materia and mesma_materia(materia, faixa.materia):
                etapa = plano.etapa_do_mapa(dia.data)
                return etapa.nome if etapa else plano.titulo

    nomes = [m.nome for m in plano.materias]
    for etapa in plano.mapa:
        for mencao in _mencoes(etapa.foco):
            candidatas = [n for n in nomes if _mencao_bate(mencao, n)]
            if candidatas == [materia]:
                return etapa.nome
    return None


def _mencoes(foco: str) -> list[str]:
    """As materias citadas na linha do mapa, uma a uma."""
    texto = (foco or "").replace(":", ",").replace("·", ",").replace(" e ", ",")
    return [pedaco.strip() for pedaco in texto.split(",") if pedaco.strip()]


def montar(plano=None, hoje: date | None = None) -> tuple[list[MateriaNaTela], Projecao]:
    """Um cartao por materia do edital, na ordem do peso na prova, e a projecao."""
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or diario.hoje_local()
    nomes = [m.nome for m in plano.materias]

    minimo = regua.carregar().do_nivel("materia")
    cartoes = {
        m.nome: MateriaNaTela(nome=m.nome, questoes_na_prova=m.questoes,
                              meta=m.meta, minimo=minimo)
        for m in plano.materias
    }
    if not cartoes:
        return [], Projecao()

    # A mesma lista de lancamentos que o "Fiz hoje" e a tela de Semanas somam,
    # agora separada por materia. Faixa mista ou sem materia, e resposta a
    # questao de materia que nao casa com o edital, ficam no total do dia e
    # em materia nenhuma.
    inicio = plano.inicio
    fim = min(plano.fim, hoje)
    da_materia: dict[str, list] = {nome: [] for nome in nomes}
    for linha in metricas.lancamentos(inicio, fim, plano):
        nome = _achar(linha.materia, nomes)
        if nome is not None:
            da_materia[nome].append(linha)

    semana_do_dia = {dia.data: dia.semana for dia in plano.dias}
    semanas_do_ciclo = sorted({d.semana for d in plano.dias if d.data <= hoje})
    with sessao() as s:
        estados = {e.data: e for e in s.scalars(select(EstadoDoDia).where(
            EstadoDoDia.data >= inicio, EstadoDoDia.data <= fim))}

    for nome, linhas in da_materia.items():
        cartao = cartoes[nome]
        # A materia da gerada casa pelo mesmo `_achar` dos lancamentos.
        cartao.treino_ia = metricas.treino_ia_de(
            lambda _conteudo, materia, nome=nome: _achar(materia, nomes) == nome)
        conta = metricas.contar(linhas)
        cartao.geral = conta.total
        cartao.radar = conta.radar
        cartao.anotado = conta.anotado
        cartao.sem_consulta = conta.sem_consulta
        cartao.minutos = conta.minutos
        # O treino de IA nao conta como "a ultima vez que estudei a materia":
        # ele nao mede, e a data dele esconderia ha quanto tempo eu nao faco
        # questao de prova.
        datas = [linha.data for linha in linhas if not linha.gerada]
        cartao.ultima_vez = max(datas) if datas else None

        por_tema: dict[str, list] = {}
        for linha in linhas:
            tema = (linha.assunto or "").strip()
            if tema and linha.questoes and not linha.gerada:
                por_tema.setdefault(tema, []).append(linha)
        cartao.assuntos = _ordenar_assuntos({
            tema: AssuntoNaMateria(tema, metricas.contar(das).total)
            for tema, das in por_tema.items()
        })

        # O grafico: o acerto sem consulta de cada semana do ciclo.
        por_semana: dict[int, list] = {}
        for linha in linhas:
            semana = semana_do_dia.get(linha.data)
            if semana:
                por_semana.setdefault(semana, []).append(linha)
        semanal = {semana: metricas.contar(das).sem_consulta
                   for semana, das in por_semana.items()}
        cartao.semanal = [
            PontoDaSemana(semana,
                          semanal[semana].porcentagem if semana in semanal else None,
                          semanal[semana].questoes if semana in semanal else 0,
                          semanal[semana].medidas if semana in semanal else 0)
            for semana in semanas_do_ciclo
        ]

    # --- o programa andando, os erros e o grafico ---------------------------
    aulas = _aulas_do_plano(plano, nomes)
    vistas = _aulas_vistas(plano, nomes, estados, hoje)
    do_caderno = caderno.listar(situacao="todos", hoje=hoje)

    for nome, cartao in cartoes.items():
        cartao.aulas_no_plano = aulas.get(nome, 0)
        cartao.aulas_vistas = vistas.get(nome, 0)
        cartao.erros_no_caderno, cartao.motivo_mais_comum = _erros(do_caderno, nome)
        if cartao.nunca_estudei:
            cartao.ciclo_de_entrada = ciclo_de_entrada(plano, nome, hoje)

    ordenados = sorted(cartoes.values(),
                       key=lambda c: (-c.questoes_na_prova, c.nome))
    return ordenados, projetar(ordenados, plano)


def _ordenar_assuntos(dos_temas: dict) -> list[AssuntoNaMateria]:
    """Do pior acerto para o melhor. Sem acerto medido vai para o fim: ele nao
    e "ruim", e desconhecido - e desconhecido nao disputa o topo da lista."""
    com_nota = [a for a in dos_temas.values() if a.medidas]
    sem_nota = [a for a in dos_temas.values() if not a.medidas]
    com_nota.sort(key=lambda a: (a.porcentagem, -a.questoes, a.nome))
    sem_nota.sort(key=lambda a: (-a.questoes, a.nome))
    return com_nota + sem_nota


def _erros(do_caderno: list, materia: str) -> tuple[int, str | None]:
    """Quantos erros do caderno sao desta materia, e o motivo que mais aparece."""
    meus = [e for e in do_caderno if mesma_materia(materia, e.materia)]
    if not meus:
        return 0, None
    vezes: dict[str, int] = {}
    for erro in meus:
        vezes[erro.motivo] = vezes.get(erro.motivo, 0) + 1
    motivo = max(vezes.items(), key=lambda item: (item[1], item[0]))[0]
    return len(meus), caderno.MOTIVOS.get(motivo, motivo)


def _aulas_do_plano(plano, nomes: list[str]) -> dict[str, int]:
    """Quantas aulas de teoria o ciclo tem de cada materia."""
    total: dict[str, int] = {}
    for dia in plano.dias:
        for faixa in dia.faixas():
            if faixa.tipo not in TIPOS_DE_AULA:
                continue
            nome = _achar(faixa.materia, nomes)
            if nome:
                total[nome] = total.get(nome, 0) + 1
    return total


def _aulas_vistas(plano, nomes: list[str], estados: dict, hoje: date) -> dict[str, int]:
    """Quantas dessas aulas eu ja marquei como feitas."""
    vistas: dict[str, int] = {}
    for dia in plano.dias:
        if dia.data > hoje:
            continue
        estado = estados.get(dia.data)
        if estado is None:
            continue
        nivel = diario.nivel_do_dia(plano, dia.data)
        montado = plano_de_estudo.montar_dia(plano, dia.data,
                                             nivel.efetivo if nivel else None)
        for (bloco, indice) in diario.faixas_feitas(montado, estado):
            faixa = getattr(montado, bloco)[indice]
            if faixa.tipo not in TIPOS_DE_AULA:
                continue
            nome = _achar(faixa.materia, nomes)
            if nome:
                vistas[nome] = vistas.get(nome, 0) + 1
    return vistas


def projetar(cartoes: list[MateriaNaTela], plano) -> Projecao:
    """Se a prova fosse hoje: o % sem consulta de cada materia x as questoes dela.

    Materia sem amostra que sustente a conta fica FORA - ela nao entra como
    zero nem como a media das outras. As duas coisas seriam invencao, e a tela
    prefere dizer quantas materias ficaram de fora.
    """
    projecao = Projecao(meta=plano.meta_total,
                        questoes_da_prova=plano.questoes_da_prova)
    total = 0.0
    for cartao in cartoes:
        previsto = cartao.acertos_projetados
        if previsto is None:
            projecao.sem_dado.append(cartao.nome)
            continue
        projecao.com_dado.append(cartao.nome)
        total += previsto
    projecao.acertos = round(total)
    return projecao


# --- o grafico do acerto por semana --------------------------------------------

#: O tamanho do desenho, em unidades do proprio SVG (ele escala sozinho).
LARGURA = 220
ALTURA = 44


def linha_do_grafico(pontos: list[PontoDaSemana]) -> str | None:
    """Os pontos do SVG ("x,y x,y ..."), ou None quando nao ha o que desenhar.

    Desenhado no SERVIDOR e servido como SVG inline: sem JavaScript, como o
    resto do radar. Semana sem questao sem consulta nao vira ponto - a linha
    pula ela, em vez de fingir um zero que eu nao tirei.
    """
    com_nota = [(i, p) for i, p in enumerate(pontos) if p.porcentagem is not None]
    if len(com_nota) < 2:
        return None
    ultimo = max(len(pontos) - 1, 1)
    return " ".join(
        f"{round(LARGURA * i / ultimo, 1)},"
        f"{round(ALTURA - (ALTURA - 4) * p.porcentagem / 100, 1)}"
        for i, p in com_nota
    )
