"""A fonte unica das metricas (Etapa 1C): uma conta, num lugar so.

O caso que motivou tudo e o 28/09: a tela mostrou "31 questoes, 13 acertos,
8 erros", e 13 + 8 nao da 31. Nao havia dado errado - as 10 que faltavam eram
de IA, e a linha nao dizia isso. Estes testes seguram a regra:

    questoes = acertos + erros + sem acerto anotado + treino de IA

O cronograma e o mini (tests/fixtures) e as datas sao fixas: nada aqui depende
do dia em que o teste roda.
"""
from datetime import date, datetime
from pathlib import Path

import pytest

from radar import cronograma
from radar.db import sessao
from radar.models import EstadoDoDia, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import extra as estudo_extra
from radar.servico import metricas
from radar.util import fuso_local

from tests.test_foco import com_quadro_do_edital  # noqa: F401 - fixture

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
SEG = date(2026, 9, 28)
TER = date(2026, 9, 29)
HOJE = date(2026, 10, 3)


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


def _faixa(plano, bloco, indice, data=SEG):
    return getattr(cronograma.montar_dia(plano, data, 1), bloco)[indice]


def _anotar(plano, bloco, indice, questoes, acertos, consulta=False, data=SEG):
    faixa = _faixa(plano, bloco, indice, data)
    diario.anotar_faixa(data, bloco, indice, faixa.titulo, questoes=questoes,
                        acertos=acertos, consulta=consulta, plano=plano, hoje=HOJE)


def _responder(acertou, quando, gerada=False, questao_id=1, simulado_id=None):
    """Uma resposta dada no radar. `quando` None = rodada nao terminada."""
    with sessao() as s:
        if simulado_id is None:
            simulado = Simulado(filtros={})
            s.add(simulado)
            s.flush()
            simulado_id = simulado.id
        s.add(RespostaDeSimulado(
            simulado_id=simulado_id, questao_id=questao_id, gerada=gerada,
            ordem=1, escolhida="a" if quando else None,
            acertou=acertou if quando else None, respondida_em=quando,
        ))
    return simulado_id


def _as_21h(data=SEG, minuto=0):
    return datetime(data.year, data.month, data.day, 21, minuto, tzinfo=fuso_local())


def _fecha(numeros) -> bool:
    return numeros.questoes == (numeros.acertos + numeros.erros
                                + numeros.sem_resultado + numeros.ia)


# --- o 28/09 ------------------------------------------------------------------

def _o_dia_28(plano):
    """O dia como ele foi: Penal 11/6 e Portugues 10/7 anotados (Qconcursos),
    o Bonus marcado com 0 questoes, e 10 questoes de IA no radar (7 certas)."""
    _anotar(plano, "noite", 0, 11, 6)
    _anotar(plano, "noite", 2, 10, 7)
    _bonus_com_zero_gravado_antes_da_1d(plano)
    for n in range(10):
        _responder(n < 7, _as_21h(minuto=n), gerada=True, questao_id=n + 1)


def test_o_28_09_fecha_a_conta(banco_temporario, plano):
    _o_dia_28(plano)

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == 31
    assert (conta.total.acertos, conta.total.erros) == (13, 8)
    assert conta.total.ia == 10
    assert metricas.frase_da_conta(conta.total) == (
        "31 questões = 13 acertos + 8 erros + 10 de treino de IA")


def test_o_acerto_da_ia_e_um_segundo_numero(banco_temporario, plano):
    _o_dia_28(plano)

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.porcentagem == 62            # 13 de 21: so as reais
    assert conta.treino_ia.ia_acertos == 7
    assert metricas.frase_da_ia(conta.total) == (
        "Treino de IA no radar: 10 questões = 7 acertos + 3 erros (70%), "
        "não entra no acerto")
    # Decisao 138: as reais numa linha, sem o treino de IA dentro.
    assert metricas.frase_das_reais(conta.reais) == (
        "Questões reais (Qconcursos e provas): 21 questões = 13 acertos + 8 erros")


