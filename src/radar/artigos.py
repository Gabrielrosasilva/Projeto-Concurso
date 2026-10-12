"""O artigo que uma fonte cita e os artigos que um tema cobre (decisao 161).

O resumo enxuto junta num bloco as frases que citam SO um artigo ("CP, art.
15" e "CP, art. 15, parágrafo único" sao o mesmo), e a traducao de cada artigo
so entra se ele e do tema. As duas perguntas sao de texto: "que artigo esta
fonte cita?" e "que artigos este titulo e este 'ler exatamente' dizem?". Puro:
so texto, sem banco.

O texto e lido normalizado (sem acento e sem caixa, `regioes.normalizar`), e
a lei e reconhecida pelo nome, por palavra inteira - o mesmo casamento do
config/alvo.yml (`alvo.palavra_inteira`). A lei de cada citacao, nesta ordem:

  1. a que vem logo depois ("arts. 83 a 90 do CP", "arts. 1º a 3º da DUDH");
  2. a ultima nomeada antes ("LEP, arts. 28 a 37", "CF, ...: art. 1º, III");
  3. a da materia (`incidencia.LEI_DA_MATERIA`), quando o texto nao diz.

Lei que nao esta em `LEIS` nao e reconhecida, e nada e contado por ela: uma
citacao que nao se le fica de fora, e nao aproximada.
"""
import re
from dataclasses import dataclass

from radar.alvo import palavra_inteira
from radar.incidencia import LEI_DA_MATERIA
from radar.regioes import normalizar


@dataclass(frozen=True)
class Lei:
    """Uma lei como o resumo a cita: a sigla da fonte ("CP"), a unidade em
    que ela se divide e os nomes com que o texto a escreve (sem acento)."""

    sigla: str
    unidade: str          # "art", "regra" ou "§"
    nomes: tuple


#: As leis que o resumo e a traducao citam, com a sigla de cada fonte. As
#: Regras de Mandela se dividem em regras (decisao 76) e a Declaracao de Viena
#: em paragrafos (decisao 122): "§ 5" e o dispositivo, e "art. 5" seria citar
#: errado. O "§" de uma lei de artigos e paragrafo DO artigo, e nao conta.
LEIS = (
    Lei("CP", "art", ("cp", "codigo penal")),
    Lei("CPP", "art", ("cpp", "codigo de processo penal")),
    Lei("CF", "art", ("cf", "constituicao federal", "constituicao")),
    Lei("LEP", "art", ("lep", "lei de execucao penal", "7.210")),
    Lei("Convenção Americana", "art", ("convencao americana", "pacto de san jose")),
    Lei("DUDH", "art", ("dudh", "declaracao universal dos direitos humanos",
                        "declaracao universal")),
    Lei("Protocolo de San Salvador", "art", ("protocolo de san salvador",)),
    Lei("Regras de Mandela", "regra", ("regras de mandela", "mandela")),
    Lei("Declaração de Viena (1993)", "§", ("declaracao e programa de acao de viena",
                                           "declaracao de viena", "viena")),
)
_POR_SIGLA = {lei.sigla: lei for lei in LEIS}


@dataclass(frozen=True)
class Artigo:
    """Um artigo (ou regra, ou paragrafo, conforme a lei): "CP, art. 15"."""

    lei: str
    numero: int
    sufixo: str = ""      # o "A" do "art. 9º-A"

    @property
    def posicao(self) -> tuple:
        return (self.numero, self.sufixo)

    @property
    def rotulo(self) -> str:
        return f"{self.lei}, {_UNIDADE_ESCRITA[_unidade_da(self.lei)][0]} {self.numero_escrito}"

    @property
    def numero_escrito(self) -> str:
        sufixo = f"-{self.sufixo}" if self.sufixo else ""
        # O ordinal ate o nono, como a lei escreve: "art. 9º-A", "art. 10".
        # A regra de Mandela e o paragrafo de Viena nao levam.
        ordinal = "º" if self.numero < 10 and _unidade_da(self.lei) == "art" else ""
        return f"{self.numero}{ordinal}{sufixo}"


#: Como cada unidade se escreve: no singular e no plural.
_UNIDADE_ESCRITA = {"art": ("art.", "arts."), "regra": ("regra", "regras"), "§": ("§", "§§")}


def _unidade_da(sigla: str) -> str:
    return _POR_SIGLA[sigla].unidade if sigla in _POR_SIGLA else "art"


@dataclass(frozen=True)
class Faixa:
    """Os artigos de uma citacao: "arts. 14 a 21" vai do (14, "") ao (21, "")
    e contem o "19"; "art. 15" e uma faixa de um artigo so."""

    lei: str
    inicio: tuple
    fim: tuple

    def contem(self, artigo: Artigo) -> bool:
        return artigo.lei == self.lei and self.inicio <= artigo.posicao <= self.fim

    @property
    def unico(self) -> Artigo | None:
        return Artigo(self.lei, *self.inicio) if self.inicio == self.fim else None

    @property
    def rotulo(self) -> str:
        """ "CP, art. 15" ou "CP, arts. 14 a 21"."""
        if self.unico is not None:
            return self.unico.rotulo
        primeiro, ultimo = Artigo(self.lei, *self.inicio), Artigo(self.lei, *self.fim)
        plural = _UNIDADE_ESCRITA[_unidade_da(self.lei)][1]
        return f"{self.lei}, {plural} {primeiro.numero_escrito} a {ultimo.numero_escrito}"


