"""O que a banca tem costume de cobrar, tirado das provas que ja estao aqui.

Tudo neste arquivo e CONTAGEM em cima do acervo: nada e opiniao, nada e
adivinhado, e todo numero da para conferir abrindo as provas. Onde a conta nao
alcanca - "que pegadinha ela faz", "como memorizar isso" - o arquivo nao
inventa: fica sem resposta ate alguem ler as questoes.

Nao fala com banco nem com rede. Recebe uma lista de questoes e devolve numeros.
"""
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field


# Como a banca costuma formular a pergunta. Isto e o mais proximo de
# "pegadinha" que da para medir: pedir a INCORRETA e o jeito classico de fazer
# quem le rapido marcar a alternativa certa e errar a questao.
PADROES_DE_COMANDO: tuple[tuple[str, str, str], ...] = (
    (
        "pede a INCORRETA",
        # O texto ja chega sem acento, entao "nao" e "nao esta" bastam. O
        # padrao anterior era n[ao], que casa duas letras e nunca pegou
        # "NAO E CORRETA".
        r"incorret|nao\s+(?:e|esta)\s+corret|except|falsa",
        "Le com calma: aqui acertar e achar o ERRO. Marcar a alternativa "
        "verdadeira e o jeito mais comum de perder ponto.",
    ),
    (
        "analise as frases e depois assinale",
        r"analise (?:as|os|o|a)\b",
        "A resposta nao esta em uma frase so: e preciso julgar cada item "
        "antes de olhar as alternativas.",
    ),
    (
        "verdadeiro ou falso",
        r"\(\s*[vf]\s*\)",
        "Um item errado no meio derruba a sequencia inteira. Vale conferir "
        "item por item, e nao a sequencia de uma vez.",
    ),
    (
        "sequencia ou ordem correta",
        r"sequ[e\u00ea]ncia correta|ordem correta",
        "Costuma ter duas alternativas parecidas, diferentes so na ordem de "
        "dois itens do meio.",
    ),
    (
        "completa as lacunas",
        r"____|completa(?:m)? corretamente as lacunas",
        "A banca testa palavras parecidas (deferiu/diferiu, \"a\" e \"à\"). "
        "Conferir lacuna por lacuna elimina alternativa rapido.",
    ),
    (
        "todas as alternativas",
        r"todas as (?:alternativas|afirmativas)",
        "Alternativa do tipo 'todas as anteriores' costuma vir junto: se duas "
        "estao claramente certas, ela e a candidata forte.",
    ),
)


# Palavra que aparece em qualquer enunciado e nao diz nada sobre o assunto.
# Sem esta lista, o topo dos "assuntos" seria "que", "alternativa", "sobre".
PALAVRAS_VAZIAS = frozenset("""
a as o os e ou de do da dos das em no na nos nas por para com sem sob sobre
ao aos as um uma uns umas que qual quais quando onde como porque pois se
nao sim mais menos muito pouco todo toda todos todas outro outra outros outras
seu sua seus suas este esta estes estas esse essa esses essas aquele aquela
isso isto aquilo ele ela eles elas eu voce nos vos lhe lhes me te
ser sao e foi era sera seja sejam esta estao estava estavam tem tem tinha
ha havia pode podem deve devem fazer feito ter haver estar
alternativa alternativas assinale correta correto corretas corretos incorreta
questao questoes analise abaixo seguinte seguintes acordo texto frase frases
item itens afirmativa afirmativas afirmacao afirmacoes considere assunto
apenas somente respectivamente conforme segundo relacao referente base
resposta marque indique julgue verifique leia trecho periodo enunciado
""".split())

MINIMO_DE_LETRAS = 4

# Abaixo disso nao da para dizer nada sobre a letra do gabarito. Buscando
# "crase" saem 59 questoes, mas so 7 enunciados diferentes: qualquer letra que
# aparecesse duas vezes viraria "tendencia" que e so sorteio.
MINIMO_PARA_TENDENCIA = 50


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


@dataclass
class Comando:
    nome: str
    quantas: int
    porcentagem: float
    conselho: str


@dataclass
class Termo:
    palavra: str
    quantas: int


@dataclass
class Repetida:
    enunciado: str
    materia: str | None
    cadernos: int


