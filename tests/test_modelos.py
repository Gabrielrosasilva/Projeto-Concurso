"""Datas voltam do banco sempre com fuso, em UTC."""
from datetime import datetime, timezone

from sqlalchemy import select

from radar.db import sessao
from radar.models import Concurso


def test_data_gravada_volta_com_fuso(banco_temporario):
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/1",
                fonte="teste",
                titulo="Concurso qualquer",
                publicado_em=datetime(2026, 3, 1, 15, 0, tzinfo=timezone.utc),
            )
        )

    with sessao() as s:
        concurso = s.scalar(select(Concurso))

    assert concurso.publicado_em.tzinfo is not None
    assert concurso.publicado_em == datetime(2026, 3, 1, 15, 0, tzinfo=timezone.utc)
    # coletado_em tem valor padrao e tambem precisa vir com fuso
    assert concurso.coletado_em.tzinfo is not None


def test_valores_padrao(banco_temporario):
    with sessao() as s:
        s.add(Concurso(url="https://exemplo.test/2", fonte="teste", titulo="X"))

    with sessao() as s:
        concurso = s.scalar(select(Concurso).where(Concurso.url.endswith("/2")))

    assert concurso.situacao == "desconhecida"
    assert concurso.relevancia == "indefinida"
    assert concurso.elegibilidade == "a_confirmar"
    assert concurso.extra == {}
