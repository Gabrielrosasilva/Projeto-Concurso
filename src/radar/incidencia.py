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
A linha e os padroes do complementar tem funcoes proprias, mais abaixo, e
nunca se somam aos do alvo (decisao 78).
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from radar import config
from radar import conteudos as arvore
from radar.regioes import normalizar
# A frase da regra inviolavel 4 mora no origem.py, a mesma em todo lugar.
from radar.origem import FRASE_SEM_EVIDENCIA


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
    #: Os outros nos que a questao tambem cobra - as classificacoes
    #: associadas (§14, item 7; decisao 86). Nunca contam na incidencia.
    associados: tuple = ()
    #: O exemplo real da ficha mostra a questao inteira (R1, 05/10): as
    #: alternativas como estao no caderno, {"a": "...", ...}.
    alternativas: dict = field(default_factory=dict)
    #: O dispositivo que a classificacao gravou ("art. 8º do Código Penal").
    #: E por ele que a pendente e a ficha sem no chegam ao tema.
    dispositivo: str | None = None
    #: O no da materia que o CADERNO declara. A de 2013 que foi para um
    #: assunto de 2019 conta noutra materia, mas o caderno diz se a materia
    #: existia naquela prova ("—").
    materia_do_caderno: str | None = None
    #: A impressao do ENUNCIADO (QuestaoDeProva.impressao), por onde a
    #: explicacao escrita (data/explicacoes.json) acha a questao.
    impressao_do_enunciado: str = ""
    #: O texto de apoio que a questao cita (QuestaoDeProva.texto_base): sem
    #: ele, o exemplo de interpretacao na ficha nao se le (item 4, 06/10).
    texto_base: str | None = None


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


# --- os conceitos associados (§14, item 7) --------------------------------------
#
# "Quais conceitos aparecem associados": o no principal da questao e os outros
# que ela tambem cobra, no enunciado ou nas alternativas. So o alvo, e so as
# questoes que contam. A contagem da incidencia nao muda: la so entra a
# principal (decisao 86).

@dataclass(frozen=True)
class Associacao:
    """Dois conceitos que caem na mesma questao."""

    principal: str
    associado: str
    #: "2019 q83", uma por questao distinta, na ordem.
    questoes: tuple

    @property
    def nome_principal(self) -> str:
        return arvore.partes(self.principal)[-1]

    @property
    def nome_associado(self) -> str:
        return arvore.partes(self.associado)[-1]


def associacoes(ocorrencias: list[Ocorrencia], materia: str) -> list[Associacao]:
    """Os pares principal + associado das questoes que contam na materia, do
    que mais aparece ao que menos. Sem associado classificado, lista vazia."""
    pares: dict[tuple, dict] = {}
    for o in validas(ocorrencias):
        if o.materia != materia:
            continue
        for associado in o.associados:
            # Pela chave: a mesma questao em dois cadernos e uma so.
            pares.setdefault((o.conteudo, associado), {})[o.impressao] = (
                f"{o.ano} q{o.numero}")
    saida = [Associacao(principal=p, associado=a, questoes=tuple(sorted(codigos.values())))
             for (p, a), codigos in pares.items()]
    saida.sort(key=lambda x: (-len(x.questoes), x.principal, x.associado))
    return saida


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
    # Cada questao entra direto no no dela e nos de cima, na ordem em que
    # veio. Perguntar a cada no da arvore se cada questao esta debaixo dele
    # eram 770 mil comparacoes por pagina, para o mesmo resultado.
    debaixo_de: dict[str, list[Ocorrencia]] = {}
    for o in ocorrencias:
        if o.anulada or not o.conteudo:
            continue
        for caminho in _o_no_e_os_de_cima(o.conteudo):
            debaixo_de.setdefault(caminho, []).append(o)
    return {no.caminho: _linha_complementar(no.caminho, debaixo_de.get(no.caminho, []))
            for no in nos}


