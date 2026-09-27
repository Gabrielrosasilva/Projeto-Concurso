"""Minhas materias: quanto eu ja fiz em cada uma, e o quanto falta para a meta.

O recorte e o CICLO que esta no config/cronograma.yml, e nao a vida inteira:
misturar o meu acerto de hoje com o da primeira semana responderia outra
pergunta. A tela diz isso em voz alta.

As regras sao as da etapa E2 (docs/decisoes.md), e as mesmas funcoes:

  * VOLUME e ACERTO somam faixas do plano + estudo extra + respostas no radar;
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
from datetime import date, timedelta

from sqlalchemy import select

from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import (
    EstadoDoDia,
    QuestaoDeProva,
    QuestaoGerada,
    RespostaDeSimulado,
)
from radar.regioes import normalizar
from radar.util import para_local
from radar.servico import cronograma as diario
from radar.servico import erros as caderno
from radar.servico import extra as estudo_extra
from radar.servico import semanas as tela_das_semanas
from radar.servico.compilado import mesma_materia

#: Abaixo disto, a porcentagem nao e leitura: e sorte. 20 questoes sem consulta
#: e o minimo para eu olhar um numero por materia e acreditar nele.
MINIMO_DA_AMOSTRA = 20

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
    questoes: int = 0
    medidas: int = 0
    acertos: int = 0

    @property
    def porcentagem(self) -> int | None:
        return round(100 * self.acertos / self.medidas) if self.medidas else None


@dataclass
class PontoDaSemana:
    """Um ponto do grafico: o acerto sem consulta daquela semana."""
    semana: int
    porcentagem: int | None
    questoes: int


@dataclass
class MateriaNaTela:
    """Um cartao da tela: a materia do edital com tudo o que eu fiz nela."""
    nome: str
    questoes_na_prova: int
    meta: int
    geral: object = None            # Numeros: faixas + extras + radar
    radar: object = None            # so o que o radar mediu, questao por questao
    anotado: object = None          # so o que eu digitei (faixas + extras)
    sem_consulta: object = None     # o que vale para a meta
    geradas: int = 0                # treino de IA: fora de todo acerto
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

    @property
    def meta_em_porcentagem(self) -> int:
        return round(100 * self.meta / self.questoes_na_prova) if self.questoes_na_prova else 0

    @property
    def nunca_estudei(self) -> bool:
        """Nao encostei nesta materia neste ciclo.

        O treino de IA conta AQUI, e so aqui: ele nao mede acerto nenhum, mas
        dizer "ainda nao estudei" depois de eu ter feito 20 questoes geradas
        seria falso - e o cartao cinza some.
        """
        return not (self.geral.questoes or self.minutos or self.aulas_vistas
                    or self.geradas)

    @property
    def amostra_pequena(self) -> bool:
        return self.sem_consulta.medidas < MINIMO_DA_AMOSTRA

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


def _numeros_do_radar(materias: list[str], inicio: date, fim: date):
    """O que o radar mediu por materia no periodo, e o treino de IA a parte.

    Devolve (por_materia, geradas_por_materia, assuntos), com o acerto medido
    questao por questao - aqui nao ha numero digitado.
    """
    criar_tabelas()
    comeco, termino = diario._janela_do_dia(inicio)
    _, fim_utc = diario._janela_do_dia(fim)

    por_materia = {nome: diario.Numeros() for nome in materias}
    geradas = {nome: 0 for nome in materias}
    assuntos: dict[str, dict[str, AssuntoNaMateria]] = {}
    ultima: dict[str, date] = {}

    with sessao() as s:
        respostas = list(s.scalars(
            select(RespostaDeSimulado)
            .where(RespostaDeSimulado.respondida_em.is_not(None))
            .where(RespostaDeSimulado.respondida_em >= comeco)
            .where(RespostaDeSimulado.respondida_em < fim_utc)
        ))
        reais = {q.id: q for q in s.scalars(
            select(QuestaoDeProva).where(QuestaoDeProva.id.in_(
                [r.questao_id for r in respostas if not r.gerada] or [0]))
        )}
        de_ia = {q.id: q for q in s.scalars(
            select(QuestaoGerada).where(QuestaoGerada.id.in_(
                [r.questao_id for r in respostas if r.gerada] or [0]))
        )}

    for resposta in respostas:
        questao = (de_ia if resposta.gerada else reais).get(resposta.questao_id)
        if questao is None:
            continue
        nome = _achar(questao.materia, materias)
        if nome is None:
            continue
        if resposta.gerada:
            # Treino: conta a parte, e em acerto nenhum.
            geradas[nome] += 1
            continue
        por_materia[nome].somar(1, 1 if resposta.acertou else 0)
        quando = para_local(resposta.respondida_em).date()
        if nome not in ultima or quando > ultima[nome]:
            ultima[nome] = quando
        tema = (getattr(questao, "assunto", None) or "").strip()
        if tema:
            alvo = assuntos.setdefault(nome, {}).setdefault(tema, AssuntoNaMateria(tema))
            alvo.questoes += 1
            alvo.medidas += 1
            alvo.acertos += 1 if resposta.acertou else 0
    return por_materia, geradas, assuntos, ultima


def montar(plano=None, hoje: date | None = None) -> tuple[list[MateriaNaTela], Projecao]:
    """Um cartao por materia do edital, na ordem do peso na prova, e a projecao."""
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or diario.hoje_local()
    nomes = [m.nome for m in plano.materias]

    cartoes = {
        m.nome: MateriaNaTela(
            nome=m.nome,
            questoes_na_prova=m.questoes,
            meta=m.meta,
            geral=diario.Numeros(),
            radar=diario.Numeros(),
            anotado=diario.Numeros(),
            sem_consulta=diario.Numeros(),
        )
        for m in plano.materias
    }
    if not cartoes:
        return [], Projecao()

    assuntos: dict[str, dict[str, AssuntoNaMateria]] = {}
    ultima: dict[str, date] = {}
    # O acerto sem consulta por semana, para o grafico: {materia: {semana: Numeros}}
    por_semana: dict[str, dict[int, object]] = {nome: {} for nome in nomes}

    def guardar(nome, tema, questoes, acertos):
        tema = (tema or "").strip()
        if not tema or not questoes:
            return
        alvo = assuntos.setdefault(nome, {}).setdefault(tema, AssuntoNaMateria(tema))
        alvo.questoes += questoes
        if acertos is not None:
            alvo.medidas += questoes
            alvo.acertos += acertos

    def visto_em(nome, quando):
        if nome not in ultima or quando > ultima[nome]:
            ultima[nome] = quando

    # --- as faixas do plano que eu marquei ---------------------------------
    inicio = plano.inicio
    fim = min(plano.fim, hoje)
    estados = {}
    with sessao() as s:
        for estado in s.scalars(select(EstadoDoDia).where(
                EstadoDoDia.data >= inicio, EstadoDoDia.data <= fim)):
            estados[estado.data] = estado

    semana_do_dia = {dia.data: dia.semana for dia in plano.dias}
    for data in _dias_do_ciclo(plano, hoje):
        estado = estados.get(data)
        if estado is None:
            continue
        nivel = diario.nivel_do_dia(plano, data)
        montado = plano_de_estudo.montar_dia(plano, data,
                                             nivel.efetivo if nivel else None)
        for feita in diario.valores_das_faixas(montado, estado).values():
            nome = _achar(feita.materia, nomes)
            if nome is None:
                continue          # faixa mista, ou sem materia: conta no geral
            cartoes[nome].minutos += feita.minutos or 0
            visto_em(nome, data)
            if not feita.questoes:
                continue
            cartoes[nome].geral.somar(feita.questoes, feita.acertos)
            cartoes[nome].anotado.somar(feita.questoes, feita.acertos)
            guardar(nome, feita.assunto, feita.questoes, feita.acertos)
            if not feita.consulta:
                cartoes[nome].sem_consulta.somar(feita.questoes, feita.acertos)
                semana = semana_do_dia.get(data)
                if semana:
                    alvo = por_semana[nome].setdefault(semana, diario.Numeros())
                    alvo.somar(feita.questoes, feita.acertos)

    # --- o estudo extra -----------------------------------------------------
    for linha in estudo_extra.entre(inicio, fim):
        nome = _achar(linha.materia, nomes)
        if nome is None:
            continue
        cartoes[nome].minutos += linha.minutos or 0
        visto_em(nome, linha.data)
        if not linha.questoes:
            continue
        cartoes[nome].geral.somar(linha.questoes, linha.acertos)
        cartoes[nome].anotado.somar(linha.questoes, linha.acertos)
        guardar(nome, linha.assunto, linha.questoes, linha.acertos)
        if not linha.consulta:
            cartoes[nome].sem_consulta.somar(linha.questoes, linha.acertos)
            semana = semana_do_dia.get(linha.data)
            if semana:
                alvo = por_semana[nome].setdefault(semana, diario.Numeros())
                alvo.somar(linha.questoes, linha.acertos)

    # --- o que o radar mediu ------------------------------------------------
    do_radar, geradas, assuntos_do_radar, ultima_do_radar = _numeros_do_radar(
        nomes, inicio, fim)
    for nome in nomes:
        numeros = do_radar[nome]
        cartoes[nome].radar = numeros
        cartoes[nome].geradas = geradas[nome]
        cartoes[nome].geral.questoes += numeros.questoes
        cartoes[nome].geral.medidas += numeros.medidas
        cartoes[nome].geral.acertos += numeros.acertos
        # O simulado do radar e sempre sem consulta: nao ha lei aberta ali.
        cartoes[nome].sem_consulta.questoes += numeros.questoes
        cartoes[nome].sem_consulta.medidas += numeros.medidas
        cartoes[nome].sem_consulta.acertos += numeros.acertos
        if nome in ultima_do_radar:
            visto_em(nome, ultima_do_radar[nome])
        for tema, achado in assuntos_do_radar.get(nome, {}).items():
            alvo = assuntos.setdefault(nome, {}).setdefault(tema, AssuntoNaMateria(tema))
            alvo.questoes += achado.questoes
            alvo.medidas += achado.medidas
            alvo.acertos += achado.acertos

    # --- o programa andando, os erros e o grafico ---------------------------
    aulas = _aulas_do_plano(plano, nomes)
    vistas = _aulas_vistas(plano, nomes, estados, hoje)
    do_caderno = caderno.listar(situacao="todos", hoje=hoje)
    semanas_do_ciclo = sorted({d.semana for d in plano.dias if d.data <= hoje})

    for nome, cartao in cartoes.items():
        cartao.aulas_no_plano = aulas.get(nome, 0)
        cartao.aulas_vistas = vistas.get(nome, 0)
        cartao.ultima_vez = ultima.get(nome)
        cartao.assuntos = _ordenar_assuntos(assuntos.get(nome, {}))
        cartao.erros_no_caderno, cartao.motivo_mais_comum = _erros(do_caderno, nome)
        cartao.semanal = [
            PontoDaSemana(
                semana,
                por_semana[nome].get(semana).porcentagem if semana in por_semana[nome] else None,
                por_semana[nome][semana].questoes if semana in por_semana[nome] else 0,
            )
            for semana in semanas_do_ciclo
        ]
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
