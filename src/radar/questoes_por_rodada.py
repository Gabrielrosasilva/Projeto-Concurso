"""Separa em questoes o caderno de outra banca que vem em mais de uma versao:
a FGV, a Access, a Idecan e a Selecon nova (decisao 172).

As quatro so mudam em duas marcas:

  - **a da questao**: o numero sozinho na linha ("41", FGV), "Questao 26"
    sozinho na linha (Access), ou "13. Joao Henrique..." (Idecan, Selecon);
  - **a da alternativa**: "(A)" (FGV, Access, Idecan) ou "A)" (Selecon).

A leitura vai pelas rodadas de alternativas, de A ate a ultima letra, e a
questao e a marca que vem antes da rodada. Entre uma rodada e outra pode haver
mais de uma marca - o numero da linha de um texto de Portugues ("5", "10")
tambem fica sozinho na linha -, e vale a de numero seguinte ao da questao
anterior; sem ela, a ultima antes da rodada. A ordem das questoes pode vir
embaralhada pelas colunas (a Selecon da 24, 26, 23, 25...): cada questao
continua com a rodada dela logo abaixo.

**O PDF pode trazer mais de uma versao, ou mais de um cargo**: o "PROVA A" da
PM de Sergipe tem as paginas da Prova A e, depois, as da Prova B; o da
SENAPPEN junta os cadernos dos 8 cargos. So entram as paginas da `versao` da
lista (a pagina sem marca e da versao da anterior) e, quando a lista diz, as
do `cargo`. Sem pagina nenhuma da versao, o caderno e recusado.

A materia nao sai do caderno: a classificacao a decide, um pedido por caderno
(decisao 169). O gabarito vem pronto, do bloco da mesma versao
(`radar/gabarito_por_versao.py`).
"""
import re
from collections import Counter
from pathlib import Path

from radar.gabarito_por_versao import versao_do_caderno
from radar.questoes import Questao, _limpar, _tirar_simbolo_sem_desenho

MARCAS_DA_QUESTAO = {
    "numero": re.compile(r"(?m)^[ \t]*(\d{1,3})[ \t]*$"),
    "questao": re.compile(r"(?m)^[ \t]*Quest[aã]o[ \t]+(\d{1,3})[ \t]*$"),
    "ponto": re.compile(r"(?m)^[ \t]*(\d{1,3})\.[ \t]+(?=\S)"),
}

MARCAS_DA_ALTERNATIVA = {
    "parenteses": re.compile(r"(?m)^[ \t]*\(([A-E])\)[ \t]*"),
    "fecha": re.compile(r"(?m)^[ \t]*([A-E])\)[ \t]*"),
}

# O titulo de materia que cai entre a ultima alternativa e a proxima questao:
# "Nocoes de Direito Penal", "Legislacao Extravagante", "Tecnologia da
# Informacao, Seguranca Cibernetica e Crimes Digitais" (Idecan), "NOCOES DE
# DIREITO PENAL" (Access). E onde a ultima alternativa acaba - sem ele, o
# titulo grudava na alternativa E da questao 38 do Escrivao da PC SC.
PADRAO_TITULO = re.compile(
    r"(?m)^[ \t]*(?:(?i:No[cç][oõ]es de|Conhecimentos|Legisla[cç][aã]o|L[ií]ngua|Racioc[ií]nio|"
    r"Tecnologia da Informa[cç][aã]o|Inform[aá]tica|Contabilidade|[ÉE]tica|Atualidades|"
    r"Matem[aá]tica|Criminologia|Medicina Legal|Reda[cç][aã]o|Prova Discursiva)"
    r"[^\n.;:]{0,90}|[A-ZÀ-Ý][A-ZÀ-Ý ,\-–/]{8,}|Realiza[cç][aã]o:?)[ \t]*$")

SO_NUMERO = re.compile(r"^\s*\d{1,3}\s*$")
ALTERNATIVA_QUALQUER = re.compile(r"^\s*\(?[A-E]\)")

# A marca de canto da Selecon: "A" numa linha e "PROVA" na de baixo, ou
# "APROVA" numa linha so. Ela nem sempre cai nas pontas da pagina: na
# SENAPPEN grudava "APROVA" no fim da 18.
MARCA_DE_CANTO = re.compile(
    r"(?m)^[ \t]*(?:[A-D][ \t]*\n?[ \t]*PROVA|PROVA[ \t]+[A-D])[ \t]*$\n?")


