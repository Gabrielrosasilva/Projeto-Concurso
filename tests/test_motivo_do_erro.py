"""O motivo de cada erro, num clique (decisao 174).

O que estes testes seguram:

  * o motivo grava na propria resposta e troca (vale o ultimo), so na errada;
  * o "Chutei" vem marcado quando marquei o "vou no chute", sem gravar nada;
  * na rodada que corrige no fim nada aparece durante ela, e o relatorio traz
    os botoes depois da ultima;
  * o caderno aberto pelo radar leva o motivo de volta para a resposta;
  * o data/simulados.json leva o motivo, e o arquivo antigo (sem a chave) vale;
  * a nota da faixa ("Como foi") recusa a soma que passa dos erros do "fiz";
  * a conta do Historico conta cada erro uma vez, por origem, nunca somadas;
  * nenhum numero que ja existia muda.
Datas fixas e o cronograma real, como os vizinhos.
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import acervo, cronograma
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import erros, metricas, notas_da_faixa
from radar.servico import simulado as rodadas
from radar.servico.comum import RegistroInvalido
from radar.web.app import app
from tests.test_correcao_na_hora import _ids, _rodada
from tests.test_fiz_no_radar import DEPOIS, SEG, _primeira_faixa_de_questoes
from tests.test_simulado import _questao


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def _resposta(simulado_id: int, questao_id: int) -> RespostaDeSimulado:
    with sessao() as s:
        return s.scalar(select(RespostaDeSimulado)
                        .where(RespostaDeSimulado.simulado_id == simulado_id)
                        .where(RespostaDeSimulado.questao_id == questao_id))


def _errar(cliente, rodada, questao_id, chutei=False):
    dados = {"questao_id": questao_id, "letra": "a"}
    if chutei:
        dados["chutei"] = "1"
    cliente.post(f"/simulado/{rodada}/responder", data=dados)


# --- os botoes ----------------------------------------------------------------------

def test_o_motivo_grava_na_resposta_e_troca(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, _ = _ids(rodada)
    _errar(cliente, rodada, primeira)

    tela = cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    assert "Por que errei?" in tela and 'aria-pressed="true"' not in tela

    ida = cliente.post(f"/simulado/{rodada}/motivo",
                       data={"questao_id": primeira, "motivo": "nao_sabia"},
                       follow_redirects=False)
    assert ida.status_code == 303
    assert ida.headers["location"] == f"/simulado/{rodada}?ver={primeira}"
    assert _resposta(rodada, primeira).motivo == "nao_sabia"

    cliente.post(f"/simulado/{rodada}/motivo", data={"questao_id": primeira,
                                                     "motivo": "confundi"})
    assert _resposta(rodada, primeira).motivo == "confundi"
    depois = cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    assert "✓ Confundi" in depois and "motivo=confundi" in depois


def test_o_chutei_vem_marcado_sem_gravar_nada(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, _ = _ids(rodada)
    _errar(cliente, rodada, primeira, chutei=True)

    tela = cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    assert "✓ Chutei" in tela
    # O caderno abre com o motivo e com a resposta de onde o erro veio.
    assert "motivo=chutei" in tela and f"simulado={rodada}" in tela
    resposta = _resposta(rodada, primeira)
    assert resposta.motivo is None and erros.motivo_do_erro(resposta) == "chutei"


def test_o_botao_so_aparece_na_errada(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, _ = _ids(rodada)
    cliente.post(f"/simulado/{rodada}/responder", data={"questao_id": primeira, "letra": "c"})

    assert "Por que errei?" not in cliente.get(f"/simulado/{rodada}?ver={primeira}").text
    recusa = cliente.post(f"/simulado/{rodada}/motivo",
                          data={"questao_id": primeira, "motivo": "nao_sabia"})
    assert recusa.status_code == 400 and "acertou" in recusa.text
    assert _resposta(rodada, primeira).motivo is None


@pytest.mark.parametrize("motivo, recado", [("pressa", "desconhecido"), ("", "desconhecido")])
def test_motivo_que_nao_existe_e_recusado(banco_temporario, motivo, recado):
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)
    rodadas.responder(rodada, primeira, "a")
    with pytest.raises(rodadas.MotivoRecusado, match=recado):
        rodadas.marcar_motivo(rodada, primeira, motivo)


def test_questao_sem_resposta_nao_tem_motivo(banco_temporario):
    rodada = _rodada(_questao(1))
    (primeira,) = _ids(rodada)
    with pytest.raises(rodadas.MotivoRecusado, match="Responda"):
        rodadas.marcar_motivo(rodada, primeira, "nao_sabia")


def test_nada_durante_a_rodada_que_corrige_no_fim(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"),
                     filtros={"rodada": "composta", "quantidade": 2})
    primeira, segunda = _ids(rodada)
    _errar(cliente, rodada, primeira)

    assert "Por que errei?" not in cliente.get(f"/simulado/{rodada}").text
    recusa = cliente.post(f"/simulado/{rodada}/motivo",
                          data={"questao_id": primeira, "motivo": "pegadinha"})
    assert recusa.status_code == 400 and "no fim" in recusa.text

    _errar(cliente, rodada, segunda)
    relatorio = cliente.get(f"/simulado/{rodada}").text
    assert relatorio.count("Por que errei?") == 2

    ida = cliente.post(f"/simulado/{rodada}/motivo",
                       data={"questao_id": primeira, "motivo": "pegadinha",
                             "volta": f"/simulado/{rodada}#erro-1"},
                       follow_redirects=False)
    assert ida.headers["location"] == f"/simulado/{rodada}#erro-1"
    assert _resposta(rodada, primeira).motivo == "pegadinha"


def test_o_caderno_aberto_pelo_radar_leva_o_motivo_para_a_resposta(cliente):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, _ = _ids(rodada)
    _errar(cliente, rodada, primeira, chutei=True)

    formulario = cliente.get(f"/erros/novo?fonte=radar&motivo=chutei"
                             f"&simulado={rodada}&questao={primeira}").text
    assert f'name="simulado" value="{rodada}"' in formulario

    cliente.post("/erros/novo", data={
        "data_estudo": "2026-09-28", "materia": "Língua Portuguesa",
        "motivo": "li_errado", "regra": "Ler o enunciado até o fim.", "fonte": "radar",
        "simulado": str(rodada), "questao": str(primeira)})

    assert _resposta(rodada, primeira).motivo == "li_errado"
    (anotado,) = erros.listar(situacao="todos")
    assert anotado.motivo == "li_errado"


# --- o backup -------------------------------------------------------------------------

def test_o_motivo_vai_e_volta_no_json(banco_temporario):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, segunda = _ids(rodada)
    rodadas.responder(rodada, primeira, "a")
    rodadas.responder(rodada, segunda, "b")
    rodadas.marcar_motivo(rodada, primeira, "pegadinha")

    acervo.exportar_simulados()
    arquivo = acervo.caminho_dos_simulados()
    (linha,) = json.loads(arquivo.read_text(encoding="utf-8"))
    com, sem = linha["respostas"]
    assert com["motivo"] == "pegadinha" and "motivo" not in sem

    # O banco perde o motivo; o arquivo novo o devolve, e o antigo (sem a
    # chave) deixa a resposta como esta.
    with sessao() as s:
        for r in s.scalars(select(RespostaDeSimulado)):
            r.motivo = None
    sem["motivo"] = "confundi"
    arquivo.write_text(json.dumps([linha]), encoding="utf-8")
    acervo.importar_simulados()
    assert _resposta(rodada, primeira).motivo == "pegadinha"
    assert _resposta(rodada, segunda).motivo == "confundi"

    del com["motivo"]
    with sessao() as s:
        s.scalar(select(RespostaDeSimulado).where(
            RespostaDeSimulado.questao_id == primeira)).motivo = None
    arquivo.write_text(json.dumps([linha]), encoding="utf-8")
    acervo.importar_simulados()
    assert _resposta(rodada, primeira).motivo is None


# --- o "Como foi" ---------------------------------------------------------------------

@pytest.fixture
def plano():
    return cronograma.carregar()


def _nota(plano, bloco, indice, titulo, **campos):
    return notas_da_faixa.anotar(SEG, bloco, indice, titulo, plano=plano, hoje=DEPOIS,
                                 **campos)


def test_a_soma_dos_motivos_nao_passa_dos_erros_do_fiz(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="10", acertos="7",
                        plano=plano, hoje=DEPOIS)

    with pytest.raises(RegistroInvalido, match="somam 4"):
        _nota(plano, bloco, indice, faixa.titulo, motivos={"nao_sabia": "3", "confundi": "1"})
    nota = _nota(plano, bloco, indice, faixa.titulo, motivos={"nao_sabia": "2", "confundi": "1"})
    assert nota.motivos == {"nao_sabia": 2, "confundi": 1}
    assert (nota.erros_do_fiz, nota.sem_motivo) == (3, 0)
    assert nota.motivos_texto == "Não sabia 2 · Confundi 1"


def test_o_chutei_nao_passa_dos_chutes(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    with pytest.raises(RegistroInvalido, match="chutes"):
        _nota(plano, bloco, indice, faixa.titulo, chutes="1", motivos={"chutei": "2"})


def test_sem_o_fiz_a_nota_grava_e_o_fiz_depois_marca_a_nota(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    nota = _nota(plano, bloco, indice, faixa.titulo, motivos={"nao_sabia": "4"})
    assert nota.teto_dos_motivos is None and not nota.motivos_passam

    # O "fiz" chega com menos erros: ele grava, e a nota fica marcada.
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="10", acertos="8",
                        plano=plano, hoje=DEPOIS)
    (nota,) = notas_da_faixa.do_dia(diario.estado_do_dia(SEG)).values()
    assert nota.motivos_passam
    assert metricas.motivos_dos_erros()["fora_do_radar"].por_motivo == {}


def test_a_tela_grava_os_motivos_e_mostra_a_soma(banco_temporario, plano, monkeypatch):
    from datetime import datetime

    from radar.util import fuso_local

    monkeypatch.setattr(diario, "hoje_local", lambda: DEPOIS)
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()))
    cliente = TestClient(app)
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="10", acertos="1",
                        plano=plano, hoje=DEPOIS)

    cliente.post("/hoje/faixa/nota", data={
        "data": SEG.isoformat(), "bloco": bloco, "indice": str(indice),
        "titulo": faixa.titulo, "motivo_nao_sabia": "3", "motivo_confundi": "2",
        "motivo_li_errado": "2", "motivo_pegadinha": "1", "motivo_chutei": "1"})

    tela = cliente.get("/hoje?data=2026-09-28").text
    assert ("Dos 9 erros: Não sabia 3 · Confundi 2 · Li errado 2 · Pegadinha 1 · Chutei 1"
            in tela)
    recusa = cliente.post("/hoje/faixa/nota", data={
        "data": SEG.isoformat(), "bloco": bloco, "indice": str(indice),
        "titulo": faixa.titulo, "motivo_nao_sabia": "10"})
    assert recusa.status_code == 400 and "somam 10" in recusa.text


# --- a conta para o Historico ---------------------------------------------------------

def test_a_conta_conta_cada_erro_uma_vez_por_origem(banco_temporario, plano):
    fepese, de_outra = _questao(1), _questao(2, impressao="i2", evidencia="fora")
    with sessao() as s:
        s.add(QuestaoGerada(modo="do_zero", enunciado="gerada", impressao="g1",
                            resposta="b", alternativas={"a": "x", "b": "y"}))
    rodada = _rodada(fepese, de_outra)
    primeira, segunda = _ids(rodada)
    rodadas.responder(rodada, primeira, "a")
    rodadas.responder(rodada, segunda, "a")
    rodadas.marcar_motivo(rodada, primeira, "li_errado")
    with sessao() as s:
        gerada = s.scalar(select(QuestaoGerada))
        das_geradas = Simulado(filtros={"geradas": True})
        s.add(das_geradas)
        s.flush()
        s.add(RespostaDeSimulado(simulado_id=das_geradas.id, questao_id=gerada.id,
                                 gerada=True, ordem=1))
        simulado_das_geradas = das_geradas.id
    rodadas.responder(simulado_das_geradas, gerada.id, "a", chutou=True)

    # Fora do radar: o "fiz" com 3 erros, a nota com os motivos, e o caderno.
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="10", acertos="7",
                        plano=plano, hoje=DEPOIS)
    _nota(plano, bloco, indice, faixa.titulo, motivos={"nao_sabia": "2", "confundi": "1"})
    erros.anotar(SEG, "Língua Portuguesa", faixa.titulo, "pegadinha", "regra",
                 fonte="qconcursos", hoje=DEPOIS)          # a nota da faixa ja o conta
    erros.anotar(SEG, "Direito Penal", "estudo extra", "nao_sabia", "regra",
                 fonte="outro", hoje=DEPOIS)               # sozinho: +1 erro
    erros.anotar(SEG, "Língua Portuguesa", "da rodada", "confundi", "regra",
                 fonte="radar", hoje=DEPOIS)               # ja conta pela resposta

    conta = metricas.motivos_dos_erros()

    assert (conta["fepese"].erros, conta["fepese"].por_motivo) == (1, {"li_errado": 1})
    assert (conta["outras_bancas"].erros, conta["outras_bancas"].sem_motivo) == (1, 1)
    assert (conta["geradas"].erros, conta["geradas"].por_motivo) == (1, {"chutei": 1})
    fora = conta["fora_do_radar"]
    assert (fora.erros, fora.por_motivo) == (4, {"nao_sabia": 3, "confundi": 1})
    assert (conta["fepese"].bobos, fora.bobos, fora.sem_motivo) == (1, 1, 0)
    # O periodo corta pelo dia: nada antes de 28/09.
    assert metricas.motivos_dos_erros(ate=SEG.replace(day=27))["fora_do_radar"].erros == 0


def test_o_erro_bobo_mora_ao_lado_dos_motivos():
    assert set(erros.ERRO_BOBO) == {"li_errado", "confundi"}
    assert set(erros.ERRO_BOBO) <= set(erros.MOTIVOS)


def test_nenhum_numero_que_ja_existia_muda(banco_temporario):
    rodada = _rodada(_questao(1), _questao(2, impressao="i2"))
    primeira, segunda = _ids(rodada)
    rodadas.responder(rodada, primeira, "a", chutou=True)
    rodadas.responder(rodada, segunda, "c")
    antes = (metricas.resumo_do_simulado(rodada), metricas.desempenho(rodada),
             metricas.acumulado(), metricas.contar(metricas.lancamentos(SEG, DEPOIS)))

    rodadas.marcar_motivo(rodada, primeira, "nao_sabia")

    depois = (metricas.resumo_do_simulado(rodada), metricas.desempenho(rodada),
              metricas.acumulado(), metricas.contar(metricas.lancamentos(SEG, DEPOIS)))
    assert depois == antes
