"""A sequencia de dias sem zerar (🔥) e a frase animadora da semana.

Contas puras sobre o config/cronograma.yml de verdade, com as metas escritas
a mao e o "hoje" fingido. A semana 1 vai de 28/09 (segunda) a 03/10 (sabado);
04/10 e domingo, fora do plano. Nivel 1 da rampa: Direito 15, Portugues 10;
nivel 2: Direito 20, Portugues 10.
"""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from radar import cronograma, servico
from radar.servico.cronograma import frase_da_semana, sequencia
from radar.util import fuso_local
from radar.web.app import app


def d(dia, mes=10):
    return date(2026, mes, dia)


@pytest.fixture(scope="module")
def plano():
    return cronograma.carregar()


def _nivel(semana, efetivo):
    return cronograma.Nivel(semana, semana, efetivo, efetivo, "neutra", "")


# --- a sequencia --------------------------------------------------------------

def test_domingo_no_meio_nao_quebra(plano):
    metas = {d(1): "ideal", d(2): "reduzida", d(3): "minima", d(5): "ideal"}
    # Hoje 06/10, ainda sem marca: conta de ontem (05) para tras, pulando o 04.
    assert sequencia(plano, metas, d(6)) == 4


def test_hoje_conta_se_ja_estiver_marcado(plano):
    metas = {d(5): "ideal", d(6): "minima"}
    assert sequencia(plano, metas, d(6)) == 2
    # Hoje sem marca nao quebra: o dia ainda nao acabou.
    assert sequencia(plano, {d(5): "ideal"}, d(6)) == 1


def test_dia_sem_marcacao_quebra(plano):
    metas = {d(1): "ideal", d(3): "ideal", d(5): "ideal"}      # 02/10 em branco
    assert sequencia(plano, metas, d(6)) == 2


def test_nao_fiz_quebra(plano):
    metas = {d(1): "ideal", d(2): "ideal", d(3): "nao_fiz", d(5): "ideal"}
    assert sequencia(plano, metas, d(6)) == 1
    # Hoje marcado como "nao fiz" tambem conta - e zera.
    assert sequencia(plano, {d(5): "ideal", d(6): "nao_fiz"}, d(6)) == 0


def test_sem_nada_marcado_e_zero(plano):
    assert sequencia(plano, {}, d(6)) == 0


def test_o_comeco_do_ciclo_encerra_a_conta(plano):
    metas = {d(28, 9): "ideal", d(29, 9): "ideal"}
    assert sequencia(plano, metas, d(30, 9)) == 2


# --- a frase da semana ------------------------------------------------------

def test_da_para_subir(plano):
    metas = {d(28, 9): "ideal", d(29, 9): "ideal", d(30, 9): "ideal"}
    frase = frase_da_semana(plano, metas, d(1), d(1), _nivel(1, 1))
    assert frase == ("🔥 3 dias completos! Mais 2 e a semana que vem sobe para "
                     "20 questões de Direito.")


def test_segunda_sem_nada_marcado(plano):
    frase = frase_da_semana(plano, {}, d(28, 9), d(28, 9), _nivel(1, 1))
    assert frase == "🔥 Faça 5 dias completos e a semana que vem sobe para 20 questões de Direito."


def test_quando_o_nivel_de_cima_muda_as_duas_materias(plano):
    # Do nivel 2 (Direito 20, Portugues 10) para o 3 (Direito 20, Portugues 15)
    # so o Portugues muda; do 3 para o 4, so o Direito.
    frase = frase_da_semana(plano, {d(5): "ideal"}, d(6), d(6), _nivel(2, 2))
    assert frase.endswith("sobe para 15 questões de Português.")


def test_semana_garantida(plano):
    metas = {d(28, 9): "ideal", d(29, 9): "ideal", d(30, 9): "ideal",
             d(1): "ideal", d(2): "ideal"}
    frase = frase_da_semana(plano, metas, d(2), d(2), _nivel(1, 1))
    assert frase == "✅ Semana garantida! A próxima sobe para o nível 2."


