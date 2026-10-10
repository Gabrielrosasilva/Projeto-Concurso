"""O nivel da questao gerada: facil, media ou dificil (decisao 151).

O nivel e o que a IA declara, com a procedencia dela. As geradas de antes da
versao 8 do banco ficam "sem nivel" ate a classificacao; o JSON antigo, sem
as chaves, continua entrando; e a tela diz o nivel junto do 🟣.
"""
import json
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from radar import acervo, db, migracoes, niveis, servico
from radar.db import sessao
from radar.models import QuestaoGerada
from tests.test_treinar_pelo_no import DOLO, _gerada

COLUNAS_DO_NIVEL = ("nivel", "por_que_o_nivel", "nivel_procedencia", "suspeita")


@pytest.fixture
def cliente(banco_temporario):
    from radar.web.app import app

    return TestClient(app)


# --- o modulo puro -------------------------------------------------------------

def test_o_nivel_e_um_dos_tres_sem_caixa_nem_acento():
    assert niveis.normalizar("Difícil") == "dificil"
    assert niveis.normalizar(" MÉDIA ") == "media"
    assert niveis.normalizar("facil") == "facil"
    # Outra palavra nao vira nivel: aproximar seria inventar.
    for torto in ("medio", "muito dificil", "", None, "misturada"):
        assert niveis.normalizar(torto) is None


def test_o_rotulo_do_selo_diz_o_nivel_ou_sem_nivel():
    assert niveis.rotulo_do_selo("dificil") == "Gerada por IA · Difícil"
    assert niveis.rotulo_do_selo(None) == "Gerada por IA · sem nível"
    assert niveis.rotulo("misturada") == "Misturada"


# --- a migracao ----------------------------------------------------------------

def test_o_banco_da_versao_7_ganha_o_nivel_vazio(banco_temporario):
    """Um banco de antes (sem as quatro colunas) migra para a 8: a gerada
    antiga fica sem nivel, e o arquivo versionado ganha as chaves."""
    _gerada(1, DOLO, modelo="Claude Code, importado manualmente, em 03/10/2026")
    arquivo = db.get_engine().url.database
    db.resetar_engine()
    with closing(sqlite3.connect(arquivo)) as conexao:
        conexao.execute("DROP INDEX ix_questoes_geradas_nivel")
        for coluna in COLUNAS_DO_NIVEL:
            conexao.execute(f"ALTER TABLE questoes_geradas DROP COLUMN {coluna}")
        conexao.execute("UPDATE versao_do_banco SET versao = 7")
        conexao.commit()

    relatorio = migracoes.migrar()

    assert (relatorio.de, relatorio.para) == (7, 8)
    assert relatorio.copia is not None          # a copia antes, como todo passo
    with sessao() as s:
        gerada = s.scalar(select(QuestaoGerada))
    assert all(getattr(gerada, c) is None for c in COLUNAS_DO_NIVEL)
    [linha] = json.loads(acervo.caminho_das_geradas().read_text(encoding="utf-8"))
    assert all(c in linha and linha[c] is None for c in COLUNAS_DO_NIVEL)


# --- o JSON versionado ---------------------------------------------------------

def _linha(numero: int, **mais) -> dict:
    linha = {"impressao": f"g{numero}", "modo": "do_zero", "materia": "Direito Penal",
             "enunciado": f"Enunciado da gerada {numero}?",
             "alternativas": {l: l for l in "abcde"}, "resposta": "a",
             "modelo": "Claude Code, importado manualmente, em 03/10/2026",
             "criada_em": "2026-10-03T12:00:00+00:00"}
    linha.update(mais)
    return linha


def _gravar(linhas) -> None:
    acervo.caminho_das_geradas().write_text(json.dumps(linhas), encoding="utf-8")


def _do_banco(impressao: str) -> QuestaoGerada:
    with sessao() as s:
        return s.scalar(select(QuestaoGerada).where(QuestaoGerada.impressao == impressao))


