"""A origem de cada dado, e o selo dela (Etapa 7A).

A secao 20 do novo.md pede quatro origens - oficial, acervo, automatico e IA
- e pede que elas fiquem REGISTRADAS NOS DADOS, e nao so pintadas na tela.
Estes testes seguram:

  * o SELOS e um so, e cada selo e de uma das origens;
  * a frase da regra inviolavel 4 tem o texto exato e mora num lugar so;
  * todo servico que entrega numero ou texto com selo devolve a origem;
  * a questao diz, no proprio dado, se e da prova ou da IA.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from radar import complementar, fichas, foco, incidencia, leis, macetes, origem
from radar.cronograma import Nivel
from radar.db import sessao
from radar.models import Concurso, QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.origem import ACERVO, AUTOMATICO, CLASSIFICACAO, IA, OFICIAL, PLANO, PROVA, TENDENCIA
from radar.servico import (
    cartoes,
    compilado,
    desempenho_por_conteudo,
    erros,
    geradas,
    inicio,
    materias,
    metricas,
    previsao,
    simulado,
)

FONTE = Path(__file__).resolve().parent.parent / "src" / "radar"
AS_CINCO = {OFICIAL, ACERVO, AUTOMATICO, IA, PLANO}


# --- os selos ----------------------------------------------------------------

def test_cada_selo_e_de_uma_das_origens():
    for chave, s in origem.SELOS.items():
        assert s.origem in AS_CINCO, chave


def test_as_quatro_origens_tem_o_emoji_do_novo_md():
    emojis = {o: origem.SELOS[o].emoji for o in (OFICIAL, ACERVO, AUTOMATICO, IA)}
    assert emojis == {OFICIAL: "🟢", ACERVO: "🔵", AUTOMATICO: "🟡", IA: "🟣"}


def test_a_variacao_tem_a_cor_da_sua_origem():
    """A questao da prova e oficial como o edital; a classificacao e a
    tendencia sao automaticas como o desempenho."""
    assert origem.SELOS[PROVA].origem == OFICIAL
    assert origem.SELOS[CLASSIFICACAO].origem == AUTOMATICO
    assert origem.SELOS[TENDENCIA].origem == AUTOMATICO


# --- a frase da regra 4 --------------------------------------------------------

def test_a_frase_padrao_com_o_texto_exato():
    assert origem.FRASE_SEM_EVIDENCIA == "Não há evidência suficiente no acervo para afirmar isso."


def test_a_frase_padrao_e_a_mesma_constante_em_todo_lugar():
    """Uma copia escrita a mao podia divergir numa virgula; importada, nao."""
    assert incidencia.FRASE_SEM_EVIDENCIA is origem.FRASE_SEM_EVIDENCIA
    assert complementar.FRASE_SEM_EVIDENCIA is origem.FRASE_SEM_EVIDENCIA
    assert fichas.FRASE_SEM_EVIDENCIA is origem.FRASE_SEM_EVIDENCIA


def _arquivos_que_dizem(trecho: str) -> list[str]:
    return sorted(
        p.relative_to(FONTE).as_posix()
        for p in FONTE.rglob("*")
        if p.suffix in (".py", ".html")
        and trecho in p.read_text(encoding="utf-8").lower()
    )


def test_a_frase_padrao_mora_num_arquivo_so():
    assert _arquivos_que_dizem("evidência suficiente no acervo") == ["origem.py"]


def test_o_desempenho_com_pouca_resposta_diz_amostra_insuficiente():
    """Um rotulo so, o estado da decisao 6 - e nao "amostra pequena" numa tela
    e outro nome na seguinte."""
    assert _arquivos_que_dizem("amostra pequena") == []


# --- a origem nos servicos ------------------------------------------------------

#: (o que e, a origem que o tipo devolve, a esperada). O tipo de origem fixa
#: tem o atributo `origem`; o que junta partes de origens diferentes, `origens`.
ORIGEM_FIXA = [
    ("metricas.Numeros", metricas.Numeros.origem, AUTOMATICO),
    ("metricas.Evolucao", metricas.Evolucao.origem, AUTOMATICO),
    ("metricas.DesempenhoDaMateria", metricas.DesempenhoDaMateria("x").origem, AUTOMATICO),
    ("cronograma.Nivel", Nivel.origem, AUTOMATICO),
    ("inicio.Revisar", inicio.Revisar.origem, AUTOMATICO),
    ("erros.Contagem", erros.Contagem.origem, AUTOMATICO),
    ("desempenho_por_conteudo.Desempenho", desempenho_por_conteudo.Desempenho.origem, AUTOMATICO),
    ("desempenho_por_conteudo.LinhaDaTela", desempenho_por_conteudo.LinhaDaTela.origem, AUTOMATICO),
    ("macetes.FatiaDoCaderno", macetes.FatiaDoCaderno.origem, ACERVO),
    ("cartoes.Cartao", cartoes.Cartao.origem, ACERVO),
    ("cartoes.MaceteDoCartao", cartoes.MaceteDoCartao.origem, IA),
    ("cartoes.QuestaoRelacionada", cartoes.QuestaoRelacionada(QuestaoDeProva(), []).origem, PROVA),
    ("previsao.PrevisaoDeAbertura", previsao.PrevisaoDeAbertura.origem, TENDENCIA),
    ("previsao.Cobertura", previsao.Cobertura.origem, AUTOMATICO),
    ("materias.Projecao", materias.Projecao.origem, TENDENCIA),
    ("leis.Lei", leis.Lei.origem, OFICIAL),
    ("models.QuestaoDeProva", QuestaoDeProva.origem, PROVA),
    ("models.QuestaoGerada", QuestaoGerada.origem, IA),
]

ORIGENS_POR_PARTE = [
    ("metricas.Conta", metricas.Conta.origens,
     {"radar": AUTOMATICO, "anotado": AUTOMATICO, "treino_ia": IA, "total": AUTOMATICO}),
    ("foco.Painel", foco.Painel.origens,
     {"edital": OFICIAL, "provas": ACERVO, "meu_acerto": AUTOMATICO,
      "assunto": ACERVO, "estimativa": TENDENCIA}),
    ("macetes.Analise", macetes.Analise.origens,
     {"recorte": ACERVO, "assunto": CLASSIFICACAO, "comandos": ACERVO,
      "repetidas": ACERVO, "gabarito": TENDENCIA}),
    ("compilado.Plano", compilado.Plano.origens, {"questoes": PROVA, "quadro": OFICIAL}),
]


@pytest.mark.parametrize("nome, achada, esperada", ORIGEM_FIXA, ids=[n for n, _a, _e in ORIGEM_FIXA])
def test_todo_servico_de_numero_devolve_a_origem(nome, achada, esperada):
    assert achada in origem.SELOS, nome
    assert achada == esperada, nome


@pytest.mark.parametrize("nome, achadas, esperadas", ORIGENS_POR_PARTE,
                         ids=[n for n, _a, _e in ORIGENS_POR_PARTE])
def test_o_que_junta_origens_diz_a_de_cada_parte(nome, achadas, esperadas):
    assert set(achadas.values()) <= set(origem.SELOS), nome
    assert achadas == esperadas, nome


def test_cada_recorte_da_conta_tem_origem():
    """O recorte novo que alguem criar no metricas precisa dizer a origem."""
    assert set(metricas.ORIGEM_DO_RECORTE) == set(metricas.RECORTES)


def test_a_questao_da_revisao_diz_se_e_da_prova_ou_da_ia():
    real = simulado.ItemDeRevisao("?", "a", "b", "x", "y", False)
    da_ia = simulado.ItemDeRevisao("?", "a", "b", "x", "y", False, gerada=True)
    assert (real.origem, real.origem_da_resposta) == (PROVA, OFICIAL)
    assert (da_ia.origem, da_ia.origem_da_resposta) == (IA, IA)


def test_a_rodada_diz_se_e_da_prova_ou_da_ia():
    def rodada(gerada):
        return simulado.ResumoDaRodada(1, None, 10, 10, 7, ["Direito Penal"], gerada)
    assert rodada(False).origem == PROVA
    assert rodada(True).origem == IA


def test_o_salario_lido_do_anuncio_e_classificacao():
    assert Concurso(titulo="x", salario=6000.0, salario_manual=False).origem_do_salario == CLASSIFICACAO
    # Digitado por mim nao leva selo: a tela diz "anotado por mim".
    assert Concurso(titulo="x", salario=6000.0, salario_manual=True).origem_do_salario is None
    assert Concurso(titulo="x", salario=None).origem_do_salario is None


def _rodada_gerada():
    """Uma rodada de uma questao gerada, respondida certo."""
    with sessao() as s:
        s.add(QuestaoGerada(modo="variacao", materia="Direito Penal", enunciado="gerada?",
                            alternativas={"a": "x", "b": "y"}, resposta="a",
                            impressao="g1", modelo="teste"))
        s.add(Simulado(filtros={"geradas": True}))
        s.flush()
        questao = s.query(QuestaoGerada).one()
        rodada = s.query(Simulado).one()
        s.add(RespostaDeSimulado(simulado_id=rodada.id, questao_id=questao.id, gerada=True,
                                 ordem=1, escolhida="a", acertou=True,
                                 respondida_em=datetime(2026, 10, 1, 12, tzinfo=timezone.utc)))
        return rodada.id


def test_o_acerto_nas_geradas_leva_o_selo_da_ia(banco_temporario):
    """O mesmo tipo do acerto nas reais, com a origem dele: os dois nunca se
    somam, e a tela nunca pinta o das geradas de amarelo."""
    rodada = _rodada_gerada()
    linhas = metricas.desempenho_das_geradas()
    assert linhas and {d.origem for d in linhas} == {IA}
    assert metricas.resumo_do_simulado(rodada)["origem"] == IA


def test_o_resultado_da_rodada_real_e_conta_do_sistema(banco_temporario):
    with sessao() as s:
        s.add(Simulado(filtros={}))
        s.flush()
        rodada = s.query(Simulado).one().id
    assert metricas.resumo_do_simulado(rodada)["origem"] == AUTOMATICO


def test_o_custo_da_geracao_e_estimativa(banco_temporario):
    assert geradas.preparar(quantas=3)["origem_do_custo"] == TENDENCIA
