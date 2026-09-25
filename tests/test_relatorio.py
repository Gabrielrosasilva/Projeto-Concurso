"""A tela de questao focada e o relatorio pos-simulado.

O relatorio e onde o simulado vira estudo: para cada erro, a alternativa que
marquei, a correta, a explicacao e o macete - cada um com o selo de onde veio.
A explicacao e texto de IA importado pelo caminho sem API; aqui ela e escrita
pelo teste, e o que se testa e o que o radar aceita, recusa e mostra.
"""
import json

import pytest
from fastapi.testclient import TestClient

from radar import servico
from radar.servico import manual
from radar.web.app import app

from tests.test_foco import com_quadro_do_edital  # noqa: F401
from tests.test_home import CADERNO, _acervo, _responder


@pytest.fixture
def cliente(banco_temporario, com_quadro_do_edital):
    _acervo()
    return TestClient(app)


def _rodada_com_um_erro():
    """Uma rodada de 3: 2 certas e 1 errada, em Direito Penal."""
    _responder(certas=2, erradas=1)
    return servico.listar_simulados()[0].id


# --- a tela de questao ------------------------------------------------------

def test_a_questao_vem_sozinha_sem_a_barra(cliente):
    """Sem distracao: sem a navegacao do site, so a saida e o progresso."""
    simulado = servico.criar_simulado(quantidade=3, materia="Direito Penal")
    texto = cliente.get(f"/simulado/{simulado.id}").text

    assert "topo-barra" not in texto
    assert "Questão 1 de 3" in texto
    assert "sair da rodada" in texto
    assert "ds-selo--oficial" in texto          # extraida da prova


# --- o relatorio ------------------------------------------------------------

def test_o_relatorio_tem_resultado_materia_e_erros(cliente):
    texto = cliente.get(f"/simulado/{_rodada_com_um_erro()}").text

    assert "Resultado geral" in texto
    assert "2 de 3 questões desta rodada" in texto
    assert "Por matéria" in texto
    assert "1 erro(s) para entender" in texto
    assert "Você marcou b)" in texto
    assert "Gabarito definitivo a)" in texto


def test_nao_ha_nota_de_corte(cliente):
    """Sem resultado oficial publicado, nao ha fonte para nota de corte."""
    texto = cliente.get(f"/simulado/{_rodada_com_um_erro()}").text
    assert "Sem nota de corte" in texto
    assert "nota de corte estimada" not in texto.lower()


def test_sem_explicacao_o_erro_convida_a_pedir(cliente):
    texto = cliente.get(f"/simulado/{_rodada_com_um_erro()}").text
    assert "radar gerar --pedido --explicacoes" in texto


def _explicacao_importada(tmp_path, **mudancas):
    lote = manual.pedido_de_explicacoes()
    manual.salvar_pedido(lote)
    item = {"correta": "a", "explicacao": "A alternativa a e a correta porque "
            "o codigo penal diz exatamente isso no artigo citado.",
            "fonte": "art. 121 do Codigo Penal"}
    item.update(mudancas)
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({"lote": lote["lote"], "respostas": [
        {"id": p["id"], "explicacao": item} for p in lote["pedidos"]
    ]}), encoding="utf-8")
    return manual.importar(resposta)


def test_explicacao_importada_aparece_com_selo_e_fonte(cliente, tmp_path):
    rodada = _rodada_com_um_erro()
    assert _explicacao_importada(tmp_path)["gravadas"] == 1

    texto = cliente.get(f"/simulado/{rodada}").text

    assert "Explicação (IA)" in texto and "ds-bloco--ia" in texto
    assert "Fonte citada: art. 121 do Codigo Penal" in texto
    assert "importado manualmente" in texto


def test_explicacao_que_contradiz_o_gabarito_e_recusada(cliente, tmp_path):
    """O gabarito oficial manda: explicar outra letra ensinaria o erro."""
    _rodada_com_um_erro()
    resultado = _explicacao_importada(tmp_path, correta="b")

    assert resultado["gravadas"] == 0
    assert "gabarito oficial e a" in resultado["recusas"][0]


def test_explicacao_sem_fonte_e_recusada(cliente, tmp_path):
    _rodada_com_um_erro()
    resultado = _explicacao_importada(tmp_path, fonte="")
    assert resultado["gravadas"] == 0


def test_o_pedido_de_explicacao_e_das_erradas_e_nao_repete(cliente, tmp_path):
    _rodada_com_um_erro()
    lote = manual.pedido_de_explicacoes()
    assert len(lote["pedidos"]) == 1
    assert lote["pedidos"][0]["gabarito"] == "a"
    assert "GABARITO OFICIAL: a" in lote["pedidos"][0]["pedido"]

    _explicacao_importada(tmp_path)
    assert manual.pedido_de_explicacoes()["pedidos"] == []


def test_macete_que_cita_a_questao_aparece_no_erro(cliente):
    rodada = _rodada_com_um_erro()
    errada = next(i for i in servico.revisao(rodada) if not i.acertou)
    manual.caminho_dos_macetes().write_text(json.dumps([{
        "materia": "Direito Penal", "regra": "Uma regra pratica de teste, longa.",
        "fonte": "art. 121 do Codigo Penal", "impressao": "c" * 32,
        "questoes": [{"prova_url": CADERNO, "numero": errada.numero}],
        "modelo": "Claude Code, importado manualmente, em 25/09/2026",
        "criado_em": "2026-09-25T10:00:00+00:00",
    }]), encoding="utf-8")

    texto = cliente.get(f"/simulado/{rodada}").text

    assert "Macete relacionado" in texto
    assert "Uma regra pratica de teste" in texto
