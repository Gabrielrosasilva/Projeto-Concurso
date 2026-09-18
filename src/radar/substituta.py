"""Quando nao ha prova do cargo que eu quero, qual e a mais parecida.

O problema e concreto: os cargos que eu mais quero - Guarda Municipal, Policia
Penal - **nao tem uma prova sequer no acervo**. Sao 134 cargos catalogados e
nenhum deles e esse. Esperar a prova aparecer nao e plano.

O que este arquivo faz e ordenar o que existe pela semelhanca com o que eu
quero, e dizer em cima de que essa semelhanca foi medida. O que ele **nao**
faz e fingir equivalencia: "Guarda Patrimonial" divide uma palavra com "Guarda
Municipal" e e outra profissao. Por isso a pontuacao vem sempre acompanhada do
motivo, e o motivo diz "1 palavra em comum", nao "cargo equivalente".

A conclusao mais util costuma ser a que menos parece resposta: para cargo que
nao existe no acervo, o que serve de verdade sao as **materias que caem em
qualquer concurso** da mesma banca. Elas valem 20 das 30 questoes de uma prova
da IESES, e o radar as trata assim no simulado.
"""
import re
import unicodedata
from dataclasses import dataclass, field

# Palavras que aparecem em nome de cargo sem dizer o que ele e. Sem tirar
# estas, "Agente Administrativo" e "Agente de Servicos Operacionais" pareceriam
# parentes por causa de "Agente" e "de".
PALAVRAS_VAZIAS = frozenset("""
de da do das dos e em a o as os para com sem por
i ii iii iv v 30h 40h 20h
""".split())

# Quanto vale cada coincidencia. Sao numeros escolhidos a mao, e a unica coisa
# que importa neles e a ORDEM: o cargo pesa mais que a banca, que pesa mais que
# o lugar. Prova de outro cargo da minha banca ensina mais que prova do meu
# cargo numa banca que nao vai me aplicar prova.
PESO_DA_PALAVRA = 10
PESO_DA_BANCA = 6
PESO_DO_MUNICIPIO = 2
PESO_DO_ANO = 1


def _sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def palavras_do_cargo(cargo: str | None) -> set[str]:
    """As palavras que dizem o que o cargo e."""
    cru = _sem_acento(cargo or "").lower()
    return {
        palavra for palavra in re.findall(r"[a-z0-9]+", cru)
        if palavra not in PALAVRAS_VAZIAS and len(palavra) > 2
    }


@dataclass
class Parecida:
    """Uma prova do acervo, e o quanto ela se parece com o que eu procuro."""

    cargo: str
    banca: str | None
    municipio: str | None
    ano: int | None
    questoes: int
    pontos: int = 0
    motivos: list[str] = field(default_factory=list)
    exata: bool = False

    @property
    def motivo(self) -> str:
        return "; ".join(self.motivos)


def _pontuar(
    candidata: Parecida,
    palavras_pedidas: set[str],
    banca: str | None,
    municipio: str | None,
    ano_recente: int | None,
) -> Parecida:
    palavras = palavras_do_cargo(candidata.cargo)
    comuns = palavras_pedidas & palavras

    if comuns:
        candidata.pontos += PESO_DA_PALAVRA * len(comuns)
        candidata.motivos.append(
            f"{len(comuns)} palavra(s) em comum no cargo: " + ", ".join(sorted(comuns))
        )
        candidata.exata = palavras == palavras_pedidas

    if banca and candidata.banca and _sem_acento(banca).lower() in _sem_acento(
        candidata.banca
    ).lower():
        candidata.pontos += PESO_DA_BANCA
        candidata.motivos.append(f"mesma banca ({candidata.banca})")

    if municipio and candidata.municipio and _sem_acento(municipio).lower() == _sem_acento(
        candidata.municipio
    ).lower():
        candidata.pontos += PESO_DO_MUNICIPIO
        candidata.motivos.append(f"mesmo municipio ({candidata.municipio})")

    if ano_recente and candidata.ano and candidata.ano >= ano_recente:
        candidata.pontos += PESO_DO_ANO
        candidata.motivos.append(f"prova recente ({candidata.ano})")

    return candidata


def ordenar(
    candidatas: list[Parecida],
    cargo: str,
    banca: str | None = None,
    municipio: str | None = None,
    ano_recente: int | None = None,
) -> list[Parecida]:
    """As provas do acervo, da mais parecida para a menos.

    Fica de fora o que nao se parece em nada: prova de Psicologo nao ajuda quem
    quer Guarda Municipal so por existir. Uma lista curta e honesta vale mais
    que 134 linhas ordenadas por acaso.
    """
    pedidas = palavras_do_cargo(cargo)
    pontuadas = [
        _pontuar(c, pedidas, banca, municipio, ano_recente) for c in candidatas
    ]

    # So entra quem divide ao menos uma palavra com o cargo pedido. Banca e
    # municipio sao DESEMPATE, e nunca motivo de entrada: sem esta regra,
    # procurar "Policia Penal" devolvia Merendeira e Professor de Ensino
    # Religioso, so por serem da mesma banca. Oito linhas de ruido sao piores
    # que uma tela que admite nao ter nada.
    parecidas = [
        c for c in pontuadas
        if pedidas & palavras_do_cargo(c.cargo)
    ]

    # O desempate e pelo tamanho: entre duas provas igualmente parecidas, a que
    # tem mais questoes rende mais estudo.
    return sorted(parecidas, key=lambda c: (-c.pontos, -c.questoes))


def explicar_ausencia(cargo: str, universais: list[str]) -> str:
    """O que dizer quando nao ha nada parecido - que e o caso mais comum aqui.

    E a resposta honesta: nao existe prova desse cargo no acervo, e o que serve
    de verdade sao as materias que caem em qualquer concurso.
    """
    materias = ", ".join(universais[:4]) if universais else "as materias gerais"
    return (
        f"Nenhuma prova de {cargo} no acervo, e nenhuma parecida o bastante "
        f"para valer a indicacao. O que serve para esse cargo sao as materias "
        f"que caem em qualquer concurso ({materias}), com as provas da mesma "
        f"banca."
    )
