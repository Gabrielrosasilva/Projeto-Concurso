"""A auditoria das provas do alvo: quadro do edital, gabarito e anuladas.

Os quadros sao TEXTO REAL, tirado dos editais de 2013 e 2016 com o mesmo
leitor de PDF do radar - e e por isso que eles tem o "Direito P rocessual" e o
cabecalho de pagina no meio da tabela. Sao exatamente as armadilhas que o
leitor precisa atravessar.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from radar import auditoria
from radar.gabarito import Grade

FIXTURES = Path(__file__).parent / "fixtures" / "auditoria"


def _texto(nome):
    return (FIXTURES / nome).read_text(encoding="utf-8")


def _pares(quadro):
    return [(m.nome, m.questoes) for m in quadro.materias]


# --- o quadro do edital -----------------------------------------------------

def test_edital_de_2013_tem_um_quadro_por_cargo():
    """Dois quadros de 70, e so o nome do cargo antes de cada um os separa."""
    quadros = auditoria.ler_quadros(_texto("quadro_2013.txt"), 70)
    assert len(quadros) == 2

    ap = auditoria.quadro_do_cargo(quadros, "Agente Penitenciário")
    assert _pares(ap) == [
        ("Língua Portuguesa", 10), ("Noções de Informática", 10),
        ("Direitos Humanos", 10), ("Direito Constitucional", 10),
        ("Direito Administrativo", 6), ("Direito Penal", 8),
        ("Direito Processual Penal", 6), ("Legislação Estadual", 10),
    ]

    as_ = auditoria.quadro_do_cargo(
        quadros, "Agente de Segurança Socioeducativo (AS)"
    )
    assert ("Direito Penal", 2) in _pares(as_)
    # O cabecalho de pagina caiu no meio do quadro e nao grudou no nome.
    assert ("Direito Administrativo", 6) in _pares(as_)


def test_edital_de_2016_sem_linha_de_total():
    """O quadro de 2016 nao escreve o TOTAL: a conferencia e o caderno."""
    (quadro,) = auditoria.ler_quadros(_texto("quadro_2016.txt"), 70)

    nomes = [nome for nome, _ in _pares(quadro)]
    assert "Legislação Estadual" in nomes       # sem "ESTADO DE SANTA CATARINA"
    assert "Língua Portuguesa" in nomes         # sem "Conhecimentos gerais"
    assert quadro.total == 70


def test_quadro_que_nao_fecha_e_descartado():
    """Nunca chutar: 70 questoes no edital e 71 no caderno nao e um quadro."""
    assert auditoria.ler_quadros(_texto("quadro_2016.txt"), 71) == []


def test_total_escrito_diferente_da_soma_e_descartado():
    texto = (
        "N° DE QUESTÕES VALOR DA QUESTÃO TOTAL\n"
        "Língua Portuguesa 10 0,10 1,00\n"
        "Direito Penal 10 0,10 1,00\n"
        "TOTAL 30 3,00\n"
    )
    assert auditoria.ler_quadros(texto, 20) == []


# --- o pareamento edital x caderno ------------------------------------------

def _materia(nome, questoes):
    return SimpleNamespace(nome=nome, questoes=questoes)


def test_pareia_pelo_nome_e_nao_pela_ordem():
    """Em 2016 o caderno troca a ordem de duas materias. Pela posicao, isso
    viraria duas contagens erradas que estao certas."""
    edital = [_materia("Direito Processual Penal", 2),
              _materia("Legislação Estadual", 10)]
    caderno = [["Legislação Estadual", 10], ["Direito Processo Penal", 2]]

    pares = auditoria._parear(edital, caderno)

    assert [(m.nome, b[0]) for m, b in pares] == [
        ("Direito Processual Penal", "Direito Processo Penal"),
        ("Legislação Estadual", "Legislação Estadual"),
    ]


def test_estadual_nao_casa_com_especial():
    """Os dois nomes sao parecidos e sao materias diferentes."""
    pares = auditoria._parear(
        [_materia("Legislação Estadual", 10)], [["Legislação Especial", 10]]
    )
    assert pares == [(pares[0][0], None), (None, ["Legislação Especial", 10])]


# --- o gabarito -------------------------------------------------------------

def _questao(numero, resposta, anulada=False):
    return SimpleNamespace(numero=numero, resposta=resposta, anulada=anulada,
                           materia="Direito Penal")


@pytest.fixture
def pdfs(monkeypatch):
    """Os PDFs de gabarito viram grades prontas; o caminho sempre existe."""
    grades = {}
    monkeypatch.setattr(auditoria, "_caminho", lambda r: r["arquivo"])
    monkeypatch.setattr(auditoria.gabarito, "ler_grades_do_pdf",
                        lambda caminho: grades[caminho])
    return grades


def test_vale_o_ultimo_definitivo_e_a_divergencia_aparece(pdfs):
    pdfs["def.pdf"] = (Grade(sigla="AP", respostas={1: "a", 2: "b", 3: "c"}),)
    pdfs["retif.pdf"] = (
        Grade(sigla="AP", respostas={1: "a", 3: "d"}, anuladas={2}),
    )
    pdfs["prov.pdf"] = (Grade(sigla="AP", respostas={1: "a", 2: "b", 3: "c"}),)
    # O banco ficou com o definitivo velho: a retificacao nao entrou.
    questoes = [_questao(1, "a"), _questao(2, "b"), _questao(3, "c")]
    prova = auditoria.ProvaAuditada(
        prova_url="x", ano=2019, cargo="Agente", reforco=False, questoes=3,
    )

    auditoria._auditar_gabarito(
        prova, {"arquivo": "AP.pdf"},
        [{"arquivo": "retif.pdf", "publicado_em": "2020-01-23"},
         {"arquivo": "def.pdf", "publicado_em": "2019-12-13"}],
        [{"arquivo": "prov.pdf"}],
        questoes,
    )

    assert prova.gabarito_que_vale == "retif.pdf"
    assert prova.anuladas_oficiais == [2]
    assert prova.divergencias == [(2, "b", "anulada"), (3, "c", "d")]
    assert prova.trocadas_pelo_definitivo == [3]


# --- o relatorio ------------------------------------------------------------

def _prova(**campos):
    base = dict(prova_url="x", ano=2019, cargo="Agente Penitenciário",
                reforco=False, questoes=100, edital_lido="edital.pdf",
                gabarito_que_vale="def.pdf", anuladas_no_banco=[11, 22])
    base.update(campos)
    return auditoria.ProvaAuditada(**base)


def test_relatorio_diz_onde_nao_bate():
    provas = [_prova(divergencias=[(33, "c", "anulada")])]
    texto = auditoria.relatorio(provas)
    assert "questao 33: banco diz c, definitivo diz anulada" in texto


def test_reforco_nunca_entra_na_soma_do_alvo():
    provas = [_prova(), _prova(ano=2016, cargo="Agente Socioeducativo",
                                reforco=True, questoes=70)]
    texto = auditoria.relatorio(provas)
    assert "Provas do alvo: 1, com 98 questoes validas" in texto
    assert "REFORCO" in texto
