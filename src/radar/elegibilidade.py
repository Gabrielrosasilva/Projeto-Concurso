"""O que o edital exige de quem se inscreve: escolaridade, idade, CNH e TAF.

Estes sao os criterios do item 2 do meu recorte - "se eu posso prestar". O
radar ja sabe ONDE a prova e aplicada; aqui ele passa a saber se eu sirvo para
a vaga, sem eu precisar abrir um PDF de 200 paginas.

Tudo sai do texto do edital, e cada achado guarda o **trecho** que o embasa. E
a mesma regra do resto do projeto: o veredito sozinho nao vale, eu preciso
poder conferir de onde ele veio.

O que este arquivo NAO faz: decidir cargo por cargo. Um edital de prefeitura
traz dezenas de cargos com requisitos diferentes, e o radar guarda um registro
por CONCURSO. Entao a leitura e sobre o concurso inteiro: se ele tem vaga de
nivel superior, se exige CNH em alguma vaga, se tem teste fisico.
"""
import re
import unicodedata
from dataclasses import dataclass, field

SUPERIOR, MEDIO, FUNDAMENTAL = "superior", "medio", "fundamental"

# Como cada nivel aparece escrito no edital. O texto e comparado sem acento.
PADROES_DE_NIVEL = (
    (SUPERIOR, r"n[ií]vel superior|ensino superior|curso superior|"
               r"gradua[cç][aã]o (?:completa|em)|bacharelado|licenciatura"),
    (MEDIO, r"n[ií]vel m[eé]dio|ensino m[eé]dio|2[oº] grau"),
    (FUNDAMENTAL, r"n[ií]vel fundamental|ensino fundamental|1[oº] grau"),
)

# "Carteira Nacional de Habilitacao categoria D". A categoria e o que muda o
# custo: B quase todo mundo tem, D e E exigem curso e tempo de habilitacao.
PADRAO_CNH = re.compile(
    r"(?i)(?:carteira nacional de habilita[cç][aã]o|\bcnh\b)"
    r"[^.;\n]{0,80}?categoria\s*[\"']?([A-E](?:\s*(?:ou|e|/|,)\s*[A-E])*)"
)
PADRAO_CNH_SIMPLES = re.compile(r"(?i)carteira nacional de habilita[cç][aã]o|\bcnh\b")

# Teste de aptidao fisica: a barreira que mais elimina em concurso policial.
PADRAO_TAF = re.compile(
    r"(?i)(?:teste|prova|exame)\s+de\s+(?:aptid[aã]o|capacidade|condicionamento)"
    r"\s+f[ií]sic|\bTAF\b"
)

# "idade maxima de 30 anos", "nao ter completado 35 anos". Raro fora de
# carreira policial e militar, e por isso mesmo importante quando aparece.
PADRAO_IDADE_MAXIMA = re.compile(
    r"(?i)(?:idade m[aá]xima(?:\s+de)?|n[aã]o (?:ter|haver) (?:completado|mais de))"
    r"[^.;\n]{0,40}?(\d{2})\s*(?:\(\w+\)\s*)?anos"
)

PADRAO_IDADE_MINIMA = re.compile(
    r"(?i)idade m[ií]nima(?:\s+de)?[^.;\n]{0,30}?(\d{2})\s*(?:\(\w+\)\s*)?anos"
)

# Quanto de texto guardar como prova de cada achado.
TAMANHO_DO_TRECHO = 150


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def _trecho(texto: str, posicao: int) -> str:
    inicio = max(0, posicao - TAMANHO_DO_TRECHO // 3)
    return " ".join(texto[inicio:posicao + TAMANHO_DO_TRECHO].split())


@dataclass
class Exigencias:
    """O que o edital pede, e o trecho que embasa cada coisa."""

    niveis: list[str] = field(default_factory=list)
    idade_minima: int | None = None
    idade_maxima: int | None = None
    cnh: str | None = None            # a categoria, ou "sim" quando nao diz
    taf: bool = False
    trechos: dict[str, str] = field(default_factory=dict)
    legivel: bool = True

    @property
    def tem_superior(self) -> bool:
        return SUPERIOR in self.niveis


# Abaixo disto o PDF nao rendeu texto: costuma ser edital escaneado, publicado
# como imagem. Medido no acervo: um dos 32 editais tem 2,5 MB e 34 caracteres.
MINIMO_DE_TEXTO = 2000


def ler(edital: str) -> Exigencias:
    """O que este edital exige. Nada e inventado: sem achar, fica vazio."""
    if len(edital or "") < MINIMO_DE_TEXTO:
        return Exigencias(legivel=False)

    limpo = _sem_acento(edital)
    achado = Exigencias()

    for nivel, padrao in PADROES_DE_NIVEL:
        encontrado = re.search(padrao, limpo, re.IGNORECASE)
        if encontrado:
            achado.niveis.append(nivel)
            achado.trechos[nivel] = _trecho(edital, encontrado.start())

    idade = PADRAO_IDADE_MINIMA.search(limpo)
    if idade:
        achado.idade_minima = int(idade.group(1))
        achado.trechos["idade_minima"] = _trecho(edital, idade.start())

    idade = PADRAO_IDADE_MAXIMA.search(limpo)
    if idade:
        achado.idade_maxima = int(idade.group(1))
        achado.trechos["idade_maxima"] = _trecho(edital, idade.start())

    categoria = PADRAO_CNH.search(limpo)
    if categoria:
        # "A ou B", e nao "AouB": o texto do edital vem com o espacamento
        # do PDF, que junta ou separa sem criterio.
        achado.cnh = " ".join(categoria.group(1).upper().split())
        achado.trechos["cnh"] = _trecho(edital, categoria.start())
    else:
        simples = PADRAO_CNH_SIMPLES.search(limpo)
        if simples:
            achado.cnh = "sim"
            achado.trechos["cnh"] = _trecho(edital, simples.start())

    fisico = PADRAO_TAF.search(limpo)
    if fisico:
        achado.taf = True
        achado.trechos["taf"] = _trecho(edital, fisico.start())

    return achado


def resumir(exigencias: Exigencias) -> str:
    """Uma linha em portugues, para a tela e para o log."""
    if not exigencias.legivel:
        return "Edital ilegivel: provavelmente digitalizado como imagem."

    partes = []
    if exigencias.niveis:
        nomes = {SUPERIOR: "superior", MEDIO: "medio", FUNDAMENTAL: "fundamental"}
        partes.append("vagas de nivel " + ", ".join(nomes[n] for n in exigencias.niveis))
    if exigencias.idade_maxima:
        partes.append(f"idade maxima {exigencias.idade_maxima}")
    if exigencias.cnh:
        partes.append("exige CNH" + ("" if exigencias.cnh == "sim"
                                     else f" categoria {exigencias.cnh}"))
    if exigencias.taf:
        partes.append("tem teste fisico")

    if not partes:
        return "Nada identificado no edital."

    # So a primeira letra sobe. capitalize() rebaixaria o resto, e "CNH"
    # viraria "cnh", "categoria D" viraria "categoria d".
    linha = "; ".join(partes)
    return linha[0].upper() + linha[1:]
