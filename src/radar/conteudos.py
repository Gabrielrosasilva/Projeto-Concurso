"""A arvore de conteudos e as regras dela. Puro: nao fala com banco nem rede.

    materia > assunto > subassunto > elemento

Os dois niveis de baixo sao opcionais: "Lingua Portuguesa > Emprego da
crase" ja e um no completo, e o Direito desce ate "CP, art. 2º" quando a
questao chega la. O que e "elemento" depende da materia, e a lista mora no
config/taxonomia.yml - ampliar a lista nao muda o banco.

Todo no e reconhecido pelo CAMINHO de nomes ("Direito Penal > Imputabilidade
penal"): e assim que a questao, a faixa do cronograma, o erro anotado e a
questao gerada apontam para ele. O id do banco muda quando o banco e refeito;
o caminho, nao.

A semente e o edital: as materias e os assuntos com o texto LITERAL do anexo
de programas, inclusive os defeitos dele (o `edital_programa` explica por
que). Nada aqui inventa no para caber uma classificacao: o que nao casa fica
pendente (regra inviolavel 9).
"""
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from radar import config
from radar.regioes import normalizar

NIVEIS = ("materia", "assunto", "subassunto", "elemento")
#: O nivel como a tela escreve: o valor gravado e chave, sem acento.
NOME_DO_NIVEL = {"materia": "matéria", "assunto": "assunto",
                 "subassunto": "subassunto", "elemento": "elemento"}
SEPARADOR = " > "

ORIGENS = ("edital", "classificacao", "manual")

# De onde veio a semente. Um texto so, para a procedencia de todos os nos do
# edital dizer a mesma coisa.
PROCEDENCIA_DO_EDITAL = "edital de 2019 (anexo de programas)"


class ConteudoInvalido(ValueError):
    """Um no que nao cabe na arvore. A mensagem diz por que."""


@dataclass
class No:
    """Um no antes de ir para o banco (ou depois de sair dele, no JSON)."""
    caminho: str
    pai: str | None
    nivel: str
    nome: str
    ordem: int = 0
    origem: str = "edital"
    texto_do_edital: str | None = None
    fora_do_edital: bool = False
    procedencia: str | None = None
    tipo_elemento: str | None = None
    referencia: str | None = None


def caminho(pai: str | None, nome: str) -> str:
    """O caminho do filho `nome` debaixo de `pai`."""
    nome = " ".join((nome or "").split())
    if not nome:
        raise ConteudoInvalido("O nó precisa de nome.")
    if SEPARADOR.strip() in nome:
        # O ">" e o separador do caminho: dentro do nome ele partiria o no
        # em dois na volta do JSON.
        raise ConteudoInvalido(f"O nome não pode ter {SEPARADOR.strip()!r}: {nome!r}")
    return f"{pai}{SEPARADOR}{nome}" if pai else nome


def partes(caminho_do_no: str) -> list[str]:
    return caminho_do_no.split(SEPARADOR)


def nivel_do_filho(nivel_do_pai: str | None) -> str:
    """O nivel de quem nasce debaixo de um no desse nivel."""
    if nivel_do_pai is None:
        return NIVEIS[0]
    posicao = NIVEIS.index(nivel_do_pai)
    if posicao == len(NIVEIS) - 1:
        raise ConteudoInvalido("O elemento é o último nível: não tem filho.")
    return NIVEIS[posicao + 1]


# --- a taxonomia ----------------------------------------------------------------