def _o_no_e_os_de_cima(caminho: str) -> list[str]:
    """"A > B > C" da ["A", "A > B", "A > B > C"]: exatamente os nos para os
    quais `_debaixo(caminho, no)` e verdade."""
    cortes = [i for i in range(len(caminho))
              if caminho.startswith(arvore.SEPARADOR, i)]
    return [caminho[:i] for i in cortes] + [caminho]


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
    #: O que a tela precisa saber da classificacao por tras do tipo de questao
    #: e das pegadinhas. Vazio no alvo, que foi todo conferido (02/10).
    nota: str = ""


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


# --- os padroes do acervo complementar (secao 13: a origem dita) -----------------
#
# "Todo padrao deve indicar em quantas questoes e em quantas provas ele foi
# observado, e se veio do concurso-alvo ou do acervo complementar." Os padroes
# do complementar sao os MESMOS do alvo, contados a parte e nunca somados. Quem
# chama passa so as questoes das provas com gabarito DEFINITIVO (o
# `entra_nos_padroes` da validacao da Etapa 3B): padrao de cobranca se mede
# sobre a letra certa, e o gabarito provisorio muda depois dos recursos.

def padroes_complementares(caminho: str, ocorrencias: list[Ocorrencia],
                           minimos: Minimos) -> Padroes:
    """Os padroes de um no no acervo complementar FEPESE.

    As mesmas regras da linha complementar do no: na materia conta a questao
    que o caderno poe nela, mesmo sem classificar; abaixo da materia, so a
    classificada.
    """
    na_materia = len(arvore.partes(caminho)) == 1
    return _padroes_do_complementar(
        [o for o in ocorrencias
         if not o.anulada and _debaixo(o.conteudo, caminho)
         and (na_materia or o.status != "pendente")],
        minimos)


def padroes_complementares_do_escopo(dentro, ocorrencias: list[Ocorrencia],
                                     minimos: Minimos) -> Padroes:
    """Os mesmos padroes para o escopo de uma ficha (uma lista de nos): so a
    questao classificada, como no `complementar_do_escopo`."""
    return _padroes_do_complementar(
        [o for o in ocorrencias
         if not o.anulada and o.conteudo and o.status != "pendente"
         and dentro(o.conteudo)],
        minimos)


def _padroes_do_complementar(contam: list[Ocorrencia], minimos: Minimos) -> Padroes:
    """A conta e em questao DISTINTA, pela chave: a FEPESE repete o mesmo
    caderno em dezenas de cargos, e contar a repeticao inflaria o acervo e
    puxaria o gabarito para a letra da questao repetida.

    Forma de perguntar, gabarito e termos saem do texto do caderno e do
    gabarito oficial. Tipo de questao e pegadinha saem da CLASSIFICACAO, e so
    da conferida: a do complementar e automatica e ainda nao foi conferida
    (decisao 78), e texto que ninguem conferiu nao vira padrao do acervo.
    """
    from radar import macetes

    unicas = macetes.uma_por_enunciado(contam)
    provas = len({o.prova for o in contam})
    texto_da_amostra = (f"padrão identificado no acervo analisado: "
                        f"{amostra(len(unicas), provas)} · acervo complementar FEPESE, "
                        f"só das provas com gabarito definitivo")
    if len(unicas) < minimos.questoes or provas < minimos.provas:
        return Padroes(suficiente=False, amostra=texto_da_amostra, frase=FRASE_SEM_EVIDENCIA)

    conferidas = [o for o in unicas if o.conferida]
    classificadas = sum(1 for o in unicas if o.status != "pendente")
    if conferidas:
        quantas = (f"da {len(conferidas)} questão" if len(conferidas) == 1
                   else f"das {len(conferidas)} questões")
        nota = (f"Tipo de questão e pegadinhas: só {quantas} com classificação "
                f"conferida (de {len(unicas)}).")
    else:
        nota = (f"Tipo de questão e pegadinhas: só da classificação conferida, e "
                f"nenhuma questão deste conteúdo foi conferida ainda "
                f"({classificadas} de {len(unicas)} classificadas automaticamente).")
    gabarito, _ = macetes.distribuicao_do_gabarito(unicas)
    return Padroes(
        suficiente=True, amostra=texto_da_amostra,
        comandos=macetes.contar_comandos(unicas),
        gabarito=gabarito,
        termos=macetes.termos_frequentes(unicas, 8),
        tipos=Counter(o.tipo_de_questao for o in conferidas
                      if o.tipo_de_questao).most_common(),
        pegadinhas=[o.pegadinha for o in conferidas if o.pegadinha],
        nota=nota,
    )


