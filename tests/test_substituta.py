"""Prova substituta: qual prova do acervo mais se parece com o cargo que quero.

O problema e concreto: Guarda Municipal e Policia Penal, que sao os cargos que
eu mais quero, nao tem uma prova sequer entre os 134 cargos do acervo.

A regra que vale para o arquivo inteiro: a lista pode ser curta ou vazia, mas
nunca pode fingir equivalencia. "Guarda Patrimonial" divide uma palavra com
"Guarda Municipal" e e outra profissao.
"""
import pytest

from radar import servico, substituta
from radar.db import sessao
from radar.models import QuestaoDeProva


def _parecida(cargo: str, **mudancas) -> substituta.Parecida:
    base = dict(cargo=cargo, banca="FEPESE", municipio="Palhoca", ano=2024,
                questoes=40)
    base.update(mudancas)
    return substituta.Parecida(**base)


def _questao(numero: int, **mudancas) -> QuestaoDeProva:
    base = dict(
        prova_url=f"https://x.test/p{numero}.pdf",
        banca="FEPESE",
        ano=2024,
        municipio="Palhoca",
        cargo="Guarda Patrimonial",
        numero=numero,
        materia="Lingua Portuguesa",
        enunciado=f"Questao {numero}?",
        alternativas={"a": "um", "b": "dois"},
        resposta="a",
        impressao=f"i{numero}",
    )
    base.update(mudancas)
    return QuestaoDeProva(**base)


def _semear(*questoes):
    with sessao() as s:
        for q in questoes:
            s.add(q)


# --- as palavras que dizem o que o cargo e ----------------------------------

def test_palavra_vazia_nao_conta():
    """Sem tirar estas, "Agente Administrativo" e "Agente de Servicos" pareceriam
    parentes por causa de "Agente" e "de"."""
    assert substituta.palavras_do_cargo("Agente de Servicos") == {"agente", "servicos"}


def test_numeral_romano_do_cargo_nao_conta():
    """Motorista III e Motorista sao o mesmo cargo em niveis diferentes."""
    assert substituta.palavras_do_cargo("Motorista III") == {"motorista"}


def test_acento_nao_atrapalha():
    assert "psicologo" in substituta.palavras_do_cargo("Psicólogo")


# --- a ordenacao ------------------------------------------------------------

def test_cargo_igual_vem_primeiro():
    achadas = substituta.ordenar(
        [_parecida("Orientador Social"), _parecida("Assistente Social")],
        cargo="Assistente Social", banca="FEPESE",
    )

    assert achadas[0].cargo == "Assistente Social"


def test_o_cargo_pesa_mais_que_a_banca():
    """Prova de outro cargo da minha banca ensina menos que prova do meu cargo
    em banca diferente - o que eu estudo e o conteudo."""
    de_outra_banca = _parecida("Assistente Social", banca="IESES")
    da_minha_banca = _parecida("Orientador Social", banca="FEPESE")

    achadas = substituta.ordenar(
        [da_minha_banca, de_outra_banca], cargo="Assistente Social", banca="FEPESE"
    )

    assert achadas[0].banca == "IESES"


def test_so_a_banca_em_comum_nao_entra_na_lista():
    """Sem esta regra, procurar "Policia Penal" devolvia Merendeira e Professor
    de Ensino Religioso, so por serem da mesma banca."""
    achadas = substituta.ordenar(
        [_parecida("Merendeira"), _parecida("Professor de Musica")],
        cargo="Policia Penal", banca="FEPESE",
    )

    assert achadas == []


def test_uma_palavra_em_comum_entra_com_o_motivo_declarado():
    """Guarda Patrimonial nao e Guarda Municipal. Entra na lista, mas o motivo
    diz exatamente o que ele e."""
    achadas = substituta.ordenar(
        [_parecida("Guarda Patrimonial")], cargo="Guarda Municipal", banca="FEPESE"
    )

    assert len(achadas) == 1
    assert "1 palavra(s) em comum" in achadas[0].motivo
    assert not achadas[0].exata


