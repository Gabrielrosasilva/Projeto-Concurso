"""O nivel da questao gerada: facil, media ou dificil, num lugar so (decisao 151).

O pedido, a importacao, a classificacao das antigas, o sorteio e a tela leem
daqui. Constante, e nao `config/*.yml`, de proposito: as tres chaves sao um
contrato com a coluna `questoes_geradas.nivel`, com o JSON versionado e com os
seletores - um YAML daria a entender que da para criar um quarto nivel, e
nao da.

O nivel e o que a IA DECLARA, com a procedencia dela, como o resto da gerada
(🟣). Nunca vira numero que mede: a gerada treina, e o acerto por nivel e
mais um numero a parte, nunca somado ao das reais.

Modulo puro: nao abre banco.
"""
from dataclasses import dataclass

from radar.complementar import normalizar as _sem_acento


@dataclass(frozen=True)
class Nivel:
    chave: str
    rotulo: str
    #: O criterio que o pedido manda a IA seguir e justificar em uma linha.
    criterio: str


#: Na ordem em que aparecem em todo lugar: seletor, saida, tabela.
NIVEIS = {
    "facil": Nivel("facil", "Fácil",
                   "a letra de um artigo só; as erradas são claramente erradas."),
    "media": Nivel("media", "Média",
                   "um caso simples, ou a letra da lei com UMA troca sutil "
                   "(prazo, número, \"permitido\" por \"vedado\")."),
    "dificil": Nivel("dificil", "Difícil",
                     "junta dois dispositivos ou uma exceção (\"salvo\", "
                     "\"exceto\"), um caso em que um detalhe muda a resposta, e "
                     "as cinco alternativas plausíveis."),
}

#: Em Portugues e Raciocinio Logico nao ha artigo: vale a regra.
CRITERIO_FORA_DO_DIREITO = ("Em Português e Raciocínio Lógico, o mesmo espírito, "
                            "pela regra em vez do artigo.")

#: Os tres niveis juntos. E o padrao de todo seletor e do `--nivel`.
MISTURADA = "misturada"
ROTULO_DA_MISTURADA = "Misturada"

#: O que o selo diz quando a gerada ainda nao tem nivel (as antigas, ate a
#: classificacao; as da API).
SEM_NIVEL = "sem nível"


def normalizar(texto: str | None) -> str | None:
    """A chave do nivel, ou None se o texto nao e nenhum dos tres.

    Caixa e acento nao contam ("Difícil" e `dificil`); outra palavra nao vira
    nivel nenhum ("medio", "muito dificil") - aproximar seria inventar o que
    a IA nao declarou.
    """
    chave = _sem_acento(texto)
    return chave if chave in NIVEIS else None


def rotulo(chave: str | None) -> str:
    """"Difícil", "Misturada" ou "sem nível"."""
    if chave == MISTURADA:
        return ROTULO_DA_MISTURADA
    nivel = NIVEIS.get(chave or "")
    return nivel.rotulo if nivel else SEM_NIVEL


def rotulo_do_selo(chave: str | None) -> str:
    """O texto do selo 🟣 na questao: "Gerada por IA · Difícil"."""
    return f"Gerada por IA · {rotulo(chave)}"
