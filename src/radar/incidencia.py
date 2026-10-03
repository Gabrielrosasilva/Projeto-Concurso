"""O mapa de incidencia do concurso-alvo, por no da arvore. Puro: so conta.

O que ele responde, para cada materia, assunto, subassunto e elemento: em
quantas questoes e em quantas provas do ALVO aquele conteudo apareceu, em
que anos e de que tipo. Nada mais - e nunca o que "vai cair" (regra
inviolavel 2). Toda linha leva a amostra ("8 questoes · 2 provas"), e o
denominador e o numero de provas que tinham aquela materia: LEP so caiu em
2019, e "apareceu em 1 de 2 provas" enganaria quando o edital de 2013 nem
cobrava LEP.

Ficam FORA da conta, e aparecem a parte com o numero:
- a questao anulada (a banca desfez a pergunta);
- a questao pendente (sem classificacao segura nao ha no onde contar).

O complementar nao entra aqui: este mapa e so do alvo (regra inviolavel 1).
"""
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from radar import config
from radar import conteudos as arvore

FRASE_SEM_EVIDENCIA = "Não há evidência suficiente no acervo para afirmar isso."


@dataclass
class Ocorrencia:
    """Uma questao do alvo, do jeito que o mapa precisa dela."""
    prova: str                 # o caderno (a "prova" do denominador)
    ano: int | None
    materia: str | None        # o no da materia em que ela conta
    conteudo: str | None       # o no da classificacao principal
    status: str                # completa | parcial | pendente
    anulada: bool = False
    tipo_de_questao: str | None = None
    pegadinha: str | None = None
    #: Para os padroes (forma de perguntar, gabarito, termos).
    enunciado: str = ""
    resposta: str | None = None
    #: O `macetes.uma_por_enunciado` agrupa por este nome. Aqui vai a CHAVE
    #: da questao inteira: duas questoes de enunciado igual sao duas.
    impressao: str = ""
    #: O numero da questao no caderno. A ficha de estudo (Etapa 6B) escreve
    #: "2013-q15", e e por ele que eu acho a questao na prova.
    numero: int | None = None
    #: A classificacao principal ja foi conferida por mim? O alvo foi (02/10);
    #: o complementar ainda nao (decisao 18), e a ficha diz qual e qual.
    conferida: bool = False


@dataclass
class Minimos:
    questoes: int = 3
    provas: int = 2


def carregar_minimos(caminho: Path | None = None) -> Minimos:
    arquivo = caminho or (config.diretorio_config() / "amostra.yml")
    if not Path(arquivo).exists():
        return Minimos()
    acervo = (yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}).get("acervo") or {}
    return Minimos(questoes=int(acervo.get("minimo_questoes", 3)),
                   provas=int(acervo.get("minimo_provas", 2)))


def amostra(questoes: int, provas: int) -> str:
    """"8 questões · 2 provas": a amostra que toda linha leva."""
    q = "questão" if questoes == 1 else "questões"
    p = "prova" if provas == 1 else "provas"
    return f"{questoes} {q} · {provas} {p}"


def rotulo(provas_com: int, denominador: int) -> str:
    """O que aconteceu, sem previsao: "apareceu nas 2 provas", "apareceu em
    1 de 2 provas", "não apareceu nas provas analisadas"."""
    if provas_com == 0:
        return "não apareceu nas provas analisadas"
    if denominador == 1:
        return "apareceu na única prova que cobrava a matéria"
    if provas_com == denominador:
        return f"apareceu nas {denominador} provas"
    return f"apareceu em {provas_com} de {denominador} provas"


