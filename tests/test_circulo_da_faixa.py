"""O circulo em toda faixa, a feita dobrada e o fechamento pelo radar (decisao 179).

O caso que motivou: o 19/10. O dia foi todo feito - a maior parte no radar,
pelos botoes das faixas -, mas as faixas de questao nao tinham circulo, so o
"fiz X, acertei Y", e 5 ficaram sem marca: a sugestao dizia "Minima (4 de 9
faixas)" num dia Ideal. Estes testes seguram:

  * o circulo da faixa de questoes marca "fiz" sem numero: a faixa conta na
    meta e no tempo, e nenhuma questao e inventada;
  * a faixa feita nasce dobrada, numa linha so, e abre de novo no clique;
  * a faixa que o radar cobriu (respostas >= o numero dela) fecha sozinha.

As datas sao fixas: nada aqui depende do dia em que o teste roda.
"""
import re
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from radar import cronograma
from radar.db import sessao
from radar.models import QuestaoGerada, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import metricas
from radar.servico import simulado as servico_simulado
from radar.util import fuso_local
from radar.web.app import app

SEG = date(2026, 9, 28)
DEPOIS = date(2026, 9, 30)


@pytest.fixture
def plano():
    return cronograma.carregar()


def _faixa_de_questoes(plano):
    """A primeira faixa de questoes do 28/09, como o servico a marca."""
    dia = plano.dia(SEG)
    for bloco in cronograma.TODOS_OS_BLOCOS:
        for indice, faixa in enumerate(getattr(dia, bloco)):
            if cronograma.tem_acerto(faixa) and faixa.questoes:
                return bloco, indice, diario._faixa_do_plano(plano, SEG, bloco, indice)
    raise AssertionError("o 28/09 do plano real nao tem faixa de questoes")


def _rodada_da_faixa(bloco, indice, titulo, respondidas: int, abertas: int = 0) -> int:
    """Uma rodada de geradas aberta pelo botao da faixa: `respondidas` ja
    respondidas, `abertas` por responder. Devolve o id."""
    quando = datetime(2026, 9, 28, 10, 40, tzinfo=fuso_local())
    with sessao() as s:
        simulado = Simulado(filtros={"geradas": True, "da_faixa": {
            "data": SEG.isoformat(), "bloco": bloco, "indice": indice, "titulo": titulo}})
        s.add(simulado)
        s.flush()
        for ordem in range(1, respondidas + abertas + 1):
            gerada = QuestaoGerada(modo="do_zero", enunciado=f"q{ordem}",
                                   impressao=f"g{simulado.id}-{ordem}",
                                   resposta="a", alternativas={"a": "sim", "b": "não"})
            s.add(gerada)
            s.flush()
            feita = ordem <= respondidas
            s.add(RespostaDeSimulado(
                simulado_id=simulado.id, questao_id=gerada.id, gerada=True, ordem=ordem,
                escolhida="a" if feita else None, acertou=True if feita else None,
                respondida_em=quando if feita else None))
        return simulado.id


def _feita(plano, bloco, indice):
    return diario.valores_das_faixas(plano.dia(SEG), diario.estado_do_dia(SEG)).get((bloco, indice))


# --- o circulo da faixa de questoes ---------------------------------------------------

