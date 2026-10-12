"""O glossario das palavras dificeis (decisao 161): o termo, as variantes, o
significado numa frase do dia a dia e as fontes. Mora em data/glossario.json,
🟣 com a procedencia de cada termo, e cresce pela importacao da traducao.

Na tela, a 1a vez que um termo aparece em cada bloco fica sublinhada, e o
significado aparece ao passar o mouse ou tocar (so CSS). O corte do texto em
trechos e feito aqui, e nao no template; o casamento e o do config/alvo.yml:
palavra inteira, sem acento e sem caixa (`alvo.palavra_inteira`). Puro: so
texto.
"""
from dataclasses import dataclass

from radar.alvo import palavra_inteira
from radar.regioes import normalizar


@dataclass
class Trecho:
    """Um pedaco do texto de uma frase. Com `significado`, e um termo do
    glossario: a tela o sublinha e mostra o significado."""

    texto: str
    termo: str | None = None
    significado: str | None = None


def chaves(termo: dict) -> set[str]:
    """As formas normalizadas de um termo: ele e as variantes."""
    return {normalizar(t) for t in [termo.get("termo") or ""] + list(termo.get("variantes") or [])
            if normalizar(t)}


def juntar(existentes: list[dict], novos: list[dict], modelo: str,
           criado_em: str) -> tuple[list[dict], int]:
    """O glossario com os termos novos, sem duplicar: o termo cujo nome (ou
    variante) ja esta no glossario fica como esta - o primeiro escrito vale,
    e a conferencia nao se perde. Devolve (glossario, quantos entraram)."""
    saida = [dict(t) for t in existentes]
    vistas = set().union(*(chaves(t) for t in saida)) if saida else set()
    entraram = 0
    for termo in novos:
        if chaves(termo) & vistas:
            continue
        saida.append({**termo, "modelo": modelo, "criado_em": criado_em})
        vistas |= chaves(termo)
        entraram += 1
    return sorted(saida, key=lambda t: normalizar(t["termo"])), entraram


def _normalizado_com_mapa(texto: str) -> tuple[str, list[int]]:
    """O texto normalizado (`regioes.normalizar`, letra a letra) e, para cada
    letra dele, a posicao no texto original. E o que deixa casar sem acento e
    cortar o texto COM acento no lugar certo."""
    normal, mapa = [], []
    for posicao, letra in enumerate(texto):
        trocada = " " if letra.isspace() else normalizar(letra)
        normal.append(trocada)
        mapa += [posicao] * len(trocada)
    return "".join(normal), mapa


def trechos(texto: str, termos: list[dict], vistos: set, protegido=None) -> list[Trecho]:
    """O texto cortado nos termos do glossario: so a 1a vez de cada termo, e
    so se ele ainda nao apareceu no bloco (`vistos`, as chaves dos termos ja
    marcados, que esta funcao atualiza). `protegido` e uma regex de trechos
    que nao se cortam: o "2019-q51 (gabarito C)", que o filtro `sem_gabarito`
    precisa achar inteiro."""
    if not texto or not termos:
        return [Trecho(texto)]
    normal, mapa = _normalizado_com_mapa(texto)
    fechados = [(m.start(), m.end()) for m in protegido.finditer(texto)] if protegido else []
    achados = []
    for termo in termos:
        chave = normalizar(termo["termo"])
        for forma in [termo["termo"]] + list(termo.get("variantes") or []):
            for m in palavra_inteira(forma).finditer(normal):
                if m.end() > m.start():
                    inicio, fim = mapa[m.start()], mapa[m.end() - 1] + 1
                    achados.append((inicio, -(fim - inicio), fim, chave, termo))
    saida, cursor = [], 0
    for inicio, _, fim, chave, termo in sorted(achados, key=lambda a: (a[0], a[1])):
        if chave in vistos or inicio < cursor:
            continue
        if any(inicio < f and fim > i for i, f in fechados):
            continue
        if inicio > cursor:
            saida.append(Trecho(texto[cursor:inicio]))
        saida.append(Trecho(texto[inicio:fim], termo["termo"], termo["significado"]))
        vistos.add(chave)
        cursor = fim
    if cursor < len(texto):
        saida.append(Trecho(texto[cursor:]))
    return saida
