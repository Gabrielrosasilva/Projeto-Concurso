"""As fichas de estudo a partir do banco e dos arquivos (Etapa 6B).

A ficha e montada no `radar.fichas` e a prioridade no `radar.prioridade`, os
dois puros. Aqui se junta o que eles precisam - a incidencia do alvo e do
complementar, o meu desempenho, a fila de revisao, as geradas, o cronograma -
e se le e grava o `data/fichas.json`, o registro versionado do que foi escrito
(o banco nao guarda ficha: ela e texto meu e do Claude Code, como o macete).
"""
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select

from radar import amostra, config, fichas, incidencia, leis, prioridade
from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, agora


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
    do_dia = [f for bloco in blocos for f in bloco.faixas]
    saida = {}
    for bloco in blocos:
        for indice, faixa in enumerate(bloco.faixas):
            escrita = fichas.da_faixa_no_dia(faixa, do_dia, escritas)
            if escrita is not None:
                saida[(bloco.chave, indice)] = escrita
    return saida


def caiu_das_faixas(blocos, escritas: list[fichas.FichaEscrita] | None = None) -> dict:
    """{(bloco, indice): incidencia.CaiuNoAlvo} das faixas que tem ficha: o
    "caiu ou nao caiu" na propria faixa (R1). So o alvo - 170 questoes -, e
    uma leitura por tela."""
    from radar.servico import incidencia as servico_incidencia

    por_faixa = das_faixas(blocos, escritas)
    if not por_faixa:
        return {}
    ocorrencias = servico_incidencia.ocorrencias()
    minimo = incidencia.carregar_minimos().provas
    por_tema: dict[str, object] = {}
    saida = {}
    for chave, escrita in por_faixa.items():
        if escrita.id not in por_tema:
            por_tema[escrita.id] = fichas.caiu_do_tema(escrita, ocorrencias, minimo)
        saida[chave] = por_tema[escrita.id]
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
    do_dia = [f for bloco in blocos for f in bloco.faixas]
    saida = {}
    for bloco in blocos:
        for indice, faixa in enumerate(bloco.faixas):
            if getattr(faixa, "desligada", False):
                continue
            onde = fichas.onde_na_arvore(
                faixa, fichas.da_faixa_no_dia(faixa, do_dia, escritas), caminhos)
            if onde is not None:
                saida[(bloco.chave, indice)] = onde
    return saida


def codigos_respondidos() -> set[str]:
    """Os codigos citaveis ("2019-q51", "FEPESE-2024-q8") das questoes reais
    que eu ja respondi no radar, com qualquer letra (P05, decisao 148). A
    gerada nao entra: ela nao tem codigo de prova."""
    criar_tabelas()
    with sessao() as s:
        questoes = s.execute(
            select(QuestaoDeProva.ano, QuestaoDeProva.numero, QuestaoDeProva.evidencia)
            .join(RespostaDeSimulado, RespostaDeSimulado.questao_id == QuestaoDeProva.id)
            .where(RespostaDeSimulado.gerada.is_not(True))
            .where(RespostaDeSimulado.escolhida.is_not(None))
            .distinct()).all()
    saida = set()
    for ano, numero, evidencia in questoes:
        codigo = f"{ano or 's/a'}-q{numero}" if numero else f"{ano or 's/a'}"
        saida.add(fichas.PREFIXO_DO_COMPLEMENTAR + codigo if evidencia == "complementar"
                  else codigo)
    return saida


def contexto(hoje: date | None = None, plano=None,
             escritas: list[fichas.FichaEscrita] | None = None) -> fichas.Contexto:
    """Tudo o que as fichas precisam, contado uma vez so."""
    from radar.servico import cartoes, manual
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
        explicacoes=manual.carregar_explicacoes(),
        macetes=[m for m in manual.carregar_macetes() if cartoes._macete_aparece(m)],
        mudancas_da_questao=leis.mudancas_da_questao,
        minimo_provas=incidencia.carregar_minimos().provas,
        respondidos=codigos_respondidos(),
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
    caiu: object = None            # incidencia.CaiuNoAlvo (R1)

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
            linha.caiu = fichas.caiu_do_tema(escrita, ctx.ocorrencias_alvo,
                                             ctx.minimo_provas)
        saida.append(linha)
    return saida


