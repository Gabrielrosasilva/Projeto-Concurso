"""Minhas matérias: o progresso por materia do edital (etapa E4).

A conta e do `servico.materias`, e e nele que estes testes batem. As regras sao
as da E2: volume e acerto somam faixas + extras + radar, a barra da meta usa so
questao SEM CONSULTA, e questao de IA aparece a parte e em acerto nenhum.

O recorte e o CICLO do config/cronograma.yml, e o relogio fica parado: o ciclo
de verdade comeca depois do dia em que isto foi escrito.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from radar import cronograma, servico
from radar.db import sessao
from radar.models import QuestaoDeProva, QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import materias as tela
from radar.util import fuso_local
from radar.web.app import app

SEG = date(2026, 9, 28)          # o primeiro dia do Ciclo 1
HOJE = date(2026, 10, 20)


@pytest.fixture
def plano():
    return cronograma.carregar()


@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    monkeypatch.setattr(
        diario, "agora_local",
        lambda: datetime(2026, 10, 20, 20, 0, tzinfo=fuso_local()),
    )
    return TestClient(app)


def _cartao(cartoes, nome):
    return next(c for c in cartoes if c.nome == nome)


def _montar(plano, hoje=HOJE):
    return tela.montar(plano, hoje=hoje)


def _faixa_de(plano, data, materia):
    """A posicao da primeira faixa de questoes daquela materia, naquele dia."""
    nivel = diario.nivel_do_dia(plano, data)
    montado = cronograma.montar_dia(plano, data, nivel.efetivo)
    for bloco in ("manha", "noite", "pos22"):
        for indice, faixa in enumerate(getattr(montado, bloco)):
            if faixa.materia == materia and cronograma.tem_acerto(faixa):
                return bloco, indice, faixa
    raise AssertionError(f"{data} nao tem faixa de questoes de {materia}")


def _anotar(plano, data, materia, questoes, acertos, consulta=False):
    bloco, indice, faixa = _faixa_de(plano, data, materia)
    diario.anotar_faixa(data, bloco, indice, faixa.titulo, questoes=questoes,
                        acertos=acertos, consulta=consulta, plano=plano,
                        hoje=date(2026, 11, 7))
    return faixa


_marcas = iter(range(1, 10_000))


def _responder(materia, acertou, quando, gerada=False, assunto=None):
    """Uma questao respondida DENTRO do radar, na materia dada."""
    marca = next(_marcas)
    with sessao() as s:
        if gerada:
            questao = QuestaoGerada(
                enunciado="?", alternativas={"a": "x"}, resposta="a",
                materia=materia, assunto=assunto, modo="treino",
                modelo="teste", impressao=f"ia{marca}",
            )
        else:
            questao = QuestaoDeProva(
                prova_url="http://exemplo.test/prova.pdf", numero=marca,
                enunciado="?", alternativas={"a": "x"}, resposta="a",
                materia=materia, assunto=assunto, impressao=f"q{marca}",
            )
        s.add(questao)
        s.flush()
        simulado = Simulado(filtros={})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=simulado.id, questao_id=questao.id, gerada=gerada,
            ordem=1, escolhida="a", acertou=acertou, respondida_em=quando,
        ))


def _em(dia, hora=21):
    return datetime(dia.year, dia.month, dia.day, hora, 0, tzinfo=fuso_local())


# --- os cartoes ----------------------------------------------------------------

def test_um_cartao_por_materia_na_ordem_do_peso(banco_temporario, plano):
    cartoes, _ = _montar(plano)
    assert len(cartoes) == len(plano.materias) == 11
    pesos = [c.questoes_na_prova for c in cartoes]
    assert pesos == sorted(pesos, reverse=True)
    assert cartoes[0].questoes_na_prova == 15


def test_materia_nunca_estudada_diz_em_que_ciclo_entra(banco_temporario, plano):
    cartoes, _ = _montar(plano)
    sociologia = _cartao(cartoes, "Sociologia Aplicada")
    assert sociologia.nunca_estudei is True
    assert sociologia.ciclo_de_entrada == "Ciclo 2"
    # A de Direito Penal entra no Ciclo 1: ela tem faixa no plano.
    assert _cartao(cartoes, "Direito Penal").ciclo_de_entrada == "Ciclo 1"


def test_as_questoes_somam_faixas_extras_e_radar(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 15, 11)
    servico.extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                         minutos=30, questoes=10, acertos=8, onde="qconcursos",
                         plano=plano, hoje=date(2026, 11, 7))
    _responder("Direito Penal", True, _em(SEG))
    _responder("Direito Penal", False, _em(SEG))

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.geral.questoes == 27
    assert penal.geral.acertos == 20
    assert penal.nunca_estudei is False


def test_a_divisao_radar_e_anotado(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 10, 5)      # anotado: 50%
    _responder("Direito Penal", True, _em(SEG))      # radar: 100%

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.anotado.porcentagem == 50
    assert penal.radar.porcentagem == 100
    assert penal.geral.porcentagem == 55             # 6 de 11


def test_a_questao_de_ia_fica_fora_do_acerto(banco_temporario, plano):
    _responder("Direito Penal", True, _em(SEG), gerada=True)
    _responder("Direito Penal", False, _em(SEG))

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.geral.ia == 1                       # volume, no total
    assert penal.radar.medidas == 1
    assert penal.geral.porcentagem == 0              # so a real mede


# --- a barra contra a meta ------------------------------------------------------

def test_a_barra_usa_so_o_que_foi_sem_consulta(banco_temporario, plano):
    # Duas faixas de Penal no mesmo dia: a aprendizagem (com consulta) e uma
    # segunda anotacao sem consulta, pelo extra.
    _anotar(plano, SEG, "Direito Penal", 20, 20, consulta=True)
    servico.extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                         minutos=30, questoes=20, acertos=12, onde="qconcursos",
                         plano=plano, hoje=date(2026, 11, 7))

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.geral.porcentagem == 80             # 32 de 40
    assert penal.sem_consulta.porcentagem == 60      # 12 de 20
    assert penal.meta_em_porcentagem == 80           # meta 4 de 5
    assert penal.na_meta is False


def test_bater_a_meta_com_amostra_suficiente(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 20, 18)     # 90%, 20 sem consulta

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.amostra_pequena is False
    assert penal.na_meta is True


def test_amostra_pequena_nao_bate_meta_nenhuma(banco_temporario, plano):
    """19 questoes com 100% nao provam nada: o aviso aparece e a meta nao."""
    _anotar(plano, SEG, "Direito Penal", 19, 19)

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.sem_consulta.medidas == 19
    assert penal.amostra_pequena is True
    assert penal.na_meta is False


# --- a projecao -----------------------------------------------------------------

def test_a_projecao_soma_so_as_materias_com_amostra(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 20, 16)                 # 80% x 5 = 4
    _anotar(plano, SEG, "Língua Portuguesa", 20, 12)             # 60% x 15 = 9

    _, projecao = _montar(plano)
    assert projecao.acertos == 13
    assert projecao.meta == 79
    assert sorted(projecao.com_dado) == ["Direito Penal", "Língua Portuguesa"]
    assert len(projecao.sem_dado) == 9
    assert projecao.tem_dado is True


def test_sem_amostra_nenhuma_nao_ha_projecao(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 10, 10)

    _, projecao = _montar(plano)
    assert projecao.tem_dado is False
    assert projecao.acertos == 0
    assert len(projecao.sem_dado) == 11


def test_a_projecao_ignora_o_que_foi_com_consulta(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 30, 30, consulta=True)

    _, projecao = _montar(plano)
    assert projecao.tem_dado is False       # nada sem consulta: nada a projetar


# --- o casamento dos nomes ------------------------------------------------------

def test_o_nome_do_caderno_antigo_casa_com_o_do_edital(banco_temporario, plano):
    """O caderno de 2013 escreve "Direito Processo Penal"; o edital de 2019,
    "Direito Processual Penal". Sao a mesma materia."""
    _responder("Direito Processo Penal", True, _em(SEG))

    processual = _cartao(_montar(plano)[0], "Direito Processual Penal")
    assert processual.radar.medidas == 1
    assert processual.nunca_estudei is False


def test_materia_que_nao_e_do_edital_nao_entra_em_cartao_nenhum(banco_temporario, plano):
    _responder("Informática", True, _em(SEG))
    cartoes, _ = _montar(plano)
    assert all(c.radar.medidas == 0 for c in cartoes)


def test_o_erro_do_caderno_casa_pelo_mesmo_nome(banco_temporario, plano):
    servico.erros.anotar(data_estudo=SEG, materia="Direito Processo Penal",
                         motivo="pegadinha", regra="Prazo.", hoje=SEG)
    servico.erros.anotar(data_estudo=SEG, materia="Direito Processo Penal",
                         motivo="pegadinha", regra="Outra.", hoje=SEG)
    servico.erros.anotar(data_estudo=SEG, materia="Direito Processo Penal",
                         motivo="chutei", regra="Mais uma.", hoje=SEG)

    processual = _cartao(_montar(plano)[0], "Direito Processual Penal")
    assert processual.erros_no_caderno == 3
    assert processual.motivo_mais_comum == "Pegadinha"


# --- aulas vistas ----------------------------------------------------------------

def test_as_aulas_vistas_contam_as_faixas_de_teoria_marcadas(banco_temporario, plano):
    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.aulas_no_plano == 6          # as aulas de Penal do Ciclo 1
    assert penal.aulas_vistas == 0

    # A teoria do primeiro dia e de Direito Penal.
    montado = cronograma.montar_dia(plano, SEG, 1)
    teoria = montado.manha[0]
    assert teoria.tipo == "teoria" and teoria.materia == "Direito Penal"
    diario.marcar_faixa(SEG, "manha", 0, teoria.titulo, plano=plano,
                        hoje=date(2026, 11, 7))

    assert _cartao(_montar(plano)[0], "Direito Penal").aulas_vistas == 1


def test_a_lei_seca_nao_conta_como_aula(banco_temporario, plano):
    """Ela le a lei do MESMO tema da teoria: contar as duas andaria em dobro."""
    montado = cronograma.montar_dia(plano, SEG, 1)
    posicao = next(i for i, f in enumerate(montado.manha) if f.tipo == "lei_seca")
    diario.marcar_faixa(SEG, "manha", posicao, montado.manha[posicao].titulo,
                        plano=plano, hoje=date(2026, 11, 7))

    assert _cartao(_montar(plano)[0], "Direito Penal").aulas_vistas == 0


# --- os assuntos -----------------------------------------------------------------

def test_os_assuntos_saem_do_pior_para_o_melhor(banco_temporario, plano):
    servico.extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                         assunto="Aplicação da lei", minutos=20, questoes=10,
                         acertos=9, onde="qconcursos", plano=plano,
                         hoje=date(2026, 11, 7))
    servico.extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                         assunto="Crimes contra a pessoa", minutos=20, questoes=10,
                         acertos=4, onde="qconcursos", plano=plano,
                         hoje=date(2026, 11, 7))

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert [a.nome for a in penal.assuntos] == ["Crimes contra a pessoa",
                                                "Aplicação da lei"]
    assert [a.porcentagem for a in penal.assuntos] == [40, 90]
    assert penal.assuntos[0].questoes == 10


def test_assunto_sem_acerto_anotado_vai_para_o_fim(banco_temporario, plano):
    servico.extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                         assunto="Sem nota", minutos=20, questoes=30, onde="outro",
                         plano=plano, hoje=date(2026, 11, 7))
    servico.extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                         assunto="Com nota", minutos=20, questoes=10, acertos=3,
                         onde="qconcursos", plano=plano, hoje=date(2026, 11, 7))

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert [a.nome for a in penal.assuntos] == ["Com nota", "Sem nota"]


def test_o_assunto_da_faixa_e_o_tema_dela(banco_temporario, plano):
    faixa = _anotar(plano, SEG, "Direito Penal", 15, 10)
    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.assuntos[0].nome == faixa.titulo


# --- tempo e ultima vez ----------------------------------------------------------

def test_as_horas_somam_faixas_e_extras(banco_temporario, plano):
    faixa = _anotar(plano, SEG, "Direito Penal", 15, 10)
    servico.extra.anotar(data=SEG, o_que="teoria", materia="Direito Penal",
                         minutos=45, onde="outro", plano=plano,
                         hoje=date(2026, 11, 7))

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert penal.minutos == faixa.duracao + 45


def test_a_ultima_vez_e_o_dia_mais_recente(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 10, 8)
    depois = SEG + timedelta(days=7)
    servico.extra.anotar(data=depois, o_que="teoria", materia="Direito Penal",
                         minutos=30, onde="outro", plano=plano,
                         hoje=date(2026, 11, 7))

    assert _cartao(_montar(plano)[0], "Direito Penal").ultima_vez == depois


# --- o grafico -------------------------------------------------------------------

def test_o_grafico_precisa_de_duas_semanas(banco_temporario, plano):
    _anotar(plano, SEG, "Direito Penal", 20, 10)
    penal = _cartao(_montar(plano)[0], "Direito Penal")
    assert tela.linha_do_grafico(penal.semanal) is None

    _anotar(plano, date(2026, 10, 5), "Direito Penal", 20, 18)
    penal = _cartao(_montar(plano)[0], "Direito Penal")
    pontos = tela.linha_do_grafico(penal.semanal)
    assert pontos is not None and len(pontos.split()) == 2


def test_o_grafico_pula_a_semana_sem_questao(banco_temporario, plano):
    """Semana sem questao sem consulta nao vira ponto: fingir zero seria mentir."""
    _anotar(plano, SEG, "Direito Penal", 20, 10)
    _anotar(plano, date(2026, 10, 12), "Direito Penal", 20, 16)

    penal = _cartao(_montar(plano)[0], "Direito Penal")
    por_semana = {p.semana: p.porcentagem for p in penal.semanal}
    assert por_semana[1] == 50
    assert por_semana[2] is None
    assert por_semana[3] == 80
    assert len(tela.linha_do_grafico(penal.semanal).split()) == 2


# --- a tela -----------------------------------------------------------------------

def test_a_tela_abre_com_as_subabas(cliente):
    texto = cliente.get("/analises/materias").text
    assert "<h1>Minhas matérias</h1>" in texto
    assert 'href="/analises"' in texto
    assert "Minhas matérias" in texto


def test_a_aba_edital_tem_as_subabas(cliente):
    texto = cliente.get("/analises").text
    assert 'href="/analises/materias"' in texto


def test_o_cartao_objetivo_leva_as_materias(cliente):
    texto = cliente.get("/hoje?data=2026-10-20").text
    assert "minhas matérias" in texto
    assert 'href="/analises/materias"' in texto


def test_a_tela_mostra_a_projecao(cliente, plano):
    _anotar(plano, SEG, "Direito Penal", 20, 16)
    texto = cliente.get("/analises/materias").text

    assert "Se a prova fosse hoje" in texto
    assert "~4 acertos" in texto
    assert "meta 79" in texto
    assert "ficaram de fora por falta" in texto


def test_a_tela_avisa_a_amostra_pequena(cliente, plano):
    _anotar(plano, SEG, "Direito Penal", 10, 9)
    texto = cliente.get("/analises/materias").text
    assert "Amostra insuficiente" in texto


def test_a_tela_mostra_o_treino_de_ia_a_parte(cliente, plano):
    _responder("Direito Penal", True, _em(SEG), gerada=True)
    texto = cliente.get("/analises/materias").text
    assert "Treino de IA: 1 de 1 (100%), fora do acerto" in texto


def test_a_tela_desenha_o_grafico_sem_javascript(cliente, plano):
    _anotar(plano, SEG, "Direito Penal", 20, 10)
    _anotar(plano, date(2026, 10, 5), "Direito Penal", 20, 18)
    texto = cliente.get("/analises/materias").text

    assert "<svg class=\"tendencia\"" in texto
    assert "<polyline" in texto
    assert "<script" not in texto.lower()


def test_a_tela_mostra_a_materia_cinza_com_o_ciclo(cliente):
    texto = cliente.get("/analises/materias").text
    assert "Ainda não estudei" in texto
    assert "entra no <b>Ciclo 2</b>" in texto
