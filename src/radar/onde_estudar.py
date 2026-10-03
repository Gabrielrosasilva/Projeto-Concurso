"""Por qual ASSUNTO comecar hoje, e quanto ele vale em ponto de prova.

A tabela de materias do Meu foco ja responde "que materia pesa mais" e "onde
eu vou pior". Falta a pergunta que decide a tarde de estudo: **dentro da
materia, qual assunto?** Direitos Humanos vale 15 questoes, mas estudar
"Direitos Humanos" nao e um plano - estudar as Regras de Mandela e.

A conta e esta, e ela cabe em duas linhas:

    questoes esperadas = quantas questoes o edital reserva para a materia
                         x a fatia que aquele assunto ocupa nas provas DO CARGO
    pontos a ganhar    = questoes esperadas x (1 - meu acerto no simulado)

O acervo complementar (as provas FEPESE ACEITAS no data/acervo_complementar.json)
nunca entra nesses dois numeros: a regra inviolavel 1 do novo.md nao deixa a
incidencia do alvo e a do complementar virarem um numero so. Ele entra so na
ORDEM, com o peso declarado no config/prioridade.yml (a §15 e a decisao 44 da
prioridade das fichas): o tamanho que ordena e

    peso da materia x (fatia no alvo + peso do complementar x fatia no complementar)

e a tela mostra as duas fatias separadas, com o peso escrito.

"Pontos a ganhar" e o que eu deixo na mesa hoje. Um assunto de 10 questoes em
que eu acerto 90% vale 1 ponto a recuperar; um de 4 questoes em que eu acerto
25% vale 3. O segundo e onde a tarde rende mais, e nenhum dos dois numeros
sozinho diria isso.

Este arquivo nao fala com banco nem com rede: recebe contagem e devolve
numero, como o `macetes`. Quem varre o acervo e o `foco`.

REGRA DE SEMPRE: nunca inventar. Assunto sem simulado fica com `acerto=None` e
`pontos=None` - e NAO com zero por cento, que diria que eu errei tudo quando o
que houve foi eu nao ter treinado. A tela diz isso com todas as letras.
"""
from dataclasses import dataclass
from datetime import date

from radar import amostra as regua
from radar.leis import Lei, do_assunto
from radar.regioes import normalizar

# Quantas linhas cabem na tela. O programa do edital de 2019 tem 70 assuntos, e
# setenta barras nao sao um grafico - sao uma lista telefonica. O que sobra vira
# uma linha de rodape dizendo quantos ficaram de fora.
NA_TELA = 12

# Quantas respostas precisa ter para o acerto virar MEDIDA. Com menos que
# isso, a porcentagem e sorte: acertar a unica questao que fiz diz "100%", e
# errar diz "0%" - e nenhum dos dois diz o que eu sei. Abaixo do minimo a
# regra e a mesma em toda tela: o numero aparece com o rotulo "amostra
# pequena", e NAO entra em conta nem ordenacao nenhuma. O item e tratado como
# "ainda nao treinado": entra pelo peso (ou pelas questoes esperadas), e o
# fator de tempo fica neutro.
#
# O minimo nao mora mais aqui: ele vem do config/amostra.yml, pelo
# `radar.amostra` (Etapa 4). Este arquivo continua puro - quem chama passa os
# minimos, e sem eles valem os da decisao 6.


def e_amostra_pequena(respondidas: int, minimo: int) -> bool:
    """Tem resposta, mas pouca: o numero aparece, e nao conta."""
    return 0 < respondidas < minimo


# O FATOR DE TEMPO da formula da especificacao:
#
#     prioridade = incidencia x (1 - meu acerto) x fator de tempo
#
# Ele cresce com os dias desde a ultima vez que eu respondi o assunto: 1 no
# dia, 2 depois de `DIAS_PARA_DOBRAR` dias, e para ai. Esquecer e o que o tempo
# faz, e o assunto que eu nao vejo ha um mes precisa subir na fila mesmo que
# meu acerto nele fosse bom.
#
# **Sem treino, o fator e neutro (1)**: nao ha "ultima revisao" para contar
# dias, e inventar uma seria dar peso a um assunto por um motivo que nao
# existe. O assunto entra pelo peso e pelo "ainda nao treinado".
DIAS_PARA_DOBRAR = 30
FATOR_MAXIMO = 2.0


