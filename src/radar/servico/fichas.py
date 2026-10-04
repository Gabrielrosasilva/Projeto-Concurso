"""As fichas de estudo a partir do banco e dos arquivos (Etapa 6B).

A ficha e montada no `radar.fichas` e a prioridade no `radar.prioridade`, os
dois puros. Aqui se junta o que eles precisam - a incidencia do alvo e do
complementar, o meu desempenho, a fila de revisao, as geradas, o cronograma -
e se le e grava o `data/fichas.json`, o registro versionado do que foi escrito
(o banco nao guarda ficha: ela e texto meu e do Claude Code, como o macete).
"""
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select

from radar import amostra, config, fichas, incidencia, leis, prioridade
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoGerada, agora


def caminho_do_arquivo() -> Path:
    return config.diretorio_dados() / "fichas.json"


def carregar(caminho: Path | None = None) -> list[fichas.FichaEscrita]:
    """As fichas escritas. A que nao diz de onde veio (`modelo` e
    `criado_em`) nao e lida: o arquivo e editavel a mao, e a tela nao confia
    em texto sem procedencia - a mesma trava do macete."""
    arquivo = caminho or caminho_do_arquivo()
    if not arquivo.exists():
        return []
    brutas = json.loads(arquivo.read_text(encoding="utf-8")) or []
    return [fichas.FichaEscrita.de_dict(b) for b in brutas
            if isinstance(b, dict) and (b.get("modelo") or "").strip()
            and b.get("criado_em") and b.get("tema") and b.get("materia")]


def gravar(escritas: list[fichas.FichaEscrita], caminho: Path | None = None) -> Path:
    """Grava o arquivo inteiro, em ordem de materia e tema: o diff do git fica
    legivel, e duas gravacoes do mesmo conteudo dao o mesmo arquivo."""
    destino = caminho or caminho_do_arquivo()
    destino.parent.mkdir(parents=True, exist_ok=True)
    ordenadas = sorted(escritas, key=lambda e: (e.materia, e.chave))
    destino.write_text(
        json.dumps([e.para_dict() for e in ordenadas], ensure_ascii=False, indent=2)
        + "\n", encoding="utf-8")
    return destino


def achar(id_ou_tema: str, escritas: list[fichas.FichaEscrita] | None = None):
    """A ficha pelo id ("art-5o-caput-e-incisos-i-a-xvi") ou pelo tema."""
    escritas = carregar() if escritas is None else escritas
    procurado = (id_ou_tema or "").strip()
    for escrita in escritas:
        if escrita.id == procurado or escrita.chave == fichas.chave_do_tema(procurado):
            return escrita
    return None


def das_faixas(blocos, escritas: list[fichas.FichaEscrita] | None = None) -> dict:
    """{(bloco, indice): FichaEscrita} das faixas que tem ficha.

    E o que a tela Hoje e o `radar hoje` perguntam, e e barato: so le o
    arquivo e compara titulos - nao conta nada no banco.
    """
    escritas = carregar() if escritas is None else escritas
    saida = {}
    for bloco in blocos:
        for indice, faixa in enumerate(bloco.faixas):
            escrita = fichas.da_faixa(faixa, escritas)
            if escrita is not None:
                saida[(bloco.chave, indice)] = escrita
    return saida


def arvore_das_faixas(blocos, escritas: list[fichas.FichaEscrita] | None = None) -> dict:
    """{(bloco, indice): OndeNaArvore} - o assunto, o subassunto e o elemento
    de cada faixa, para a tela Hoje dizer na propria faixa (decisao 71).

    Barato como o `das_faixas`: so le o arquivo das fichas e os caminhos da
    arvore - nao conta nada.
    """
    from radar.servico import conteudos

    escritas = carregar() if escritas is None else escritas
    caminhos = set(conteudos.caminhos())
    saida = {}
    for bloco in blocos:
        for indice, faixa in enumerate(bloco.faixas):
            if getattr(faixa, "desligada", False):
                continue
            onde = fichas.onde_na_arvore(faixa, fichas.da_faixa(faixa, escritas), caminhos)
            if onde is not None:
                saida[(bloco.chave, indice)] = onde
    return saida


