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

A faixa liga-se ao no pela chave `conteudo`. A que nao a tem conta no que
cobre - os `nos` do plano, e os da ficha depois de conferida -, mas so para
estudado, praticado e as datas: o acerto dela nao vai a no nenhum, porque nao
se sabe de qual dos cobertos ele e (decisao 81).

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
     ou da ultima pratica. Passa de etapa com o acerto no radar e com a
     revisao feita fora dele (o R+7, o extra de revisao), no vencimento ou
     depois (decisao 82); feita a de 30 dias, o prazo acaba.

Um no pode disparar por mais de um; a lista guarda todos os motivos. **Esta e
a unica fila de revisao** (decisao 128): o Meu desempenho a mostra inteira, e
a home e a rodada de revisao, so as pontas dela (`pontas`). "Questoes
a refazer" sao as erradas no radar mais as do caderno de erros - as duas
listas que ja existem, nunca uma terceira.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from radar import amostra as regua
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar import fichas
from radar.regioes import normalizar
from radar.servico import conteudos as servico_conteudos
from radar.servico import desempenho_por_conteudo as por_conteudo
from radar.servico import erros as caderno
from radar.servico import espacada
from radar.servico import fichas as servico_fichas
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


@dataclass(frozen=True)
class Semana:
    """Uma semana da evolucao de um no (a "evolucao por assunto" da secao 19)."""

    numero: int
    #: O acerto sem consulta, em questao real: as contas da tela Semanas.
    porcentagem: int
    #: Quantas respostas mediram esse acerto.
    respostas: int
    #: Chegou ao minimo do nivel do no no config/amostra.yml? Abaixo dele o
    #: numero aparece, mas e pouco para dizer se eu melhorei.
    suficiente: bool


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
    #: A ultima revisao (decisao 79): faixa de revisao do plano ou estudo
    #: extra de revisao anotados no no, ou questao dele respondida numa rodada
    #: que revisa - a revisao espacada e as erradas. Questao de rodada comum e
    #: pratica, nao revisao. None = nunca revisei.
    ultima_revisao: date | None = None
    #: Os dias de revisao feita FORA do radar (a faixa de revisao, o extra de
    #: revisao). No vencimento ou depois, cada um passa o 1-7-30 para a etapa
    #: seguinte, como o acerto no radar (decisao 82). A rodada de revisao do
    #: radar nao entra aqui: ela anda pelo acerto, e errar nela nao e passar.
    revisoes_fora_do_radar: list = field(default_factory=list)

    minutos: int = 0
    #: O desempenho do no, quando ele tem resposta. None quando nao tem.
    desempenho: object = None
    estado: regua.Estado | None = None
    #: [Semana], da mais velha a mais nova - as mesmas contas da Semanas.
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

    # --- o historico: as faixas, o estudo extra e as respostas do radar -----
    # A faixa e o extra chegam ao no que eu escolhi ao anotar; a resposta do
    # radar, ao no da classificacao da questao.
    de_quem = por_conteudo.nos_das_questoes()
    escritas = servico_fichas.carregar()
    inicio = plano.inicio
    fim = min(plano.fim, hoje) if plano.fim else hoje
    por_semana: dict[str, dict[int, list]] = {}
    for linha in metricas.lancamentos(inicio, fim, plano):
        if linha.origem == metricas.RADAR:
            onde = de_quem.get(linha.chave) if linha.chave else None
        else:
            onde = linha.conteudo
        if not onde:
            if linha.origem == metricas.FAIXA and linha.faixa is not None:
                # Faixa sem `conteudo`: conta no que ela cobre, so para a
                # situacao e as datas. O acerto fica fora - nao se sabe de
                # qual dos nos cobertos ele e (decisao 81).
                cobertos = _o_que_a_faixa_cobre(linha.faixa, escritas, situacao)
                for caminho in {a for no in cobertos for a in _ancestrais(no)}:
                    if caminho in situacao:
                        _situacao_e_datas(situacao[caminho], linha)
            continue
        semana = _semana_de(plano, linha.data)
        for caminho in _ancestrais(onde):
            atual = situacao.get(caminho)
            if atual is None:
                continue
            if semana is not None:
                # TODA resposta, e nao so a ultima de cada questao: a evolucao
                # e o historico - errar e depois acertar e o que ela mostra.
                por_semana.setdefault(caminho, {}).setdefault(semana, []).append(linha)
            if linha.origem == metricas.RADAR:
                # O "praticado" do radar sai das ultimas respostas, abaixo;
                # daqui so a revisao.
                if linha.revisao:
                    atual.ultima_revisao = _mais_nova(atual.ultima_revisao, linha.data)
                continue
            atual.minutos += linha.minutos
            _situacao_e_datas(atual, linha)

    # --- as respostas do radar --------------------------------------------
    # TODA resposta, e nao so a ultima de cada questao: a questao refeita nao
    # pode empurrar o primeiro contato, que e a ancora do 1-7-30 (decisao 85).
    for chave, _, dia in por_conteudo._questoes_respondidas(None, hoje, todas=True):
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

    # --- o desempenho, o estado e a evolucao ------------------------------
    minimos = regua.carregar()
    medido = por_conteudo.por_no(recorte, plano, hoje)
    for caminho, atual in situacao.items():
        no = medido.get(caminho)
        if no is not None:
            atual.desempenho = no
            atual.estado = no.estado(minimos)
        atual.semanal = _evolucao(por_semana.get(caminho, {}),
                                  minimos.do_nivel(atual.nivel))
    return situacao


