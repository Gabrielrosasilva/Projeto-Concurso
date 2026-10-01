"""A classificacao das questoes do alvo pelo pedido em arquivo (Etapa 3A).

O pedido sai por materia, com a arvore e as regras; a resposta volta e so
entra o que esta inteiro e justificado. Cada recusa do roteiro tem um teste:
sem procedencia, sem justificativa, assunto fora do edital, tipo fora da
lista, questao fora do pedido - e "pendente" fica pendente, sem no forcado.
"""
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from radar import edital_programa
from radar.db import sessao
from radar.models import Classificacao, Conteudo, QuestaoDeProva
from radar.servico import classificacoes, conteudos, manual

FIXTURES = Path(__file__).parent / "fixtures"
PROGRAMA = edital_programa.ler_programa(
    (FIXTURES / "provas" / "edital_sap_2019_programa.txt").read_text(encoding="utf-8"))

IMPUTABILIDADE = "Imputabilidade penal"


def _questao(ano, numero, materia, anulada=False):
    return QuestaoDeProva(
        prova_url=f"https://fepese.test/{ano}.pdf", banca="FEPESE", ano=ano,
        numero=numero, materia=materia, cargo="Agente Penitenciário",
        enunciado=f"Questão {numero} de {ano} sobre {materia}?",
        alternativas={l: l for l in "abcde"}, resposta="a", anulada=anulada,
        impressao=f"{ano}-{numero}", evidencia="alvo")


@pytest.fixture
def alvo(banco_temporario):
    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        s.add(_questao(2019, 51, "Direito Penal"))
        s.add(_questao(2019, 52, "Direito Penal"))
        s.add(_questao(2019, 53, "Direito Penal", anulada=True))
        s.add(_questao(2013, 11, "Noções de Informática"))
        s.add(_questao(2013, 41, "Direito Administrativo"))
        s.add(_questao(2013, 47, "Direito Processo Penal"))
        # De outra evidencia: nao entra no pedido do alvo.
        outra = _questao(2016, 1, "Direito Penal")
        outra.evidencia = "complementar"
        s.add(outra)


def _pedido(materia):
    lote = manual.pedido_de_classificacao()
    return lote, next(p for p in lote["pedidos"] if p["materia"] == materia)


def _boa(codigo, **mudancas):
    item = {"questao": codigo, "status": "classificada", "assunto": IMPUTABILIDADE,
            "subassunto": "Menoridade", "elemento": "CP, art. 27",
            "tipo_elemento": "artigo", "referencia": "CP, art. 27",
            "tipo_de_questao": "literalidade da lei", "pegadinha": "16 anos",
            "trecho": "menores de 18 anos", "item_do_edital": "Imputabilidade penal",
            "dispositivo": "art. 27 do Código Penal"}
    item.update(mudancas)
    return item


def _importar(tmp_path, lote, respostas):
    manual.salvar_pedido(lote)
    arquivo = tmp_path / "resposta.json"
    arquivo.write_text(json.dumps({"lote": lote["lote"], "respostas": respostas}),
                       encoding="utf-8")
    return manual.importar(arquivo)


def _k(codigo):
    """A chave da questao do teste ("2019-51"): a classificacao e por ela."""
    with sessao() as s:
        q = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.impressao == codigo))
    return classificacoes.chave_de(q)


def _principal(codigo):
    with sessao() as s:
        return s.scalar(select(Classificacao).where(Classificacao.chave == _k(codigo))
                        .where(Classificacao.principal.is_(True)))


# --- o pedido ---------------------------------------------------------------------

def test_o_pedido_sai_por_materia_so_com_o_alvo(alvo):
    lote = manual.pedido_de_classificacao()

    por_materia = {p["materia"]: p for p in lote["pedidos"]}
    assert set(por_materia) == {"Direito Penal", "Noções de Informática",
                                "Direito Administrativo", "Direito Processual Penal"}
    penal = por_materia["Direito Penal"]
    assert set(penal["questoes"]) == {"2019-q51", "2019-q52", "2019-q53"}
    assert IMPUTABILIDADE in penal["assuntos_do_edital"]
    assert "artigo" in penal["elementos"]
    assert "ANULADA" in penal["pedido"]                     # vai, marcada
    assert "GABARITO OFICIAL: a" in penal["pedido"]
    # O sinonimo de 2013 leva a materia ao no do edital.
    assert set(por_materia["Direito Processual Penal"]["questoes"]) == {"2013-q47"}
    assert por_materia["Noções de Informática"]["fora_do_edital"] is True
    assert "Administração Pública" in por_materia["Direito Administrativo"]["outras_materias_do_edital"]


