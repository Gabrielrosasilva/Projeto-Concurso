"""A ficha de estudo: cada tarefa do cronograma como instrumento de estudo.

O novo.md pede, na secao 11, uma estrutura UNICA para toda tarefa do
cronograma: o que estudar, a parte exata, onde, como procurar, o que entender e
memorizar, as pegadinhas, como a FEPESE cobrou, as questoes reais, quantas
questoes fazer e quando revisar. Este modulo e essa estrutura - a
`FichaDeEstudo` -, e e a mesma para a tela Hoje, o `radar hoje` e o `radar
fichas`. Puro: recebe o que o banco ja contou (o `Contexto`) e devolve a ficha,
sem falar com banco nem com rede.

Cada campo tem UMA origem, e ela vai junto do dado (secao 20):

  * **plano** (📌) - o que eu planejei no config/cronograma.yml: as faixas do
    tema, os artigos-chave do dia, o numero de questoes;
  * **oficial** (🟢) - o texto da lei, pelo config/leis.yml (so o link);
  * **acervo** (🔵) - o que as provas mostram: incidencia, padroes,
    pegadinhas e questoes reais, com a amostra e o alvo separado do
    complementar (regra inviolavel 1);
  * **automatico** (🟡) - o que o sistema calcula de mim: desempenho,
    prioridade, fila de revisao;
  * **ia** (🟣) - o que o Claude Code ESCREVEU (data/fichas.json): o que ler,
    como pesquisar, o que entender e memorizar, confusoes comuns. Sempre com
    a procedencia (decisao 9 da Etapa 0), e conferivel por mim.

O TEMA e a chave. A ficha vale para toda faixa daquele tema - teoria,
fixacao, aprendizagem, R+7, R+30 e o Plano B -, reconhecida pelo titulo
EXATO, sem o prefixo ("Fixação: ", "R+7: "...). Nada e aproximado, e o
cronograma.yml nao muda por causa dela.

O ESCOPO e a lista de nos que a ficha cobre (`nos`). "Art. 5º, caput e
incisos I a XVI" nao e um no so: sao tres subassuntos de um assunto e o caput,
que no edital e outro assunto. Ficha cujo tema nao tem no que sirva fica com a
lista vazia - e diz isso -, em vez de ganhar um no inventado (regra 9).
"""
import re
from dataclasses import asdict, dataclass, field
from datetime import date

from radar import conteudos as arvore
from radar import cronograma as plano_de_estudo
from radar import incidencia
from radar import prioridade as regra_de_prioridade
# As origens (secao 20), mais a do plano, e a frase da regra inviolavel 4: as
# mesmas do resto do site, que desde a Etapa 7A moram todas no origem.py.
from radar.origem import ACERVO, AUTOMATICO, FRASE_SEM_EVIDENCIA, IA, OFICIAL, PLANO
from radar.regioes import normalizar

#: Campo escrito que ainda nao foi escrito. Nao e a frase do acervo: "nao ha
#: evidencia no acervo" diria uma coisa sobre as provas, e o que falta aqui e
#: texto, nao prova.
FRASE_SEM_TEXTO = "Ainda não há texto escrito para este campo da ficha."

#: Os campos da secao 11 do novo.md e o nome deles aqui. E a estrutura unica:
#: o teste confere que a ficha tem todos.
CAMPOS_DA_SECAO_11 = {
    "subject": "materia",
    "topic": "assunto",
    "subtopic": "subassunto",
    "specific_element": "elemento",
    "element_type": "tipo_elemento",
    "why_now": "por_que_agora",
    "source_material": "fonte",
    "read_exactly": "ler_exatamente",
    "search_queries": "como_pesquisar",
    "must_understand": "entender",
    "must_memorize": "memorizar",
    "fepese_traps": "pegadinhas_do_acervo",
    "fepese_pattern": "padroes_do_alvo",
    "related_real_questions": "questoes_reais",
    "practice_target": "meta_de_questoes",
    "review_trigger": "quando_revisar",
}

#: A origem de cada campo. O `fonte` e o unico que muda (oficial quando ha
#: lei, ia quando a ficha sugere a fonte), e por isso ele carrega a dele.
ORIGEM_DO_CAMPO = {
    # A materia e a da faixa (o plano). O assunto e o subassunto sao nomes do
    # edital, mas a ESCOLHA deles para o tema e da ficha escrita - por isso 🟣.
    "materia": PLANO, "assunto": IA, "subassunto": IA,
    "elemento": IA, "tipo_elemento": IA,
    "por_que_agora": AUTOMATICO,
    "ler_exatamente": IA, "artigos_chave": PLANO,
    "como_pesquisar": IA, "entender": IA, "memorizar": IA,
    "pegadinhas_do_acervo": ACERVO, "pegadinhas_escritas": IA,
    "padroes_do_alvo": ACERVO, "linha_complementar": ACERVO,
    "questoes_reais": ACERVO,
    "meta_de_questoes": PLANO,
    "quando_revisar": AUTOMATICO, "refazer": AUTOMATICO,
    "desempenho": AUTOMATICO, "geradas": IA,
}

