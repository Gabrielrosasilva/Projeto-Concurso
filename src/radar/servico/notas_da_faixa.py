"""A nota de cada faixa: como eu fui, quantas chutei e se entendi (decisao 142).

O acerto diz QUANTO eu acertei; a nota diz COMO. "Acertei 7, mas 3 foram no
chute e eu ainda nao entendi" e um tema que fica no Ciclo 2, e o numero
sozinho nao conta isso.

Mora em `estados_do_dia.notas_das_faixas`, ao lado do `faixas_feitas` e nao
dentro dele: desmarcar a faixa nao apaga a nota, e da para escrever antes de
marcar. Como o check, a nota e reconhecida por bloco + indice + titulo - se o
cronograma.yml mudar a faixa daquela posicao, a nota antiga continua com o
titulo dela, e a faixa nova nao a herda.

E diario, como o caderno de erros: nao entra em acerto medido nenhum. Os
chutes daqui sao os de FORA do radar (os do Qconcursos, como o "fiz"); no
radar cada questao ja grava o seu "vou no chute".

Os erros por motivo (decisao 174) tambem sao os de fora do radar, so em
numeros ("dos 9 erros: Nao sabia 3, Confundi 2"): a soma nao passa dos erros
do "fiz" da faixa. Sem o "fiz", a nota grava e a soma espera por ele; se o
"fiz" chega depois com menos erros, ele grava assim mesmo - o numero que
conta nao espera a nota -, e a nota fica marcada ate eu corrigir.
"""
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select

from radar import cronograma as plano_de_estudo
from radar import fichas
from radar.db import criar_tabelas, sessao
from radar.models import EstadoDoDia, agora
from radar.servico import cronograma as diario
from radar.servico.comum import RegistroInvalido
from radar.servico.erros import MOTIVOS

#: As respostas do "entendi o assunto?", na ordem da tela.
ENTENDI = {
    "sim": "Entendi",
    "mais_ou_menos": "Mais ou menos",
    "nao": "Não entendi",
}

#: O mesmo limite da anotacao do dia.
TAMANHO_DA_NOTA = 2000


@dataclass
class NotaDaFaixa:
    """O que eu disse de uma faixa num dia."""

    data: date
    bloco: str
    indice: int
    titulo: str
    materia: str | None = None
    #: Quantas questoes de fora do radar eu chutei. None: nao disse.
    chutes: int | None = None
    #: Uma chave de ENTENDI, ou None.
    entendi: str | None = None
    nota: str = ""
    #: Os erros de fora do radar por motivo (decisao 174): {chave de MOTIVOS:
    #: quantos}, so os maiores que zero.
    motivos: dict = field(default_factory=dict)
    #: O "fiz" da faixa: as questoes e, com os acertos, os erros. None: o
    #: "fiz" nao disse (ou ainda nao existe).
    questoes_do_fiz: int | None = None
    erros_do_fiz: int | None = None

    @property
    def tema(self) -> str:
        """O tema pelo titulo, sem o prefixo: e assim que a ficha o acha."""
        return fichas.tema_da_faixa(self.titulo, self.materia)

    @property
    def entendi_texto(self) -> str | None:
        return ENTENDI.get(self.entendi)

    @property
    def soma_dos_motivos(self) -> int:
        return sum(self.motivos.values())

    @property
    def teto_dos_motivos(self) -> int | None:
        """Quantos erros o "fiz" permite: os erros, ou as questoes quando o
        "fiz" nao tem os acertos. None: ainda sem "fiz"."""
        return self.erros_do_fiz if self.erros_do_fiz is not None else self.questoes_do_fiz

    @property
    def motivos_passam(self) -> bool:
        """O "fiz" chegou depois com menos erros que a soma: a nota fica
        marcada, e a conta do Historico deixa os motivos dela de fora."""
        teto = self.teto_dos_motivos
        return bool(self.motivos) and teto is not None and self.soma_dos_motivos > teto

    @property
    def sem_motivo(self) -> int | None:
        """Os erros do "fiz" a que eu nao dei motivo, ou None sem os erros."""
        if self.erros_do_fiz is None or self.motivos_passam:
            return None
        return self.erros_do_fiz - self.soma_dos_motivos

    @property
    def motivos_texto(self) -> str:
        """"Nao sabia 3 · Confundi 2", na ordem dos MOTIVOS."""
        return " · ".join(f"{nome} {self.motivos[chave]}"
                          for chave, nome in MOTIVOS.items() if self.motivos.get(chave))


