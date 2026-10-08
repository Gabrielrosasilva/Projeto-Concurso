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
"""
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from radar import cronograma as plano_de_estudo
from radar import fichas
from radar.db import criar_tabelas, sessao
from radar.models import EstadoDoDia, agora
from radar.servico import cronograma as diario
from radar.servico.comum import RegistroInvalido

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

    @property
    def tema(self) -> str:
        """O tema pelo titulo, sem o prefixo: e assim que a ficha o acha."""
        return fichas.tema_da_faixa(self.titulo, self.materia)

    @property
    def entendi_texto(self) -> str | None:
        return ENTENDI.get(self.entendi)


def anotar(data: date, bloco: str, indice: int, titulo: str,
           chutes=None, entendi: str | None = None, nota: str | None = None,
           *, plano=None, hoje: date | None = None) -> NotaDaFaixa | None:
    """Grava (ou troca) a nota da faixa. Tudo vazio tira a nota.

    Devolve a nota gravada, ou None quando ela saiu. A faixa e conferida pela
    mesma regra do check: dia que ainda nao chegou, pausa, faixa desligada ou
    titulo que mudou desde que a tela abriu sao recusados em voz alta.
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

    nova = None
    if chutes is not None or entendi or nota:
        nova = {"bloco": bloco, "indice": indice, "titulo": faixa.titulo,
                "materia": faixa.materia, "chutes": chutes, "entendi": entendi,
                "nota": nota, "anotado_em": agora().isoformat()}

    criar_tabelas()
    with sessao() as s:
        estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))
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
    return _da_linha(data, nova) if nova else None


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


def _da_linha(data: date, linha: dict) -> NotaDaFaixa:
    return NotaDaFaixa(data=data, bloco=linha.get("bloco"), indice=linha.get("indice"),
                       titulo=linha.get("titulo") or "", materia=linha.get("materia"),
                       chutes=linha.get("chutes"), entendi=linha.get("entendi"),
                       nota=linha.get("nota") or "")


def do_dia(estado: EstadoDoDia | None) -> dict[tuple[str, int, str], NotaDaFaixa]:
    """As notas de um dia, pela chave (bloco, indice, titulo) - a mesma do
    check. A tela so mostra a que bate com o titulo da faixa de hoje."""
    if estado is None:
        return {}
    notas = {}
    for linha in estado.notas_das_faixas or []:
        nota = _da_linha(estado.data, linha)
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
