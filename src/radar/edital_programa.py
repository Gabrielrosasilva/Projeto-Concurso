"""O conteudo programatico do edital: que assuntos cada materia pode cobrar.

O `edital_materias` ja le o QUADRO do edital, que diz quantas questoes cada
materia vale. Este arquivo le o ANEXO seguinte, que diz o que cai dentro de
cada uma delas - e sao duas coisas diferentes: o quadro da o peso, e o
programa da o conteudo.

Para que serve: a classificacao de assunto paga (`radar assuntos`) escolhia o
rotulo por conta propria, e inventava nome. Com esta lista ela passa a
ESCOLHER dentro do que o edital prometeu cobrar. O ganho nao e de economia, e
de verdade: "Regras minimas da ONU para o tratamento de pessoas presas" e um
item do edital, e nenhum modelo ia acertar essa formulacao sozinho.

A regra de sempre vale aqui: **o texto e o do edital**. Nada e reescrito, nem
encurtado, nem traduzido para um nome mais bonito - inclusive os defeitos
dele. O edital de 2019 escreveu "Acao penal; especies", e por isso "especies"
aparece na lista sozinho; escreveu "Decreto º 7.037/2009" sem o "n", e assim
fica. Consertar na mao seria eu decidindo o que a banca quis dizer.
"""
import logging
import re
from pathlib import Path

from radar.edital_materias import arrumar_nome
from radar.questoes import extrair_texto

log = logging.getLogger(__name__)

# Onde o anexo de programas comeca e onde ele acaba, no edital de 2019. Sao
# marcos do proprio documento, e nao posicao fixa: o anexo nao e sempre o
# mesmo numero de pagina.
#
# O marco tem que estar sozinho na linha e em maiuscula: o corpo do edital
# fala em "programa da prova escrita" no meio de paragrafo mais de uma vez, e
# comecar por ali trazia o capitulo de prova de capacidade fisica inteiro
# dentro da lista de assuntos.
INICIO_DO_PROGRAMA = re.compile(r"(?m)^\s*PROGRAMAS?\s+DA\s+PROVA\s+ESCRITA\s*$")
FIM_DO_PROGRAMA = re.compile(r"(?im)^\s*anexo\s+\d+\b(?!\s+programas?)")

# Cabecalho e rodape de pagina que caem no meio do anexo.
MOBILIA = re.compile(
    r"(?im)^\s*(estado de santa catarina"
    r"|secretaria de estado.*"
    r"|p[aá]gina \d+ de \d+"
    r"|anexo \d+.*"
    r"|programas.*)\s*$"
)

# O nome da materia vem em linha propria e toda em maiuscula, como no quadro.
NOME_DA_MATERIA = re.compile(
    r"(?m)^\s*([A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ \-]{4,})\s*$"
)

# A referencia de artigo nao e assunto: e onde ler. "(arts. 13 a 25)" aparece
# em metade dos itens de Direito Penal e so atrapalha o rotulo.
REFERENCIA_DE_ARTIGO = re.compile(r"\(\s*(?:arts?\.?|artigos?)\s[^)]*\)", re.IGNORECASE)

# "publicada no D.O.U. de 24 de agosto de 2006" idem: e a mesma lei outra vez.
PUBLICACAO = re.compile(
    r",?\s*publicad[ao]s?\s+no\s+D\s*\.?\s*O\s*\.?\s*U\s*\.?[^()]*", re.IGNORECASE
)

ENUMERACAO = re.compile(r"^\d{1,2}\.\s*")

# Ponto que NAO fecha item: numero (7.210), e as abreviacoes que o edital usa.
# Elas viram marca antes do corte e voltam depois - sem isso, "Lei n.º 6.745"
# vira tres assuntos.
ABREVIACOES = (
    (re.compile(r"(?i)\bn\.\s*º"), "\x01"),
    (re.compile(r"(?i)\bD\.O\.U\."), "\x02"),
    (re.compile(r"(?i)\barts?\."), "\x03"),
    (re.compile(r"(\d)\.(\d)"), "\\1\x04\\2"),
)

DE_VOLTA = {"\x01": "n.º", "\x02": "D.O.U.", "\x03": "art.", "\x04": "."}