def anotar(data: date, bloco: str, indice: int, titulo: str,
           chutes=None, entendi: str | None = None, nota: str | None = None,
           motivos: dict | None = None,
           *, plano=None, hoje: date | None = None) -> NotaDaFaixa | None:
    """Grava (ou troca) a nota da faixa. Tudo vazio tira a nota.

    Devolve a nota gravada, ou None quando ela saiu. A faixa e conferida pela
    mesma regra do check: dia que ainda nao chegou, pausa, faixa desligada ou
    titulo que mudou desde que a tela abriu sao recusados em voz alta.

    `motivos` e {chave de MOTIVOS: quantos} (decisao 174). A soma nao passa
    dos erros do "fiz" (ou das questoes, se ele nao tem os acertos), e o
    "Chutei" nao passa dos chutes que eu disse.
    """
    hoje = hoje or diario.hoje_local()
    plano = plano or plano_de_estudo.carregar()
    # A mesma conferencia do check: e a faixa que a tela mostrou.
    faixa = diario._faixa_para_marcar(data, bloco, indice, titulo, plano, hoje)

    chutes = _chutes(chutes)
    entendi = (entendi or "").strip() or None
    if entendi is not None and entendi not in ENTENDI:
        raise RegistroInvalido(
            f"Entendi {entendi!r} não existe. Escolha uma destas: {', '.join(ENTENDI)}.")
    nota = (nota or "").strip()
    if len(nota) > TAMANHO_DA_NOTA:
        raise RegistroInvalido(
            f"A nota passou de {TAMANHO_DA_NOTA} caracteres ({len(nota)}).")
    motivos = _motivos(motivos)
    if motivos.get("chutei") and chutes is not None and motivos["chutei"] > chutes:
        raise RegistroInvalido(
            f"Os erros por chute ({motivos['chutei']}) passam dos chutes que você "
            f"disse ({chutes}).")

    nova = None
    if chutes is not None or entendi or nota or motivos:
        nova = {"bloco": bloco, "indice": indice, "titulo": faixa.titulo,
                "materia": faixa.materia, "chutes": chutes, "entendi": entendi,
                "nota": nota, "anotado_em": agora().isoformat()}
        # So com valor: as notas antigas e as sem motivo ficam como eram.
        if motivos:
            nova["motivos"] = motivos

    criar_tabelas()
    with sessao() as s:
        estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))
        check = _check_da_posicao(estado, bloco, indice, faixa.titulo)
        teto = _teto(check)
        if motivos and teto is not None and sum(motivos.values()) > teto:
            raise RegistroInvalido(
                f"Os motivos somam {sum(motivos.values())}, e o “fiz” da faixa diz "
                f"{teto} {'erros' if check.get('acertos') is not None else 'questões'}"
                f" fora do radar: a soma não pode passar disso.")
        if estado is None:
            if nova is None:
                return None
            estado = EstadoDoDia(data=data, faixas_feitas=[])
            s.add(estado)
        # A nota velha da mesma posicao sai, com qualquer titulo: a de outro
        # titulo nao vale mais para a faixa que esta ali.
        ficam = [n for n in (estado.notas_das_faixas or [])
                 if not (n.get("bloco") == bloco and n.get("indice") == indice)]
        if nova is not None:
            ficam.append(nova)
        # Lista nova: o SQLAlchemy so percebe a coluna JSON trocada.
        estado.notas_das_faixas = ficam or None
        estado.atualizado_em = agora()
    return _da_linha(data, nova, check) if nova else None


def _motivos(valores: dict | None) -> dict:
    """{chave: quantos}, so os maiores que zero; recusa o que nao e numero."""
    saida = {}
    for chave, valor in (valores or {}).items():
        if chave not in MOTIVOS:
            raise RegistroInvalido(
                f"Motivo {chave!r} não existe. Escolha um destes: {', '.join(MOTIVOS)}.")
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            continue
        try:
            numero = int(str(valor).strip())
        except ValueError:
            raise RegistroInvalido(
                f"Os erros por “{MOTIVOS[chave]}” precisam ser um número inteiro "
                f"(veio {valor!r}).")
        if numero < 0:
            raise RegistroInvalido(
                f"Os erros por “{MOTIVOS[chave]}” não podem ser negativos ({numero}).")
        if numero:
            saida[chave] = numero
    return saida


def _check_da_posicao(estado: EstadoDoDia | None, bloco: str, indice: int,
                      titulo: str) -> dict | None:
    """O "fiz" daquela faixa, pela mesma chave da nota."""
    return next((c for c in (estado.faixas_feitas if estado else None) or []
                 if c.get("bloco") == bloco and c.get("indice") == indice
                 and c.get("titulo") == titulo), None)


