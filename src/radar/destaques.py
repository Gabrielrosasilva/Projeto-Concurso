"""O sublinhado e o negrito do caderno, que a leitura do texto perde (decisao 178).

A questao diz "o termo sublinhado pode ser substituido por" e a tela mostrava
o texto sem o sublinhado: o `pypdf` le so as letras. No caderno, o sublinhado
nao e um atributo da letra - e um traco desenhado logo abaixo dela (na FEPESE,
uma linha ondulada) - e o negrito e a fonte ("MyriadPro-Bold"). Os dois so se
acham com a POSICAO de cada letra e os tracos da pagina, que o `pdfminer` da.

Tres passos, e nenhum muda o texto da questao (nem a chave, nem a
classificacao):

1. `ler_marcas`: os blocos de texto do caderno, com o trecho sublinhado ou em
   negrito de cada um;
2. `localizar`: cada trecho marcado vai para o campo da questao em que ele
   esta - o enunciado, uma alternativa ou o texto de apoio -, achado pelo
   texto em volta, e so quando o lugar e um so;
3. `partes`: o campo cortado em pedacos, cada um com as suas marcas, para a
   tela desenhar.

O caderno sem traco (escaneado, ou o sublinhado que a banca esqueceu) fica
sem marca: a tela mostra o texto como antes.
"""
from __future__ import annotations

import io
import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path

SUBLINHADO = "sublinhado"
NEGRITO = "negrito"

#: O nome da fonte que diz negrito. "Black" e "Heavy" sao mais grossas ainda.
FONTES_NEGRITAS = ("bold", "black", "heavy", "semibold", "demibold")

#: O traco que sublinha e fino e deitado: ate 3 pontos de altura, e ao menos
#: 2 de comprimento (o ponto solto nao e sublinhado).
ALTURA_MAXIMA_DO_TRACO = 3.0
COMPRIMENTO_MINIMO_DO_TRACO = 2.0
#: Onde o traco tem de passar para sublinhar a letra, em fracao do tamanho
#: dela: da linha de base para baixo ate metade da altura (a linha ondulada da
#: FEPESE passa uns 2 pontos abaixo da base, numa letra de 10), e nunca acima
#: da base - o traco que corta a letra no meio e tachado, e nao sublinhado.
ABAIXO_DA_BASE = 0.5
ACIMA_DA_BASE = 0.1
#: O traco grosso e a regua entre as questoes (4 a 12 pontos na FEPESE); o
#: sublinhado e fino (a linha ondulada tem 0,4).
ESPESSURA_MAXIMA_DO_TRACO = 2.0
#: O traco que passa das letras que cobre mais que isto, para um lado ou para
#: o outro, e regua debaixo da ultima linha (o Cebraspe), e nao sublinhado: o
#: sublinhado acaba onde acaba a palavra.
FOLGA_DO_TRACO = 6.0
#: A letra menor que isto, perto das outras do bloco, e o "o" elevado do
#: ordinal ("2º", "nº"): a fonte desenha o traco embaixo dele, e a questao
#: nao destaca nada ali.
LETRA_ELEVADA = 0.75

#: Quantas letras do texto em volta se tenta casar, da mais longa para a mais
#: curta: o trecho marcado so vale onde o texto em volta e o mesmo.
CONTEXTOS = (40, 25, 15, 8, 4, 0)
#: O trecho mais o texto em volta, sem os espacos: abaixo disso o casamento
#: pode ser coincidencia ("a" sublinhado acha um "a" em qualquer lugar).
MINIMO_PARA_CASAR = 12

#: Onde a marca mora na questao: o enunciado, o texto de apoio, ou a letra da
#: alternativa.
ENUNCIADO = "enunciado"
TEXTO_BASE = "texto_base"


@dataclass(frozen=True)
class BlocoMarcado:
    """Um bloco de texto do caderno e os trechos marcados nele."""

    texto: str
    #: ((inicio, fim, tipo), ...) no `texto`.
    marcas: tuple


# --- 1. ler o caderno -----------------------------------------------------------------

def eh_negrito(fonte: str | None) -> bool:
    nome = (fonte or "").lower()
    return any(marca in nome for marca in FONTES_NEGRITAS)


