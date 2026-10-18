"""Separa o caderno de multipla escolha do Cebraspe em questoes (decisao 169).

O Cebraspe autoriza no proprio caderno: "E permitida a reproducao deste
material apenas para fins didaticos, desde que citada a fonte". O radar guarda
o link de cada caderno, que e a fonte.

Como o caderno se le, e o que cada coisa muda no codigo:

  1. **"Questao N" numa linha sozinha** abre a questao: e o corte, e por ele
     a leitura vai questao a questao;
  2. **as alternativas sao "A " a "E " no comeco da linha, sem parentese** - e
     o enunciado tambem pode comecar assim ("A partir das ideias..."). Vale a
     ULTIMA sequencia completa de A a E da questao;
  3. **o caderno "com justificativas"** traz, depois das alternativas, a parte
     "||JUSTIFICATIVAS||" (ou "JUSTIFICATIVAS"), com cada alternativa marcada
     CORRETA/INCORRETA ou CERTO/ERRADO. A justificativa nunca entra no texto da
     questao; quando o gabarito definitivo e de outra versao do caderno (a
     SERES/PE 2021), a resposta sai dela;
  4. **o caderno nao diz a materia** - so "Conhecimentos Basicos/Especificos".
     A materia e pergunta da classificacao (o bloco generico, decisao 169), e
     a entrada da prova no config diz so QUAIS questoes ler (`ler`): as de
     Direito, sem o Portugues e o Raciocinio;
  5. **o texto de apoio** ("Situacao hipotetica 1A3-I", "Texto 1A1-I") vem
     antes da primeira questao que o usa, e vira o texto-base de cada questao
     que o cita - no banco, nunca em arquivo versionado (decisao 132).

O gabarito definitivo e um PDF a parte, em fileiras: uma linha com os numeros
(as vezes colados: "1 23456789 1 0") e, embaixo, as letras coladas
("E CDXACBDDEE..."), com X na anulada.
"""
import re
from pathlib import Path

from radar.questoes import Questao, _limpar, extrair_texto

PADRAO_QUESTAO = re.compile(r"(?m)^[ \t]*Quest[ãa]o[ \t]+(\d{1,3})[ \t]*$")
PADRAO_JUSTIFICATIVAS = re.compile(r"(?m)^[ \t]*(?:\|\|)?JUSTIFICATIVAS(?:\|\|)?[ \t]*$")
# O titulo de secao ("-- CONHECIMENTOS ESPECIFICOS --") e o cabecalho do
# texto de apoio: e onde a ultima alternativa acaba.
PADRAO_SECAO = re.compile(r"(?m)^[ \t]*--.*--[ \t]*$")
PADRAO_APOIO = re.compile(
    r"(?m)^[ \t]*(?:Texto|Situa[çc][ãa]o hipot[ée]tica)[ \t]+([0-9A-Z]+-[IVX]+)[ \t]*$")
# Linhas que nao sao texto de ninguem: o cabecalho de pagina, o "Espaco
# livre" e o numero de pagina sozinho. (O limpador de linha repetida dos
# outros cadernos nao serve aqui: "JUSTIFICATIVAS" se repete em toda questao,
# e e ele que separa a alternativa da justificativa.)
PADRAO_SOBRA = re.compile(
    r"(?m)^[ \t]*(?:Espa[çc]o livre|CEBRASPE[ \t]*[–-].*|\d{1,3})[ \t]*$")
# O rodape que o pypdf cola no fim da linha de cima: o codigo da matriz e o
# cabecalho ("662001_01N27724 CEBRASPE – PC/RJ – Edital: 2021").
PADRAO_RODAPE_COLADO = re.compile(
    r"[ \t]*(?:\b\d{6}_\d{2}N\d+\b)?[ \t]*CEBRASPE[ \t]*[–-][^\n]*?Edital:[ \t]*\d{4}")
# Na justificativa: "||A|| - ..." ou "A – ERRADO." no comeco da linha.
PADRAO_LETRA_DA_JUSTIFICATIVA = re.compile(r"(?m)^[ \t]*(?:\|\|)?([A-E])(?:\|\|)?[ \t]*[-–][ \t]*")
MARCA_DA_CERTA = re.compile(r"(?<![A-Z])(?:CORRETA|CERTO)\b")


def ler_gabarito(texto: str) -> dict[int, str | None]:
    """{numero: letra minuscula}, None na anulada (X), das fileiras do PDF.

    A linha de numeros so diz onde a fileira comeca (o primeiro numero); a
    linha de letras, sem os espacos, da uma letra por questao, em ordem.
    """
    gabarito: dict[int, str | None] = {}
    comeco = None
    for linha in texto.splitlines():
        enxuta = linha.strip()
        if re.fullmatch(r"[\d ]{5,}", enxuta) and re.search(r"[1-9]", enxuta):
            comeco = int(enxuta.split()[0])
            continue
        # A ultima fileira vem com o enchimento colado: "D BADCCACCD 0000000000".
        letras = re.sub(r"\s*0[0 ]*$", "", enxuta).replace(" ", "")
        if comeco is not None and re.fullmatch(r"[A-EX]{2,}", letras):
            for deslocamento, letra in enumerate(letras):
                gabarito[comeco + deslocamento] = None if letra == "X" else letra.lower()
            comeco = None
    return gabarito


