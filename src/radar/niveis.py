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
    #: "difíceis", para o "so havia N difíceis neste assunto".
    plural: str


#: Na ordem em que aparecem em todo lugar: seletor, saida, tabela.
NIVEIS = {
    "facil": Nivel("facil", "Fácil",
                   "a letra de um artigo só; as erradas são claramente erradas.",
                   "fáceis"),
    "media": Nivel("media", "Média",
                   "um caso simples, ou a letra da lei com UMA troca sutil "
                   "(prazo, número, \"permitido\" por \"vedado\").",
                   "médias"),
    "dificil": Nivel("dificil", "Difícil",
                     "junta dois dispositivos ou uma exceção (\"salvo\", "
                     "\"exceto\"), um caso em que um detalhe muda a resposta, e "
                     "as cinco alternativas plausíveis.",
                     "difíceis"),
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


#: O que o `--nivel` aceita: os tres e a misturada.
OPCOES = (MISTURADA, *NIVEIS)

#: A volta da reparticao: a media primeiro, porque e ela que leva a sobra.
_ORDEM_DA_VOLTA = ("media", "facil", "dificil")


def dividir(quantas: int, nivel: str = MISTURADA) -> dict[str, int]:
    """{facil, media, dificil: quantas} de um pedido.

    Misturada sao partes iguais, e o que sobra vai para a media: 10 da
    3/4/3, 11 da 3/5/3, 5 da 1/3/1. Um nivel so leva tudo.
    """
    quantas = max(int(quantas or 0), 0)
    if nivel != MISTURADA:
        if nivel not in NIVEIS:
            raise ValueError(f"nível {nivel!r} não existe: use {', '.join(OPCOES)}")
        return {chave: (quantas if chave == nivel else 0) for chave in NIVEIS}
    base, sobra = divmod(quantas, len(NIVEIS))
    return {chave: base + (sobra if chave == "media" else 0) for chave in NIVEIS}


def repartir(tamanhos: list[int], total: dict[str, int]) -> list[dict[str, int]]:
    """O total do lote dividido entre os pedidos dele, cada um com a sua
    parte de cada nivel.

    O lote e varios pedidos (as variacoes de 3 em 3, o do zero em blocos), e
    a mistura e do LOTE: a volta passa pelos niveis que ainda tem cota, a
    media primeiro, e cada pedido pega os proximos. Assim cada pedido sai
    misturado, e a soma bate com o total.
    """
    fila: list[str] = []
    resta = dict(total)
    while any(resta.values()):
        for chave in _ORDEM_DA_VOLTA:
            if resta.get(chave):
                fila.append(chave)
                resta[chave] -= 1
    saida, inicio = [], 0
    for tamanho in tamanhos:
        parte = fila[inicio:inicio + tamanho]
        inicio += tamanho
        saida.append({chave: parte.count(chave) for chave in NIVEIS})
    return saida


def descrever(contagem: dict[str, int]) -> str:
    """"3/4/3", na ordem facil/media/dificil."""
    return "/".join(str(contagem.get(chave, 0)) for chave in NIVEIS)


def instrucao(contagem: dict[str, int]) -> str:
    """O bloco que entra na instrucao do pedido: quantas de cada nivel, os
    criterios, e os dois campos que cada questao tem de declarar."""
    pedidas = [f"{n} {chave}" for chave, n in contagem.items() if n]
    if len(pedidas) > 1:
        quantas = ", ".join(pedidas[:-1]) + " e " + pedidas[-1]
    else:
        quantas = pedidas[0] if pedidas else "0"
    linhas = [
        "",
        "NIVEL - cada questao tem um nivel, e este pedido diz quantas de cada:",
        f"  escreva exatamente: {quantas}.",
        *[f"- {chave}: {nivel.criterio}" for chave, nivel in NIVEIS.items()],
        CRITERIO_FORA_DO_DIREITO,
        "Em cada questao, responda tambem:",
        '  "nivel": "facil", "media" ou "dificil" - o que a questao E, nao o que '
        "foi pedido;",
        '  "por_que_o_nivel": uma linha, pelo criterio acima.',
        "Se nao der para escrever um nivel sem sair do escopo, escreva menos dele:",
        "nao troque por outro.",
    ]
    return "\n".join(linhas)


def ler_da_resposta(item: dict) -> tuple[str | None, str | None, str | None]:
    """(nivel, por_que_o_nivel, motivo da recusa) de uma questao da resposta.

    Recusa sem nivel, nivel fora da lista e sem a justificativa: e o que a
    IA DECLARA que vai para o banco, e declarar e o que torna conferivel.
    """
    cru = item.get("nivel")
    if not str(cru or "").strip():
        return None, None, "sem o nivel (facil, media ou dificil)"
    chave = normalizar(str(cru))
    if chave is None:
        return None, None, f"nivel {cru!r} fora da lista (facil, media ou dificil)"
    por_que = " ".join(str(item.get("por_que_o_nivel") or "").split())
    if not por_que:
        return None, None, "sem o por_que_o_nivel"
    return chave, por_que, None


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


def quantas_do_nivel(n: int, chave: str) -> str:
    """"4 difíceis", "1 difícil"; na misturada, "4 questões geradas"."""
    nivel = NIVEIS.get(chave)
    if nivel is None:
        return f"{n} {'questão gerada' if n == 1 else 'questões geradas'}"
    return f"{n} {nivel.rotulo.lower() if n == 1 else nivel.plural}"


def rotulo_do_selo(chave: str | None) -> str:
    """O texto do selo 🟣 na questao: "Gerada por IA · Difícil"."""
    return f"Gerada por IA · {rotulo(chave)}"
