"""O diario do cronograma: como foi cada dia, anotado a mao.

A meta do dia e uma das quatro do plano - ideal, reduzida, minima, ou nao
fiz. Questoes feitas e acertos sao o que EU digito, e a maior parte vem do
Qconcursos: por isso ficam aqui, numa tabela so deles, e NAO entram em
acerto medido nenhum do radar. O Meu foco, o Onde estudar e a home contam so
o que eu respondi dentro do radar, questao por questao; somar um numero
digitado a mao ali misturaria medida com lembranca.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from radar import acervo
from radar import alvo
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import EstadoDoDia, RegistroDoDia, agora
from radar.util import fuso_local

METAS = ("ideal", "reduzida", "minima", "nao_fiz")


class RegistroInvalido(ValueError):
    """O registro foi recusado. A mensagem diz por que."""


def agora_local() -> datetime:
    """O relogio de Florianopolis. Um lugar so, para o teste poder parar o tempo."""
    return datetime.now(fuso_local())


def hoje_local() -> date:
    return agora_local().date()


def registrar(
    data: date,
    meta: str,
    questoes_feitas: int | None = None,
    acertos: int | None = None,
    anotacao: str | None = None,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> RegistroDoDia:
    """Cria ou atualiza o registro daquela data.

    `plano` e `hoje` existem para o teste: o ciclo real comeca no futuro, e
    sem eles nenhum teste conseguiria marcar um dia "passado" do plano.
    """
    if meta not in METAS:
        raise RegistroInvalido(
            f"Meta {meta!r} nao existe. Use uma destas: {', '.join(METAS)}"
        )
    for nome, valor in (("questoes feitas", questoes_feitas), ("acertos", acertos)):
        if valor is not None and valor < 0:
            raise RegistroInvalido(f"{nome.capitalize()} nao pode ser negativo ({valor})")
    if acertos is not None:
        if questoes_feitas is None:
            raise RegistroInvalido("Acertos sem questoes feitas: diga quantas fez")
        if acertos > questoes_feitas:
            raise RegistroInvalido(
                f"Acertos ({acertos}) maior que questoes feitas ({questoes_feitas})"
            )

    hoje = hoje or hoje_local()
    if data > hoje:
        # Marcar o futuro seria anotar o que eu PRETENDO fazer, e o diario e
        # do que eu fiz.
        raise RegistroInvalido(
            f"{data:%d/%m/%Y} ainda nao chegou: so se marca hoje ou dia passado"
        )
    plano = plano or plano_de_estudo.carregar()
    if plano.dia(data) is None:
        raise RegistroInvalido(f"{data:%d/%m/%Y} nao esta no cronograma")

    criar_tabelas()
    with sessao() as s:
        registro = s.scalar(select(RegistroDoDia).where(RegistroDoDia.data == data))
        if registro is None:
            registro = RegistroDoDia(data=data)
            s.add(registro)
        registro.meta = meta
        registro.questoes_feitas = questoes_feitas
        registro.acertos = acertos
        registro.anotacao = anotacao
        registro.anotado_em = agora()
    return registro


def registros(inicio: date, fim: date) -> dict[date, RegistroDoDia]:
    """Os registros entre as duas datas, inclusive, pela data."""
    criar_tabelas()
    with sessao() as s:
        achados = s.scalars(
            select(RegistroDoDia)
            .where(RegistroDoDia.data >= inicio)
            .where(RegistroDoDia.data <= fim)
        )
        return {r.data: r for r in achados}


def apagar(data: date) -> bool:
    """Apaga o dia inteiro do diario: o registro e os checks das faixas.

    Do banco E dos arquivos (data/registro_estudo.json e
    data/estado_do_dia.json), pelo mesmo motivo do descartar simulado: o
    arquivo so cresce, e o que saisse so do banco voltaria no proximo
    `importar`.
    """
    criar_tabelas()
    with sessao() as s:
        registro = s.scalar(select(RegistroDoDia).where(RegistroDoDia.data == data))
        if registro is not None:
            s.delete(registro)
        estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))
        if estado is not None:
            s.delete(estado)
    saiu_do_arquivo = (acervo.esquecer_registros([data])
                       + acervo.esquecer_estados([data]))
    return registro is not None or estado is not None or saiu_do_arquivo > 0


# --- os checks de cada faixa ---------------------------------------------------
# A faixa e reconhecida por bloco + indice + TITULO. So a posicao nao basta:
# se o cronograma.yml mudar, a faixa 2 da noite pode virar outra, e o check
# antigo marcaria como feita uma faixa que eu nao fiz. Com o titulo junto, o
# check que nao bate mais e simplesmente ignorado.

def _faixa_do_plano(plano, data: date, bloco: str, indice: int):
    gravado = plano.dia(data)
    if gravado is None:
        raise RegistroInvalido(f"{data:%d/%m/%Y} nao esta no cronograma")
    if bloco not in plano_de_estudo.BLOCOS:
        raise RegistroInvalido(f"Bloco {bloco!r} nao existe")
    faixas = getattr(gravado, bloco)
    if not 0 <= indice < len(faixas):
        raise RegistroInvalido(f"O bloco {bloco} nao tem a faixa {indice}")
    return faixas[indice]


def marcar_faixa(
    data: date,
    bloco: str,
    indice: int,
    titulo: str,
    *,
    plano: plano_de_estudo.Plano | None = None,
    hoje: date | None = None,
) -> bool:
    """Marca a faixa se estava aberta, desmarca se estava feita.

    Devolve True quando ela ficou FEITA. `plano` e `hoje` existem para o
    teste, como no `registrar`.
    """
    hoje = hoje or hoje_local()
    if data > hoje:
        raise RegistroInvalido(
            f"{data:%d/%m/%Y} ainda nao chegou: so se marca faixa de hoje ou de dia passado"
        )
    plano = plano or plano_de_estudo.carregar()
    faixa = _faixa_do_plano(plano, data, bloco, indice)
    if faixa.titulo != titulo:
        raise RegistroInvalido(
            "Essa faixa mudou no config/cronograma.yml desde que a tela abriu. "
            "Recarregue a página e marque de novo."
        )
    if faixa.tipo == "pausa":
        raise RegistroInvalido("Pausa não se marca.")

    criar_tabelas()
    with sessao() as s:
        estado = s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))
        if estado is None:
            estado = EstadoDoDia(data=data, faixas_feitas=[])
            s.add(estado)
        antes = list(estado.faixas_feitas or [])
        # Check velho na mesma posicao, com outro titulo, sai junto: nao vale
        # mais nada e so atrapalharia a leitura do arquivo.
        mesma_posicao = [c for c in antes
                         if c.get("bloco") == bloco and c.get("indice") == indice]
        estava_feita = any(c.get("titulo") == titulo for c in mesma_posicao)
        ficam = [c for c in antes if c not in mesma_posicao]
        if not estava_feita:
            ficam.append({"bloco": bloco, "indice": indice, "titulo": titulo})
        # Lista nova, e nao append na velha: o SQLAlchemy so percebe que a
        # coluna JSON mudou quando o valor e trocado.
        estado.faixas_feitas = ficam
        estado.atualizado_em = agora()
    return not estava_feita


def estado_do_dia(data: date) -> EstadoDoDia | None:
    criar_tabelas()
    with sessao() as s:
        return s.scalar(select(EstadoDoDia).where(EstadoDoDia.data == data))


def faixas_feitas(dia, estado: EstadoDoDia | None) -> set[tuple[str, int]]:
    """As posicoes (bloco, indice) feitas que ainda batem com o dia do
    cronograma.yml. Check cujo titulo nao bate e ignorado, sem erro."""
    if dia is None or estado is None:
        return set()
    feitas = set()
    for check in estado.faixas_feitas or []:
        bloco, indice = check.get("bloco"), check.get("indice")
        if bloco not in plano_de_estudo.BLOCOS or not isinstance(indice, int):
            continue
        faixas = getattr(dia, bloco)
        if not 0 <= indice < len(faixas):
            continue
        faixa = faixas[indice]
        if faixa.titulo == check.get("titulo") and faixa.tipo != "pausa":
            feitas.add((bloco, indice))
    return feitas


@dataclass
class Sugestao:
    """O que os checks sugerem para o "Como foi o dia". So sugere: quem
    escolhe a meta e salva sou eu."""
    meta: str | None            # ideal | reduzida | minima | None (sem sugestao)
    feitas: int                 # faixas que contam, feitas
    total: int                  # faixas que contam: nem pausa, nem opcional
    questoes: int               # soma das questoes das faixas marcadas


def sugerir_meta(dia, feitas: set[tuple[str, int]]) -> Sugestao:
    """A regra, em ordem:

    - todas as faixas que contam (nem pausa, nem bonus) = Ideal;
    - a manha inteira + a faixa de Direito da noite = Reduzida;
    - pelo menos uma faixa de questoes (fora o bonus) = Minima;
    - nada marcado, ou so o que nao fecha nenhuma regra = sem sugestao.

    As questoes somam TODA faixa marcada, bonus inclusive: e o que eu fiz.
    O numero e o do dia montado, ou seja, o do nivel efetivo.
    """
    def contam(bloco):
        return [(bloco, i) for i, f in enumerate(getattr(dia, bloco))
                if f.tipo != "pausa" and not f.opcional]

    def faixa(posicao):
        bloco, indice = posicao
        return getattr(dia, bloco)[indice]

    todas = [p for bloco in plano_de_estudo.BLOCOS for p in contam(bloco)]
    feitas_que_contam = [p for p in todas if p in feitas]
    questoes = sum(faixa(p).questoes or 0 for p in feitas)
    sugestao = Sugestao(None, len(feitas_que_contam), len(todas), questoes)
    if not feitas:
        return sugestao

    manha_inteira = all(p in feitas for p in contam("manha"))
    direito_feito = any(f.rampa == "direito" and ("noite", i) in feitas
                        for i, f in enumerate(dia.noite))
    alguma_de_questoes = any(faixa(p).questoes and not faixa(p).opcional for p in feitas)
    if todas and len(feitas_que_contam) == len(todas):
        sugestao.meta = "ideal"
    elif manha_inteira and direito_feito:
        sugestao.meta = "reduzida"
    elif alguma_de_questoes:
        sugestao.meta = "minima"
    return sugestao


# --- a tela "Hoje" -----------------------------------------------------------
# Tudo o que a pagina precisa, montado aqui: o template so desenha. Nenhuma
# conta de horario ou de nivel mora no HTML.

@dataclass
class Pilula:
    """Um dia na faixa da semana."""
    data: date
    rotulo: str                 # "Seg"
    meta: str | None            # o que marquei; None = sem marcacao
    futuro: bool
    aberta: bool                # e o dia que esta na tela


@dataclass
class BlocoNaTela:
    chave: str
    nome: str
    faixas: list
    inicio: time | None = None
    fim: time | None = None
    questoes: int = 0


@dataclass
class Agora:
    """O cartao AGORA: so existe quando o dia aberto e hoje."""
    situacao: str               # antes | faixa | entre | fim
    atual: object = None        # a Faixa em andamento
    proxima: object = None      # a Faixa que vem depois


@dataclass
class TelaDoDia:
    # dia | domingo | antes | depois | fora | sem_arquivo | erro
    estado: str
    data: date
    hoje: date
    mensagem: str | None = None
    plano: object = None
    dia: object = None
    nivel: object = None
    total_semanas: int = 0
    pilulas: list[Pilula] = field(default_factory=list)
    blocos: list[BlocoNaTela] = field(default_factory=list)
    fim_do_dia: time | None = None
    agora: Agora | None = None
    hora: time | None = None    # a hora de agora, so quando o dia e hoje
    registro: RegistroDoDia | None = None
    # O dia que o estado vazio mostra: amanha (domingo) ou o primeiro (antes).
    outro_dia: object = None
    # O cartao "Objetivo": o nome do alvo sai do config/alvo.yml, nunca daqui.
    nome_do_alvo: str | None = None
    # Dias seguidos cumprindo a meta. Vazio ate a conta existir: a tela mostra
    # "–" e nao um numero inventado.
    sequencia: int | None = None
    # Os checks: as posicoes (bloco, indice) feitas, e o que elas sugerem.
    feitas: set = field(default_factory=set)
    sugestao: object = None

    @property
    def e_hoje(self) -> bool:
        return self.data == self.hoje

    @property
    def futuro(self) -> bool:
        return self.data > self.hoje

    @property
    def dias_para_o_fim(self) -> int | None:
        """Quantos dias faltam, contados de HOJE (e nao do dia na tela), para
        o fim do ciclo. Negativo quando ja acabou; None sem plano."""
        if self.plano is None:
            return None
        return (self.plano.fim - self.hoje).days

    @property
    def anterior(self) -> date:
        return self.data - timedelta(days=1)

    @property
    def proximo(self) -> date:
        return self.data + timedelta(days=1)


def _metas(plano) -> dict[date, str]:
    return {d: r.meta for d, r in registros(plano.inicio, plano.fim).items()}


def hoje_do_gatilho(data: date) -> date:
    """O "hoje" que o gatilho usa para ver o dia `data`.

    Dia passado: a propria data, para mostrar a carga que valia naquele dia.
    Dia futuro: o hoje de verdade - o gatilho so sabe o que ja aconteceu, e
    as semanas que ainda nao chegaram ficam na carga do plano.
    """
    return min(data, hoje_local())


def nivel_do_dia(plano, data: date, metas: dict[date, str] | None = None):
    """O nivel da semana de `data`, ou None se o dia nao esta no plano.

    O lugar unico da conta, para a tela e o `radar hoje` nunca divergirem.
    """
    gravado = plano.dia(data)
    if gravado is None:
        return None
    if metas is None:
        metas = _metas(plano)
    return plano_de_estudo.niveis(plano, metas, hoje_do_gatilho(data))[gravado.semana]


def _montado(plano, data: date, metas: dict[date, str]):
    """O dia com o nivel efetivo da semana dele, como o `radar hoje` mostra."""
    nivel = nivel_do_dia(plano, data, metas)
    if nivel is None:
        return None, None
    return plano_de_estudo.montar_dia(plano, data, nivel.efetivo), nivel


def _agora(dia, hora: time) -> Agora:
    faixas = dia.faixas()
    if not faixas or hora < faixas[0].inicio:
        return Agora("antes", proxima=faixas[0] if faixas else None)
    atual, proxima = plano_de_estudo.faixa_atual(dia, hora)
    if atual is not None:
        return Agora("faixa", atual=atual, proxima=proxima)
    if proxima is not None:
        return Agora("entre", proxima=proxima)
    return Agora("fim")


def tela_do_dia(data: date | None = None, caminho=None) -> TelaDoDia:
    """O que a tela "Hoje" mostra para `data` (padrao: hoje, no fuso local)."""
    relogio = agora_local()
    hoje = relogio.date()
    data = data or hoje

    try:
        plano = plano_de_estudo.carregar(caminho)
    except FileNotFoundError as erro:
        return TelaDoDia("sem_arquivo", data, hoje, mensagem=str(erro.filename))
    except plano_de_estudo.ErroNoCronograma as erro:
        return TelaDoDia("erro", data, hoje, mensagem=str(erro))

    tela = TelaDoDia("dia", data, hoje, plano=plano,
                     total_semanas=max((d.semana for d in plano.dias), default=0),
                     nome_do_alvo=alvo.principal().get("nome"))
    metas = _metas(plano)

    if data < plano.inicio:
        tela.estado = "antes"
        tela.outro_dia, _ = _montado(plano, plano.inicio, metas)
        return tela
    if data > plano.fim:
        tela.estado = "depois"
        return tela
    if data.weekday() == plano_de_estudo.DOMINGO:
        tela.estado = "domingo"
        tela.outro_dia, _ = _montado(plano, data + timedelta(days=1), metas)
        return tela

    dia, nivel = _montado(plano, data, metas)
    if dia is None:
        tela.estado = "fora"
        return tela
    tela.dia, tela.nivel = dia, nivel

    segunda = data - timedelta(days=data.weekday())
    for i in range(6):
        d = segunda + timedelta(days=i)
        if plano.dia(d) is None:
            continue
        tela.pilulas.append(Pilula(d, plano_de_estudo.DIAS_CURTOS[i],
                                   metas.get(d), d > hoje, d == data))

    for chave in plano_de_estudo.BLOCOS:
        faixas = getattr(dia, chave)
        bloco = BlocoNaTela(chave, plano.blocos[chave].nome, faixas)
        if faixas:
            bloco.inicio, bloco.fim = faixas[0].inicio, faixas[-1].fim
            bloco.questoes = sum(f.questoes or 0 for f in faixas if not f.opcional)
        tela.blocos.append(bloco)

    noite = dia.noite or dia.faixas()
    tela.fim_do_dia = noite[-1].fim if noite else None
    if tela.e_hoje:
        tela.hora = relogio.time().replace(second=0, microsecond=0)
        tela.agora = _agora(dia, tela.hora)
    tela.registro = registros(data, data).get(data)
    tela.feitas = faixas_feitas(dia, estado_do_dia(data))
    tela.sugestao = sugerir_meta(dia, tela.feitas)
    return tela