# A unidade e o numero, no texto normalizado: "art. 15", "arts. 14 a 21",
# "artigo 112", "regras 36 e 37", "§ 5". O "º" vira "o" na normalizacao.
_UNIDADE = re.compile(r"\b(arts?\.|artigos?\b|regras?\b)\s*|(§§?)\s*")
_NUMERO = re.compile(r"(\d+)\s*[o°]?(?:\s*-\s*([a-z])\b)?")
_SEPARADOR = re.compile(r"\s*(,|\be\b|\ba\b|\bate\b)\s*")
# Depois da lista: "do CP", "da DUDH", com um parentese no meio se houver.
_DEPOIS = re.compile(r"\s*(?:\([^)]*\)\s*)?d[aoe]s?\s+")


def _unidade(token: str) -> tuple[str, bool]:
    """("art" | "regra" | "§", plural?)"""
    if token.startswith("§"):
        return "§", token == "§§"
    if token.startswith("regra"):
        return "regra", token == "regras"
    return "art", token.startswith("arts") or token == "artigos"


def _leis_nomeadas(texto: str) -> list[tuple[int, int, str]]:
    """[(inicio, fim, sigla)] de cada lei nomeada no texto normalizado."""
    achadas = []
    for lei in LEIS:
        for nome in lei.nomes:
            for m in palavra_inteira(nome).finditer(texto):
                achadas.append((m.start(), m.end(), lei.sigla))
    return sorted(achadas)


def _lista(texto: str, inicio: int, plural: bool) -> tuple[list, int]:
    """Os numeros depois da unidade, e onde a lista acaba. No singular, so o
    primeiro ("art. 5º, §§ 1º a 4º" e o art. 5º); no plural, a lista com a
    faixa ("arts. 1º, 2º e 33 a 69")."""
    m = _NUMERO.match(texto, inicio)
    if m is None:
        return [], inicio
    numeros = [((int(m.group(1)), (m.group(2) or "").upper()),)]
    fim = m.end()
    while plural:
        sep = _SEPARADOR.match(texto, fim)
        if sep is None:
            break
        seguinte = _NUMERO.match(texto, sep.end())
        if seguinte is None:
            break
        artigo = (int(seguinte.group(1)), (seguinte.group(2) or "").upper())
        if sep.group(1) in ("a", "ate"):
            numeros[-1] = (numeros[-1][0], artigo)
        else:
            numeros.append((artigo,))
        fim = seguinte.end()
    return numeros, fim


def citados(texto: str | None, lei_padrao: str | None = None) -> list[Faixa]:
    """As faixas de artigos que o texto cita, cada uma com a sua lei.

    "CP, art. 18, I e II" -> [CP 18]; "LEP, arts. 131 e 132" -> [LEP 131,
    LEP 132]; "Regras de Mandela, regra 12.1" -> [Mandela 12]; "2019-q53",
    "Súmula Vinculante 25" e "doutrina (...)" -> [] (nao sao artigo).
    """
    normal = normalizar(texto or "")
    nomeadas = _leis_nomeadas(normal)
    saida = []
    for m in _UNIDADE.finditer(normal):
        unidade, plural = _unidade(m.group(1) or m.group(2))
        numeros, fim = _lista(normal, m.end(), plural)
        if not numeros:
            continue
        depois = _DEPOIS.match(normal, fim)
        lei = None
        if depois is not None:
            lei = next((s for i, _, s in nomeadas if i == depois.end()), None)
        if lei is None:
            antes = [s for i, f, s in nomeadas if f <= m.start()]
            lei = antes[-1] if antes else lei_padrao
        if lei not in _POR_SIGLA or _POR_SIGLA[lei].unidade != unidade:
            continue
        for faixa in numeros:
            saida.append(Faixa(lei, faixa[0], faixa[-1]))
    return saida


def unico(faixas) -> Artigo | None:
    """O artigo, quando todas as faixas citam o MESMO e so ele; senao None."""
    artigos = {f.unico for f in faixas}
    if len(artigos) != 1:
        return None
    (artigo,) = artigos
    return artigo


def da_fonte(fonte: str | None) -> Artigo | None:
    """O artigo que uma fonte cita, se cita um so: "CP, art. 15, I" -> CP 15."""
    return unico(citados(fonte))


def do_tema(titulo: str | None, ler_exatamente: str | None,
            materia: str | None) -> list[Faixa]:
    """Os artigos que o tema cobre, pelo titulo e pelo "ler exatamente" da
    ficha (o que o pedido de 12/10 manda). Sem lei nomeada, vale a da
    materia."""
    padrao = LEI_DA_MATERIA.get(materia or "")
    return citados(titulo, padrao) + citados(ler_exatamente, padrao)


def do_tema_contem(faixas: list[Faixa], artigo: Artigo) -> bool:
    return any(f.contem(artigo) for f in faixas)
