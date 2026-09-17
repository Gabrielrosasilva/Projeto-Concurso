"""Conexao com o banco.

O engine e criado na primeira vez que alguem pede, e nao na importacao do
modulo. Isso e o que permite um teste apontar para um SQLite temporario:
ele muda a variavel de ambiente e chama resetar_engine().
"""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from radar import config
from radar.models import Base

_engine: Engine | None = None
_Sessao: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _Sessao
    if _engine is None:
        _engine = create_engine(config.url_do_banco(), future=True)
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
    """Cria o que ainda nao existe. Seguro rodar quantas vezes quiser."""
    Base.metadata.create_all(get_engine())


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