@dataclass
class Taxonomia:
    #: {familia: (materias, elementos)}
    familias: dict[str, tuple[list[str], list[str]]]
    elementos_comuns: list[str]
    tipos_de_questao: list[str]
    #: [{"nome": ..., "procedencia": ...}]
    materias_fora_do_edital: list[dict]
    #: {nome antigo: nome do edital}
    sinonimos_de_materia: dict[str, str]

    def elementos_da_materia(self, materia: str) -> list[str]:
        """Os tipos de elemento que esta materia aceita."""
        alvo = normalizar(materia)
        for materias, elementos in self.familias.values():
            if any(normalizar(m) == alvo for m in materias):
                return list(self.elementos_comuns) + list(elementos)
        return list(self.elementos_comuns)

    def materia_do_texto(self, texto: str | None) -> str | None:
        """O nome do edital para um nome de materia escrito numa prova antiga,
        quando ha sinonimo declarado. None quando nao ha."""
        alvo = normalizar(texto or "")
        for antigo, novo in self.sinonimos_de_materia.items():
            if normalizar(antigo) == alvo:
                return novo
        return None

    def nome_do_edital(self, materia: str | None) -> str | None:
        """O nome do edital para qualquer grafia: o do sinonimo, ou o proprio."""
        return self.materia_do_texto(materia) or materia

    def grafias(self, materia: str) -> list[str]:
        """Todas as grafias que valem como esta materia nas provas: o nome do
        edital e os nomes antigos que o `sinonimos_de_materia` liga a ele.

        E por aqui que um filtro pela coluna `materia` das questoes acha as
        duas provas: a de 2013 grava "Direito Processo Penal", a de 2019
        "Direito Processual Penal" (auditoria de 04/10, BUG-4).
        """
        edital = self.nome_do_edital(materia)
        alvo = normalizar(edital)
        return [edital] + [antigo for antigo, novo in self.sinonimos_de_materia.items()
                           if normalizar(novo) == alvo]


#: Acima disto, dois nomes do mesmo nivel e da mesma materia sao o mesmo
#: conceito escrito de outro jeito ("Geracoes (dimensoes) de direitos" e
#: "... dos direitos humanos" ficam abaixo: o nome sozinho nao prova).
PARECIDO_O_BASTANTE = 0.9


def _palavras(nome: str) -> str:
    return " ".join(re.findall(r"\w+", normalizar(nome)))


def no_parecido(nos, materia: str, nivel: str, nome: str) -> str | None:
    """O caminho de um no que ja existe e parece o `nome` novo, ou None.

    Mesma materia e mesmo nivel; parecido e o nome igual (sem acento nem
    caixa), um contido no outro por palavra inteira ("Formas de violencia
    domestica" e "... e familiar"), ou quase igual. Existe porque a
    classificacao do complementar criou nos paralelos aos do alvo para o
    mesmo conceito (auditoria de 04/10, BUG-3): com isto ela e recusada e
    aponta o no que ja existe, em vez de criar outro.
    """
    novo = _palavras(nome)
    if not novo:
        return None
    for no in nos:
        if no.nivel != nivel or partes(no.caminho)[0] != materia:
            continue
        existente = _palavras(no.nome)
        if (existente == novo or f" {novo} " in f" {existente} "
                or f" {existente} " in f" {novo} "
                or SequenceMatcher(None, existente, novo).ratio() >= PARECIDO_O_BASTANTE):
            return no.caminho
    return None


def grafias_da_materia(materia: str) -> list[str]:
    """`Taxonomia.grafias`, com a taxonomia do config/. Para filtro de banco."""
    return carregar_taxonomia().grafias(materia)


def carregar_taxonomia(caminho_do_arquivo: Path | None = None) -> Taxonomia:
    arquivo = caminho_do_arquivo or (config.diretorio_config() / "taxonomia.yml")
    dados = yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}
    familias = {}
    for nome, bruta in (dados.get("familias") or {}).items():
        bruta = bruta or {}
        familias[nome] = ([str(m) for m in bruta.get("materias") or []],
                          [str(e) for e in bruta.get("elementos") or []])
    return Taxonomia(
        familias=familias,
        elementos_comuns=[str(e) for e in dados.get("elementos_comuns") or []],
        tipos_de_questao=[str(t) for t in dados.get("tipos_de_questao") or []],
        materias_fora_do_edital=list(dados.get("materias_fora_do_edital") or []),
        sinonimos_de_materia={str(k): str(v) for k, v
                              in (dados.get("sinonimos_de_materia") or {}).items()},
    )


def conferir_elemento(taxonomia: Taxonomia, materia: str, tipo: str | None) -> None:
    """Recusa o tipo de elemento que a familia da materia nao aceita."""
    if tipo is None:
        raise ConteudoInvalido("O elemento precisa de tipo (artigo, regra gramatical...).")
    aceitos = taxonomia.elementos_da_materia(materia)
    if tipo not in aceitos:
        raise ConteudoInvalido(
            f"{tipo!r} não é tipo de elemento de {materia} no config/taxonomia.yml "
            f"(aceitos: {', '.join(aceitos)})."
        )


# --- a semente ------------------------------------------------------------------

