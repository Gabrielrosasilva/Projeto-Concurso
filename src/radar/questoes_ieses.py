"""Separa o caderno da IESES em questoes, com materia e gabarito.

Tres diferencas em relacao ao caderno da FEPESE, e cada uma muda o codigo:

  1. **quatro alternativas**, de a) a d), e nao cinco;
  2. **o gabarito e um PDF a parte** ("1 A", "2B", "3C"...), e nao uma marca
     dentro do proprio caderno;
  3. **a materia nao aparece no caderno**. Ela vem do edital, por faixa de
     numeracao - veja `edital_ieses`.

O que e igual, e por isso reaproveitado de `questoes`: a leitura parte das
ALTERNATIVAS e nao dos numeros, porque o enunciado pode ter lista numerada
dentro; a linha que se repete em toda pagina e mobilia e sai do texto; e a
corrida de espacos vira lacuna.
"""
import logging
import re
from pathlib import Path

from radar.questoes import (
    Questao,
    _limpar,
    cortar_mobilia,
    extrair_texto,
    limpar_mobilia,
    marcar_lacunas,
)

log = logging.getLogger(__name__)

# "a) texto da alternativa". A IESES usa parentese, e so quatro letras.
LETRAS = "abcd"
PADRAO_ALTERNATIVA = re.compile(rf"(?m)^\s*([{LETRAS}])\)\s*", re.IGNORECASE)

# "12. Enunciado da questao" - o numero que abre a questao.
PADRAO_QUESTAO = re.compile(r"(?m)^\s*(\d{1,2})\.\s")

# No gabarito: "1 A", "2B", "10 C". Numero e letra, com ou sem espaco.
PADRAO_RESPOSTA = re.compile(r"(?m)^\s*(\d{1,2})\s*([A-E])\s*$")

# "Cargo: 1016 - Assistente Social", no alto do caderno. Quando dois cargos
# dividem o mesmo caderno, vem "Cargo: 1020/1033 - Auxiliar de Ensino": vale o
# primeiro codigo, porque os dois estao no mesmo nivel e fazem a mesma prova.
PADRAO_CARGO = re.compile(
    r"(?im)^\s*cargo:\s*(\d{3,5})(?:/\d{3,5})*\s*-\s*(.+?)\s*$"
)


def ler_gabarito(caminho: Path) -> dict[int, str]:
    """{numero da questao: letra correta}, do PDF de gabarito.

    O arquivo e uma folha so, com uma linha por questao. A letra vem em
    maiuscula la e minuscula aqui, para bater com o resto do banco.
    """
    texto = extrair_texto(caminho)
    return {
        int(numero): letra.lower()
        for numero, letra in PADRAO_RESPOSTA.findall(texto)
    }


def codigo_e_cargo(texto: str) -> tuple[str | None, str | None]:
    """O codigo e o nome do cargo, do cabecalho do caderno.

    O codigo e o que liga o caderno ao edital: e por ele que se descobre o
    nivel, e do nivel sai a materia de cada questao.
    """
    achado = PADRAO_CARGO.search(texto)
    if not achado:
        return None, None
    return achado.group(1), " ".join(achado.group(2).split())


def _blocos_de_alternativas(texto: str) -> list[list[re.Match]]:
    """Agrupa as alternativas em rodadas de a) ate d).

    Mesma ideia usada no caderno da FEPESE: cada rodada completa fecha uma
    questao. Partir do numero quebraria no enunciado que tem lista dentro
    ("I. ...", "1. ...").
    """
    marcas = list(PADRAO_ALTERNATIVA.finditer(texto))
    rodadas: list[list[re.Match]] = []
    atual: list[re.Match] = []

    for marca in marcas:
        letra = marca.group(1).lower()
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
            # letra fora de ordem: a rodada anterior se perdeu no meio
            if len(atual) >= 2:
                rodadas.append(atual)
            atual = []

    if len(atual) >= 2:
        rodadas.append(atual)
    return rodadas


def _ler_alternativas(rodada: list[re.Match], texto: str, fim: int) -> dict[str, str]:
    alternativas: dict[str, str] = {}
    for indice, marca in enumerate(rodada):
        limite = rodada[indice + 1].start() if indice + 1 < len(rodada) else fim
        conteudo = cortar_mobilia(_limpar(texto[marca.end():limite]))
        if conteudo:
            alternativas[marca.group(1).lower()] = conteudo
    return alternativas


def dividir_em_questoes(texto: str, materias: dict[int, str] | None = None,
                        gabarito: dict[int, str] | None = None) -> list[Questao]:
    """As questoes do caderno, com materia e resposta quando se sabe."""
    texto = limpar_mobilia(texto)
    materias = materias or {}
    gabarito = gabarito or {}

    rodadas = _blocos_de_alternativas(texto)
    questoes: list[Questao] = []
    fim_anterior = 0

    for indice, rodada in enumerate(rodadas):
        inicio_alternativas = rodada[0].start()
        fim_rodada = (rodadas[indice + 1][0].start()
                      if indice + 1 < len(rodadas) else len(texto))

        regiao = texto[fim_anterior:inicio_alternativas]
        marcador = PADRAO_QUESTAO.search(regiao)
        fim_anterior = rodada[-1].end()

        if not marcador:
            continue

        numero = int(marcador.group(1))
        enunciado = _limpar(marcar_lacunas(
            re.sub(r"^\s*\d{1,2}\.\s*", "", regiao[marcador.start():])
        ))
        alternativas = _ler_alternativas(rodada, texto, fim_rodada)
        if not enunciado or len(alternativas) < 2:
            continue

        questoes.append(Questao(
            numero=numero,
            enunciado=enunciado,
            alternativas=alternativas,
            resposta=gabarito.get(numero),
            materia=materias.get(numero),
        ))

    # Numero repetido fica com o bloco de enunciado mais completo.
    melhores: dict[int, Questao] = {}
    for questao in questoes:
        anterior = melhores.get(questao.numero)
        if anterior is None or len(questao.enunciado) > len(anterior.enunciado):
            melhores[questao.numero] = questao

    return [melhores[numero] for numero in sorted(melhores)]


def ler_prova(
    caminho: Path,
    gabarito: dict[int, str] | None = None,
    materias: dict[int, str] | None = None,
) -> list[Questao]:
    """Le um caderno da IESES inteiro."""
    return dividir_em_questoes(extrair_texto(caminho), materias, gabarito)
