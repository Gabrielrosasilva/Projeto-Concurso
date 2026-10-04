"""O controle que o ANKI fazia: estudado, nao estudado, revisar, refazer.

O que estes testes seguram:

  * a definicao de "estudado" (faixa de ESTUDO feita, ou extra de teoria/lei),
    separada de "praticado" (tem resposta);
  * os tres gatilhos de revisao, e qual deles disparou;
  * revisar o que eu nunca estudei nao entra na fila;
  * a lista de refazer: as erradas no radar e o caderno, nunca somadas;
  * a evolucao semanal com as mesmas contas da tela Semanas - toda resposta,
    e nao so a ultima de cada questao -, e a semana abaixo do minimo marcada;
  * a data da ultima revisao (decisao 79): so o que e revisao, nunca a
    pratica comum;
  * a faixa sem `conteudo` conta no que cobre - os `nos` do plano e a
    ficha conferida -, so para a situacao e as datas (decisao 81).

As datas sao fixas e o cronograma e o mini: nada aqui depende do dia em que o
teste roda.
"""
import re
from datetime import date, datetime, timedelta

import pytest
import yaml
from sqlalchemy import select

from radar import amostra as regua
from radar import cronograma, fichas
from radar.db import sessao
from radar.models import QuestaoDeProva, RespostaDeSimulado, Simulado
from radar.servico import desempenho_por_conteudo as por_conteudo
from radar.servico import erros as caderno
from radar.servico import estudo
from radar.servico import conteudos as servico_conteudos
from radar.servico import cronograma as diario
from radar.servico import extra as estudo_extra
from radar.servico import fichas as servico_fichas
from radar.servico import metricas
from radar.servico import semanas as tela_de_semanas
from radar.util import fuso_local

from tests.test_desempenho import (  # noqa: F401 - fixtures e ajudantes
    APLICACAO, HOJE, MINI, NO_TEMPO, PENAL, PORTUGUES, SEG, TER, _anotar,
    _responder, arvore, plano,
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

    assert situacao.semanal == [estudo.Semana(1, 75, 16, suficiente=True)]  # 12 de 16
    # E o total da semana na tela Semanas inclui essas mesmas 16.
    (ciclo,) = tela_de_semanas.montar(plano=plano, hoje=HOJE)
    assert ciclo.semanas[0].numeros.questoes >= 16


def test_o_que_teve_consulta_fica_fora_da_evolucao(plano):
    _anotar(plano, "noite", 0, 15, 15, consulta=True, conteudo=NO_TEMPO)

    assert estudo.situacoes(plano=plano, hoje=HOJE)[NO_TEMPO].semanal == []


def _responder_de_novo(numero: int, acertou: bool, quando: date, filtros: dict) -> None:
    """Mais uma resposta a questao `numero`, numa rodada nova com estes
    filtros: e o filtro da rodada que diz se ela revisa."""
    with sessao() as s:
        questao = s.scalar(select(QuestaoDeProva).where(QuestaoDeProva.numero == numero))
        simulado = Simulado(filtros=filtros)
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=simulado.id, questao_id=questao.id, ordem=1,
            escolhida="a" if acertou else "b", acertou=acertou,
            respondida_em=datetime.combine(quando, datetime.min.time(),
                                           tzinfo=fuso_local()) + timedelta(hours=21),
        ))


def test_a_evolucao_conta_toda_resposta_e_nao_so_a_ultima(plano):
    """Errei em 28/09 e acertei a mesma questao em 29/09: a semana tem as duas
    respostas, como a tela Semanas. So a ultima daria 100% em 1, e apagaria o
    erro que a evolucao existe para mostrar."""
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder_de_novo(1, True, TER, filtros={})

    (semana,) = estudo.situacoes(plano=plano, hoje=HOJE)[APLICACAO].semanal

    assert (semana.numero, semana.porcentagem, semana.respostas) == (1, 50, 2)


def test_a_semana_abaixo_do_minimo_do_assunto_aparece_marcada(plano):
    """O numero aparece, mas a semana diz que nao chegou ao minimo do
    config/amostra.yml - lido de la, e nao repetido aqui."""
    minimo = regua.carregar().do_nivel("assunto")
    _anotar(plano, "noite", 0, minimo - 1, minimo - 1, conteudo=APLICACAO)

    (semana,) = estudo.situacoes(plano=plano, hoje=HOJE)[APLICACAO].semanal

    assert (semana.porcentagem, semana.respostas) == (100, minimo - 1)
    assert not semana.suficiente


def test_a_semana_que_chega_ao_minimo_do_assunto_vale(plano):
    minimo = regua.carregar().do_nivel("assunto")
    _anotar(plano, "noite", 0, minimo, minimo, conteudo=APLICACAO)

    (semana,) = estudo.situacoes(plano=plano, hoje=HOJE)[APLICACAO].semanal

    assert semana.suficiente


def test_questao_de_ia_nao_entra_na_evolucao(plano):
    _responder(1, True, SEG, gerada=True, classificar_em=NO_TEMPO)

    assert estudo.situacoes(plano=plano, hoje=HOJE)[NO_TEMPO].semanal == []