def _bonus_com_zero_gravado_antes_da_1d(plano):
    """O Bonus de 28/09: marcado com 0 questoes. Desde a 1D a tela recusa
    isso, e o dado so existe gravado direto no banco - como o de verdade
    estava antes da conferencia."""
    faixa = _faixa(plano, "pos22", 1)
    check = {"bloco": "pos22", "indice": 1, "titulo": faixa.titulo,
             "minutos": faixa.duracao or 0, "questoes": 0, "acertos": None,
             "consulta": False, "materia": faixa.materia, "assunto": faixa.titulo}
    with sessao() as s:
        estado = s.query(EstadoDoDia).filter_by(data=SEG).one_or_none()
        if estado is None:
            estado = EstadoDoDia(data=SEG, faixas_feitas=[])
            s.add(estado)
        estado.faixas_feitas = list(estado.faixas_feitas or []) + [check]


def test_o_bonus_com_zero_questoes_conta_os_minutos_e_nenhuma_questao(
        banco_temporario, plano):
    """O que ja estava gravado com 0 questoes nao inventa questao. A tela nao
    aceita mais o 0 (1D); a conferencia dos dias propoe desmarcar."""
    _bonus_com_zero_gravado_antes_da_1d(plano)

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == 0
    assert conta.minutos > 0


# --- a regra do total, em todos os recortes -----------------------------------

def test_a_regra_fecha_em_todos_os_recortes(banco_temporario, plano):
    """Um dia com os quatro estados: acerto, erro, sem acerto anotado e IA."""
    _anotar(plano, "noite", 0, 15, None, consulta=True)       # sem resultado
    _anotar(plano, "noite", 2, 10, 2)
    estudo_extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                        minutos=30, questoes=12, acertos=9, onde="qconcursos",
                        plano=plano, hoje=HOJE)
    _responder(True, _as_21h(minuto=1))
    _responder(False, _as_21h(minuto=2))
    _responder(True, _as_21h(minuto=3), gerada=True)

    conta = metricas.do_dia(SEG, plano)

    for nome in ("faixas", "extra", "radar", "treino_ia", "sem_consulta"):
        assert _fecha(getattr(conta, nome)), nome
    for numeros in (conta.anotado, conta.total):
        assert _fecha(numeros)
    assert metricas.frase_da_conta(conta.total) == (
        "40 questões = 12 acertos + 12 erros + 15 sem acerto anotado "
        "+ 1 de treino de IA")
    # A meta olha so o que foi feito sem consulta: a faixa de 15 fica fora.
    assert conta.sem_consulta.questoes == 24


def test_o_total_e_a_soma_dos_recortes(banco_temporario, plano):
    _o_dia_28(plano)
    _responder(True, _as_21h(minuto=30))

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == (conta.anotado.questoes + conta.radar.questoes
                                    + conta.treino_ia.questoes)
    assert conta.total.acertos == conta.anotado.acertos + conta.radar.acertos


# --- o que nao conta ----------------------------------------------------------

def test_ia_nunca_entra_no_acerto(banco_temporario, plano):
    _responder(True, _as_21h(), gerada=True)

    conta = metricas.do_dia(SEG, plano)

    assert conta.total.questoes == 1
    assert conta.total.medidas == 0
    assert conta.total.porcentagem is None
    assert conta.radar.questoes == 0


def test_rodada_nao_terminada_nao_conta(banco_temporario, plano):
    simulado = _responder(True, _as_21h())
    _responder(None, None, simulado_id=simulado, questao_id=2)

    assert metricas.do_dia(SEG, plano).total.questoes == 1


def test_linha_que_nao_fecha_e_acusada_e_nao_arredondada(banco_temporario, plano):
    """A conta antiga fazia max(medidas - acertos, 0) e escondia isto."""
    faixa = _faixa(plano, "noite", 2)
    with sessao() as s:
        s.add(EstadoDoDia(data=SEG, faixas_feitas=[{
            "bloco": "noite", "indice": 2, "titulo": faixa.titulo,
            "questoes": 10, "acertos": 12}]))

    with pytest.raises(metricas.ContaInconsistente, match="12 acertos em 10"):
        metricas.do_dia(SEG, plano)


