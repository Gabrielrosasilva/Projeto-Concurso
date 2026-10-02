"""O acervo complementar FEPESE: o que ha, e o que esta pronto para usar.

Complementar e toda prova de uma banca do alvo que NAO e do meu cargo no meu
estado (`servico/evidencia.py`). Ela serve para entender o estilo da FEPESE -
nunca para engrossar a incidencia da Policia Penal: os dois numeros aparecem
em linhas separadas e jamais somados (regra inviolavel 1).

Este modulo e puro: recebe os cadernos ja lidos e devolve o levantamento e a
validacao. Quem fala com o banco e o `servico/complementar.py`.

## Duas colunas, e por que elas nao se somam

- **pelo nome da materia**: o caderno diz "Direito Penal". E certo.
- **por termo no texto** (🟡 indicio): o caderno diz so "Conhecimentos
  Especificos", e o termo apareceu no enunciado ou nas alternativas. Nao e
  evidencia - o termo pode estar de passagem, e a falta dele nao prova nada.
  So as questoes que NAO foram contadas pelo nome entram aqui, para a mesma
  questao nunca contar duas vezes.

Quem diz de verdade qual conteudo caiu e a classificacao, questao a questao.
Este levantamento existe para escolher QUAIS provas vale a pena classificar.

## A validacao (secao 5 do pedido)

Tres perguntas por prova, todas respondidas sem reler o PDF:

1. **a extracao parece inteira?** A numeracao vai de 1 a N sem buraco e sem
   repetir, toda questao tem as cinco alternativas, e toda questao tem letra
   no gabarito (ou esta anulada). O quadro do edital nao entra aqui: o leitor
   de quadro so da conta dos editais do Estado, e nas provas de prefeitura
   ele nao acha o quadro. Fica registrado "nao lido", nunca "bate";
2. **que gabarito e esse?** `definitivo` (o de depois dos recursos),
   `provisorio` (o que vem embutido no caderno) ou `ausente`. No acervo de
   hoje a maioria so tem o provisorio;
3. **ja esta no acervo?** Pelo sha256 do PDF: a mesma prova com outro nome de
   arquivo e recusada.

O que cada estado permite:

| Estado | Classificar | Entrar nos padroes de cobranca |
|---|---|---|
| extracao com defeito, ou PDF repetido | nao | nao |
| gabarito ausente | sim | nao |
| gabarito provisorio | sim | nao |
| gabarito definitivo | sim | sim |

O gabarito provisorio nao entra nos padroes porque padrao de cobranca se
mede sobre a letra CERTA (distribuicao do gabarito, qual alternativa engana),
e o provisorio muda depois dos recursos. Para saber de que assunto a banca
gosta, ele basta - e por isso classificar continua valendo.
"""
import re
import unicodedata
from dataclasses import dataclass, field

LETRAS = ("a", "b", "c", "d", "e")

DEFINITIVO, PROVISORIO, AUSENTE = "definitivo", "provisório", "ausente"

#: O que a tela escreve quando o acervo nao sustenta a afirmacao (regra 4).
FRASE_SEM_EVIDENCIA = "Não há evidência suficiente no acervo para afirmar isso."

#: O quadro de distribuicao de questoes do edital nao foi conferido: o leitor
#: de quadro (auditoria.py) so le os editais do Estado.
QUADRO_NAO_LIDO = "não lido"


def normalizar(texto: str | None) -> str:
    """Sem acento, sem caixa e sem espaco sobrando, para comparar e procurar."""
    normal = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in normal if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


@dataclass
class QuestaoDoCaderno:
    """Uma questao de uma prova complementar, do jeito que o levantamento usa."""

    numero: int
    #: O nome da materia NO EDITAL do alvo, quando o caderno diz um nome que
    #: e de uma materia minha (sinonimo ja resolvido). None quando o caderno
    #: diz "Conhecimentos Especificos" ou uma materia que nao e minha.
    materia_no_edital: str | None
    #: Enunciado e alternativas juntos, para a busca por termo.
    texto: str = ""
    letras: tuple[str, ...] = LETRAS
    resposta: str | None = None
    anulada: bool = False


@dataclass
class Caderno:
    """Uma prova complementar inteira."""

    prova_url: str
    cargo: str | None
    ano: int | None
    questoes: list[QuestaoDoCaderno] = field(default_factory=list)
    #: Do manifesto (`data/provas.json`).
    sha256: str | None = None
    gabarito: str = AUSENTE


