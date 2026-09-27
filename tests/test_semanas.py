"""A tela de Semanas: como eu fui em cada semana, por ciclo (etapa E3).

Toda a conta e do `servico.semanas`, e e nele que estes testes batem: a tela so
mostra. Os numeros seguem as regras da E2 - volume e acerto somam faixas do
plano, estudo extra e respostas no radar, e a meta usa so questao sem consulta.

O cronograma e o de verdade (o Ciclo 1 inteiro esta nele) e o relogio fica
parado: o ciclo comeca depois do dia em que isto foi escrito.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import acervo, cronograma, servico
from radar.db import sessao
from radar.models import NotaDaSemana, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import semanas as tela
from radar.util import fuso_local
from radar.web.app import app

# As quatro primeiras semanas do Ciclo 1, pelas segundas-feiras.
S1 = date(2026, 9, 28)
S2 = date(2026, 10, 5)
S3 = date(2026, 10, 12)
S4 = date(2026, 10, 19)


@pytest.fixture
def plano():
    return cronograma.carregar()


@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    """A tela, com o relogio parado numa terca da semana 4."""
    monkeypatch.setattr(
        diario, "agora_local",
        lambda: datetime(2026, 10, 20, 20, 0, tzinfo=fuso_local()),
    )
    return TestClient(app)


def _dias_uteis(segunda):
    return [segunda + timedelta(days=i) for i in range(6)]


def _semana_completa(plano, segunda, meta="ideal", hoje=None):
    """Marca os seis dias da semana com a mesma meta."""
    for dia in _dias_uteis(segunda):
        diario.registrar(dia, meta, plano=plano, hoje=hoje or date(2026, 11, 7))


def _anotar_faixa(plano, dia, questoes, acertos, consulta=False, bloco="noite",
                  indice=0):
    montado = cronograma.montar_dia(plano, dia, diario.nivel_do_dia(plano, dia).efetivo)
    faixa = getattr(montado, bloco)[indice]
    diario.anotar_faixa(dia, bloco, indice, faixa.titulo, questoes=questoes,
                        acertos=acertos, consulta=consulta, plano=plano,
                        hoje=date(2026, 11, 7))


def _resposta(acertou, quando, gerada=False):
    with sessao() as s:
        simulado = Simulado(filtros={})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=simulado.id, questao_id=1, gerada=gerada, ordem=1,
            escolhida="a", acertou=acertou, respondida_em=quando,
        ))


def _ciclo1(plano, hoje):
    (ciclo,) = [c for c in tela.montar(plano, hoje=hoje) if c.nome == "Ciclo 1"]
    return ciclo


def _por_numero(ciclo):
    return {s.numero: s for s in ciclo.semanas}


# --- o agrupamento ------------------------------------------------------------

def test_as_semanas_saem_agrupadas_no_ciclo_do_mapa(banco_temporario, plano):
    ciclos = tela.montar(plano, hoje=S4 + timedelta(days=1))
    assert [c.nome for c in ciclos] == ["Ciclo 1"]
    assert ciclos[0].atual is True
    assert ciclos[0].terminou is False
    assert [s.numero for s in ciclos[0].semanas] == [1, 2, 3, 4]


def test_semana_futura_nao_aparece(banco_temporario, plano):
    ciclo = _ciclo1(plano, hoje=S2 + timedelta(days=2))
    assert [s.numero for s in ciclo.semanas] == [1, 2]


def test_a_semana_corrente_aparece_em_andamento(banco_temporario, plano):
    ciclo = _ciclo1(plano, hoje=S4 + timedelta(days=1))
    por_numero = _por_numero(ciclo)
    assert por_numero[4].em_andamento is True
    assert por_numero[3].em_andamento is False


def test_antes_do_ciclo_comecar_nao_ha_semana(banco_temporario, plano):
    assert tela.montar(plano, hoje=date(2026, 9, 1)) == []


def test_o_ciclo_que_terminou_vem_marcado_com_o_resumo(banco_temporario, plano):
    """Em dezembro o Ciclo 1 acabou: ele fecha e vale a linha de resumo."""
    _semana_completa(plano, S1)
    _anotar_faixa(plano, S1, 15, 12)

    ciclo = _ciclo1(plano, hoje=date(2026, 12, 1))
    assert ciclo.terminou is True
    assert ciclo.atual is False
    assert ciclo.resumo.dias_completos == 6
    assert ciclo.resumo.questoes == 15
    assert ciclo.resumo.porcentagem == 80


# --- dias completos -----------------------------------------------------------

def test_semana_completa(banco_temporario, plano):
    _semana_completa(plano, S1)
    semana = _por_numero(_ciclo1(plano, hoje=S2))[1]

    assert semana.dias_completos == 6
    assert semana.dias_no_plano == 6
    assert semana.ruim is False
    assert semana.sequencia == 6


def test_semana_ruim(banco_temporario, plano):
    """Dois dias zerados e um sem marcar: a semana nao e completa nem boa."""
    dias = _dias_uteis(S1)
    for dia in dias[:3]:
        diario.registrar(dia, "ideal", plano=plano, hoje=date(2026, 11, 7))
    for dia in dias[3:5]:
        diario.registrar(dia, "nao_fiz", plano=plano, hoje=date(2026, 11, 7))

    semana = _por_numero(_ciclo1(plano, hoje=S2))[1]
    assert semana.dias_completos == 3
    assert semana.zerados == 2
    assert semana.sem_marcacao == 1
    assert semana.ruim is True


def test_feriado_na_minima_conta_como_completo(banco_temporario, plano):
    """A mesma regra do gatilho: cumprir o minimo no feriado nao derruba."""
    feriado = date(2026, 10, 12)          # segunda, feriado no cronograma real
    assert plano.dia(feriado).feriado
    diario.registrar(feriado, "minima", plano=plano, hoje=date(2026, 11, 7))

    semana = _por_numero(_ciclo1(plano, hoje=S4))[3]
    assert semana.dias_completos == 1


# --- volume e acerto ----------------------------------------------------------

def test_as_questoes_somam_faixas_extras_e_radar(banco_temporario, plano):
    _anotar_faixa(plano, S1, 15, 11)
    servico.extra.anotar(data=S1, o_que="questoes", materia="Direito Penal",
                         minutos=30, questoes=10, acertos=8, onde="qconcursos",
                         plano=plano, hoje=date(2026, 11, 7))
    _resposta(True, datetime(2026, 9, 28, 21, 0, tzinfo=fuso_local()))
    _resposta(False, datetime(2026, 9, 29, 21, 0, tzinfo=fuso_local()))

    semana = _por_numero(_ciclo1(plano, hoje=S2))[1]
    assert semana.numeros.questoes == 27          # 15 + 10 + 2
    assert semana.numeros.acertos == 20           # 11 + 8 + 1
    assert semana.numeros.erros == 7
    assert semana.numeros.porcentagem == 74


def test_as_horas_somam_faixas_e_extras(banco_temporario, plano):
    """O radar nao cronometra simulado: ele entra em questao, nao em tempo."""
    _anotar_faixa(plano, S1, 15, 11)
    montado = cronograma.montar_dia(plano, S1, 1)
    minutos_da_faixa = montado.noite[0].duracao
    servico.extra.anotar(data=S1, o_que="teoria", minutos=45, onde="outro",
                         plano=plano, hoje=date(2026, 11, 7))
    _resposta(True, datetime(2026, 9, 28, 21, 0, tzinfo=fuso_local()))

    semana = _por_numero(_ciclo1(plano, hoje=S2))[1]
    assert semana.minutos == minutos_da_faixa + 45


def test_a_meta_olha_so_o_que_foi_sem_consulta(banco_temporario, plano):
    _anotar_faixa(plano, S1, 20, 18, consulta=True)
    _anotar_faixa(plano, S1 + timedelta(days=1), 10, 6, consulta=False)

    semana = _por_numero(_ciclo1(plano, hoje=S2))[1]
    assert semana.numeros.porcentagem == 80           # 24 de 30
    assert semana.sem_consulta.porcentagem == 60      # 6 de 10


def test_questao_de_ia_conta_no_volume_e_em_acerto_nenhum(banco_temporario, plano):
    _resposta(True, datetime(2026, 9, 28, 21, 0, tzinfo=fuso_local()), gerada=True)
    _resposta(False, datetime(2026, 9, 28, 21, 1, tzinfo=fuso_local()))

    semana = _por_numero(_ciclo1(plano, hoje=S2))[1]
    assert semana.geradas == 1
    assert semana.numeros.questoes == 2
    assert semana.numeros.medidas == 1
    assert semana.numeros.porcentagem == 0


def test_o_plano_b_da_semana_e_contado(banco_temporario, plano):
    diario.ativar_plano_b(S1, 30, plano=plano, hoje=date(2026, 11, 7))
    diario.ativar_plano_b(S1 + timedelta(days=2), 60, plano=plano,
                          hoje=date(2026, 11, 7))

    assert _por_numero(_ciclo1(plano, hoje=S2))[1].plano_b == 2


def test_os_erros_do_caderno_entram_na_semana(banco_temporario, plano):
    servico.erros.anotar(data_estudo=S1, materia="LEP", motivo="pegadinha",
                         regra="Conta da prisão.", hoje=S1)
    servico.erros.anotar(data_estudo=S2, materia="LEP", motivo="chutei",
                         regra="Outra regra.", hoje=S2)

    por_numero = _por_numero(_ciclo1(plano, hoje=S3))
    assert por_numero[1].erros_anotados == 1
    assert por_numero[2].erros_anotados == 1


# --- as setas -----------------------------------------------------------------

def test_as_setas_comparam_com_a_semana_anterior(banco_temporario, plano):
    _anotar_faixa(plano, S1, 20, 16)          # 80%
    _anotar_faixa(plano, S2, 55, 42)          # 76%

    por_numero = _por_numero(_ciclo1(plano, hoje=S3))
    semana2 = por_numero[2]
    assert semana2.comparacao["questoes"].diferenca == 35
    assert semana2.comparacao["questoes"].melhor is True
    assert semana2.comparacao["acerto"].diferenca == -4
    assert semana2.comparacao["acerto"].melhor is False
    # A primeira semana do ciclo nao tem com o que comparar.
    assert por_numero[1].comparacao == {}


def test_menos_erros_e_seta_verde(banco_temporario, plano):
    _anotar_faixa(plano, S1, 20, 10)          # 10 erros
    _anotar_faixa(plano, S2, 20, 18)          # 2 erros

    semana2 = _por_numero(_ciclo1(plano, hoje=S3))[2]
    assert semana2.comparacao["erros"].diferenca == -8
    assert semana2.comparacao["erros"].melhor is True


def test_numero_igual_nao_ganha_seta(banco_temporario, plano):
    _anotar_faixa(plano, S1, 20, 16)
    _anotar_faixa(plano, S2, 20, 16)

    semana2 = _por_numero(_ciclo1(plano, hoje=S3))[2]
    assert "questoes" not in semana2.comparacao
    assert "acerto" not in semana2.comparacao


def test_semana_sem_acerto_medido_nao_compara_acerto(banco_temporario, plano):
    """Comparar 76% com o nada daria uma flecha inventada."""
    _anotar_faixa(plano, S1, 20, 16)
    _anotar_faixa(plano, S2, 30, None)

    semana2 = _por_numero(_ciclo1(plano, hoje=S3))[2]
    assert "acerto" not in semana2.comparacao
    assert semana2.comparacao["questoes"].diferenca == 10


# --- a melhor semana ----------------------------------------------------------

def test_a_melhor_semana_e_a_de_mais_dias_completos(banco_temporario, plano):
    _semana_completa(plano, S1)                              # 6 completos
    for dia in _dias_uteis(S2)[:3]:
        diario.registrar(dia, "ideal", plano=plano, hoje=date(2026, 11, 7))

    por_numero = _por_numero(_ciclo1(plano, hoje=S3))
    assert por_numero[1].melhor is True
    assert por_numero[2].melhor is False


def test_no_empate_de_dias_ganha_quem_fez_mais_questoes(banco_temporario, plano):
    _semana_completa(plano, S1)
    _semana_completa(plano, S2)
    _anotar_faixa(plano, S1, 20, 15)
    _anotar_faixa(plano, S2, 60, 40)

    por_numero = _por_numero(_ciclo1(plano, hoje=S3))
    assert por_numero[2].melhor is True
    assert por_numero[1].melhor is False


def test_a_semana_em_andamento_nao_concorre(banco_temporario, plano):
    """Ela nao acabou: comparar com semana fechada seria competicao torta."""
    _semana_completa(plano, S1)
    for dia in _dias_uteis(S2)[:2]:
        diario.registrar(dia, "ideal", plano=plano, hoje=date(2026, 10, 7))

    por_numero = _por_numero(_ciclo1(plano, hoje=S2 + timedelta(days=2)))
    assert por_numero[2].em_andamento is True
    assert por_numero[2].melhor is False
    assert por_numero[1].melhor is True


def test_sem_dia_completo_nenhum_nao_ha_campea(banco_temporario, plano):
    ciclo = _ciclo1(plano, hoje=S2)
    assert all(not s.melhor for s in ciclo.semanas)


# --- a reflexao ---------------------------------------------------------------

def test_anotar_a_reflexao(banco_temporario):
    nota = tela.anotar(S1, funcionou="Acordei cedo.", ajustar="Dormir antes.")
    assert (nota.funcionou, nota.ajustar) == ("Acordei cedo.", "Dormir antes.")
    assert tela.nota(S1).funcionou == "Acordei cedo."


def test_corrigir_a_reflexao_nao_cria_outra(banco_temporario):
    tela.anotar(S1, funcionou="Primeiro texto.")
    tela.anotar(S1, funcionou="Texto corrigido.", ajustar="E um ajuste.")

    with sessao() as s:
        (guardada,) = s.scalars(select(NotaDaSemana)).all()
    assert guardada.funcionou == "Texto corrigido."
    assert guardada.ajustar == "E um ajuste."


def test_texto_vazio_apaga_o_campo(banco_temporario):
    tela.anotar(S1, funcionou="Alguma coisa.")
    assert tela.anotar(S1, funcionou="   ").funcionou is None


def test_a_reflexao_e_de_uma_segunda(banco_temporario):
    with pytest.raises(diario.RegistroInvalido, match="segunda-feira"):
        tela.anotar(date(2026, 9, 30))


def test_a_reflexao_aparece_na_semana(banco_temporario, plano):
    tela.anotar(S1, funcionou="A manhã rendeu.")
    semana = _por_numero(_ciclo1(plano, hoje=S2))[1]
    assert semana.nota.funcionou == "A manhã rendeu."


def test_exportar_e_importar_a_reflexao(banco_temporario, tmp_path):
    tela.anotar(S1, funcionou="Funcionou.", ajustar="Ajustar.")
    arquivo = tmp_path / "notas_semana.json"

    assert acervo.exportar_notas(arquivo) == 1
    with sessao() as s:
        s.delete(s.scalars(select(NotaDaSemana)).one())
    assert acervo.importar_notas(arquivo) == 1

    with sessao() as s:
        voltou = s.scalars(select(NotaDaSemana)).one()
    assert (voltou.inicio, voltou.funcionou, voltou.ajustar) == (S1, "Funcionou.",
                                                                "Ajustar.")
    # Importar de novo nao muda nada.
    assert acervo.importar_notas(arquivo) == 0


def test_o_arquivo_das_notas_entra_no_sincronizar():
    from radar.cli import ARQUIVOS_DO_RADAR
    assert "data/notas_semana.json" in ARQUIVOS_DO_RADAR


# --- a tela -------------------------------------------------------------------

def test_a_tela_abre_com_as_semanas_e_as_subabas(cliente):
    texto = cliente.get("/semanas").text
    assert "<h1>Semanas</h1>" in texto
    assert 'href="/hoje"' in texto and 'href="/erros"' in texto
    assert "Semana 1" in texto and "Semana 4" in texto
    assert "em andamento" in texto
    # A semana 5 ainda nao comecou.
    assert "Semana 5" not in texto


def test_a_tela_hoje_tem_o_link_para_as_semanas(cliente):
    texto = cliente.get("/hoje?data=2026-10-20").text
    assert "ver todas as semanas" in texto
    assert 'href="/semanas"' in texto


def test_o_grafico_sai_em_css_sem_javascript(cliente, plano):
    _anotar_faixa(plano, S1, 40, 30)
    texto = cliente.get("/semanas").text

    assert "Questões por semana" in texto
    assert 'class="barra' in texto
    assert "height:100%" in texto          # a semana 1 e a maior
    assert "75%" in texto                  # 30 de 40, em cima da barra
    assert "<script" not in texto.lower()


def test_a_tela_mostra_o_sem_consulta_e_as_setas(cliente, plano):
    _anotar_faixa(plano, S1, 20, 16, consulta=True)
    _anotar_faixa(plano, S2, 30, 20, consulta=False)
    texto = cliente.get("/semanas").text

    assert "sem consulta:" in texto
    assert "↑" in texto or "↓" in texto


def test_escrever_a_reflexao_pela_tela(cliente):
    resposta = cliente.post("/semanas/nota", data={
        "inicio": S1.isoformat(), "funcionou": "Acordei cedo todos os dias.",
        "ajustar": "Menos celular à noite."}, follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == f"/semanas#semana-{S1.isoformat()}"
    texto = cliente.get("/semanas").text
    assert "Acordei cedo todos os dias." in texto
    assert "Menos celular à noite." in texto


def test_reflexao_em_dia_que_nao_e_segunda_avisa_na_tela(cliente):
    resposta = cliente.post("/semanas/nota", data={"inicio": "2026-09-30",
                                                   "funcionou": "x"})
    assert resposta.status_code == 200
    assert "segunda-feira" in resposta.text


def test_o_ciclo_fechado_vem_num_details_com_o_resumo(cliente, plano, monkeypatch):
    """Em marco, o Ciclo 1 ja acabou: ele fica fechado, com a linha de resumo."""
    _semana_completa(plano, S1)
    _anotar_faixa(plano, S1, 50, 36)
    monkeypatch.setattr(
        diario, "agora_local",
        lambda: datetime(2027, 3, 10, 20, 0, tzinfo=fuso_local()),
    )

    texto = cliente.get("/semanas").text
    assert "<details class=\"ciclo-fechado\">" in texto
    assert "6 dias completos" in texto
    assert "50 questões" in texto
    assert "72% de acerto" in texto