# --- caiu ou nao caiu: o tema nas provas do alvo, prova a prova (R1, 05/10) -------
#
# A pergunta da ficha, da faixa e da aba Fichas: "este tema caiu?". Uma conta
# so, aqui, para as tres telas e para a redistribuicao do Ciclo 1 dizerem a
# mesma coisa. Tres fontes, nesta ordem, e nunca aproximadas:
#
#   1. a questao classificada num no do tema (a mesma regra do mapa);
#   2. sem no na ficha, a questao classificada na materia cujo ARTIGO gravado
#      (o `dispositivo` da classificacao) cai na faixa de artigos do tema
#      ("LEP, arts. 28 a 37") - e a lei do artigo tem de ser a do tema;
#   3. a questao PENDENTE da materia com o artigo na faixa do tema. Ela caiu,
#      mas nao tem no onde contar (o tema esta fora do programa de 2019): vai
#      a parte, com o aviso, e nunca entra no mapa do no.
#
# A anulada continua fora da conta e aparece a parte.

#: A classe do tema na redistribuicao do Ciclo 1 (decisoes da R1):
#: caiu nas provas que bastam (o minimo do config/amostra.yml) = cheio;
#: caiu numa so = normal; nao caiu, com a materia em provas que bastam e
#: com o tema contado = basico. Sem contagem, ou com uma prova so, o tema
#: NAO e rebaixado: sem evidencia nao se rebaixa ninguem.
CHEIO, NORMAL, BASICO = "cheio", "normal", "basico"

#: Como o dispositivo cita a lei de cada materia, sem acento e sem caixa. So
#: serve para a ficha chegar a questao pelo artigo; lei que nao esta aqui nao
#: e reconhecida, e nada e contado por ela.
LEI_DO_DISPOSITIVO = {
    "CP": ("codigo penal",),
    "CPP": ("codigo de processo penal",),
    "CF": ("constituicao federal",),
    "LEP": ("7.210", "execucao penal"),
}

#: A lei da materia, quando a ficha nao diz a sigla no elemento.
LEI_DA_MATERIA = {
    "Direito Penal": "CP",
    "Direito Processual Penal": "CPP",
    "Direito Constitucional": "CF",
    "Lei de Execução Penal": "LEP",
}

_NUMERO = r"(\d+)\s*[ºo°]?(?:\s*-\s*([A-Z]))?"
_FAIXA_DE_ARTIGOS = re.compile(
    r"\b[Aa]rts?\.\s*" + _NUMERO + r"(?:\s*(?:a|até)\s*" + _NUMERO + r")?")
_SIGLA = re.compile(r"^\s*(CPP|CP|CF|LEP)\b")
_INICIO_DE_ARTIGO = re.compile(r"\b[Aa]rts?\.\s*")
# Onde a lista de artigos de um dispositivo acaba: no paragrafo, na lei
# ("da Lei", "do Código") ou no parentese.
_FIM_DA_LISTA = re.compile(r"§|\bd[ao]s?\b|\(|;")
_ARTIGO = re.compile(_NUMERO)


@dataclass(frozen=True)
class FaixaDeArtigos:
    """"LEP, arts. 28 a 37" -> lei LEP, do (28, "") ao (37, "")."""

    lei: str
    inicio: tuple
    fim: tuple

    def contem(self, artigo: tuple) -> bool:
        return self.inicio <= artigo <= self.fim


def _artigo(numero: str, letra: str | None) -> tuple:
    return (int(numero), (letra or "").upper())


