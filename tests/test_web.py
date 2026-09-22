"""A pagina web renderiza?

Erro em template Jinja so aparece quando a pagina e pedida de verdade - nao
no import. Como a web e a unica interface visual do projeto, vale um teste
que realmente monte o HTML.
"""
import pytest
from fastapi.testclient import TestClient

from radar.db import sessao
from radar.models import Concurso
from radar.web.app import app


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_pagina_abre_vazia(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "Radar de Concursos" in resposta.text
    assert "Nada coletado ainda" in resposta.text


def test_pagina_mostra_concurso(cliente):
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/ascurra",
                fonte="concursosnobrasil",
                titulo="Edital Prefeitura de Ascurra (SC) oferta salarios",
                uf="SC",
                situacao="edital_publicado",
                relevancia="nucleo",   # o padrao da pagina so mostra o que e perto
            )
        )

    texto = cliente.get("/").text
    assert "Ascurra" in texto
    assert "https://exemplo.test/ascurra" in texto   # o link original aparece
    # cada informacao vem com rotulo: "FEPESE" sozinho nao diz nada
    assert "Cidade:" in texto
    assert "Salario:" in texto
    assert "Banca:" in texto
    assert "Status:" in texto


def test_aba_estadual_sc(cliente):
    """"estadual" e jargao do banco; na tela vale o que eu entendo. A aba e
    propria porque concurso do estado nao e "perto" nem "longe"."""
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/sap",
                fonte="fepese",
                titulo="2019 - Secretaria de Estado da Administracao Prisional",
                uf="SC",
                tipo="concurso",
                relevancia="estadual",
                motivo_relevancia=(
                    "Orgao estadual de SC; polos de prova a confirmar no edital."
                ),
            )
        )

    inicio = cliente.get("/").text
    assert "Estadual SC" in inicio          # a aba, com a contagem

    texto = cliente.get("/?relevancia=estadual").text
    assert "Administracao Prisional" in texto
    assert "polos de prova a confirmar no edital" in texto


def test_filtro_por_uf(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="De SC",
                       uf="SC", relevancia="nucleo"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="De Sao Paulo",
                       uf="SP", relevancia="nucleo"))

    texto = cliente.get("/?uf=SC").text
    assert "De SC" in texto
    assert "De Sao Paulo" not in texto


def test_contagem_mostra_o_total_quando_filtra(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="De SC",
                       uf="SC", relevancia="nucleo"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="De SP",
                       uf="SP", relevancia="nucleo"))

    assert "1 de 2 concurso(s)" in cliente.get("/?uf=SC").text


def test_atalhos_mostram_a_contagem_de_cada_anel(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="Perto",
                       uf="SC", relevancia="nucleo"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="Longe 1",
                       uf="SP", relevancia="remoto"))
        s.add(Concurso(url="https://a.test/3", fonte="f", titulo="Longe 2",
                       uf="SP", relevancia="remoto"))

    texto = cliente.get("/").text
    assert "Perto de mim" in texto and "Longe" in texto
    assert 'href="/?relevancia=remoto"' in texto


def test_pagina_vazia_explica_em_vez_de_parecer_quebrada(cliente):
    """O caso real: tudo coletado esta longe. A pagina precisa dizer isso."""
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="Capinzal",
                       uf="SC", relevancia="remoto"))

    texto = cliente.get("/").text
    assert "Nenhum concurso perto de voce agora" in texto
    assert "Ver todos" in texto          # oferece a saida
    assert "Nada coletado ainda" not in texto   # nao confunde com banco vazio


def test_noticia_nao_aparece(cliente):
    """O "Bolsa Familia" que veio no feed nao pode poluir a lista."""
    with sessao() as s:
        s.add(Concurso(url="https://a.test/bolsa", fonte="f", tipo="noticia",
                       titulo="Bolsa Familia passa a ter novo valor",
                       relevancia="nucleo"))

    assert "Bolsa Familia" not in cliente.get("/?todos=true").text


def test_motivo_da_classificacao_aparece_na_tela(cliente):
    """Preciso poder auditar por que o radar decidiu o que decidiu."""
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="Palhoca",
                       uf="SC", relevancia="nucleo",
                       motivo_relevancia="Palhoca (SC) esta no anel nucleo."))

    assert "esta no anel nucleo" in cliente.get("/").text


def test_os_grids_declaram_coluna_que_encolhe(cliente):
    """Grid sem coluna declarada usa uma implicita de tamanho `auto`, que pode
    chegar a max-content e furar a largura da tela com um titulo longo.

    Isto e prevencao, nao conserto: o corte que eu achei ter visto no celular
    era artefato do print (o Chrome no Windows tem largura minima de janela de
    500px, entao um screenshot pedido com 400px e so um recorte). Declarar
    minmax(0,1fr) continua sendo o certo e custa nada."""
    texto = cliente.get("/").text
    assert texto.count("grid-template-columns:minmax(0,1fr)") >= 3
