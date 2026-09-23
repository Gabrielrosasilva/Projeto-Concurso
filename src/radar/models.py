"""Modelos = tabelas do banco. Uma classe vira tabela, um atributo vira coluna.

O schema ja nasce completo, com colunas que so serao preenchidas em fases
futuras (prazos, salario, relevancia). Isso e de proposito: o projeto nao usa
Alembic, entao cada coluna nova depois significaria recriar o banco. Criar a
coluna vazia agora custa zero e evita esse incomodo.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
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

# Na ordem do que interessa: perto, perto o bastante, estadual de SC (eu
# presto onde for), longe, e o que ainda depende de ler o edital.
RELEVANCIAS = ("nucleo", "proximo", "estadual", "remoto", "indefinida")

TIPOS = ("concurso", "seletivo", "desconhecido", "noticia")

# O cargo e meu alvo? `principal` e a Policia Penal SC, que passa por cima do
# filtro de distancia e do teto de avisos. `secundario` e o resto da lista do
# CLAUDE.md, que so ganha a marca. Nulo = nao e cargo meu. Quem decide e
# config/alvo.yml, nunca o codigo.
ALVOS = ("principal", "secundario")

ELEGIBILIDADES = ("elegivel", "inelegivel", "a_confirmar")

# O que pode acontecer com um concurso e virar linha do tempo. O vocabulario e
# fechado pelo mesmo motivo dos outros: string solta pelo codigo vira erro de
# digitacao silencioso.
TIPOS_DE_EVENTO = (
    "apareceu",               # entrou no radar pela primeira vez
    "mudou_situacao",         # qualquer outro passo do ciclo de vida
    "edital_publicado",       # saiu o edital
    "inscricoes_abertas",     # o prazo abriu
    "inscricoes_encerradas",  # o prazo fechou
    "edital_retificado",      # o PDF do edital mudou de conteudo
    "prova_marcada",          # a data da prova ficou conhecida
)


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

    # concurso | seletivo | desconhecido | noticia
    # `noticia` e o que veio junto no feed sem ser concurso; fica guardado em
    # vez de apagado, para eu conferir se o filtro nao esta comendo coisa boa.
    tipo: Mapped[str] = mapped_column(String(15), default="desconhecido", index=True)

    # --- prazos (fase 2.5: extraidos do PDF do edital) ----------------------
    inscricoes_de: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)
    inscricoes_ate: Mapped[datetime | None] = mapped_column(DataHoraUTC, index=True, nullable=True)
    data_prova: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)

    # --- filtro geografico (fase 1.5) --------------------------------------
    relevancia: Mapped[str] = mapped_column(String(15), default="indefinida", index=True)
    motivo_relevancia: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # --- filtro de cargo ----------------------------------------------------
    # principal | secundario | nulo. Sai de config/alvo.yml, e como a
    # relevancia e recalculado a cada `radar reclassificar`.
    alvo: Mapped[str | None] = mapped_column(String(15), index=True, nullable=True)
    motivo_alvo: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # --- filtro de elegibilidade (fase 2.5) --------------------------------
    salario: Mapped[float | None] = mapped_column(nullable=True)
    escolaridade: Mapped[str | None] = mapped_column(String(60), nullable=True)
    idade_maxima: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elegibilidade: Mapped[str] = mapped_column(String(15), default="a_confirmar", index=True)
    motivo_elegibilidade: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Liga quando EU digito o salario na tela. A partir dai o classificador
    # nao encosta mais no campo: o valor que eu li no edital vale mais que o
    # que da para adivinhar pelo titulo.
    salario_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    # Liga quando o municipio veio da PAGINA do edital ("lotacao em
    # Florianopolis"), e nao do titulo. A pagina e fonte melhor, entao o
    # classificador - que so ve o titulo - para de mexer no campo.
    municipio_confirmado: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- suas anotacoes (fase 1.5) -----------------------------------------
    # Isto e SEU, nao da fonte: a coleta nunca sobrescreve estes dois campos.
    interesse: Mapped[str | None] = mapped_column(String(15), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quando li a pagina do post atras de prazo, banca e lotacao. Preenchido
    # mesmo quando nao achei nada: serve para nao ficar buscando a mesma
    # pagina toda vez.
    detalhado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)

    # --- avisos (fase 2) ----------------------------------------------------
    # Quando o Telegram foi avisado sobre este concurso. Nulo = ainda nao
    # avisei. E o que impede a coleta de amanha de reavisar o de hoje.
    avisado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)

    # --- controle -----------------------------------------------------------
    publicado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)
    coletado_em: Mapped[datetime] = mapped_column(DataHoraUTC, default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DataHoraUTC, default=agora, onupdate=agora)

    # O que a fonte mandou e ainda nao virou coluna. Melhor guardar do que
    # descobrir daqui a tres meses que o dado existia e foi jogado fora.
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<Concurso {self.uf or '--'} {self.titulo[:50]!r}>"


class Evento(Base):
    """Uma coisa que aconteceu com um concurso, na ordem em que aconteceu.

    Existe porque o resto do banco guarda so o AGORA. Quando a situacao muda, o
    valor antigo e sobrescrito e ninguem lembra que ele existiu: nao da para
    responder "quando foi que essa inscricao abriu?" nem "esse edital ja tinha
    sido retificado antes?". Aqui a mudanca vira linha, e a linha fica.

    O concurso e apontado pela URL, e nao pelo id, de proposito: a url e a
    chave natural do projeto, e o id muda quando o banco e reconstruido a
    partir de data/concursos.json. Evento amarrado a id nao sobreviveria a um
    `radar importar`.
    """

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(primary_key=True)
    concurso_url: Mapped[str] = mapped_column(String(800), index=True)

    # Quando aconteceu - ou, quando nao da para saber o momento exato, quando
    # o radar percebeu. Nunca fica vazio.
    data: Mapped[datetime] = mapped_column(DataHoraUTC, default=agora, index=True)

    tipo: Mapped[str] = mapped_column(String(30), index=True)
    descricao: Mapped[str] = mapped_column(String(300))

    # Para onde ir para conferir: a pagina do concurso, ou o PDF que mudou.
    link: Mapped[str | None] = mapped_column(String(800), nullable=True)

    # Quando este evento virou mensagem no Telegram. Nulo = ainda nao avisei.
    # So evento de concurso FAVORITO vira aviso, e so os tipos que mudam o que
    # eu tenho que fazer - o resto fica na linha do tempo, para eu ler quando
    # quiser, sem tocar o celular.
    avisado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)

    def __repr__(self) -> str:
        return f"<Evento {self.tipo} {self.data:%d/%m/%Y}>"


class QuestaoDeProva(Base):
    """Uma questao objetiva tirada de um caderno de prova.

    Tabela separada dos concursos de proposito: uma prova rende 40 questoes, e
    misturar as duas coisas na mesma tabela nao ajudaria ninguem.
    """

    __tablename__ = "questoes"
    __table_args__ = (
        # A mesma questao do mesmo caderno nao entra duas vezes, e isso
        # permite rodar a extracao de novo sem duplicar nada.
        UniqueConstraint("prova_url", "numero", name="uq_questao_prova_numero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # De onde veio
    prova_url: Mapped[str] = mapped_column(String(800), index=True)
    concurso_url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    banca: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    ano: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    municipio: Mapped[str | None] = mapped_column(String(150), nullable=True)
    cargo: Mapped[str | None] = mapped_column(String(300), index=True, nullable=True)

    # A questao
    numero: Mapped[int] = mapped_column(Integer)
    materia: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    enunciado: Mapped[str] = mapped_column(Text)
    alternativas: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    resposta: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Hash do enunciado. Questao repetida entre provas e o padrao mais forte
    # que existe, e e por aqui que se acha.
    impressao: Mapped[str] = mapped_column(String(32), index=True)

    # Assunto fino dentro da materia ("Direito Penal", "Primeiros Socorros").
    # Vazio por enquanto: e o passo seguinte da fase 4.
    assunto: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)

    extraida_em: Mapped[datetime] = mapped_column(DataHoraUTC, default=agora)

    def __repr__(self) -> str:
        return f"<Questao {self.numero} {self.materia} {self.enunciado[:40]!r}>"


class Simulado(Base):
    """Uma rodada de questoes respondidas.

    O estado fica no banco, e nao numa sessao do navegador: assim da para
    fechar a pagina no meio e voltar depois, e o historico serve para medir se
    eu estou melhorando.
    """

    __tablename__ = "simulados"

    id: Mapped[int] = mapped_column(primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(DataHoraUTC, default=agora)
    finalizado_em: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)

    # Com que filtros ele foi montado. Guardado para eu saber depois o que
    # aquele resultado significava.
    filtros: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<Simulado {self.id} de {self.criado_em:%d/%m/%Y}>"


class RespostaDeSimulado(Base):
    """Uma questao dentro de um simulado, e o que eu marquei nela."""

    __tablename__ = "respostas_de_simulado"
    __table_args__ = (
        UniqueConstraint("simulado_id", "questao_id", name="uq_resposta_questao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    simulado_id: Mapped[int] = mapped_column(Integer, index=True)
    questao_id: Mapped[int] = mapped_column(Integer, index=True)

    # A ordem em que a questao aparece nesta rodada.
    ordem: Mapped[int] = mapped_column(Integer)

    # Nulo enquanto nao respondi. E isso que diz onde eu parei.
    escolhida: Mapped[str | None] = mapped_column(String(1), nullable=True)
    acertou: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    respondida_em: Mapped[datetime | None] = mapped_column(DataHoraUTC, nullable=True)

    def __repr__(self) -> str:
        return f"<Resposta q{self.questao_id} = {self.escolhida}>"