def _teto(check: dict | None) -> int | None:
    """Os erros do "fiz" (questoes - acertos), ou as questoes sem os acertos.
    None: sem "fiz", ou "fiz" sem numero - a soma espera."""
    if check is None or check.get("questoes") is None:
        return None
    if check.get("acertos") is not None:
        return check["questoes"] - check["acertos"]
    return check["questoes"]


def _chutes(valor) -> int | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    try:
        numero = int(str(valor).strip())
    except ValueError:
        raise RegistroInvalido(f"Os chutes precisam ser um número inteiro (veio {valor!r})")
    if numero < 0:
        raise RegistroInvalido(f"Os chutes não podem ser negativos ({numero})")
    return numero


def _da_linha(data: date, linha: dict, check: dict | None = None) -> NotaDaFaixa:
    questoes = (check or {}).get("questoes")
    acertos = (check or {}).get("acertos")
    return NotaDaFaixa(data=data, bloco=linha.get("bloco"), indice=linha.get("indice"),
                       titulo=linha.get("titulo") or "", materia=linha.get("materia"),
                       chutes=linha.get("chutes"), entendi=linha.get("entendi"),
                       nota=linha.get("nota") or "",
                       motivos={k: v for k, v in (linha.get("motivos") or {}).items()
                                if k in MOTIVOS and v},
                       questoes_do_fiz=questoes,
                       erros_do_fiz=(questoes - acertos
                                     if questoes is not None and acertos is not None else None))


def do_dia(estado: EstadoDoDia | None) -> dict[tuple[str, int, str], NotaDaFaixa]:
    """As notas de um dia, pela chave (bloco, indice, titulo) - a mesma do
    check. A tela so mostra a que bate com o titulo da faixa de hoje. Cada
    nota sabe o "fiz" da faixa dela, para a soma dos motivos (decisao 174)."""
    if estado is None:
        return {}
    notas = {}
    for linha in estado.notas_das_faixas or []:
        check = _check_da_posicao(estado, linha.get("bloco"), linha.get("indice"),
                                  linha.get("titulo") or "")
        nota = _da_linha(estado.data, linha, check)
        notas[(nota.bloco, nota.indice, nota.titulo)] = nota
    return notas


def todas() -> list[NotaDaFaixa]:
    """Todas as notas, da mais nova para a mais velha."""
    criar_tabelas()
    with sessao() as s:
        estados = list(s.scalars(
            select(EstadoDoDia).where(EstadoDoDia.notas_das_faixas.is_not(None))))
    notas = [nota for estado in estados for nota in do_dia(estado).values()]
    notas.sort(key=lambda n: (n.data, n.bloco, n.indice), reverse=True)
    return notas


@dataclass
class NotasDoTema:
    """As notas de um tema juntas: e a lista que o Ciclo 2 le."""

    tema: str
    materia: str | None
    notas: list
    #: Soma dos chutes que eu disse (fora do radar). None: nenhuma nota disse.
    chutes: int | None = None

    @property
    def ultima(self) -> NotaDaFaixa:
        return self.notas[0]

    @property
    def entendi(self) -> str | None:
        """O "entendi" da nota mais nova que disse alguma coisa."""
        return next((n.entendi_texto for n in self.notas if n.entendi), None)

    @property
    def ainda_nao_entendi(self) -> bool:
        return next((n.entendi for n in self.notas if n.entendi), None) in (
            "nao", "mais_ou_menos")


def por_tema(notas: list[NotaDaFaixa] | None = None) -> list[NotasDoTema]:
    """As notas agrupadas por tema. Primeiro os que eu ainda nao entendi (o
    que o Ciclo 2 precisa rever), depois pela nota mais nova."""
    notas = todas() if notas is None else notas
    grupos: dict[str, NotasDoTema] = {}
    for nota in notas:
        chave = fichas.chave_do_tema(nota.tema)
        grupo = grupos.setdefault(chave, NotasDoTema(nota.tema, nota.materia, []))
        grupo.notas.append(nota)
        if nota.chutes is not None:
            grupo.chutes = (grupo.chutes or 0) + nota.chutes
    saida = sorted(grupos.values(), key=lambda g: g.ultima.data, reverse=True)
    # `sorted` e estavel: dentro de cada grupo fica a ordem por data.
    return sorted(saida, key=lambda g: not g.ainda_nao_entendi)


def do_tema(tema: str) -> NotasDoTema | None:
    """As notas de um tema (o da ficha), ou None."""
    chave = fichas.chave_do_tema(tema)
    return next((g for g in por_tema() if fichas.chave_do_tema(g.tema) == chave), None)