def test_cargo_identico_e_marcado_como_exato():
    achadas = substituta.ordenar([_parecida("Motorista")], cargo="Motorista")

    assert achadas[0].exata


def test_o_desempate_e_pelo_tamanho_da_prova():
    achadas = substituta.ordenar(
        [_parecida("Motorista", questoes=20), _parecida("Motorista", questoes=40)],
        cargo="Motorista",
    )

    assert achadas[0].questoes == 40


def test_mesmo_municipio_desempata():
    de_longe = _parecida("Motorista", municipio="Chapeco")
    de_perto = _parecida("Motorista", municipio="Palhoca")

    achadas = substituta.ordenar(
        [de_longe, de_perto], cargo="Motorista", municipio="Palhoca"
    )

    assert achadas[0].municipio == "Palhoca"


def test_todo_achado_carrega_o_motivo():
    achadas = substituta.ordenar([_parecida("Motorista")], cargo="Motorista",
                                 banca="FEPESE")

    assert achadas[0].motivo


# --- quando nao ha nada -----------------------------------------------------

def test_o_recado_diz_o_que_serve_no_lugar():
    """A resposta honesta e que as materias universais sao o que sobra - e elas
    valem 20 das 30 questoes de uma prova da IESES."""
    recado = substituta.explicar_ausencia("Policia Penal", ["Lingua Portuguesa"])

    assert "Policia Penal" in recado
    assert "Lingua Portuguesa" in recado


def test_recado_sem_materia_nenhuma_nao_quebra():
    assert substituta.explicar_ausencia("Policia Penal", [])


# --- pelo servico -----------------------------------------------------------

def test_busca_no_acervo_de_verdade(banco_temporario):
    _semear(_questao(1), _questao(2, cargo="Psicologo", impressao="b"))

    achadas = servico.provas_parecidas("Guarda Municipal")

    assert [p.cargo for p in achadas] == ["Guarda Patrimonial"]


def test_conta_quantas_questoes_cada_prova_tem(banco_temporario):
    _semear(*[_questao(n, impressao=f"i{n}") for n in range(1, 4)])

    assert servico.provas_parecidas("Guarda Municipal")[0].questoes == 3


def test_cargo_em_branco_devolve_lista_vazia(banco_temporario):
    _semear(_questao(1))

    assert servico.provas_parecidas("   ") == []


def test_o_servico_da_o_recado_quando_nao_acha(banco_temporario):
    _semear(_questao(1, cargo="Psicologo"))

    achadas = servico.provas_parecidas("Policia Penal")

    assert achadas == []
    assert "Policia Penal" in servico.recado_sobre_o_cargo("Policia Penal", achadas)


def test_achando_prova_nao_ha_recado(banco_temporario):
    _semear(_questao(1))

    achadas = servico.provas_parecidas("Guarda Municipal")

    assert servico.recado_sobre_o_cargo("Guarda Municipal", achadas) == ""


# --- na tela ----------------------------------------------------------------

@pytest.fixture
def cliente(banco_temporario):
    from fastapi.testclient import TestClient
    from radar.web.app import app
    return TestClient(app)


def test_a_tela_lista_as_parecidas(cliente):
    _semear(_questao(1))

    texto = cliente.get("/macetes?banca=FEPESE&cargo=Guarda+Municipal").text

    assert "Guarda Patrimonial" in texto
    assert "palavra(s) em comum" in texto


def test_a_tela_admite_quando_nao_ha_prova_do_cargo(cliente):
    """Melhor uma tela que admite nao ter nada que oito linhas de ruido."""
    _semear(_questao(1, cargo="Psicologo"))

    texto = cliente.get("/macetes?banca=FEPESE&cargo=Policia+Penal").text

    assert "Nenhuma prova de Policia Penal" in texto


def test_sem_cargo_pedido_a_secao_nao_aparece(cliente):
    _semear(_questao(1))

    assert "no acervo</h2>" not in cliente.get("/macetes?banca=FEPESE").text
