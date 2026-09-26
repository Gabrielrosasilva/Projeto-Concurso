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
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import RegistroDoDia, agora
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
    """Tira o registro do banco E do data/registro_estudo.json.

    Os dois lugares, pelo mesmo motivo do descartar simulado: o arquivo so
    cresce, e o que saisse so do banco voltaria no proximo `importar`.
    """
    criar_tabelas()
    with sessao() as s:
        registro = s.scalar(select(RegistroDoDia).where(RegistroDoDia.data == data))
        if registro is not None:
            s.delete(registro)
    saiu_do_arquivo = acervo.esquecer_registros([data])
    return registro is not None or saiu_do_arquivo > 0


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

    @property
    def e_hoje(self) -> bool:
        return self.data == self.hoje

    @property
    def futuro(self) -> bool:
        return self.data > self.hoje

    @property
    def anterior(self) -> date:
        return self.data - timedelta(days=1)

    @property
    def proximo(self) -> date:
        return self.data + timedelta(days=1)


def _metas(plano) -> dict[date, str]:
    return {d: r.meta for d, r in registros(plano.inicio, plano.fim).items()}


def _montado(plano, data: date, metas: dict[date, str]):
    """O dia com o nivel efetivo da semana dele, como o `radar hoje` mostra."""
    gravado = plano.dia(data)
    if gravado is None:
        return None, None
    nivel = plano_de_estudo.niveis(plano, metas, data)[gravado.semana]
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
                     total_semanas=max((d.semana for d in plano.dias), default=0))
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
    return tela