@dataclass
class Validacao:
    """O que esta prova permite, e por que."""

    prova_url: str
    questoes: int
    gabarito: str
    sha256: str | None = None
    #: Outra prova do acervo com o mesmo PDF. Quando ha, esta nao entra.
    repetida_de: str | None = None
    problemas: list[str] = field(default_factory=list)
    quadro_do_edital: str = QUADRO_NAO_LIDO

    @property
    def pode_classificar(self) -> bool:
        """Extracao inteira e PDF novo. O gabarito provisorio nao impede."""
        return not self.problemas and self.repetida_de is None

    @property
    def entra_nos_padroes(self) -> bool:
        """Alem disso, o gabarito tem que ser o definitivo."""
        return self.pode_classificar and self.gabarito == DEFINITIVO

    @property
    def motivo(self) -> str:
        """Em uma frase, por que a prova nao entra. Vazio quando entra."""
        if self.repetida_de:
            return f"o mesmo PDF já está no acervo em {self.repetida_de}"
        if self.problemas:
            return "; ".join(self.problemas)
        if self.gabarito != DEFINITIVO:
            return (f"gabarito {self.gabarito}: serve para classificar, mas fica "
                    "fora dos padrões de cobrança, que se medem sobre a letra certa")
        return ""

    @property
    def situacao(self) -> str:
        """Uma palavra para a tabela do relatorio."""
        if not self.pode_classificar:
            return "recusada"
        return "validada" if self.entra_nos_padroes else "só para classificar"


def validar(caderno: Caderno, hashes_do_acervo: dict[str, str] | None = None) -> Validacao:
    """A validacao minima de uma prova, sem reler o PDF.

    `hashes_do_acervo` e {sha256: prova_url} do que ja foi aceito antes: a
    mesma prova com outro nome de arquivo e recusada por ele.
    """
    questoes = sorted(caderno.questoes, key=lambda q: q.numero)
    problemas = []

    numeros = [q.numero for q in questoes]
    if not numeros:
        problemas.append("nenhuma questão extraída")
    else:
        # O caderno vai ate o maior numero que apareceu, e nao ate a
        # quantidade extraida: faltando a questao 20 de um caderno de 40,
        # "1 a 39" esconderia justamente o buraco.
        ultima = max(max(numeros), len(numeros))
        esperados = list(range(1, ultima + 1))
        if numeros != esperados:
            faltando = sorted(set(esperados) - set(numeros))
            repetidos = sorted({n for n in numeros if numeros.count(n) > 1})
            detalhe = []
            if faltando:
                detalhe.append("falta " + ", ".join(map(str, faltando)))
            if repetidos:
                detalhe.append("repete " + ", ".join(map(str, repetidos)))
            problemas.append(
                "{} questões extraídas, e o caderno vai até a {}: a numeração "
                "não fecha ({})".format(len(numeros), ultima,
                                        "; ".join(detalhe) or "fora de ordem"))

    sem_letras = [q.numero for q in questoes if tuple(sorted(q.letras)) != LETRAS]
    if sem_letras:
        problemas.append("alternativas diferentes de a-e nas questões "
                         + ", ".join(map(str, sem_letras[:10]))
                         + (f" e mais {len(sem_letras) - 10}" if len(sem_letras) > 10 else ""))

    sem_gabarito = [q.numero for q in questoes if not q.resposta and not q.anulada]
    if sem_gabarito:
        problemas.append("sem letra no gabarito nas questões "
                         + ", ".join(map(str, sem_gabarito[:10]))
                         + (f" e mais {len(sem_gabarito) - 10}" if len(sem_gabarito) > 10 else ""))

    repetida = (hashes_do_acervo or {}).get(caderno.sha256 or "") if caderno.sha256 else None
    if repetida == caderno.prova_url:
        repetida = None
    return Validacao(prova_url=caderno.prova_url, questoes=len(questoes),
                     gabarito=caderno.gabarito, sha256=caderno.sha256,
                     repetida_de=repetida, problemas=problemas)


# --- o levantamento por materia -------------------------------------------------

@dataclass
class ProvaDaMateria:
    """O que uma prova complementar tem de UMA materia do meu edital."""

    prova_url: str
    cargo: str | None
    ano: int | None
    #: Questoes cujo caderno diz o nome da materia. Certo.
    pelo_nome: int
    #: Questoes de bloco generico em que um termo da materia apareceu. Indicio.
    por_termo: int
    validacao: Validacao

    @property
    def questoes(self) -> int:
        """As duas colunas juntas - e elas NAO se sobrepoem (por_termo so
        conta o que o nome nao contou)."""
        return self.pelo_nome + self.por_termo


