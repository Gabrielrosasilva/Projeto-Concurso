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


def _grupos_de_sinonimo(sinonimos) -> dict[str, set[str]]:
    """Cada sinonimo com as palavras que ele tem. Sinonimo vazio nao entra."""
    grupos = {}
    for termo in sinonimos or []:
        palavras = palavras_do_cargo(str(termo))
        if palavras:
            grupos[str(termo)] = palavras
    return grupos


def _sinonimo_que_casa(palavras: set[str], grupos: dict[str, set[str]]):
    """O sinonimo INTEIRO que cabe dentro deste cargo, se algum.

    Inteiro de proposito, e esta e a diferenca que faz a regra funcionar:
    "Agente Penitenciario (masculino)" tem as duas palavras de "agente
    penitenciario" e e a mesma profissao, enquanto "Agente Administrativo" tem
    so "agente" e nao e. Exigir o sinonimo completo e o que separa os dois -
    aceitar palavra solta encheria a lista de todo "Agente" do acervo.

    Entre dois sinonimos que casam, vale o mais especifico (o de mais
    palavras): ele e o que diz mais sobre a semelhanca.
    """
    casaram = [
        (termo, grupo) for termo, grupo in grupos.items() if grupo <= palavras
    ]
    if not casaram:
        return None, set()
    return max(casaram, key=lambda par: len(par[1]))


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
    grupos: dict[str, set[str]] | None = None,
) -> Parecida:
    palavras = palavras_do_cargo(candidata.cargo)
    comuns = palavras_pedidas & palavras
    sinonimo, grupo = _sinonimo_que_casa(palavras, grupos or {})

    if comuns:
        candidata.motivos.append(
            f"{len(comuns)} palavra(s) em comum no cargo: " + ", ".join(sorted(comuns))
        )
        candidata.exata = palavras == palavras_pedidas

    if sinonimo:
        candidata.motivos.append(f'"{sinonimo}" e o mesmo cargo com outro nome')
        candidata.exata = candidata.exata or palavras == grupo

    # O maior dos dois, e nao a soma: quando o cargo pedido e o sinonimo
    # dividem palavra - "policia penal" e "policial penal" dividem "penal" -
    # somar contaria a mesma semelhanca duas vezes.
    peso = max(len(comuns), len(grupo))
    if peso:
        candidata.pontos += PESO_DA_PALAVRA * peso

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
    sinonimos: list[str] | None = None,
) -> list[Parecida]:
    """As provas do acervo, da mais parecida para a menos.

    Fica de fora o que nao se parece em nada: prova de Psicologo nao ajuda quem
    quer Guarda Municipal so por existir. Uma lista curta e honesta vale mais
    que 134 linhas ordenadas por acaso.

    `sinonimos` sao os outros nomes do mesmo cargo, e quem os conhece e
    `config/alvo.yml`. Eles existem por um caso real: as duas provas que eu
    tenho do meu concurso estao catalogadas como "Agente Penitenciario", o
    nome de 2013 e 2019, e procurar por "Policial Penal" - o nome de hoje -
    nao devolvia nenhuma delas. Os dois nomes nao dividem UMA palavra sequer,
    entao nenhuma regra de semelhanca de texto ia salvar: quem sabe que sao o
    mesmo cargo sou eu, e esta escrito no YAML.
    """
    pedidas = palavras_do_cargo(cargo)
    grupos = _grupos_de_sinonimo(sinonimos)
    pontuadas = [
        _pontuar(c, pedidas, banca, municipio, ano_recente, grupos)
        for c in candidatas
    ]

    # So entra quem divide ao menos uma palavra com o cargo pedido, ou quem
    # cabe inteiro num sinonimo. Banca e municipio sao DESEMPATE, e nunca
    # motivo de entrada: sem esta regra, procurar "Policia Penal" devolvia
    # Merendeira e Professor de Ensino Religioso, so por serem da mesma banca.
    # Oito linhas de ruido sao piores que uma tela que admite nao ter nada.
    parecidas = [
        c for c in pontuadas
        if (pedidas & palavras_do_cargo(c.cargo))
        or _sinonimo_que_casa(palavras_do_cargo(c.cargo), grupos)[0]
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
