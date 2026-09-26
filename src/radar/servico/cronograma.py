"""O diario do cronograma: como foi cada dia, anotado a mao.

A meta do dia e uma das quatro do plano - ideal, reduzida, minima, ou nao
fiz. Questoes feitas e acertos sao o que EU digito, e a maior parte vem do
Qconcursos: por isso ficam aqui, numa tabela so deles, e NAO entram em
acerto medido nenhum do radar. O Meu foco, o Onde estudar e a home contam so
o que eu respondi dentro do radar, questao por questao; somar um numero
digitado a mao ali misturaria medida com lembranca.
"""
from datetime import date, datetime

from sqlalchemy import select

from radar import acervo
from radar import cronograma as plano_de_estudo
from radar.db import criar_tabelas, sessao
from radar.models import RegistroDoDia, agora
from radar.util import fuso_local

METAS = ("ideal", "reduzida", "minima", "nao_fiz")


class RegistroInvalido(ValueError):
    """O registro foi recusado. A mensagem diz por que."""


def hoje_local() -> date:
    return datetime.now(fuso_local()).date()


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
