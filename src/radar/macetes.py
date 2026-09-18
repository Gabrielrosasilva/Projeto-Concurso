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