#: Os prefixos que o cronograma poe no titulo das faixas de um mesmo tema. A
#: lista e fechada de proposito: um prefixo novo no YAML tem de entrar aqui, e
#: nao ser adivinhado.
PREFIXOS_DO_TEMA = ("Fixação: ", "Aprendizagem: ", "R+7: ", "R+30: ",
                    "Artigos-chave: ", "Questões de prova: ")

#: As faixas que DIZEM o tema: a de estudo. As outras (questoes, revisao)
#: herdam o tema dela pelo titulo.
TIPOS_QUE_DIZEM_O_TEMA = ("teoria", "portugues", "raciocinio")

#: Texto escrito que fala como previsao, ou que afirma costume da banca sem a
#: amostra. O padrao da banca sai do ACERVO, com o numero; texto de IA nao o
#: afirma (regras inviolaveis 2 e 3).
PREVISAO = re.compile(
    r"(?i)vai cair|certamente|com certeza|sempre cobra|cai sempre|caira\b|cairá"
    r"|fepese\s+(sempre|costuma|adora|gosta|prefere|cobra muito)")


class FichaRecusada(ValueError):
    """Uma ficha escrita que nao entra. A mensagem diz por que."""


# --- o tema ---------------------------------------------------------------------

def tema_da_faixa(titulo: str | None, materia: str | None = None) -> str:
    """O tema de uma faixa: o titulo sem os prefixos do cronograma.

    "R+7: Art. 5º, caput e incisos I a XVI" -> "Art. 5º, caput e incisos I a
    XVI". O sabado de Raciocinio escreve a materia na frente ("Raciocínio
    Lógico: princípios de contagem"), e ela sai tambem.
    """
    texto = " ".join((titulo or "").split())
    mudou = True
    while mudou:
        mudou = False
        for prefixo in PREFIXOS_DO_TEMA:
            if texto.startswith(prefixo):
                texto = texto[len(prefixo):].strip()
                mudou = True
    if materia:
        cabeca = materia + ":"
        if normalizar(texto[:len(cabeca)]) == normalizar(cabeca):
            texto = texto[len(cabeca):].strip()
    return texto


def chave_do_tema(tema: str | None) -> str:
    """O tema para comparar: sem acento, sem caixa, sem espaco sobrando."""
    return normalizar(tema or "")


def id_do_tema(tema: str) -> str:
    """O endereco da ficha: "Art. 5º, caput e incisos I a XVI" ->
    "art-5o-caput-e-incisos-i-a-xvi". Vai na URL, e por isso nao e o `tema`:
    `?tema=` ja e o tema claro/escuro da web."""
    return re.sub(r"[^a-z0-9]+", "-", chave_do_tema(tema)).strip("-")


# --- a parte escrita (data/fichas.json) ---------------------------------------------

@dataclass
class FichaEscrita:
    """O que o Claude Code escreveu de um tema (ou eu, a mao). Sempre 🟣.

    `nos` e o escopo: os nos da arvore que o tema cobre, de onde saem as
    questoes reais, a incidencia, os padroes e o meu desempenho. A escolha dos
    nos e julgamento, e por isso vem com o porque (`por_que_estes_nos`) e
    espera a minha conferencia (`conferida_em`).
    """

    tema: str
    materia: str
    assunto: str | None = None
    subassunto: str | None = None
    elemento: str | None = None
    tipo_elemento: str | None = None
    nos: list = field(default_factory=list)
    por_que_estes_nos: str = ""
    ler_exatamente: str = ""
    como_pesquisar: list = field(default_factory=list)
    entender: list = field(default_factory=list)
    memorizar: list = field(default_factory=list)
    pegadinhas: list = field(default_factory=list)
    fonte_sugerida: str | None = None
    #: A procedencia: quem escreveu e quando. Sem ela a ficha nao e lida.
    modelo: str = ""
    criado_em: str = ""
    #: Quando eu conferi (AAAA-MM-DD). Conferir nao reescreve o `modelo`: a
    #: proposta continua sendo de IA, e e isso que deixa auditavel.
    conferida_em: str | None = None

    @property
    def id(self) -> str:
        return id_do_tema(self.tema)

    @property
    def chave(self) -> str:
        return chave_do_tema(self.tema)

    def para_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def de_dict(cls, bruto: dict) -> "FichaEscrita":
        campos = {k: bruto.get(k) for k in cls.__dataclass_fields__ if k in bruto}
        for lista in ("nos", "como_pesquisar", "entender", "memorizar", "pegadinhas"):
            campos[lista] = list(campos.get(lista) or [])
        return cls(**campos)


