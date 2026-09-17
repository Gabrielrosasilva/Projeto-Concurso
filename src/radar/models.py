"""Modelos = tabelas do banco. Uma classe vira tabela, um atributo vira coluna.

O schema ja nasce completo, com colunas que so serao preenchidas em fases
futuras (prazos, salario, relevancia). Isso e de proposito: o projeto nao usa
Alembic, entao cada coluna nova depois significaria recriar o banco. Criar a
coluna vazia agora custa zero e evita esse incomodo.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def agora() -> datetime:
    """Momento atual, sempre em UTC e sempre com fuso explicito."""
    return datetime.now(timezone.utc)


class DataHoraUTC(TypeDecorator):
    """Coluna de data/hora que garante UTC nas duas pontas.

    Por que isso existe: o SQLite nao guarda fuso nenhum. Sem este tipo, voce
    grava um horario com fuso e le de volta um sem fuso, e ai comparar duas
    datas estoura com "can't compare offset-naive and offset-aware datetimes".
    Aqui a regra fica em um lugar so: na entrada converte para UTC, na saida
    devolve com UTC colado de volta.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:          # veio sem fuso: assumimos UTC
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


# --- Vocabularios fechados -------------------------------------------------
# Strings soltas pelo codigo viram erro de digitacao silencioso. Constante
# nomeada o compilador nao pega, mas o seu editor pega.

SITUACOES = (
    "prevista",           # so rumor ou expectativa, sem ato oficial
    "autorizado",         # governo autorizou a realizacao
    "banca_definida",     # banca contratada: edital costuma sair em 2-4 meses
    "edital_publicado",
    "inscricoes_abertas",
    "encerrado",
    "desconhecida",
)

RELEVANCIAS = ("nucleo", "proximo", "remoto", "indefinida")

ELEGIBILIDADES = ("elegivel", "inelegivel", "a_confirmar")


class Concurso(Base):
    __tablename__ = "concursos"

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- identidade ---------------------------------------------------------
    # A url e a chave natural: e o que diz se dois itens sao o mesmo concurso.
    url: Mapped[str] = mapped_column(String(800), unique=True, index=True)
    fonte: Mapped[str] = mapped_column(String(60), index=True)
    titulo: Mapped[str] = mapped_column(String(500))
    resumo: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- quem abriu ---------------------------------------------------------
    orgao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    municipio: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), index=True, nullable=True)
    banca: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)

    # --- ciclo de vida ------------------------------------------------------
    situacao: Mapped[str] = mapped_column(String(25), default="desconhecida", index=True)

    # --- prazos (fase 2.5: extraidos do PDF do edital) ----------------------
    inscricoes_de: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)
    inscricoes_ate: Mapped[datetime | None] = mapped_column(DataHoraUTC, index=True, nullable=True)
    data_prova: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)

    # --- filtro geografico (fase 1.5) --------------------------------------
    relevancia: Mapped[str] = mapped_column(String(15), default="indefinida", index=True)
    motivo_relevancia: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # --- filtro de elegibilidade (fase 2.5) --------------------------------
    salario: Mapped[float | None] = mapped_column(nullable=True)
    escolaridade: Mapped[str | None] = mapped_column(String(60), nullable=True)
    idade_maxima: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elegibilidade: Mapped[str] = mapped_column(String(15), default="a_confirmar", index=True)
    motivo_elegibilidade: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # --- suas anotacoes (fase 1.5) -----------------------------------------
    # Isto e SEU, nao da fonte: a coleta nunca sobrescreve estes dois campos.
    interesse: Mapped[str | None] = mapped_column(String(15), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- controle -----------------------------------------------------------
    publicado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)
    coletado_em: Mapped[datetime] = mapped_column(DataHoraUTC, default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DataHoraUTC, default=agora, onupdate=agora)

    # O que a fonte mandou e ainda nao virou coluna. Melhor guardar do que
    # descobrir daqui a tres meses que o dado existia e foi jogado fora.
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<Concurso {self.uf or '--'} {self.titulo[:50]!r}>"