@dataclass
class CartaoDoTema:
    """Um tema num bloco do dia, na aba Fichas (R1): o mesmo cartao em todo
    bloco em que o tema aparece."""

    escrita: fichas.FichaEscrita
    rotulos: list                  # as faixas do tema neste bloco: "Teoria", "R+7"...
    onde: object = None            # fichas.OndeNaArvore
    caiu: object = None            # incidencia.CaiuNoAlvo
    complementar: object = None    # complementar.LinhaComplementar


@dataclass
class BlocoDasFichas:
    chave: str
    nome: str
    cartoes: list
    #: As faixas com materia que ainda nao tem ficha: (rotulo, titulo).
    sem_ficha: list


@dataclass
class FichasDoDia:
    data: date
    blocos: list
    anterior: date | None = None
    proximo: date | None = None
    #: R2: os resumos dos temas do dia (ResumosDoDia), para o botao do cartao.
    resumos: object = None

    def resumo_do(self, escrita) -> list:
        """[ResumoNaTela] do tema do cartao, para o botao (lista de um)."""
        if self.resumos is None:
            return []
        ident = _id_na_tela(escrita.id)
        return [self.resumos.temas[ident]] if ident in self.resumos.temas else []

    @property
    def vazio(self) -> bool:
        return not any(b.cartoes or b.sem_ficha for b in self.blocos)


def do_dia(data: date | None = None, ctx: fichas.Contexto | None = None) -> FichasDoDia:
    """As fichas do dia, separadas por bloco (Manha, Noite, Depois das 22h),
    cada tema uma vez por bloco. O dia e o do arquivo (o nivel nao muda o
    tema de faixa nenhuma). A lei seca leva o tema da teoria do dia."""
    from radar.servico import conteudos

    ctx = ctx or contexto()
    data = data or ctx.hoje
    dia = ctx.plano.dia(data)
    datas = sorted(d.data for d in ctx.plano.dias)
    anterior = next((d for d in reversed(datas) if d < data), None)
    proximo = next((d for d in datas if d > data), None)
    if dia is None:
        return FichasDoDia(data, [], anterior, proximo)

    caminhos = set(conteudos.caminhos())
    do_dia_inteiro = [f for chave in plano_de_estudo.BLOCOS for f in getattr(dia, chave)]
    caiu_por_tema: dict[str, object] = {}
    blocos = []
    for chave in plano_de_estudo.BLOCOS:
        bloco_do_plano = ctx.plano.blocos.get(chave)
        cartoes: dict[str, CartaoDoTema] = {}
        sem = []
        for faixa in getattr(dia, chave):
            if faixa.desligada or not faixa.materia:
                continue
            escrita = fichas.da_faixa_no_dia(faixa, do_dia_inteiro, ctx.escritas)
            rotulo = fichas._rotulo_da_faixa(faixa)
            if escrita is None:
                sem.append((rotulo, faixa.titulo))
                continue
            if escrita.id not in cartoes:
                if escrita.id not in caiu_por_tema:
                    caiu_por_tema[escrita.id] = fichas.caiu_do_tema(
                        escrita, ctx.ocorrencias_alvo, ctx.minimo_provas)
                cartoes[escrita.id] = CartaoDoTema(
                    escrita=escrita, rotulos=[],
                    onde=fichas.onde_na_arvore(faixa, escrita, caminhos),
                    caiu=caiu_por_tema[escrita.id],
                    complementar=incidencia.complementar_do_escopo(
                        escrita.id, fichas.dentro_de(escrita.nos),
                        ctx.ocorrencias_complementares))
            if rotulo not in cartoes[escrita.id].rotulos:
                cartoes[escrita.id].rotulos.append(rotulo)
        blocos.append(BlocoDasFichas(
            chave=chave, nome=bloco_do_plano.nome if bloco_do_plano else chave,
            cartoes=list(cartoes.values()), sem_ficha=sem))
    from types import SimpleNamespace

    resumos = resumos_do_dia(
        [SimpleNamespace(chave=c, faixas=getattr(dia, c)) for c in plano_de_estudo.BLOCOS],
        data, ctx.plano, ctx.escritas, ctx.ocorrencias_alvo, ctx.ocorrencias_complementares)
    return FichasDoDia(data, blocos, anterior, proximo, resumos)


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


