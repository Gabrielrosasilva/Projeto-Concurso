"""O gabarito DEFINITIVO, e as questoes que a banca anulou.

Por que isto existe: o caderno de prova da FEPESE traz a resposta certa
marcada dentro do proprio PDF, e e de la que o `radar questoes` tira o
gabarito. So que esse caderno e publicado no dia seguinte a prova, **antes dos
recursos** - ele carrega o gabarito PROVISORIO. Depois dos recursos a banca
publica o definitivo, com duas coisas que mudam tudo:

  * questoes **anuladas**, que deixam de ter resposta certa;
  * gabaritos **trocados**, em que a letra do caderno esta errada.

No concurso de 2019 da Policia Penal SC foram 5 anuladas e 4 trocadas, em 100
questoes. Treinar pelo caderno significava marcar como erro 4 respostas certas
minhas, e tentar acertar 5 questoes que nao tem resposta.

O PDF do definitivo e uma grade: uma linha com os numeros das questoes, a
linha de baixo com a letra de cada uma, e `x` onde a questao foi anulada.

    1 2 3 4 5 6 7 8 9 10 11 12 ...
    c d b a c a e b b e  x  b  ...

Este arquivo so LE a grade. Quem decide a qual caderno ela pertence e o
`servico`, e ele so aplica depois de conferir que o cargo e o numero de
questoes batem - grade de outro cargo aplicada por engano seria pior do que
ficar com o provisorio.
"""
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

#: O que a banca escreve no lugar da letra quando anula a questao.
MARCA_DE_ANULADA = "x"

# Uma linha de grade: so numeros separados por espaco, pelo menos cinco deles.
# Menos que isso e data, numero de pagina ou item de edital.
LINHA_DE_NUMEROS = re.compile(r"^\s*\d{1,3}(?:\s+\d{1,3}){4,}\s*$")

# A linha das respostas: so letras de a a e, ou o x da anulada.
LINHA_DE_LETRAS = re.compile(r"^\s*[a-ex](?:\s+[a-ex]){4,}\s*$", re.IGNORECASE)