def _pdf_que_o_pdfminer_le(caminho: Path) -> io.BytesIO:
    """O caderno regravado pelo `pypdf`. Os cadernos do InDesign guardam o
    indice em dois formatos ao mesmo tempo, e com esse o `pdfminer` nao acha
    pagina nenhuma (0 de 16 na CINCATARINA 2024); regravado, acha todas."""
    from pypdf import PdfReader, PdfWriter

    for ruidoso in ("pypdf", "pypdf._cmap", "pypdf._reader", "pypdf.generic",
                    "pypdf._writer"):
        logging.getLogger(ruidoso).setLevel(logging.ERROR)
    copia = io.BytesIO()
    PdfWriter(clone_from=PdfReader(str(caminho))).write(copia)
    copia.seek(0)
    return copia


def _tracos(objeto, saida: list) -> None:
    """Os tracos finos e deitados da pagina: (x0, x1, altura do meio)."""
    from pdfminer.layout import LTCurve, LTTextContainer

    for filho in objeto:
        # LTLine e LTRect sao LTCurve: uma regra so para os tres.
        if isinstance(filho, LTCurve):
            if (filho.height <= ALTURA_MAXIMA_DO_TRACO
                    and filho.width >= COMPRIMENTO_MINIMO_DO_TRACO
                    and (getattr(filho, "linewidth", 0) or 0) <= ESPESSURA_MAXIMA_DO_TRACO):
                saida.append((filho.x0, filho.x1, (filho.y0 + filho.y1) / 2))
        elif not isinstance(filho, LTTextContainer) and hasattr(filho, "__iter__"):
            _tracos(filho, saida)


def _blocos(objeto, saida: list) -> None:
    from pdfminer.layout import LTTextBox

    for filho in objeto:
        if isinstance(filho, LTTextBox):
            saida.append(filho)
        elif hasattr(filho, "__iter__") and not isinstance(filho, str):
            try:
                _blocos(filho, saida)
            except TypeError:
                pass


def _embaixo(letra, x0: float, x1: float, y: float) -> bool:
    """O traco (x0, x1, altura) passa logo abaixo da linha de base da letra,
    na largura dela?"""
    base = letra.matrix[5]
    tamanho = letra.size or 0
    meio = (letra.x0 + letra.x1) / 2
    return (x0 - 0.5 <= meio <= x1 + 0.5
            and base - ABAIXO_DA_BASE * tamanho <= y <= base + ACIMA_DA_BASE * tamanho)