# --- o resumo do tema (R2) -----------------------------------------------------------

def codigos_do_tema(ficha: fichas.FichaDeEstudo) -> dict:
    """{"2019-q51": "c"}: as questoes reais que o resumo do tema pode citar -
    os exemplos do alvo e as do complementar -, com o gabarito oficial. Um
    codigo que aponta duas questoes diferentes (dois cadernos do mesmo ano,
    com gabarito diferente) fica de fora: a citacao seria ambigua."""
    vistos: dict[str, set] = {}
    for q in list(ficha.exemplos) + list(ficha.questoes_reais):
        vistos.setdefault(fichas.codigo_citavel(q), set()).add((q.resposta or "").lower())
    return {codigo: next(iter(letras)) for codigo, letras in vistos.items()
            if len(letras) == 1 and next(iter(letras))}


def exigencias_do_resumo(ficha: fichas.FichaDeEstudo) -> dict:
    """O que a conferencia do resumo exige deste tema: os codigos, se caiu,
    se o basico e obrigatorio e se a materia pede o dispositivo."""
    caiu = ficha.caiu
    return {"codigos": codigos_do_tema(ficha), "caiu": bool(caiu and caiu.caiu),
            "basico_obrigatorio": bool(caiu and caiu.classe == incidencia.BASICO),
            "exige_artigo": leis.exige_artigo(ficha.materia)}


def importar_resumos(pedidos: list[dict], respostas: list[dict], modelo: str) -> dict:
    """Confere cada resumo contra o pedido e grava o que presta, dentro da
    ficha do tema. Recusa (e conta): pedido que nao existe, resposta repetida,
    ficha que sumiu, o resumo que eu ja conferi, e tudo o que o
    `fichas.conferir_resumo` recusa."""
    por_id = {p["id"]: p for p in pedidos}
    escritas = carregar()
    por_ficha = {e.id: e for e in escritas}
    quando = agora().isoformat()
    gravadas, recusas, vistas = 0, [], set()
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
        escrita = por_ficha.get(pedido["ficha"])
        if escrita is None:
            recusas.append(f"{onde}: a ficha do tema não existe mais")
            continue
        if escrita.resumo and escrita.resumo.get("conferido_em"):
            recusas.append(f"{onde}: você já conferiu este resumo em "
                           f"{escrita.resumo['conferido_em']}; ele não é sobrescrito")
            continue
        try:
            partes = fichas.conferir_resumo(
                resposta.get("resumo"), codigos=pedido["codigos"], caiu=pedido["caiu"],
                basico_obrigatorio=pedido.get("basico_obrigatorio"),
                exige_artigo=pedido["exige_artigo"])
        except fichas.FichaRecusada as erro:
            recusas.append(f"{onde}: {erro}")
            continue
        escrita.resumo = {"partes": partes, "modelo": modelo, "criado_em": quando,
                          "conferido_em": None}
        gravadas += 1
    if gravadas:
        gravar(escritas)
    return {"gravadas": gravadas, "repetidas": 0, "recusas": recusas}


def conferir_resumo(id_ou_tema: str, quando: date | None = None) -> fichas.FichaEscrita:
    """Marca o resumo do tema como conferido por mim. O `modelo` nao muda."""
    from radar.servico import cronograma as diario

    escritas = carregar()
    escrita = achar(id_ou_tema, escritas)
    if escrita is None:
        raise LookupError(f"não há ficha para {id_ou_tema!r}")
    if not escrita.resumo:
        raise LookupError(f"o tema {escrita.tema!r} ainda não tem resumo escrito")
    escrita.resumo["conferido_em"] = (quando or diario.hoje_local()).isoformat()
    gravar(escritas)
    return escrita


