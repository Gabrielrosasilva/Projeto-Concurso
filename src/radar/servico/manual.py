"""Usar a IA sem pagar a API: o pedido vai para um arquivo, a resposta volta.

O `radar gerar --valendo` chama a API e custa dinheiro. Este e o outro
caminho: o radar escreve TODOS os pedidos em `data/pedido_ia.json`, com a
instrucao e o formato da resposta dentro, eu respondo pelo Claude Code do VS
Code (na minha assinatura), e o radar le a resposta de volta.

Duas regras seguram tudo, e sao as mesmas da API:

  * **procedencia honesta.** O que entra por aqui e gravado como "Claude
    Code, importado manualmente, em <data>" - NUNCA com o nome do modelo da
    API. O radar nao sabe qual modelo o Claude Code usou, e dizer que sabe
    seria inventar procedencia;
  * **resposta torta e recusada, e contada.** Questao sem as cinco
    alternativas, sem gabarito ou sem o artigo da lei nao entra; macete sem
    fonte, ou citando questao que nao foi enviada, tambem nao.

Serve para os dois: questao gerada (`tipo: questoes`) e macete (`tipo:
macetes`). A questao gerada entra na tabela `questoes_geradas`, com a mesma
separacao de sempre - treina, nunca mede. O macete ainda nao tem tela: ele
vai para `data/macetes.json`, versionado, e a Central de Macetes (fase 5 da
especificacao) le de la.
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from radar import config, gerador, leis
from radar.db import criar_tabelas, sessao
from radar.models import agora
from radar.regioes import normalizar
from radar.servico import geradas

TIPOS = ("questoes", "macetes", "explicacoes")

# Quantos macetes por materia. Tres cabe numa resposta so e obriga a IA a
# escolher o que mais cai, em vez de listar tudo.
MACETES_POR_MATERIA = 3


def caminho_do_pedido() -> Path:
    return config.diretorio_dados() / "pedido_ia.json"


def caminho_dos_macetes() -> Path:
    return config.diretorio_dados() / "macetes.json"


def caminho_das_explicacoes() -> Path:
    return config.diretorio_dados() / "explicacoes.json"


def procedencia(quando: datetime | None = None) -> str:
    """O que vai no campo `modelo`. Diz o caminho, e nao um modelo que eu nao
    sei qual foi."""
    return f"Claude Code, importado manualmente, em {(quando or agora()):%d/%m/%Y}"


# --- as instrucoes ----------------------------------------------------------

INSTRUCAO_MACETE = """Voce recebe questoes reais de concurso publico brasileiro, da banca FEPESE, com o gabarito oficial ja conferido, todas da mesma materia.

Escreva macetes para estudar esta materia para a proxima prova da mesma banca.

Regras:
- cada macete e uma regra pratica curta, que ajuda a resolver questoes como
  estas - nao um resumo da materia;
- diga a FONTE de cada macete: o artigo da lei, assim: "art. 112 da Lei
  7.210/1984"; fora de Direito, a regra gramatical ou logica. Sem fonte
  segura, nao escreva o macete;
- a lei pode ter mudado depois da prova: cite o texto VIGENTE, e se a questao
  antiga ficou desatualizada, diga isso na regra;
- se houver uma pegadinha recorrente (a alternativa errada que a banca usa
  para enganar), descreva-a em "pegadinha"; se nao houver, responda "";
- em "questoes", cite os CODIGOS (ex.: "2019-q66") das questoes reais em que o
  macete se apoia. So codigos que estao neste pedido;
- no maximo %d macetes, os que mais ajudam.

Responda SOMENTE um JSON, no formato:
{"macetes": [{"assunto": "...", "regra": "...", "fonte": "art. 112 da Lei 7.210/1984", "pegadinha": "...", "questoes": ["2019-q66"]}]}""" % MACETES_POR_MATERIA


INSTRUCAO_EXPLICACAO = """Voce recebe UMA questao real de concurso publico brasileiro, da banca FEPESE, com o gabarito oficial ja conferido. Eu errei esta questao.

Explique por que a alternativa do gabarito oficial e a correta.

Regras:
- o gabarito oficial manda: explique a alternativa dele, e repita a letra dele
  no campo "correta". Se voce discordar do gabarito, NAO responda este pedido;
- diga a FONTE: o artigo da lei, assim: "art. 112 da Lei 7.210/1984"; fora de
  Direito, a regra gramatical ou logica. Sem fonte segura, nao responda;
- a lei pode ter mudado depois da prova: se o texto vigente mudou o gabarito,
  diga isso na explicacao;
- diga tambem por que a alternativa errada mais tentadora esta errada;
- curto: no maximo 5 frases.

