"""Banco antigo continua funcionando depois de um `git pull`.

Este teste existe por causa de um erro real: apos a fase 1.5, quem tinha o
banco da fase 1 tomava

    sqlite3.OperationalError: no such column: concursos.tipo

porque a coluna nova so existia no modelo. A correcao foi o programa criar a
coluna sozinho. Lembrar de apagar arquivo na mao nao pode ser requisito.
"""
from sqlalchemy import inspect, text

from radar import servico
from radar.db import criar_tabelas, get_engine, sessao
from radar.models import Concurso

# A tabela como ela era na fase 1: sem tipo, sem relevancia, sem salario.
SCHEMA_ANTIGO = """
CREATE TABLE concursos (
    id INTEGER NOT NULL PRIMARY KEY,
    url VARCHAR(800) NOT NULL UNIQUE,
    fonte VARCHAR(60),
    titulo VARCHAR(500),
    resumo TEXT,
    situacao VARCHAR(25),
    uf VARCHAR(2)
)
"""


def _criar_banco_antigo():
    engine = get_engine()
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS concursos"))
        conexao.execute(text(SCHEMA_ANTIGO))
        conexao.execute(
            text(
                "INSERT INTO concursos (url, fonte, titulo, uf, situacao) "
                "VALUES ('https://exemplo.test/antigo', 'concursosnobrasil', "
                "'Concurso Prefeitura de Palhoca (SC) abre vagas', 'SC', "
                "'edital_publicado')"
            )
        )


def test_colunas_novas_sao_criadas_sozinhas(banco_temporario):
    _criar_banco_antigo()
    criar_tabelas()

    colunas = {c["name"] for c in inspect(get_engine()).get_columns("concursos")}
    for nova in ("tipo", "relevancia", "motivo_relevancia", "salario", "municipio"):
        assert nova in colunas


def test_o_dado_antigo_sobrevive(banco_temporario):
    _criar_banco_antigo()
    criar_tabelas()

    with sessao() as s:
        concurso = s.query(Concurso).one()

    assert concurso.titulo == "Concurso Prefeitura de Palhoca (SC) abre vagas"
    assert concurso.uf == "SC"


def test_valor_padrao_preenche_as_linhas_que_ja_existiam(banco_temporario):
    """Sem isto, a linha antiga ficaria com tipo NULL e sumiria dos filtros."""
    _criar_banco_antigo()
    criar_tabelas()

    with sessao() as s:
        concurso = s.query(Concurso).one()

    assert concurso.tipo == "desconhecido"
    assert concurso.relevancia == "indefinida"


def test_a_consulta_que_quebrava_agora_funciona(banco_temporario):
    """Era exatamente este SELECT que estourava: WHERE tipo != 'noticia'."""
    _criar_banco_antigo()
    assert servico.listar(todas_relevancias=True) is not None


def test_reclassificar_conserta_o_registro_antigo(banco_temporario):
    """Depois de migrar, `radar reclassificar` preenche o que faltava."""
    _criar_banco_antigo()
    servico.reclassificar()

    with sessao() as s:
        concurso = s.query(Concurso).one()

    assert concurso.relevancia == "nucleo"        # Palhoca e Grande Floripa
    assert concurso.municipio == "Palhoca"
    assert "Palhoca" in concurso.motivo_relevancia
