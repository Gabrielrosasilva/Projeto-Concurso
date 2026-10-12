"""O glossario das palavras dificeis (decisao 161): o termo, as variantes, o
significado numa frase do dia a dia e as fontes. Mora em data/glossario.json,
🟣 com a procedencia de cada termo, e cresce pela importacao da traducao.

O casamento e o do config/alvo.yml: palavra inteira, sem acento e sem caixa
(`alvo.palavra_inteira`). Puro: so texto.
"""
from radar.regioes import normalizar


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
