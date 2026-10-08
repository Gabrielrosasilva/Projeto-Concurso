"""A nota de cada faixa: como fui, quantas chutei e se entendi (decisao 142).

O que estes testes seguram: a nota grava e troca; tudo vazio tira; desmarcar
a faixa nao apaga a nota (e da para escrever antes de marcar); faixa de dia
que nao chegou e titulo que mudou sao recusados; a nota vai e volta no
backup do dia; a tela Hoje mostra a caixa e o que foi escrito; a ficha e o Meu
desempenho releem, com o tema que eu ainda nao entendi na frente; e o chute
do radar aparece na faixa. Datas fixas, cronograma real, como os vizinhos.
"""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from radar import acervo, cronograma
from radar.db import sessao
from radar.models import EstadoDoDia, RespostaDeSimulado, Simulado
from radar.servico import cronograma as diario
from radar.servico import metricas, notas_da_faixa
from radar.util import fuso_local
from radar.web.app import app
from tests.test_fiz_no_radar import DEPOIS, SEG, _primeira_faixa_de_questoes


@pytest.fixture
def plano():
    return cronograma.carregar()


@pytest.fixture
def em_30_09(banco_temporario, monkeypatch):
    """A tela e a rota sem `hoje=`: o dia de hoje fica fixo em 30/09."""
    monkeypatch.setattr(diario, "hoje_local", lambda: DEPOIS)
    monkeypatch.setattr(diario, "agora_local",
                        lambda: datetime(2026, 9, 30, 12, 0, tzinfo=fuso_local()))
    return TestClient(app)


def _anotar(plano, bloco, indice, titulo, **campos):
    return notas_da_faixa.anotar(SEG, bloco, indice, titulo, plano=plano, hoje=DEPOIS,
                                 **campos)


# --- gravar ---------------------------------------------------------------------

def test_a_nota_grava_e_troca(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)

    _anotar(plano, bloco, indice, faixa.titulo, chutes="3", entendi="nao",
            nota="Chutei, ainda não entendi, mas o chute foi bom.")
    _anotar(plano, bloco, indice, faixa.titulo, chutes="2", entendi="mais_ou_menos",
            nota="Melhorou.")

    (nota,) = notas_da_faixa.do_dia(diario.estado_do_dia(SEG)).values()
    assert (nota.chutes, nota.entendi, nota.nota) == (2, "mais_ou_menos", "Melhorou.")
    assert nota.entendi_texto == "Mais ou menos"