# --- o dia e o de Florianopolis -------------------------------------------------

def test_resposta_as_22h_cai_no_dia_certo(banco_temporario, plano):
    """22h30 aqui e 1h30 do dia seguinte em UTC."""
    _responder(True, datetime(2026, 9, 28, 22, 30, tzinfo=fuso_local()))

    assert metricas.do_dia(SEG, plano).total.questoes == 1
    assert metricas.do_dia(TER, plano).total.questoes == 0


def test_resposta_a_meia_noite_e_do_dia_seguinte(banco_temporario, plano):
    _responder(True, datetime(2026, 9, 29, 0, 5, tzinfo=fuso_local()))

    assert metricas.do_dia(SEG, plano).total.questoes == 0
    assert metricas.do_dia(TER, plano).total.questoes == 1


# --- respostas: o volume ---------------------------------------------------------

def test_a_mesma_questao_em_duas_rodadas_sao_duas_respostas(banco_temporario, plano):
    _responder(False, _as_21h(minuto=1), questao_id=7)
    _responder(True, _as_21h(minuto=2), questao_id=7)

    conta = metricas.do_dia(SEG, plano)

    assert conta.radar.questoes == 2
    assert (conta.radar.acertos, conta.radar.erros) == (1, 1)


# --- mesmo periodo, mesmo numero -------------------------------------------------

def test_o_dia_e_o_mesmo_dentro_de_um_periodo_maior(banco_temporario, plano):
    """A semana soma a mesma lista que o dia: filtrar o periodo pelo dia da o
    numero do dia, e nao um parecido."""
    _o_dia_28(plano)
    _responder(True, _as_21h(TER))

    linhas = metricas.lancamentos(SEG, HOJE, plano)
    do_periodo = metricas.contar(l for l in linhas if l.data == SEG)

    assert do_periodo == metricas.do_dia(SEG, plano)
    assert metricas.contar(linhas).total.questoes == 32


# --- a tela Hoje e o `radar hoje` -------------------------------------------------
#
# No cronograma de verdade, como os outros testes de tela: o 28/09 dele tem as
# mesmas faixas do mini nas mesmas posicoes (Penal, Portugues, Bonus).

def _o_dia_28_de_verdade():
    real = cronograma.carregar()
    _o_dia_28(real)
    return real


def test_a_tela_hoje_mostra_o_28_09_fechado(banco_temporario, monkeypatch):
    from fastapi.testclient import TestClient

    from radar.web.app import app

    _o_dia_28_de_verdade()
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()))

    texto = TestClient(app).get("/hoje?data=2026-09-28").text

    assert ("<b>Questões reais (Qconcursos e provas): 21 questões = 13 acertos "
            "+ 8 erros</b>") in texto
    assert ("Treino de IA no radar: 10 questões = 7 acertos + 3 erros (70%), "
            "não entra no acerto.") in texto
    assert "Total do dia: 31 questões" in texto
    assert "Fiz hoje:" not in texto
    # O treino de IA leva o selo da IA (Etapa 7A): e resposta a questao que
    # a IA escreveu, e ela nunca pode parecer questao da banca.
    assert ('<span aria-hidden="true">🟣</span> Gerado por IA</span> '
            "Treino de IA no radar: 10 questões") in texto