@dataclass
class Analise:
    """O retrato do recorte pedido: uma banca, um cargo, um tema."""

    total: int = 0
    distintas: int = 0
    materias: list[tuple[str, int]] = field(default_factory=list)
    comandos: list[Comando] = field(default_factory=list)
    termos: list[Termo] = field(default_factory=list)
    repetidas: list[Repetida] = field(default_factory=list)
    gabarito: list[tuple[str, int, float]] = field(default_factory=list)
    gabarito_veredito: str = "amostra_pequena"

    # Preenchidos so quando o tema procurado aponta para uma materia so.
    materia_dominante: str | None = None
    retrato: "RetratoDaMateria | None" = None
    assunto_procurado: "Assunto | None" = None


def contar_comandos(questoes: list) -> list[Comando]:
    """Quantas questoes usam cada forma de perguntar, da mais comum a menos."""
    achados = []
    for nome, padrao, conselho in PADROES_DE_COMANDO:
        quantas = sum(
            1 for q in questoes if re.search(padrao, _sem_acento(q.enunciado), re.I)
        )
        if quantas:
            achados.append(Comando(
                nome=nome,
                quantas=quantas,
                porcentagem=quantas / len(questoes) * 100,
                conselho=conselho,
            ))
    achados.sort(key=lambda c: -c.quantas)
    return achados


def distribuicao_do_gabarito(questoes: list) -> tuple[list[tuple[str, int, float]], str]:
    """Quantas vezes cada letra e a correta, e se vale chutar em alguma.

    Devolve tambem o veredito: "equilibrado", "tendencia" ou "amostra_pequena".
    O resultado costuma ser o contrario do que dizem por ai - quando as cinco
    letras ficam perto de 20%, o "chute na C" nao existe nesta banca.
    """
    letras = Counter(q.resposta for q in questoes if q.resposta)
    total = sum(letras.values())
    if not total:
        return [], "amostra_pequena"

    linhas = [(letra, n, n / total * 100) for letra, n in sorted(letras.items())]
    if total < MINIMO_PARA_TENDENCIA:
        return linhas, "amostra_pequena"

    # Ate 4 pontos porcentuais de diferenca para 20% e sorteio, nao tendencia.
    esperado = 100 / len(linhas)
    equilibrado = all(abs(pct - esperado) <= 4 for _, _, pct in linhas)
    return linhas, "equilibrado" if equilibrado else "tendencia"


def termos_frequentes(questoes: list, quantos: int = 15) -> list[Termo]:
    """As palavras de conteudo que mais aparecem nos enunciados.

    E o mais perto de "assunto" que da para chegar sem alguem ler as questoes:
    se "crase" aparece em 40 enunciados, crase cai.
    """
    conta: Counter[str] = Counter()
    for questao in questoes:
        # Uma vez por questao: enunciado que repete a palavra nao vale mais.
        vistas = set()
        for palavra in re.findall(r"[A-Za-z\u00c0-\u00ff]+", questao.enunciado):
            crua = _sem_acento(palavra).lower()
            if len(crua) >= MINIMO_DE_LETRAS and crua not in PALAVRAS_VAZIAS:
                vistas.add(palavra.lower())
        conta.update(vistas)

    return [Termo(palavra=p, quantas=n) for p, n in conta.most_common(quantos)]


def mais_repetidas(questoes: list, quantos: int = 5) -> list[Repetida]:
    """As questoes que a banca mais reaproveitou entre cadernos.

    E o achado que mais vale estudar: no acervo inteiro uma questao aparece em
    44 cadernos diferentes.
    """
    por_impressao: dict[str, list] = {}
    for questao in questoes:
        por_impressao.setdefault(questao.impressao, []).append(questao)

    repetidas = [
        Repetida(
            enunciado=grupo[0].enunciado,
            materia=grupo[0].materia,
            cadernos=len(grupo),
        )
        for grupo in por_impressao.values()
        if len(grupo) > 1
    ]
    repetidas.sort(key=lambda r: -r.cadernos)
    return repetidas[:quantos]


def uma_por_enunciado(questoes: list) -> list:
    """Uma questao por enunciado, para conta que a repeticao estragaria.

    Medido: buscando "crase", a mesma questao aparece em 38 cadernos e a
    resposta dela e "d". Contando todas, o gabarito dava "letra d em 64%" e a
    conclusao seria chutar d - que so vale naquela questao, e nao na banca.
    O mesmo vale para os termos: "ginastica" subia ao topo dos assuntos.
    """
    unicas: dict[str, object] = {}
    for questao in questoes:
        unicas.setdefault(questao.impressao, questao)
    return list(unicas.values())