Responda SOMENTE um JSON, no formato:
{"correta": "c", "explicacao": "...", "fonte": "art. 112 da Lei 7.210/1984"}"""


def _como_responder(tipo: str) -> str:
    """O recado para quem responde. Vai dentro do arquivo, no topo."""
    if tipo == "explicacoes":
        return (
            "Este arquivo foi gerado por `radar gerar --pedido --explicacoes`. "
            "Para cada item de `pedidos`, siga a `instrucao` usando o texto de "
            "`pedido`. Responda TODOS num unico arquivo JSON, no formato de "
            "`formato_da_resposta`: o mesmo `lote` deste arquivo, e o `id` de "
            "cada pedido com o objeto `explicacao` dele. Salve como "
            "data/resposta_ia.json e rode `radar gerar --importar "
            "data/resposta_ia.json`. Explicacao cuja `correta` nao for a letra "
            "do gabarito oficial, ou sem `fonte`, sera RECUSADA."
        )
    campo = "questoes" if tipo == "questoes" else "macetes"
    texto = (
        "Este arquivo foi gerado por `radar gerar --pedido`. Para cada item de "
        "`pedidos`, siga a `instrucao` usando o texto de `pedido`. Responda "
        "TODOS os pedidos num unico arquivo JSON, no formato de "
        "`formato_da_resposta`: o mesmo `lote` deste arquivo, e o `id` de cada "
        f"pedido com a lista `{campo}` dele. Salve como data/resposta_ia.json e "
        "rode `radar gerar --importar data/resposta_ia.json`. "
    )
    if tipo == "questoes":
        texto += (
            "Questao sem o artigo da lei no campo `artigo` sera RECUSADA - fora "
            "de Direito (Portugues, Raciocinio Logico), ponha ali a regra em "
            "que a resposta se apoia. Se nao tiver certeza do artigo, nao "
            "escreva a questao: a instrucao diz para deixar vazio, mas aqui "
            "vazio e recusado. Escreva no maximo `quantas` questoes por pedido."
        )
    else:
        texto += (
            "Macete sem `fonte`, ou citando em `questoes` um codigo que nao "
            "esta no pedido, sera RECUSADO."
        )
    return texto


def _formato(tipo: str) -> dict:
    if tipo == "explicacoes":
        item = {"correta": "c", "explicacao": "...",
                "fonte": "art. 112 da Lei 7.210/1984"}
        return {"lote": "<o lote deste arquivo>",
                "respostas": [{"id": "e1", "explicacao": item}]}
    if tipo == "questoes":
        item = {"enunciado": "...", "alternativas": {
            "a": "...", "b": "...", "c": "...", "d": "...", "e": "..."},
            "resposta": "c", "artigo": "art. 41, XV, da Lei 7.210/1984"}
        return {"lote": "<o lote deste arquivo>",
                "respostas": [{"id": "p1", "questoes": [item]}]}
    item = {"assunto": "...", "regra": "...", "fonte": "art. 112 da Lei 7.210/1984",
            "pegadinha": "...", "questoes": ["2019-q66"]}
    return {"lote": "<o lote deste arquivo>",
            "respostas": [{"id": "m1", "macetes": [item]}]}


def _novo_lote(tipo: str, pedidos: list[dict]) -> dict:
    agora_ = agora()
    return {
        "lote": f"{tipo}-{agora_:%Y%m%d-%H%M%S}",
        "tipo": tipo,
        "criado_em": agora_.isoformat(),
        "como_responder": _como_responder(tipo),
        "formato_da_resposta": _formato(tipo),
        "pedidos": pedidos,
    }


# --- montar o pedido --------------------------------------------------------

def pedido_de_questoes(materia: str | None = None, quantas: int = 5,
                       semente: int | None = None) -> dict:
    """Os mesmos pedidos que o `--valendo` mandaria a API, todos num lote.

    Sai do mesmo `geradas.preparar`: a escolha da questao de base, o modo do
    zero e a divisao em chamadas sao os de sempre. O que muda e so quem
    responde.
    """
    plano = geradas.preparar(materia, quantas, semente)
    pedidos = []
    for numero, pedido in enumerate(plano["pedidos"], start=1):
        if pedido["modo"] == "do_zero":
            instrucao = gerador.INSTRUCAO_DO_ZERO
            corpo = gerador._montar_pedido_do_zero(
                pedido["materia"], pedido.get("assunto"),
                pedido.get("exemplos") or [], pedido["quantas"],
            )
            base = {"materia": pedido["materia"], "assunto": pedido.get("assunto"),
                    "origem_impressao": None}
        else:
            questao = pedido["questao"]
            instrucao = gerador.INSTRUCAO_VARIACAO
            corpo = gerador._montar_pedido_variacao(questao, pedido["quantas"])
            base = {"materia": questao.materia,
                    "assunto": getattr(questao, "assunto", None),
                    "origem_impressao": questao.impressao}
        pedidos.append({
            "id": f"p{numero}", "modo": pedido["modo"],
            "quantas": pedido["quantas"], **base,
            "instrucao": instrucao, "pedido": corpo,
        })
    return _novo_lote("questoes", pedidos)


def _codigo(questao) -> str:
    return f"{questao.ano}-q{questao.numero}"


def pedido_de_macetes(materia: str | None = None) -> dict:
    """Um pedido por materia, com as questoes reais do MEU cargo nela.

    So as provas do alvo (2013 e 2019), e nao o reforco: macete e sobre o que
    a banca cobra de mim. Anulada fica de fora - a banca disse que ela nao tem
    resposta certa, e um macete apoiado nela ensinaria o erro.
    """
    criar_tabelas()
    with sessao() as s:
        reais = geradas._reais_do_alvo(s, materia)

    por_materia: dict[str, list] = {}
    for q in sorted(reais, key=lambda q: (q.ano or 0, q.numero)):
        por_materia.setdefault(q.materia or "sem materia", []).append(q)

    pedidos = []
    for numero, (nome, questoes) in enumerate(sorted(por_materia.items()), start=1):
        citaveis, blocos = {}, []
        for q in questoes:
            codigo = _codigo(q)
            citaveis[codigo] = {"prova_url": q.prova_url, "numero": q.numero,
                                "impressao": q.impressao, "ano": q.ano}
            blocos.append(f"[{codigo}]\n{gerador._questao_por_extenso(q)}")
        corpo = (f"MATERIA: {nome}\n\nQUESTOES REAIS\n\n" + "\n\n".join(blocos)
                 + f"\n\nEscreva ate {MACETES_POR_MATERIA} macetes.")
        pedidos.append({
            "id": f"m{numero}", "materia": nome,
            "instrucao": INSTRUCAO_MACETE, "pedido": corpo,
            "citaveis": citaveis,
        })
    return _novo_lote("macetes", pedidos)


def pedido_de_explicacoes() -> dict:
    """Um pedido por questao real que eu errei na ultima vez que respondi.

    A lista e a mesma do [Revisar agora] - uma regra so para "errei" - e a
    questao que ja tem explicacao fica de fora: pedir duas vezes a mesma
    explicacao nao ensina nada novo.
    """
    from radar.models import QuestaoDeProva
    from radar.servico import simulado as treino

    ja_explicadas = set(carregar_explicacoes())
    criar_tabelas()
    with sessao() as s:
        questoes = [
            q for q in (s.get(QuestaoDeProva, qid) for qid in treino.questoes_erradas())
            if q is not None and q.resposta and q.impressao not in ja_explicadas
        ]
        pedidos = []
        vistos = set()
        for q in sorted(questoes, key=lambda q: (q.ano or 0, q.numero)):
            if q.impressao in vistos:
                continue
            vistos.add(q.impressao)
            pedidos.append({
                "id": f"e{len(pedidos) + 1}", "materia": q.materia,
                "impressao": q.impressao, "gabarito": q.resposta,
                "instrucao": INSTRUCAO_EXPLICACAO,
                "pedido": (f"MATERIA: {q.materia or 'nao informada'}\n\n"
                           f"QUESTAO ({q.banca or 'FEPESE'} {q.ano or ''})\n\n"
                           f"{gerador._questao_por_extenso(q)}"),
            })
    return _novo_lote("explicacoes", pedidos)


def salvar_pedido(lote: dict, caminho: Path | None = None) -> Path:
    destino = caminho or caminho_do_pedido()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(lote, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return destino


# --- ler a resposta de volta ------------------------------------------------

# "art. 41", "arts. 5º e 6º", "artigo 112", "Súmula Vinculante 56".
CITA_ARTIGO = re.compile(r"(?i)\bart(?:igo)?s?\.?\s*\d|\bs[uú]mula\b")


def fonte_serve(fonte: str | None, materia: str | None) -> bool:
    fonte = " ".join((fonte or "").split())
    if not fonte:
        return False
    return bool(CITA_ARTIGO.search(fonte)) if leis.exige_artigo(materia) else True


def _ler_json(texto: str) -> dict:
    """O JSON da resposta, mesmo cercado de crase tripla ou de uma frase."""
    achado = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if not achado:
        raise ValueError("a resposta nao tem JSON nenhum")
    try:
        return json.loads(achado.group(0))
    except json.JSONDecodeError as erro:
        raise ValueError(f"a resposta nao e um JSON valido ({erro})") from erro


def _importar_questoes(lote: dict, respostas: list[dict], modelo: str) -> dict:
    por_id = {p["id"]: p for p in lote["pedidos"]}
    aceitas, recusas = [], []

    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        itens = [i for i in resposta.get("questoes") or [] if isinstance(i, dict)]
        for posicao, item in enumerate(itens, start=1):
            onde = f"{pedido['id']}, questao {posicao}"
            if posicao > pedido["quantas"]:
                recusas.append(f"{onde}: o pedido era de {pedido['quantas']}")
                continue
            conferida = gerador._conferir(item)
            if conferida is None:
                recusas.append(f"{onde}: sem as 5 alternativas ou sem gabarito valido")
                continue
            if not fonte_serve(conferida["artigo"], pedido.get("materia")):
                recusas.append(f"{onde}: sem o artigo da lei em que se apoia")
                continue
            aceitas.append(gerador.QuestaoNova(
                modo=pedido["modo"], materia=pedido.get("materia"),
                assunto=pedido.get("assunto"),
                origem_impressao=pedido.get("origem_impressao"),
                modelo=modelo, **conferida,
            ))

    # Repetida dentro da resposta, ou ja gerada antes: nao entra duas vezes.
    gravadas = geradas.gravar(aceitas)
    repetidas = len(aceitas) - gravadas
    if gravadas:
        from radar import acervo

        acervo.exportar_geradas()
    return {"gravadas": gravadas, "repetidas": repetidas, "recusas": recusas}


def _impressao_do_macete(materia: str, regra: str) -> str:
    return hashlib.md5(
        f"{normalizar(materia)}|{normalizar(regra)}".encode("utf-8")
    ).hexdigest()


def carregar_macetes(caminho: Path | None = None) -> list[dict]:
    origem = caminho or caminho_dos_macetes()
    if not origem.exists():
        return []
    return json.loads(origem.read_text(encoding="utf-8")) or []


def gravar_macetes(novos: list[dict], caminho: Path | None = None) -> int:
    """Junta os macetes novos ao arquivo. Devolve quantos entraram.

    A mesma trava da questao gerada: macete sem `modelo` e `criado_em` nao
    entra, e o lote inteiro para.
    """
    if any(not m.get("modelo") or not m.get("criado_em") for m in novos):
        raise ValueError("macete sem procedencia nao e gravado: diga de onde veio")

    destino = caminho or caminho_dos_macetes()
    existentes = carregar_macetes(destino)
    vistos = {m.get("impressao") for m in existentes}
    entraram = 0
    for macete in novos:
        if macete["impressao"] in vistos:
            continue
        vistos.add(macete["impressao"])
        existentes.append(macete)
        entraram += 1

    existentes.sort(key=lambda m: (m.get("materia") or "", m.get("criado_em") or ""))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(existentes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return entraram


def _importar_macetes(lote: dict, respostas: list[dict], modelo: str) -> dict:
    por_id = {p["id"]: p for p in lote["pedidos"]}
    aceitos, recusas = [], []
    quando = agora().isoformat()

    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        itens = [i for i in resposta.get("macetes") or [] if isinstance(i, dict)]
        for posicao, item in enumerate(itens, start=1):
            onde = f"{pedido['id']} ({pedido['materia']}), macete {posicao}"
            if posicao > MACETES_POR_MATERIA:
                recusas.append(f"{onde}: o pedido era de ate {MACETES_POR_MATERIA}")
                continue
            regra = " ".join(str(item.get("regra") or "").split())
            fonte = " ".join(str(item.get("fonte") or "").split())
            codigos = [str(c) for c in item.get("questoes") or []]
            if len(regra) < 20:
                recusas.append(f"{onde}: sem regra")
                continue
            if not fonte_serve(fonte, pedido["materia"]):
                recusas.append(f"{onde}: sem a fonte (o artigo da lei)")
                continue
            # A pegadinha vira link para as questoes reais. Codigo que nao
            # foi enviado seria um link para uma questao que nao existe.
            citaveis = pedido.get("citaveis") or {}
            if not codigos or any(c not in citaveis for c in codigos):
                recusas.append(f"{onde}: cita questao que nao estava no pedido")
                continue
            aceitos.append({
                "materia": pedido["materia"],
                "assunto": " ".join(str(item.get("assunto") or "").split()) or None,
                "regra": regra,
                "fonte": fonte,
                "pegadinha": " ".join(str(item.get("pegadinha") or "").split()) or None,
                "questoes": [{"codigo": c, **citaveis[c]} for c in codigos],
                "modelo": modelo,
                "criado_em": quando,
                "impressao": _impressao_do_macete(pedido["materia"], regra),
            })

    gravados = gravar_macetes(aceitos) if aceitos else 0
    return {"gravadas": gravados, "repetidas": len(aceitos) - gravados,
            "recusas": recusas}


def carregar_explicacoes(caminho: Path | None = None) -> dict[str, dict]:
    """{impressao: explicacao} - so as que dizem a fonte e de onde vieram.

    O arquivo e editavel a mao, e a tela nao confia nele: explicacao sem
    `fonte` ou sem procedencia nao aparece, como o macete.
    """
    origem = caminho or caminho_das_explicacoes()
    if not origem.exists():
        return {}
    linhas = json.loads(origem.read_text(encoding="utf-8")) or []
    return {
        e["impressao"]: e for e in linhas
        if e.get("impressao") and (e.get("fonte") or "").strip()
        and (e.get("modelo") or "").strip() and e.get("criado_em")
    }


def _importar_explicacoes(lote: dict, respostas: list[dict], modelo: str) -> dict:
    por_id = {p["id"]: p for p in lote["pedidos"]}
    destino = caminho_das_explicacoes()
    existentes = (json.loads(destino.read_text(encoding="utf-8")) or []
                  if destino.exists() else [])
    ja = {e.get("impressao") for e in existentes}
    quando = agora().isoformat()
    gravadas = repetidas = 0
    recusas = []

    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: nao existe esse pedido no lote")
            continue
        item = resposta.get("explicacao") or {}
        onde = f"{pedido['id']} ({pedido.get('materia')})"
        texto = " ".join(str(item.get("explicacao") or "").split())
        fonte = " ".join(str(item.get("fonte") or "").split())
        correta = str(item.get("correta") or "").strip().lower()[:1]
        # O gabarito oficial manda. Explicacao que defende outra letra
        # ensinaria o erro com cara de certeza.
        if correta != (pedido.get("gabarito") or "").lower():
            recusas.append(f"{onde}: explica a letra {correta or '?'}, e o "
                           f"gabarito oficial e {pedido.get('gabarito')}")
            continue
        if len(texto) < 40:
            recusas.append(f"{onde}: sem explicacao")
            continue
        if not fonte_serve(fonte, pedido.get("materia")):
            recusas.append(f"{onde}: sem a fonte (o artigo da lei)")
            continue
        if pedido["impressao"] in ja:
            repetidas += 1
            continue
        ja.add(pedido["impressao"])
        existentes.append({
            "impressao": pedido["impressao"], "materia": pedido.get("materia"),
            "correta": correta, "explicacao": texto, "fonte": fonte,
            "modelo": modelo, "criado_em": quando,
        })
        gravadas += 1

    if gravadas:
        existentes.sort(key=lambda e: e["impressao"])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(existentes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {"gravadas": gravadas, "repetidas": repetidas, "recusas": recusas}


def importar(resposta: Path, pedido: Path | None = None,
             quando: datetime | None = None) -> dict:
    """Le a resposta, confere contra o lote do pedido, e grava o que presta.

    Devolve {"tipo", "gravadas", "repetidas", "recusas"}. Levanta ValueError
    quando nada pode ser lido: sem pedido, JSON quebrado, ou resposta de
    OUTRO lote - aplicar a resposta de um pedido velho sobre o pedido novo
    poria a variacao de uma questao em cima de outra.
    """
    origem_do_pedido = pedido or caminho_do_pedido()
    if not origem_do_pedido.exists():
        raise ValueError(f"nao achei o pedido em {origem_do_pedido}")
    lote = json.loads(origem_do_pedido.read_text(encoding="utf-8"))
    corpo = _ler_json(resposta.read_text(encoding="utf-8"))

    if corpo.get("lote") != lote.get("lote"):
        raise ValueError(
            f"a resposta e do lote {corpo.get('lote')!r} e o pedido e do lote "
            f"{lote.get('lote')!r}"
        )
    respostas = [r for r in corpo.get("respostas") or [] if isinstance(r, dict)]
    modelo = procedencia(quando)

    if lote.get("tipo") == "macetes":
        resultado = _importar_macetes(lote, respostas, modelo)
    elif lote.get("tipo") == "explicacoes":
        resultado = _importar_explicacoes(lote, respostas, modelo)
    else:
        resultado = _importar_questoes(lote, respostas, modelo)
    return {"tipo": lote.get("tipo"), "modelo": modelo, **resultado}
