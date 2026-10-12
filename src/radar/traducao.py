"""A traducao de cada artigo, "do meu jeito" (decisao 161, pedido de 12/10).

O texto do artigo, como esta no resumo, nao muda: a traducao e a mais, por
artigo, em tres linhas - "na real" (o artigo numa frase do dia a dia),
"exemplo" (uma cena concreta) e "na prova" (o numero ou a palavra que a banca
troca para derrubar) -, mais o "nao confunda" do tema e os termos dificeis do
glossario. Mora na ficha, numa chave propria (`traducao`), porque tem
procedencia e data proprias.

A regra que nao muda: a traducao nunca diz o que o artigo nao diz.
  * o "na real" e o "exemplo" citam SO o proprio artigo;
  * o "na prova" pode citar outro artigo do tema, sumula ou questao real do
    tema, com a mesma conferencia do resumo (decisao 118).

Puro, menos o `perfil()`, que le o config/linguagem.yml.
"""
from dataclasses import dataclass
from functools import cache

import yaml

from radar import artigos, config
from radar.alvo import palavra_inteira
from radar.fichas import (CODIGO_DA_QUESTAO, GABARITO_CITADO, LINHAS_DA_TRADUCAO, PREVISAO,
                          TEXTO_MINIMO_DA_FRASE, FichaRecusada, _lista, _texto)
from radar.regioes import normalizar

#: As tres linhas de cada artigo, na ordem da tela, com o nome que a tela da:
#: as mesmas do resumo enxuto, que as desenha.
LINHAS = LINHAS_DA_TRADUCAO
NOME_DA_LINHA = dict(LINHAS)

#: As linhas que citam so o proprio artigo. O "na prova" fica de fora: ele
#: mira no que a banca troca, e pode citar a sumula ou a questao real.
SO_O_PROPRIO_ARTIGO = ("na_real", "exemplo")

#: O "nao confunda" e uma tabela: a situacao, o que ela e e o que acontece.
COLUNAS_DO_NAO_CONFUNDA = ("situacao", "o_que_e", "o_que_acontece")

#: Um campo curto do "nao confunda" ("Desistência voluntária") e mais curto
#: que uma frase; menos que isto e campo vazio.
TEXTO_MINIMO_DA_COLUNA = 3


@cache
def perfil() -> dict:
    """O config/linguagem.yml inteiro. Ausente vira {}: o pedido sai sem o
    perfil, e a importacao sem a lista de palavroes."""
    arquivo = config.diretorio_config() / "linguagem.yml"
    if not arquivo.exists():
        return {}
    return yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}


def recarregar() -> None:
    """Esquece o que foi lido. Usado pelos testes e se voce editar o YAML."""
    perfil.cache_clear()


def palavroes() -> list[str]:
    return [str(p) for p in perfil().get("palavroes") or [] if str(p).strip()]


def palavrao_em(texto: str, lista) -> str | None:
    """O primeiro palavrao da lista que aparece no texto, por palavra
    inteira, sem acento e sem caixa - o casamento do config/alvo.yml."""
    normal = normalizar(texto or "")
    for palavra in lista or []:
        if palavra_inteira(str(palavra)).search(normal):
            return str(palavra)
    return None


def faixas_do_pedido(brutas) -> list[artigos.Faixa]:
    """As faixas de artigos do tema como o pedido as grava (dicionarios)."""
    return [artigos.Faixa(b["lei"], tuple(b["inicio"]), tuple(b["fim"])) for b in brutas or []]


def faixas_para_o_pedido(faixas: list[artigos.Faixa]) -> list[dict]:
    vistas = []
    for f in faixas:
        bruta = {"lei": f.lei, "inicio": list(f.inicio), "fim": list(f.fim)}
        if bruta not in vistas:
            vistas.append(bruta)
    return vistas


def _linha(bruta, onde: str) -> dict:
    if not isinstance(bruta, dict):
        raise FichaRecusada(f"{onde}: tem de ser um objeto com texto e fontes")
    texto = _texto(bruta.get("texto"))
    fontes = _lista(bruta.get("fontes"))
    if len(texto) < TEXTO_MINIMO_DA_FRASE:
        raise FichaRecusada(f"{onde}: linha sem texto")
    if not fontes:
        raise FichaRecusada(f"{onde}: linha sem fonte")
    return {"texto": texto, "fontes": fontes}


def _e_sumula(fonte: str) -> bool:
    return "sumula" in normalizar(fonte)


def _conferir_codigos(textos: list[str], codigos: dict, onde: str) -> None:
    """A mesma conferencia do resumo (decisao 118): a questao citada e do
    tema, e o gabarito citado e o oficial."""
    juntas = " ".join(textos)
    for codigo in CODIGO_DA_QUESTAO.findall(juntas):
        if codigo not in codigos:
            raise FichaRecusada(f"{onde}: a questão {codigo} não é deste tema (ou não existe)")
    for codigo, letra in GABARITO_CITADO.findall(juntas):
        if (codigos.get(codigo) or "").lower() != letra.lower():
            raise FichaRecusada(f"{onde}: o gabarito oficial de {codigo} não é {letra.upper()}")