def faixa_de_artigos(texto: str | None, materia: str | None = None) -> FaixaDeArtigos | None:
    """A faixa de artigos de um tema, pelo elemento ou pelo titulo da ficha.

    A lei sai da sigla do comeco ("LEP, arts. ...") ou, sem ela, da materia
    (LEI_DA_MATERIA). Sem faixa no texto, ou sem lei conhecida, None: o tema
    nao chega a questao pelo artigo.
    """
    if not texto:
        return None
    achado = _FAIXA_DE_ARTIGOS.search(texto)
    if achado is None:
        return None
    sigla = _SIGLA.match(texto)
    lei = sigla.group(1) if sigla else LEI_DA_MATERIA.get(materia or "")
    if lei not in LEI_DO_DISPOSITIVO:
        return None
    inicio = _artigo(achado.group(1), achado.group(2))
    fim = _artigo(achado.group(3), achado.group(4)) if achado.group(3) else inicio
    return FaixaDeArtigos(lei, inicio, fim)


def artigos_do_dispositivo(dispositivo: str | None) -> list[tuple]:
    """Os artigos que o dispositivo cita: "art. 8º do Código Penal (alternativas
    também dos arts. 2º, 3º e 4º)" -> [(8,""), (2,""), (3,""), (4,"")]. Numero
    de paragrafo e de inciso nao entram."""
    artigos = []
    for inicio in _INICIO_DE_ARTIGO.finditer(dispositivo or ""):
        resto = dispositivo[inicio.end():]
        fim = _FIM_DA_LISTA.search(resto)
        trecho = resto[:fim.start()] if fim else resto
        artigos += [_artigo(n, l) for n, l in _ARTIGO.findall(trecho)]
    return artigos


def no_tema_pelo_artigo(o: Ocorrencia, faixa: FaixaDeArtigos | None) -> bool:
    """A questao cita, no dispositivo gravado, um artigo da faixa e a lei dela?"""
    if faixa is None or not o.dispositivo:
        return False
    texto = normalizar(o.dispositivo)
    if not any(marca in texto for marca in LEI_DO_DISPOSITIVO[faixa.lei]):
        return False
    return any(faixa.contem(a) for a in artigos_do_dispositivo(o.dispositivo))


@dataclass(frozen=True)
class ProvaDoAlvo:
    """Uma prova do alvo, vista de um tema."""

    ano: int | None
    #: O caderno daquele ano tinha a materia? Sem ela, a tela escreve "—".
    tinha_a_materia: bool
    contadas: tuple = ()      # "2013-q7"
    pendentes: tuple = ()

    @property
    def total(self) -> int:
        return len(self.contadas) + len(self.pendentes)


def _codigo_da(o: Ocorrencia) -> str:
    return f"{o.ano}-q{o.numero}" if o.numero else str(o.ano)