def fator_de_tempo(ultima: date | None, hoje: date | None = None,
                   dias_para_dobrar: int = DIAS_PARA_DOBRAR,
                   maximo: float = FATOR_MAXIMO) -> float:
    """1 sem treino; de 1 a 2 conforme os dias desde a ultima resposta.

    Os dois numeros podem vir de fora: a prioridade da ficha de estudo (Etapa
    6B) os le do config/prioridade.yml. Sem eles, valem os desta tela.
    """
    if ultima is None:
        return 1.0
    dias = max(0, ((hoje or date.today()) - ultima).days)
    return min(maximo, 1 + dias / dias_para_dobrar)


# De onde saiu o nome do assunto. Nao e detalhe de implementacao: uma origem
# custou dinheiro e a outra nao, e a tela mostra qual e qual.
CATALOGO, EDITAL = "catalogo", "edital"


@dataclass(frozen=True)
class LinhaDeEstudo:
    """Um assunto do programa, e quanto ele vale em ponto de prova."""

    materia: str
    assunto: str

    #: Quantas questoes o edital reserva para a materia inteira.
    questoes_no_edital: int

    #: Em quantas questoes cada fatia se apoia, uma por evidencia, e nunca
    #: somadas (regra inviolavel 1). As proprias sao as provas do meu cargo
    #: no meu estado - so duas existem. O complementar e o das provas FEPESE
    #: aceitas no acervo complementar (Etapa 3B).
    proprias: int
    complementar: int
    #: Os denominadores das duas fatias: as marcas de assunto da materia nas
    #: provas do cargo, e no complementar.
    base_do_alvo: int
    base_do_complementar: int

    #: O peso da materia vezes a fatia no ALVO. Fracionado de proposito: dizer
    #: "3,8 questoes" e mais honesto que arredondar para 4 e parecer contagem.
    #: O complementar nunca entra aqui.
    esperadas: float

    #: Meu acerto naquele assunto, em porcento. None = nunca treinei.
    acerto: float | None
    respondidas: int

    #: esperadas x (1 - acerto). None quando nao ha acerto medido.
    pontos: float | None

    origem: str
    lei: Lei | None = None
    #: A data da ultima resposta minha no assunto. None = nunca treinei.
    ultima: date | None = None
    #: O fator de tempo, ja calculado para hoje. 1 sem treino.
    fator: float = 1.0
    #: Quantas eu acertei, como veio da conta (`servico.metricas`) - e nao de
    #: volta da porcentagem, que arredonda e pode dizer outro numero.
    acertos: int = 0
    #: O minimo que esta linha precisava ter para o acerto virar medida. Vem
    #: do config/amostra.yml e viaja NA LINHA, para a tela escrever o mesmo
    #: numero que fez a conta.
    minimo: int = regua.PADRAO.do_nivel("assunto")
    #: O peso declarado do complementar na ORDEM (config/prioridade.yml). Zero
    #: quer dizer que a ordem e so a do alvo.
    peso_do_complementar: float = 0.0
    #: "radar 70% em 10 · anotado 73% em 15" (decisao 7): o que a tela mostra
    #: do meu acerto. O `acerto` acima junta os dois so para a conta da ordem
    #: e da amostra - a tela nunca o mostra sozinho. None sem resposta.
    divisao: str | None = None

    @property
    def amostra_pequena(self) -> bool:
        return e_amostra_pequena(self.respondidas, self.minimo)

    @property
    def dias_sem_revisar(self) -> int | None:
        return None if self.ultima is None else (date.today() - self.ultima).days

    @property
    def fatia_no_alvo(self) -> float:
        return _fatia(self.proprias, self.base_do_alvo)

    @property
    def fatia_no_complementar(self) -> float:
        return _fatia(self.complementar, self.base_do_complementar)

    @property
    def tamanho(self) -> float:
        """O que ordena a lista antes do acerto: o peso da materia vezes a fatia
        no alvo e, com o peso declarado, a do complementar. E regra de
        priorizacao, e nao incidencia - por isso nao aparece como numero de
        questoes na tela, e as duas fatias aparecem separadas."""
        return self.questoes_no_edital * (
            self.fatia_no_alvo + self.peso_do_complementar * self.fatia_no_complementar)

    @property
    def so_no_complementar(self) -> bool:
        """O assunto nunca caiu nas provas do cargo: esta na lista so pelo
        complementar, e sem questao esperada nenhuma."""
        return not self.proprias

    @property
    def repete_a_materia(self) -> bool:
        """O assunto do programa ja diz o nome da materia?

        Tem materia do edital que e uma lei so, e ai o assunto do programa
        repete o nome dela: "Lei de Execução Penal (Lei nº 7.210 ...)" dentro
        da materia "Lei de Execução Penal". Mostrar as duas daria uma linha que
        se gagueja, e por isso a tela e a frase de conclusao perguntam isto.
        """
        return normalizar(self.materia) in normalizar(self.assunto)

    @property
    def ordem(self) -> float:
        """Por onde a lista e ordenada, do maior para o menor.

        Com acerto medido, e o tamanho vezes o que eu ainda erro, vezes o
        fator de tempo. Sem acerto, e o proprio tamanho - o teto do que o
        assunto poderia valer: e o unico palpite que nao precisa de dado que
        eu nao tenho, e o fator fica neutro.

        Com o peso do complementar em zero, o tamanho e as questoes esperadas
        e a ordem e a de antes: pontos a ganhar x fator.
        """
        if self.pontos is None:
            return self.tamanho
        return self.tamanho * (1 - self.acerto / 100) * self.fator