def sublinhadas(letras: list, tracos: list) -> set[int]:
    """Os indices das letras sublinhadas.

    Cada traco cobre as letras logo acima dele, e so vale quando acaba perto
    delas: a regua que passa da ultima palavra nao sublinha a linha. A letra
    elevada do ordinal fica de fora."""
    tamanhos = sorted(letra.size or 0 for letra in letras)
    comum = tamanhos[len(tamanhos) // 2] if tamanhos else 0
    marcadas: set[int] = set()
    for x0, x1, y in tracos:
        cobertas = [i for i, letra in enumerate(letras) if _embaixo(letra, x0, x1, y)]
        if not cobertas:
            continue
        de = min(letras[i].x0 for i in cobertas)
        ate = max(letras[i].x1 for i in cobertas)
        if x0 < de - FOLGA_DO_TRACO or x1 > ate + FOLGA_DO_TRACO:
            continue
        marcadas.update(i for i in cobertas
                        if (letras[i].size or 0) >= LETRA_ELEVADA * comum)
    return marcadas


def _marcas_do_bloco(bloco, tracos: list) -> BlocoMarcado | None:
    """O texto do bloco e os trechos marcados. O espaco entre duas palavras
    da mesma marca entra nela: "no qual" e um trecho, e nao dois."""
    from pdfminer.layout import LTChar, LTTextLine

    texto = ""
    letras: list = []          # as letras de verdade, na ordem
    posicoes: list[int] = []   # onde cada uma comeca no `texto`
    for linha in bloco:
        if not isinstance(linha, LTTextLine):
            continue
        for letra in linha:
            pedaco = letra.get_text()
            if isinstance(letra, LTChar) and pedaco.strip():
                letras.append(letra)
                posicoes.append(len(texto))
            texto += pedaco
    tipos: list[set] = [set() for _ in texto]
    for i in sublinhadas(letras, tracos):
        for k in range(posicoes[i], posicoes[i] + len(letras[i].get_text())):
            tipos[k].add(SUBLINHADO)
    for letra, posicao in zip(letras, posicoes):
        if eh_negrito(letra.fontname):
            for k in range(posicao, posicao + len(letra.get_text())):
                tipos[k].add(NEGRITO)
    marcas = []
    for tipo in (SUBLINHADO, NEGRITO):
        inicio = None
        for i, (letra, marca) in enumerate(zip(texto, tipos)):
            if tipo in marca:
                if inicio is None:
                    inicio = i
                fim = i + 1
            elif inicio is not None and not letra.isspace():
                marcas.append((inicio, fim, tipo))
                inicio = None
        if inicio is not None:
            marcas.append((inicio, fim, tipo))
    return BlocoMarcado(texto=texto, marcas=tuple(sorted(marcas))) if marcas else None


def ler_marcas(caminho: Path) -> list[BlocoMarcado]:
    """Os blocos do caderno que tem algum trecho sublinhado ou em negrito."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LAParams

    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    saida = []
    for pagina in extract_pages(_pdf_que_o_pdfminer_le(caminho), laparams=LAParams()):
        tracos: list = []
        _tracos(pagina, tracos)
        blocos: list = []
        _blocos(pagina, blocos)
        for bloco in blocos:
            marcado = _marcas_do_bloco(bloco, tracos)
            if marcado is not None:
                saida.append(marcado)
    return saida


# --- 2. achar o trecho na questao -----------------------------------------------------

def _sem_espaco(texto: str) -> tuple[str, list[int]]:
    """O texto sem espaco nenhum, e de onde veio cada letra no original.

    O `pypdf` e o `pdfminer` quebram linha e espacam cada um do seu jeito; a
    letra e a mesma. A ligadura ("ﬁ") vira duas letras (NFKC), e o hifen que
    parte a palavra no fim da linha sai: o leitor da questao ja a juntou."""
    letras: list[str] = []
    origem: list[int] = []
    i = 0
    while i < len(texto):
        letra = texto[i]
        if letra in "-­" and _fim_de_linha_partida(texto, i):
            i += 1
            continue
        for pedaco in unicodedata.normalize("NFKC", letra):
            if not pedaco.isspace():
                letras.append(pedaco)
                origem.append(i)
        i += 1
    return "".join(letras), origem


def _fim_de_linha_partida(texto: str, i: int) -> bool:
    """O hifen em "alter-\\nnativa": letra antes, quebra de linha e minuscula depois."""
    depois = texto[i + 1:i + 3]
    return (i > 0 and texto[i - 1].isalpha() and depois[:1] == "\n"
            and depois[1:2].islower())


def _ocorrencias(onde: str, procurado: str) -> list[int]:
    achadas, inicio = [], onde.find(procurado)
    while inicio != -1:
        achadas.append(inicio)
        inicio = onde.find(procurado, inicio + 1)
    return achadas


def localizar(blocos: list[BlocoMarcado], campos: dict) -> dict:
    """{id da questao: [marca, ...]} - cada trecho marcado no campo em que ele
    esta, pelo texto em volta.

    `campos` e {id da questao: {campo: texto}}, com o campo "enunciado",
    "texto_base" ou a letra da alternativa. O texto em volta vem do proprio
    bloco do caderno: tenta-se do mais longo ao mais curto, e vale o primeiro
    que cai num lugar so - o mesmo texto de apoio em varias questoes e um
    lugar so, e vai para todas elas. Duas alternativas iguais em questoes
    diferentes, ou o trecho que nao se acha, ficam sem marca: na duvida, o
    texto aparece como antes.
    """
    # O mesmo texto em varias questoes (o texto de apoio) e um lugar so.
    lugares: dict[str, list[tuple[int, str]]] = {}
    for questao_id, dela in campos.items():
        for campo, texto in dela.items():
            if texto:
                lugares.setdefault(texto, []).append((questao_id, campo))
    preparados = {texto: _sem_espaco(texto) for texto in lugares}

    saida: dict[int, list[dict]] = {}
    for bloco in blocos:
        corrido, origem = _sem_espaco(bloco.texto)
        for inicio, fim, tipo in bloco.marcas:
            # As letras do trecho no texto corrido do bloco.
            dentro = [k for k, o in enumerate(origem) if inicio <= o < fim]
            if not dentro:
                continue
            a, b = dentro[0], dentro[-1] + 1
            achado = _achar(corrido, a, b, preparados)
            if achado is None:
                continue
            texto, (de, ate) = achado
            for questao_id, campo in lugares[texto]:
                saida.setdefault(questao_id, []).append(
                    {"campo": campo, "inicio": de, "fim": ate, "tipo": tipo,
                     "trecho": texto[de:ate]})
    return {questao_id: juntar(marcas) for questao_id, marcas in saida.items()}


def _achar(corrido: str, a: int, b: int, preparados: dict):
    """(texto do campo, (inicio, fim)) do trecho corrido[a:b], ou None."""
    for esquerda in CONTEXTOS:
        for direita in CONTEXTOS:
            de, ate = max(0, a - esquerda), min(len(corrido), b + direita)
            procurado = corrido[de:ate]
            if len(procurado) < MINIMO_PARA_CASAR:
                continue
            achados = [(texto, pos) for texto, (sem, _o) in preparados.items()
                       for pos in _ocorrencias(sem, procurado)]
            if len(achados) == 1:
                texto, pos = achados[0]
                _sem, origem = preparados[texto]
                primeiro = pos + (a - de)
                ultimo = primeiro + (b - a) - 1
                return texto, (origem[primeiro], origem[ultimo] + 1)
            if len(achados) > 1:
                # Mais texto em volta nao achou um lugar so; menos tambem nao vai.
                break
    return _achar_a_alternativa_inteira(corrido[a:b], preparados)


def _achar_a_alternativa_inteira(trecho: str, preparados: dict):
    """A alternativa marcada inteira ("ao qual"): curta demais para o texto
    em volta, que no caderno e a letra e o quadradinho. Vale quando um campo,
    e so um, e exatamente o trecho."""
    iguais = [texto for texto, (sem, _o) in preparados.items() if sem == trecho]
    if len(iguais) != 1 or not trecho:
        return None
    texto = iguais[0]
    _sem, origem = preparados[texto]
    return texto, (origem[0], origem[-1] + 1)


def juntar(marcas: list[dict]) -> list[dict]:
    """Sem repetida (o caderno com duas versoes da a mesma marca duas vezes),
    e os pedacos vizinhos do mesmo tipo num so - a palavra partida no fim da
    linha vem em dois blocos ou duas marcas."""
    unicas = {(m["campo"], m["inicio"], m["fim"], m["tipo"]): m for m in marcas}
    ordem = sorted(unicas.values(), key=lambda m: (m["campo"], m["tipo"], m["inicio"]))
    saida: list[dict] = []
    for marca in ordem:
        anterior = saida[-1] if saida else None
        if (anterior and anterior["campo"] == marca["campo"]
                and anterior["tipo"] == marca["tipo"] and marca["inicio"] <= anterior["fim"]):
            if marca["fim"] > anterior["fim"]:
                anterior["trecho"] += marca["trecho"][anterior["fim"] - marca["inicio"]:]
                anterior["fim"] = marca["fim"]
            continue
        saida.append(dict(marca))
    return sorted(saida, key=lambda m: (m["campo"], m["inicio"], m["tipo"]))


# --- 3. a tela ------------------------------------------------------------------------

def partes(texto: str | None, marcas: list[dict] | None, campo: str) -> list[tuple[str, frozenset]]:
    """O texto do campo em pedacos, cada um com as suas marcas.

    So vale a marca cujo trecho ainda e o do texto: se o texto mudou (o
    caderno relido), a marca velha nao sublinha a palavra errada - fica de
    fora ate a proxima leitura das marcas.
    """
    texto = texto or ""
    # A letra da alternativa vem "a" ou "A" conforme a tela; e a mesma.
    validas = [m for m in (marcas or []) if str(m.get("campo", "")).lower() == campo.lower()
               and 0 <= m.get("inicio", -1) < m.get("fim", -1) <= len(texto)
               and texto[m["inicio"]:m["fim"]] == m.get("trecho")]
    if not validas:
        return [(texto, frozenset())] if texto else []
    cortes = sorted({0, len(texto)} | {m["inicio"] for m in validas}
                    | {m["fim"] for m in validas})
    saida = []
    for de, ate in zip(cortes, cortes[1:]):
        tipos = frozenset(m["tipo"] for m in validas if m["inicio"] <= de and ate <= m["fim"])
        saida.append((texto[de:ate], tipos))
    return saida