def contexto(hoje: date | None = None, plano=None,
             escritas: list[fichas.FichaEscrita] | None = None) -> fichas.Contexto:
    """Tudo o que as fichas precisam, contado uma vez so."""
    from radar.servico import complementar as servico_complementar
    from radar.servico import conteudos as servico_conteudos
    from radar.servico import cronograma as diario
    from radar.servico import desempenho_por_conteudo as por_conteudo
    from radar.servico import estudo
    from radar.servico import incidencia as servico_incidencia

    hoje = hoje or diario.hoje_local()
    plano = plano or plano_de_estudo.carregar()
    nos = servico_conteudos.nos()
    metas_do_diario = diario.metas_do_plano(plano)

    def dia_montado(data: date):
        # O mesmo dia que a tela Hoje mostra: com o nivel efetivo daquele dia.
        nivel = diario.nivel_do_dia(plano, data, metas_do_diario)
        if nivel is None:
            return None
        return plano_de_estudo.montar_dia(plano, data, nivel.efetivo)

    criar_tabelas()
    with sessao() as s:
        geradas = list(s.scalars(
            select(QuestaoGerada)
            .where(QuestaoGerada.rejeitada.is_(False))
            .where(QuestaoGerada.conteudo.is_not(None))))

    return fichas.Contexto(
        hoje=hoje, plano=plano,
        caminhos=[n.caminho for n in nos],
        niveis={n.caminho: n.nivel for n in nos},
        ocorrencias_alvo=servico_incidencia.ocorrencias(),
        ocorrencias_complementares=servico_incidencia.ocorrencias_complementares(),
        entradas=por_conteudo.entradas(por_conteudo.CICLO, plano, hoje),
        metas=por_conteudo._metas_das_materias(plano),
        fila=estudo.para_revisar(plano, hoje),
        situacoes=estudo.situacoes(plano=plano, hoje=hoje),
        geradas=geradas,
        lei=leis.do_assunto,
        leis_mudadas=leis.fronteira_do_tema,
        minimos_amostra=amostra.carregar(),
        minimos_acervo=incidencia.carregar_minimos(),
        regra=prioridade.carregar(),
        dia_montado=dia_montado,
        refazer=lambda dentro: estudo.refazer_do_escopo(dentro, hoje),
        escritas=carregar() if escritas is None else escritas,
        provas_dos_padroes=servico_complementar.provas_dos_padroes(),
    )


def prioridades(ctx: fichas.Contexto) -> dict:
    """{id da ficha: Prioridade}, ja com a posicao de cada uma."""
    por_id = {e.id: fichas.prioridade_de(e, ctx) for e in ctx.escritas}
    prioridade.ordenar(ctx.escritas, lambda e: por_id[e.id])
    return por_id


def ficha(id_ou_tema: str, data: date | None = None,
          ctx: fichas.Contexto | None = None) -> fichas.FichaDeEstudo | None:
    """A ficha inteira de um tema, ou None se o tema nao tem ficha."""
    ctx = ctx or contexto()
    escrita = achar(id_ou_tema, ctx.escritas)
    if escrita is None:
        return None
    return fichas.montar(escrita, ctx, data, prioridades(ctx)[escrita.id])


@dataclass
class LinhaDaLista:
    """Um tema do cronograma na lista das fichas."""

    tema: fichas.TemaDoPlano
    escrita: fichas.FichaEscrita | None = None
    prioridade: object = None
    alvo: object = None            # incidencia.LinhaDoMapa do escopo
    complementar: object = None    # complementar.LinhaComplementar do escopo

    @property
    def tem_ficha(self) -> bool:
        return self.escrita is not None


def lista(desde: date | None = None,
          ctx: fichas.Contexto | None = None) -> list[LinhaDaLista]:
    """Os temas do cronograma de `desde` em diante (padrao: hoje), com a
    ficha e a prioridade de cada um. Tema sem ficha aparece tambem, para eu
    ver o que falta pedir. A ordem e a do calendario: a prioridade vai na
    linha, e a tela nao se reordena sozinha."""
    ctx = ctx or contexto()
    por_id = prioridades(ctx) if ctx.escritas else {}
    saida = []
    for tema in fichas.temas_do_plano(ctx.plano, desde or ctx.hoje):
        escrita = next((e for e in ctx.escritas
                        if e.chave == fichas.chave_do_tema(tema.tema)
                        and e.materia == tema.materia), None)
        linha = LinhaDaLista(tema=tema, escrita=escrita)
        if escrita is not None:
            dentro = fichas.dentro_de(escrita.nos)
            linha.prioridade = por_id.get(escrita.id)
            linha.alvo = incidencia.linha_do_escopo(
                escrita.id, escrita.tema, dentro, escrita.materia, ctx.ocorrencias_alvo)
            linha.complementar = incidencia.complementar_do_escopo(
                escrita.id, dentro, ctx.ocorrencias_complementares)
        saida.append(linha)
    return saida