def _fatia(marcas: int, base: int) -> float:
    return marcas / base if base else 0.0


def montar(
    materias_do_edital: list,
    contagens: dict[tuple[str, str], tuple[int, int]],
    acertos: dict[tuple[str, str], tuple[int, int]],
    origens: dict[str, str],
    ultimas: dict[tuple[str, str], date] | None = None,
    hoje: date | None = None,
    minimos: regua.Minimos | None = None,
    peso_do_complementar: float = 0.0,
    divisoes: dict[tuple[str, str], str] | None = None,
) -> list[LinhaDeEstudo]:
    """As linhas ordenadas por quanto ha para ganhar em cada assunto.

    - `materias_do_edital`: o quadro lido do PDF, que da o peso de cada materia;
    - `contagens`: {(materia, assunto): (proprias, complementar)}, em
      enunciados distintos - o complementar so das provas aceitas;
    - `acertos`: {(materia, assunto): (respondidas, acertos)}, do simulado;
    - `origens`: {materia: "catalogo" ou "edital"};
    - `peso_do_complementar`: o do config/prioridade.yml; zero, a ordem e so
      a do alvo;
    - `divisoes`: {(materia, assunto): "radar X% em N · anotado Y% em M"}, o
      que a tela escreve no lugar de um acerto somado.

    Materia que nao esta no quadro do edital fica de fora: sem o peso dela nao
    ha "questoes esperadas" nenhuma, e inventar um peso e justamente o que
    faria eu estudar a materia errada por meses.
    """
    minimo = (minimos or regua.PADRAO).do_nivel("assunto")
    peso_da_materia = {m.nome: m.questoes for m in materias_do_edital}

    # Cada base e a soma das marcas da PROPRIA materia, e nao o total do
    # acervo: a fatia responde "quanto desta materia e este assunto". E sao
    # duas bases, uma por evidencia - somar as duas e o que a regra 1 proibe.
    base_do_alvo: dict[str, int] = {}
    base_do_complementar: dict[str, int] = {}
    for (materia, _assunto), (proprias, complementar) in contagens.items():
        base_do_alvo[materia] = base_do_alvo.get(materia, 0) + proprias
        base_do_complementar[materia] = base_do_complementar.get(materia, 0) + complementar

    linhas = []
    for (materia, assunto), (proprias, complementar) in contagens.items():
        if materia not in peso_da_materia:
            continue

        no_edital = peso_da_materia[materia]
        if not no_edital:
            continue
        esperadas = no_edital * _fatia(proprias, base_do_alvo.get(materia, 0))
        # Sem marca nenhuma no alvo, o assunto so entra se o complementar
        # pesar na ordem - e entra com zero questao esperada, dizendo isso.
        if not proprias and not (peso_do_complementar and complementar):
            continue

        respondidas, certas = acertos.get((materia, assunto), (0, 0))
        acerto = (certas / respondidas * 100) if respondidas else None
        # Abaixo do minimo, o acerto fica na linha para a tela mostrar - mas
        # nao vira pontos, e sem pontos o fator de tempo fica neutro. Senao 1
        # erro jogava o assunto para o topo por "0%", e 1 acerto o jogava
        # para o fim como se eu dominasse.
        medido = respondidas >= minimo
        pontos = esperadas * (1 - acerto / 100) if medido else None
        ultima = (ultimas or {}).get((materia, assunto)) if medido else None

        linhas.append(LinhaDeEstudo(
            materia=materia,
            assunto=assunto,
            questoes_no_edital=no_edital,
            proprias=proprias,
            complementar=complementar,
            base_do_alvo=base_do_alvo.get(materia, 0),
            base_do_complementar=base_do_complementar.get(materia, 0),
            esperadas=esperadas,
            acerto=acerto,
            respondidas=respondidas,
            pontos=pontos,
            origem=origens.get(materia, EDITAL),
            lei=do_assunto(materia, assunto),
            ultima=ultima,
            fator=fator_de_tempo(ultima, hoje),
            acertos=certas,
            minimo=minimo,
            peso_do_complementar=peso_do_complementar,
            divisao=(divisoes or {}).get((materia, assunto)),
        ))

    # Empate desempata pelo assunto mais visto nas provas do cargo, depois no
    # complementar, e por fim pelo nome: duas aberturas seguidas da tela tem
    # que mostrar a mesma ordem.
    linhas.sort(key=lambda l: (-l.ordem, -l.proprias, -l.complementar, l.assunto))
    return linhas