def _fonte_do_tema(fonte: str, tema: list, codigos: dict, onde: str) -> None:
    """A fonte do "na prova" e do "nao confunda": artigo do tema, sumula ou
    questao real do tema. Outra coisa (doutrina, outra lei) e recusada."""
    citados = artigos.citados(fonte)
    for faixa in citados:
        for artigo in (artigos.Artigo(faixa.lei, *faixa.inicio),
                       artigos.Artigo(faixa.lei, *faixa.fim)):
            if not artigos.do_tema_contem(tema, artigo):
                raise FichaRecusada(f"{onde}: o artigo {artigo.rotulo} não é do tema")
    if citados or _e_sumula(fonte) or CODIGO_DA_QUESTAO.search(fonte):
        return
    raise FichaRecusada(f"{onde}: a fonte {fonte!r} não é artigo do tema, súmula nem "
                        f"questão real")


def conferir_traducao(bruto, *, tema: list, codigos: dict,
                      lista_de_palavroes=()) -> tuple[dict, list]:
    """A traducao conferida e os termos do glossario. Levanta `FichaRecusada`
    com o motivo; a recusa e da traducao inteira, como a do resumo.

    - `tema`: as faixas de artigos que o tema cobre (o titulo e o "ler
      exatamente" da ficha, `artigos.do_tema`);
    - `codigos`: {"2019-q51": "c"}, as questoes reais do tema, com o
      gabarito oficial (as mesmas que o resumo pode citar).

    Recusa: linha sem texto ou sem fonte; "na real" ou "exemplo" com fonte
    que nao e o proprio artigo; artigo que nao e do tema (ou que nao e um
    dispositivo so); questao fora do tema ou com o gabarito trocado;
    palavrao; e previsao, como no resumo.
    """
    if not isinstance(bruto, dict):
        raise FichaRecusada("sem o objeto `traducao`")
    itens_brutos = bruto.get("itens")
    if not isinstance(itens_brutos, list) or not itens_brutos:
        raise FichaRecusada("a tradução não tem itens (um por artigo)")

    itens, vistos, textos_para_conferir = [], set(), []
    for numero, item in enumerate(itens_brutos, start=1):
        if not isinstance(item, dict):
            raise FichaRecusada(f"item {numero}: tem de ser um objeto")
        rotulo = _texto(item.get("artigo"))
        artigo = artigos.da_fonte(rotulo)
        onde = f"item {numero} ({rotulo or 'sem artigo'})"
        if artigo is None:
            raise FichaRecusada(f"{onde}: o artigo tem de ser um dispositivo só "
                                f"(\"CP, art. 15\")")
        if not artigos.do_tema_contem(tema, artigo):
            raise FichaRecusada(f"{onde}: o artigo {artigo.rotulo} não é do tema")
        if artigo in vistos:
            raise FichaRecusada(f"{onde}: o artigo {artigo.rotulo} aparece duas vezes")
        vistos.add(artigo)
        conferido = {"artigo": artigo.rotulo}
        for chave, nome in LINHAS:
            linha = _linha(item.get(chave), f"{onde}, {nome}")
            if chave in SO_O_PROPRIO_ARTIGO:
                juntas = " ".join([linha["texto"]] + linha["fontes"])
                if CODIGO_DA_QUESTAO.search(juntas):
                    raise FichaRecusada(f"{onde}, {nome}: cita só o próprio artigo - a "
                                        f"questão real vai no 'Na prova'")
                for fonte in linha["fontes"]:
                    if artigos.da_fonte(fonte) != artigo:
                        raise FichaRecusada(f"{onde}, {nome}: a fonte {fonte!r} não é o "
                                            f"próprio artigo ({artigo.rotulo})")
            else:
                for fonte in linha["fontes"]:
                    _fonte_do_tema(fonte, tema, codigos, f"{onde}, {nome}")
                _conferir_codigos([linha["texto"]] + linha["fontes"], codigos,
                                  f"{onde}, {nome}")
            textos_para_conferir.append((f"{onde}, {nome}",
                                         " ".join([linha["texto"]] + linha["fontes"])))
            conferido[chave] = linha
        itens.append(conferido)

    nao_confunda = []
    for numero, bruta in enumerate(bruto.get("nao_confunda") or [], start=1):
        onde = f"não confunda, linha {numero}"
        if not isinstance(bruta, dict):
            raise FichaRecusada(f"{onde}: tem de ser um objeto")
        linha = {coluna: _texto(bruta.get(coluna)) for coluna in COLUNAS_DO_NAO_CONFUNDA}
        if any(len(v) < TEXTO_MINIMO_DA_COLUNA for v in linha.values()):
            raise FichaRecusada(f"{onde}: linha sem texto (situação, o que é e o que "
                                f"acontece)")
        linha["fontes"] = _lista(bruta.get("fontes"))
        if not linha["fontes"]:
            raise FichaRecusada(f"{onde}: linha sem fonte")
        for fonte in linha["fontes"]:
            _fonte_do_tema(fonte, tema, codigos, onde)
        juntas = [linha[c] for c in COLUNAS_DO_NAO_CONFUNDA] + linha["fontes"]
        _conferir_codigos(juntas, codigos, onde)
        textos_para_conferir.append((onde, " ".join(juntas)))
        nao_confunda.append(linha)

    termos = []
    for numero, bruto_termo in enumerate(bruto.get("glossario") or [], start=1):
        onde = f"glossário, termo {numero}"
        termo = _termo(bruto_termo, onde)
        textos_para_conferir.append((onde, " ".join(
            [termo["termo"], termo["significado"]] + termo["variantes"] + termo["fontes"])))
        termos.append(termo)

    for onde, texto in textos_para_conferir:
        palavra = palavrao_em(texto, lista_de_palavroes)
        if palavra:
            raise FichaRecusada(f"{onde}: palavrão ({palavra!r}) - o perfil do "
                                f"config/linguagem.yml não aceita")
        achado = PREVISAO.search(texto)
        if achado:
            raise FichaRecusada(f"{onde}: texto com cara de previsão ({achado.group(0)!r})")
    return {"itens": itens, "nao_confunda": nao_confunda}, termos