# --- a data da ultima revisao (decisao 79) --------------------------------------

def test_praticar_nao_e_revisar(plano):
    """Faixa de questoes e rodada comum sao pratica: a revisao fica vazia."""
    _anotar(plano, "noite", 0, 15, 11, conteudo=NO_TEMPO)
    _responder(1, True, TER, classificar_em=NO_TEMPO)

    situacao = estudo.situacoes(plano=plano, hoje=HOJE)[NO_TEMPO]

    assert situacao.ultima_pratica == TER
    assert situacao.ultima_revisao is None


def test_a_faixa_de_revisao_anotada_no_no_e_a_ultima_revisao(plano):
    """O R+7 de 29/09 do cronograma mini, anotado no subassunto: e revisao
    dele e dos nos de cima, e de mais nenhum."""
    _anotar(plano, "noite", 0, 10, 8, data=TER, conteudo=NO_TEMPO)

    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    for caminho in (NO_TEMPO, APLICACAO, PENAL):
        assert todas[caminho].ultima_revisao == TER
    assert todas[PORTUGUES].ultima_revisao is None


def test_o_estudo_extra_de_revisao_e_revisao(plano):
    estudo_extra.anotar(data=TER, o_que="revisao", minutos=30,
                        conteudo=NO_TEMPO, plano=plano, hoje=HOJE)

    assert estudo.situacoes(plano=plano, hoje=HOJE)[NO_TEMPO].ultima_revisao == TER


def test_a_rodada_que_revisa_no_radar_e_revisao(plano):
    """Errada numa rodada comum em 28/09, refeita numa rodada so de erradas
    em 29/09: a revisao e a de 29/09."""
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    _responder_de_novo(1, True, TER, filtros={"quantidade": 1, "erros": True})

    situacao = estudo.situacoes(plano=plano, hoje=HOJE)[NO_TEMPO]

    assert situacao.ultima_revisao == TER
    assert situacao.ultima_pratica == TER


@pytest.mark.parametrize("filtros, revisa", [
    ({"revisao": [{"materia": PENAL, "assunto": None, "etapa": 1}]}, True),  # a espacada
    ({"quantidade": 5, "erros": True}, True),                       # Refazer as erradas
    ({"erros": True, "rodada": "erros_das_rodadas"}, True),         # a do sabado
    ({"quantidade": 10, "materia": PENAL}, False),                  # rodada comum
    ({"rodada": "composta"}, False),                                # diagnostico, simulado
    ({}, False),
    (None, False),
])
def test_quais_rodadas_revisam(filtros, revisa):
    assert metricas.rodada_que_revisa(filtros) is revisa


# --- a secao da tela ------------------------------------------------------------

def test_estudados_ou_praticados_vem_na_ordem_da_arvore_e_filtram_a_materia(plano):
    _responder(1, True, SEG, classificar_em=NO_TEMPO)
    _responder(2, True, SEG, materia=PORTUGUES, classificar_em=PORTUGUES)
    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    assert [s.caminho for s in estudo.estudados_ou_praticados(todas)] == [
        PENAL, APLICACAO, NO_TEMPO, PORTUGUES]
    # Sem acento e sem caixa, como o filtro do resto da tela.
    assert [s.caminho for s in estudo.estudados_ou_praticados(
        todas, "lingua portuguesa")] == [PORTUGUES]


def test_a_fila_e_os_nao_estudados_aceitam_as_situacoes_ja_montadas(plano):
    """A tela monta as situacoes uma vez so, e o resultado nao muda."""
    _responder(1, False, SEG, classificar_em=NO_TEMPO)
    todas = estudo.situacoes(recorte=por_conteudo.CICLO, plano=plano, hoje=HOJE)

    def caminhos(lista):
        return [item.caminho for item in lista]

    assert caminhos(estudo.para_revisar(plano, HOJE, todas=todas)) == caminhos(
        estudo.para_revisar(plano, HOJE))
    assert caminhos(estudo.nao_estudados(todas=todas)) == caminhos(
        estudo.nao_estudados(plano=plano, hoje=HOJE))


