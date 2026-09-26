"""A tela Hoje (/hoje) e o cartao do cronograma na home.

Le o config/cronograma.yml de verdade: o que se testa e a tela, e o arquivo
real e o dado fixo mais fiel que ha. O relogio e parado pelo agora_local,
porque o ciclo real comeca depois do dia em que estes testes foram escritos.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from radar import servico
from radar.util import fuso_local
from radar.web.app import app


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def _parar_o_relogio(monkeypatch, *quando):
    momento = datetime(*quando, tzinfo=fuso_local())
    monkeypatch.setattr(servico.cronograma, "agora_local", lambda: momento)


# --- o dia -------------------------------------------------------------------

def test_o_primeiro_dia(cliente):
    resposta = cliente.get("/hoje?data=2026-09-28")
    assert resposta.status_code == 200
    texto = resposta.text
    assert "Aplicação da lei penal" in texto
    assert "18:00" in texto
    assert "15 questões" in texto
    assert "Qconcursos" in texto
    assert "Segunda, 28 de setembro" in texto
    assert "Semana 1 de 6" in texto
    assert "⚡ Nível 1" in texto
    assert "Primeira semana: nível 1." in texto
    assert "termina às" in texto and "19:35" in texto
    assert "Meta da prova: 79 acertos" in texto


def test_o_detalhe_da_teoria_fica_aberto_e_o_das_questoes_fechado(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "Princípios da legalidade e da anterioridade" in texto
    assert "<details><summary>ver detalhe</summary>" in texto
    assert "Filtro: Direito Penal" in texto
    assert 'target="_blank"' in texto and "Ler no Planalto" in texto


def test_revisao_diz_de_que_dia_volta_e_feriado_ganha_chip(cliente):
    texto = cliente.get("/hoje?data=2026-10-12").text
    assert "R+7" in texto
    assert "volta do dia 05/10" in texto
    assert "chip-feriado" in texto and "N. Sra. Aparecida" in texto


def test_simulado_mostra_cronometrado(cliente):
    texto = cliente.get("/hoje?data=2026-10-10").text
    assert "⏱ cronometrado" in texto
    assert "18:00 – 19:30" in texto


def test_domingo_e_descanso(cliente):
    texto = cliente.get("/hoje?data=2026-10-04").text
    assert "Domingo é descanso total" in texto
    assert "Sem estudo, sem Anki, sem questão." in texto
    assert "Amanhã:" in texto and "Fato típico e nexo causal" in texto


def test_antes_e_depois_do_ciclo(cliente):
    antes = cliente.get("/hoje?data=2026-09-01").text
    assert "O Ciclo 1 começa em 28/09 (segunda)" in antes
    depois = cliente.get("/hoje?data=2026-12-01").text
    assert "O Ciclo 1 terminou em 07/11" in depois
    assert "O Ciclo 2 entra quando o <code>config/cronograma.yml</code>" in depois


def test_sem_o_arquivo_diz_qual_falta(cliente, tmp_path, monkeypatch):
    monkeypatch.setenv("RADAR_CONFIG_DIR", str(tmp_path))
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "Falta o arquivo do cronograma" in texto
    assert "cronograma.yml" in texto


def test_data_invalida_nao_quebra(cliente):
    resposta = cliente.get("/hoje?data=ontem")
    assert resposta.status_code == 200
    assert "Data inválida" in resposta.text


# --- o cartao AGORA ----------------------------------------------------------

def test_agora_no_meio_de_uma_faixa(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 18, 20)
    texto = cliente.get("/hoje").text
    assert "Agora · 18:20" in texto
    assert "EM ANDAMENTO · 18:00–18:40" in texto
    assert "Aprendizagem: Aplicação da lei penal" in texto
    assert "depois: Pausa" in texto
    # Na linha do tempo, a faixa atual leva a etiqueta AGORA embaixo do horario.
    assert 'class="etiqueta-agora"' in texto
    assert "passou" in texto               # a manha ja foi


def test_agora_antes_de_comecar_entre_blocos_e_no_fim(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 8, 0)
    assert "Começa às 10:15 com Teoria · Direito Penal" in cliente.get("/hoje").text
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 14, 0)
    assert "Próximo bloco às 18:00" in cliente.get("/hoje").text
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 23, 30)
    assert "Dia encerrado. Marque como foi lá embaixo." in cliente.get("/hoje").text


def test_agora_so_aparece_no_dia_de_hoje(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 18, 20)
    texto = cliente.get("/hoje?data=2026-09-29").text
    assert "Agora ·" not in texto
    assert "Este dia: começa às 10:15" in texto


# --- como foi o dia ----------------------------------------------------------

def test_registrar_grava_e_volta_para_o_dia(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 30, 12, 0)
    resposta = cliente.post("/hoje/registrar", data={
        "data": "2026-09-28", "meta": "ideal", "questoes_feitas": "25",
        "acertos": "18", "anotacao": "rendeu"}, follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje?data=2026-09-28"

    (r,) = servico.cronograma.registros(
        datetime(2026, 9, 28).date(), datetime(2026, 9, 28).date()).values()
    assert (r.meta, r.questoes_feitas, r.acertos, r.anotacao) == ("ideal", 25, 18, "rendeu")

    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "Editar o registro de 28/09" in texto
    assert 'value="ideal" checked' in texto
    assert 'value="25"' in texto
    # A pilula do dia fica verde (classe ideal).
    assert "pilula ideal" in texto


def test_campos_vazios_nao_quebram(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 30, 12, 0)
    resposta = cliente.post("/hoje/registrar", data={
        "data": "2026-09-28", "meta": "minima", "questoes_feitas": "",
        "acertos": "", "anotacao": ""}, follow_redirects=False)
    assert resposta.status_code == 303


def test_data_futura_e_recusada_na_tela(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 12, 0)
    resposta = cliente.post("/hoje/registrar", data={
        "data": "2026-09-29", "meta": "ideal"})
    assert resposta.status_code == 400
    assert "ainda nao chegou" in resposta.text
    assert servico.cronograma.registros(
        datetime(2026, 9, 1).date(), datetime(2026, 12, 31).date()) == {}


def test_dia_futuro_mostra_o_formulario_desabilitado(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 12, 0)
    texto = cliente.get("/hoje?data=2026-09-30").text
    assert "Só dá para marcar hoje ou um dia que já passou." in texto
    assert "disabled" in texto


@pytest.mark.parametrize("campos, texto", [
    ({"meta": ""}, "Escolha como foi o dia"),
    ({"meta": "ideal", "questoes_feitas": "dez"}, "precisa ser um número inteiro"),
    ({"meta": "ideal", "questoes_feitas": "10", "acertos": "12"}, "maior que questoes feitas"),
])
def test_erro_de_validacao_aparece_na_tela(cliente, monkeypatch, campos, texto):
    _parar_o_relogio(monkeypatch, 2026, 9, 30, 12, 0)
    resposta = cliente.post("/hoje/registrar", data={"data": "2026-09-28", **campos})
    assert resposta.status_code == 400
    assert texto in resposta.text
    assert 'role="alert"' in resposta.text


# --- acesso facil ------------------------------------------------------------

def test_a_barra_tem_o_hoje_em_primeiro(cliente):
    texto = cliente.get("/concursos").text
    assert 'href="/hoje"' in texto
    assert texto.index('href="/hoje"') < texto.index("Meu foco")
    assert 'class="item ativo" href="/hoje"' in cliente.get("/hoje").text


def test_a_home_tem_o_cartao_do_dia(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 28, 10, 30)
    texto = cliente.get("/").text
    assert "Hoje no cronograma" in texto
    assert 'href="/hoje"' in texto and "Abrir o dia" in texto
    assert "Semana 1 · Nível 1" in texto
    assert "Aplicação da lei penal" in texto
    assert "25 questões" in texto


def test_a_home_no_domingo_e_depois_do_ciclo(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 10, 4, 10, 0)
    assert "Hoje é descanso." in cliente.get("/").text
    _parar_o_relogio(monkeypatch, 2026, 12, 1, 10, 0)
    texto = cliente.get("/").text
    assert "Hoje no cronograma" not in texto
    assert "Ver o primeiro dia" not in texto and "Abrir o dia" not in texto


def test_a_home_antes_do_ciclo_diz_quando_comeca(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 9, 26, 10, 0)
    texto = cliente.get("/").text
    assert "O Ciclo 1 começa segunda, 28/09" in texto
    assert "Aplicação da lei penal (arts. 1º a 12)" in texto
    assert 'href="/hoje?data=2026-09-28"' in texto
    assert "Ver o primeiro dia" in texto


def test_o_unico_javascript_e_o_do_cronometro(cliente):
    """A excecao da etapa A5 (docs/decisoes.md): um arquivo so, e nada inline."""
    texto = cliente.get("/hoje?data=2026-09-28").text.lower()
    assert texto.count("<script") == 1
    assert '<script src="/estatico/cronometro.js" defer></script>' in texto


# --- o gatilho olhando o futuro ----------------------------------------------

def _niveis_vistos_de(real, quando):
    from radar import cronograma
    return cronograma.niveis(real, {}, servico.cronograma.hoje_do_gatilho(quando))


def test_olhando_o_futuro_vale_a_carga_do_plano(cliente, monkeypatch):
    from datetime import date

    from radar import cronograma
    _parar_o_relogio(monkeypatch, 2026, 9, 26, 12, 0)
    t = servico.cronograma.tela_do_dia(date(2026, 10, 28))
    assert (t.nivel.efetivo, t.nivel.situacao) == (5, "futura")
    assert t.dia.total_questoes == 60
    assert t.fim_do_dia.strftime("%H:%M") == "21:15"
    situacoes = {n.situacao for n in _niveis_vistos_de(cronograma.carregar(),
                                                        date(2026, 10, 28)).values()}
    assert not situacoes & {"ruim", "desceu"}

    texto = cliente.get("/hoje?data=2026-10-28").text
    assert "Nível 5" in texto and "Semana futura: carga do plano" in texto


def test_no_meio_do_ciclo_so_as_semanas_que_chegaram_contam(monkeypatch):
    from datetime import date

    from radar import cronograma
    _parar_o_relogio(monkeypatch, 2026, 10, 10, 12, 0)     # sabado da semana 2
    n = _niveis_vistos_de(cronograma.carregar(), date(2026, 10, 28))
    assert (n[2].situacao, n[2].efetivo) == ("ruim", 1)   # a semana 1 fechou sem marca
    assert [n[s].situacao for s in (3, 4, 5, 6)] == ["futura"] * 4


def test_dia_passado_continua_como_era(monkeypatch):
    from datetime import date
    _parar_o_relogio(monkeypatch, 2026, 10, 30, 12, 0)
    t = servico.cronograma.tela_do_dia(date(2026, 10, 5))
    assert (t.nivel.situacao, t.nivel.efetivo) == ("ruim", 1)
    assert t.nivel.motivo.startswith("A semana 1 fechou com 6 dias abaixo")


def test_a_reduzida_da_tela_acompanha_o_nivel(cliente, monkeypatch):
    # Visto em setembro, 28/10 fica na carga do plano: nivel 5, 25 de Direito.
    _parar_o_relogio(monkeypatch, 2026, 9, 26, 12, 0)
    assert "só as 25 questões de Lei de Execução Penal" in cliente.get(
        "/hoje?data=2026-10-28").text
    # Visto em 30/10, sem marcacao nenhuma, o gatilho deixou no nivel 1: 15.
    _parar_o_relogio(monkeypatch, 2026, 10, 30, 12, 0)
    assert "só as 15 questões de Lei de Execução Penal" in cliente.get(
        "/hoje?data=2026-10-28").text


# --- o visual novo (etapa A2) ------------------------------------------------

def test_a_faixa_do_topo_tem_nivel_e_meta(cliente):
    texto = cliente.get("/hoje?data=2026-10-28").text
    assert 'class="heroi"' in texto
    assert "⚡ Nível" in texto
    assert "🎯 Meta: 79 acertos" in texto
    assert "dias seguidos" in texto
    # Sem a conta da sequencia (A6), o lugar fica com "–", nunca um numero.
    assert "🔥 – dias seguidos" in texto


def test_a_coluna_lateral_tem_os_tres_cartoes(cliente):
    texto = cliente.get("/hoje?data=2026-10-28").text
    assert 'class="lateral"' in texto
    assert 'id="cronometro"' in texto          # o lugar do cronometro, vazio
    for titulo in ("Agora", "Esta semana", "Objetivo"):
        assert f'<h2 class="lateral-titulo">{titulo}' in texto
    assert "Meta da prova: 79 acertos" in texto
    assert 'class="pilula' in texto


def test_o_botao_da_lei_diz_onde_abre():
    from radar.web.app import rotulo_da_lei
    assert rotulo_da_lei("https://www.planalto.gov.br/ccivil_03/leis/l7210.htm") == "Ler no Planalto"
    assert rotulo_da_lei("https://leis.alesc.sc.gov.br/html/2005/1234.html") == "Ler na ALESC"
    assert rotulo_da_lei("http://alesc.sc.gov.br/lei") == "Ler na ALESC"
    assert rotulo_da_lei("https://www.stf.jus.br/sumula") == "Ler a lei"
    # Um dominio que so TERMINA parecido nao e o Planalto.
    assert rotulo_da_lei("https://falsoplanalto.gov.br/x") == "Ler a lei"


def test_o_botao_da_lei_aparece_na_tela(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert 'class="botao-lei"' in texto and "⚖️" in texto and "Ler no Planalto" in texto


def test_o_bloco_das_22h_e_sobreaviso(cliente):
    texto = cliente.get("/hoje?data=2026-09-29").text
    assert "bloco-pos22" in texto
    assert "🌙 sobreaviso · pode interromper" in texto
    assert "bloco-noite" in texto


def test_fim_do_ciclo_em_n_dias(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 10, 28, 9, 0)
    assert "Fim do Ciclo 1 em 10 dias" in cliente.get("/hoje").text


def test_fim_do_ciclo_hoje_e_encerrado(cliente, monkeypatch):
    _parar_o_relogio(monkeypatch, 2026, 11, 7, 9, 0)
    assert "Fim do Ciclo 1 hoje" in cliente.get("/hoje").text
    _parar_o_relogio(monkeypatch, 2026, 11, 10, 9, 0)
    assert "Ciclo 1 encerrado" in cliente.get("/hoje").text


def test_a_minima_se_chama_plano_b_no_formulario(cliente):
    texto = cliente.get("/hoje?data=2026-09-28").text
    assert "Plano B</small>" in texto
    assert "Anki + poucas questões" not in texto