def _texto(valor) -> str:
    return " ".join(str(valor or "").split())


def _lista(valor) -> list[str]:
    if not isinstance(valor, list):
        return []
    return [t for t in (_texto(v) for v in valor) if t]


def conferir_escrita(bruta: dict, *, tema: str, materia: str, caminhos,
                     niveis: dict[str, str], taxonomia) -> FichaEscrita:
    """A ficha escrita, conferida. Levanta `FichaRecusada` com o motivo.

    As recusas, e cada uma segura uma regra:
      * de outro tema ou de outra materia que nao a do pedido;
      * assunto ou subassunto que a arvore nao tem (nada e aproximado);
      * tipo de elemento fora do config/taxonomia.yml;
      * no que nao existe, fora da materia, a propria materia (materia inteira
        nao e tarefa: e simulado), repetido, ou um dentro do outro (a mesma
        resposta contaria duas vezes);
      * sem o porque dos nos, sem o que ler, sem como pesquisar, sem o que
        entender ou memorizar - a ficha tem de ter comeco, meio e fim (§12);
      * texto com cara de previsao ou que afirma costume da banca sem amostra.
    """
    if chave_do_tema(bruta.get("tema") or tema) != chave_do_tema(tema):
        raise FichaRecusada(f"a ficha é de outro tema ({bruta.get('tema')!r}), "
                            f"e o pedido era {tema!r}")
    caminhos = set(caminhos)
    if materia not in caminhos or niveis.get(materia) != "materia":
        raise FichaRecusada(f"a matéria {materia!r} não está na árvore")

    assunto = _texto(bruta.get("assunto")) or None
    subassunto = _texto(bruta.get("subassunto")) or None
    if assunto:
        no_do_assunto = arvore.caminho(materia, assunto)
        if niveis.get(no_do_assunto) != "assunto":
            raise FichaRecusada(f"o assunto {assunto!r} não existe em {materia!r}")
        if subassunto:
            no_do_sub = arvore.caminho(no_do_assunto, subassunto)
            if niveis.get(no_do_sub) != "subassunto":
                raise FichaRecusada(
                    f"o subassunto {subassunto!r} não existe em {no_do_assunto!r}")
    elif subassunto:
        raise FichaRecusada("subassunto sem assunto: diga o assunto também")

    tipo = _texto(bruta.get("tipo_elemento")) or None
    if tipo and tipo not in taxonomia.elementos_da_materia(materia):
        raise FichaRecusada(
            f"{tipo!r} não é tipo de elemento de {materia} no config/taxonomia.yml")

    nos = _lista(bruta.get("nos"))
    vistos = []
    for no in nos:
        if no not in caminhos:
            raise FichaRecusada(f"o nó {no!r} não está na árvore")
        if no == materia:
            raise FichaRecusada(
                "a matéria inteira não é escopo de ficha: escolha os nós do tema")
        if not no.startswith(materia + arvore.SEPARADOR):
            raise FichaRecusada(f"o nó {no!r} é de outra matéria, e não de {materia!r}")
        if no in vistos:
            raise FichaRecusada(f"o nó {no!r} aparece duas vezes")
        vistos.append(no)
    for no in vistos:
        for outro in vistos:
            if no != outro and no.startswith(outro + arvore.SEPARADOR):
                raise FichaRecusada(
                    f"o nó {no!r} está dentro de {outro!r}: a mesma resposta "
                    f"contaria duas vezes")

    escrita = FichaEscrita(
        tema=tema, materia=materia, assunto=assunto, subassunto=subassunto,
        elemento=_texto(bruta.get("elemento")) or None, tipo_elemento=tipo,
        nos=vistos,
        por_que_estes_nos=_texto(bruta.get("por_que_estes_nos")),
        ler_exatamente=_texto(bruta.get("ler_exatamente")),
        como_pesquisar=_lista(bruta.get("como_pesquisar")),
        entender=_lista(bruta.get("entender")),
        memorizar=_lista(bruta.get("memorizar")),
        pegadinhas=_lista(bruta.get("pegadinhas")),
        fonte_sugerida=_texto(bruta.get("fonte_sugerida")) or None,
    )
    if not escrita.por_que_estes_nos:
        raise FichaRecusada("sem o porquê dos nós (ou de não haver nó que sirva)")
    if len(escrita.ler_exatamente) < 10:
        raise FichaRecusada("sem o que ler exatamente")
    for campo in ("como_pesquisar", "entender", "memorizar"):
        if not getattr(escrita, campo):
            raise FichaRecusada(f"sem {campo.replace('_', ' ')}")

    textos = ([escrita.elemento or "", escrita.por_que_estes_nos,
               escrita.ler_exatamente, escrita.fonte_sugerida or ""]
              + escrita.como_pesquisar + escrita.entender + escrita.memorizar
              + escrita.pegadinhas)
    for texto in textos:
        achado = PREVISAO.search(texto)
        if achado:
            raise FichaRecusada(
                f"texto com cara de previsão ou de costume da banca sem amostra "
                f"({achado.group(0)!r}): o padrão da FEPESE sai do acervo, com o "
                f"número")
    return escrita


