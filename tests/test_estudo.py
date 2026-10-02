"""O controle que o ANKI fazia: estudado, nao estudado, revisar, refazer.

O que estes testes seguram:

  * a definicao de "estudado" (faixa de ESTUDO feita, ou extra de teoria/lei),
    separada de "praticado" (tem resposta);
  * os tres gatilhos de revisao, e qual deles disparou;
  * revisar o que eu nunca estudei nao entra na fila;
  * a lista de refazer: as erradas no radar e o caderno, nunca somadas;
  * a evolucao semanal com as mesmas contas da tela Semanas.

As datas sao fixas e o cronograma e o mini: nada aqui depende do dia em que o
teste roda.
"""
from datetime import date

import pytest

from radar import amostra as regua
from radar.servico import erros as caderno
from radar.servico import estudo
from radar.servico import extra as estudo_extra
from radar.servico import semanas as tela_de_semanas

from tests.test_desempenho import (  # noqa: F401 - fixtures e ajudantes
    APLICACAO, HOJE, NO_TEMPO, PENAL, PORTUGUES, SEG, TER, _anotar, _responder,
    arvore, plano,
)


# --- estudado, praticado, nao estudado ------------------------------------------

def test_sem_nada_tudo_e_nao_estudado(plano):
    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    assert len(todas) == 4
    for situacao in todas.values():
        assert situacao.rotulo == estudo.NAO_ESTUDADO
        assert not situacao.estudado and not situacao.praticado


def test_faixa_de_teoria_feita_deixa_o_no_estudado(plano):
    """A faixa de teoria de 28/09 aponta para o assunto: marcar ela torna o
    assunto e a materia estudados."""
    from radar.servico import cronograma as diario

    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano, hoje=HOJE)

    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    assert todas[APLICACAO].estudado and todas[PENAL].estudado
    assert todas[APLICACAO].rotulo == estudo.ESTUDADO
    assert todas[APLICACAO].primeiro_estudo == SEG
    assert todas[APLICACAO].ultimo_estudo == SEG
    # O subassunto NAO herda de cima: ter lido o assunto nao e ter estudado
    # cada parte dele.
    assert not todas[NO_TEMPO].estudado


def test_faixa_de_questoes_nao_deixa_o_no_estudado_e_sim_praticado(plano):
    """Fazer questao e praticar. Eu posso praticar o que nunca li."""
    _anotar(plano, "noite", 0, 15, 11, conteudo=NO_TEMPO)

    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    assert todas[NO_TEMPO].praticado and not todas[NO_TEMPO].estudado
    assert todas[NO_TEMPO].rotulo == estudo.PRATICADO
    assert todas[NO_TEMPO].ultima_pratica == SEG


def test_estudo_extra_de_teoria_deixa_estudado(plano):
    estudo_extra.anotar(data=SEG, o_que="teoria", minutos=40,
                        conteudo=NO_TEMPO, plano=plano, hoje=HOJE)

    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    assert todas[NO_TEMPO].estudado and todas[NO_TEMPO].minutos == 40


def test_responder_no_radar_deixa_praticado(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    assert todas[NO_TEMPO].praticado and todas[PENAL].praticado
    assert todas[NO_TEMPO].ultima_pratica == SEG


def test_estudado_e_praticado_aparecem_juntos(plano):
    _anotar(plano, "noite", 0, 10, 8, conteudo=APLICACAO)
    from radar.servico import cronograma as diario
    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano, hoje=HOJE)

    assert estudo.situacoes(plano=plano, hoje=HOJE)[APLICACAO].rotulo == (
        f"{estudo.ESTUDADO} e {estudo.PRATICADO}")


def test_nao_estudados_lista_a_materia_e_nao_os_filhos_dela(plano):
    """Materia inteira virgem aparece como materia: listar os assuntos dela um
    por um e lista telefonica, nao informacao."""
    _responder(1, True, SEG, materia=PORTUGUES, classificar_em=PORTUGUES)

    virgens = [s.caminho for s in estudo.nao_estudados(plano=plano, hoje=HOJE)]

    assert virgens == [PENAL]        # e nao o assunto nem o subassunto dele


def test_nao_estudados_desce_quando_o_pai_foi_estudado(plano):
    _responder(1, True, SEG, classificar_em=APLICACAO)

    virgens = [s.caminho for s in estudo.nao_estudados(plano=plano, hoje=HOJE)]

    assert NO_TEMPO in virgens and PENAL not in virgens


# --- a evolucao semanal ---------------------------------------------------------

def test_a_evolucao_semanal_usa_as_contas_da_tela_semanas(plano):
    """O mesmo periodo, o mesmo numero: 15 questoes com 11 acertos na semana 1
    da faixa, mais a resposta do radar."""
    _anotar(plano, "noite", 0, 15, 11, conteudo=NO_TEMPO)
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    situacao = estudo.situacoes(plano=plano, hoje=HOJE)[NO_TEMPO]

    assert situacao.semanal == [(1, 75, 16)]     # 12 de 16
    # E o total da semana na tela Semanas inclui essas mesmas 16.
    (ciclo,) = tela_de_semanas.montar(plano=plano, hoje=HOJE)
    assert ciclo.semanas[0].numeros.questoes >= 16


def test_o_que_teve_consulta_fica_fora_da_evolucao(plano):
    _anotar(plano, "noite", 0, 15, 15, consulta=True, conteudo=NO_TEMPO)

    assert estudo.situacoes(plano=plano, hoje=HOJE)[NO_TEMPO].semanal == []