def test_feriado_feito_como_minima_conta_como_completo(plano):
    # Semana 3: 12/10 e feriado. Minima nele + 4 dias completos = garantida.
    feriado = plano.dia(d(12))
    assert feriado.feriado
    metas = {d(12): "minima", d(13): "ideal", d(14): "ideal", d(15): "ideal", d(16): "ideal"}
    frase = frase_da_semana(plano, metas, d(16), d(16), _nivel(3, 3))
    assert frase.startswith("✅ Semana garantida!")


def test_nao_sobe_mais_depois_de_um_nao_fiz(plano):
    metas = {d(28, 9): "nao_fiz"}
    frase = frase_da_semana(plano, metas, d(29, 9), d(29, 9), _nivel(1, 1))
    assert frase == ("Essa semana não sobe mais, mas cada dia feito mantém a sua "
                     "sequência. Bora!")


def test_nao_sobe_mais_quando_faltam_mais_dias_do_que_restam(plano):
    # 2 completos; restam 02/10 e 03/10; faltam 3.
    metas = {d(28, 9): "ideal", d(29, 9): "reduzida", d(30, 9): "minima", d(1): "ideal"}
    frase = frase_da_semana(plano, metas, d(2), d(2), _nivel(1, 1))
    assert frase.startswith("Essa semana não sobe mais")


def test_dia_passado_sem_marcacao_conta_como_perdido(plano):
    # Hoje e 03/10 (sabado): so ele resta; 28/09 a 02/10 em branco.
    frase = frase_da_semana(plano, {}, d(3), d(3), _nivel(1, 1))
    assert frase.startswith("Essa semana não sobe mais")


def test_carga_maxima(plano):
    ultimo = max(plano.rampa)
    frase = frase_da_semana(plano, {}, d(2, 11), d(2, 11), _nivel(6, ultimo))
    assert frase == "💪 Você está na carga máxima do ciclo. Mantenha!"


def test_semana_futura_e_fora_do_ciclo_nao_tem_frase(plano):
    assert frase_da_semana(plano, {}, d(5), d(1), _nivel(2, 2)) is None
    assert frase_da_semana(plano, {}, d(4), d(4), _nivel(1, 1)) is None     # domingo
    assert frase_da_semana(plano, {}, d(1, 12), d(1, 12), _nivel(6, 6)) is None


def test_ultima_semana_abaixo_do_teto_nao_promete_subir(plano):
    """Nao ha "semana que vem" depois da ultima do ciclo."""
    assert frase_da_semana(plano, {}, d(2, 11), d(2, 11), _nivel(6, 4)) is None


# --- na tela ------------------------------------------------------------------

@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    momento = datetime(2026, 10, 1, 12, 0, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: momento)
    return TestClient(app)


def test_a_tela_mostra_a_sequencia_e_a_frase(cliente):
    for dia in (d(28, 9), d(29, 9), d(30, 9)):
        servico.cronograma.registrar(dia, "ideal")
    texto = cliente.get("/hoje").text
    assert "🔥 3 dias seguidos" in texto                          # o selo azul
    assert "<b>🔥 3</b> · dias seguidos sem zerar" in texto        # o cartao
    assert ("🔥 3 dias completos! Mais 2 e a semana que vem sobe para "
            "20 questões de Direito.") in texto


def test_sem_nada_marcado_a_tela_convida(cliente, monkeypatch):
    # Na segunda, com a semana inteira pela frente.
    segunda = datetime(2026, 9, 28, 9, 0, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: segunda)
    texto = cliente.get("/hoje").text
    assert texto.count("Comece hoje a sua sequência") == 2        # selo e cartao
    assert "🔥 Faça 5 dias completos" in texto


def test_semana_futura_na_tela_nao_tem_frase(cliente):
    texto = cliente.get("/hoje?data=2026-10-06").text
    assert 'class="frase"' not in texto
