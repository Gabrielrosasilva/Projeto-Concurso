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
from dataclasses import asdict, dataclass, field, replace
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
    "padroes_complementares": ACERVO,
    "questoes_reais": ACERVO,
    "meta_de_questoes": PLANO,
    "quando_revisar": AUTOMATICO, "refazer": AUTOMATICO,
    "desempenho": AUTOMATICO, "geradas": IA, "leis_mudadas": IA,
    # R1 (05/10): o "caiu ou nao caiu" e contagem nas provas (acervo); o
    # exemplo e a questao tirada da prova, com o gabarito oficial (oficial,
    # decisao 53); a explicacao e o macete sao texto de IA.
    "caiu": ACERVO, "exemplos": OFICIAL, "explicacao": IA, "macetes": IA,
}

#: Os prefixos que o cronograma poe no titulo das faixas de um mesmo tema. A
#: lista e fechada de proposito: um prefixo novo no YAML tem de entrar aqui, e
#: nao ser adivinhado.
PREFIXOS_DO_TEMA = ("Fixação: ", "Aprendizagem: ", "R+7: ", "R+30: ",
                    "Artigos-chave: ", "Questões de prova: ",
                    # A faixa da redistribuicao do Ciclo 1 (R4): revisao de um
                    # tema que caiu, no tempo de um que nao caiu.
                    "Extra: ")

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
    "art-5o-caput-e-incisos-i-a-xvi". Vai na URL pelo endereco, e nao por um
    `?tema=` (que ate 04/10 era tambem o claro/escuro da web)."""
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
    #: O RESUMO do tema (R2): o texto corrido de uma tela, para o caderno.
    #: {"partes": {parte: [{"texto", "fontes"}]}, "modelo", "criado_em",
    #: "conferido_em"}. A parte 1 ("caiu ou nao caiu") nao mora aqui: e
    #: estatistica, e sai na hora do `incidencia.caiu_no_alvo`.
    resumo: dict | None = None

    @property
    def id(self) -> str:
        return id_do_tema(self.tema)

    @property
    def chave(self) -> str:
        return chave_do_tema(self.tema)

    def para_dict(self) -> dict:
        dados = asdict(self)
        # Sem resumo, a chave nao vai: as fichas sem resumo ficam no arquivo
        # exatamente como eram.
        if dados.get("resumo") is None:
            dados.pop("resumo", None)
        return dados

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


# --- o resumo do tema (R2) -----------------------------------------------------------
#
# Um texto curto, de uma tela, para passar ao caderno antes da videoaula. A
# parte 1 ("caiu ou nao caiu", com a amostra) e calculada na hora; as outras
# cinco sao texto de IA (🟣), e CADA frase diz o que a sustenta: o artigo, a
# regra ou a questao real. A conferencia abaixo e a mesma na importacao e no
# verificador (`radar fichas --verificar-resumos`).

#: As partes escritas, na ordem da tela. A parte 1 nao esta aqui.
PARTES_DO_RESUMO = (
    ("dominar", "O que eu preciso dominar"),
    ("artigos", "Os artigos ou regras-chave"),
    ("como_cobra", "Como a banca cobra"),
    ("pegadinhas", "As pegadinhas"),
    ("basico", "O básico é isto"),
)
NOME_DA_PARTE = dict(PARTES_DO_RESUMO)

#: A fonte de uma pegadinha que nao vem de questao real: "confusao comum".
SEM_QUESTAO_REAL = "sem questão real"

#: Uma questao real citada: "2019-q51" (as provas do meu cargo) ou
#: "FEPESE-2024-q8" (outra prova da FEPESE, do complementar: o mesmo ano e
#: numero pode ser de outra prova, e o prefixo nao deixa confundir), e o
#: gabarito quando a frase o da: "2019-q51 (gabarito C)".
PREFIXO_DO_COMPLEMENTAR = "FEPESE-"
CODIGO_DA_QUESTAO = re.compile(r"(?<![\w-])((?:FEPESE-)?20\d\d-q\d+)\b")
GABARITO_CITADO = re.compile(r"(?<![\w-])((?:FEPESE-)?20\d\d-q\d+)\s*\(gabarito\s+([A-Ea-e])\)")


def codigo_citavel(q) -> str:
    """O codigo com que o resumo cita a questao real: o do caderno no alvo, e
    com o prefixo FEPESE- no complementar."""
    if getattr(q, "evidencia", "alvo") == "complementar":
        return PREFIXO_DO_COMPLEMENTAR + q.codigo
    return q.codigo


#: O que fica no lugar da letra da questao que eu ainda nao respondi (P05).
GABARITO_ESCONDIDO = "gabarito depois de responder no radar"


def esconder_gabarito(texto: str, respondidos) -> str:
    """O texto do resumo sem a letra das questoes que eu ainda nao respondi no
    radar (P05, decisao 148): "2019-q51 (gabarito C)" vira "2019-q51
    (gabarito depois de responder no radar)". A letra continua no dado - e
    com ela que a importacao confere o resumo (decisao 118)."""
    if not texto:
        return texto
    return GABARITO_CITADO.sub(
        lambda m: m.group(0) if m.group(1) in respondidos
        else f"{m.group(1)} ({GABARITO_ESCONDIDO})", texto)
# O "§" nao tem fronteira de palavra antes dele: fica fora do \b.
CITA_DISPOSITIVO = re.compile(r"(?i)(\barts?\.|\bart\b|\bregras?\s+\d|\bs[úu]mula|§)")

TEXTO_MINIMO_DA_FRASE = 10


def _frases(bruto, parte: str) -> list[dict]:
    if bruto is None:
        return []
    if not isinstance(bruto, list):
        raise FichaRecusada(f"a parte {parte!r} do resumo tem de ser uma lista de frases")
    saida = []
    for numero, frase in enumerate(bruto, start=1):
        if not isinstance(frase, dict):
            raise FichaRecusada(f"{parte}, frase {numero}: tem de ser um objeto com texto e fontes")
        texto = _texto(frase.get("texto"))
        fontes = _lista(frase.get("fontes"))
        if len(texto) < TEXTO_MINIMO_DA_FRASE:
            raise FichaRecusada(f"{parte}, frase {numero}: sem texto")
        if not fontes:
            raise FichaRecusada(f"{parte}, frase {numero}: sem fonte (artigo, regra ou "
                                f"questão real que a sustente)")
        saida.append({"texto": texto, "fontes": fontes})
    return saida


def conferir_resumo(bruto, *, codigos: dict, caiu: bool, exige_artigo: bool,
                    basico_obrigatorio: bool | None = None) -> dict:
    """As partes do resumo, conferidas. Levanta `FichaRecusada` com o motivo.

    - `codigos`: {"2019-q51": "c"} - as questoes reais do tema (as do alvo e
      as do complementar), com o gabarito oficial. Questao citada fora desta
      lista, ou com o gabarito trocado, e recusada;
    - `caiu`: o tema caiu nas provas do alvo? Se caiu, "o basico e isto" nao
      entra;
    - `basico_obrigatorio`: o tema e da classe basica (nao caiu nas provas que
      bastam). Sem base para afirmar (uma prova so, ou o tema nao contado), o
      basico e opcional. None = obrigatorio sempre que nao caiu;
    - `exige_artigo`: materia de lei (o config/leis.yml): cada artigo-chave
      cita o dispositivo.
    """
    if basico_obrigatorio is None:
        basico_obrigatorio = not caiu
    if not isinstance(bruto, dict):
        raise FichaRecusada("sem o objeto `resumo`")
    partes_brutas = bruto.get("partes", bruto)
    if not isinstance(partes_brutas, dict):
        raise FichaRecusada("o resumo tem de ter as partes por nome")
    estranhas = set(partes_brutas) - set(NOME_DA_PARTE)
    if estranhas:
        raise FichaRecusada(f"parte que o resumo não tem: {', '.join(sorted(estranhas))}")
    partes = {chave: _frases(partes_brutas.get(chave), chave) for chave in NOME_DA_PARTE}

    for chave in ("dominar", "artigos", "como_cobra", "pegadinhas"):
        if not partes[chave]:
            raise FichaRecusada(f"sem a parte {NOME_DA_PARTE[chave]!r}")
    if basico_obrigatorio and not caiu and not partes["basico"]:
        raise FichaRecusada("o tema não caiu: falta 'o básico é isto'")
    if caiu and partes["basico"]:
        raise FichaRecusada("o tema caiu: 'o básico é isto' é só para o que não caiu")

    for chave, frases in partes.items():
        for numero, frase in enumerate(frases, start=1):
            juntas = " ".join([frase["texto"]] + frase["fontes"])
            achado = PREVISAO.search(juntas)
            if achado:
                raise FichaRecusada(f"{chave}, frase {numero}: texto com cara de previsão "
                                    f"({achado.group(0)!r})")
            for codigo in CODIGO_DA_QUESTAO.findall(juntas):
                if codigo not in codigos:
                    raise FichaRecusada(f"{chave}, frase {numero}: a questão {codigo} não é "
                                        f"deste tema (ou não existe)")
            for codigo, letra in GABARITO_CITADO.findall(juntas):
                if (codigos.get(codigo) or "").lower() != letra.lower():
                    raise FichaRecusada(f"{chave}, frase {numero}: o gabarito oficial de "
                                        f"{codigo} não é {letra.upper()}")

    if not codigos:
        textos = [f["texto"] for f in partes["como_cobra"]]
        if textos != [FRASE_SEM_EVIDENCIA]:
            raise FichaRecusada("o tema não tem questão real: 'como a banca cobra' é "
                                "exatamente a frase de evidência insuficiente")
    else:
        for numero, frase in enumerate(partes["como_cobra"], start=1):
            if not CODIGO_DA_QUESTAO.search(" ".join([frase["texto"]] + frase["fontes"])):
                raise FichaRecusada(f"como_cobra, frase {numero}: padrão sem a questão real "
                                    f"que o mostra")
    for numero, frase in enumerate(partes["pegadinhas"], start=1):
        juntas = " ".join([frase["texto"]] + frase["fontes"])
        if not CODIGO_DA_QUESTAO.search(juntas) and SEM_QUESTAO_REAL not in frase["fontes"]:
            raise FichaRecusada(f"pegadinhas, frase {numero}: cite a questão real, ou marque "
                                f"a fonte {SEM_QUESTAO_REAL!r}")
    if exige_artigo:
        for numero, frase in enumerate(partes["artigos"], start=1):
            if not any(CITA_DISPOSITIVO.search(f) for f in frase["fontes"]):
                raise FichaRecusada(f"artigos, frase {numero}: sem o dispositivo na fonte")
    return {chave: frases for chave, frases in partes.items() if frases}


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


#: As faixas que nao dizem o tema no titulo, mas sao do tema da TEORIA do dia
#: (decisao da R1, 05/10): a lei seca dirigida le os artigos-chave da teoria.
TIPOS_DO_TEMA_DA_TEORIA = ("lei_seca",)


def da_faixa_no_dia(faixa, faixas_do_dia, escritas: list[FichaEscrita]) -> FichaEscrita | None:
    """A ficha da faixa; a lei seca sem ficha propria fica com a da teoria do
    mesmo dia e da mesma materia. So para a tela (a ficha e o resumo): o
    "estudado" da Etapa 4 continua contando so a faixa com ficha propria."""
    escrita = da_faixa(faixa, escritas)
    if (escrita is None and faixa is not None and not getattr(faixa, "desligada", False)
            and faixa.tipo in TIPOS_DO_TEMA_DA_TEORIA and faixa.materia):
        for outra in faixas_do_dia:
            if outra.tipo == "teoria" and outra.materia == faixa.materia:
                return da_faixa(outra, escritas)
    return escrita


# --- onde a faixa esta na arvore (subetapa 2C, decisao 71) ------------------------
#
# O assunto e o subassunto ficavam dentro da ficha: a faixa dizia o tema e so.
# Agora a propria faixa diz o assunto, o subassunto - ou que a arvore nao tem
# subassunto para ela - e o elemento. Nada aqui cria no (escolha 5B): o que
# nao esta na arvore, a tela diz que nao esta.

@dataclass(frozen=True)
class AssuntoDaFaixa:
    """Um assunto da arvore que a faixa cobre, e o que ela cobre dele."""

    nome: str
    #: Os subassuntos da arvore que a faixa cobre.
    subassuntos: tuple = ()
    elementos: tuple = ()
    #: Sem subassunto: a faixa cobre o assunto INTEIRO (o no escolhido e o
    #: proprio assunto, e a arvore tem subassunto nele)? Falso, a tela diz que
    #: nao ha subassunto na arvore para o tema - a frase da escolha 5B.
    inteiro: bool = False


@dataclass(frozen=True)
class OndeNaArvore:
    """O assunto, o subassunto e o elemento de uma faixa, ditos na faixa."""

    assuntos: tuple               # (AssuntoDaFaixa, ...), na ordem dos nos
    #: O elemento exato, escrito na ficha ("LEP, arts. 28 a 37").
    elemento: str | None = None
    tipo_elemento: str | None = None
    #: IA quando vem da ficha (escrita por IA, por conferir); PLANO quando vem
    #: dos nos que o cronograma.yml da para a faixa.
    origem: str = IA
    #: A ficha nao aponta no: o assunto e o que ela escreveu, conferido
    #: contra a arvore quando foi importada.
    sem_no: bool = False


def _por_assunto(nos, caminhos, escolhidos: bool = True) -> tuple:
    """Os nos agrupados por assunto, na ordem em que aparecem.

    `caminhos` e a arvore inteira: e dela que sai se o assunto tem subassunto.
    `escolhidos` falso quando o no nao foi escolhido (a ficha sem no): ai o
    tema e um pedaco do assunto, e nunca "o assunto inteiro".
    """
    por_assunto: dict[str, tuple[str, list, list]] = {}
    for no in nos:
        partes = arvore.partes(no)
        if len(partes) < 2:
            continue
        no_do_assunto = arvore.SEPARADOR.join(partes[:2])
        _caminho, subassuntos, elementos = por_assunto.setdefault(
            partes[1], (no_do_assunto, [], []))
        if len(partes) > 2 and partes[2] not in subassuntos:
            subassuntos.append(partes[2])
        if len(partes) > 3 and partes[3] not in elementos:
            elementos.append(partes[3])
    return tuple(
        AssuntoDaFaixa(nome, tuple(subs), tuple(elems), inteiro=(
            escolhidos and not subs
            and any(c.startswith(caminho + arvore.SEPARADOR) for c in caminhos)))
        for nome, (caminho, subs, elems) in por_assunto.items())


def onde_na_arvore(faixa, escrita: "FichaEscrita | None",
                   caminhos=()) -> OndeNaArvore | None:
    """Onde a faixa esta na arvore: pela ficha, ou pelos nos do plano.

    A ficha manda quando existe: os nos dela; sem no, o assunto e o
    subassunto que ela escreveu (a importacao conferiu os dois contra a
    arvore). Sem ficha, os nos da propria faixa no cronograma.yml (`nos`, ou
    o `conteudo`). None quando nada diz. `caminhos` e a arvore inteira.
    """
    if escrita is not None and escrita.nos:
        return OndeNaArvore(_por_assunto(escrita.nos, caminhos), escrita.elemento,
                            escrita.tipo_elemento, IA)
    if escrita is not None and escrita.assunto:
        no = arvore.caminho(escrita.materia, escrita.assunto)
        if escrita.subassunto:
            no = arvore.caminho(no, escrita.subassunto)
        return OndeNaArvore(_por_assunto([no], caminhos, escolhidos=False),
                            escrita.elemento, escrita.tipo_elemento, IA, sem_no=True)
    nos = list(getattr(faixa, "nos", ()) or ())
    if not nos and getattr(faixa, "conteudo", None):
        nos = [faixa.conteudo]
    assuntos = _por_assunto(nos, caminhos)
    if not assuntos:
        return None
    return OndeNaArvore(assuntos, origem=PLANO)


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
    #: A questao inteira, para o exemplo real (R1): as alternativas como no
    #: caderno, a explicacao escrita (🟣, data/explicacoes.json) quando ha, e
    #: a lei que mudou depois da prova num ponto que ela cobra (config/leis.yml).
    alternativas: tuple = ()          # (("a", "texto"), ...)
    explicacao: dict | None = None
    mudancas: tuple = ()
    #: Classificacao pendente (o artigo e do tema, mas nao ha no) ou contada
    #: pelo artigo (a ficha nao tem no): a tela diz como ela chegou aqui.
    como: str = "no"                  # no | artigo | pendente
    prova: str = ""
    #: O texto de apoio que a questao cita, quando ela cita (item 4, 06/10).
    texto_base: str | None = None
    #: Ja respondi esta questao no radar? Sem isso, a ficha esconde a letra, a
    #: explicacao e a pegadinha: a faixa manda responder sem consulta, e quem
    #: leu o gabarito antes mede a memoria (P05, decisao 148).
    respondida: bool = False

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
    #: Os cadernos complementares que entram nos padroes de cobranca: os
    #: aceitos com gabarito definitivo (decisao 78). Vazio, nenhum entra.
    provas_dos_padroes: set = field(default_factory=set)
    #: (materia, nos, titulo) -> [leis.Mudanca]: a lei que mudou num ponto que
    #: nenhuma questao cobra (decisao 84). None, nenhuma.
    leis_mudadas: object = None
    #: R1: {impressao do enunciado: explicacao} do data/explicacoes.json.
    explicacoes: dict = field(default_factory=dict)
    #: R1: os macetes escritos (data/macetes.json), ligados a ficha pelas
    #: questoes reais que eles citam - nunca pelo nome do assunto.
    macetes: list = field(default_factory=list)
    #: R1: (ano, materia, texto) -> [leis.Mudanca] da questao. None, nenhuma.
    mudancas_da_questao: object = None
    #: O minimo de provas do config/amostra.yml (acervo): quantas bastam para
    #: dizer que o tema "caiu nas provas" ou rebaixa-lo.
    minimo_provas: int = 2
    #: Os codigos citaveis ("2019-q51", "FEPESE-2024-q8") das questoes reais
    #: que eu ja respondi no radar (P05). Fora daqui, a letra fica escondida.
    respondidos: set = field(default_factory=set)


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
    #: Os mesmos padroes no acervo complementar, a parte e nunca somados.
    padroes_complementares: object
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
    #: A lei que mudou depois das provas num ponto que elas nao cobram
    #: (decisao 84). Escrito por IA, por conferir - o aviso diz isso.
    leis_mudadas: list = field(default_factory=list)
    #: R1: o tema nas provas do alvo, prova a prova (incidencia.CaiuNoAlvo).
    caiu: object = None
    #: R1: os exemplos reais do alvo - as contadas e as pendentes do tema -,
    #: com a questao inteira.
    exemplos: list = field(default_factory=list)
    #: R1: os macetes que citam questao real deste tema.
    macetes: list = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.escrita.id

    @property
    def conferida(self) -> bool:
        return bool(self.escrita.conferida_em)

    @property
    def reais(self) -> int:
        """Quantas questoes reais do conteudo. A conta e daqui, e nao da tela
        (decisao 128)."""
        return len(self.questoes_reais)

    @property
    def reais_do_alvo(self) -> int:
        return sum(1 for q in self.questoes_reais if q.evidencia == "alvo")

    @property
    def reais_do_complementar(self) -> int:
        return self.reais - self.reais_do_alvo

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


def _questao_real(o, evidencia: str, ctx: Contexto, como: str = "no") -> QuestaoReal:
    """A questao real como a ficha mostra: inteira, com o gabarito oficial, a
    explicacao escrita quando existe e a lei que mudou depois da prova."""
    alternativas = tuple(sorted((str(k).lower(), str(v))
                                for k, v in (getattr(o, "alternativas", None) or {}).items()))
    mudancas = ()
    if ctx.mudancas_da_questao is not None:
        texto = " ".join([o.enunciado or ""] + [v for _, v in alternativas])
        mudancas = tuple(ctx.mudancas_da_questao(o.ano, o.materia, texto) or ())
    questao = QuestaoReal(
        _codigo(o), o.ano, o.numero, evidencia, o.conteudo or "", o.resposta,
        o.enunciado, o.pegadinha, o.tipo_de_questao, o.conferida,
        alternativas=alternativas,
        explicacao=ctx.explicacoes.get(getattr(o, "impressao_do_enunciado", "") or ""),
        mudancas=mudancas, como=como, prova=o.prova,
        texto_base=getattr(o, "texto_base", None))
    return replace(questao, respondida=codigo_citavel(questao) in ctx.respondidos)


def _questoes_reais(dentro, ctx: Contexto) -> list[QuestaoReal]:
    """As do alvo primeiro (a minha prova), depois as do complementar, cada
    uma marcada (§9). No complementar, a mesma questao em dez cadernos e uma."""
    saida = []
    alvo = sorted((o for o in incidencia.validas(ctx.ocorrencias_alvo)
                   if dentro(o.conteudo)),
                  key=lambda o: (o.ano or 0, o.numero or 0))
    for o in alvo:
        saida.append(_questao_real(o, "alvo", ctx))
    vistas = set()
    complementares = sorted(
        (o for o in ctx.ocorrencias_complementares
         if not o.anulada and o.status != "pendente" and dentro(o.conteudo)),
        key=lambda o: (-(o.ano or 0), o.numero or 0))
    for o in complementares:
        if o.impressao in vistas:
            continue
        vistas.add(o.impressao)
        saida.append(_questao_real(o, "complementar", ctx))
    return saida


def faixa_do_tema(escrita: FichaEscrita):
    """A faixa de artigos do tema: pelo elemento da ficha, ou pelo titulo."""
    return (incidencia.faixa_de_artigos(escrita.elemento, escrita.materia)
            or incidencia.faixa_de_artigos(escrita.tema, escrita.materia))


def caiu_do_tema(escrita: FichaEscrita, ocorrencias_alvo, minimo_provas: int = 2,
                 provas_para_tendencia: int | None = None):
    """O tema nas provas do alvo (incidencia.caiu_no_alvo): a conta unica que a
    ficha, a faixa, a aba Fichas e a redistribuicao usam. Sem
    `provas_para_tendencia`, o do config/amostra.yml."""
    if provas_para_tendencia is None:
        from radar import amostra as regua
        provas_para_tendencia = regua.carregar().provas_para_tendencia
    return incidencia.caiu_no_alvo(
        ocorrencias_alvo, materia=escrita.materia, dentro=dentro_de(escrita.nos),
        tem_no=bool(escrita.nos), faixa=faixa_do_tema(escrita),
        minimo_provas=minimo_provas, provas_para_tendencia=provas_para_tendencia)


def _exemplos(caiu, ctx: Contexto) -> list[QuestaoReal]:
    """Os exemplos do alvo: as que contam e as pendentes do tema, por ano."""
    como = "artigo" if caiu.pelo_artigo else "no"
    saida = ([(_questao_real(o, "alvo", ctx, como), o) for o in caiu.contadas]
             + [(_questao_real(o, "alvo", ctx, "pendente"), o) for o in caiu.pendentes])
    saida.sort(key=lambda par: (par[1].ano or 0, par[1].numero or 0))
    return [q for q, _ in saida]


def _macetes_do_tema(questoes: list[QuestaoReal], ctx: Contexto) -> list[dict]:
    """Os macetes que citam alguma questao real deste tema (prova e numero).
    Macete sem questao do tema nao entra: a ligacao e pela questao, e nunca
    pelo nome do assunto."""
    do_tema = {(q.prova, q.numero): q.codigo for q in questoes if q.prova}
    saida = []
    for macete in ctx.macetes:
        citadas = [do_tema[(c.get("prova_url"), c.get("numero"))]
                   for c in macete.get("questoes") or []
                   if (c.get("prova_url"), c.get("numero")) in do_tema]
        if citadas:
            saida.append({**macete, "do_tema": citadas})
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
    padroes_complementares = incidencia.padroes_complementares_do_escopo(
        dentro, [o for o in ctx.ocorrencias_complementares
                 if o.prova in ctx.provas_dos_padroes],
        ctx.minimos_acervo)
    reais = _questoes_reais(dentro, ctx)
    caiu = caiu_do_tema(escrita, ctx.ocorrencias_alvo, ctx.minimo_provas)
    exemplos = _exemplos(caiu, ctx)
    desempenho, estado = _desempenho(escrita, dentro, ctx)
    prioridade = prioridade or prioridade_de(escrita, ctx)
    motivos_de_revisao, revisoes = _quando_revisar(escrita, dentro, faixas, ctx)

    por_que = _motivos_do_plano(faixas, data, ctx.hoje)
    if caiu.classe == incidencia.BASICO and escrita.nos:
        # A prioridade que o "nao caiu" da: e regra, e fica aqui (P10,
        # decisao 149), e nao sob o selo azul do historico.
        por_que.append(Item(
            "Prioridade baixa: o tema não apareceu nas provas do alvo analisadas, "
            "e por isso o plano pede o básico. É regra de priorização, não "
            "previsão de prova - com poucas provas, o tema pode cair na próxima.",
            AUTOMATICO))
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
        # As pegadinhas da classificacao: das reais do escopo e, na ficha sem
        # no, das que chegaram pelo artigo - cada questao uma vez.
        pegadinhas_do_acervo=[q for q in {(q.prova, q.numero, q.evidencia): q
                                          for q in reais + exemplos}.values()
                              if q.pegadinha],
        pegadinhas_escritas=list(escrita.pegadinhas),
        linha_do_alvo=linha_do_alvo, padroes_do_alvo=padroes,
        linha_complementar=complementar,
        padroes_complementares=padroes_complementares,
        questoes_reais=reais,
        meta_de_questoes=_praticas(faixas, ctx),
        quando_revisar=motivos_de_revisao, revisoes_do_plano=revisoes,
        geradas=[g for g in ctx.geradas if dentro(getattr(g, "conteudo", None))],
        refazer=ctx.refazer(dentro), desempenho=desempenho, estado=estado,
        situacao=_situacao(dentro, ctx), faixas=faixas,
        leis_mudadas=(ctx.leis_mudadas(escrita.materia, _nos_do_tema(escrita), escrita.tema)
                      if ctx.leis_mudadas else []),
        caiu=caiu, exemplos=exemplos,
        macetes=_macetes_do_tema(exemplos + reais, ctx),
    )


def _nos_do_tema(escrita: FichaEscrita) -> list[str]:
    """Os nos que dizem onde o tema esta, para ligar a ele a lei que mudou.

    Os da ficha; sem eles, o subassunto que ela escreve. So o assunto nao
    serve: na LEP o assunto e a lei inteira, e cada caso de fronteira dela
    iria parar em todas as fichas da materia.
    """
    if escrita.nos:
        return list(escrita.nos)
    if escrita.assunto and escrita.subassunto:
        return [arvore.caminho(arvore.caminho(escrita.materia, escrita.assunto),
                               escrita.subassunto)]
    return []


#: Como o comando e chamado no Windows, para copiar e colar no terminal do VS
#: Code (R6). `python -m radar` NAO funciona: o pacote nao tem __main__.py.
#: O `radar.exe` do venv funciona no PowerShell e no cmd, com ou sem o venv
#: ativado.
RADAR_NO_WINDOWS = r".venv\Scripts\radar.exe"

#: Os passos 2 e 3 do caminho sem API (README, "Sem pagar"). Nunca o
#: `--valendo` nem o botao da API: este e o caminho dos meus creditos.
PASSO_NO_CLAUDE_CODE = ("Leia data/pedido_ia.json e siga o como_responder; "
                        "escreva data/resposta_ia.json")
COMANDO_DE_IMPORTAR = RADAR_NO_WINDOWS + " gerar --importar data/resposta_ia.json"
AVISO_DO_PEDIDO = ("Faça os 3 passos antes de pedir outro assunto: pedido novo "
                   "substitui o anterior.")

#: Pedido menor que isto nao vale os 3 passos (decisao da R6): faltando 2
#: questoes num no, pede 5.
PEDIDO_MINIMO_DE_GERADAS = 5


def comando_de_gerar(no: str, quantas: int = 10) -> str:
    """O `radar gerar --pedido` de um no do escopo, em modo treino (Etapa 5).

    Um comando por no, e nao um para a ficha inteira: o escopo fechado da
    Etapa 5 e um caminho so, e e ele que a importacao confere. Juntar nos de
    assuntos diferentes num pedido afrouxaria essa trava. O `--elemento` so
    vai quando o proprio no e um elemento da arvore. E a UNICA funcao que
    escreve este comando: a ficha, a faixa e a tela de gerar mostram o mesmo.
    """
    nomes = arvore.partes(no)
    partes = [f'--materia "{nomes[0]}"', f'--assunto "{nomes[1]}"']
    if len(nomes) > 2:
        partes.append(f'--subassunto "{nomes[2]}"')
    if len(nomes) > 3:
        partes.append(f'--elemento "{nomes[3]}"')
    return (f"{RADAR_NO_WINDOWS} gerar --pedido --modo treino {' '.join(partes)} "
            f"--quantas {quantas}")


# --- as geradas da faixa de questoes (R6) -------------------------------------------
#
# Primeiro as reais no Qconcursos, que medem; depois, se eu quiser mais, as
# geradas do radar, que so treinam (o acerto delas e um segundo numero, nunca
# somado ao da faixa). A faixa diz quantas geradas ha em cada no dela e, se
# faltam, o pedido para gerar - sem criar no e sem aproximar.

#: O que a faixa diz quando o estoque de geradas do no esta acabando
#: (decisao 142), com as palavras do pedido. Os 3 passos vem junto.
FRASE_FEZ_TODAS = "Você já fez todas as questões deste tema: está na hora de criar mais."
FRASE_FEZ_METADE = "Você já tem metade das questões feitas: vamos fazer mais algumas."


@dataclass(frozen=True)
class GeradasDoNo:
    """Um no da faixa: quantas geradas ele tem e quantas pedir."""

    no: str
    geradas: int
    #: A parte das questoes da faixa que cabe a este no.
    cota: int
    #: Quantas pedir (0 = ja ha o bastante). Pede tambem quando eu ja fiz
    #: metade ou todas (decisao 142): o estoque que eu ja vi nao e estoque.
    pedir: int
    #: Quantas geradas DIFERENTES deste no eu ja fiz.
    feitas: int = 0

    @property
    def aviso(self) -> str | None:
        """"todas", "metade" ou None: o quanto do estoque eu ja fiz."""
        if not self.geradas:
            return None
        if self.feitas >= self.geradas:
            return "todas"
        if self.feitas * 2 >= self.geradas:
            return "metade"
        return None

    @property
    def frase_do_aviso(self) -> str | None:
        return {"todas": FRASE_FEZ_TODAS, "metade": FRASE_FEZ_METADE}.get(self.aviso)

    @property
    def comando(self) -> str | None:
        return comando_de_gerar(self.no, self.pedir) if self.pedir else None

    @property
    def nome(self) -> str:
        """O caminho sem a materia: "Infração penal: elementos, espécies"."""
        return arvore.SEPARADOR.join(arvore.partes(self.no)[1:]) or self.no


def geradas_por_no(questoes: int, nos: list[str], ja: dict,
                   feitas: dict | None = None) -> list[GeradasDoNo]:
    """As questoes da faixa divididas entre os nos dela, por igual (o resto
    vai para os primeiros), e quantas pedir em cada um: a cota menos as
    geradas que o no ja tem, no minimo PEDIDO_MINIMO_DE_GERADAS. No com o
    bastante nao pede nada - a nao ser que eu ja tenha feito metade ou todas
    (`feitas`, decisao 142): ai pede a cota, no minimo o mesmo piso."""
    if not nos:
        return []
    feitas = feitas or {}
    base, resto = divmod(max(questoes or 0, 0), len(nos))
    saida = []
    for posicao, no in enumerate(nos):
        cota = base + (1 if posicao < resto else 0)
        geradas = int(ja.get(no, 0))
        falta = max(cota - geradas, 0)
        pedir = max(falta, PEDIDO_MINIMO_DE_GERADAS) if falta else 0
        item = GeradasDoNo(no=no, geradas=geradas, cota=cota, pedir=pedir,
                           feitas=min(int(feitas.get(no, 0)), geradas))
        if not pedir and item.aviso:
            item = replace(item, pedir=max(cota, PEDIDO_MINIMO_DE_GERADAS))
        saida.append(item)
    return saida


@dataclass(frozen=True)
class GeradasDaFaixa:
    """O que a faixa de questoes diz das geradas: o tema, o no, o Qconcursos
    e os passos. `sem_no` quando a arvore nao tem no para o tema."""

    tema: str
    materia: str
    questoes: int
    filtro: str | None
    nos: tuple = ()               # (GeradasDoNo, ...)
    sem_no: bool = False

    @property
    def precisa_gerar(self) -> bool:
        return any(n.pedir for n in self.nos)

    @property
    def passos(self) -> list[str]:
        """Os 3 passos, com os comandos exatos: um pedido por no que falta, o
        Claude Code e a importacao. Vazio quando nada falta."""
        if not self.precisa_gerar:
            return []
        return ([n.comando for n in self.nos if n.comando]
                + [PASSO_NO_CLAUDE_CODE, COMANDO_DE_IMPORTAR])

    @property
    def nos_com_geradas(self) -> list[str]:
        """Os nos que entram no "Treinar geral": so os que tem gerada."""
        return [n.no for n in self.nos if n.geradas]

    @property
    def geral(self) -> int:
        """Quantas o "Treinar geral" sugere: as do plano, sem passar das
        geradas dos nos nem de 30. Zero com menos de 2 nos com gerada: com um
        so, o geral seria o mesmo botao do no."""
        if len(self.nos_com_geradas) < 2:
            return 0
        tem = sum(n.geradas for n in self.nos)
        return min(tem, self.questoes or tem, 30)


def geradas_da_faixa(faixa, escrita: "FichaEscrita | None", ja: dict,
                     feitas: dict | None = None) -> GeradasDaFaixa:
    """As geradas de uma faixa de questoes. Os nos sao os da ficha (decisao
    71); sem ficha, os `nos` do plano ou o `conteudo`. A ficha SEM no fica sem
    no - o assunto que ela escreve pode ser a lei inteira, e contar as geradas
    dele seria aproximar."""
    materia = getattr(faixa, "materia", None) or ""
    tema = escrita.tema if escrita is not None else tema_da_faixa(faixa.titulo, materia)
    if escrita is not None:
        nos = list(escrita.nos)
    else:
        nos = list(getattr(faixa, "nos", ()) or ())
        if not nos and getattr(faixa, "conteudo", None):
            nos = [faixa.conteudo]
    questoes = getattr(faixa, "questoes", 0) or 0
    return GeradasDaFaixa(
        tema=tema, materia=materia, questoes=questoes,
        filtro=getattr(faixa, "filtro", None),
        nos=tuple(geradas_por_no(questoes, nos, ja, feitas)), sem_no=not nos)