def analisar(questoes: list) -> Analise:
    """Junta tudo num retrato so.

    Materia e comando contam TODAS as questoes: questao que a banca repete em
    38 cadernos pesa mesmo mais na prova que eu vou fazer. Gabarito e termos
    contam uma por enunciado, porque ali a repeticao mentiria.
    """
    if not questoes:
        return Analise()

    distintas = uma_por_enunciado(questoes)
    materias = Counter(q.materia or "sem materia" for q in questoes)
    gabarito, veredito = distribuicao_do_gabarito(distintas)

    return Analise(
        total=len(questoes),
        distintas=len(distintas),
        materias=materias.most_common(),
        comandos=contar_comandos(questoes),
        termos=termos_frequentes(distintas),
        repetidas=mais_repetidas(questoes),
        gabarito=gabarito,
        gabarito_veredito=veredito,
    )


# --- assuntos dentro da materia ---------------------------------------------

# A banca diz a MATERIA no cabecalho da secao ("Lingua Portuguesa"), mas nunca
# o assunto da questao. Este catalogo e um dicionario de palavras-chave escrito
# a mao: nao adivinha nada, e da para conferir cada padrao abrindo as provas.
#
# Cobertura medida no acervo, em enunciados distintos: portugues 76%,
# informatica 61%, conhecimentos gerais 59%, raciocinio 53%. O que sobra a tela
# conta como "sem assunto detectado", e nao empurra para um assunto qualquer.
CATALOGO_DE_ASSUNTOS: dict[str, tuple[tuple[str, str], ...]] = {
    "portugues": (
        ("Interpretacao de texto", r"\btexto \d|de acordo com o texto|segundo o texto|com base no texto|conforme o texto|no texto acima|do texto\b|tipologia|genero textual"),
        ("Verbos", r"\bverb(?:o|os|al|ais)\b|tempo verbal|modo verbal|conjugac|particip|infinitiv"),
        ("Classes de palavras", r"substantiv|adjetiv|adverbi|\bpronom|numeral|preposic|conjunc|interjeic|artigo definido"),
        ("Concordancia", r"concordanc"),
        ("Crase", r"\bcrase|sinal indicativo de crase"),
        ("Ortografia", r"ortograf|grafia correta|corretamente (?:escrit|grafad)|escrita correta"),
        ("Emprego de palavras", r"vocabul|corretamente empregad|empregad[ao] corretamente|\bonde\b.*\baonde\b|\bmau\b.*\bmal\b|por que|porqu[e]"),
        ("Pontuacao", r"pontuac|\bvirgula|ponto e virgula|dois pontos"),
        ("Sintaxe da oracao", r"sujeito|predicad|objeto diret|objeto indiret|adjunto|aposto|vocativ|complemento nominal|agente da passiva"),
        ("Figuras de linguagem", r"figura de linguagem|metafor|metonim|hiperbol|eufemism|personificac|conotativ|denotativ|sentido figurado"),
        ("Periodo composto", r"oracao (?:coordenada|subordinada)|periodo composto|subordinad|coordenad"),
        ("Formacao de palavras", r"derivac|composic|sufixo|prefixo|radical|formad[ao]s? por"),
        ("Semantica", r"sinonim|antonim|homonim|paronim|significado d[ao]|sentido d[ao] (?:palavra|termo)"),
        ("Regencia", r"regenc"),
        ("Acentuacao", r"acentuac|acento (?:grafico|agudo|circunflexo)|proparoxiton|oxiton|paroxiton"),
        ("Coesao e coerencia", r"coesao|coerenc|conectiv|elemento coesivo"),
        ("Colocacao pronominal", r"colocacao pronominal|proclise|enclise|mesoclise"),
        ("Vozes verbais", r"voz (?:ativa|passiva|reflexiva)|voz verbal"),
    ),
    "raciocinio": (
        ("Logica proposicional", r"proposic|negac|conjuncao|disjuncao|condicional|equivalen|tautolog|valor logico|se .{0,25} entao"),
        ("Probabilidade", r"probabilidad|chance de|ao acaso|sortead"),
        ("Problemas com valores e idades", r"idade de|quantos anos|reais|quantia|salario de"),
        ("Porcentagem", r"porcent|por cento|%|desconto de|aumento de"),
        ("Conjuntos", r"conjunto|diagrama|uniao|intersec|pertence a"),
        ("Analise combinatoria", r"combinac|permutac|arranjo|quantas maneiras|de quantos modos|anagrama"),
        ("Sequencias e padroes", r"sequenc|proxim[oa] (?:numero|termo|figura)|padrao numerico|termo seguinte"),
        ("Regra de tres e proporcao", r"regra de tres|proporc|razao entre|diretamente proporcional|inversamente proporcional"),
    ),
    "informatica": (
        ("Planilha (Excel/Calc)", r"excel|planilha|calc\b|celula [a-z]\d|formula|soma\(|tabela dinamica"),
        ("Sistema operacional", r"windows|sistema operacional|explorador de arquivos|painel de controle|area de trabalho|linux"),
        ("Internet e navegador", r"navegador|browser|chrome|firefox|edge\b|\burl\b|site\b|internet\b|hiperlink"),
        ("Editor de texto (Word/Writer)", r"\bword\b|writer|editor de texto|documento .{0,20}texto"),
        ("Seguranca da informacao", r"antivirus|malware|phishing|backup|criptograf|firewall|senha segura|virus"),
        ("Correio eletronico", r"e-?mail|correio eletronico|outlook|caixa de entrada"),
        ("Redes e hardware", r"\brede[s]? de computador|\bwi-?fi|roteador|hardware|memoria ram|processador|perifer"),
        ("Nuvem e armazenamento", r"nuvem|cloud|google drive|onedrive|dropbox|armazenamento"),
        ("Atalhos de teclado", r"ctrl ?\+|atalho de teclado|tecla de atalho|\bf\d\b"),
    ),
    "gerais": (
        ("Santa Catarina", r"santa catarina|catarinens|florianopolis|\bsc\b|colonizac|imigrac"),
        ("Historia", r"histori|seculo|guerra|revoluc|independenc|republica"),
        ("Geografia", r"geograf|relevo|clima|populac|territori|fronteira|bacia|regiao"),
        ("Politica e governo", r"presidente|governador|prefeit|congresso|ministr|constituic|poder (?:executivo|legislativo|judiciario)"),
        ("Atualidades", r"em 202\d|recentement|atualment|noticia|eleic|pandemia"),
        ("Meio ambiente", r"meio ambiente|sustentabil|poluic|reciclag|desmatament"),
        ("Esporte e cultura", r"olimpiad|copa do mundo|futebol|atleta|festival|patrimonio cultural"),
    ),
}