def _normalizar(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in normal if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


@dataclass
class Grade:
    """O gabarito definitivo de UM caderno.

    `respostas` tem a letra de cada questao; a anulada entra em `anuladas` e
    NAO entra em `respostas` - ela nao tem resposta certa, e guardar uma seria
    inventar.
    """

    cargo: str | None = None
    sigla: str | None = None
    respostas: dict[int, str] = field(default_factory=dict)
    anuladas: set[int] = field(default_factory=set)

    @property
    def total(self) -> int:
        """Quantas questoes a grade cobre, anuladas inclusive."""
        return len(self.respostas) + len(self.anuladas)

    def __bool__(self) -> bool:
        return bool(self.total)


def _cargo_da_grade(linhas: list[str], ate: int) -> tuple[str | None, str | None]:
    """(cargo, sigla) pela ultima linha de texto antes da grade.

    O PDF escreve "AP • Agente Penitenciário" - a sigla e a mesma do nome do
    caderno (AP.pdf), e e ela que amarra a grade ao caderno certo quando o
    concurso tem varios cargos.
    """
    for linha in reversed(linhas[:ate]):
        texto = linha.strip()
        # Linha de data ("01 de dezembro, das 13 às 18 h") nao nomeia cargo.
        if len(texto) < 4 or re.match(r"^\d", texto):
            continue
        achado = re.match(r"^([A-Z]{1,4}\d?)\s*[•·\-–]?\s+(\D.*)$", texto)
        if achado:
            return achado.group(2).strip(" •·-–"), achado.group(1)
        return texto.strip(" •·-–"), None
    return None, None


def ler_grades(texto: str) -> list[Grade]:
    """As grades de um PDF de gabarito definitivo, uma por cargo.

    Um PDF so costuma trazer varios cargos: o de 2013 tem "AP • Agente
    Penitenciário" e "AS • Agente de Segurança Socioeducativo", cada um com a
    sua numeracao de 1 a 70. Lendo tudo junto, as duas grades viravam uma de
    73 questoes que nao era de cargo nenhum.

    O que separa uma da outra e a numeracao recomecar no 1. Nunca chutar vale
    aqui como no resto: linha de numeros sem a linha de letras logo abaixo, ou
    com contagem diferente, e descartada inteira. Meia grade aplicada e pior
    do que nenhuma - ela trocaria a resposta de umas e deixaria as outras com
    a do provisorio, sem ninguem notar.
    """
    linhas = (texto or "").splitlines()
    grades: list[Grade] = []
    atual: Grade | None = None

    for indice, linha in enumerate(linhas[:-1]):
        if not LINHA_DE_NUMEROS.match(linha):
            continue
        seguinte = linhas[indice + 1]
        if not LINHA_DE_LETRAS.match(seguinte):
            continue

        numeros = [int(n) for n in linha.split()]
        letras = seguinte.split()
        if len(numeros) != len(letras):
            log.warning("grade com %d numeros e %d letras: descartada",
                        len(numeros), len(letras))
            continue

        # Numeracao de volta ao 1 e cargo novo, e nao continuacao.
        if atual is None or (numeros[0] == 1 and atual.total):
            atual = Grade()
            atual.cargo, atual.sigla = _cargo_da_grade(linhas, indice)
            grades.append(atual)

        for numero, letra in zip(numeros, letras):
            if letra.lower() == MARCA_DE_ANULADA:
                atual.anuladas.add(numero)
                atual.respostas.pop(numero, None)
            else:
                atual.respostas[numero] = letra.lower()

    return grades


@lru_cache(maxsize=32)
def ler_grades_do_pdf(caminho: Path) -> tuple[Grade, ...]:
    """As grades de um PDF, lidas uma vez so.

    O cache existe por causa do concurso com muitos cargos: o de Brusque tem
    17 cadernos, e sem ele o mesmo gabarito seria aberto 17 vezes para a
    conferencia de cargo dizer 16 vezes que nao era daquele.
    """
    from radar.questoes import extrair_texto

    try:
        return tuple(ler_grades(extrair_texto(caminho)))
    except Exception as erro:  # noqa: BLE001 - PDF ruim e rotina, nao acidente
        log.warning("nao li o gabarito %s (%s)", caminho.name, type(erro).__name__)
        return ()


def e_deste_caderno(grade: Grade, cargo: str | None, arquivo: str,
                    quantas: int) -> bool:
    """Esta grade e mesmo do caderno que estou lendo?

    Tres perguntas, e as tres precisam de sim - ou pelo menos de "nao ha como
    discordar". O concurso de 2019 publicou UM gabarito definitivo por cargo, e
    aplicar o do cargo errado trocaria 100 respostas de uma vez.

      * o numero de questoes bate;
      * a sigla da grade e o nome do arquivo do caderno (AP -> AP.pdf);
      * ou, sem sigla, o cargo da grade aparece no cargo do caderno.
    """
    if not grade or grade.total != quantas:
        return False

    nome = re.sub(r"\.pdf$", "", arquivo or "", flags=re.IGNORECASE)
    if grade.sigla and _normalizar(grade.sigla) == _normalizar(nome):
        return True

    if grade.cargo and cargo:
        return _normalizar(grade.cargo) in _normalizar(cargo)
    return False


def aplicar(questoes: list, grade: Grade) -> tuple[int, int]:
    """Poe a grade nas questoes lidas do caderno. (trocadas, anuladas).

    Trabalha sobre os objetos que o leitor de caderno devolveu, e nao sobre o
    banco: assim o gabarito definitivo vale tambem quando eu refaco a extracao
    do zero, em vez de ser um conserto que se perde na proxima leitura.
    """
    trocadas = anuladas = 0
    for questao in questoes:
        if questao.numero in grade.anuladas:
            questao.anulada = True
            questao.resposta = None
            anuladas += 1
            continue

        certa = grade.respostas.get(questao.numero)
        if not certa:
            continue

        # A grade manda nas duas pontas: ela nao so troca a letra errada como
        # DESmarca a anulacao. Sem isso, aplicar a retificacao depois do
        # definitivo deixaria anulada para sempre uma questao que voltou.
        questao.anulada = False
        if certa != questao.resposta:
            questao.resposta = certa
            trocadas += 1
    return trocadas, anuladas