# --- as faixas de um tema no cronograma -------------------------------------------

@dataclass(frozen=True)
class FaixaDoTema:
    """Uma faixa do cronograma que e deste tema, e onde ela esta."""

    data: date
    bloco: str
    indice: int
    faixa: object


def da_faixa(faixa, escritas: list[FichaEscrita]) -> FichaEscrita | None:
    """A ficha desta faixa, pelo titulo exato sem prefixo e pela materia.

    Faixa sem materia (pausa, correcao, simulado misto) nao tem ficha. Faixa
    desligada (o Anki com `anki: desativado`) tambem nao.
    """
    if faixa is None or getattr(faixa, "desligada", False):
        return None
    materia = getattr(faixa, "materia", None)
    if not materia:
        return None
    chave = chave_do_tema(tema_da_faixa(faixa.titulo, materia))
    for escrita in escritas:
        if escrita.chave == chave and escrita.materia == materia:
            return escrita
    return None


def faixas_do_tema(plano, tema: str, materia: str) -> list[FaixaDoTema]:
    """Todas as faixas do plano que sao deste tema, na ordem do calendario.

    Le o plano como esta no arquivo (sem a rampa do nivel): aqui so interessa
    ONDE o tema aparece. O numero de questoes do dia sai do dia montado.
    """
    chave = chave_do_tema(tema)
    saida = []
    for dia in plano.dias:
        for bloco in plano_de_estudo.BLOCOS:
            for indice, faixa in enumerate(getattr(dia, bloco)):
                if faixa.desligada or faixa.materia != materia:
                    continue
                if chave_do_tema(tema_da_faixa(faixa.titulo, materia)) == chave:
                    saida.append(FaixaDoTema(dia.data, bloco, indice, faixa))
    return saida


@dataclass
class TemaDoPlano:
    """Um tema de estudo do cronograma, com as faixas dele."""

    tema: str
    materia: str
    faixas: list[FaixaDoTema] = field(default_factory=list)

    @property
    def id(self) -> str:
        return id_do_tema(self.tema)

    def proxima(self, hoje: date) -> date | None:
        """A primeira data do tema de hoje em diante. None se ja passou toda."""
        return next((f.data for f in self.faixas if f.data >= hoje), None)

    def estudo(self) -> FaixaDoTema | None:
        """A faixa de estudo (teoria, portugues, raciocinio) do tema."""
        return next((f for f in self.faixas
                     if f.faixa.tipo in TIPOS_QUE_DIZEM_O_TEMA), None)


def temas_do_plano(plano, desde: date | None = None) -> list[TemaDoPlano]:
    """Os temas de estudo do cronograma que aparecem de `desde` em diante.

    Um tema nasce de uma faixa de ESTUDO (teoria, portugues, raciocinio); as
    faixas de questoes e as revisoes R+7/R+30 entram nele pelo titulo. Por
    isso um tema estudado antes de `desde` entra quando a revisao dele ainda
    vem: o "Art. 5º, caput e incisos I a XVI" foi de 29/09, e volta em 06/10
    e em 29/10.
    """
    temas: dict[tuple, TemaDoPlano] = {}
    for dia in plano.dias:
        for bloco in plano_de_estudo.BLOCOS:
            for faixa in getattr(dia, bloco):
                if faixa.tipo not in TIPOS_QUE_DIZEM_O_TEMA or not faixa.materia:
                    continue
                tema = tema_da_faixa(faixa.titulo, faixa.materia)
                chave = (chave_do_tema(tema), faixa.materia)
                temas.setdefault(chave, TemaDoPlano(tema, faixa.materia))
    saida = []
    for tema in temas.values():
        tema.faixas = faixas_do_tema(plano, tema.tema, tema.materia)
        if desde is None or any(f.data >= desde for f in tema.faixas):
            saida.append(tema)
    referencia = desde or date.min
    saida.sort(key=lambda t: (t.proxima(referencia) or date.max, t.tema))
    return saida


# --- a ficha montada ------------------------------------------------------------

@dataclass(frozen=True)
class Item:
    """Um texto com a origem dele, e o link quando ha."""

    texto: str
    origem: str
    link: str | None = None
    nota: str | None = None