# Como o nome que a banca usa vira a chave do catalogo. "Lingua Portuguesa",
# "Portugues" e "Lingua Portuguesa e Interpretacao" caem todos em portugues.
APELIDOS_DE_MATERIA: dict[str, tuple[str, ...]] = {
    "portugues": ("portug",),
    "raciocinio": ("raciocinio", "logic", "matemat"),
    "informatica": ("informatica", "computac"),
    "gerais": ("gerais", "atualidade"),
    # Cai em concurso publico de qualquer cargo, e o catalogo de assuntos dela
    # ainda nao existe - por isso a tupla vazia em CATALOGO_DE_ASSUNTOS.
    "etica": ("etica",),
}


# Palavra que denuncia materia de uma area so, ainda que o nome comece igual.
# "Conhecimentos Gerais sobre Educacao" so cai em prova de professor, e sem
# isto ela entrava no simulado como se caisse em qualquer concurso.
MARCAS_DE_AREA = ("educacao", "saude", "pedagog", "docente", "ensino")


def chave_da_materia(materia: str | None) -> str | None:
    """Qual grupo do catalogo cobre essa materia, se algum."""
    limpo = _sem_acento(materia or "").lower()
    if any(marca in limpo for marca in MARCAS_DE_AREA):
        return None
    for chave, marcas in APELIDOS_DE_MATERIA.items():
        if any(marca in limpo for marca in marcas):
            return chave
    return None


@dataclass
class Assunto:
    nome: str
    questoes: int
    distintas: int
    cadernos: int