def test_o_selo_de_cada_linha_do_dia_sai_do_dado(banco_temporario, monkeypatch):
    """A tela nao escolhe a cor (Etapa 7A): trocada a origem no dado - o
    recorte da Conta e o Nivel da semana -, o selo troca junto."""
    from fastapi.testclient import TestClient

    from radar.web.app import app

    _o_dia_28_de_verdade()
    # Uma questao real respondida no radar, para a linha "medido no radar"
    # aparecer ao lado do anotado.
    _responder(True, _as_21h(minuto=30), questao_id=99)
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()))
    monkeypatch.setattr(metricas.Conta, "origens",
                        {**metricas.ORIGEM_DO_RECORTE, "radar": "acervo"})
    monkeypatch.setattr(cronograma.Nivel, "origem", "ia")

    texto = TestClient(app).get("/hoje?data=2026-09-28").text

    assert ('<span aria-hidden="true">🔵</span> Estatística do acervo</span> '
            "medido no radar") in texto
    assert '<p class="motivo"><span class="ds-selo ds-selo--ia"' in texto


def test_o_radar_hoje_mostra_a_mesma_linha(banco_temporario):
    from typer.testing import CliRunner

    from radar.cli import app as cli

    _o_dia_28_de_verdade()

    saida = CliRunner().invoke(cli, ["hoje", "--data", "2026-09-28"],
                               env={"COLUMNS": "200"})

    assert saida.exit_code == 0, saida.output
    assert ("Questões reais (Qconcursos e provas): 21 questões = 13 acertos "
            "+ 8 erros") in saida.output
    assert ("Treino de IA no radar: 10 questões = 7 acertos + 3 erros (70%), "
            "não entra no acerto") in saida.output
    assert "Total do dia: 31 questões" in saida.output


# --- mesmo periodo, mesmo numero, em todas as telas --------------------------------
#
# Hoje, Semanas e Minhas materias somam a mesma lista do `metricas`. Com toda
# linha do dia numa materia do edital, o dia, a semana e a soma dos cartoes
# tem que dar EXATAMENTE os mesmos Numeros - acerto, erro, IA e minutos.

def _soma(numeros):
    total = metricas.Numeros()
    for n in numeros:
        total = total + n
    return total


def test_hoje_semanas_e_materias_dao_o_mesmo_numero(banco_temporario):
    from radar.servico import materias, semanas
    from tests.test_materias_na_tela import _anotar as anotar_na_materia
    from tests.test_materias_na_tela import _responder as responder_na_materia
    from tests.test_semanas import _ciclo1, _por_numero

    real = cronograma.carregar()
    anotar_na_materia(real, SEG, "Direito Penal", 11, 6)
    anotar_na_materia(real, SEG, "Língua Portuguesa", 10, 7)
    for n in range(10):
        responder_na_materia("Direito Penal", n < 7, _as_21h(minuto=n), gerada=True)
    responder_na_materia("Língua Portuguesa", False, _as_21h(minuto=20))

    dia = metricas.do_dia(SEG, real).total
    semana = _por_numero(_ciclo1(real, hoje=date(2026, 10, 5)))[1].numeros
    cartoes, _ = materias.montar(real, hoje=date(2026, 10, 5))

    assert dia.questoes == 32
    assert semana == dia
    assert _soma(c.geral for c in cartoes) == dia


def test_o_plano_b_conta_igual_no_dia_na_semana_e_na_materia(banco_temporario):
    """Antes, a tela Hoje contava as faixas do Plano B e a de Semanas montava
    o dia normal - e nao achava check nenhum: as questoes sumiam da semana."""
    from radar.servico import materias, semanas
    from tests.test_semanas import _ciclo1, _por_numero

    real = cronograma.carregar()
    quarta, depois = date(2026, 10, 28), date(2026, 11, 2)
    diario.ativar_plano_b(quarta, 30, plano=real, hoje=depois)
    nivel = diario.nivel_do_dia(real, quarta)
    questoes = cronograma.montar_plano_b(real, quarta, 30, nivel.efetivo).plano_b[1]
    diario.anotar_faixa(quarta, cronograma.BLOCO_DO_PLANO_B, 1, questoes.titulo,
                        questoes=8, acertos=5, plano=real, hoje=depois)

    dia = metricas.do_dia(quarta, real).total
    numero = real.dia(quarta).semana
    semana = _por_numero(_ciclo1(real, hoje=depois))[numero].numeros
    cartoes, _ = materias.montar(real, hoje=depois)
    lep = next(c for c in cartoes if c.nome == questoes.materia)

    assert (dia.questoes, dia.acertos) == (8, 5)
    assert semana == dia
    assert lep.geral == dia


