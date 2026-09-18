"""Previsao de abertura: quando o proximo concurso do municipio deve sair.

A pergunta que isto responde e "onde vale ficar de olho agora", e nao "quando
exatamente". Por isso toda previsao carrega o motivo junto: eu preciso poder
conferir a conta.
"""
from datetime import date, datetime, timezone

import pytest

from radar import servico
from radar.db import sessao
from radar.models import Concurso


def _concurso(titulo: str, municipio: str, ano: int | None = None, **mudancas):
    base = dict(
        url=f"https://x.test/{titulo}".replace(" ", "-"),
        fonte="teste",
        titulo=titulo,
        municipio=municipio,
        relevancia="nucleo",
        tipo="concurso",
        publicado_em=datetime(ano or 2026, 6, 1, tzinfo=timezone.utc),
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos):
    with sessao() as s:
        for c in concursos:
            s.add(c)


def _por_municipio(previsoes):
    return {p.municipio: p for p in previsoes}


# --- de onde sai o ano ------------------------------------------------------

def test_ano_vem_do_titulo_e_nao_da_data_do_post():
    """Na migracao do site da FEPESE, 345 concursos antigos ficaram todos com
    data de dezembro de 2020. O titulo dela diz o ano de verdade."""
    c = _concurso("2014 - Prefeitura Municipal de Tijucas", "Tijucas", ano=2020)

    assert servico._ano_do_concurso(c) == 2014


def test_ano_do_numero_do_edital():
    """Os titulos antigos nao comecam com ano, mas trazem "Edital 003/2018"."""
    c = _concurso("Prefeitura Municipal de Fraiburgo - Edital 003/2018",
                  "Fraiburgo", ano=2020)

    assert servico._ano_do_concurso(c) == 2018


def test_sem_ano_no_titulo_vale_a_publicacao():
    c = _concurso("Concurso Publico CASAN", "Florianopolis", ano=2023)

    assert servico._ano_do_concurso(c) == 2023


def test_sem_ano_nenhum_fica_de_fora():
    c = _concurso("Concurso Publico CASAN", "Florianopolis")
    c.publicado_em = None

    assert servico._ano_do_concurso(c) is None


# --- a previsao -------------------------------------------------------------

def test_municipio_parado_ha_muito_tempo_e_atrasado(banco_temporario):
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 12} - Prefeitura de Tijucas", "Tijucas"),
        _concurso(f"{este_ano - 9} - Prefeitura de Tijucas", "Tijucas"),
    )

    previsao = _por_municipio(servico.previsao_de_abertura())["Tijucas"]

    assert previsao.situacao == "atrasado"
    assert previsao.anos_parado == 9


def test_quem_acabou_de_abrir_esta_em_dia(banco_temporario):
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 3} - Prefeitura de Palhoca", "Palhoca"),
        _concurso(f"{este_ano} - Prefeitura de Palhoca", "Palhoca"),
    )

    assert _por_municipio(servico.previsao_de_abertura())["Palhoca"].situacao == "em_dia"


def test_buraco_de_cobertura_nao_vira_previsao_absurda(banco_temporario):
    """De Tubarao eu so conheco 2011 e 2026. A conta crua dizia "um a cada 15
    anos, proximo em 2041" - o buraco e o que eu nao coletei."""
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 15} - Prefeitura de Tubarao", "Tubarao"),
        _concurso(f"{este_ano} - Prefeitura de Tubarao", "Tubarao"),
    )

    previsao = _por_municipio(servico.previsao_de_abertura())["Tubarao"]

    assert previsao.proximo_previsto == este_ano + servico.VALIDADE_MAXIMA


def test_dois_editais_seguidos_nao_viram_ritmo_anual(banco_temporario):
    """Biguacu tem 2021 e 2022 no historico, que sao dois editais do mesmo
    momento - e nao um concurso por ano."""
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 5} - Prefeitura de Biguacu", "Biguacu"),
        _concurso(f"{este_ano - 4} - Prefeitura de Biguacu", "Biguacu"),
    )

    previsao = _por_municipio(servico.previsao_de_abertura())["Biguacu"]

    assert previsao.proximo_previsto >= este_ano - 4 + servico.VALIDADE_MINIMA


def test_um_concurso_so_usa_a_validade_legal(banco_temporario):
    """Nao da para tirar ritmo de um ponto: vale a validade de 4 anos."""
    este_ano = date.today().year
    _semear(_concurso(f"{este_ano - 1} - Prefeitura de Nova Trento", "Nova Trento"))

    previsao = _por_municipio(servico.previsao_de_abertura())["Nova Trento"]

    assert previsao.proximo_previsto == este_ano - 1 + servico.VALIDADE_MAXIMA


def test_a_previsao_diz_por_que(banco_temporario):
    """Eu preciso poder conferir a conta, e nao so ver o veredito."""
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 8} - Prefeitura de Tijucas", "Tijucas"),
        _concurso(f"{este_ano - 4} - Prefeitura de Tijucas", "Tijucas"),
    )

    motivo = _por_municipio(servico.previsao_de_abertura())["Tijucas"].motivo

    assert "2 concursos conhecidos" in motivo
    assert "a cada 4 ano(s)" in motivo


def test_atrasado_vem_antes_de_quem_esta_em_dia(banco_temporario):
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano} - Prefeitura de Palhoca", "Palhoca"),
        _concurso(f"{este_ano - 10} - Prefeitura de Tijucas", "Tijucas"),
    )

    assert servico.previsao_de_abertura()[0].municipio == "Tijucas"


def test_longe_de_casa_nao_entra(banco_temporario):
    """A previsao existe para eu saber onde ficar de olho perto de casa."""
    _semear(_concurso("2015 - Prefeitura de Chapeco", "Chapeco", relevancia="remoto"))

    assert servico.previsao_de_abertura() == []


def test_noticia_nao_conta_como_concurso(banco_temporario):
    _semear(_concurso("2015 - INSS paga hoje", "Tijucas", tipo="noticia"))

    assert servico.previsao_de_abertura() == []


# --- a tela -----------------------------------------------------------------

@pytest.fixture
def cliente(banco_temporario):
    from fastapi.testclient import TestClient
    from radar.web.app import app as web
    return TestClient(web)


def test_a_tela_abre_e_agrupa_por_situacao(cliente):
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 10} - Prefeitura de Tijucas", "Tijucas"),
        _concurso(f"{este_ano} - Prefeitura de Palhoca", "Palhoca"),
    )

    texto = cliente.get("/previsao").text

    assert "Atrasados" in texto and "Em dia" in texto
    assert "Tijucas" in texto and "Palhoca" in texto


def test_a_tela_avisa_o_que_o_historico_nao_cobre(cliente):
    """Municipio que usou outra banca entre 2021 e 2025 aparece mais atrasado
    do que e, e eu preciso saber disso ao olhar a lista."""
    texto = cliente.get("/previsao").text

    assert "outra banca" in texto


def test_a_tela_mostra_os_anos_que_embasam_a_conta(cliente):
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 8} - Prefeitura de Tijucas", "Tijucas"),
        _concurso(f"{este_ano - 4} - Prefeitura de Tijucas", "Tijucas"),
    )

    texto = cliente.get("/previsao").text

    assert f"{este_ano - 8}, {este_ano - 4}" in texto


def test_sem_historico_a_tela_explica_o_que_fazer(cliente):
    assert "radar coletar" in cliente.get("/previsao").text


def test_o_radar_tem_link_para_a_previsao(cliente):
    assert 'href="/previsao"' in cliente.get("/").text