@dataclass
class RetratoDaMateria:
    """Como essa materia se comporta nas provas desta banca."""

    materia: str
    cadernos: int
    questoes: int
    por_caderno: float
    assuntos: list[Assunto] = field(default_factory=list)
    sem_assunto: int = 0


def assuntos_de(questoes: list, chave: str) -> tuple[list[Assunto], int]:
    """[(assunto, quanto caiu)] e quantas ficaram sem assunto detectado.

    Uma questao pode cair em mais de um assunto - "crase" e "regencia" andam
    juntas - e isso e proposital: a soma nao fecha com o total, e esconder a
    segunda marca seria pior que a soma nao fechar.
    """
    catalogo = CATALOGO_DE_ASSUNTOS.get(chave, ())
    achados: list[Assunto] = []
    classificadas: set[str] = set()

    # Tirar o acento uma vez por questao, e nao uma vez por padrao: sao ate 18
    # padroes por materia, e o "Onde estudar primeiro" chama isto para milhares
    # de enunciados a cada abertura da home.
    limpos = [(q, _sem_acento(q.enunciado).lower()) for q in questoes]

    for nome, padrao in catalogo:
        casaram = [q for q, texto in limpos if re.search(padrao, texto)]
        if not casaram:
            continue
        classificadas.update(q.impressao for q in casaram)
        achados.append(Assunto(
            nome=nome,
            questoes=len(casaram),
            distintas=len({q.impressao for q in casaram}),
            cadernos=len({q.prova_url for q in casaram}),
        ))

    achados.sort(key=lambda a: -a.questoes)
    sem_assunto = len({q.impressao for q in questoes} - classificadas)
    return achados, sem_assunto


def retratar_materia(questoes_da_materia: list, materia: str) -> RetratoDaMateria:
    """Quanto essa materia cai por caderno, e de que assuntos ela e feita."""
    cadernos = len({q.prova_url for q in questoes_da_materia})
    chave = chave_da_materia(materia)
    assuntos, sem_assunto = assuntos_de(questoes_da_materia, chave) if chave else ([], 0)

    return RetratoDaMateria(
        materia=materia,
        cadernos=cadernos,
        questoes=len(questoes_da_materia),
        por_caderno=len(questoes_da_materia) / cadernos if cadernos else 0.0,
        assuntos=assuntos,
        sem_assunto=sem_assunto,
    )


def materia_dominante(questoes: list) -> str | None:
    """A materia da maioria das questoes, quando ha maioria clara.

    Procurar "crase" traz 56 questoes de Lingua Portuguesa e 3 de
    Conhecimentos Especificos: a materia e Portugues, e nao "as duas". Sem
    maioria de pelo menos 60%, o recorte mistura materias demais e afirmar uma
    seria escolher por escolher.
    """
    if not questoes:
        return None

    contagem = Counter(q.materia for q in questoes if q.materia)
    if not contagem:
        return None

    materia, quantas = contagem.most_common(1)[0]
    return materia if quantas / len(questoes) >= 0.6 else None


def assunto_do_tema(tema: str, retrato: "RetratoDaMateria") -> "Assunto | None":
    """O assunto do catalogo que corresponde ao que eu escrevi, se houver.

    Escrevendo "crase" eu quero ver a linha "Crase" em destaque; escrevendo
    "primeiros socorros" nao ha assunto no catalogo, e a tela mostra so o
    retrato da materia.
    """
    procurado = _sem_acento(tema).lower().strip()
    if not procurado:
        return None

    for assunto in retrato.assuntos:
        nome = _sem_acento(assunto.nome).lower()
        if procurado in nome or nome in procurado:
            return assunto
    return None


@dataclass
class FatiaDoCaderno:
    materia: str
    por_caderno: float
    total: int


