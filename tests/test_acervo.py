"""Exportar e importar preserva o conteudo e produz arquivo estavel."""
import json
from datetime import datetime, timezone

from sqlalchemy import select

from radar import acervo
from radar.db import sessao
from radar.models import Concurso


def _semear():
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/palhoca",
                fonte="teste",
                titulo="Guarda Municipal de Palhoca",
                uf="SC",
                situacao="edital_publicado",
                publicado_em=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
                interesse="quero",
                extra={"categorias": ["Santa Catarina"]},
            )
        )


def test_exporta_e_importa_sem_perder_dado(banco_temporario, tmp_path):
    _semear()
    arquivo = tmp_path / "concursos.json"
    assert acervo.exportar(arquivo) == 1

    # apaga tudo e reconstroi so a partir do JSON
    with sessao() as s:
        s.query(Concurso).delete()
    assert acervo.importar(arquivo) == 1

    with sessao() as s:
        concurso = s.scalar(select(Concurso))

    assert concurso.titulo == "Guarda Municipal de Palhoca"
    assert concurso.uf == "SC"
    assert concurso.interesse == "quero"
    assert concurso.extra == {"categorias": ["Santa Catarina"]}
    assert concurso.publicado_em == datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def test_exportar_duas_vezes_gera_arquivo_identico(banco_temporario, tmp_path):
    """Se o dado nao mudou, o commit diario nao deve ter diff nenhum."""
    _semear()
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    acervo.exportar(a)
    acervo.exportar(b)
    assert a.read_text() == b.read_text()


def test_json_e_legivel_por_humano(banco_temporario, tmp_path):
    _semear()
    arquivo = tmp_path / "concursos.json"
    acervo.exportar(arquivo)

    texto = arquivo.read_text(encoding="utf-8")
    assert "Guarda Municipal de Palhoca" in texto   # nao escapou em \u...
    assert texto.count("\n") > 5                    # esta indentado

    linhas = json.loads(texto)
    assert "id" not in linhas[0]                    # id e interno, nao exportado


def test_importar_arquivo_inexistente_nao_quebra(banco_temporario, tmp_path):
    assert acervo.importar(tmp_path / "nao-existe.json") == 0


# --- toda coluna de data precisa voltar como data ---------------------------

def test_toda_coluna_de_data_do_modelo_e_convertida():
    """A lista de colunas de data ja foi escrita a mao, e envelheceu calada:
    `avisado_em` entrou na fase 2 e `detalhado_em` na 2.5, nenhuma das duas foi
    acrescentada ali. O `radar importar` passou a quebrar com "'str' object has
    no attribute 'tzinfo'", e a coleta diaria do GitHub Actions falhava todo
    dia - na maquina local nao aparecia, porque o banco ja existia.

    Agora a lista vem do proprio modelo. Este teste guarda isso.
    """
    from radar.models import DataHoraUTC

    do_modelo = {
        c.name for c in Concurso.__table__.columns
        if isinstance(c.type, DataHoraUTC)
    }

    assert do_modelo == set(acervo.COLUNAS_DE_DATA)


def test_importar_num_banco_vazio_com_todas_as_datas(banco_temporario, tmp_path):
    """O caso do GitHub Actions: banco inexistente, JSON com todas as datas
    preenchidas."""
    quando = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    with sessao() as s:
        s.add(Concurso(
            url="https://exemplo.test/completo",
            fonte="teste",
            titulo="Concurso com todas as datas",
            publicado_em=quando,
            inscricoes_de=quando,
            inscricoes_ate=quando,
            data_prova=quando,
            detalhado_em=quando,
            avisado_em=quando,
        ))

    arquivo = tmp_path / "concursos.json"
    acervo.exportar(arquivo)

    # apaga tudo e reimporta, como o Actions faz todo dia
    with sessao() as s:
        for c in s.scalars(select(Concurso)):
            s.delete(c)

    assert acervo.importar(arquivo) == 1

    with sessao() as s:
        lido = s.scalars(select(Concurso)).first()
    for coluna in acervo.COLUNAS_DE_DATA:
        valor = getattr(lido, coluna)
        assert valor is None or valor.tzinfo is not None, coluna


def test_data_volta_como_datetime_e_nao_como_texto(banco_temporario, tmp_path):
    """O sintoma exato do defeito: o valor chegava ao banco como str."""
    valor = acervo._desserializar("avisado_em", "2026-09-17T12:00:00+00:00")

    assert isinstance(valor, datetime)