def paginas_da_versao(paginas: list[str], versao: str | None,
                      cargo: str | None = None) -> list[str]:
    """So as paginas da versao e do cargo da lista. A pagina sem marca de
    versao (o miolo da FGV so tem a marca na capa) e da versao da anterior."""
    saida, atual = [], None
    for pagina in paginas:
        atual = versao_do_caderno(pagina) or atual
        if versao and atual != versao:
            continue
        if cargo and cargo.lower() not in pagina.lower():
            continue
        saida.append(pagina)
    return saida


def sem_cabecalho(paginas: list[str], tirar_numeros: bool = True) -> str:
    """O texto do caderno sem o cabecalho e o rodape de pagina: a linha das
    PONTAS da pagina (as 6 primeiras e as 6 ultimas; o "A / PROVA" do canto
    da Selecon e a 5a linha) que aparece nas pontas de metade das paginas ou
    mais. Na linha com "pagina", os digitos nao
    contam ("PAGINA 2" e "PAGINA 3" sao a mesma).

    So as pontas, porque o meio da pagina repete de verdade: a Access poe
    "(A) se apenas as afirmativas I e II estiverem corretas." em metade das
    paginas, e a Idecan repete "comprovada necessidade." nas cinco
    alternativas de uma pagina so - o limpador de linha repetida dos outros
    leitores, que conta no caderno inteiro, apagava as duas.

    A linha so de numero e o numero da pagina, e sai com `tirar_numeros`; na
    FGV ela e a marca da questao, e fica."""
    def forma(linha: str) -> str:
        linha = linha.strip()
        return re.sub(r"\d+", "#", linha) if re.search(r"p[aá]gina", linha, re.I) else linha

    def pontas(linhas: list[str]) -> set[int]:
        # A alternativa nunca e cabecalho, mesmo na ultima linha da pagina:
        # "(E) se todas estiverem corretas." fecha muitas paginas da Access.
        cheias = [i for i, linha in enumerate(linhas)
                  if linha.strip() and not SO_NUMERO.match(linha)
                  and not ALTERNATIVA_QUALQUER.match(linha)]
        return set(cheias[:6] + cheias[-6:])

    paginas = [MARCA_DE_CANTO.sub("", pagina) for pagina in paginas]
    em_quantas: Counter = Counter()
    for pagina in paginas:
        linhas = pagina.splitlines()
        em_quantas.update({forma(linhas[i]) for i in pontas(linhas)})
    minimo = max(3, (len(paginas) + 1) // 2)
    mobilia = {linha for linha, vezes in em_quantas.items() if vezes >= minimo}

    saida = []
    for pagina in paginas:
        linhas = pagina.splitlines()
        nas_pontas = pontas(linhas)
        for indice, linha in enumerate(linhas):
            if SO_NUMERO.match(linha):
                if not tirar_numeros:
                    saida.append(linha)
            elif indice not in nas_pontas or forma(linha) not in mobilia:
                saida.append(linha)
    return "\n".join(saida)


def _e_titulo(linha: str) -> bool:
    """A linha curta, sem pontuacao no fim, com a maioria das palavras em
    maiuscula: "Direitos Humanos", "Promocao da Igualdade Racial e de Genero".
    O fim de uma alternativa ("comprovada necessidade.") nao passa."""
    linha = linha.strip()
    if not linha or len(linha) > 90 or linha[-1] in ".;:?!)" or linha.startswith("("):
        return False
    palavras = [p for p in re.split(r"[\s,]+", linha) if p]
    grandes = [p for p in palavras if p[0].isupper()]
    return palavras[0][0].isupper() and len(grandes) * 2 >= len(palavras)


def _titulos_antes_das_marcas(texto: str, marcadores: list[re.Match]) -> list[int]:
    """Onde comeca o titulo que fica logo acima da marca de uma questao - o
    titulo que nenhuma lista preve. Ele pode quebrar em duas linhas
    ("Promocao da Igualdade Racial e de" / "Genero", na FGV)."""
    inicios = []
    for marcador in marcadores:
        fim = texto.rfind("\n", 0, marcador.start())
        inicio = None
        for _ in range(2):
            if fim <= 0:
                break
            comeco = texto.rfind("\n", 0, fim) + 1
            if not _e_titulo(texto[comeco:fim]):
                break
            inicio, fim = comeco, comeco - 1
        if inicio is not None:
            inicios.append(inicio)
    return inicios


def _rodadas(texto: str, padrao: re.Pattern, letras: str) -> list[list[re.Match]]:
    """As sequencias A, B... ate a ultima letra, na ordem do texto. Uma
    rodada incompleta vale se tiver pelo menos duas letras."""
    rodadas: list[list[re.Match]] = []
    atual: list[re.Match] = []
    for marca in padrao.finditer(texto):
        letra = marca.group(1)
        if letra not in letras:
            continue
        esperada = letras[len(atual)] if atual and len(atual) < len(letras) else None
        if letra == "A":
            if len(atual) >= 2:
                rodadas.append(atual)
            atual = [marca]
        elif letra == esperada:
            atual.append(marca)
            if len(atual) == len(letras):
                rodadas.append(atual)
                atual = []
        else:
            if len(atual) >= 2:
                rodadas.append(atual)
            atual = []
    if len(atual) >= 2:
        rodadas.append(atual)
    return rodadas


def _dentro(numero: int, ler: list[str] | None) -> bool:
    if not ler:
        return True
    for faixa in ler:
        inicio, _, fim = str(faixa).partition("-")
        if int(inicio) <= numero <= int(fim or inicio):
            return True
    return False


def dividir_em_questoes(texto: str, gabarito: dict[int, str | None] | None = None,
                        marca: str = "numero", alternativa: str = "parenteses",
                        letras: str = "ABCDE", ler: list[str] | None = None) -> list[Questao]:
    """As questoes do caderno, na ordem do numero, com a resposta do
    gabarito (None e anulada na que ele anulou). `ler` limita as questoes
    ("31-80"); sem ele, todas. O texto ja vem sem o cabecalho de pagina
    (`sem_cabecalho`)."""
    texto = texto.replace("\t", " ")
    gabarito = gabarito or {}
    marcadores = list(MARCAS_DA_QUESTAO[marca].finditer(texto))
    cortes = sorted({m.start() for m in marcadores}
                    | {m.start() for m in PADRAO_TITULO.finditer(texto)}
                    | set(_titulos_antes_das_marcas(texto, marcadores)))
    rodadas = _rodadas(texto, MARCAS_DA_ALTERNATIVA[alternativa], letras)

    questoes: list[Questao] = []
    anterior, fim_anterior = 0, 0
    for indice, rodada in enumerate(rodadas):
        antes = [m for m in marcadores if fim_anterior <= m.start() < rodada[0].start()]
        fim_anterior = rodada[-1].end()
        if not antes:
            continue
        seguinte = [m for m in antes if int(m.group(1)) == anterior + 1]
        marcador = seguinte[0] if seguinte else antes[-1]
        numero = int(marcador.group(1))
        anterior = numero

        limite = rodadas[indice + 1][0].start() if indice + 1 < len(rodadas) else len(texto)
        depois = [corte for corte in cortes if rodada[-1].end() <= corte < limite]
        fim_da_ultima = min(depois) if depois else limite

        alternativas = {}
        for posicao, achado in enumerate(rodada):
            ate = rodada[posicao + 1].start() if posicao + 1 < len(rodada) else fim_da_ultima
            conteudo = _limpar(texto[achado.end():ate])
            if conteudo:
                alternativas[achado.group(1).lower()] = conteudo
        enunciado = _limpar(texto[marcador.end():rodada[0].start()])
        if not enunciado or len(alternativas) < 2 or not _dentro(numero, ler):
            continue
        anulada = numero in gabarito and gabarito[numero] is None
        questoes.append(Questao(numero=numero, enunciado=enunciado,
                                alternativas=alternativas, resposta=gabarito.get(numero),
                                anulada=anulada))

    melhores: dict[int, Questao] = {}
    for questao in questoes:
        ja = melhores.get(questao.numero)
        if ja is None or len(questao.enunciado) > len(ja.enunciado):
            melhores[questao.numero] = questao
    return [melhores[n] for n in sorted(melhores)]


def paginas_do_caderno(caminho: Path) -> list[str]:
    from pypdf import PdfReader

    return [_tirar_simbolo_sem_desenho(pagina.extract_text() or "")
            for pagina in PdfReader(str(caminho)).pages]


def ler_prova(caminho: Path, gabarito: dict[int, str | None] | None = None,
              versao: str | None = None, cargo: str | None = None,
              marca: str = "numero", **opcoes) -> list[Questao]:
    """Le o caderno, so nas paginas da versao (e do cargo), com o gabarito
    da mesma versao. ValueError quando nenhuma pagina e da versao."""
    paginas = paginas_da_versao(paginas_do_caderno(caminho), versao, cargo)
    if not paginas:
        raise ValueError(f"nenhuma pagina do caderno e da versao {versao}"
                         + (f" e do cargo {cargo}" if cargo else ""))
    texto = sem_cabecalho(paginas, tirar_numeros=marca != "numero")
    return dividir_em_questoes(texto, gabarito, marca=marca, **opcoes)