def composicao_do_caderno(questoes: list) -> list[FatiaDoCaderno]:
    """Quantas questoes de cada materia caem num caderno tipico desta banca.

    Responde "quantas questoes de portugues caem na prova": divide o total de
    cada materia pelo numero de cadernos em que a banca aplicou alguma coisa.
    Nem toda materia cai em todo caderno - cargo de professor tem Temas de
    Educacao, guarda nao tem -, entao a divisao usa os cadernos em que AQUELA
    materia apareceu, e nao o total de cadernos.
    """
    # Questao sem materia conhecida fica de fora: a pergunta aqui e "quantas
    # questoes de cada MATERIA caem", e "sem materia" nao e uma delas. Num
    # caderno em que o edital nao declara o nivel do cargo, ela apareceria em
    # primeiro lugar no grafico.
    por_materia: dict[str, list] = {}
    for questao in questoes:
        if questao.materia:
            por_materia.setdefault(questao.materia, []).append(questao)

    fatias = []
    for materia, doGrupo in por_materia.items():
        cadernos = len({q.prova_url for q in doGrupo})
        fatias.append(FatiaDoCaderno(
            materia=materia,
            por_caderno=len(doGrupo) / cadernos if cadernos else 0.0,
            total=len(doGrupo),
        ))

    fatias.sort(key=lambda f: -f.por_caderno)
    return fatias


# --- grafico de pizza -------------------------------------------------------

# Cores das fatias, na ordem. Sao oito porque acima disso a legenda fica
# ilegivel - e por isso o resto vira uma fatia so, "outros".
CORES_DA_PIZZA = (
    "#1d4ed8", "#0891b2", "#059669", "#ca8a04",
    "#dc2626", "#7c3aed", "#db2777", "#475569",
)

MAXIMO_DE_FATIAS = 8
ROTULO_DO_RESTO = "outros"


@dataclass
class Fatia:
    rotulo: str
    valor: float
    porcentagem: float
    inicio: float       # onde a fatia comeca, em % do circulo
    fim: float
    cor: str
    # Numero que acompanha a fatia na legenda, quando ele diz outra coisa que
    # a porcentagem nao diz - "9,0 questoes por prova", por exemplo.
    por_caderno: float | None = None


def fatias(
    itens: list[tuple[str, float]],
    extras: dict[str, float] | None = None,
) -> list[Fatia]:
    """Transforma [(rotulo, valor)] nas fatias de um grafico de pizza.

    O calculo fica aqui, e nao no template, por dois motivos: o angulo
    acumulado e conta, e assim da para testar. A pizza em si e desenhada com
    `conic-gradient` no CSS - sem JavaScript, como o resto da tela.

    Acima de oito categorias a legenda vira uma parede de texto, entao o que
    sobra e somado numa fatia "outros". Ela e sempre a ultima.
    """
    limpos = [(rotulo, float(valor)) for rotulo, valor in itens if valor > 0]
    if not limpos:
        return []

    limpos.sort(key=lambda item: -item[1])
    if len(limpos) > MAXIMO_DE_FATIAS:
        resto = sum(valor for _, valor in limpos[MAXIMO_DE_FATIAS - 1:])
        limpos = limpos[: MAXIMO_DE_FATIAS - 1] + [(ROTULO_DO_RESTO, resto)]

    total = sum(valor for _, valor in limpos)
    montadas: list[Fatia] = []
    acumulado = 0.0

    for indice, (rotulo, valor) in enumerate(limpos):
        porcentagem = valor / total * 100
        # A ultima fecha em 100 na unha: somar porcentagens arredondadas deixa
        # uma frestinha branca no fim do circulo.
        fim = 100.0 if indice == len(limpos) - 1 else acumulado + porcentagem
        montadas.append(Fatia(
            rotulo=rotulo,
            valor=valor,
            porcentagem=porcentagem,
            inicio=acumulado,
            fim=fim,
            cor=CORES_DA_PIZZA[indice % len(CORES_DA_PIZZA)],
            por_caderno=(extras or {}).get(rotulo),
        ))
        acumulado = fim

    return montadas


def assuntos_do_enunciado(enunciado: str, chave: str) -> list[str]:
    """Que assuntos do catalogo este enunciado casa. Vazio = nenhum.

    E o `assuntos_de` visto pelo outro lado: la a pergunta e "quantas questoes
    tem este assunto", aqui e "que assuntos tem esta questao". O segundo e o
    que o "Onde estudar primeiro" precisa para dizer quanto eu acerto POR
    ASSUNTO - ele tem uma resposta de simulado na mao, e nao um monte de
    questoes.

    Uma questao pode casar mais de um assunto, como la: crase e regencia andam
    juntas, e esconder a segunda marca seria pior que a soma nao fechar.
    """
    limpo = _sem_acento(enunciado or "").lower()
    return [
        nome for nome, padrao in CATALOGO_DE_ASSUNTOS.get(chave, ())
        if re.search(padrao, limpo)
    ]
