"""O numero do treino de IA honesto: so a 1a tentativa (decisao 152).

O NIVEL ("o quanto eu sei") conta a 1a resposta de cada gerada; refazer a
mesma vira REVISAO, ao lado. O VOLUME ("o que eu fiz", o "Fiz hoje") continua
contando toda resposta. O chute fica ao lado (o firme); variacao e do zero
saem separados; abaixo do minimo do `config/amostra.yml`, "Amostra
insuficiente". E nada disto entra no acerto das reais.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from radar import amostra
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import metricas
from radar.util import fuso_local
from radar.web.app import app

NO = "Direito Penal > Tipicidade > Dolo e culpa"
DIA = date(2026, 10, 1)


def _gerada(numero: int, conteudo: str = NO, modo: str = "do_zero", **mais) -> int:
    with sessao() as s:
        q = QuestaoGerada(modo=modo, materia="Direito Penal", conteudo=conteudo,
                          enunciado=f"Gerada {numero}, com tamanho bastante?",
                          alternativas={l: l for l in "abcde"}, resposta="c",
                          impressao=f"g{numero}", **mais)
        s.add(q)
        s.flush()
        return q.id


def _responder(questao_id: int, acertou: bool, minuto: int, chutou=None,
               simulado_id: int | None = None) -> int:
    """Uma resposta, numa rodada propria (ou na dada), em ordem de minuto."""
    quando = datetime(2026, 10, 1, 10, 0, tzinfo=fuso_local()) + timedelta(minutes=minuto)
    with sessao() as s:
        if simulado_id is None:
            rodada = Simulado(filtros={"geradas": True})
            s.add(rodada)
            s.flush()
            simulado_id = rodada.id
        s.add(RespostaDeSimulado(simulado_id=simulado_id, questao_id=questao_id, ordem=1,
                                 gerada=True, escolhida="c" if acertou else "a",
                                 acertou=acertou, chutou=chutou, respondida_em=quando))
    return simulado_id


# --- o nivel e a revisao --------------------------------------------------------

def test_uma_gerada_respondida_3_vezes_conta_1_no_nivel_e_2_na_revisao(banco_temporario):
    g = _gerada(1)
    _responder(g, False, 0)                 # a 1a: errei
    _responder(g, True, 10)                 # depois, ja lembrando
    _responder(g, True, 20)

    treino = metricas.treino_ia_dos_nos([NO])

    assert (treino.respondidas, treino.acertos) == (1, 0)
    assert (treino.revisao, treino.revisao_acertos) == (2, 2)
    assert treino.porcentagem == 0
    assert "revisão: 2 de 2" in treino.frase_da_faixa()


def test_o_volume_do_dia_nao_muda(banco_temporario):
    g = _gerada(1)
    for minuto, acertou in ((0, False), (10, True), (20, True)):
        _responder(g, acertou, minuto)

    dia = metricas.do_dia(DIA)

    # O "Fiz hoje" conta as 3 respostas, como sempre (decisao 127).
    assert (dia.treino_ia.ia, dia.treino_ia.ia_acertos) == (3, 2)
    assert metricas.frase_da_ia(dia.total).startswith("Treino de IA no radar: 3 questões")


def test_a_1a_vez_e_pela_ordem_em_que_respondi(banco_temporario):
    g = _gerada(1)
    # Gravadas fora de ordem: a de 10h00 e a 1a, mesmo entrando depois.
    _responder(g, True, 30)
    _responder(g, False, 0)

    treino = metricas.treino_ia_dos_nos([NO])

    assert (treino.respondidas, treino.acertos, treino.revisao_acertos) == (1, 0, 1)


# --- o chute ao lado --------------------------------------------------------------

def test_o_chute_fica_ao_lado_no_firme(banco_temporario):
    respostas = [(True, True), (False, True), (True, False), (True, False), (False, None)]
    for numero, (acertou, chutou) in enumerate(respostas, start=1):
        _responder(_gerada(numero), acertou, numero, chutou=chutou)

    treino = metricas.treino_ia_dos_nos([NO])

    # O acerto e o mesmo, com ou sem chute: 3 de 5.
    assert (treino.acertos, treino.respondidas, treino.porcentagem) == (3, 5, 60)
    # O firme tira os 2 chutes (o certo e o errado): 2 de 3. A resposta sem o
    # chute registrado (de antes de 07/10) conta como nao chutada.
    assert (treino.chutes, treino.chutes_certos, treino.firmes) == (2, 1, 3)
    assert treino.porcentagem_firme == 67
    assert "firme: 67%, sem os 2 chutes" in treino.frase_da_faixa()


def test_sem_chute_marcado_nao_ha_firme(banco_temporario):
    _responder(_gerada(1), True, 0, chutou=False)

    assert "firme" not in metricas.treino_ia_dos_nos([NO]).frase_da_faixa()


# --- o minimo de amostra ------------------------------------------------------------

def test_os_minimos_do_treino_de_ia_vem_do_config():
    minimos = amostra.carregar()
    assert [minimos.do_treino_ia(n) for n in amostra.NIVEIS] == [30, 15, 10, 10]
    # Nunca a regua das reais.
    assert minimos.do_nivel("subassunto") == 6


def test_o_minimo_sai_do_arquivo(tmp_path):
    arquivo = tmp_path / "amostra.yml"
    arquivo.write_text("treino_ia:\n  minimos:\n    subassunto: 4\n", encoding="utf-8")

    minimos = amostra.carregar(arquivo)

    assert minimos.do_treino_ia("subassunto") == 4
    assert minimos.do_treino_ia("materia") == 30        # o resto, o padrao


def test_abaixo_do_minimo_amostra_insuficiente(banco_temporario):
    for numero in range(1, 10):                         # 9 de 10 no subassunto
        _responder(_gerada(numero), True, numero)

    treino = metricas.treino_ia_dos_nos([NO])
    assert treino.minimo == 10 and not treino.suficiente
    assert treino.amostra == amostra.INSUFICIENTE
    assert "(100%, amostra insuficiente)" in treino.frase_da_faixa()
    assert "o mínimo aqui é 10" in treino.linhas_da_ficha()[0]

    _responder(_gerada(10), True, 10)                   # a 10a
    completo = metricas.treino_ia_dos_nos([NO])
    assert completo.suficiente and completo.amostra is None
    assert "insuficiente" not in completo.frase_da_faixa()


def test_a_revisao_nao_completa_o_minimo(banco_temporario):
    g = _gerada(1)
    for minuto in range(12):
        _responder(g, True, minuto)

    treino = metricas.treino_ia_dos_nos([NO])
    assert treino.respondidas == 1 and not treino.suficiente


def test_o_tema_de_varios_nos_pede_o_minimo_do_mais_largo(banco_temporario):
    assunto = "Direito Penal > Tipicidade"
    assert metricas.treino_ia_dos_nos([NO, assunto]).minimo == 15
    assert metricas.treino_ia_dos_nos([NO]).minimo == 10


# --- variacao e do zero ------------------------------------------------------------

def test_variacao_e_do_zero_separados(banco_temporario):
    _responder(_gerada(1, modo="variacao"), True, 1)
    _responder(_gerada(2, modo="variacao"), False, 2)
    _responder(_gerada(3), True, 3)

    treino = metricas.treino_ia_dos_nos([NO])

    assert (treino.variacao, treino.variacao_acertos) == (2, 1)
    assert (treino.do_zero, treino.do_zero_acertos) == (1, 1)
    assert "Variação de questão real: 50% em 2 · do zero: 100% em 1." in treino.linhas_da_ficha()


# --- nada disto no acerto das reais -------------------------------------------------

def test_nada_disto_aparece_no_acerto_das_reais(banco_temporario):
    g = _gerada(1)
    _responder(g, True, 0)
    _responder(g, True, 5)

    assert metricas.desempenho() == []                  # as reais: nada
    assert metricas.do_dia(DIA).reais.medidas == 0
    # O acumulado das geradas conta a 1a vez, como o das reais conta uma vez.
    [linha] = metricas.desempenho_das_geradas()
    assert (linha.respondidas, linha.acertos) == (1, 1)


def test_o_acerto_por_nivel_da_rodada_e_so_a_1a_vez(banco_temporario):
    antiga, nova = _gerada(1, nivel="dificil"), _gerada(2, nivel="facil")
    _responder(antiga, False, 0)                        # vista antes
    rodada = _responder(antiga, True, 10)
    _responder(nova, True, 11, simulado_id=rodada)

    por_nivel = metricas.acerto_das_geradas_por_nivel(rodada)

    assert [(n.rotulo, n.acertos, n.respondidas) for n in por_nivel] == [("Fácil", 1, 1)]
    assert metricas.revisao_da_rodada(rodada) == (1, 1)


# --- as telas ------------------------------------------------------------------------

def test_o_simulado_e_a_tela_de_gerar_mostram_a_1a_vez_e_a_revisao(banco_temporario):
    g = _gerada(1)
    _responder(g, False, 0)
    _responder(g, True, 5)
    cliente = TestClient(app)

    simulado = cliente.get("/simulado").text
    parte = simulado.split("Nas questões geradas")[1].split("</section>")[0]
    assert "1ª vez" in parte and "0% em 1" in parte and "1 de 1" in parte
    assert amostra.INSUFICIENTE in parte

    gerar = cliente.get("/geradas").text
    tabela = gerar.split("Como você vai, nos dois")[1].split("</section>")[0]
    assert "a 1ª resposta de cada uma" in tabela
    assert "revisão 1 de 1" in tabela