@dataclass
class LinhaDoMapa:
    caminho: str
    nivel: str
    nome: str
    profundidade: int
    fora_do_edital: bool = False
    #: As questoes que contam: nem anulada, nem pendente.
    questoes: list[Ocorrencia] = field(default_factory=list)
    denominador: int = 0

    @property
    def provas(self) -> set[str]:
        return {o.prova for o in self.questoes}

    @property
    def anos(self) -> list[int]:
        return sorted({o.ano for o in self.questoes if o.ano})

    @property
    def tipos(self) -> list[tuple[str, int]]:
        return Counter(o.tipo_de_questao for o in self.questoes
                       if o.tipo_de_questao).most_common()

    @property
    def amostra(self) -> str:
        return amostra(len(self.questoes), len(self.provas))

    @property
    def rotulo(self) -> str:
        return rotulo(len(self.provas), self.denominador)


@dataclass
class MapaDaMateria:
    materia: str
    linhas: list[LinhaDoMapa]
    provas: int = 0
    anuladas: int = 0
    pendentes: int = 0

    @property
    def topo(self) -> LinhaDoMapa:
        return self.linhas[0]


def _debaixo(caminho: str | None, no: str) -> bool:
    return bool(caminho) and (caminho == no or caminho.startswith(no + arvore.SEPARADOR))


def validas(ocorrencias: list[Ocorrencia]) -> list[Ocorrencia]:
    """As que CONTAM: nem anulada (a banca desfez a pergunta), nem pendente
    (sem classificacao segura nao ha no onde contar). Uma regra so, para o
    mapa e para a ficha de estudo dizerem o mesmo numero."""
    return [o for o in ocorrencias
            if not o.anulada and o.status != "pendente" and o.conteudo]


def provas_da_materia(ocorrencias: list[Ocorrencia], materia: str) -> int:
    """O denominador: em quantas provas a materia teve questao. LEP so caiu
    em 2019, e "1 de 2 provas" enganaria quando o edital de 2013 nem a
    cobrava."""
    return len({o.prova for o in ocorrencias if o.materia == materia})


def montar(nos: list[arvore.No], ocorrencias: list[Ocorrencia]) -> list[MapaDaMateria]:
    """O mapa, materia por materia, na ordem da arvore.

    `nos` vem na ordem da arvore (pai antes dos filhos). A questao conta no no
    da sua classificacao principal e em todos os que estao acima dele.
    """
    contam = validas(ocorrencias)
    mapas = []
    for materia in (n for n in nos if n.nivel == "materia"):
        da_materia = [o for o in ocorrencias if o.materia == materia.caminho]
        denominador = provas_da_materia(ocorrencias, materia.caminho)
        linhas = []
        for no in nos:
            if not _debaixo(no.caminho, materia.caminho):
                continue
            linhas.append(LinhaDoMapa(
                caminho=no.caminho, nivel=no.nivel, nome=no.nome,
                profundidade=len(arvore.partes(no.caminho)) - 1,
                fora_do_edital=no.fora_do_edital,
                questoes=[o for o in contam if _debaixo(o.conteudo, no.caminho)],
                denominador=denominador))
        # Materia sem questao nenhuma no alvo continua no mapa: o edital a
        # cobra, e "não apareceu" tambem e informacao.
        mapas.append(MapaDaMateria(
            materia=materia.caminho, linhas=linhas, provas=denominador,
            anuladas=sum(1 for o in da_materia if o.anulada),
            pendentes=sum(1 for o in da_materia if not o.anulada and o.status == "pendente")))
    return mapas


# --- a linha do acervo complementar (secao 4) -----------------------------------

def complementar_por_no(nos: list[arvore.No], ocorrencias: list[Ocorrencia]) -> dict:
    """{caminho do no: LinhaComplementar}, do acervo complementar FEPESE.

    Linha SEPARADA da do alvo, e nunca somada a ela (regra inviolavel 1):
    "Policia Penal SC: 2 questoes · 2 provas · Acervo complementar FEPESE:
    30 questoes · 12 provas".

    A diferenca para a conta do alvo: aqui a questao SEM classificacao conta
    na materia, porque o proprio caderno diz a materia dela ("Lingua
    Portuguesa"), e isso e evidencia, nao palpite. Abaixo da materia so conta
    a classificada - sem classificacao nao ha como saber o assunto, e
    inventar um seria o que a regra 9 proibe. Quantas ainda faltam
    classificar vai escrito na linha.

    Anulada continua fora: a banca desfez a pergunta.
    """
    sem_anulada = [o for o in ocorrencias if not o.anulada and o.conteudo]
    return {no.caminho: _linha_complementar(
                no.caminho, [o for o in sem_anulada if _debaixo(o.conteudo, no.caminho)])
            for no in nos}