# --- os tres gatilhos de revisao ------------------------------------------------

def test_gatilho_do_prazo_vencido(plano):
    """Estudei em 28/09; a revisao de 1 dia vencia em 29/09, e hoje e 03/10."""
    from radar.servico import cronograma as diario

    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano, hoje=HOJE)

    fila = {r.caminho: r for r in estudo.para_revisar(plano=plano, hoje=HOJE)}

    assert estudo.POR_PRAZO in fila[APLICACAO].porque
    assert fila[APLICACAO].atraso >= 0 and fila[APLICACAO].etapa == 1


def test_gatilho_do_erro_recente(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)

    fila = {r.caminho: r for r in estudo.para_revisar(plano=plano, hoje=HOJE)}

    assert estudo.POR_ERRO in fila[NO_TEMPO].porque
    assert len(fila[NO_TEMPO].erradas) == 1


def test_gatilho_do_erro_anotado_no_caderno(plano):
    # Anotado em 28/09: a revisao de 1 dia vencia em 29/09, e hoje e 03/10.
    caderno.anotar(data_estudo=SEG, materia=PENAL, motivo="pegadinha",
                   regra="o art. 2º cuida da lei penal no tempo",
                   conteudo=NO_TEMPO, hoje=SEG)
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    fila = {r.caminho: r for r in estudo.para_revisar(plano=plano, hoje=HOJE)}

    assert estudo.POR_ERRO in fila[NO_TEMPO].porque
    assert len(fila[NO_TEMPO].erros_do_caderno) == 1


def test_gatilho_do_desempenho_abaixo_do_corte(plano):
    """6 respostas no subassunto (o minimo dele), 2 certas: 33%, abaixo de 60."""
    for numero in range(1, 7):
        _responder(numero, numero <= 2, SEG, classificar_em=NO_TEMPO)

    fila = {r.caminho: r for r in estudo.para_revisar(plano=plano, hoje=HOJE)}

    assert estudo.POR_DESEMPENHO in fila[NO_TEMPO].porque
    assert fila[NO_TEMPO].estado.nome == regua.PRECISA_REVISAR


def test_os_motivos_se_acumulam_na_mesma_linha(plano):
    for numero in range(1, 7):
        _responder(numero, numero <= 2, SEG, classificar_em=NO_TEMPO)

    (linha,) = [r for r in estudo.para_revisar(plano=plano, hoje=HOJE)
                if r.caminho == NO_TEMPO]

    assert estudo.POR_ERRO in linha.porque
    assert estudo.POR_DESEMPENHO in linha.porque
    assert estudo.POR_PRAZO in linha.porque


def test_o_que_eu_nunca_estudei_nao_entra_na_fila(plano):
    """Revisar o que eu nao vi nao e revisao."""
    assert estudo.para_revisar(plano=plano, hoje=HOJE) == []


def test_acertar_na_data_do_vencimento_empurra_o_prazo(plano):
    """A mesma regra do espacada: acertar NO vencimento passa para a proxima
    etapa, e o no sai da fila por prazo."""
    _responder(1, True, SEG, classificar_em=NO_TEMPO)         # pratica em 28/09
    _responder(2, True, TER, classificar_em=NO_TEMPO)         # acerto em 29/09

    # A etapa andou para a de 7 dias, que vence em 06/10: nao esta vencida, e
    # sem outro gatilho o no sai da fila inteira.
    assert [r.caminho for r in estudo.para_revisar(plano=plano, hoje=HOJE)] == []


def test_o_mais_atrasado_vem_primeiro(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, TER, materia=PORTUGUES, classificar_em=PORTUGUES)

    fila = estudo.para_revisar(plano=plano, hoje=HOJE)

    assert fila[0].atraso >= fila[-1].atraso


# --- as questoes a refazer ------------------------------------------------------

def test_refazer_separa_o_radar_do_caderno_e_nunca_soma(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    caderno.anotar(data_estudo=SEG, materia=PENAL, motivo="chutei",
                   regra="ler o enunciado inteiro", conteudo=NO_TEMPO, hoje=SEG)

    tudo = estudo.refazer(hoje=HOJE)

    assert len(tudo.do_radar) == 1
    assert len(tudo.do_caderno) == 1
    assert tudo.total == 2 and not tudo.vazio
    # Nao existe um campo so com os dois: refazer questao e reler regra sao
    # acoes diferentes.
    assert not hasattr(tudo, "tudo_junto")


def test_refazer_de_um_no_so(plano):
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder(2, False, SEG, materia=PORTUGUES, classificar_em=PORTUGUES)

    do_no = estudo.refazer(NO_TEMPO, hoje=HOJE)

    assert len(do_no.do_radar) == 1
    assert len(estudo.refazer(PORTUGUES, hoje=HOJE).do_radar) == 1
    assert len(estudo.refazer(PENAL, hoje=HOJE).do_radar) == 1   # sobe para o pai


def test_sem_erro_nenhum_a_lista_esta_vazia(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)

    assert estudo.refazer(hoje=HOJE).vazio


def test_questao_de_ia_errada_nao_entra_no_refazer(plano):
    _responder(1, False, SEG, gerada=True, classificar_em=NO_TEMPO)

    assert estudo.refazer(hoje=HOJE).vazio