def test_a_questao_ja_conferida_sai_do_pedido(alvo):
    classificacoes.classificar(_k("2019-51"), "Direito Penal > " + IMPUTABILIDADE, "manual")
    classificacoes.conferir(_k("2019-51"))
    _, penal = _pedido("Direito Penal")
    assert "2019-q51" not in penal["questoes"]


# --- a importacao -----------------------------------------------------------------

def test_a_boa_entra_e_cria_o_subassunto_e_o_elemento(alvo, tmp_path):
    lote, penal = _pedido("Direito Penal")
    resultado = _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [_boa("2019-q51")]}])

    assert resultado["gravadas"] == 1 and resultado["recusas"] == []
    c = _principal("2019-51")
    assert c.conteudo == "Direito Penal > Imputabilidade penal > Menoridade > CP, art. 27"
    assert c.status == "completa"
    assert (c.tipo_de_questao, c.pegadinha, c.dispositivo) == (
        "literalidade da lei", "16 anos", "art. 27 do Código Penal")
    assert c.procedencia.startswith("Claude Code, importado manualmente")
    assert c.conferida_em is None
    with sessao() as s:
        elemento = s.scalar(select(Conteudo).where(Conteudo.caminho == c.conteudo))
    assert (elemento.origem, elemento.tipo_elemento) == ("classificacao", "artigo")
    assert elemento.procedencia == c.procedencia
    assert json.loads(classificacoes.caminho_do_arquivo().read_text(encoding="utf-8"))


@pytest.mark.parametrize("mudanca, motivo", [
    ({"trecho": ""}, "sem justificativa"),
    ({"item_do_edital": " "}, "sem justificativa"),
    ({"assunto": "Aplicação da lei penal"}, "assunto fora do edital"),
    ({"tipo_de_questao": "adivinhação"}, "fora do config/taxonomia.yml"),
    ({"subassunto": ""}, "elemento sem subassunto"),
    ({"tipo_elemento": "crase"}, "não é tipo de elemento"),
    ({"materia": "Direito Constitucional"}, "matéria trocada"),
    ({"questao": "2016-q1"}, "não estava no pedido"),
])
def test_o_que_a_importacao_recusa(alvo, tmp_path, mudanca, motivo):
    lote, penal = _pedido("Direito Penal")
    resultado = _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [
        _boa("2019-q51", **mudanca)]}])

    assert resultado["gravadas"] == 0
    (recusa,) = resultado["recusas"]
    assert motivo in recusa
    with sessao() as s:
        assert s.scalar(select(Classificacao)) is None
        # Recusa nao deixa no pela metade na arvore.
        assert s.scalar(select(Conteudo).where(Conteudo.origem == "classificacao")) is None


def test_sem_procedencia_nao_entra(alvo):
    _, penal = _pedido("Direito Penal")
    with pytest.raises(classificacoes.ClassificacaoInvalida, match="procedência"):
        classificacoes.aplicar_proposta(_boa("2019-q51"), penal, "")


def test_pendente_fica_pendente_sem_no_forcado(alvo, tmp_path):
    lote, penal = _pedido("Direito Penal")
    resultado = _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [
        {"questao": "2019-q52", "status": "pendente",
         "motivo": "aplicação da lei penal no tempo: o edital não lista"},
        {"questao": "2019-q53", "status": "pendente", "motivo": ""},
    ]}])

    assert resultado["gravadas"] == 1
    assert "pendente sem motivo" in resultado["recusas"][0]
    c = _principal("2019-52")
    assert (c.conteudo, c.status) == ("Direito Penal", "pendente")
    assert "lei penal no tempo" in c.trecho


def test_a_mesma_questao_duas_vezes_na_resposta(alvo, tmp_path):
    lote, penal = _pedido("Direito Penal")
    resultado = _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [
        _boa("2019-q51"), _boa("2019-q51", subassunto="Outro")]}])
    assert resultado["gravadas"] == 1
    assert "duas vezes" in resultado["recusas"][0]


