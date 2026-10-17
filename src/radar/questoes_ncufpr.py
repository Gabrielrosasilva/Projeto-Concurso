"""Separa o caderno do NC-UFPR (Nucleo de Concursos da UFPR) em questoes.

A banca da Policia Civil PR 2020 e das Guardas Municipais do Parana (decisao
167). O caderno "definitivo" e o mais facil de todos os do acervo, porque traz
o gabarito dentro:

  1. **a resposta certa vem marcada** com "►" antes da letra ("►b) estelionato."),
     e a questao anulada tem asterisco no numero ("*28 - ...") e uma nota
     depois ("*Questao anulada, portanto todos os candidatos serao pontuados.");
  2. **cinco alternativas**, de a) a e), e o numero no formato "01 - ";
  3. **a materia e o titulo em maiusculas** antes do bloco ("NOCOES DE DIREITO
     PENAL"), e vale ate o titulo seguinte;
  4. **as palavras vem separadas por TAB** nas linhas justificadas, e o numero
     da pagina ("3/14") fica solto entre as linhas.

O que e igual ao da IESES, e por isso tem a mesma forma: a leitura parte das
ALTERNATIVAS (uma rodada de a) a e) fecha uma questao), e a ultima
alternativa acaba onde comeca a questao seguinte ou o proximo titulo - senao
ela levaria o enunciado de baixo junto, o defeito que a IESES tinha.

A prova discursiva do fim do caderno nao tem alternativa, e fica de fora.
"""
import re
from pathlib import Path

from radar.questoes import Questao, _limpar, extrair_texto

LETRAS = "abcde"
MARCA_DA_CERTA = "►"

# "a) texto", "►b) texto", "►\td) 1,6 L." - a marca pode vir antes, com espaco.
PADRAO_ALTERNATIVA = re.compile(r"(?m)^[ \t]*(►)?[ \t]*([a-e])\)[ \t]*")

# "01 - Enunciado" ou "*28 - Enunciado" (anulada). Dois digitos: a lista
# numerada de dentro do enunciado ("1. ...") nao casa.
PADRAO_QUESTAO = re.compile(r"(?m)^[ \t]*(\*)?(\d{2})[ \t]*-[ \t]")

# O titulo da materia: uma linha so de maiusculas ("NOCOES DE DIREITO PENAL").
PADRAO_TITULO = re.compile(r"(?m)^[ \t]*([A-ZÀ-Ý][A-ZÀ-Ý ,\-–]{5,}?)[ \t]*$")

# O numero da pagina, sozinho na linha.
PADRAO_PAGINA = re.compile(r"(?m)^[ \t]*\d{1,2}/\d{1,2}[ \t]*$")

# A nota da anulada, que pode quebrar em duas linhas.
NOTA_DA_ANULADA = re.compile(r"\*Quest[ãa]o anulada[^.]*\.", re.IGNORECASE)

# Palavras que ficam em minuscula no nome da materia.
MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em"}


def preparar(texto: str) -> str:
    """O texto do caderno sem TAB, sem numero de pagina e sem a nota da anulada."""
    texto = texto.replace("\t", " ")
    texto = PADRAO_PAGINA.sub("", texto)
    return NOTA_DA_ANULADA.sub("", texto)


def nome_da_materia(titulo: str) -> str:
    """"NOCOES DE DIREITO PENAL" -> "Noções de Direito Penal": o mesmo nome,
    escrito como o resto do acervo; o `config/taxonomia.yml` liga ao edital."""
    palavras = " ".join(titulo.split()).lower().split(" ")
    return " ".join(p if (i and p in MINUSCULAS) else p[:1].upper() + p[1:]
                    for i, p in enumerate(palavras))


def _rodadas(texto: str) -> list[list[re.Match]]:
    """As alternativas agrupadas de a) ate e): cada rodada completa e uma questao."""
    rodadas: list[list[re.Match]] = []
    atual: list[re.Match] = []
    for marca in PADRAO_ALTERNATIVA.finditer(texto):
        letra = marca.group(2)
        esperada = LETRAS[len(atual)] if len(atual) < len(LETRAS) else None
        if letra == "a":
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


def dividir_em_questoes(texto: str) -> list[Questao]:
    """As questoes objetivas do caderno, com materia, resposta e anulada."""
    texto = preparar(texto)
    rodadas = _rodadas(texto)
    marcadores = list(PADRAO_QUESTAO.finditer(texto))
    titulos = list(PADRAO_TITULO.finditer(texto))

    questoes: list[Questao] = []
    fim_anterior = 0
    for indice, rodada in enumerate(rodadas):
        inicio_das_alternativas = rodada[0].start()
        antes = [m for m in marcadores if fim_anterior <= m.start() < inicio_das_alternativas]
        fim_anterior = rodada[-1].end()
        if not antes:
            continue
        marcador = antes[-1]

        # A ultima alternativa acaba na questao seguinte ou no titulo seguinte.
        limite = (rodadas[indice + 1][0].start() if indice + 1 < len(rodadas)
                  else len(texto))
        depois = [m.start() for m in marcadores + titulos
                  if rodada[-1].end() <= m.start() < limite]
        fim_da_ultima = min(depois) if depois else limite

        alternativas, resposta = {}, None
        for posicao, marca in enumerate(rodada):
            ate = rodada[posicao + 1].start() if posicao + 1 < len(rodada) else fim_da_ultima
            conteudo = _limpar(texto[marca.end():ate])
            if conteudo:
                alternativas[marca.group(2)] = conteudo
            if marca.group(1) == MARCA_DA_CERTA:
                resposta = marca.group(2)

        enunciado = _limpar(texto[marcador.end():inicio_das_alternativas])
        if not enunciado or len(alternativas) < 2:
            continue
        titulo = next((t for t in reversed(titulos) if t.start() < marcador.start()), None)
        anulada = marcador.group(1) == "*"
        questoes.append(Questao(
            numero=int(marcador.group(2)), enunciado=enunciado,
            alternativas=alternativas,
            # A anulada nao tem resposta: a banca desfez a pergunta.
            resposta=None if anulada else resposta,
            materia=nome_da_materia(titulo.group(1)) if titulo else None,
            anulada=anulada))

    melhores: dict[int, Questao] = {}
    for questao in questoes:
        anterior = melhores.get(questao.numero)
        if anterior is None or len(questao.enunciado) > len(anterior.enunciado):
            melhores[questao.numero] = questao
    return [melhores[n] for n in sorted(melhores)]


def ler_prova(caminho: Path) -> list[Questao]:
    """Le um caderno do NC-UFPR inteiro."""
    return dividir_em_questoes(extrair_texto(caminho))