def _situacao_e_datas(atual: Situacao, linha) -> None:
    """O que uma faixa ou um extra diz de um no: estudado ou praticado, e
    quando. Nada de acerto aqui."""
    if linha.revisao:
        atual.ultima_revisao = _mais_nova(atual.ultima_revisao, linha.data)
        atual.revisoes_fora_do_radar.append(linha.data)
    if linha.questoes:
        atual.praticado = True
        atual.primeira_pratica = _mais_velha(atual.primeira_pratica, linha.data)
        atual.ultima_pratica = _mais_nova(atual.ultima_pratica, linha.data)
    elif _e_estudo(linha):
        # Faixa de estudo ou extra de teoria ou de lei seca: foi leitura, e
        # e isto que faz o conteudo "estudado" (decisao 20). A revisao sem
        # questao fica de fora: contar como estudo reiniciaria o 1-7-30, em
        # vez de passar de etapa.
        atual.estudado = True
        atual.primeiro_estudo = _mais_velha(atual.primeiro_estudo, linha.data)
        atual.ultimo_estudo = _mais_nova(atual.ultimo_estudo, linha.data)


def _e_estudo(linha) -> bool:
    """A linha sem questao e estudo? So a faixa de ESTUDO e o extra de teoria
    ou de lei seca (decisao 20): a correcao, o Anki e a revisao nao sao."""
    if linha.origem == metricas.FAIXA:
        return linha.tipo in TIPOS_DE_ESTUDO
    return linha.tipo in EXTRA_DE_ESTUDO


def _o_que_a_faixa_cobre(faixa, escritas, arvore_inteira) -> set[str]:
    """Os nos que uma faixa SEM `conteudo` cobre (decisao 81): os `nos` que o
    plano da a ela e, depois que eu confiro a ficha do tema, os da ficha. A
    ficha por conferir nao entra: ate la, o vinculo e so da IA."""
    cobertos = set(getattr(faixa, "nos", ()) or ())
    escrita = fichas.da_faixa(faixa, escritas)
    if escrita is not None and escrita.conferida_em:
        cobertos.update(escrita.nos)
        if not escrita.nos and escrita.assunto:
            # A ficha sem no diz o assunto (e o subassunto) por escrito.
            assunto = arvore.caminho(escrita.materia, escrita.assunto)
            cobertos.add(assunto)
            if escrita.subassunto:
                cobertos.add(arvore.caminho(assunto, escrita.subassunto))
    return {caminho for caminho in cobertos if caminho in arvore_inteira}


