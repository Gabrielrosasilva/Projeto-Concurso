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


def test_a_conferencia_esconde_as_anuladas_e_a_caixa_traz_de_volta(banco_temporario):
    """A banca desfez a pergunta: conferir uma anulada nao muda numero nenhum,
    e ela so atrapalha a lista. Os totais continuam mostrando as duas contas."""
    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        for numero, anulada in ((1, False), (2, True)):
            q = QuestaoDeProva(
                prova_url="https://fepese.test/2019.pdf", banca="FEPESE", ano=2019,
                numero=numero, materia="Direito Penal",
                enunciado=f"Questão {numero} de 2019?",
                alternativas={"a": "x", "b": "y"}, resposta=None if anulada else "a",
                anulada=anulada, impressao=f"2019-{numero}", evidencia="alvo")
            s.add(q)

    tela = classificacoes.conferencia()
    assert [i.codigo for i in tela.itens] == ["2019-q1"]
    assert (tela.total, tela.validas) == (2, 1)

    com = classificacoes.conferencia(com_anuladas=True)
    assert [i.codigo for i in com.itens] == ["2019-q1", "2019-q2"]


def test_a_tela_de_conferencia_nao_lista_anulada_sem_a_caixa(banco_temporario):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    conteudos.semear(programa=PROGRAMA)
    with sessao() as s:
        s.add(QuestaoDeProva(
            prova_url="https://fepese.test/2019.pdf", banca="FEPESE", ano=2019,
            numero=7, materia="Direito Penal", enunciado="Questão anulada de 2019?",
            alternativas={"a": "x"}, anulada=True, impressao="2019-7", evidencia="alvo"))

    cliente = TestClient(app)
    assert "2019-q7" not in cliente.get("/analises/conferencia").text
    assert "2019-q7" in cliente.get("/analises/conferencia?anuladas=1").text


# --- o complementar aceito (B.8) ---------------------------------------------------

def _aceitar(*urls):
    """O arquivo de status do complementar, com estas provas aceitas."""
    from radar.servico import complementar
    complementar.caminho_do_registro().write_text(json.dumps(
        {"provas": [{"prova_url": u, "aceita": True} for u in urls]}), encoding="utf-8")


def _do_complementar(url, numero, enunciado, cargo="Agente de Trânsito"):
    return QuestaoDeProva(
        prova_url=url, banca="FEPESE", ano=2024, municipio="Brusque", cargo=cargo,
        numero=numero, materia="Direito Penal", enunciado=enunciado,
        alternativas={l: l for l in "abcde"}, resposta="b",
        impressao=f"{url}-{numero}", evidencia="complementar")


def _linha(chave):
    with sessao() as s:
        return s.scalar(select(Classificacao).where(Classificacao.chave == chave)
                        .where(Classificacao.principal.is_(True)))


def test_o_complementar_lista_so_o_aceito_e_uma_linha_por_questao(alvo):
    aceita = "https://fepese.test/2024/A.pdf"
    outra_aceita = "https://fepese.test/2024/B.pdf"
    recusada = "https://fepese.test/2024/C.pdf"
    _aceitar(aceita, outra_aceita)
    with sessao() as s:
        # A mesma questao em dois cadernos aceitos do concurso, um por cargo.
        s.add(_do_complementar(aceita, 1, "Sobre a imputabilidade, é correto?"))
        s.add(_do_complementar(outra_aceita, 1, "Sobre a imputabilidade, é correto?",
                               cargo="Fiscal de Tributos"))
        s.add(_do_complementar(aceita, 2, "Questão que ninguém classificou?"))
        s.add(_do_complementar(recusada, 3, "Questão de prova recusada?"))
    caminho = "Direito Penal > " + IMPUTABILIDADE
    for codigo in (f"{aceita}-1", f"{recusada}-3", "2019-51"):
        classificacoes.classificar(_k(codigo), caminho, "Claude Code")

    tela = classificacoes.conferencia(evidencia_escolhida="complementar")

    (item,) = tela.itens
    assert item.enunciado == "Sobre a imputabilidade, é correto?"
    assert item.outros_cadernos == 1
    assert item.codigo == "FEPESE 2024 · Brusque · Agente de Trânsito · q1"
    assert (tela.total, tela.evidencia, tela.amostras) == (1, "complementar", [])
    # E o alvo continua so com o alvo: nada do complementar entra nele.
    alvo_ = classificacoes.conferencia()
    assert "Sobre a imputabilidade, é correto?" not in [i.enunciado for i in alvo_.itens]
    assert alvo_.total == 6


