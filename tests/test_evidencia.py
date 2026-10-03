"""A evidencia de cada prova: alvo, complementar ou fora (Etapa 2).

Uma regra so, no `servico.evidencia`, no lugar das duas de antes (a do Meu
foco, cargo E estado; a do simulado, so o cargo). O que estes testes seguram:
2013 e 2019 sao alvo, 2016 e complementar, a IESES e fora - e adicionar uma
prova complementar nao muda NENHUM numero do alvo (secao 4 do pedido).
"""
from sqlalchemy import select

from radar import foco
from radar.db import sessao
from radar.models import QuestaoDeProva
from radar.servico import conteudos, evidencia, simulado

from tests.test_foco import _concurso, _questao

PARANA = "https://concursosnobrasil.com/policia-penal-pr-2026"


def test_a_regra_de_cada_prova():
    assert evidencia.da_prova("Agente Penitenciário", "FEPESE", "SC") == "alvo"
    assert evidencia.da_prova("Agente Penitenciário - Feminino (AP)", "FEPESE", "SC") == "alvo"
    # O mesmo cargo em outro estado nao e o meu concurso.
    assert evidencia.da_prova("Policial Penal", "FEPESE", "PR") == "complementar"
    # Sem o concurso nao ha estado provado: nao vira alvo por palpite.
    assert evidencia.da_prova("Agente Penitenciário", "FEPESE", None) == "complementar"
    assert evidencia.da_prova("Agente de Segurança Socioeducativo (AS)", "FEPESE", "SC") == "complementar"
    assert evidencia.da_prova("Professor de Matemática", "FEPESE", "SC") == "complementar"
    assert evidencia.da_prova("Agente Penitenciário", "IESES", "PR") == "fora"
    assert evidencia.da_prova("Agente Administrativo", None, None) == "fora"


def _acervo(s):
    """2013 e 2019 do alvo, o Socioeducativo 2016 e uma prova da IESES."""
    s.add(_concurso())
    for n in range(1, 4):
        s.add(_questao(n, "Agente Penitenciário", 2019, "Direito Penal"))
        s.add(_questao(n, "Agente Penitenciário", 2013, "Direito Penal"))
        s.add(_questao(n, "Agente de Segurança Socioeducativo (AS)", 2016, "Direito Penal"))
    ieses = _questao(9, "Agente Penitenciário", 2020, "Direito Penal", concurso_url=None)
    ieses.banca, ieses.prova_url = "IESES", "https://ieses.test/2020.pdf"
    s.add(ieses)


def test_atualizar_grava_a_coluna(banco_temporario):
    with sessao() as s:
        _acervo(s)

    contagem = evidencia.atualizar()

    assert contagem == {"alvo": 6, "complementar": 3, "fora": 1}
    with sessao() as s:
        por_ano = dict(s.execute(select(QuestaoDeProva.ano, QuestaoDeProva.evidencia)
                                 .distinct()).all())
    assert por_ano == {2013: "alvo", 2019: "alvo", 2016: "complementar", 2020: "fora"}


def test_as_duas_regras_antigas_dao_o_mesmo_que_a_nova(banco_temporario):
    from tests.test_treino_do_alvo import _aceitar

    with sessao() as s:
        _acervo(s)
    evidencia.atualizar()
    with sessao() as s:
        # O treino so completa com prova aceita na Etapa 3B (decisao 75).
        _aceitar(s.scalars(select(QuestaoDeProva)
                           .where(QuestaoDeProva.ano == 2016)).all())

    with sessao() as s:
        do_foco = foco._provas_do_alvo(s)
        proprias, da_banca = simulado._questoes_para_o_alvo(s)
        da_coluna = set(s.scalars(select(QuestaoDeProva.prova_url)
                                  .where(QuestaoDeProva.evidencia == "alvo")))
    assert do_foco == da_coluna == {q.prova_url for q in proprias}
    assert len(proprias) == 6
    # A "da banca" do simulado e o complementar aceito nas mesmas materias.
    assert {q.ano for q in da_banca} == {2016}


def _numeros_do_alvo():
    """Tudo o que se conta do alvo: incidencia, questoes do treino, pendentes."""
    evidencia.atualizar()
    with sessao() as s:
        provas = foco._provas_do_alvo(s)
        incidencia = foco._incidencia_do_cargo(s, provas)
        proprias, _ = simulado._questoes_para_o_alvo(s)
    return (provas, incidencia, sorted(q.id for q in proprias),
            conteudos.pendentes().por_evidencia.get("alvo"))


def test_adicionar_prova_complementar_nao_muda_nenhum_numero_do_alvo(banco_temporario):
    with sessao() as s:
        _acervo(s)
    antes = _numeros_do_alvo()

    with sessao() as s:
        # Uma prova FEPESE nova, nas MESMAS materias, e ate do mesmo cargo -
        # mas do Parana. Ela engorda o complementar e mais nada.
        s.add(_concurso(url=PARANA, titulo="Concurso Policia Penal PR", uf="PR",
                        alvo=None))
        for n in range(1, 11):
            outra = _questao(n, "Policial Penal", 2024, "Direito Penal",
                             concurso_url=PARANA)
            outra.prova_url = "https://fepese.test/pr-2024.pdf"
            s.add(outra)

    assert _numeros_do_alvo() == antes
    assert conteudos.pendentes().por_evidencia["complementar"] == 13