def nos_do_erro(faixa, escritas, arvore_inteira) -> list[str]:
    """Os nos a que o erro anotado numa faixa se liga (U21): o `conteudo`
    dela, ou o que ela cobre pela regra da decisao 81 - so o dado meu, nunca a
    ficha por conferir. Sai o no que esta acima de outro da lista (a ficha sem
    no da o assunto E o subassunto): o erro vai ao mais especifico."""
    if getattr(faixa, "conteudo", None):
        nos = {faixa.conteudo} & set(arvore_inteira)
    else:
        nos = _o_que_a_faixa_cobre(faixa, escritas, arvore_inteira)
    return sorted(no for no in nos
                  if not any(outro.startswith(no + arvore.SEPARADOR) for outro in nos))


def nos_do_erro_das_faixas(blocos) -> dict:
    """{(bloco, indice): [nos]} das faixas do dia que tem no para o erro.
    Barato: le o arquivo das fichas e os caminhos da arvore, sem contar nada."""
    escritas = servico_fichas.carregar()
    caminhos = set(servico_conteudos.caminhos())
    saida = {}
    for bloco in blocos:
        for indice, faixa in enumerate(bloco.faixas):
            nos = nos_do_erro(faixa, escritas, caminhos)
            if nos:
                saida[(bloco.chave, indice)] = nos
    return saida


def _evolucao(por_semana: dict[int, list], minimo: int) -> list[Semana]:
    """As semanas de um no, pela conta do `metricas` - a mesma da tela
    Semanas. Semana em que nada mede o acerto (so consulta, ou sem acerto
    anotado) nao entra."""
    saida = []
    for numero, linhas in sorted(por_semana.items()):
        conta = metricas.contar(linhas).sem_consulta
        if conta.medidas:
            saida.append(Semana(numero, conta.porcentagem, conta.medidas,
                                suficiente=conta.medidas >= minimo))
    return saida


def _mais_nova(atual: date | None, nova: date) -> date:
    return nova if atual is None or nova > atual else atual


def _mais_velha(atual: date | None, nova: date) -> date:
    return nova if atual is None or nova < atual else atual


def nao_estudados(plano=None, hoje: date | None = None,
                  todas: dict | None = None) -> list[Situacao]:
    """Os nos em que eu nunca encostei, de cima para baixo na arvore.

    Materia inteira nao estudada aparece como materia: listar os 20 assuntos
    dela um por um nao e informacao, e lista telefonica. Por isso o filho de
    um nao estudado nao entra.

    `todas` sao as situacoes ja montadas, para a tela que tambem as mostra
    nao montar tudo de novo.
    """
    if todas is None:
        todas = situacoes(plano=plano, hoje=hoje)
    virgens = {c for c, s in todas.items()
               if not s.estudado and not s.praticado}
    saida = [todas[c] for c in sorted(virgens)
             if not any(pai in virgens for pai in _ancestrais(c)[:-1])]
    return saida


def estudados_ou_praticados(todas: dict[str, Situacao],
                            materia: str | None = None) -> list[Situacao]:
    """Os nos em que eu ja encostei, na ordem da arvore: as linhas de "Quando
    eu estudei e revisei" no Meu desempenho. A materia vale sem acento e sem
    caixa, como no resto da tela."""
    procurada = normalizar(materia) if materia else None
    return [s for _, s in sorted(todas.items())
            if (s.estudado or s.praticado)
            and (procurada is None or normalizar(s.materia) == procurada)]


# --- a revisao ------------------------------------------------------------------