@dataclass
class CaiuNoAlvo:
    """O que as provas do alvo dizem de um tema, prova a prova."""

    provas: list                      # [ProvaDoAlvo], do ano mais velho ao mais novo
    contadas: list                    # [Ocorrencia] que contam (no, ou artigo)
    pendentes: list                   # [Ocorrencia] pendentes com o artigo do tema
    anuladas: list                    # [Ocorrencia] a parte, fora da conta
    pelo_artigo: bool                 # as contadas sairam do artigo, e nao do no
    sem_contagem: bool                # sem no e sem faixa de artigos: nada contado
    minimo_provas: int = 2

    @property
    def provas_com(self) -> int:
        return len({o.prova for o in self.contadas + self.pendentes})

    @property
    def provas_da_materia(self) -> int:
        return sum(1 for p in self.provas if p.tinha_a_materia)

    @property
    def questoes(self) -> int:
        return len(self.contadas) + len(self.pendentes)

    @property
    def amostra(self) -> str:
        return amostra(self.questoes, self.provas_com)

    @property
    def caiu(self) -> bool:
        return self.questoes > 0

    @property
    def classe(self) -> str:
        if self.provas_com >= self.minimo_provas:
            return CHEIO
        if self.provas_com:
            return NORMAL
        if self.sem_contagem or self.provas_da_materia < self.minimo_provas:
            return NORMAL
        return BASICO

    @property
    def por_prova(self) -> str:
        """"2013: — · 2019: 1": cada prova com o seu numero, nunca somadas."""
        partes = []
        for p in self.provas:
            if not p.tinha_a_materia and not p.total:
                partes.append(f"{p.ano}: —")
            else:
                partes.append(f"{p.ano}: {p.total}")
        return " · ".join(partes)

    @property
    def frase(self) -> str:
        """A frase da tela, sem previsao: o que aconteceu nas provas."""
        if self.sem_contagem:
            return ("O tema não tem nó na árvore nem faixa de artigos: o acervo "
                    "não foi contado para ele.")
        com = [p for p in self.provas if p.total]
        if com:
            anos = " e ".join(str(p.ano) for p in com)
            texto = f"Caiu em {anos}: {self.amostra}"
            if self.provas_da_materia == 1:
                texto += ", a única prova que cobrava a matéria"
            return texto + "."
        tinham = [str(p.ano) for p in self.provas if p.tinha_a_materia]
        if len(tinham) >= self.minimo_provas:
            return (f"Não apareceu nas provas de {' e '.join(tinham)} analisadas: "
                    f"prioridade baixa, estude o básico.")
        if tinham:
            return f"Não apareceu na prova de {tinham[0]}, a única que cobrava a matéria."
        return "A matéria não estava nas provas do alvo analisadas."

    @property
    def notas(self) -> list[str]:
        """O que a frase precisa ter ao lado para ser honesta."""
        saida = []
        if self.pendentes:
            codigos = ", ".join(_codigo_da(o) for o in self.pendentes)
            saida.append(f"{len(self.pendentes)} com classificação pendente ({codigos}): "
                         f"o artigo gravado é do tema, mas não há nó onde contar "
                         f"(fora do programa de 2019, ou classificação insegura).")
        if self.pelo_artigo and self.contadas:
            saida.append("Contadas pelo artigo gravado na classificação: a ficha não "
                         "aponta nó da árvore.")
        if (not self.caiu and not self.sem_contagem
                and self.provas_da_materia < self.minimo_provas):
            saida.append(f"Base de uma prova só, e o tema não é rebaixado: "
                         f"{FRASE_SEM_EVIDENCIA}")
        if self.anuladas:
            codigos = ", ".join(_codigo_da(o) for o in self.anuladas)
            saida.append(f"Fora da conta: anulada(s) {codigos}.")
        return saida


def caiu_no_alvo(ocorrencias: list[Ocorrencia], *, materia: str, dentro,
                 tem_no: bool, faixa: FaixaDeArtigos | None = None,
                 minimo_provas: int = 2) -> CaiuNoAlvo:
    """O tema nas provas do alvo. `dentro(caminho)` e o escopo da ficha (os
    nos); `tem_no` falso quando a ficha nao aponta no. `faixa` e a faixa de
    artigos do tema, ou None."""
    pelo_artigo = not tem_no and faixa is not None
    if tem_no:
        contadas = [o for o in validas(ocorrencias) if dentro(o.conteudo)]
    elif faixa is not None:
        contadas = [o for o in validas(ocorrencias)
                    if o.materia == materia and no_tema_pelo_artigo(o, faixa)]
    else:
        contadas = []
    pendentes = [o for o in ocorrencias
                 if not o.anulada and o.status == "pendente" and o.materia == materia
                 and no_tema_pelo_artigo(o, faixa)]
    anuladas = [o for o in ocorrencias if o.anulada and (
        (tem_no and dentro(o.conteudo))
        or (o.materia == materia and no_tema_pelo_artigo(o, faixa)))]

    provas = []
    for prova, ano in sorted({(o.prova, o.ano) for o in ocorrencias},
                             key=lambda p: (p[1] or 0, p[0])):
        tinha = any(o.prova == prova and (o.materia_do_caderno or o.materia) == materia
                    for o in ocorrencias)
        provas.append(ProvaDoAlvo(
            ano=ano, tinha_a_materia=tinha,
            contadas=tuple(_codigo_da(o) for o in contadas if o.prova == prova),
            pendentes=tuple(_codigo_da(o) for o in pendentes if o.prova == prova)))
    return CaiuNoAlvo(provas=provas, contadas=contadas, pendentes=pendentes,
                      anuladas=anuladas, pelo_artigo=pelo_artigo,
                      sem_contagem=not tem_no and faixa is None,
                      minimo_provas=minimo_provas)
