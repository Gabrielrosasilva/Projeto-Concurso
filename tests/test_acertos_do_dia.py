"""Acertos na propria faixa, e a conta do dia (etapa E2).

As regras que estes testes seguram, e elas valem para o radar inteiro
(docs/decisoes.md):

  * VOLUME soma tudo - faixas do plano, estudo extra e o que eu respondi dentro
    do radar;
  * o ACERTO tambem soma as tres, e a tela mostra de onde ele vem;
  * a comparacao com a META usa so questao SEM CONSULTA;
  * questao escrita por IA conta no volume e em acerto nenhum.

O cronograma usado e o mini (tests/fixtures), e o relogio fica parado: o ciclo
de verdade comeca depois do dia em que isto foi escrito.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from radar import cronograma, servico
from radar.cli import app as cli
from radar.db import sessao
from radar.models import RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import metricas
from radar.util import fuso_local
from radar.web.app import app

MINI = Path(__file__).parent / "fixtures" / "cronograma_mini.yml"
SEG = date(2026, 9, 28)
HOJE = date(2026, 10, 3)


@pytest.fixture
def plano():
    return cronograma.carregar(MINI)


@pytest.fixture
def cliente(banco_temporario, monkeypatch):
    """A tela, no cronograma de verdade, com o relogio parado em 30/09.

    O de verdade, e nao o mini, pelo mesmo motivo dos outros testes de tela: a
    tela le tambem o alvo, as leis e o perfil, e trocar a pasta de config
    inteira por causa de um arquivo esconderia mais do que mostraria.
    """
    monkeypatch.setattr(
        diario, "agora_local",
        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()),
    )
    return TestClient(app)


def _faixa_real(bloco, indice, data=SEG):
    """A faixa do cronograma de verdade, montada no nivel 1 da semana 1."""
    return getattr(cronograma.montar_dia(cronograma.carregar(), data, 1), bloco)[indice]


def _faixa(plano, bloco, indice, data=SEG):
    dia = cronograma.montar_dia(plano, data, 1)
    return getattr(dia, bloco)[indice]


def _dia_montado(plano, data=SEG):
    return cronograma.montar_dia(plano, data, 1)


def _totais(plano, data=SEG):
    """A conta do dia, pela fonte unica (Etapa 1C)."""
    return metricas.do_dia(data, plano)


# --- o check com os numeros ----------------------------------------------------

def test_anotar_a_faixa_guarda_fiz_acertei_e_o_resto(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    assert diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=25,
                               acertos=18, consulta=True, plano=plano, hoje=HOJE)

    (check,) = diario.estado_do_dia(SEG).faixas_feitas
    assert check["questoes"] == 25
    assert check["acertos"] == 18
    assert check["consulta"] is True
    assert check["materia"] == faixa.materia
    assert check["assunto"] == faixa.titulo
    # Os minutos sao os da faixa MONTADA, com o nivel do dia aplicado.
    assert check["minutos"] == faixa.duracao


def test_fiz_mais_questoes_do_que_o_plano_pedia(banco_temporario, plano):
    """Mesmo tema, so mais questoes: 25 no lugar das 15 do plano."""
    faixa = _faixa(plano, "noite", 0)
    assert faixa.questoes == 15
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=25, acertos=20,
                        plano=plano, hoje=HOJE)
    assert _totais(plano).total.questoes == 25


def test_acertei_vazio_conta_no_volume_e_nao_no_acerto(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=15, acertos="",
                        plano=plano, hoje=HOJE)

    totais = _totais(plano)
    assert totais.total.questoes == 15
    assert totais.total.medidas == 0
    assert totais.total.porcentagem is None
    valores = diario.valores_das_faixas(_dia_montado(plano), diario.estado_do_dia(SEG))
    assert valores[("noite", 0)].porcentagem is None


def test_corrigir_a_faixa_troca_os_numeros_sem_duplicar(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=15, acertos=9,
                        plano=plano, hoje=HOJE)
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=15, acertos=11,
                        plano=plano, hoje=HOJE)

    checks = diario.estado_do_dia(SEG).faixas_feitas
    assert len(checks) == 1
    assert checks[0]["acertos"] == 11


def test_desmarcar_tira_o_check_e_os_numeros(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=15, acertos=9,
                        plano=plano, hoje=HOJE)
    assert diario.desmarcar_faixa(SEG, "noite", 0, faixa.titulo,
                                  plano=plano, hoje=HOJE) is False
    assert diario.estado_do_dia(SEG).faixas_feitas == []
    assert _totais(plano).vazio


def test_acertos_maior_que_as_questoes_e_recusado(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    with pytest.raises(diario.RegistroInvalido, match="maior que as questões"):
        diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=10, acertos=12,
                            plano=plano, hoje=HOJE)


def test_acertos_sem_questoes_e_recusado(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    with pytest.raises(diario.RegistroInvalido, match="diga quantas"):
        diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes="", acertos=5,
                            plano=plano, hoje=HOJE)


def test_faixa_que_nao_e_de_questoes_nao_aceita_acerto(banco_temporario, plano):
    teoria = _faixa(plano, "manha", 0)
    assert not cronograma.tem_acerto(teoria)
    with pytest.raises(diario.RegistroInvalido, match="não é de questões"):
        diario.anotar_faixa(SEG, "manha", 0, teoria.titulo, questoes=10,
                            plano=plano, hoje=HOJE)


# --- a caixa "com consulta" ---------------------------------------------------

def test_a_aprendizagem_de_direito_vem_com_consulta_marcada(plano):
    """O detalhe dela diz "PODE consultar a lei": ela treina, nao mede."""
    direito = _faixa(plano, "noite", 0)
    assert direito.rampa == "direito"
    assert cronograma.consulta_por_padrao(direito) is True


@pytest.mark.parametrize("bloco, indice", [("noite", 2), ("pos22", 1)])
def test_as_outras_faixas_vem_sem_consulta(plano, bloco, indice):
    assert cronograma.consulta_por_padrao(_faixa(plano, bloco, indice)) is False


def test_o_padrao_vale_quando_eu_nao_digo_nada(banco_temporario, plano):
    direito = _faixa(plano, "noite", 0)
    diario.marcar_faixa(SEG, "noite", 0, direito.titulo, plano=plano, hoje=HOJE)
    (check,) = diario.estado_do_dia(SEG).faixas_feitas
    assert check["consulta"] is True


def test_com_consulta_fica_fora_da_conta_da_meta(banco_temporario, plano):
    direito = _faixa(plano, "noite", 0)
    portugues = _faixa(plano, "noite", 2)
    diario.anotar_faixa(SEG, "noite", 0, direito.titulo, questoes=15, acertos=12,
                        consulta=True, plano=plano, hoje=HOJE)
    diario.anotar_faixa(SEG, "noite", 2, portugues.titulo, questoes=10, acertos=7,
                        consulta=False, plano=plano, hoje=HOJE)

    totais = _totais(plano)
    assert (totais.total.questoes, totais.total.acertos) == (25, 19)
    # A meta se compara so com o que eu fiz sem a lei aberta.
    assert (totais.sem_consulta.questoes, totais.sem_consulta.acertos) == (10, 7)


# --- o check antigo, sem os campos novos --------------------------------------

def test_check_antigo_e_preenchido_pelo_plano(banco_temporario, plano):
    """Os checks gravados antes desta etapa tinham so a posicao e o titulo."""
    faixa = _faixa(plano, "noite", 0)
    with sessao() as s:
        from radar.models import EstadoDoDia
        s.add(EstadoDoDia(data=SEG, faixas_feitas=[
            {"bloco": "noite", "indice": 0, "titulo": faixa.titulo}]))

    valores = diario.valores_das_faixas(_dia_montado(plano), diario.estado_do_dia(SEG))
    feita = valores[("noite", 0)]
    assert feita.do_plano is True
    assert feita.questoes == faixa.questoes      # o que o plano pedia
    assert feita.acertos is None                 # que eu nao anotei
    assert feita.minutos == faixa.duracao
    assert feita.materia == faixa.materia
    assert _totais(plano).total.questoes == faixa.questoes


# --- o simulado misto ---------------------------------------------------------

def test_o_simulado_misto_conta_no_geral_e_em_nenhuma_materia(banco_temporario, plano):
    """Sabado tem simulado de varias materias: o total nao e de nenhuma delas."""
    sabado = date(2026, 10, 3)
    simulado = _faixa(plano, "noite", 0, sabado)
    assert simulado.tipo == "simulado"
    assert simulado.materia is None

    diario.anotar_faixa(sabado, "noite", 0, simulado.titulo, questoes=30,
                        acertos=21, plano=plano, hoje=HOJE)

    (check,) = diario.estado_do_dia(sabado).faixas_feitas
    assert check["materia"] is None
    totais = _totais(plano, sabado)
    assert (totais.total.questoes, totais.total.acertos) == (30, 21)


# --- o total do dia -----------------------------------------------------------

def _resposta(acertou, quando, gerada=False):
    with sessao() as s:
        simulado = Simulado(filtros={})
        s.add(simulado)
        s.flush()
        s.add(RespostaDeSimulado(
            simulado_id=simulado.id, questao_id=1, gerada=gerada, ordem=1,
            escolhida="a", acertou=acertou, respondida_em=quando,
        ))


def test_o_total_soma_faixa_extra_e_radar(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=15, acertos=11,
                        plano=plano, hoje=HOJE)
    servico.extra.anotar(data=SEG, o_que="questoes", materia="Direito Penal",
                         minutos=30, questoes=10, acertos=8, onde="qconcursos",
                         plano=plano, hoje=HOJE)
    _resposta(True, datetime(2026, 9, 28, 21, 0, tzinfo=fuso_local()))
    _resposta(False, datetime(2026, 9, 28, 21, 5, tzinfo=fuso_local()))

    totais = _totais(plano)
    assert totais.total.questoes == 27          # 15 + 10 + 2
    assert totais.total.acertos == 20           # 11 + 8 + 1
    assert totais.total.erros == 7
    assert totais.faixas.minutos + totais.extra.minutos == totais.minutos
    assert totais.extra.minutos == 30


def test_o_acerto_do_radar_e_do_anotado_aparecem_separados(banco_temporario, plano):
    faixa = _faixa(plano, "noite", 0)
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=10, acertos=5,
                        plano=plano, hoje=HOJE)
    _resposta(True, datetime(2026, 9, 28, 21, 0, tzinfo=fuso_local()))

    totais = _totais(plano)
    assert totais.radar.porcentagem == 100
    assert totais.anotado.porcentagem == 50


def test_questao_de_ia_conta_no_volume_e_em_acerto_nenhum(banco_temporario, plano):
    _resposta(True, datetime(2026, 9, 28, 21, 0, tzinfo=fuso_local()), gerada=True)
    _resposta(True, datetime(2026, 9, 28, 21, 1, tzinfo=fuso_local()))

    totais = _totais(plano)
    assert totais.total.ia == 1
    assert totais.total.questoes == 2          # o tempo foi gasto nas duas
    assert totais.total.medidas == 1           # so a real mede
    assert totais.radar.acertos == 1


def test_a_resposta_da_noite_nao_vaza_para_o_dia_seguinte(banco_temporario, plano):
    """22h em Florianopolis e 1h do dia seguinte em UTC."""
    _resposta(True, datetime(2026, 9, 28, 22, 30, tzinfo=fuso_local()))
    assert _totais(plano, SEG).radar.questoes == 1
    assert _totais(plano, date(2026, 9, 29)).radar.questoes == 0


def test_dia_sem_nada_tem_total_vazio(banco_temporario, plano):
    assert _totais(plano).vazio


# --- a tela -------------------------------------------------------------------

def test_a_faixa_de_questoes_tem_o_formulario_e_a_de_teoria_nao(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert 'name="questoes"' in texto
    assert "com consulta" in texto
    assert 'class="circulo"' in texto          # a teoria continua com o circulo


def test_anotar_pela_tela_e_voltar_para_a_faixa(cliente):
    faixa = _faixa_real("noite", 0)
    resposta = cliente.post("/hoje/faixa/questoes", data={
        "data": "2026-09-28", "bloco": "noite", "indice": "0",
        "titulo": faixa.titulo, "questoes": "15", "acertos": "11",
        "consulta": "1"}, follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje?data=2026-09-28#faixa-noite-0"
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "11" in texto and "de 15" in texto
    assert "73%" in texto                       # 11 de 15
    assert "corrigir os números" in texto
    assert "desmarcar" in texto


def test_desmarcar_pela_tela(cliente):
    faixa = _faixa_real("noite", 0)
    cliente.post("/hoje/faixa/questoes", data={
        "data": "2026-09-28", "bloco": "noite", "indice": "0",
        "titulo": faixa.titulo, "questoes": "15", "acertos": "11"})
    cliente.post("/hoje/faixa/questoes", data={
        "data": "2026-09-28", "bloco": "noite", "indice": "0",
        "titulo": faixa.titulo, "desmarcar": "1"})

    assert diario.estado_do_dia(SEG).faixas_feitas == []
    assert "corrigir os números" not in cliente.get("/hoje?data=2026-09-28").text


def test_a_recusa_da_faixa_aparece_na_tela(cliente):
    faixa = _faixa_real("noite", 0)
    resposta = cliente.post("/hoje/faixa/questoes", data={
        "data": "2026-09-28", "bloco": "noite", "indice": "0",
        "titulo": faixa.titulo, "questoes": "10", "acertos": "12"})
    assert resposta.status_code == 400
    assert "maior que as questões feitas" in resposta.text


def test_a_tela_mostra_a_linha_do_total(cliente):
    faixa = _faixa_real("noite", 0)
    cliente.post("/hoje/faixa/questoes", data={
        "data": "2026-09-28", "bloco": "noite", "indice": "0",
        "titulo": faixa.titulo, "questoes": "15", "acertos": "11"})
    cliente.post("/hoje/extra", data={
        "data": "2026-09-28", "o_que": "questoes", "materia": "Direito Penal",
        "minutos": "30", "questoes": "20", "acertos": "16", "onde": "qconcursos"})

    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "Fiz hoje:</b> 35 questões = 27 acertos + 8 erros" in texto
    assert "do plano + 30 min extra" in texto
    # Com erro no dia, o atalho para o caderno da etapa E1.
    assert "anotar os erros" in texto


def test_sem_erro_nenhum_nao_ha_atalho_para_o_caderno(cliente):
    faixa = _faixa_real("noite", 0)
    cliente.post("/hoje/faixa/questoes", data={
        "data": "2026-09-28", "bloco": "noite", "indice": "0",
        "titulo": faixa.titulo, "questoes": "15", "acertos": "15"})
    assert "anotar os erros" not in cliente.get("/hoje?data=2026-09-28").text


def test_os_campos_digitados_sairam_da_tela(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert 'name="questoes_feitas"' not in texto
    assert 'name="acertos" min="0" inputmode="numeric" value=""' not in texto


# --- o comando ----------------------------------------------------------------

def test_radar_hoje_mostra_o_acerto_da_faixa(banco_temporario, plano, tmp_path,
                                             monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "cronograma.yml").write_text(MINI.read_text(encoding="utf-8"),
                                               encoding="utf-8")
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(config_dir))
    faixa = _faixa(plano, "noite", 0)
    diario.anotar_faixa(SEG, "noite", 0, faixa.titulo, questoes=15, acertos=11,
                        consulta=True, plano=plano, hoje=HOJE)
    servico.extra.anotar(data=SEG, o_que="lei_seca", materia="Direito Penal",
                         assunto="Art. 33", minutos=40, onde="outro",
                         plano=plano, hoje=HOJE)

    saida = CliRunner().invoke(cli, ["hoje", "--data", "2026-09-28"],
                              env={"COLUMNS": "200"})

    assert saida.exit_code == 0, saida.output
    assert "11/15" in saida.output
    assert "73%" in saida.output
    assert "com consulta" in saida.output
    assert "Estudo extra" in saida.output
    assert "Lei seca · Direito Penal · Art. 33 · 40 min" in saida.output
    assert "Fiz hoje:" in saida.output