@dataclass(frozen=True)
class QuestaoReal:
    """Uma questao real do acervo dentro do escopo da ficha."""

    codigo: str          # "2013-q15"
    ano: int | None
    numero: int | None
    evidencia: str       # alvo | complementar
    conteudo: str
    resposta: str | None
    enunciado: str
    pegadinha: str | None
    tipo_de_questao: str | None
    conferida: bool

    @property
    def onde(self) -> str:
        """"Polícia Penal SC" ou "acervo complementar FEPESE"."""
        return "Polícia Penal SC" if self.evidencia == "alvo" else "acervo complementar FEPESE"

    @property
    def no(self) -> str:
        """O no da questao, sem a materia na frente."""
        return arvore.SEPARADOR.join(arvore.partes(self.conteudo)[1:]) or self.conteudo


@dataclass(frozen=True)
class Pratica:
    """Uma faixa de questoes do tema no cronograma: quando, quantas, como."""

    data: date
    rotulo: str
    questoes: int
    consulta: bool
    filtro: str | None
    detalhe: str | None


@dataclass
class Contexto:
    """Tudo o que a ficha precisa, ja contado. Quem monta e o
    `servico.fichas.contexto()`; o teste monta a mao, sem banco."""

    hoje: date
    plano: object
    caminhos: list
    niveis: dict
    ocorrencias_alvo: list
    ocorrencias_complementares: list
    #: As entradas do `desempenho_por_conteudo` (respostas e anotacoes).
    entradas: list
    #: {materia: meta em %} do config/cronograma.yml.
    metas: dict
    #: A fila de revisao (`estudo.para_revisar`) e as situacoes por no.
    fila: list
    situacoes: dict
    #: As questoes geradas (nao rejeitadas), com `conteudo`.
    geradas: list
    #: (materia, assunto) -> leis.Lei | None
    lei: object
    minimos_amostra: object
    minimos_acervo: object
    regra: object
    #: data -> o Dia montado com o nivel daquele dia (ou None).
    dia_montado: object
    #: dentro -> estudo.Refazer (as erradas no radar e o caderno do escopo).
    refazer: object
    escritas: list = field(default_factory=list)


@dataclass
class FichaDeEstudo:
    """A tarefa do cronograma inteira, com a origem de cada parte.

    Os nomes sao os da secao 11 em portugues (`CAMPOS_DA_SECAO_11`). Campo
    sem dado nao e inventado: a tela e o terminal escrevem `vazio(campo)`.
    """

    escrita: FichaEscrita
    data: date | None
    tema: str
    materia: str
    assunto: str | None
    subassunto: str | None
    elemento: str | None
    tipo_elemento: str | None
    nos: list
    por_que_agora: list
    prioridade: object
    fonte: Item | None
    ler_exatamente: Item
    artigos_chave: list
    como_pesquisar: list
    entender: list
    memorizar: list
    pegadinhas_do_acervo: list
    pegadinhas_escritas: list
    linha_do_alvo: object
    padroes_do_alvo: object
    linha_complementar: object
    questoes_reais: list
    meta_de_questoes: list
    quando_revisar: list
    revisoes_do_plano: list
    geradas: list
    refazer: object
    desempenho: object
    estado: object
    situacao: str
    faixas: list

    @property
    def id(self) -> str:
        return self.escrita.id

    @property
    def conferida(self) -> bool:
        return bool(self.escrita.conferida_em)

    @property
    def origens(self) -> dict[str, str]:
        """A origem de cada campo, para a tela desenhar o selo dela (7A)."""
        return ORIGEM_DO_CAMPO

    @property
    def procedencia(self) -> str:
        return self.escrita.modelo

    @property
    def caminho_exibido(self) -> list[str]:
        """"Direito Constitucional → Direitos e garantias... → Art. 5º...":
        materia, assunto, subassunto e elemento, o que houver."""
        return [p for p in (self.materia, self.assunto, self.subassunto,
                            self.elemento) if p]

    def vazio(self, campo: str) -> str:
        """O que escrever quando o campo nao tem dado.

        Campo do acervo leva a frase da regra inviolavel 4, exata. Campo
        escrito leva a outra: o que falta ali e texto, nao prova. Os campos do
        plano e da conta tem frase propria na tela ("o cronograma nao tem
        faixa de questoes deste tema"), e nao passam por aqui.
        """
        origem = ORIGEM_DO_CAMPO.get(campo)
        if origem == ACERVO:
            return FRASE_SEM_EVIDENCIA
        if origem == IA:
            return FRASE_SEM_TEXTO
        raise KeyError(f"o campo {campo!r} não tem frase de vazio: ele é do plano ou da conta")

    @property
    def sem_no(self) -> bool:
        """O tema nao tem no que sirva na arvore: nada do acervo e contado."""
        return not self.nos


def dentro_de(nos: list[str]):
    """f(caminho) -> o no esta dentro do escopo? Escopo vazio nao tem nada."""
    def dentro(caminho: str | None) -> bool:
        if not caminho:
            return False
        return any(caminho == no or caminho.startswith(no + arvore.SEPARADOR)
                   for no in nos)
    return dentro


