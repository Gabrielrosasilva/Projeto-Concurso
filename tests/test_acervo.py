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