# Onde um item acaba: no ponto-e-virgula sempre, e no ponto so quando o
# proximo comeca com maiuscula ou numero. O edital tem "Processos. dos crimes
# de responsabilidade..." - ali o ponto e engano dele, e cortar criaria um
# assunto que comeca no meio da frase.
CORTE = re.compile(r";|\.(?=\s*(?:[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ0-9]|$))")

# Abaixo disso nao e nome de assunto, e sim sobra de pontuacao.
TAMANHO_MINIMO = 4


def _limpar_item(bruto: str) -> str:
    texto = bruto
    for marca, volta in DE_VOLTA.items():
        texto = texto.replace(marca, volta)
    # Ponto seguido de minuscula sobrou de erro de digitacao do edital: ele nao
    # separa nada, e deixa "Processos. dos crimes" no meio do rotulo.
    texto = re.sub(r"\.\s+(?=[a-zà-ÿ])", " ", texto)
    return ENUMERACAO.sub("", texto.strip()).strip(" -,.")


def _assuntos_da_materia(corpo: str) -> list[str]:
    corpo = REFERENCIA_DE_ARTIGO.sub(" ", corpo)
    corpo = PUBLICACAO.sub(" ", corpo)
    corpo = re.sub(r"\s+\)", ")", corpo)
    corpo = re.sub(r"\s+", " ", corpo).strip()

    for padrao, marca in ABREVIACOES:
        corpo = padrao.sub(marca, corpo)

    achados = []
    for pedaco in CORTE.split(corpo):
        item = _limpar_item(pedaco)
        if len(item) >= TAMANHO_MINIMO and item not in achados:
            achados.append(item)
    return achados


def ler_programa(texto: str) -> dict[str, list[str]]:
    """{materia: [assunto, ...]} pelo anexo de programas do edital.

    Devolve {} quando o anexo nao esta no texto - edital que nao traz programa
    nao vira lista inventada, pela mesma razao que o quadro de materias e
    recusado quando nao fecha a conta.
    """
    comeco = INICIO_DO_PROGRAMA.search(texto or "")
    if not comeco:
        return {}

    bloco = texto[comeco.end():]
    fim = FIM_DO_PROGRAMA.search(bloco)
    if fim:
        bloco = bloco[:fim.start()]

    bloco = MOBILIA.sub("", bloco)

    programa: dict[str, list[str]] = {}
    nome = None
    inicio = 0
    for cabecalho in NOME_DA_MATERIA.finditer(bloco):
        if nome:
            programa[nome] = _assuntos_da_materia(bloco[inicio:cabecalho.start()])
        # Pela MESMA regra do quadro de materias: e assim que "LEI DE EXECUCAO
        # PENAL" daqui encontra a "Lei de Execucao Penal" de la.
        nome = arrumar_nome(cabecalho.group(1))
        inicio = cabecalho.end()
    if nome:
        programa[nome] = _assuntos_da_materia(bloco[inicio:])

    # Materia sem nenhum assunto legivel nao entra: ela seria uma lista vazia
    # na qual a IA nao teria o que escolher, e o comando trataria isso como
    # "pode inventar" - que e exatamente o que esta lista existe para impedir.
    return {materia: itens for materia, itens in programa.items() if itens}


def ler_programa_do_pdf(caminho: Path) -> dict[str, list[str]]:
    """O programa do edital em PDF. Erro de leitura devolve {}, nao excecao.

    O modo `layout` e obrigatorio aqui: no modo normal o texto justificado do
    anexo volta com espaco no meio das palavras, e o assunto "cidadania e
    direitos politicos" chegava escrito "cidad ania e direitos politicos".
    """
    try:
        texto = extrair_texto(caminho, layout=True)
    except Exception as erro:  # noqa: BLE001 - PDF ruim e rotina, nao acidente
        log.warning("nao li o programa de %s (%s)", caminho.name, type(erro).__name__)
        return {}

    # A palavra partida no fim da linha volta inteira, COM o hifen: no anexo de
    # 2019 a unica ocorrencia e "Tabelas-verdade", que e hifenizada de verdade.
    # Juntar sem o hifen dava "Tabelasverdade".
    texto = re.sub(r"(\w)-[ \t]*\n[ \t]*(\w)", r"\1-\2", texto)
    return ler_programa(texto)