def test_a_amostra_do_catalogo_e_fixa_e_a_correcao_conta_o_erro(alvo, monkeypatch):
    import dataclasses

    from radar import amostra as regua
    monkeypatch.setattr(regua, "carregar", lambda caminho=None: dataclasses.replace(
        regua.PADRAO, amostra_do_catalogo=2))
    url = "https://fepese.test/2024/A.pdf"
    _aceitar(url)
    with sessao() as s:
        for numero in range(1, 6):
            s.add(_do_complementar(url, numero, f"Proposta {numero} do catálogo?"))
    for numero in range(1, 6):
        classificacoes.classificar(_k(f"{url}-{numero}"), "Direito Penal > " + IMPUTABILIDADE,
                                   classificacoes.PROCEDENCIA_DO_CATALOGO)

    antes = classificacoes.conferencia(evidencia_escolhida="complementar", so_amostra=True)
    amostra = [i.chave for i in antes.itens]
    assert len(amostra) == 2 and all(i.na_amostra for i in antes.itens)
    (resumo,) = antes.amostras
    assert (resumo.materia, resumo.propostas, resumo.tamanho, resumo.conferidas) == (
        "Direito Penal", 5, 2, 0)

    classificacoes.conferir(amostra[0])                                 # estava certa
    classificacoes.conferir(amostra[1], corrigir_para="Direito Penal")  # estava errada

    # A correcao vira "manual", mas guarda de onde veio: a amostra nao muda,
    # e o erro do catalogo aparece na conta.
    assert classificacoes.ERA_DO_CATALOGO in _linha(amostra[1]).trecho
    depois = classificacoes.conferencia(evidencia_escolhida="complementar", so_amostra=True)
    assert [i.chave for i in depois.itens] == amostra
    (resumo,) = depois.amostras
    assert (resumo.conferidas, resumo.corrigidas) == (2, 1)


def test_corrigir_proposta_que_nao_e_do_catalogo_nao_ganha_o_rastro(alvo):
    classificacoes.classificar(_k("2019-51"), "Direito Penal > " + IMPUTABILIDADE, "Claude Code")
    classificacoes.conferir(_k("2019-51"), corrigir_para="Direito Penal")
    assert _principal("2019-51").trecho == "corrigida na conferência"


def test_a_tela_do_complementar_volta_para_o_mesmo_recorte(alvo):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    url = "https://fepese.test/2024/A.pdf"
    _aceitar(url)
    with sessao() as s:
        s.add(_do_complementar(url, 1, "Proposta do catálogo?"))
    chave = _k(f"{url}-1")
    classificacoes.classificar(chave, "Direito Penal > " + IMPUTABILIDADE,
                               classificacoes.PROCEDENCIA_DO_CATALOGO)
    cliente = TestClient(app)

    texto = cliente.get("/analises/conferencia?evidencia=complementar&amostra=1").text
    assert "Proposta do catálogo?" in texto and "🟡 na amostra" in texto
    assert "Questão 51 de 2019" not in texto                     # o alvo nao entra
    assert "Proposta do catálogo?" not in cliente.get("/analises/conferencia").text

    resposta = cliente.post("/analises/conferencia", data={
        "chave": chave, "acao": "confirmar", "evidencia": "complementar", "amostra": "1"},
        follow_redirects=False)
    assert resposta.headers["location"] == (
        f"/analises/conferencia?evidencia=complementar&amostra=1#q-{chave}")
    assert _linha(chave).conferida_em is not None


def test_subassunto_parecido_com_um_que_ja_existe_e_recusado(alvo, tmp_path):
    """Auditoria de 04/10 (BUG-3): a classificacao do complementar criou
    "Formas de violencia domestica" ao lado de "... e familiar", e o mesmo
    conceito ficou em dois nos. Agora o nome parecido e recusado e aponta o
    no que ja existe - e nenhum no novo e criado."""
    lote, penal = _pedido("Direito Penal")
    _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [_boa("2019-q51")]}])

    resultado = _importar(tmp_path, lote, [{"id": penal["id"], "classificacoes": [
        _boa("2019-q52", subassunto="Menoridade penal", elemento="CP, art. 28",
             referencia="CP, art. 28")]}])

    assert resultado["gravadas"] == 0
    (recusa,) = resultado["recusas"]
    assert "parece o que já existe" in recusa and "Menoridade" in recusa
    with sessao() as s:
        assert s.scalar(select(Conteudo).where(Conteudo.nome == "Menoridade penal")) is None