def test_tudo_vazio_tira_a_nota(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _anotar(plano, bloco, indice, faixa.titulo, nota="algo")

    assert _anotar(plano, bloco, indice, faixa.titulo, chutes="", entendi="", nota="  ") is None
    assert notas_da_faixa.do_dia(diario.estado_do_dia(SEG)) == {}


def test_zero_chutes_e_uma_resposta_e_nao_vazio(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    nota = _anotar(plano, bloco, indice, faixa.titulo, chutes="0")
    assert nota is not None and nota.chutes == 0


def test_desmarcar_a_faixa_nao_apaga_a_nota(banco_temporario, plano):
    """Escrevo antes de marcar, marco, desmarco: a nota fica."""
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _anotar(plano, bloco, indice, faixa.titulo, nota="antes de marcar")
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="10", acertos="7",
                        plano=plano, hoje=DEPOIS)
    diario.desmarcar_faixa(SEG, bloco, indice, faixa.titulo, plano=plano, hoje=DEPOIS)

    (nota,) = notas_da_faixa.do_dia(diario.estado_do_dia(SEG)).values()
    assert nota.nota == "antes de marcar"


@pytest.mark.parametrize("campos, recado", [
    ({"chutes": "x"}, "número inteiro"),
    ({"chutes": "-1"}, "negativos"),
    ({"entendi": "talvez"}, "não existe"),
    ({"nota": "a" * 2001}, "2000"),
])
def test_valores_errados_sao_recusados(banco_temporario, plano, campos, recado):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    with pytest.raises(diario.RegistroInvalido, match=recado):
        _anotar(plano, bloco, indice, faixa.titulo, **campos)


def test_dia_que_nao_chegou_e_titulo_que_mudou_sao_recusados(banco_temporario, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    with pytest.raises(diario.RegistroInvalido, match="ainda não chegou"):
        notas_da_faixa.anotar(SEG, bloco, indice, faixa.titulo, nota="x",
                              plano=plano, hoje=date(2026, 9, 27))
    with pytest.raises(diario.RegistroInvalido, match="mudou"):
        _anotar(plano, bloco, indice, "outro titulo", nota="x")


def test_a_nota_vai_e_volta_no_backup(banco_temporario, plano, tmp_path):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _anotar(plano, bloco, indice, faixa.titulo, chutes="4", entendi="sim", nota="ok")
    arquivo = tmp_path / "estado_do_dia.json"
    acervo.exportar_estados(arquivo)
    with sessao() as s:
        s.query(EstadoDoDia).delete()

    acervo.importar_estados(arquivo)

    (nota,) = notas_da_faixa.do_dia(diario.estado_do_dia(SEG)).values()
    assert (nota.chutes, nota.entendi, nota.nota) == (4, "sim", "ok")


def test_dia_sem_nota_nao_ganha_a_chave_no_backup(banco_temporario, plano, tmp_path):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    diario.anotar_faixa(SEG, bloco, indice, faixa.titulo, questoes="10",
                        plano=plano, hoje=DEPOIS)
    arquivo = tmp_path / "estado_do_dia.json"
    acervo.exportar_estados(arquivo)

    assert "notas_das_faixas" not in arquivo.read_text(encoding="utf-8")


# --- reler ------------------------------------------------------------------------

def test_por_tema_poe_primeiro_o_que_eu_nao_entendi(banco_temporario, plano):
    dia = plano.dia(SEG)
    faixas = [(b, i, f) for b in cronograma.TODOS_OS_BLOCOS
              for i, f in enumerate(getattr(dia, b))
              if f.tipo != "pausa" and not f.desligada][:2]
    (b1, i1, f1), (b2, i2, f2) = faixas
    _anotar(plano, b1, i1, f1.titulo, entendi="sim", chutes="1")
    _anotar(plano, b2, i2, f2.titulo, entendi="nao", chutes="2")

    grupos = notas_da_faixa.por_tema()

    assert grupos[0].ainda_nao_entendi and grupos[0].chutes == 2
    assert not grupos[-1].ainda_nao_entendi


# --- as telas ---------------------------------------------------------------------

def test_a_faixa_mostra_a_caixa_e_grava_pela_tela(em_30_09, plano):
    cliente = em_30_09
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)

    antes = cliente.get("/hoje?data=2026-09-28").text
    assert "📝 Como foi" in antes and "Entendi o assunto?" in antes

    resposta = cliente.post("/hoje/faixa/nota", data={
        "data": SEG.isoformat(), "bloco": bloco, "indice": str(indice),
        "titulo": faixa.titulo, "chutes": "3", "entendi": "nao",
        "nota": "Chutei e o chute foi bom."}, follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"].endswith(f"#faixa-{bloco}-{indice}")
    depois = cliente.get("/hoje?data=2026-09-28").text
    assert "Chutei e o chute foi bom." in depois
    assert "não entendi, 3 no chute" in depois


def test_a_recusa_aparece_na_tela(em_30_09, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    resposta = em_30_09.post("/hoje/faixa/nota", data={
        "data": SEG.isoformat(), "bloco": bloco, "indice": str(indice),
        "titulo": faixa.titulo, "chutes": "-2"})
    assert resposta.status_code == 400 and "negativos" in resposta.text


def test_o_meu_desempenho_mostra_a_lista_do_ciclo_2(em_30_09, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _anotar(plano, bloco, indice, faixa.titulo, entendi="nao", nota="rever isto")

    texto = em_30_09.get("/analises/desempenho").text

    assert "Como eu disse que fui (para o Ciclo 2)" in texto
    assert "rever isto" in texto and "fica no Ciclo 2" in texto


def test_o_chute_no_radar_aparece_na_faixa(em_30_09, plano):
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    quando = datetime(2026, 9, 28, 10, 40, tzinfo=fuso_local())
    with sessao() as s:
        simulado = Simulado(filtros={"geradas": True, "da_faixa": {
            "data": SEG.isoformat(), "bloco": bloco, "indice": indice,
            "titulo": faixa.titulo}})
        s.add(simulado)
        s.flush()
        for ordem, chutou in enumerate([True, True, False], start=1):
            s.add(RespostaDeSimulado(simulado_id=simulado.id, questao_id=ordem,
                                     gerada=True, ordem=ordem, escolhida="a",
                                     acertou=True, respondida_em=quando, chutou=chutou))

    numeros = metricas.no_radar_por_faixa(SEG)[(bloco, indice, faixa.titulo)]
    assert (numeros.questoes, numeros.chutes) == (3, 2)
    assert "🎲 2 no chute." in em_30_09.get("/hoje?data=2026-09-28").text


def test_a_ficha_acha_as_notas_pelo_tema_sem_o_prefixo(banco_temporario, plano):
    """A ficha reconhece o tema pelo titulo da faixa sem o prefixo, como no
    resto do radar: "Fixação: X" e "R+7: X" sao o mesmo tema X."""
    bloco, indice, faixa = _primeira_faixa_de_questoes(plano)
    _anotar(plano, bloco, indice, faixa.titulo, nota="da ficha")
    tema = notas_da_faixa.todas()[0].tema

    grupo = notas_da_faixa.do_tema(tema.upper())

    assert grupo is not None and grupo.notas[0].nota == "da ficha"
    assert notas_da_faixa.do_tema("tema que nao existe") is None