def semente(programa: dict[str, list[str]], taxonomia: Taxonomia) -> list[No]:
    """Os nos que o edital da: cada materia e os assuntos dela, literais.

    Mais as materias que cairam numa prova do alvo e nao estao no edital de
    agora (`materias_fora_do_edital`), marcadas assim - sem assunto, porque
    nao ha programa delas para copiar.
    """
    nos: list[No] = []
    for ordem, (materia, assuntos) in enumerate(programa.items()):
        nos.append(No(caminho=caminho(None, materia), pai=None, nivel="materia",
                      nome=materia, ordem=ordem, texto_do_edital=materia,
                      procedencia=PROCEDENCIA_DO_EDITAL))
        vistos = set()
        for posicao, assunto in enumerate(assuntos):
            filho = caminho(materia, assunto.replace(SEPARADOR.strip(), "-"))
            if filho in vistos:
                continue
            vistos.add(filho)
            nos.append(No(caminho=filho, pai=materia, nivel="assunto",
                          nome=partes(filho)[-1], ordem=posicao,
                          texto_do_edital=assunto, procedencia=PROCEDENCIA_DO_EDITAL))

    ja_tem = {normalizar(n.nome) for n in nos if n.nivel == "materia"}
    for posicao, fora in enumerate(taxonomia.materias_fora_do_edital):
        nome = str(fora.get("nome") or "").strip()
        if not nome or normalizar(nome) in ja_tem:
            continue
        nos.append(No(caminho=caminho(None, nome), pai=None, nivel="materia",
                      nome=nome, ordem=len(programa) + posicao, origem="manual",
                      fora_do_edital=True,
                      procedencia=str(fora.get("procedencia") or "") or None))
    return nos


def achar(caminhos: list[str], texto: str | None, pai: str | None = None) -> str | None:
    """O caminho cujo ultimo nome e IGUAL a `texto` (sem diferenca de
    maiuscula nem de acento), debaixo de `pai` (ou entre as materias, sem
    pai). None quando nao ha - e ai o texto fica pendente, nunca aproximado."""
    alvo = normalizar(texto or "")
    if not alvo:
        return None
    for candidato in caminhos:
        nomes = partes(candidato)
        mesmo_pai = (SEPARADOR.join(nomes[:-1]) or None) == pai
        if mesmo_pai and normalizar(nomes[-1]) == alvo:
            return candidato
    return None


# --- o escopo de um pedido de geracao (Etapa 5) ---------------------------------
#
# A secao 7 do pedido: "Lei de Execucao Penal" sozinho e amplo demais, e pode
# trazer questao de conteudo que eu nem estudei. O escopo e o caminho fechado
# materia > assunto > subassunto > elemento, e tudo o que for gerado tem de
# estar DENTRO dele.
#
# Duas regras que mandam aqui:
#
#   * **nada e aproximado.** Nome que nao existe na arvore nao vira o nome mais
#     parecido: o pedido PARA e devolve as sugestoes, para eu escolher. Alargar
#     o escopo sozinho e o defeito que esta etapa veio consertar;
#   * **o nivel de baixo exige o de cima.** Pedir subassunto sem assunto nao e
#     um escopo: e uma busca pelo nome, e duas materias podem ter subassunto de
#     nome igual.

#: Quantos nomes parecidos sugerir quando o pedido erra o nome. Cinco e o que
#: cabe numa linha de terminal sem virar lista para estudar.
QUANTAS_SUGESTOES = 5

#: Abaixo desta semelhanca o nome nem e sugerido: sugerir qualquer coisa e pior
#: que dizer "nao achei", porque convida a aceitar o que nao e.
SEMELHANCA_MINIMA = 0.5


class EscopoInvalido(ValueError):
    """Um nome que a arvore nao tem. A mensagem traz as sugestoes."""

    def __init__(self, mensagem: str, sugestoes: list[str] | None = None):
        super().__init__(mensagem)
        self.sugestoes = sugestoes or []