def sem_ficha(plano=None, desde: date | None = None,
              escritas: list[fichas.FichaEscrita] | None = None) -> list[fichas.TemaDoPlano]:
    """Os temas do cronograma, de `desde` em diante, que ainda nao tem ficha."""
    from radar.servico import cronograma as diario

    plano = plano or plano_de_estudo.carregar()
    escritas = carregar() if escritas is None else escritas
    ja = {(e.chave, e.materia) for e in escritas}
    return [t for t in fichas.temas_do_plano(plano, desde or diario.hoje_local())
            if (fichas.chave_do_tema(t.tema), t.materia) not in ja]


def conferir(id_ou_tema: str, quando: date | None = None) -> fichas.FichaEscrita:
    """Marca a ficha como conferida por mim. O `modelo` NAO muda: a proposta
    continua sendo de IA, e a data diz que eu li (decisao 16, a mesma da
    conferencia das classificacoes)."""
    from radar.servico import cronograma as diario

    escritas = carregar()
    escrita = achar(id_ou_tema, escritas)
    if escrita is None:
        raise LookupError(f"não há ficha para {id_ou_tema!r}")
    escrita.conferida_em = (quando or diario.hoje_local()).isoformat()
    gravar(escritas)
    return escrita


def importar_respostas(pedidos: list[dict], respostas: list[dict], modelo: str) -> dict:
    """Confere cada ficha da resposta contra o pedido e grava a que presta.

    Recusa, e conta na saida: resposta a pedido que nao existe, a mesma
    resposta duas vezes, ficha sem o objeto, tudo o que o
    `fichas.conferir_escrita` recusa, e a ficha que eu ja conferi - a
    conferencia e minha, e nao se reescreve por cima. A nao conferida e
    substituida pela nova.
    """
    from radar.servico import conteudos as servico_conteudos

    por_id = {p["id"]: p for p in pedidos}
    escritas = carregar()
    por_tema = {e.id: e for e in escritas}
    nos = servico_conteudos.nos()
    caminhos = [n.caminho for n in nos]
    niveis = {n.caminho: n.nivel for n in nos}
    taxonomia = arvore.carregar_taxonomia()
    quando = agora().isoformat()

    gravadas = substituidas = 0
    recusas, vistas = [], set()
    for resposta in respostas:
        pedido = por_id.get(resposta.get("id"))
        if pedido is None:
            recusas.append(f"{resposta.get('id')}: não existe esse pedido no lote")
            continue
        onde = f"{pedido['id']} ({pedido['tema']})"
        if pedido["id"] in vistas:
            recusas.append(f"{onde}: respondido duas vezes")
            continue
        vistas.add(pedido["id"])
        bruta = resposta.get("ficha")
        if not isinstance(bruta, dict):
            recusas.append(f"{onde}: sem o objeto `ficha`")
            continue
        try:
            escrita = fichas.conferir_escrita(
                bruta, tema=pedido["tema"], materia=pedido["materia"],
                caminhos=caminhos, niveis=niveis, taxonomia=taxonomia)
        except fichas.FichaRecusada as erro:
            recusas.append(f"{onde}: {erro}")
            continue
        existente = por_tema.get(escrita.id)
        if existente is not None and existente.materia != escrita.materia:
            recusas.append(f"{onde}: já existe ficha de {existente.materia} com o "
                           f"mesmo endereço ({escrita.id})")
            continue
        if existente is not None and existente.conferida_em:
            recusas.append(f"{onde}: você já conferiu esta ficha em "
                           f"{existente.conferida_em}; ela não é sobrescrita")
            continue
        escrita.modelo, escrita.criado_em = modelo, quando
        if existente is not None:
            substituidas += 1
        por_tema[escrita.id] = escrita
        gravadas += 1

    if gravadas:
        gravar(list(por_tema.values()))
    return {"gravadas": gravadas, "repetidas": 0, "substituidas": substituidas,
            "recusas": recusas}