def _nivel_do_escopo(nos: list[str], niveis: dict) -> str:
    """O nivel da regua de amostra para o escopo: o mais alto entre os nos.

    Um escopo com um assunto inteiro pede o minimo do assunto (10); so com
    subassuntos e elementos, o deles (6). O config/amostra.yml manda.
    """
    presentes = {niveis.get(no) for no in nos}
    for nivel in ("assunto", "subassunto"):
        if nivel in presentes:
            return nivel
    return "elemento"


def _codigo(o) -> str:
    return f"{o.ano or 's/a'}-q{o.numero}" if o.numero else f"{o.ano or 's/a'}"


def _questoes_reais(dentro, ctx: Contexto) -> list[QuestaoReal]:
    """As do alvo primeiro (a minha prova), depois as do complementar, cada
    uma marcada (§9). No complementar, a mesma questao em dez cadernos e uma."""
    saida = []
    alvo = sorted((o for o in incidencia.validas(ctx.ocorrencias_alvo)
                   if dentro(o.conteudo)),
                  key=lambda o: (o.ano or 0, o.numero or 0))
    for o in alvo:
        saida.append(QuestaoReal(_codigo(o), o.ano, o.numero, "alvo", o.conteudo,
                                 o.resposta, o.enunciado, o.pegadinha,
                                 o.tipo_de_questao, o.conferida))
    vistas = set()
    complementares = sorted(
        (o for o in ctx.ocorrencias_complementares
         if not o.anulada and o.status != "pendente" and dentro(o.conteudo)),
        key=lambda o: (-(o.ano or 0), o.numero or 0))
    for o in complementares:
        if o.impressao in vistas:
            continue
        vistas.add(o.impressao)
        saida.append(QuestaoReal(_codigo(o), o.ano, o.numero, "complementar",
                                 o.conteudo, o.resposta, o.enunciado, o.pegadinha,
                                 o.tipo_de_questao, o.conferida))
    return saida


def _desempenho(escrita: FichaEscrita, dentro, ctx: Contexto):
    from radar.servico import desempenho_por_conteudo as por_conteudo

    desempenho = por_conteudo.do_escopo(
        dentro, caminho=escrita.id, nome=escrita.tema,
        nivel=_nivel_do_escopo(escrita.nos, ctx.niveis),
        meta=ctx.metas.get(escrita.materia), lista=ctx.entradas)
    return desempenho, (desempenho.estado(ctx.minimos_amostra)
                        if not desempenho.vazio else None)


def _ultima_pratica(desempenho) -> date | None:
    dias = desempenho.radar.dias | desempenho.anotado.dias
    return max(dias) if dias else None


def prioridade_de(escrita: FichaEscrita, ctx: Contexto):
    """A prioridade do tema, pela regra do config/prioridade.yml."""
    dentro = dentro_de(escrita.nos)
    alvo_no_escopo = len([o for o in incidencia.validas(ctx.ocorrencias_alvo)
                          if dentro(o.conteudo)])
    alvo_na_materia = len([o for o in incidencia.validas(ctx.ocorrencias_alvo)
                           if o.materia == escrita.materia])
    compl_no_escopo = incidencia.complementar_do_escopo(
        escrita.id, dentro, ctx.ocorrencias_complementares).questoes
    compl_na_materia = incidencia.complementar_do_escopo(
        escrita.materia, dentro_de([escrita.materia]),
        ctx.ocorrencias_complementares).questoes
    desempenho, estado = _desempenho(escrita, dentro, ctx)
    materia_do_edital = ctx.plano.materia(escrita.materia)
    motivos = []
    for item in ctx.fila:
        if dentro(item.caminho):
            for motivo in item.motivos:
                if motivo not in motivos:
                    motivos.append(motivo)
    return regra_de_prioridade.calcular(
        materia=escrita.materia,
        questoes_da_materia=materia_do_edital.questoes if materia_do_edital else None,
        questoes_da_prova=ctx.plano.questoes_da_prova,
        alvo_no_escopo=alvo_no_escopo, alvo_na_materia=alvo_na_materia,
        complementar_no_escopo=compl_no_escopo,
        complementar_na_materia=compl_na_materia,
        estado=estado, ultima=_ultima_pratica(desempenho),
        motivos_da_revisao=motivos, hoje=ctx.hoje, regra=ctx.regra,
        sem_no=not escrita.nos)


def _rotulo_da_faixa(faixa) -> str:
    if faixa.rotulo:
        return faixa.rotulo
    if faixa.titulo.startswith("Fixação: "):
        return "Fixação"
    if faixa.titulo.startswith("Aprendizagem: "):
        return "Aprendizagem"
    return plano_de_estudo.TIPO_LEGIVEL.get(faixa.tipo, faixa.tipo)