@dataclass
class MateriaComplementar:
    materia: str
    provas: list[ProvaDaMateria] = field(default_factory=list)

    @property
    def pelo_nome(self) -> int:
        return sum(p.pelo_nome for p in self.provas)

    @property
    def por_termo(self) -> int:
        return sum(p.por_termo for p in self.provas)

    @property
    def provas_pelo_nome(self) -> int:
        return sum(1 for p in self.provas if p.pelo_nome)

    @property
    def provas_por_termo(self) -> int:
        return sum(1 for p in self.provas if p.por_termo)

    @property
    def tem_alguma_coisa(self) -> bool:
        return bool(self.provas)

    def amostra(self) -> str:
        """"20 questões · 2 provas pelo nome · 13 indícios em 9 provas"."""
        if not self.tem_alguma_coisa:
            return "nenhuma questão no acervo complementar"
        pedacos = []
        if self.pelo_nome:
            pedacos.append(f"{_questoes(self.pelo_nome)} · "
                           f"{_provas(self.provas_pelo_nome)} pelo nome da matéria")
        if self.por_termo:
            pedacos.append(f"{self.por_termo} indício(s) por termo em "
                           f"{_provas(self.provas_por_termo)}")
        return " · ".join(pedacos)


def _questoes(quantas: int) -> str:
    return f"{quantas} {'questão' if quantas == 1 else 'questões'}"


def _provas(quantas: int) -> str:
    return f"{quantas} {'prova' if quantas == 1 else 'provas'}"


def montar(materias: list[str], cadernos: list[Caderno],
           termos: dict[str, list[str]],
           validacoes: dict[str, Validacao]) -> list[MateriaComplementar]:
    """O levantamento: para cada materia do meu edital, as provas que a tem.

    A ordem e a das materias que vieram; dentro de cada uma, a prova com mais
    questoes primeiro.
    """
    procurar = {m: [normalizar(t) for t in termos.get(m, []) if t] for m in materias}
    levantamento = []
    for materia in materias:
        da_materia = MateriaComplementar(materia=materia)
        for caderno in cadernos:
            pelo_nome, por_termo = 0, 0
            for q in caderno.questoes:
                if q.materia_no_edital == materia:
                    pelo_nome += 1
                    continue
                # So o que o nome nao contou - nem para esta materia, nem
                # para outra: questao que ja tem materia propria no caderno
                # nao vira indicio de uma terceira.
                if q.materia_no_edital is None and procurar[materia]:
                    texto = normalizar(q.texto)
                    if any(t in texto for t in procurar[materia]):
                        por_termo += 1
            if pelo_nome or por_termo:
                da_materia.provas.append(ProvaDaMateria(
                    prova_url=caderno.prova_url, cargo=caderno.cargo, ano=caderno.ano,
                    pelo_nome=pelo_nome, por_termo=por_termo,
                    validacao=validacoes[caderno.prova_url]))
        da_materia.provas.sort(key=lambda p: (-p.questoes, p.ano or 0, p.cargo or ""))
        levantamento.append(da_materia)
    return levantamento


# --- quem entra no acervo complementar ------------------------------------------
#
# A regra e sua (01/10/2026): entra a prova que tem ao menos uma materia do
# edital de 2019, e que passa na validacao minima. Materia que nao esta no
# edital de agora (Nocoes de Informatica, Direito Administrativo, Temas de
# Educacao) nao serve de motivo para a prova entrar - o acervo e para estudar
# o que vai cair na minha prova, nao para colecionar caderno.

@dataclass
class Registro:
    """Uma prova do acervo complementar, com o que ela permite e desde quando.

    E isto que vai para o `data/acervo_complementar.json`: o arquivo
    versionado que a secao 5 do pedido descreve (fonte, hash, status de
    validacao e data de inclusao).
    """

    prova_url: str
    cargo: str | None
    ano: int | None
    concurso_url: str | None
    arquivo: str | None
    sha256: str | None
    questoes: int
    materias_do_edital: list[str]
    gabarito: str
    quadro_do_edital: str
    aceita: bool
    motivo: str
    entra_nos_padroes: bool
    incluida_em: str | None


def decidir(validacao: Validacao, materias_do_edital: list[str]) -> tuple[bool, str]:
    """A prova entra? E, quando nao entra ou entra pela metade, por que.

    A ordem importa: a prova sem materia minha nao entra, e nem adianta
    conferir a extracao dela.
    """
    if not materias_do_edital:
        return False, "nenhuma matéria do edital de 2019 neste caderno"
    if not validacao.pode_classificar:
        return False, validacao.motivo
    return True, validacao.motivo       # vazio, ou o aviso do gabarito provisorio


# --- a linha complementar da incidencia -----------------------------------------
#
# Secao 4 do pedido: "Policia Penal SC: 2 ocorrencias em 2 provas · Acervo
# complementar FEPESE: 30 ocorrencias em X provas". As duas linhas vivem
# lado a lado e NUNCA se somam.

