"""A classificacao de nivel das geradas antigas (decisao 151).

Um pedido por materia, so das que nao tem nivel; a resposta da so o nivel, o
porque e a suspeita - o enunciado, as alternativas e o gabarito nao mudam. A
suspeita so e listada: nada e rejeitado por ela.
"""
import json

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from radar import acervo, cli, niveis
from radar.db import sessao
from radar.models import QuestaoGerada
from radar.servico import manual
from tests.test_treinar_pelo_no import DOLO, _gerada

runner = CliRunner()
DP = "Direito Penal"


@pytest.fixture
def estoque(banco_temporario):
    for numero in range(1, 4):
        _gerada(numero, DOLO, materia=DP, modelo="Claude Code, em 03/10/2026")
    _gerada(4, DOLO, materia=DP, nivel="facil", por_que_o_nivel="ja tinha")
    _gerada(5, DOLO, materia=DP, rejeitada=True)
    _gerada(6, None, materia="Raciocínio Lógico")


def _do_banco(numero: int) -> QuestaoGerada:
    with sessao() as s:
        return s.scalar(select(QuestaoGerada).where(QuestaoGerada.impressao == f"gerada{numero}"))


def _salvar_e_responder(tmp_path, lote: dict, niveis_: list[dict], ident="n1"):
    pedido = manual.salvar_pedido(lote, tmp_path / "pedido.json")
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({"lote": lote["lote"], "modelo": "claude-opus-5-5",
                                    "respostas": [{"id": ident, "niveis": niveis_}]}),
                        encoding="utf-8")
    return resposta, pedido


def _linha(numero: int, nivel="media", por_que="uma troca sutil de prazo", suspeita=""):
    return {"questao": f"gerada{numero}", "nivel": nivel, "por_que_o_nivel": por_que,
            "suspeita": suspeita}


# --- o pedido -----------------------------------------------------------------

def test_o_pedido_leva_so_as_sem_nivel_e_valendo_da_materia(estoque):
    lote = manual.pedido_de_niveis(DP)

    assert lote["tipo"] == "niveis"
    [pedido] = lote["pedidos"]
    assert [q["questao"] for q in pedido["questoes"]] == ["gerada1", "gerada2", "gerada3"]
    # O gabarito vai junto: e preciso para julgar o nivel e para desconfiar.
    assert pedido["questoes"][0]["resposta"] == "c"
    for nivel in niveis.NIVEIS.values():
        assert nivel.criterio in pedido["instrucao"]
    assert "NAO reescreva o enunciado" in pedido["instrucao"]
    assert "--classificar-nivel" in lote["como_responder"]
    assert lote["formato_da_resposta"]["respostas"][0]["niveis"][0]["suspeita"] == ""


def test_o_pedido_e_dividido_de_40_em_40(banco_temporario):
    for numero in range(1, 86):
        _gerada(numero, DOLO, materia=DP)

    lote = manual.pedido_de_niveis(DP)

    assert [len(p["questoes"]) for p in lote["pedidos"]] == [40, 40, 5]
    assert [p["id"] for p in lote["pedidos"]] == ["n1", "n2", "n3"]


def test_as_materias_sem_nivel_sao_contadas(estoque):
    assert manual.materias_sem_nivel() == {DP: 3, "Raciocínio Lógico": 1}


# --- a importacao -------------------------------------------------------------

def test_grava_so_o_nivel_e_nao_toca_no_texto(estoque, tmp_path):
    antes = _do_banco(1)
    texto = (antes.enunciado, dict(antes.alternativas), antes.resposta, antes.modelo)
    lote = manual.pedido_de_niveis(DP)
    resposta, pedido = _salvar_e_responder(tmp_path, lote, [
        dict(_linha(1, "dificil", "junta dois artigos"),
             # A resposta tenta mexer no texto: nao passa.
             enunciado="Outro enunciado", resposta="a")])

    resultado = manual.importar(resposta, pedido)

    assert resultado["tipo"] == "niveis" and resultado["gravadas"] == 1
    depois = _do_banco(1)
    assert (depois.enunciado, dict(depois.alternativas), depois.resposta,
            depois.modelo) == texto
    assert (depois.nivel, depois.por_que_o_nivel) == ("dificil", "junta dois artigos")
    assert depois.nivel_procedencia.startswith("Claude Code (claude-opus-5-5), importado manualmente")
    [linha] = [l for l in json.loads(acervo.caminho_das_geradas().read_text(encoding="utf-8"))
               if l["impressao"] == "gerada1"]
    assert linha["nivel"] == "dificil"