def _termo(bruto, onde: str) -> dict:
    """Um termo do glossario: o termo, as variantes (outras formas de
    escrever: plural, sem acento nao precisa), o significado numa frase do dia
    a dia e as fontes."""
    if not isinstance(bruto, dict):
        raise FichaRecusada(f"{onde}: tem de ser um objeto")
    termo = _texto(bruto.get("termo"))
    significado = _texto(bruto.get("significado"))
    fontes = _lista(bruto.get("fontes"))
    if len(termo) < 2:
        raise FichaRecusada(f"{onde}: sem o termo")
    if len(significado) < TEXTO_MINIMO_DA_FRASE:
        raise FichaRecusada(f"{onde} ({termo}): sem o significado")
    if not fontes:
        raise FichaRecusada(f"{onde} ({termo}): sem fonte")
    variantes = [v for v in _lista(bruto.get("variantes"))
                 if normalizar(v) != normalizar(termo)]
    return {"termo": termo, "variantes": variantes, "significado": significado,
            "fontes": fontes}


# --- a traducao orfa --------------------------------------------------------------------

@dataclass(frozen=True)
class Orfa:
    """Um item da traducao que nao aparece mais na tela, e por que."""

    artigo: str
    motivo: str


def citados_no_resumo(resumo: dict | None) -> list[artigos.Faixa]:
    """As faixas de artigos que o resumo cita, em qualquer parte e fonte."""
    return [faixa for frases in ((resumo or {}).get("partes") or {}).values()
            for frase in frases for fonte in frase.get("fontes") or []
            for faixa in artigos.citados(fonte)]


def orfas(traducao: dict | None, resumo: dict | None, tema: list) -> list[Orfa]:
    """Os itens que nao aparecem: o artigo deixou de ser do tema (a ficha foi
    refeita), ou o resumo foi refeito e o artigo sumiu dele - estava entre os
    que o resumo citava quando a traducao foi importada
    (`artigos_do_resumo`), e nao esta mais. O artigo que o resumo nunca citou
    continua: e o bloco so com o numero e a traducao."""
    if not traducao:
        return []
    citados = citados_no_resumo(resumo)
    antes = faixas_do_pedido(traducao.get("artigos_do_resumo"))
    saida = []
    for item in traducao.get("itens") or []:
        artigo = artigos.da_fonte(item.get("artigo"))
        if artigo is None or not artigos.do_tema_contem(tema, artigo):
            saida.append(Orfa(item.get("artigo") or "", "o artigo não é mais do tema"))
        elif (artigos.do_tema_contem(antes, artigo)
              and not artigos.do_tema_contem(citados, artigo)):
            saida.append(Orfa(item.get("artigo"), "o resumo foi refeito e o artigo sumiu dele"))
    return saida


def visiveis(traducao: dict | None, resumo: dict | None, tema: list) -> list[dict]:
    """Os itens da traducao que a tela mostra: todos menos os orfaos."""
    if not traducao:
        return []
    fora = {o.artigo for o in orfas(traducao, resumo, tema)}
    return [i for i in traducao.get("itens") or [] if i.get("artigo") not in fora]
