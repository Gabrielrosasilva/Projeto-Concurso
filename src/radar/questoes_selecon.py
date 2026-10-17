"""Separa o caderno da Selecon em questoes, e le o gabarito a parte.

A banca da SEJUSP/MG 2021 (Policial Penal) e de Guardas Municipais (decisao
168). Tres diferencas em relacao aos outros cadernos, e cada uma muda o codigo:

  1. **quatro alternativas**, de A) a D), em maiuscula, e o numero "26. ";
  2. **duas colunas embaralham a ordem**: o pypdf le a pagina 6 como 26, 27,
     23, 24, 25, 22, 21, 28, 20. Cada questao continua inteira, com as
     alternativas dela logo abaixo - e por isso a leitura vai pelas rodadas de
     A) a D), cada uma com o numero que vem antes, e no fim ordena;
  3. **o titulo da materia cai fora do lugar** (pelas colunas), e a materia
     sai da faixa de questoes da capa ("21 a 30 Nocoes de Direito
     Constitucional e Penal"), copiada na entrada da prova no
     `config/provas_de_outras_bancas.yml`.

O gabarito e um PDF a parte, em fileiras: uma linha de numeros e, logo
abaixo, uma de letras, com "ANULADA" no lugar da letra da anulada.
"""
import re
from pathlib import Path

from radar.questoes import Questao, _limpar, extrair_texto, limpar_mobilia

LETRAS = "ABCD"

# "A)  texto": a letra maiuscula, no comeco da linha.
PADRAO_ALTERNATIVA = re.compile(r"(?m)^[ \t]*([A-D])\)[ \t]*")

# "26. Enunciado", ou "14.Considerando" sem o espaco. O numero da questao vem
# antes de tudo na regiao dela; "14.695" (o numero de uma lei) nao e questao.
PADRAO_QUESTAO = re.compile(r"(?m)^[ \t]*(\d{1,2})\.(?!\d)[ \t]*(?=\S)")

# "politico32. A luz das Regras": o numero colado no fim da linha de cima.
NUMERO_COLADO = re.compile(r"(?<=[a-zà-ÿ])(\d{1,2}\.[ \t]+)(?=[A-ZÀ-Ý“\"])")

# O titulo de materia, uma linha so de maiusculas: e onde a ultima alternativa
# acaba quando o titulo cai no meio da pagina.
PADRAO_TITULO = re.compile(r"(?m)^[ \t]*[A-ZÀ-Ý][A-ZÀ-Ý ,\-–]{5,}[ \t]*$")

# O numero da pagina, sozinho na linha.
PADRAO_PAGINA = re.compile(r"(?m)^[ \t]*\d{1,2}[ \t]*$")


def ler_gabarito(texto: str) -> dict[int, str | None]:
    """{numero: letra minuscula}, e None na anulada, das fileiras do PDF."""
    linhas = [linha.split() for linha in texto.splitlines()]
    gabarito: dict[int, str | None] = {}
    numeros: list[int] = []
    for partes in linhas:
        if partes and all(p.isdigit() for p in partes):
            numeros = [int(p) for p in partes]
            continue
        if numeros and partes and all(p in LETRAS + "E" or p == "ANULADA" for p in partes):
            if len(partes) == len(numeros):
                for numero, letra in zip(numeros, partes):
                    gabarito[numero] = None if letra == "ANULADA" else letra.lower()
            numeros = []
    return gabarito


def materia_da_faixa(numero: int, faixas: list[tuple[int, int, str]]) -> str | None:
    for inicio, fim, nome in faixas:
        if inicio <= numero <= fim:
            return nome
    return None


def faixas_do_config(materias: dict | None) -> list[tuple[int, int, str]]:
    """{"21-25": "Direito Constitucional", ...} -> [(21, 25, nome), ...]."""
    faixas = []
    for intervalo, nome in (materias or {}).items():
        inicio, _, fim = str(intervalo).partition("-")
        faixas.append((int(inicio), int(fim or inicio), str(nome)))
    return sorted(faixas)


def _rodadas(texto: str) -> list[list[re.Match]]:
    rodadas: list[list[re.Match]] = []
    atual: list[re.Match] = []
    for marca in PADRAO_ALTERNATIVA.finditer(texto):
        letra = marca.group(1)
        esperada = LETRAS[len(atual)] if len(atual) < len(LETRAS) else None
        if letra == "A":
            if len(atual) >= 2:
                rodadas.append(atual)
            atual = [marca]
        elif letra == esperada:
            atual.append(marca)
            if len(atual) == len(LETRAS):
                rodadas.append(atual)
                atual = []
        else:
            if len(atual) >= 2:
                rodadas.append(atual)
            atual = []
    if len(atual) >= 2:
        rodadas.append(atual)
    return rodadas


def dividir_em_questoes(texto: str, gabarito: dict[int, str | None] | None = None,
                        faixas: list[tuple[int, int, str]] | None = None) -> list[Questao]:
    """As questoes do caderno, na ordem do numero, com a materia da faixa da
    capa e a resposta do gabarito (None na anulada, que vem marcada)."""
    texto = PADRAO_PAGINA.sub("", limpar_mobilia(texto.replace("\t", " ")))
    texto = NUMERO_COLADO.sub(lambda m: "\n" + m.group(1), texto)
    gabarito = gabarito or {}
    rodadas = _rodadas(texto)
    marcadores = list(PADRAO_QUESTAO.finditer(texto))
    titulos = list(PADRAO_TITULO.finditer(texto))

    questoes: list[Questao] = []
    fim_anterior = 0
    for indice, rodada in enumerate(rodadas):
        antes = [m for m in marcadores if fim_anterior <= m.start() < rodada[0].start()]
        fim_anterior = rodada[-1].end()
        if not antes:
            continue
        marcador = antes[0]
        limite = rodadas[indice + 1][0].start() if indice + 1 < len(rodadas) else len(texto)
        depois = [m.start() for m in marcadores + titulos if rodada[-1].end() <= m.start() < limite]
        fim_da_ultima = min(depois) if depois else limite

        alternativas = {}
        for posicao, marca in enumerate(rodada):
            ate = rodada[posicao + 1].start() if posicao + 1 < len(rodada) else fim_da_ultima
            conteudo = _limpar(texto[marca.end():ate])
            if conteudo:
                alternativas[marca.group(1).lower()] = conteudo
        enunciado = _limpar(texto[marcador.end():rodada[0].start()])
        if not enunciado or len(alternativas) < 2:
            continue
        numero = int(marcador.group(1))
        anulada = numero in gabarito and gabarito[numero] is None
        questoes.append(Questao(
            numero=numero, enunciado=enunciado, alternativas=alternativas,
            resposta=gabarito.get(numero), anulada=anulada,
            materia=materia_da_faixa(numero, faixas or [])))

    melhores: dict[int, Questao] = {}
    for questao in questoes:
        anterior = melhores.get(questao.numero)
        if anterior is None or len(questao.enunciado) > len(anterior.enunciado):
            melhores[questao.numero] = questao
    return [melhores[n] for n in sorted(melhores)]


def ler_prova(caminho: Path, caminho_do_gabarito: Path | None = None,
              faixas: list[tuple[int, int, str]] | None = None) -> list[Questao]:
    """Le um caderno da Selecon inteiro, com o gabarito ao lado quando ha."""
    gabarito = ler_gabarito(extrair_texto(caminho_do_gabarito)) if caminho_do_gabarito else {}
    return dividir_em_questoes(extrair_texto(caminho), gabarito, faixas)