def _praticas(faixas: list[FaixaDoTema], ctx: Contexto) -> list[Pratica]:
    """As faixas de questoes do tema, com o numero do dia montado (a rampa do
    nivel muda o numero da aprendizagem; a tela Hoje mostra o mesmo)."""
    saida = []
    for f in faixas:
        if not plano_de_estudo.tem_acerto(f.faixa):
            continue
        montado = ctx.dia_montado(f.data)
        faixa = f.faixa
        if montado is not None:
            bloco = getattr(montado, f.bloco)
            if f.indice < len(bloco):
                faixa = bloco[f.indice]
        saida.append(Pratica(
            data=f.data, rotulo=_rotulo_da_faixa(faixa), questoes=faixa.questoes or 0,
            consulta=plano_de_estudo.consulta_por_padrao(faixa),
            filtro=faixa.filtro, detalhe=faixa.detalhe))
    return saida


def _dia_mes(d: date) -> str:
    return d.strftime("%d/%m")


def _motivos_do_plano(faixas: list[FaixaDoTema], data: date | None,
                      hoje: date) -> list[Item]:
    """O que o CRONOGRAMA diz do tema: o dia aberto, ou o proximo e o ultimo."""
    if data is not None:
        no_dia = [f for f in faixas if f.data == data]
        if no_dia:
            partes = []
            for f in no_dia:
                rotulo = _rotulo_da_faixa(f.faixa)
                if f.faixa.origem:
                    rotulo += f" (a volta do estudo de {_dia_mes(date.fromisoformat(str(f.faixa.origem)))})"
                partes.append(rotulo)
            return [Item(f"O cronograma de {_dia_mes(data)} traz este tema: "
                         + " · ".join(partes) + ".", PLANO)]
    saida = []
    passadas = [f for f in faixas if f.data < hoje]
    futuras = [f for f in faixas if f.data >= hoje]
    if futuras:
        f = futuras[0]
        saida.append(Item(f"Próxima vez no cronograma: {_dia_mes(f.data)} "
                          f"({_rotulo_da_faixa(f.faixa)}).", PLANO))
    if passadas:
        f = passadas[-1]
        saida.append(Item(f"Última vez no cronograma: {_dia_mes(f.data)} "
                          f"({_rotulo_da_faixa(f.faixa)}).", PLANO))
    return saida


def _situacao(dentro, ctx: Contexto) -> str:
    """"estudado e praticado", "estudado", "praticado" ou "não estudado", pela
    definicao da Etapa 4 (decisao 20), olhando os nos do escopo."""
    from radar.servico import estudo

    estudado = praticado = False
    for caminho, situacao in ctx.situacoes.items():
        if dentro(caminho):
            estudado = estudado or situacao.estudado
            praticado = praticado or situacao.praticado
    if estudado and praticado:
        return f"{estudo.ESTUDADO} e {estudo.PRATICADO}"
    if estudado:
        return estudo.ESTUDADO
    if praticado:
        return estudo.PRATICADO
    return estudo.NAO_ESTUDADO


def _quando_revisar(escrita, dentro, faixas, ctx: Contexto) -> tuple[list, list]:
    """(motivos, revisoes do plano). As revisoes fixas do cronograma (R+7,
    R+30) e a fila da Etapa 4, que SUGERE e nao troca o tema da faixa."""
    revisoes = [(f.data, f.faixa.rotulo or "Revisão") for f in faixas
                if f.faixa.tipo == "revisao"]
    motivos = []
    if revisoes:
        motivos.append(Item(
            "No cronograma: " + " · ".join(f"{r} em {_dia_mes(d)}" for d, r in revisoes)
            + ".", PLANO))
    na_fila = [item for item in ctx.fila if dentro(item.caminho)]
    if na_fila:
        for item in na_fila:
            nome = arvore.SEPARADOR.join(arvore.partes(item.caminho)[1:])
            motivos.append(Item(f"Na fila de revisão agora: {nome} — {item.porque}.",
                                AUTOMATICO))
    elif escrita.nos:
        motivos.append(Item("Fora da fila de revisão hoje.", AUTOMATICO))
    minimos = ctx.minimos_amostra
    from radar.servico import estudo

    intervalos = "-".join(str(i) for i in estudo.INTERVALOS)
    motivos.append(Item(
        f"A regra (Etapa 4): o conteúdo volta para a revisão por erro recente (no "
        f"radar ou no caderno de erros), por acerto abaixo de "
        f"{minimos.precisa_revisar_abaixo_de}% com amostra suficiente "
        f"({minimos.do_nivel('assunto')} respostas sem consulta no assunto, "
        f"{minimos.do_nivel('subassunto')} no subassunto ou elemento), ou pelo prazo "
        f"{intervalos} vencido.", AUTOMATICO))
    return motivos, revisoes