def test_o_circulo_marca_feita_sem_numero_e_nao_inventa_questao(banco_temporario, plano,
                                                               monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: DEPOIS)
    bloco, indice, faixa = _faixa_de_questoes(plano)
    cliente = TestClient(app)

    resposta = cliente.post("/hoje/faixa/questoes", data={
        "data": SEG.isoformat(), "bloco": bloco, "indice": str(indice),
        "titulo": faixa.titulo}, follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"].endswith(f"#faixa-{bloco}-{indice}")
    feita = _feita(plano, bloco, indice)
    assert (feita.questoes, feita.sem_numero, feita.no_radar) == (0, True, False)
    conta = metricas.do_dia(SEG, plano)
    assert conta.total.questoes == 0          # o numero do plano nao entra
    assert conta.minutos == feita.minutos > 0   # o tempo da faixa, sim
    sugestao = diario.sugerir_meta(plano.dia(SEG), {(bloco, indice)})
    assert sugestao.feitas == 1                # e ela conta na sugestao da meta


def test_o_circulo_verde_desmarca(banco_temporario, plano, monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: DEPOIS)
    bloco, indice, faixa = _faixa_de_questoes(plano)
    dados = {"data": SEG.isoformat(), "bloco": bloco, "indice": str(indice),
             "titulo": faixa.titulo}
    cliente = TestClient(app)
    cliente.post("/hoje/faixa/questoes", data=dados)

    cliente.post("/hoje/faixa/questoes", data={**dados, "desmarcar": "1"})

    assert _feita(plano, bloco, indice) is None


def _li_da_faixa(texto: str, bloco: str, indice: int) -> str:
    inicio = texto.index(f'id="faixa-{bloco}-{indice}"')
    fim = texto.find('<li class="faixa', inicio + 1)
    return texto[inicio:fim if fim != -1 else len(texto)]


def test_a_faixa_feita_nasce_dobrada_e_a_aberta_nao(banco_temporario, plano, monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: DEPOIS)
    bloco, indice, faixa = _faixa_de_questoes(plano)
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="15", acertos="11",
                        plano=plano, hoje=DEPOIS)

    texto = TestClient(app).get("/hoje?data=2026-09-28").text

    feita = _li_da_faixa(texto, bloco, indice)
    assert '<details class="faixa-dobra">' in feita        # fechada
    assert "11" in feita and "de 15" in feita              # o resultado na linha
    assert 'aria-pressed="true"' in feita                  # o circulo verde
    abertas = re.findall(r'<details class="faixa-dobra" open>', texto)
    assert abertas, "as faixas por fazer continuam abertas"


# --- o radar fecha a faixa sozinho ----------------------------------------------------

def test_o_radar_fecha_a_faixa_quando_chega_ao_numero_dela(banco_temporario, plano):
    bloco, indice, faixa = _faixa_de_questoes(plano)
    _rodada_da_faixa(bloco, indice, faixa.titulo, faixa.questoes - 1)

    assert not diario.fechar_pelo_radar(SEG, bloco, indice, faixa.titulo,
                                        plano=plano, hoje=DEPOIS)
    assert _feita(plano, bloco, indice) is None

    _rodada_da_faixa(bloco, indice, faixa.titulo, 1)

    assert diario.fechar_pelo_radar(SEG, bloco, indice, faixa.titulo, plano=plano, hoje=DEPOIS)
    feita = _feita(plano, bloco, indice)
    assert (feita.no_radar, feita.automatica, feita.questoes) == (True, True, 0)


def test_o_radar_nao_mexe_na_faixa_que_eu_ja_marquei(banco_temporario, plano):
    bloco, indice, faixa = _faixa_de_questoes(plano)
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="7", acertos="5",
                        plano=plano, hoje=DEPOIS)
    _rodada_da_faixa(bloco, indice, faixa.titulo, faixa.questoes)

    assert not diario.fechar_pelo_radar(SEG, bloco, indice, faixa.titulo,
                                        plano=plano, hoje=DEPOIS)
    assert (_feita(plano, bloco, indice).questoes, _feita(plano, bloco, indice).acertos) == (7, 5)


def test_responder_a_ultima_questao_no_radar_fecha_a_faixa(banco_temporario, plano,
                                                          monkeypatch):
    monkeypatch.setattr(diario, "hoje_local", lambda: DEPOIS)
    bloco, indice, faixa = _faixa_de_questoes(plano)
    rodada = _rodada_da_faixa(bloco, indice, faixa.titulo, faixa.questoes - 1, abertas=1)
    with sessao() as s:
        aberta = s.query(RespostaDeSimulado).filter_by(simulado_id=rodada,
                                                       escolhida=None).one().questao_id

    assert servico_simulado.responder(rodada, aberta, "a") is True

    feita = _feita(plano, bloco, indice)
    assert feita is not None and feita.automatica