@dataclass
class LinhaComplementar:
    """O que o acervo complementar tem debaixo de um no da arvore."""

    caminho: str
    questoes: int = 0
    provas: int = 0
    #: Dessas, quantas ja tem classificacao. No nivel da materia a conta
    #: aceita a questao sem classificar (o caderno diz a materia, e isso e
    #: evidencia); abaixo dela, so a classificada conta - e por isso as duas
    #: colunas existem.
    classificadas: int = 0

    @property
    def amostra(self) -> str:
        return f"{_questoes(self.questoes)} · {_provas(self.provas)}"

    @property
    def frase(self) -> str:
        """A linha pronta, do jeito que a secao 4 pede."""
        if not self.questoes:
            return "Acervo complementar FEPESE: nada no acervo"
        falta = self.questoes - self.classificadas
        pendente = f" ({falta} sem classificação ainda)" if falta else ""
        return f"Acervo complementar FEPESE: {self.amostra}{pendente}"


# --- as perguntas da secao 5 do pedido ------------------------------------------

@dataclass
class Resposta:
    pergunta: str
    resposta: str


def responder(levantamento: list[MateriaComplementar]) -> list[Resposta]:
    """As 6 perguntas da secao 5, respondidas SO com o que o acervo tem.

    Nenhuma delas afirma o que nao esta no acervo: "nao ha prova com LEP" e
    diferente de "a FEPESE nunca cobrou LEP", e o texto diz isso.
    """
    por_materia = {m.materia: m for m in levantamento}
    com_nome = sorted((m for m in levantamento if m.pelo_nome),
                      key=lambda m: -m.pelo_nome)
    sem_nada = [m for m in levantamento if not m.tem_alguma_coisa]
    so_indicio = [m for m in levantamento if not m.pelo_nome and m.por_termo]

    def linha(materia: str) -> str:
        m = por_materia.get(materia)
        if m is None:
            return f"{materia} não é matéria do edital do alvo na árvore de conteúdos."
        if not m.tem_alguma_coisa:
            return (f"Nenhuma questão de {materia} no acervo complementar — nem pelo "
                    f"nome da matéria, nem por termo no texto. Isso diz o que o ACERVO "
                    f"tem, e não o que a FEPESE já cobrou: {FRASE_SEM_EVIDENCIA}")
        return f"{materia}: {m.amostra()}."

    respostas = [
        Resposta(
            "1. Quais matérias da Polícia Penal têm boa quantidade de provas "
            "FEPESE complementares?",
            ("Pelo nome da matéria no caderno, da maior para a menor: "
             + "; ".join(f"{m.materia} ({m.pelo_nome} em {_provas(m.provas_pelo_nome)})"
                         for m in com_nome) + "."
             if com_nome else
             "Nenhuma matéria do edital aparece com o próprio nome num caderno "
             f"complementar. {FRASE_SEM_EVIDENCIA}")),
        Resposta(
            "2. Quais têm pouco ou nenhum material complementar?",
            ("Sem nada no acervo: "
             + ("; ".join(m.materia for m in sem_nada) if sem_nada else "nenhuma")
             + ". Só com indício por termo, a confirmar na classificação: "
             + ("; ".join(f"{m.materia} ({m.por_termo})" for m in so_indicio)
                if so_indicio else "nenhuma") + ".")),
        Resposta("3. Existem provas FEPESE anteriores com LEP?",
                 linha("Lei de Execução Penal")),
        Resposta("4. Existem provas FEPESE com Sociologia Aplicada?",
                 linha("Sociologia Aplicada")),
        Resposta("5. Existem provas FEPESE com legislação estadual específica "
                 "do sistema prisional de SC?",
                 linha("Legislação Estadual")
                 + " Atenção: esta linha é a da matéria Legislação Estadual "
                 "inteira. Se o que caiu ali é lei do sistema PRISIONAL ou de "
                 "outra área do Estado, só a classificação, questão a questão, "
                 "diz — o levantamento não sabe."),
        Resposta(
            "6. Quais outras matérias têm acervo suficiente para servir de reforço?",
            ("Com prova validada (extração inteira e gabarito definitivo): "
             + ("; ".join(
                 f"{m.materia} ({sum(p.pelo_nome for p in m.provas if p.validacao.entra_nos_padroes)} "
                 f"em {_provas(sum(1 for p in m.provas if p.validacao.entra_nos_padroes and p.pelo_nome))})"
                 for m in com_nome
                 if any(p.validacao.entra_nos_padroes and p.pelo_nome for p in m.provas))
                or "nenhuma") + ". As demais dependem de você aprovar a prova e "
             "de ela passar na validação.")),
    ]
    return respostas
