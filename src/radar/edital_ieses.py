"""De que materia e cada questao, segundo o edital da IESES.

Por que isto existe: o caderno da IESES nao diz a materia em lugar nenhum. Sao
30 questoes numeradas de 1 a 30, sem cabecalho de secao - ao contrario da
FEPESE, que escreve "Lingua Portuguesa 10 questoes" no meio do caderno.

A informacao existe, so que no edital, e declarada pela propria banca:

  * **Anexo II** liga o codigo do cargo ao nivel ("1016 Assistente Social" esta
    sob "1. NIVEL SUPERIOR");
  * **Anexo IV** diz de que o nivel e feito, na ordem em que cai na prova
    ("LINGUA PORTUGUESA - 8 QUESTOES", "MATEMATICA E RACIOCINIO LOGICO - 4"...).

Com os dois, a questao 13 de um caderno de nivel superior e de Informatica
porque o edital diz isso, e nao porque alguem olhou o enunciado e achou.

Conferido no caderno real de Biguacu 2024, cargo 1016: as seis faixas batem com
o conteudo - 1 a 8 sao o poema e a gramatica, 9 a 12 sao juros e sequencia, 13
a 15 sao Word e Excel, 16 e 17 sao economia verde e inteligencia artificial, 18
a 20 sao etica do servidor, e 21 a 30 sao servico social.
"""
import re
import unicodedata

# "1. NIVEL SUPERIOR", "2. NÍVEL MÉDIO" - abre um bloco nos dois anexos.
PADRAO_NIVEL = re.compile(r"(?im)^\s*\d+\.\s*N[IÍ]VEL\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+?)\s*$")

# "1016 Assistente Social (Secretaria de Educacao) Habilitacao profissional..."
PADRAO_CODIGO = re.compile(r"^\s*(\d{4})\s+\S")

# "LÍNGUA PORTUGUESA – 8 (OITO) QUESTÕES". O numero por extenso entre
# parenteses varia demais para listar - "TRES", "QUATRO", "DUAS" -, entao vale
# qualquer coisa curta ali dentro.
PADRAO_MATERIA = re.compile(
    r"(?im)^\s*([A-ZÁÂÃÉÊÍÓÔÕÚÇ][A-ZÁÂÃÉÊÍÓÔÕÚÇ \-/]{3,60}?)"
    r"\s*[–-]\s*(\d+)\s*\([^)]{2,14}\)\s*QUEST[OÕ]ES\s*$"
)

ESPECIFICOS = re.compile(
    r"(?im)^\s*PROVA DE CONHECIMENTOS ESPEC[IÍ]FICOS\s*[–-]\s*COM\s+(\d+)\s*\("
)
# O mesmo edital escreve a frase de tres jeitos: "contera 10 (dez) questoes
# especificas", "tera 10 (dez questoes)" - com a palavra dentro do parentese -
# e a forma do titulo. Por isso o padrao procura o numero depois da expressao,
# e nao uma redacao exata.
PADRAO_ESPECIFICOS_NA_FRASE = re.compile(
    r"(?i)conhecimentos\s+espec[ií]ficos.{0,160}?"
    r"(?:ter[aá]|conter[aá])\s+(\d+)\s*\("
)

# Com acento, para casar com o nome que a FEPESE usa no caderno dela: e a
# mesma materia, e na tela virariam duas linhas separadas.
ESPECIFICOS = "Conhecimentos Específicos"

# Palavras que ficam em minuscula no meio do nome da materia. O edital escreve
# tudo em caixa alta ("MATEMATICA E RACIOCINIO LOGICO") e title() sozinho
# devolveria "Matemática E Raciocínio Lógico", com o E gritando no meio.
CONECTIVOS = ("e", "de", "do", "da", "dos", "das", "no", "na", "em", "a", "o")


def _nome_de_materia(bruto: str) -> str:
    palavras = " ".join(bruto.split()).title().split()
    return " ".join(
        p.lower() if i and p.lower() in CONECTIVOS else p
        for i, p in enumerate(palavras)
    )


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def _chave_do_nivel(nome: str) -> str:
    """"FUNDAMENTAL ANOS INICIAIS" e "FUNDAMENTAL COMPLETO" viram FUNDAMENTAL.

    Os dois anexos nomeiam os niveis de jeitos diferentes: o Anexo II fala em
    "FUNDAMENTAL ANOS INICIAIS" e o IV em "FUNDAMENTAL COMPLETO" e
    "INCOMPLETO". A primeira palavra e o que os dois tem em comum, e as duas
    variantes do fundamental tem a MESMA composicao de prova.
    """
    return _sem_acento(nome).upper().split()[0] if nome.split() else ""


