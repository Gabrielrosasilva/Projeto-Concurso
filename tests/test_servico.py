"""A gravacao insere, atualiza e nao estraga o que e seu."""
from datetime import datetime, timezone

import pytest

from radar import servico
from radar.collectors.base import Coletor, ItemColetado
from radar.db import sessao
from radar.models import Concurso
from sqlalchemy import select


def _item(**mudancas) -> ItemColetado:
    base = dict(
        titulo="Prefeitura de Palhoca abre concurso para Guarda Municipal",
        url="https://exemplo.test/palhoca-guarda",
        resumo="Salario de R$ 5.200.",
        uf="SC",
        situacao="edital_publicado",
        publicado_em=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    base.update(mudancas)
    return ItemColetado(**base)


def _gravar(item: ItemColetado) -> str:
    with sessao() as s:
        return servico._gravar(s, item, fonte="teste")


def _buscar() -> Concurso:
    with sessao() as s:
        return s.scalar(select(Concurso))


def test_item_novo_e_inserido(banco_temporario):
    assert _gravar(_item()) == "novo"
    assert _buscar().titulo.startswith("Prefeitura de Palhoca")


def test_mesma_url_nao_duplica(banco_temporario):
    _gravar(_item())
    assert _gravar(_item()) == "sem_mudanca"

    with sessao() as s:
        assert len(list(s.scalars(select(Concurso)))) == 1


def test_mudanca_de_situacao_atualiza_o_registro(banco_temporario):
    _gravar(_item())
    assert _gravar(_item(situacao="encerrado")) == "atualizado"
    assert _buscar().situacao == "encerrado"


def test_campo_vazio_da_fonte_nao_apaga_o_que_ja_existe(banco_temporario):
    """Uma coleta incompleta nao pode piorar um registro que ja estava bom."""
    _gravar(_item())
    _gravar(_item(resumo=None, uf=None))

    concurso = _buscar()
    assert concurso.resumo == "Salario de R$ 5.200."
    assert concurso.uf == "SC"


def test_coleta_nao_sobrescreve_suas_anotacoes(banco_temporario):
    _gravar(_item())

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
        concurso.interesse = "quero"
        concurso.notas = "estudar edital ate sexta"

    _gravar(_item(titulo="Titulo corrigido pela fonte"))

    concurso = _buscar()
    assert concurso.titulo == "Titulo corrigido pela fonte"   # a fonte manda aqui
    assert concurso.interesse == "quero"                      # e aqui nao
    assert concurso.notas == "estudar edital ate sexta"


class ColetorQuebrado(Coletor):
    nome = "quebrado"

    def coletar(self):
        raise RuntimeError("site fora do ar")


class ColetorBom(Coletor):
    nome = "bom"

    def coletar(self):
        return [_item()]


def test_fonte_que_falha_nao_derruba_as_outras(banco_temporario, monkeypatch):
    monkeypatch.setattr(servico, "COLETORES", [ColetorQuebrado, ColetorBom])

    resultados = {r.fonte: r for r in servico.coletar_tudo()}

    assert resultados["quebrado"].erro is not None
    assert resultados["bom"].novos == 1          # a boa foi gravada mesmo assim