@dataclass(frozen=True)
class Escopo:
    """O escopo fechado de um pedido: o no mais fundo, e os elementos dele.

    `elementos` so e preenchido quando eu pedi elemento explicitamente. Vazio,
    o escopo e o no e TUDO abaixo dele.
    """

    no: str
    nivel: str
    elementos: tuple = ()

    @property
    def materia(self) -> str:
        return partes(self.no)[0]

    @property
    def caminhos(self) -> tuple:
        """Os caminhos que o pedido cobre: os elementos, ou o no."""
        return self.elementos or (self.no,)

    @property
    def especifico(self) -> bool:
        """Desceu do nivel da materia? E o que separa treino de simulado."""
        return self.nivel != NIVEIS[0]

    def dentro(self, caminho: str | None) -> bool:
        """Aquele no esta dentro deste escopo?

        Com elemento pedido, so os elementos valem - e os nos abaixo deles, se
        um dia houver. Sem elemento, vale o no e tudo abaixo.
        """
        if not caminho:
            return False
        return any(caminho == alvo or caminho.startswith(alvo + SEPARADOR)
                   for alvo in self.caminhos)

    def como_texto(self) -> str:
        if not self.elementos:
            return self.no
        nomes = ", ".join(partes(e)[-1] for e in self.elementos)
        return f"{self.no} ({nomes})"


def _parecidos(procurado: str, candidatos: list[str]) -> list[str]:
    """Os nomes mais parecidos, do mais para o menos. Vazio se nenhum serve."""
    import difflib

    por_nome = {}
    for caminho in candidatos:
        por_nome.setdefault(partes(caminho)[-1], caminho)
    achados = difflib.get_close_matches(
        procurado or "", list(por_nome), n=QUANTAS_SUGESTOES, cutoff=SEMELHANCA_MINIMA
    )
    return [por_nome[nome] for nome in achados]


def _filhos(caminhos: list[str], pai: str | None) -> list[str]:
    """Os caminhos que nascem direto debaixo de `pai`."""
    if pai is None:
        return [c for c in caminhos if SEPARADOR not in c]
    comeco = pai + SEPARADOR
    return [c for c in caminhos
            if c.startswith(comeco) and SEPARADOR not in c[len(comeco):]]


def _descer(caminhos: list[str], pai: str | None, nome: str, rotulo: str) -> str:
    """O filho de `pai` chamado `nome`. Erra em voz alta, com sugestoes."""
    achado = achar(caminhos, nome, pai=pai)
    if achado:
        return achado

    irmaos = _filhos(caminhos, pai)
    sugestoes = _parecidos(nome, irmaos)
    onde = f" em {pai!r}" if pai else ""
    if not irmaos:
        recado = (f"{rotulo} {nome!r} não existe{onde}, e {pai!r} não tem "
                  f"nenhum nível abaixo dele.")
    elif sugestoes:
        recado = (f"{rotulo} {nome!r} não existe{onde}. "
                  f"Você quis dizer: {'; '.join(partes(s)[-1] for s in sugestoes)}?")
    else:
        recado = (f"{rotulo} {nome!r} não existe{onde}. "
                  f"Os que existem: {'; '.join(partes(i)[-1] for i in irmaos)}.")
    raise EscopoInvalido(recado, sugestoes)


def resolver_escopo(
    caminhos: list[str],
    materia: str | None = None,
    assunto: str | None = None,
    subassunto: str | None = None,
    elementos: list[str] | None = None,
) -> Escopo | None:
    """O escopo de um pedido. None quando nao pedi nada (vale o edital inteiro).

    Cada nivel e conferido DENTRO do de cima, e um nome que a arvore nao tem
    para o pedido com sugestoes - nunca viram o nome mais parecido.
    """
    elementos = [e for e in (elementos or []) if (e or "").strip()]
    if not materia:
        if assunto or subassunto or elementos:
            raise EscopoInvalido(
                "Sem a matéria eu não sei onde procurar o assunto: "
                "diga a matéria também."
            )
        return None

    no = _descer(caminhos, None, materia, "A matéria")
    nivel = NIVEIS[0]
    if assunto:
        no = _descer(caminhos, no, assunto, "O assunto")
        nivel = NIVEIS[1]
    elif subassunto:
        raise EscopoInvalido(
            "Subassunto sem assunto não fecha um escopo: duas matérias podem "
            "ter subassunto de mesmo nome. Diga o assunto também."
        )
    if subassunto:
        no = _descer(caminhos, no, subassunto, "O subassunto")
        nivel = NIVEIS[2]

    escolhidos = []
    for nome in elementos:
        escolhidos.append(_descer(caminhos, no, nome, "O elemento"))
    if escolhidos:
        nivel = NIVEIS[3]
    return Escopo(no=no, nivel=nivel, elementos=tuple(escolhidos))
