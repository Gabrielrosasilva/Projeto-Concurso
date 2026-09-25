"""O caminho sem API: `radar gerar --pedido`, e `--importar` da resposta.

Nenhum teste fala com IA nenhuma. A "resposta" e um arquivo escrito aqui, do
jeito que o Claude Code deixaria - e o que se testa e o que o radar faz com
ela: aceita a certa, recusa a torta, e nunca a chama de saida da API.
"""
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from radar import acervo, cli, gerador, servico
from radar.db import sessao
from radar.models import QuestaoGerada
from radar.servico import manual

from tests.test_gerador import _concurso, _questao_boa, _real, _semear

runner = CliRunner()
DIA = datetime(2026, 9, 25, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def acervo_do_alvo(banco_temporario):
    _semear(
        _concurso(),
        _real(81), _real(82),
        _real(1, materia="Língua Portuguesa", enunciado="Assinale a crase certa.",
              impressao="port1"),
    )


def _responder(lote: dict, respostas: list[dict], tmp_path, nome="resposta.json"):
    arquivo = tmp_path / nome
    arquivo.write_text(
        json.dumps({"lote": lote["lote"], "respostas": respostas}), encoding="utf-8"
    )
    return arquivo


def _pedido_salvo(lote):
    manual.salvar_pedido(lote)
    return lote


# --- o pedido ---------------------------------------------------------------

def test_o_pedido_leva_todos_os_pedidos_com_instrucao_e_formato(acervo_do_alvo):
    lote = manual.pedido_de_questoes(materia="Lei de Execução Penal", quantas=5)

    assert len(lote["pedidos"]) == 2          # 3 + 2, como o --valendo faria
    assert lote["como_responder"] and lote["formato_da_resposta"]
    for pedido in lote["pedidos"]:
        assert pedido["instrucao"] == gerador.INSTRUCAO_VARIACAO
        assert "GABARITO OFICIAL" in pedido["pedido"]


def test_o_pedido_vai_para_o_arquivo_e_nao_gasta(acervo_do_alvo, monkeypatch):
    """Nada de API: se alguem chamar a rede aqui, o teste estoura."""
    monkeypatch.setattr(gerador, "_chamar", lambda *a, **k: pytest.fail("API"))

    resultado = runner.invoke(cli.app, ["gerar", "--pedido", "--quantas", "4"])

    assert resultado.exit_code == 0
    salvo = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    assert salvo["tipo"] == "questoes"
    assert sum(p["quantas"] for p in salvo["pedidos"]) == 4


def test_o_pedido_de_macete_e_um_por_materia_com_os_codigos(acervo_do_alvo):
    lote = manual.pedido_de_macetes()

    materias = {p["materia"]: p for p in lote["pedidos"]}
    assert set(materias) == {"Lei de Execução Penal", "Língua Portuguesa"}
    lep = materias["Lei de Execução Penal"]
    assert set(lep["citaveis"]) == {"2019-q81", "2019-q82"}
    assert "[2019-q81]" in lep["pedido"]


# --- a importacao da questao ------------------------------------------------

def test_importa_e_grava_com_a_procedencia_honesta(acervo_do_alvo, tmp_path):
    lote = _pedido_salvo(manual.pedido_de_questoes("Lei de Execução Penal", 3))
    arquivo = _responder(lote, [{"id": "p1", "questoes": [_questao_boa()]}], tmp_path)

    resultado = manual.importar(arquivo, quando=DIA)

    assert resultado["gravadas"] == 1
    with sessao() as s:
        (gerada,) = s.scalars(select(QuestaoGerada))
    assert gerada.modelo == "Claude Code, importado manualmente, em 25/09/2026"
    # NUNCA como saida da API.
    assert gerada.modelo != gerador.MODELO
    assert gerada.origem_impressao == lote["pedidos"][0]["origem_impressao"]
    # E o arquivo versionado ja a carrega.
    linhas = json.loads(acervo.caminho_das_geradas().read_text(encoding="utf-8"))
    assert [l["modelo"] for l in linhas] == [gerada.modelo]


@pytest.mark.parametrize("estrago, motivo", [
    (lambda q: q["alternativas"].pop("e"), "5 alternativas"),
    (lambda q: q.update(resposta="f"), "gabarito"),
    (lambda q: q.update(artigo=""), "artigo"),
    (lambda q: q.update(artigo="conforme a doutrina"), "artigo"),
])
def test_questao_torta_e_recusada_e_dita(acervo_do_alvo, tmp_path, estrago, motivo):
    lote = _pedido_salvo(manual.pedido_de_questoes("Lei de Execução Penal", 3))
    torta = _questao_boa()
    estrago(torta)
    arquivo = _responder(lote, [{"id": "p1", "questoes": [torta]}], tmp_path)

    resultado = manual.importar(arquivo)

    assert resultado["gravadas"] == 0
    assert len(resultado["recusas"]) == 1 and motivo in resultado["recusas"][0]


def test_fora_de_direito_basta_a_regra(acervo_do_alvo, tmp_path):
    """Portugues nao tem artigo de lei; a regra gramatical serve de fonte."""
    lote = _pedido_salvo(manual.pedido_de_questoes("Língua Portuguesa", 1))
    questao = _questao_boa("Assinale a alternativa com a crase correta.")
    questao["artigo"] = "crase: fusao da preposicao a com o artigo a"
    arquivo = _responder(lote, [{"id": "p1", "questoes": [questao]}], tmp_path)

    assert manual.importar(arquivo)["gravadas"] == 1


def test_questao_a_mais_do_que_o_pedido_e_recusada(acervo_do_alvo, tmp_path):
    lote = _pedido_salvo(manual.pedido_de_questoes("Lei de Execução Penal", 1))
    arquivo = _responder(lote, [{"id": "p1", "questoes": [
        _questao_boa("Primeira questao sobre execucao penal."),
        _questao_boa("Segunda questao sobre execucao penal."),
    ]}], tmp_path)

    resultado = manual.importar(arquivo)
    assert resultado["gravadas"] == 1 and len(resultado["recusas"]) == 1


def test_resposta_de_outro_lote_e_recusada_inteira(acervo_do_alvo, tmp_path):
    velho = manual.pedido_de_questoes("Lei de Execução Penal", 3)
    velho["lote"] = "questoes-velho"
    arquivo = _responder(velho, [{"id": "p1", "questoes": [_questao_boa()]}], tmp_path)
    _pedido_salvo(manual.pedido_de_questoes("Lei de Execução Penal", 3))

    with pytest.raises(ValueError, match="lote"):
        manual.importar(arquivo)


def test_a_trava_de_procedencia_vale_para_qualquer_caminho(banco_temporario):
    """Questao sem modelo nao entra, venha de onde vier."""
    sem_origem = gerador.QuestaoNova(
        enunciado="Questao sem dizer de onde veio, e longa.",
        alternativas={l: l for l in "abcde"}, resposta="a",
    )
    with pytest.raises(ValueError, match="modelo"):
        servico.geradas.gravar([sem_origem])


def test_arquivo_de_geradas_sem_procedencia_nao_entra(banco_temporario):
    acervo.caminho_das_geradas().write_text(json.dumps([{
        "impressao": "x1", "enunciado": "escrita a mao", "modo": "variacao",
        "alternativas": {}, "resposta": "a",
    }]), encoding="utf-8")

    assert acervo.importar_geradas() == 0


# --- a importacao do macete -------------------------------------------------

def _macete(**mudancas):
    base = {"assunto": "Progressao", "regra": "Progressao exige o requisito "
            "objetivo e o subjetivo, sempre os dois.",
            "fonte": "art. 112 da Lei 7.210/1984",
            "pegadinha": "a banca cita so um dos requisitos",
            "questoes": ["2019-q81"]}
    base.update(mudancas)
    return base


def _id_da_lep(lote):
    return next(p["id"] for p in lote["pedidos"]
                if p["materia"] == "Lei de Execução Penal")


def test_macete_entra_no_arquivo_com_as_questoes_reais(acervo_do_alvo, tmp_path):
    lote = _pedido_salvo(manual.pedido_de_macetes())
    arquivo = _responder(lote, [{"id": _id_da_lep(lote), "macetes": [_macete()]}],
                         tmp_path)

    resultado = manual.importar(arquivo, quando=DIA)

    assert resultado["tipo"] == "macetes" and resultado["gravadas"] == 1
    (macete,) = manual.carregar_macetes()
    assert macete["modelo"] == "Claude Code, importado manualmente, em 25/09/2026"
    assert macete["questoes"][0]["numero"] == 81
    assert macete["questoes"][0]["prova_url"] == "https://fepese.test/sap2019.pdf"


@pytest.mark.parametrize("mudanca, motivo", [
    ({"fonte": ""}, "fonte"),
    ({"questoes": ["2019-q99"]}, "nao estava no pedido"),
    ({"questoes": []}, "nao estava no pedido"),
    ({"regra": "curta"}, "regra"),
])
def test_macete_torto_e_recusado(acervo_do_alvo, tmp_path, mudanca, motivo):
    lote = _pedido_salvo(manual.pedido_de_macetes())
    arquivo = _responder(
        lote, [{"id": _id_da_lep(lote), "macetes": [_macete(**mudanca)]}], tmp_path
    )

    resultado = manual.importar(arquivo)

    assert resultado["gravadas"] == 0
    assert motivo in resultado["recusas"][0]


def test_importar_o_mesmo_macete_duas_vezes_nao_duplica(acervo_do_alvo, tmp_path):
    lote = _pedido_salvo(manual.pedido_de_macetes())
    arquivo = _responder(lote, [{"id": _id_da_lep(lote), "macetes": [_macete()]}],
                         tmp_path)
    manual.importar(arquivo)
    manual.importar(arquivo)

    assert len(manual.carregar_macetes()) == 1


def test_a_cli_conta_as_recusas_em_voz_alta(acervo_do_alvo, tmp_path):
    lote = _pedido_salvo(manual.pedido_de_questoes("Lei de Execução Penal", 3))
    arquivo = _responder(lote, [{"id": "p1", "questoes": [
        _questao_boa(), {**_questao_boa("Outra questao, esta sem artigo."),
                         "artigo": ""},
    ]}], tmp_path)

    resultado = runner.invoke(cli.app, ["gerar", "--importar", str(arquivo)])

    assert resultado.exit_code == 0
    assert "1 questao(oes) gravado(s)" in resultado.output
    assert "1 recusada(s)" in resultado.output
    assert "importado manualmente" in resultado.output