def _linha_complementar(caminho: str, debaixo: list[Ocorrencia]):
    """A linha complementar de um conjunto de questoes. A conta mora aqui, e
    so aqui: o no da arvore e o escopo da ficha de estudo usam a mesma."""
    from radar.complementar import LinhaComplementar

    # A mesma questao em dez cadernos e UMA questao: a chave desempata.
    distintas = {o.impressao or f"{o.prova}-{id(o)}": o for o in debaixo}
    return LinhaComplementar(
        caminho=caminho,
        questoes=len(distintas),
        ocorrencias=len(debaixo),
        provas=len({o.prova for o in debaixo}),
        classificadas=sum(1 for o in distintas.values() if o.status != "pendente"))


# --- um escopo que nao e um no so (a ficha de estudo, Etapa 6B) -------------------
#
# "Art. 5º, caput e incisos I a XVI" cobre tres subassuntos de um assunto e o
# caput, que no edital e outro assunto. A ficha guarda a lista de nos, e estas
# duas funcoes contam a lista com as MESMAS regras do mapa: nada de conta
# paralela.

def linha_do_escopo(caminho: str, nome: str, dentro, materia: str,
                    ocorrencias: list[Ocorrencia]) -> LinhaDoMapa:
    """A linha do alvo para um escopo: as questoes que contam dentro dele, e o
    denominador da materia. `dentro(caminho)` diz se um no esta no escopo."""
    return LinhaDoMapa(
        caminho=caminho, nivel="escopo", nome=nome,
        profundidade=0,
        questoes=[o for o in validas(ocorrencias) if dentro(o.conteudo)],
        denominador=provas_da_materia(ocorrencias, materia))


def complementar_do_escopo(caminho: str, dentro, ocorrencias: list[Ocorrencia]):
    """A linha complementar para um escopo, separada da do alvo e nunca
    somada a ela. Abaixo da materia so conta a questao classificada."""
    return _linha_complementar(
        caminho, [o for o in ocorrencias
                  if not o.anulada and o.conteudo and o.status != "pendente"
                  and dentro(o.conteudo)])


# --- os padroes de cobranca (secao 13) ------------------------------------------

@dataclass
class Padroes:
    """O padrao identificado no acervo analisado, num no. Ou a frase padrao."""
    suficiente: bool
    amostra: str
    frase: str = ""
    comandos: list = field(default_factory=list)
    gabarito: list = field(default_factory=list)
    termos: list = field(default_factory=list)
    tipos: list = field(default_factory=list)
    pegadinhas: list[str] = field(default_factory=list)


def padroes(linha: LinhaDoMapa, minimos: Minimos) -> Padroes:
    """Forma de perguntar, gabarito, termos, tipo de questao e pegadinhas do
    no - so com a amostra minima. Abaixo dela, a frase exata."""
    from radar import macetes

    questoes = linha.questoes
    provas = len(linha.provas)
    texto_da_amostra = f"padrão identificado no acervo analisado: {linha.amostra} · alvo"
    if len(questoes) < minimos.questoes or provas < minimos.provas:
        return Padroes(suficiente=False, amostra=texto_da_amostra, frase=FRASE_SEM_EVIDENCIA)
    unicas = macetes.uma_por_enunciado(questoes)
    gabarito, _ = macetes.distribuicao_do_gabarito(unicas)
    return Padroes(
        suficiente=True, amostra=texto_da_amostra,
        comandos=macetes.contar_comandos(unicas),
        gabarito=gabarito,
        termos=macetes.termos_frequentes(unicas, 8),
        tipos=linha.tipos,
        pegadinhas=[o.pegadinha for o in questoes if o.pegadinha],
    )