def _artigos_chave(escrita: FichaEscrita, faixas: list[FaixaDoTema], plano) -> list:
    """Os artigos-chave do dia da TEORIA do tema - os mesmos do Plano B e da
    lei seca dirigida (o `essencial` do cronograma.yml). So para o tema que e
    a teoria do dia: o `essencial` e do Direito do dia, e nao do Portugues."""
    for f in faixas:
        if f.faixa.tipo == "teoria":
            dia = plano.dia(f.data)
            if dia is not None and dia.essencial is not None:
                return list(dia.essencial.chave) + list(dia.essencial.apoio)
    return []


def montar(escrita: FichaEscrita, ctx: Contexto, data: date | None = None,
           prioridade=None) -> FichaDeEstudo:
    """A ficha inteira de um tema. `data` e o dia aberto na tela (o "agora")."""
    dentro = dentro_de(escrita.nos)
    faixas = faixas_do_tema(ctx.plano, escrita.tema, escrita.materia)

    lei = ctx.lei(escrita.materia, escrita.assunto)
    if lei is not None:
        fonte = Item(lei.titulo, OFICIAL, link=lei.url, nota=lei.nota)
    elif escrita.fonte_sugerida:
        fonte = Item(escrita.fonte_sugerida, IA)
    else:
        fonte = None

    linha_do_alvo = incidencia.linha_do_escopo(
        escrita.id, escrita.tema, dentro, escrita.materia, ctx.ocorrencias_alvo)
    padroes = incidencia.padroes(linha_do_alvo, ctx.minimos_acervo)
    complementar = incidencia.complementar_do_escopo(
        escrita.id, dentro, ctx.ocorrencias_complementares)
    reais = _questoes_reais(dentro, ctx)
    desempenho, estado = _desempenho(escrita, dentro, ctx)
    prioridade = prioridade or prioridade_de(escrita, ctx)
    motivos_de_revisao, revisoes = _quando_revisar(escrita, dentro, faixas, ctx)

    por_que = _motivos_do_plano(faixas, data, ctx.hoje)
    por_que += [Item(f"{f.nome.capitalize()} — {f.texto}.", f.origem)
                for f in prioridade.fatores]
    if prioridade.posicao:
        por_que.append(Item(
            f"Prioridade {regra_de_prioridade.numero(prioridade.valor, 2)} "
            f"({prioridade.conta}): {prioridade.posicao}º de {prioridade.de} temas "
            f"com ficha. É regra de priorização (config/prioridade.yml), "
            f"não previsão de prova.", AUTOMATICO))

    return FichaDeEstudo(
        escrita=escrita, data=data, tema=escrita.tema, materia=escrita.materia,
        assunto=escrita.assunto, subassunto=escrita.subassunto,
        elemento=escrita.elemento, tipo_elemento=escrita.tipo_elemento,
        nos=list(escrita.nos), por_que_agora=por_que, prioridade=prioridade,
        fonte=fonte, ler_exatamente=Item(escrita.ler_exatamente, IA),
        artigos_chave=_artigos_chave(escrita, faixas, ctx.plano),
        como_pesquisar=list(escrita.como_pesquisar),
        entender=list(escrita.entender), memorizar=list(escrita.memorizar),
        pegadinhas_do_acervo=[q for q in reais if q.pegadinha],
        pegadinhas_escritas=list(escrita.pegadinhas),
        linha_do_alvo=linha_do_alvo, padroes_do_alvo=padroes,
        linha_complementar=complementar,
        questoes_reais=reais,
        meta_de_questoes=_praticas(faixas, ctx),
        quando_revisar=motivos_de_revisao, revisoes_do_plano=revisoes,
        geradas=[g for g in ctx.geradas if dentro(getattr(g, "conteudo", None))],
        refazer=ctx.refazer(dentro), desempenho=desempenho, estado=estado,
        situacao=_situacao(dentro, ctx), faixas=faixas,
    )


def comando_de_gerar(no: str, quantas: int = 10) -> str:
    """O `radar gerar` de um no do escopo, em modo treino (Etapa 5).

    Um comando por no, e nao um para a ficha inteira: o escopo fechado da
    Etapa 5 e um caminho so, e e ele que a importacao confere. Juntar nos de
    assuntos diferentes num pedido afrouxaria essa trava.
    """
    nomes = arvore.partes(no)
    partes = [f'--materia "{nomes[0]}"', f'--assunto "{nomes[1]}"']
    if len(nomes) > 2:
        partes.append(f'--subassunto "{nomes[2]}"')
    if len(nomes) > 3:
        partes.append(f'--elemento "{nomes[3]}"')
    return (f"radar gerar --pedido --modo treino {' '.join(partes)} "
            f"--quantas {quantas}")