def _etapa_e_vencimento(desde: date, revisoes_feitas: list[date],
                        hoje: date) -> tuple[int, date | None]:
    """A etapa do 1-7-30 e quando ela vence, contando de `desde`.

    Revisar NA data do vencimento ou depois passa para a proxima etapa; antes
    e treino, nao revisao. Revisao feita e o acerto no radar, ou a revisao
    marcada fora dele (decisao 82). Feita a de 30 dias, o prazo acabou e o
    vencimento e None: sem isso o no voltava para a fila por prazo para
    sempre (decisao 128).
    """
    etapa, vence = 1, desde + timedelta(days=INTERVALOS[0])
    for dia in sorted(revisoes_feitas):
        if dia >= vence:
            if etapa == len(INTERVALOS):
                return etapa, None
            etapa += 1
            vence = dia + timedelta(days=INTERVALOS[etapa - 1])
    return etapa, vence


def para_revisar(plano=None, hoje: date | None = None,
                 recorte: str = por_conteudo.CICLO,
                 todas: dict | None = None) -> list[ParaRevisar]:
    """Os nos que voltaram para a fila hoje, do mais atrasado ao mais novo.

    So no que eu ja estudei ou pratiquei entra: "revisar" o que eu nunca vi
    nao e revisao, e a lista de nao estudados existe para isso.

    `todas` sao as situacoes ja montadas COM O MESMO RECORTE, para a tela que
    tambem as mostra nao montar tudo de novo.
    """
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or date.today()
    if todas is None:
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
            # O R+7 e o extra de revisao andam como o acerto no radar.
            feitas = acertos_por_no.get(caminho, []) + atual.revisoes_fora_do_radar
            etapa, vence_em = _etapa_e_vencimento(desde, feitas, hoje)
            if vence_em is not None and vence_em <= hoje:
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


def pontas(fila: list[ParaRevisar]) -> list[ParaRevisar]:
    """Os nos da fila sem descendente nela, na ordem da fila.

    O erro num subassunto poe na fila ele, o assunto e a materia: contar os
    tres seria contar a mesma revisao tres vezes. A home e a rodada de
    revisao (`espacada.criar_simulado_de_revisao`) usam so a ponta, que e o
    no mais fundo e o mais acionavel; o Meu desempenho mostra a fila inteira.
    """
    caminhos = [r.caminho for r in fila]
    return [r for r in fila
            if not any(c.startswith(r.caminho + arvore.SEPARADOR) for c in caminhos)]


def proxima_revisao(plano=None, hoje: date | None = None,
                    recorte: str = por_conteudo.CICLO,
                    todas: dict | None = None) -> ParaRevisar | None:
    """O proximo prazo do 1-7-30 que ainda nao venceu, para a home dizer
    quando volta a ter revisao. None quando nenhum no estudado tem prazo.

    A mesma conta do prazo da `para_revisar`; entre dois no mesmo dia, o no
    mais fundo.
    """
    plano = plano or plano_de_estudo.carregar()
    hoje = hoje or date.today()
    if todas is None:
        todas = situacoes(recorte=recorte, plano=plano, hoje=hoje)
    acertos_por_no = _dias_de_acerto_por_no(hoje)

    melhor = None
    for caminho, atual in todas.items():
        desde = atual.ultimo_estudo or atual.primeira_pratica
        if not (atual.estudado or atual.praticado) or desde is None:
            continue
        feitas = acertos_por_no.get(caminho, []) + atual.revisoes_fora_do_radar
        etapa, vence_em = _etapa_e_vencimento(desde, feitas, hoje)
        if vence_em is None or vence_em <= hoje:
            continue
        chave = (vence_em, -len(arvore.partes(caminho)), caminho)
        if melhor is None or chave < melhor[0]:
            melhor = (chave, ParaRevisar(caminho=caminho, nome=atual.nome,
                                         nivel=atual.nivel, vence_em=vence_em,
                                         etapa=etapa))
    return None if melhor is None else melhor[1]


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