def verificar_resumos(ctx: fichas.Contexto | None = None) -> list[tuple[str, str]]:
    """O verificador automatico (item 4e): cada resumo gravado passa de NOVO
    pela conferencia, contra o acervo de hoje - a questao citada ainda e do
    tema e tem o mesmo gabarito, o padrao ainda cita questao, o basico ainda
    vale. Devolve [(tema, problema)]; vazio, nenhum."""
    ctx = ctx or contexto()
    problemas = []
    for escrita in ctx.escritas:
        if not escrita.resumo:
            continue
        montada = fichas.montar(escrita, ctx)
        exige = exigencias_do_resumo(montada)
        try:
            fichas.conferir_resumo({"partes": escrita.resumo.get("partes") or {}}, **exige)
        except fichas.FichaRecusada as erro:
            problemas.append((escrita.tema, str(erro)))
    return problemas


# --- o botao "Resumo" das faixas (R2) -------------------------------------------------

@dataclass
class ResumoNaTela:
    """O resumo de um tema, como a janela por cima da pagina mostra."""

    id: str
    tema: str
    materia: str
    resumo: dict | None = None
    caiu: object = None            # incidencia.CaiuNoAlvo (a parte 1, na hora)
    complementar: str | None = None
    tem_ficha: bool = True
    ficha_id: str | None = None

    @property
    def escrito(self) -> bool:
        return bool(self.resumo and self.resumo.get("partes"))

    @property
    def conferido(self) -> str | None:
        return (self.resumo or {}).get("conferido_em")

    @property
    def procedencia(self) -> str:
        return (self.resumo or {}).get("modelo") or ""

    @property
    def partes(self) -> list:
        """[(chave, nome, frases)], na ordem da tela, so as que tem frase."""
        escritas = (self.resumo or {}).get("partes") or {}
        return [(chave, nome, escritas[chave]) for chave, nome in fichas.PARTES_DO_RESUMO
                if escritas.get(chave)]


@dataclass
class ResumosDoDia:
    #: {(bloco, indice): [id do tema]} - um tema, ou a lista da faixa com varios.
    por_faixa: dict
    #: {id: ResumoNaTela}, cada tema uma vez, na ordem em que aparece.
    temas: dict
    #: Os codigos das questoes reais ja respondidas no radar: a letra das
    #: outras fica escondida na janela (P05, decisao 148).
    respondidos: set = field(default_factory=set)

    def da_faixa(self, bloco: str, indice: int) -> list:
        return [self.temas[i] for i in self.por_faixa.get((bloco, indice), [])]


#: As faixas sem materia que cobrem varios temas, e de onde vem a lista.
TIPOS_DE_VARIOS_TEMAS = ("correcao", "revisao_semanal")
#: As faixas que medem sem consulta: nao tem botao de resumo (decisao 136).
TIPOS_SEM_CONSULTA = ("simulado", "diagnostico")


def _id_na_tela(texto: str) -> str:
    return "resumo-" + fichas.id_do_tema(texto)