def numero(valor: float, casas: int = 1) -> str:
    """O numero como se escreve em portugues: virgula, e sem zero a toa."""
    texto = f"{valor:.{casas}f}".replace(".", ",")
    return texto[:-2] if texto.endswith(",0") else texto


def _como_chamar(linha: LinhaDeEstudo) -> str:
    """O assunto, com a materia entre parenteses so quando ela acrescenta algo."""
    if linha.repete_a_materia:
        return linha.assunto
    return f"{linha.assunto} ({linha.materia})"


def conclusao(linhas: list[LinhaDeEstudo]) -> str | None:
    """Uma frase montada dos numeros da primeira linha. Nunca inventada.

    Ela nao acrescenta nada ao grafico: diz em portugues o que a primeira
    barra ja diz em pixel. Existe porque o grafico responde "qual e o maior" e
    a frase responde "e dai?" - e e a segunda que faz eu abrir a apostila.

    None quando nao ha linha nenhuma: sem numero nao ha conclusao, e escrever
    uma mesmo assim seria inventar.
    """
    if not linhas:
        return None

    primeira = linhas[0]
    onde = _como_chamar(primeira)

    # O primeiro da ordem pode estar ali so pelo complementar: entao a frase
    # diz isso, com os numeros dele, e nao inventa questao esperada do cargo.
    if primeira.so_no_complementar:
        return (
            f"{onde} vem primeiro pelo acervo complementar: "
            f"{primeira.complementar} de {primeira.base_do_complementar} marcas "
            f"de assunto da matéria nas provas aceitas, com peso "
            f"{numero(primeira.peso_do_complementar, 2)} na ordem. Nas provas do "
            f"cargo ele não apareceu - não há questão esperada dele."
        )

    # Sem pontos, a frase NAO cita porcentagem: com amostra insuficiente ela
    # seria sorte dita em voz alta, justamente o que o minimo existe para evitar.
    if primeira.pontos is None:
        if primeira.respondidas:
            de_onde = f" ({primeira.divisao})" if primeira.divisao else ""
            medida = (f"Respondi só {primeira.respondidas} questão(ões) dele{de_onde} "
                      f"- {regua.INSUFICIENTE.lower()}, abaixo das {primeira.minimo} "
                      f"que fazem o acerto valer")
        else:
            medida = "Eu ainda não respondi nenhuma questão dele, nem no radar nem anotada"
        return (
            f"{onde} vem primeiro na ordem: "
            f"{numero(primeira.esperadas)} questões esperadas pelas provas do cargo. "
            f"{medida}, então não dá para dizer quanto há a ganhar - vale "
            f"medir antes de escolher por onde começar."
        )

    if primeira.divisao:
        # Os dois recortes, cada um com o seu numero (decisao 7): a soma dos
        # dois so fez a conta dos pontos.
        return (
            f"{onde} vem primeiro na ordem: {numero(primeira.esperadas)} questões "
            f"esperadas pelas provas do cargo, e o meu acerto nele é "
            f"{primeira.divisao} - são {numero(primeira.pontos)} pontos a ganhar."
        )
    return (
        f"{onde} vem primeiro na ordem: {numero(primeira.esperadas)} questões "
        f"esperadas pelas provas do cargo, e eu acerto "
        f"{numero(primeira.acerto, 0)}% delas - são "
        f"{numero(primeira.pontos)} pontos a ganhar."
    )