def test_a_tela_mostra_a_ultima_revisao_e_a_evolucao_no_assunto(plano, monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    monkeypatch.setattr("radar.cronograma.carregar", lambda *a, **k: plano)
    _anotar(plano, "noite", 0, 5, 4, data=TER, conteudo=NO_TEMPO)      # o R+7
    _responder(1, True, HOJE, classificar_em=APLICACAO)
    _responder(2, True, SEG, materia=PORTUGUES, classificar_em=PORTUGUES)

    pagina = TestClient(app).get("/analises/desempenho").text
    secao = re.search(r"Quando eu estudei e revisei cada conteúdo</h2>(.*?)</section>",
                      pagina, re.S).group(1)
    texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", secao))

    # Ultima vez 03/10 (a resposta do radar), ultima revisao 29/09 (o R+7), e
    # a semana do assunto: 4 de 5 anotadas + 1 de 1 no radar = 83% em 6.
    assert "Aplicação da lei penal praticado 03/10 29/09 semana 1: 83% em 6" in texto
    assert "Lei penal no tempo praticado 29/09 29/09 —" in texto
    assert "Língua Portuguesa praticado 28/09 nunca —" in texto
    # 6 respostas e menos que o minimo do assunto: a semana vem marcada.
    assert regua.carregar().do_nivel("assunto") > 6
    assert 'class="semana abaixo">semana 1: 83% em 6<' in secao


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


# --- a faixa sem `conteudo` conta no que cobre (decisao 81) ---------------------

@pytest.fixture
def plano_com_nos(arvore, tmp_path):
    """O cronograma mini SEM `conteudo`: a faixa de questoes de 28/09 e o R+7
    de 29/09 dizem o que cobrem pela chave `nos` do plano."""
    servico_conteudos.exportar()
    dados = yaml.safe_load(MINI.read_text(encoding="utf-8"))
    dados["dias"][0]["noite"][0]["nos"] = [NO_TEMPO]    # Aprendizagem, de Direito Penal
    dados["dias"][1]["noite"][0]["nos"] = [NO_TEMPO]    # o R+7
    arquivo = tmp_path / "cronograma_com_nos.yml"
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return cronograma.carregar(arquivo)


def _ficha(**mudar) -> fichas.FichaEscrita:
    """A ficha do tema da teoria de 28/09 ("Aplicação da lei penal")."""
    base = dict(tema="Aplicação da lei penal", materia=PENAL, nos=[NO_TEMPO],
                modelo="Claude Code, de teste", criado_em="2026-10-02T12:00:00+00:00")
    base.update(mudar)
    return fichas.FichaEscrita(**base)


def test_a_faixa_sem_conteudo_conta_nos_nos_do_plano_so_para_situacao_e_datas(plano_com_nos):
    _anotar(plano_com_nos, "noite", 0, 15, 11)          # sem escolher conteudo

    todas = estudo.situacoes(plano=plano_com_nos, hoje=HOJE)

    for caminho in (NO_TEMPO, APLICACAO, PENAL):
        assert todas[caminho].praticado and todas[caminho].ultima_pratica == SEG
    # O acerto nao vai a no nenhum: nem o desempenho, nem a evolucao.
    assert todas[NO_TEMPO].semanal == [] and todas[NO_TEMPO].desempenho is None
    assert NO_TEMPO not in por_conteudo.por_no(plano=plano_com_nos, hoje=HOJE)
    assert todas[PORTUGUES].rotulo == estudo.NAO_ESTUDADO


def test_o_r7_sem_conteudo_marca_a_revisao_do_que_cobre(plano_com_nos):
    _anotar(plano_com_nos, "noite", 0, 10, 8, data=TER)

    todas = estudo.situacoes(plano=plano_com_nos, hoje=HOJE)

    assert todas[NO_TEMPO].ultima_revisao == TER
    assert todas[PENAL].ultima_revisao == TER


def test_a_ficha_so_liga_a_faixa_depois_de_conferida(plano_com_nos):
    """A teoria de 28/09 nao tem `nos` no plano: so a ficha diz o que ela
    cobre, e a ficha e da IA ate eu conferir."""
    servico_fichas.gravar([_ficha()])
    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano_com_nos, hoje=HOJE)

    assert not estudo.situacoes(plano=plano_com_nos, hoje=HOJE)[NO_TEMPO].estudado

    servico_fichas.gravar([_ficha(conferida_em="2026-10-03")])
    todas = estudo.situacoes(plano=plano_com_nos, hoje=HOJE)

    assert todas[NO_TEMPO].estudado and todas[NO_TEMPO].ultimo_estudo == SEG
    assert todas[APLICACAO].estudado


def test_a_ficha_conferida_sem_no_conta_no_assunto_que_ela_escreve(plano_com_nos):
    servico_fichas.gravar([_ficha(nos=[], assunto="Aplicação da lei penal",
                                  conferida_em="2026-10-03")])
    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano_com_nos, hoje=HOJE)

    todas = estudo.situacoes(plano=plano_com_nos, hoje=HOJE)

    assert todas[APLICACAO].estudado
    # O subassunto nao: a ficha nao disse que o tema e ele.
    assert not todas[NO_TEMPO].estudado


def test_a_faixa_com_conteudo_continua_so_no_conteudo(plano):
    """Com a chave `conteudo`, nada muda: o acerto vai ao no escolhido, e a
    ficha conferida nao espalha a faixa para outros nos."""
    servico_fichas.gravar([_ficha(nos=[NO_TEMPO], conferida_em="2026-10-03")])
    diario.marcar_faixa(SEG, "manha", 0, "Aplicação da lei penal",
                        plano=plano, hoje=HOJE)

    todas = estudo.situacoes(plano=plano, hoje=HOJE)

    assert todas[APLICACAO].estudado
    assert not todas[NO_TEMPO].estudado
