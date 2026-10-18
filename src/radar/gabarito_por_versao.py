"""O gabarito de outra banca que imprime o caderno em mais de uma versao.

Muitas bancas imprimem a mesma prova em 2 a 4 versoes, com as questoes ou as
alternativas em outra ordem: "Tipo 1" a "Tipo 4" (FGV, Access), "Tipo A" e
"Tipo B" (Idecan), "Prova A" e "Prova B" (Selecon). O gabarito traz um bloco
por versao, e a letra certa da questao 30 no Tipo 1 nao e a do Tipo 2 - nem a
anulada e a mesma (na Guarda de Ribeirao Preto, a 47 e a 48 no Tipo 1, a 45 e
a 49 no Tipo 2). Por isso a entrada da prova no
`config/provas_de_outras_bancas.yml` diz a `versao` do caderno baixado, o
radar confere que o caderno e mesmo dela e so le o bloco dela (decisao 172).

O texto do gabarito sai do pypdf de dois jeitos, e cada banca so funciona num
deles: no modo comum a Access poe o nome do bloco antes dele e a Idecan o
poe no fim da pagina; no modo layout e o contrario. O bloco vale quando um dos
dois o acha com o nome - e, se os dois o acham, as letras tem de ser as
mesmas, ou o gabarito e recusado.
"""
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

# "Tipo 1", "PROVA TIPO A", "TIPO  2" (FGV, Access, Idecan) ou "PROVA A"
# (Selecon), numa linha que nao e de resposta.
PADRAO_TIPO = re.compile(r"\bTIPO\s+([1-4]|[A-D])\b", re.IGNORECASE)
PADRAO_PROVA = re.compile(r"\bPROVA\s+([A-D])\b", re.IGNORECASE)

# "01: D" (Selecon, Idecan), "1 – B" e "47 – anulada" (Access). O X, o "*" e a
# palavra "anulada" marcam a anulada; o numero nao pode ser o fim de um codigo
# de cargo ("02100 – ESCRIVAO").
PADRAO_PAR = re.compile(
    r"(?<!\d)(\d{1,3})\s*[:–-]\s*(anulada|[A-EX*])(?![A-Za-zÀ-ÿ])", re.IGNORECASE)

# A fileira da FGV e do Cebraspe: uma linha so de numeros e, embaixo, uma so
# de letras.
SO_NUMEROS = re.compile(r"^\s*\d{1,3}(?:\s+\d{1,3})+\s*$")
SO_LETRAS = re.compile(r"^\s*[A-EX*](?:\s+[A-EX*])+\s*$")

# O cabecalho de outro cargo no mesmo gabarito: "502 - ANALISTA TECNICO...".
PADRAO_CARGO = re.compile(r"^\s*\d{3,5}\s*[-–]\s*\S")


def nome_da_versao(linha: str) -> str | None:
    """"TIPO 1", "TIPO A" ou "PROVA A", do jeito que a lista escreve."""
    achado = PADRAO_TIPO.search(linha)
    if achado:
        return f"TIPO {achado.group(1).upper()}"
    achado = PADRAO_PROVA.search(linha)
    if achado:
        return f"PROVA {achado.group(1).upper()}"
    return None


def _letra(marca: str) -> str | None:
    marca = marca.strip().lower()
    return None if marca in ("x", "*", "anulada") else marca


def _de_outro_cargo(linha: str, cargo: str) -> bool:
    """A linha abre o bloco de OUTRO cargo: "502 - ANALISTA..." (Selecon),
    ou o nome da versao junto do nome de outro cargo, "Escrivao de Policia
    Civil Substituto - Tipo 1" (FGV). "PROVA A" sozinho e do mesmo cargo."""
    if cargo.lower() in linha.lower():
        return False
    if PADRAO_CARGO.match(linha):
        return True
    sem_a_versao = PADRAO_PROVA.sub("", PADRAO_TIPO.sub("", linha))
    return bool(nome_da_versao(linha)) and len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", sem_a_versao)) >= 2


def _so_do_cargo(texto: str, cargo: str | None) -> str:
    """O pedaco do gabarito de um cargo so, quando o PDF junta varios: da
    linha que cita o cargo ate a que abre o bloco de outro."""
    if not cargo:
        return texto
    linhas = texto.splitlines()
    inicio = next((i for i, linha in enumerate(linhas) if cargo.lower() in linha.lower()), None)
    if inicio is None:
        return ""
    fim = next((i for i in range(inicio + 1, len(linhas)) if _de_outro_cargo(linhas[i], cargo)),
               len(linhas))
    return "\n".join(linhas[inicio:fim])