NIVEL_DIFICIL = {"nivel": "dificil", "por_que_o_nivel": "junta os arts. 39 e 41",
                 "nivel_procedencia": "Claude Code (claude-opus-5-5), importado "
                                      "manualmente, em 10/10/2026"}


def test_o_json_antigo_sem_as_chaves_entra_sem_nivel(banco_temporario):
    _gravar([_linha(1)])

    assert acervo.importar_geradas() == 1
    assert _do_banco("g1").nivel is None


def test_o_json_novo_entra_com_o_nivel(banco_temporario):
    _gravar([_linha(1, **NIVEL_DIFICIL, suspeita=None)])

    acervo.importar_geradas()

    gerada = _do_banco("g1")
    assert gerada.nivel == "dificil"
    assert gerada.por_que_o_nivel == "junta os arts. 39 e 41"
    assert gerada.nivel_procedencia.startswith("Claude Code (claude-opus-5-5)")


def test_nivel_fora_da_lista_no_arquivo_fica_sem_nivel(banco_temporario):
    _gravar([_linha(1, nivel="muito dificil", por_que_o_nivel="?")])

    acervo.importar_geradas()

    gerada = _do_banco("g1")
    assert gerada.nivel is None and gerada.por_que_o_nivel is None


def test_o_nivel_chega_depois_na_gerada_que_ja_estava_no_banco(banco_temporario):
    """A classificacao feita em outra maquina: o `git pull` traz o arquivo com
    o nivel, e a gerada que ja estava aqui sem nivel ganha o dele."""
    _gravar([_linha(1)])
    acervo.importar_geradas()
    _gravar([_linha(1, **NIVEL_DIFICIL, suspeita="o gabarito parece ser B")])

    assert acervo.importar_geradas() == 0          # nao duplica
    gerada = _do_banco("g1")
    assert gerada.nivel == "dificil"
    assert gerada.suspeita == "o gabarito parece ser B"


def test_o_arquivo_nao_troca_o_nivel_que_o_banco_ja_tem(banco_temporario):
    _gravar([_linha(1, **NIVEL_DIFICIL)])
    acervo.importar_geradas()
    _gravar([_linha(1, nivel="facil", por_que_o_nivel="outra")])

    acervo.importar_geradas()

    assert _do_banco("g1").nivel == "dificil"


def test_exportar_leva_o_nivel_e_volta_igual(banco_temporario):
    _gravar([_linha(1, **NIVEL_DIFICIL), _linha(2)])
    acervo.importar_geradas()

    acervo.exportar_geradas()

    linhas = {l["impressao"]: l for l in
              json.loads(acervo.caminho_das_geradas().read_text(encoding="utf-8"))}
    assert linhas["g1"]["nivel"] == "dificil"
    assert linhas["g2"]["nivel"] is None


# --- o rotulo na questao -------------------------------------------------------

def _rodada_com(**nivel) -> tuple[int, int]:
    _gerada(1, DOLO, **nivel)
    rodada = servico.geradas.criar_simulado(quantidade=1, conteudo=DOLO)
    return rodada.id, _do_banco("gerada1").id


def test_a_questao_sem_nivel_diz_sem_nivel(cliente):
    rodada, _ = _rodada_com()

    tela = cliente.get(f"/simulado/{rodada}").text

    assert "Gerada por IA · sem nível" in tela


def test_a_questao_diz_o_nivel_e_o_porque_so_depois_de_responder(cliente):
    rodada, questao = _rodada_com(nivel="dificil",
                                  por_que_o_nivel="o item 3 esta errado")

    antes = cliente.get(f"/simulado/{rodada}").text
    assert "Gerada por IA · Difícil" in antes
    # O porque pode entregar a resposta (decisao 148): so depois.
    assert "o item 3 esta errado" not in antes

    cliente.post(f"/simulado/{rodada}/responder",
                 data={"questao_id": questao, "letra": "c"})
    depois = cliente.get(f"/simulado/{rodada}?ver={questao}").text
    assert "Gerada por IA · Difícil" in depois
    assert "Por que difícil, segundo a IA: o item 3 esta errado" in depois