def faixas(ler: list | str | None) -> list[tuple[int, int]]:
    """["21-60", "75"] -> [(21, 60), (75, 75)]. Vazio: todas."""
    if not ler:
        return []
    saida = []
    for parte in ([ler] if isinstance(ler, str) else ler):
        inicio, _, fim = str(parte).partition("-")
        saida.append((int(inicio), int(fim or inicio)))
    return saida


def _dentro(numero: int, intervalos: list[tuple[int, int]]) -> bool:
    return not intervalos or any(a <= numero <= b for a, b in intervalos)


def _alternativas(corpo: str, letras: str) -> tuple[str, dict[str, str]] | None:
    """(enunciado, {letra: texto}) pela ULTIMA sequencia completa de letras."""
    linhas = corpo.splitlines()
    inicios = {letra: [i for i, linha in enumerate(linhas)
                       if re.match(rf"^[ \t]*{letra}[ \t]+\S", linha)]
               for letra in letras}
    for primeira in reversed(inicios[letras[0]]):
        posicoes, atual = [primeira], primeira
        for letra in letras[1:]:
            seguinte = next((i for i in inicios[letra] if i > atual), None)
            if seguinte is None:
                break
            posicoes.append(seguinte)
            atual = seguinte
        if len(posicoes) != len(letras):
            continue
        enunciado = _limpar("\n".join(linhas[:primeira]))
        alternativas = {}
        for indice, (letra, posicao) in enumerate(zip(letras, posicoes)):
            ate = posicoes[indice + 1] if indice + 1 < len(posicoes) else len(linhas)
            pedaco = "\n".join(linhas[posicao:ate])
            pedaco = re.sub(rf"^[ \t]*{letra}[ \t]+", "", pedaco)
            alternativas[letra.lower()] = _limpar(pedaco)
        return enunciado, alternativas
    return None


def _certa_das_justificativas(justificativas: str) -> str | None:
    """A letra que a justificativa marca CORRETA/CERTO, quando e uma so."""
    marcas = list(PADRAO_LETRA_DA_JUSTIFICATIVA.finditer(justificativas))
    certas = []
    for indice, marca in enumerate(marcas):
        fim = marcas[indice + 1].start() if indice + 1 < len(marcas) else len(justificativas)
        if MARCA_DA_CERTA.search(justificativas[marca.end():fim][:300]):
            certas.append(marca.group(1).lower())
    return certas[0] if len(set(certas)) == 1 else None


def dividir_em_questoes(texto: str, gabarito: dict[int, str | None] | None = None,
                        ler: list | str | None = None, letras: str = "ABCDE",
                        resposta_das_justificativas: bool = False,
                        anuladas: list[int] | None = None) -> list[Questao]:
    """As questoes do caderno, com resposta e texto de apoio."""
    texto = PADRAO_SOBRA.sub("", PADRAO_RODAPE_COLADO.sub("", texto))
    intervalos = faixas(ler)
    anuladas = set(anuladas or [])
    gabarito = gabarito or {}
    marcadores = list(PADRAO_QUESTAO.finditer(texto))
    apoios = _textos_de_apoio(texto, marcadores)

    questoes = []
    for indice, marcador in enumerate(marcadores):
        numero = int(marcador.group(1))
        if not _dentro(numero, intervalos):
            continue
        fim = marcadores[indice + 1].start() if indice + 1 < len(marcadores) else len(texto)
        bloco = texto[marcador.end():fim]
        justificativas = ""
        achado = PADRAO_JUSTIFICATIVAS.search(bloco)
        if achado:
            bloco, justificativas = bloco[:achado.start()], bloco[achado.end():]
        # A ultima alternativa acaba no titulo de secao ou no texto de apoio.
        corte = [m.start() for m in (*PADRAO_SECAO.finditer(bloco), *PADRAO_APOIO.finditer(bloco))]
        if corte:
            bloco = bloco[:min(corte)]
        lido = _alternativas(bloco, letras)
        if lido is None:
            continue
        enunciado, alternativas = lido
        if not enunciado:
            continue
        if resposta_das_justificativas:
            resposta = _certa_das_justificativas(justificativas)
        else:
            resposta = gabarito.get(numero)
        anulada = numero in anuladas or (numero in gabarito and gabarito[numero] is None)
        citados = [apoio for codigo, apoio in apoios.items() if codigo in enunciado]
        questao = Questao(numero=numero, enunciado=enunciado, alternativas=alternativas,
                          resposta=None if anulada else resposta, anulada=anulada)
        if citados:
            questao.texto_base = "\n\n".join(citados)
        questoes.append(questao)
    return questoes


def _textos_de_apoio(texto: str, marcadores: list[re.Match]) -> dict[str, str]:
    """{codigo: texto} de cada texto de apoio do caderno, ate a questao seguinte."""
    inicios = [m.start() for m in marcadores]
    apoios = {}
    for cabecalho in PADRAO_APOIO.finditer(texto):
        fim = next((i for i in inicios if i > cabecalho.start()), len(texto))
        corpo = PADRAO_SECAO.sub("", texto[cabecalho.end():fim])
        apoios[cabecalho.group(1)] = _limpar(corpo)
    return apoios


def ler_prova(caminho: Path, caminho_do_gabarito: Path | None = None, **opcoes) -> list[Questao]:
    """Le um caderno do Cebraspe, com o gabarito definitivo ao lado quando ha."""
    gabarito = ler_gabarito(extrair_texto(caminho_do_gabarito)) if caminho_do_gabarito else {}
    return dividir_em_questoes(extrair_texto(caminho), gabarito, **opcoes)