# --- questoes: o acumulado ----------------------------------------------------------

def test_duas_respostas_e_uma_questao(banco_temporario, plano):
    """Errei e depois acertei a mesma questao: o dia conta as duas RESPOSTAS,
    o acumulado conta uma QUESTAO, pela ultima resposta (acertou)."""
    from tests.test_espacada import _questao

    questao = _questao(1)
    _responder(False, _as_21h(minuto=1), questao_id=questao)
    _responder(True, _as_21h(minuto=2), questao_id=questao)

    assert metricas.do_dia(SEG, plano).radar.questoes == 2
    total = metricas.acumulado()
    assert (total.respondidas, total.acertos) == (1, 1)


def test_meu_foco_e_home_leem_o_mesmo_acumulado(banco_temporario,
                                                 com_quadro_do_edital):
    """Recorte *medido no radar*, ultima resposta de cada questao: o Meu foco
    e a home dizem o mesmo numero que o metricas."""
    from radar import foco
    from radar.regioes import normalizar
    from radar.servico import inicio
    from tests.test_home import _acervo
    from tests.test_home import _responder as responder_rodada

    _acervo(25, "Direito Penal")
    responder_rodada(10, 15)

    (penal,) = metricas.acumulado_por_materia()
    meu_foco = next(d for nome, d in foco.montar().acerto_por_materia.items()
                    if normalizar(nome) == normalizar("Direito Penal"))
    home = inicio.montar()

    assert (penal.respondidas, penal.acertos) == (25, 10)
    assert (meu_foco.respondidas, meu_foco.acertos) == (25, 10)
    assert home.revisar.respondidas == metricas.acumulado().respondidas == 25
    assert ("Direito Penal", 40.0, 25) in home.revisar.materias_fracas


def test_nenhum_template_soma_contagem():
    """CLAUDE.md: "template nenhum soma". A auditoria de 04/10 achou quatro
    contas em template (Meu desempenho, Macetes, a rodada compilada e a
    ficha); foram para o Python. Este teste nao deixa voltar: nada de
    `| sum(`, nada de `set x = contagem + contagem` e nada de
    `{{ contagem - contagem }}` num template - a ultima escapou ate a
    decisao 128 (o "faltarão" do simulado), porque so o `set` era olhado."""
    import re
    from pathlib import Path

    pasta = Path(__file__).resolve().parents[1] / "src" / "radar" / "web" / "templates"
    contagem = (r"(questoes|acertos|erros|respondidas|total|com_consulta|"
                r"sem_resultado|pedidas|entregues|disponiveis|reais)")
    proibido = [
        re.compile(r"\|\s*sum\("),
        re.compile(r"\{%-?\s*set\s+\w+\s*=[^%]*\b" + contagem + r"\b[^%~]*\s[-+]\s"),
        re.compile(r"\{\{[^}]*\b" + contagem + r"\b\s*[-+]\s*[\w(]"),
        re.compile(r"\{\{[^}]*[\w)]\s*[-+]\s*[\w.]*\b" + contagem + r"\b"),
        # A ficha contava as questoes reais pelo tamanho da lista.
        re.compile(r"questoes_reais\s*\|\s*length"),
        # Subtrair tamanhos de listas de QUESTOES; "e mais N assuntos" na tela
        # e apresentacao de lista, e nao contagem de questao.
        re.compile(r"questoes\w*\s*\|\s*length\s*\)?\s*[-+]\s"),
    ]
    achados = [f"{arquivo.name}:{n}: {linha.strip()[:90]}"
               for arquivo in sorted(pasta.glob("*.html"))
               for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1)
               if any(p.search(linha) for p in proibido)]
    assert achados == []