def blocos(texto: str, cargo: str | None = None) -> list[tuple[str | None, dict]]:
    """[(nome da versao ou None, {numero: letra, ou None na anulada})], na
    ordem do texto. Um bloco novo abre no nome de uma versao, ou quando a
    numeracao recomeca."""
    saida: list[tuple[str | None, dict]] = []
    nome, atual, ultimo = None, {}, 0
    numeros: list[int] = []

    def fechar():
        if atual:
            saida.append((nome, dict(atual)))

    for linha in _so_do_cargo(texto, cargo).splitlines():
        pares = PADRAO_PAR.findall(linha)
        if not pares and not SO_NUMEROS.match(linha) and not SO_LETRAS.match(linha):
            versao = nome_da_versao(linha)
            if versao:
                fechar()
                nome, atual, ultimo, numeros = versao, {}, 0, []
            continue
        if SO_NUMEROS.match(linha):
            numeros = [int(n) for n in linha.split()]
            continue
        if SO_LETRAS.match(linha) and numeros:
            pares = list(zip(numeros, linha.split()))
            numeros = []
        for numero, marca in pares:
            numero = int(numero)
            if numero <= ultimo and numero in atual:
                # A numeracao recomecou sem nome: e outra versao.
                fechar()
                nome, atual = None, {}
            atual[numero] = _letra(marca)
            ultimo = numero
    fechar()
    return saida


def _do_nome(lista: list[tuple[str | None, dict]], versao: str) -> dict | None:
    """O bloco com o nome da versao. Um pedaco nao conta: no modo comum, o
    nome que a Idecan poe no fim da pagina so pega as anuladas que vem
    depois dele."""
    maior = max((len(bloco) for _, bloco in lista), default=0)
    achados = [bloco for nome, bloco in lista if nome == versao and len(bloco) * 2 >= maior]
    return achados[0] if len(achados) == 1 else None


def bloco_da_versao(textos: list[str], versao: str,
                    cargo: str | None = None) -> dict[int, str | None]:
    """O bloco da `versao`, de um ou mais textos do mesmo gabarito (os dois
    modos de leitura). ValueError quando nenhum o acha com o nome, ou quando
    dois o acham com letras diferentes."""
    achados = []
    for texto in textos:
        bloco = _do_nome(blocos(texto, cargo), versao)
        if bloco:
            achados.append(bloco)
    if not achados:
        raise ValueError(f"o gabarito nao tem um bloco so com o nome {versao}")
    if any(bloco != achados[0] for bloco in achados[1:]):
        raise ValueError(f"os dois modos de leitura dao letras diferentes para {versao}")
    return achados[0]


def da_versao(caminho: Path, versao: str, cargo: str | None = None) -> dict[int, str | None]:
    """O bloco da `versao` no gabarito em PDF, lido nos dois modos."""
    paginas = PdfReader(caminho).pages
    textos = ["\n".join((p.extract_text(extraction_mode=modo) or "") for p in paginas)
              for modo in ("plain", "layout")]
    return bloco_da_versao(textos, versao, cargo)


def versao_do_caderno(texto: str) -> str | None:
    """A versao que o caderno mais cita: "TIPO 1 - BRANCA" na capa, "- TIPO A"
    no cabecalho de toda pagina, "A / PROVA" no canto da Selecon. A instrucao
    "marque a letra da prova (A ou B)" cita as duas, uma vez so."""
    contagem: Counter = Counter()
    for achado in re.finditer(r"\bTIPO\W{0,3}([1-4]|[A-D])\b", texto, re.IGNORECASE):
        contagem[f"TIPO {achado.group(1).upper()}"] += 1
    for achado in re.finditer(r"\bPROVA\W{0,3}([A-D])\b|\b([A-D])\W{0,3}PROVA\b", texto):
        contagem[f"PROVA {(achado.group(1) or achado.group(2)).upper()}"] += 1
    if not contagem:
        return None
    (primeira, vezes), *resto = contagem.most_common()
    if resto and resto[0][1] == vezes:
        return None
    return primeira
