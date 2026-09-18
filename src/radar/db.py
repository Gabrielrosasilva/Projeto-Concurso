"""Conexao com o banco.

O engine e criado na primeira vez que alguem pede, e nao na importacao do
modulo. Isso e o que permite um teste apontar para um SQLite temporario:
ele muda a variavel de ambiente e chama resetar_engine().
"""
from collections.abc import Iterator
from contextlib import contextmanager

import logging

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from radar import config
from radar.models import Base

log = logging.getLogger(__name__)

_engine: Engine | None = None
_Sessao: sessionmaker[Session] | None = None


def _registrar_sem_acento(engine: Engine) -> None:
    """Ensina o SQLite a comparar texto ignorando acento.

    Sem isto, procurar "Palhoca" no filtro nao acha "Palhoca" com cedilha - e
    quem digita no campo de busca raramente poe acento. O LIKE do SQLite ja
    ignora maiuscula/minuscula, mas nao acento.

    So vale para SQLite. Em Postgres a busca cai no LIKE comum, que continua
    funcionando - so exige o acento certo.
    """
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    import unicodedata

    from sqlalchemy import event

    def sem_acento(texto):
        if texto is None:
            return None
        normal = unicodedata.normalize("NFKD", str(texto))
        return "".join(c for c in normal if not unicodedata.combining(c))

    @event.listens_for(engine, "connect")
    def ao_conectar(conexao, _registro):  # noqa: ANN001
        conexao.create_function("sem_acento", 1, sem_acento)


def get_engine() -> Engine:
    global _engine, _Sessao
    if _engine is None:
        _engine = create_engine(config.url_do_banco(), future=True)
        _registrar_sem_acento(_engine)
        # expire_on_commit=False: sem isso, usar um objeto depois que a sessao
        # fechou dispara um SELECT novo e estoura. Como o servico devolve
        # objetos para a CLI e para a web, precisamos deles vivos.
        _Sessao = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def resetar_engine() -> None:
    """Descarta a conexao atual. Usado pelos testes entre um caso e outro."""
    global _engine, _Sessao
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Sessao = None


def criar_tabelas() -> None:
    """Deixa o banco igual ao modelo. Seguro rodar quantas vezes quiser."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    _adicionar_colunas_novas(engine)


def _adicionar_colunas_novas(engine: Engine) -> None:
    """Cria no banco as colunas que o modelo ganhou desde a ultima vez.

    Por que isto existe: o projeto nao usa Alembic, e sem isto toda coluna
    nova exigia apagar data/radar.db na mao depois de um `git pull`. Quem
    esquecia levava um "no such column" na cara. Lembrar de apagar arquivo
    nao pode ser requisito para o programa funcionar.

    O que isto faz e so ADICIONAR coluna, que e a unica mudanca de schema que
    este projeto teve ate hoje. Renomear, trocar tipo ou remover coluna
    continua fora do alcance - se um dia precisarmos disso, ai sim vale a
    conversa sobre Alembic.
    """
    inspetor = inspect(engine)

    for tabela in Base.metadata.sorted_tables:
        if not inspetor.has_table(tabela.name):
            continue

        existentes = {c["name"] for c in inspetor.get_columns(tabela.name)}
        faltando = [c for c in tabela.columns if c.name not in existentes]
        if not faltando:
            continue

        with engine.begin() as conexao:
            for coluna in faltando:
                tipo = coluna.type.compile(engine.dialect)
                # A coluna entra sempre aceitando nulo: o SQLite recusa
                # ADD COLUMN NOT NULL numa tabela que ja tem linhas, porque
                # nao saberia o que colocar nelas. O valor padrao e aplicado
                # logo abaixo, e o ORM continua preenchendo nas linhas novas.
                conexao.execute(
                    text(f'ALTER TABLE {tabela.name} ADD COLUMN {coluna.name} {tipo}')
                )

                padrao = getattr(coluna.default, "arg", None)
                if padrao is not None and not callable(padrao):
                    conexao.execute(
                        text(
                            f"UPDATE {tabela.name} SET {coluna.name} = :valor "
                            f"WHERE {coluna.name} IS NULL"
                        ),
                        {"valor": padrao},
                    )

                log.info("coluna %s.%s criada no banco", tabela.name, coluna.name)

        log.info(
            "Banco atualizado com %d coluna(s) nova(s). Rode `radar "
            "reclassificar` para preencher os registros antigos.",
            len(faltando),
        )


@contextmanager
def sessao() -> Iterator[Session]:
    """Abre uma sessao, faz commit no fim, rollback se der erro."""
    get_engine()
    assert _Sessao is not None
    s = _Sessao()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