def test_a_resposta_torta_e_recusada_e_a_suspeita_so_listada(estoque, tmp_path):
    lote = manual.pedido_de_niveis(DP)
    resposta, pedido = _salvar_e_responder(tmp_path, lote, [
        _linha(1, suspeita="a alternativa C tambem esta certa pelo art. 18"),
        _linha(2, nivel="medio"),
        _linha(3, por_que=""),
        _linha(6),                       # de outra materia: nao estava no pedido
        _linha(1),                       # duas vezes
    ])

    resultado = manual.importar(resposta, pedido)

    assert resultado["gravadas"] == 1
    motivos = " | ".join(resultado["recusas"])
    assert "n1/gerada2: nivel 'medio' fora da lista" in motivos
    assert "n1/gerada3: sem o por_que_o_nivel" in motivos
    assert "n1/gerada6: a questao nao estava neste pedido" in motivos
    assert "n1/gerada1: classificada duas vezes" in motivos
    # A suspeita nao rejeita: a questao continua no sorteio, so com o aviso.
    assert resultado["suspeitas"] == [
        ("gerada1", DOLO, "a alternativa C tambem esta certa pelo art. 18")]
    questao = _do_banco(1)
    assert questao.rejeitada is False and questao.suspeita.startswith("a alternativa C")


def test_a_que_ja_tem_nivel_fica_com_o_dela(estoque, tmp_path):
    lote = manual.pedido_de_niveis(DP)
    # A 4 nao estava no pedido (ja tinha nivel); um pedido feito a mao com ela:
    lote["pedidos"][0]["questoes"].append({"questao": "gerada4"})
    resposta, pedido = _salvar_e_responder(tmp_path, lote, [_linha(4, "dificil")])

    resultado = manual.importar(resposta, pedido)

    assert resultado["gravadas"] == 0
    assert "ja tinha nivel" in " ".join(resultado["recusas"])
    assert _do_banco(4).nivel == "facil"


# --- o terminal ---------------------------------------------------------------

def test_sem_a_materia_o_terminal_para_e_lista(estoque):
    saida = runner.invoke(cli.app, ["gerar", "--pedido", "--classificar-nivel"])

    assert saida.exit_code == 1
    assert "Diga a matéria" in saida.output and '--materia "Direito Penal"' in saida.output


def test_o_terminal_faz_o_pedido_e_diz_a_importacao(estoque, tmp_path):
    saida = runner.invoke(cli.app, ["gerar", "--pedido", "--classificar-nivel",
                                    "--materia", DP])
    assert saida.exit_code == 0, saida.output
    assert "1 pedido(s) de nível" in saida.output and "3 questões" in saida.output

    lote = json.loads(manual.caminho_do_pedido().read_text(encoding="utf-8"))
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({"lote": lote["lote"], "modelo": "claude-opus-5-5",
                                    "respostas": [{"id": "n1", "niveis": [
                                        _linha(1, "facil"), _linha(2, "media"),
                                        _linha(3, "dificil", suspeita="o art. 18 mudou")]}]}),
                        encoding="utf-8")
    importada = runner.invoke(cli.app, ["gerar", "--importar", str(resposta)],
                              env={"COLUMNS": "200"})

    assert importada.exit_code == 0, importada.output
    assert "3 nível(is) gravado(s)" in importada.output
    assert "Nível: fácil/média/difícil 1/1/1" in importada.output
    assert "1 suspeita(s), para conferir:" in importada.output
    assert "o art. 18 mudou" in importada.output