def test_resposta_de_outro_lote_nao_entra(alvo, tmp_path):
    lote, penal = _pedido("Direito Penal")
    manual.salvar_pedido(lote)
    arquivo = tmp_path / "resposta.json"
    arquivo.write_text(json.dumps({"lote": "outro", "respostas": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="lote"):
        manual.importar(arquivo)


def test_fora_do_edital_vai_para_o_edital_so_justificado_ou_fica_nela(alvo, tmp_path):
    lote = manual.pedido_de_classificacao()
    adm = next(p for p in lote["pedidos"] if p["materia"] == "Direito Administrativo")
    info = next(p for p in lote["pedidos"] if p["materia"] == "Noções de Informática")
    resultado = _importar(tmp_path, lote, [
        {"id": adm["id"], "classificacoes": [_boa(
            "2013-q41", materia="Administração Pública",
            assunto="Organização administrativa: administração direta e indireta",
            item_do_edital="Organização administrativa: administração direta e indireta",
            subassunto="", elemento="", tipo_de_questao="conceito")]},
        {"id": info["id"], "classificacoes": [_boa(
            "2013-q11", assunto="Editor de textos", subassunto="", elemento="",
            item_do_edital="(sem edital atual: prova de 2013)", tipo_de_questao="conceito")]},
    ])

    assert resultado["recusas"] == []
    assert _principal("2013-41").conteudo == (
        "Administração Pública > Organização administrativa: administração direta e indireta")
    c = _principal("2013-11")
    assert (c.conteudo, c.status) == ("Noções de Informática > Editor de textos", "completa")
    with sessao() as s:
        novo = s.scalar(select(Conteudo).where(Conteudo.caminho == c.conteudo))
    assert novo.origem == "classificacao"


def test_a_materia_do_edital_nao_ganha_assunto_novo(alvo, tmp_path):
    lote, penal = _pedido("Direito Penal")
    resultado = _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [
        _boa("2019-q51", assunto="Assunto inventado", subassunto="", elemento="")]}])
    assert "assunto fora do edital" in resultado["recusas"][0]


def test_a_classificacao_conferida_nao_e_sobrescrita(alvo, tmp_path):
    lote, penal = _pedido("Direito Penal")
    classificacoes.classificar(_k("2019-51"), "Direito Penal > " + IMPUTABILIDADE, "manual")
    classificacoes.conferir(_k("2019-51"))
    resultado = _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [_boa("2019-q51")]}])
    assert "já conferida" in resultado["recusas"][0]


# --- a conferencia -----------------------------------------------------------------

def test_conferir_confirma_corrige_ou_deixa_pendente(alvo):
    caminho = "Direito Penal > " + IMPUTABILIDADE
    for codigo in ("2019-51", "2019-52", "2013-11"):
        classificacoes.classificar(_k(codigo), caminho, "Claude Code")

    classificacoes.conferir(_k("2019-51"))
    c = _principal("2019-51")
    assert c.conferida_em is not None and c.procedencia == "Claude Code"

    classificacoes.conferir(_k("2019-52"), corrigir_para="Direito Penal > Crimes contra a Administração Pública")
    c = _principal("2019-52")
    assert c.conteudo.endswith("Crimes contra a Administração Pública")
    assert (c.procedencia, c.conferida_em is not None) == ("manual", True)

    classificacoes.conferir(_k("2013-11"), pendente="não sei se é de Penal")
    c = _principal("2013-11")
    assert (c.conteudo, c.status) == ("Direito Penal", "pendente")
    assert "não sei se é de Penal" in c.trecho


# --- a tela ---------------------------------------------------------------------

def test_a_tela_mostra_a_proposta_e_grava_a_decisao(alvo):
    from fastapi.testclient import TestClient
    from radar.web.app import app

    caminho = "Direito Penal > " + IMPUTABILIDADE
    classificacoes.classificar(_k("2019-51"), caminho, "Claude Code, importado manualmente",
                               trecho="menores de 18", item_do_edital=IMPUTABILIDADE)
    cliente = TestClient(app)

    texto = cliente.get("/analises/conferencia?materia=Direito+Penal").text
    assert "Questão 51 de 2019 sobre Direito Penal?" in texto
    assert "← gabarito" in texto and "Direito Penal &gt; Imputabilidade penal" in texto
    assert "0 de 5" in texto                      # 6 do alvo, 1 anulada
    assert "2013-q11" not in texto                # o filtro da materia

    resposta = cliente.post("/analises/conferencia", data={
        "chave": _k("2019-51"), "acao": "confirmar", "materia": "Direito Penal"},
        follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == f"/analises/conferencia?materia=Direito+Penal#q-{_k('2019-51')}"
    assert _principal("2019-51").conferida_em is not None
    assert "1 de 5" in cliente.get("/analises/conferencia").text
    assert "2019-q51" not in cliente.get("/analises/conferencia?abertas=1").text

    cliente.post("/analises/conferencia", data={
        "chave": _k("2019-52"), "acao": "corrigir",
        "conteudo": "Direito Penal > Crimes contra a Administração Pública"})
    assert _principal("2019-52").procedencia == "manual"
    assert json.loads(classificacoes.caminho_do_arquivo().read_text(encoding="utf-8"))

    recusa = cliente.post("/analises/conferencia", data={"chave": _k("2019-51"), "acao": "x"})
    assert recusa.status_code == 400
