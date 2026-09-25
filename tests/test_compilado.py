"""O simulado compilado e o caderno "so meus erros".

O compilado le os pesos do quadro do edital - aqui, o quadro REAL de 2019 em
fixture, pelo mesmo leitor do Meu foco. Nenhum peso e escrito no teste nem
no codigo: se o quadro mudar, a distribuicao muda junto.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import foco, servico
from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado
from radar.servico import compilado
from radar.web.app import app

from tests.test_foco import _concurso, com_quadro_do_edital  # noqa: F401

CADERNO = "https://fepese.test/ap2019.pdf"


@pytest.fixture
def quadro_real(com_quadro_do_edital, monkeypatch):
    """O quadro de 2019 lido do texto real, sem precisar do PDF."""
    monkeypatch.setattr(
        foco, "quadro_do_edital",
        lambda: (foco.EditalLido(com_quadro_do_edital, 100, 2019, None),
                 "2019_SAP_Edital_1.pdf"),
    )
    return {m.nome: m.questoes for m in com_quadro_do_edital}


def _semear(por_materia: dict[str, int]):
    """Questoes reais do meu cargo, quantas por materia."""
    with sessao() as s:
        s.add(_concurso())
        numero = 0
        for materia, quantas in por_materia.items():
            for _ in range(quantas):
                numero += 1
                s.add(QuestaoDeProva(
                    prova_url=CADERNO, banca="FEPESE", concurso_url=_concurso().url,
                    ano=2019, cargo="Agente Penitenciário", numero=numero,
                    materia=materia, enunciado=f"{materia} {numero}?",
                    alternativas={"a": "x", "b": "y"}, resposta="a",
                    impressao=f"q{numero}",
                ))


# --- a distribuicao ---------------------------------------------------------

def test_distribuir_soma_o_tamanho_e_segue_o_peso(quadro_real):
    for tamanho in compilado.TAMANHOS:
        partes = compilado.distribuir(quadro_real, tamanho)
        assert sum(partes.values()) == tamanho


def test_com_100_questoes_e_o_proprio_quadro(quadro_real):
    """100 e o tamanho da prova de 2019: a distribuicao e o quadro."""
    assert compilado.distribuir(quadro_real, 100) == quadro_real


def test_com_40_as_de_15_levam_6(quadro_real):
    partes = compilado.distribuir(quadro_real, 40)
    assert partes["Língua Portuguesa"] == 6 and partes["Direitos Humanos"] == 6
    assert partes["Lei de Execução Penal"] == 4


def test_os_pesos_vem_do_edital_e_nao_do_codigo(banco_temporario, monkeypatch):
    """Troque o quadro e a distribuicao troca - prova de que nada esta fixo."""
    from radar.edital_materias import MateriaDoEdital

    outro = [MateriaDoEdital("Direito Penal", 30), MateriaDoEdital("Língua Portuguesa", 10)]
    monkeypatch.setattr(foco, "quadro_do_edital",
                        lambda: (foco.EditalLido(outro, 40, 2030, None), "novo.pdf"))
    plano = compilado.planejar(40)
    assert {l.materia: l.pedidas for l in plano.linhas} == {
        "Direito Penal": 30, "Língua Portuguesa": 10,
    }
    assert plano.arquivo_do_edital == "novo.pdf"


def test_sem_quadro_nao_ha_compilado(banco_temporario, monkeypatch):
    monkeypatch.setattr(foco, "quadro_do_edital", lambda: (foco.EditalLido(), None))
    assert compilado.planejar(40) is None
    assert compilado.criar_simulado_compilado(40) is None


def test_desmarcar_materia_redistribui_entre_as_outras(banco_temporario, quadro_real):
    plano = compilado.planejar(40, ["Língua Portuguesa", "Direito Penal"])
    assert {l.materia: l.pedidas for l in plano.linhas} == {
        "Língua Portuguesa": 30, "Direito Penal": 10,     # 15:5 do edital
    }


def test_2013_e_2019_escrevem_processual_diferente_e_e_a_mesma():
    assert compilado.mesma_materia("Direito Processual Penal", "Direito Processo Penal")
    assert not compilado.mesma_materia("Legislação Estadual", "Legislação Especial")


# --- a rodada ---------------------------------------------------------------

def test_a_rodada_segue_o_plano_e_diz_o_que_faltou(banco_temporario, quadro_real):
    """Direito Penal pede 2 em 40 e tem 1: entrega 1 e conta 1 faltando, sem
    completar com outra materia."""
    _semear({"Língua Portuguesa": 10, "Direito Penal": 1})

    simulado, plano = compilado.criar_simulado_compilado(
        40, ["Língua Portuguesa", "Direito Penal"]
    )

    por = {l.materia: l for l in plano.linhas}
    assert por["Língua Portuguesa"].pedidas == 30 and por["Língua Portuguesa"].entregues == 10
    assert por["Direito Penal"].entregues == 1
    assert plano.faltaram == 20 + 9
    assert simulado.filtros["compilado"] == 40
    assert simulado.filtros["edital"] == "2019_SAP_Edital_1.pdf"


def test_o_compilado_nunca_tem_questao_gerada(banco_temporario, quadro_real):
    _semear({"Língua Portuguesa": 5})
    with sessao() as s:
        s.add(QuestaoGerada(modo="variacao", materia="Língua Portuguesa",
                            enunciado="gerada?", alternativas={"a": "x"},
                            resposta="a", impressao="g1", modelo="teste"))

    simulado, _ = compilado.criar_simulado_compilado(40, ["Língua Portuguesa"])

    with sessao() as s:
        linhas = list(s.scalars(select(RespostaDeSimulado)
                                .where(RespostaDeSimulado.simulado_id == simulado.id)))
    assert linhas and not any(r.gerada for r in linhas)


# --- so meus erros ----------------------------------------------------------

def test_meus_erros_sem_anuladas_e_sem_geradas(banco_temporario, quadro_real):
    """Questao que a banca anulou depois de eu errar sai do caderno; e errar
    uma gerada nao poe nada no caderno de questoes reais."""
    _semear({"Direito Penal": 2})
    rodada = servico.criar_simulado(quantidade=2, materia="Direito Penal")
    for _ in range(2):
        _r, q = servico.questao_atual(rodada.id)
        servico.responder(rodada.id, q.id, "b")
    assert len(servico.questoes_erradas()) == 2

    with sessao() as s:
        uma = s.scalar(select(QuestaoDeProva).limit(1))
        uma.anulada = True
    assert len(servico.questoes_erradas()) == 1


# --- a tela -----------------------------------------------------------------

def test_a_tela_mostra_os_dois_cadernos_e_o_selo(banco_temporario, quadro_real):
    _semear({"Língua Portuguesa": 3})
    texto = TestClient(app).get("/simulado").text

    assert "Só meus erros" in texto
    assert "Simulado compilado" in texto
    assert "só questões reais" in texto
    assert "2019_SAP_Edital_1.pdf" in texto
    for n in compilado.TAMANHOS:
        assert f'value="{n}"' in texto


def test_o_botao_monta_e_a_questao_diz_que_e_compilado(banco_temporario, quadro_real):
    _semear({"Língua Portuguesa": 3})
    cliente = TestClient(app)

    resposta = cliente.post("/simulado/compilado",
                            data={"tamanho": "40", "materias": ["Língua Portuguesa"]},
                            follow_redirects=False)

    assert resposta.status_code == 303
    texto = cliente.get(resposta.headers["location"]).text
    assert "Compilado de 40 pelo quadro do edital 2019" in texto
    assert "faltaram 37" in texto
    assert "Só questões reais" in texto
