"""O quadro de materias do edital: quantas questoes de cada uma.

Isto e diferente do que `radar padrao` responde. O `padrao` conta o que a
banca JA cobrou, olhando as provas antigas. Aqui esta o que o edital PROMETE
cobrar - e os dois juntos e que dizem alguma coisa: onde eles batem, o peso e
regra; onde discordam, e sinal de que a prova mudou.

O quadro do edital de 2019 da Policia Penal SC e assim:

    9.7 A distribuicao das questoes da prova e o valor a elas
    correspondente acham-se no quadro abaixo:
     N° DE QUESTOES VALOR DA QUESTAO TOTAL
    Lingua Portuguesa 15 0,10 1,50
    Raciocinio Logico 10 0,10 1,00
    ...
    TOTAL 100  10,00

Regra deste arquivo, que e a do projeto inteiro: **nunca chutar**. Edital que
nao tem quadro, ou que tem um quadro que nao fecha a conta, devolve lista
vazia - e quem chama diz "nao sei ainda". Um peso inventado mandaria eu
estudar a materia errada por meses.
"""
import logging
import re
from dataclasses import dataclass

log = logging.getLogger(__name__)

# "Lingua Portuguesa 15 0,10 1,50" - nome, quantas questoes, quanto vale cada
# uma, e o total da materia. O nome nao pode ter digito: isso descarta a linha
# de cabecalho e qualquer numeracao de item que caia junto.
LINHA_DO_QUADRO = re.compile(
    r"^[ \t]*([^\d\n]{4,60}?)[ \t]+(\d{1,3})[ \t]+"
    r"(\d{1,2},\d{2})[ \t]+(\d{1,3},\d{2})[ \t]*$",
    re.MULTILINE,
)

# A linha que fecha o quadro. Ela tem o total de questoes e serve de conferencia:
# se a soma das materias nao bater com ela, o quadro foi lido errado.
LINHA_DO_TOTAL = re.compile(
    r"^[ \t]*TOTAL[ \t]+(\d{1,3})[ \t]", re.MULTILINE | re.IGNORECASE
)

# Onde o quadro comeca. Sem esta ancora, a busca varreria o edital inteiro e
# acharia qualquer tabela de numeros - cronograma, vagas por regiao, notas.
ABERTURA_DO_QUADRO = re.compile(
    r"(?i)distribui[cç][aã]o\s+das\s+quest[oõ]es", re.DOTALL
)

# Quanto texto olhar depois da ancora. O quadro de 2019 tem 11 linhas e cabe
# de sobra; passar disso comeca a pegar o item seguinte do edital.
JANELA_DO_QUADRO = 1500


@dataclass(frozen=True)
class MateriaDoEdital:
    """Uma linha do quadro de distribuicao de questoes."""

    nome: str
    questoes: int

    def peso(self, total: int) -> float:
        """Quanto esta materia vale da prova inteira, em porcento."""
        return (self.questoes / total * 100) if total else 0.0


def _arrumar_nome(bruto: str) -> str:
    """Tira espaco sobrando e arruma a caixa.

    O edital escreve "Direito constitucional" e "Direito penal" em caixa baixa
    no meio do quadro, e "Lingua Portuguesa" em caixa alta. Padronizar aqui
    evita a mesma materia aparecer duas vezes na tela por causa disso.
    """
    nome = re.sub(r"\s+", " ", bruto).strip(" .:-")
    # "de", "da", "do" ficam minusculos; o resto ganha maiuscula inicial. E o
    # jeito como o proprio edital escreve as materias que ele escreve direito.
    pequenas = {"de", "da", "do", "das", "dos", "e"}
    palavras = [
        p if p.lower() in pequenas and i else p[:1].upper() + p[1:].lower()
        for i, p in enumerate(nome.split())
    ]
    return " ".join(palavras)


def ler_quadro(texto: str) -> list[MateriaDoEdital]:
    """As materias do edital, na ordem em que ele as lista.

    Lista vazia quando nao da para afirmar: edital sem quadro, quadro que nao
    fecha a conta, ou menos de tres materias. Quem chama diz "nao sei ainda".
    """
    achado = ABERTURA_DO_QUADRO.search(texto or "")
    if not achado:
        return []

    trecho = texto[achado.end():achado.end() + JANELA_DO_QUADRO]

    materias = [
        MateriaDoEdital(nome=_arrumar_nome(nome), questoes=int(quantas))
        for nome, quantas, _valor, _total in LINHA_DO_QUADRO.findall(trecho)
    ]
    # "TOTAL 100 10,00" nao e materia; ele e a conferencia, logo abaixo.
    materias = [m for m in materias if m.nome.lower() != "total"]

    if len(materias) < 3:
        return []

    total_declarado = LINHA_DO_TOTAL.search(trecho)
    if total_declarado:
        somado = sum(m.questoes for m in materias)
        if somado != int(total_declarado.group(1)):
            # Ler metade do quadro e pior que nao ler: eu estudaria com pesos
            # errados sem nunca desconfiar.
            log.warning(
                "quadro do edital nao fecha: %d somados contra %s declarados",
                somado, total_declarado.group(1),
            )
            return []

    return materias


def total_de_questoes(materias: list[MateriaDoEdital]) -> int:
    return sum(m.questoes for m in materias)