def niveis_por_codigo(edital: str) -> dict[str, str]:
    """{codigo do cargo: nivel}, lido do Anexo II."""
    inicio = edital.find("ANEXO II ")
    if inicio < 0:
        return {}
    fim = edital.find("ANEXO III", inicio)
    trecho = edital[inicio:fim if fim > inicio else len(edital)]

    niveis: dict[str, str] = {}
    atual: str | None = None
    for linha in trecho.split("\n"):
        achado = PADRAO_NIVEL.match(linha)
        if achado:
            atual = _chave_do_nivel(achado.group(1))
            continue
        codigo = PADRAO_CODIGO.match(linha)
        if codigo and atual:
            niveis.setdefault(codigo.group(1), atual)
    return niveis


def composicao_por_nivel(edital: str) -> dict[str, list[tuple[str, int]]]:
    """{nivel: [(materia, quantas questoes)]}, na ordem da prova, do Anexo IV.

    Quando o mesmo nivel aparece duas vezes com composicoes diferentes -
    fundamental completo e incompleto -, fica so o que der para afirmar: se
    divergirem, o nivel sai do resultado em vez de valer o primeiro.
    """
    inicio = edital.find("ANEXO IV")
    if inicio < 0:
        return {}
    trecho = edital[inicio:]

    blocos: list[tuple[str, list[tuple[str, int]]]] = []
    for linha in trecho.split("\n"):
        achado = PADRAO_NIVEL.match(linha)
        if achado:
            blocos.append((_chave_do_nivel(achado.group(1)), []))
            continue
        if not blocos:
            continue

        materia = PADRAO_MATERIA.match(linha)
        if materia:
            nome = _nome_de_materia(materia.group(1))
            blocos[-1][1].append((nome, int(materia.group(2))))
            continue


    composicao: dict[str, list[tuple[str, int]]] = {}
    divergentes: set[str] = set()
    for nivel, materias in blocos:
        if not materias:
            continue
        if nivel in composicao and composicao[nivel] != materias:
            divergentes.add(nivel)
        composicao[nivel] = materias

    for nivel in divergentes:
        composicao.pop(nivel, None)
    return composicao


def materias_por_numero(
    composicao: list[tuple[str, int]], total: int | None = None
) -> dict[int, str]:
    """{numero da questao: materia}, a partir da composicao de um nivel.

    O edital lista as materias na ordem em que caem, e e so isso que permite
    dizer que a questao 13 e de Informatica: as 8 de portugues e as 4 de
    matematica vieram antes.

    O que passa da ultima materia listada e Conhecimentos Especificos. Isso
    evita caçar o numero de especificos no texto, que o mesmo edital escreve de
    tres jeitos - "ESPECIFICOS - COM 10 (DEZ) QUESTOES", "contera 10 (dez)
    questoes especificas" e "tera 10 (dez questoes)", com a palavra dentro do
    parentese. A ordem, essa sim, e sempre a mesma: gerais primeiro.
    """
    materias: dict[int, str] = {}
    proximo = 1
    for nome, quantas in composicao:
        for numero in range(proximo, proximo + quantas):
            materias[numero] = nome
        proximo += quantas

    if total:
        for numero in range(proximo, total + 1):
            materias[numero] = ESPECIFICOS
    return materias


def materias_do_cargo(
    edital: str, codigo: str, total: int | None = None
) -> dict[int, str]:
    """{numero da questao: materia} para o cargo daquele codigo.

    `total` e quantas questoes o caderno tem: o que passar das materias
    listadas no edital e Conhecimentos Especificos.

    Vazio quando o edital nao deixa claro - codigo que nao esta no Anexo II,
    nivel sem composicao no Anexo IV. Melhor sem materia que com materia
    errada: o simulado filtra por ela.
    """
    nivel = niveis_por_codigo(edital).get(str(codigo))
    if not nivel:
        return {}

    composicao = composicao_por_nivel(edital).get(nivel)
    if not composicao:
        return {}

    return materias_por_numero(composicao, total)