def resumos_do_dia(blocos, data: date, plano=None, escritas=None,
                   ocorrencias=None, complementares=None) -> ResumosDoDia:
    """O que o botao "Resumo" de cada faixa abre (R2). Regras:
    - faixa de um tema (teoria, lei seca, Portugues, Raciocinio, questoes,
      R+7, R+30, bonus com tema): o resumo daquele tema;
    - a correcao: os temas das faixas do dia; a revisao semanal: os temas
      estudados de segunda ate o dia; a revisao mista (o R+7 dos
      diagnosticos): os das materias dos diagnosticos do dia de origem;
    - o simulado e o diagnostico nao tem botao: medem sem consulta, e o
      resumo cita a questao real com o gabarito (decisao 136);
    - a pausa nao tem botao; faixa com materia e sem ficha diz que o resumo
      nao foi escrito.
    """
    from datetime import timedelta

    from radar.servico import incidencia as servico_incidencia

    plano = plano or plano_de_estudo.carregar()
    escritas = carregar() if escritas is None else escritas
    if ocorrencias is None:
        ocorrencias = servico_incidencia.ocorrencias()
    if complementares is None:
        complementares = servico_incidencia.ocorrencias_complementares()
    minimo = incidencia.carregar_minimos().provas
    temas: dict[str, ResumoNaTela] = {}

    def do_tema(escrita) -> str:
        ident = _id_na_tela(escrita.id)
        if ident not in temas:
            temas[ident] = ResumoNaTela(
                id=ident, tema=escrita.tema, materia=escrita.materia,
                resumo=escrita.resumo, ficha_id=escrita.id,
                caiu=fichas.caiu_do_tema(escrita, ocorrencias, minimo),
                complementar=(incidencia.complementar_do_escopo(
                    escrita.id, fichas.dentro_de(escrita.nos), complementares).frase
                    if escrita.nos else None))
        return ident

    def sem_ficha(faixa) -> str:
        ident = _id_na_tela(f"{faixa.materia}-{faixa.titulo}")
        temas.setdefault(ident, ResumoNaTela(id=ident, tema=faixa.titulo,
                                             materia=faixa.materia, tem_ficha=False))
        return ident

    estudados = []      # (data do estudo, escrita)
    for tema in fichas.temas_do_plano(plano):
        estudo = tema.estudo()
        escrita = next((e for e in escritas if e.chave == fichas.chave_do_tema(tema.tema)
                        and e.materia == tema.materia), None)
        if estudo is not None and escrita is not None:
            estudados.append((estudo.data, escrita))

    def estudados_em(desde: date, ate: date, materias=None) -> list[str]:
        return [do_tema(e) for d, e in sorted(estudados, key=lambda x: x[0])
                if desde <= d <= ate and (not materias or e.materia in materias)]

    do_dia = [f for bloco in blocos for f in bloco.faixas]
    por_faixa: dict = {}
    ids_do_dia: list[str] = []
    varios = []
    for bloco in blocos:
        for indice, faixa in enumerate(bloco.faixas):
            if getattr(faixa, "desligada", False) or faixa.tipo == "pausa":
                continue
            if faixa.tipo in TIPOS_SEM_CONSULTA:
                continue
            mista = bool(faixa.materia) and plano.e_mista(faixa.materia)
            if faixa.tipo in TIPOS_DE_VARIOS_TEMAS or mista:
                varios.append((bloco.chave, indice, faixa, mista))
            elif faixa.materia:
                escrita = fichas.da_faixa_no_dia(faixa, do_dia, escritas)
                ident = do_tema(escrita) if escrita is not None else sem_ficha(faixa)
                por_faixa[(bloco.chave, indice)] = [ident]
                if escrita is not None and ident not in ids_do_dia:
                    ids_do_dia.append(ident)

    inicio = plano.inicio
    for chave, indice, faixa, mista in varios:
        if faixa.tipo == "correcao":
            lista = list(ids_do_dia)
        elif faixa.tipo == "revisao_semanal":
            lista = estudados_em(data - timedelta(days=data.weekday()), data)
        else:
            origem = plano.dia(date.fromisoformat(str(faixa.origem))) if faixa.origem else None
            materias = {f.materia for f in (origem.faixas() if origem else [])
                        if f.tipo == "diagnostico" and f.materia}
            lista = estudados_em(inicio, data, materias or None)
        por_faixa[(chave, indice)] = list(dict.fromkeys(lista))
    return ResumosDoDia(por_faixa=por_faixa, temas=temas, respondidos=codigos_respondidos())


def levar_no(duplicado: str, mantido: str) -> int:
    """Depois de `servico.conteudos.juntar`: a ficha que apontava o no
    duplicado (ou um no abaixo dele) passa a apontar o mantido, sem repetir
    no. Devolve quantas fichas mudaram. O texto escrito nao muda: so o
    caminho, que e o vinculo, e a ficha continua por conferir como estava."""
    from radar.servico.conteudos import novo_caminho

    escritas = carregar()
    mudaram = 0
    for escrita in escritas:
        novos = []
        for no in escrita.nos:
            caminho = novo_caminho(no, duplicado, mantido)
            if caminho not in novos:
                novos.append(caminho)
        # O no levado pode cair dentro de outro no da mesma ficha (o art. 75,
        # que foi para "Orgaos da execucao penal", ficha que ja tinha o
        # subassunto): fica so o de cima, senao a resposta conta duas vezes.
        novos = [no for no in novos
                 if not any(no.startswith(outro + " > ") for outro in novos)]
        if novos != escrita.nos:
            escrita.nos = novos
            mudaram += 1
    if mudaram:
        gravar(escritas)
    return mudaram
