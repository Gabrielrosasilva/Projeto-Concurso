"""Previsao de abertura: quando o proximo concurso do municipio deve sair.

A pergunta que isto responde e "onde vale ficar de olho agora", e nao "quando
exatamente". Por isso toda previsao carrega o motivo junto: eu preciso poder
conferir a conta.
"""
from datetime import date, datetime, timezone

import pytest

from radar import servico
from radar.servico import comum
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
#
# A funcao e de `servico.comum`: o acervo e a previsao usam a mesma, e ela
# deixou de ter apelido na fachada na faxina da etapa 11.

def test_ano_vem_do_titulo_e_nao_da_data_do_post():
    """Na migracao do site da FEPESE, 345 concursos antigos ficaram todos com
    data de dezembro de 2020. O titulo dela diz o ano de verdade."""
    c = _concurso("2014 - Prefeitura Municipal de Tijucas", "Tijucas", ano=2020)

    assert comum.ano_do_concurso(c) == 2014


def test_ano_do_numero_do_edital():
    """Os titulos antigos nao comecam com ano, mas trazem "Edital 003/2018"."""
    c = _concurso("Prefeitura Municipal de Fraiburgo - Edital 003/2018",
                  "Fraiburgo", ano=2020)

    assert comum.ano_do_concurso(c) == 2018


def test_sem_ano_no_titulo_vale_a_publicacao():
    c = _concurso("Concurso Publico CASAN", "Florianopolis", ano=2023)

    assert comum.ano_do_concurso(c) == 2023


def test_sem_ano_nenhum_fica_de_fora():
    c = _concurso("Concurso Publico CASAN", "Florianopolis")
    c.publicado_em = None

    assert comum.ano_do_concurso(c) is None


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
    assert "a cada 4 anos" in motivo


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
    assert "Tijucas" in texto and "Palhoça" in texto


def test_a_tela_avisa_o_que_o_historico_nao_cobre(cliente):
    """Municipio que usou banca fora das fontes aparece mais atrasado do que
    e, e eu preciso saber disso ao olhar a lista."""
    texto = cliente.get("/previsao").text

    assert "banca fora delas" in texto


def test_os_anos_de_cobertura_vem_do_banco(cliente):
    """A tela dizia "FEPESE (2006 a 2026)" escrito a mao. Agora o intervalo e
    o que o banco tem - e a fonte que o texto esquecia aparece sozinha."""
    from radar import servico

    texto = cliente.get("/previsao").text

    for c in servico.previsao.cobertura_do_historico():
        assert f"{c.fonte} ({c.primeiro_ano}" in texto
    assert "2006 a 2026" not in texto or any(
        c.primeiro_ano == 2006 for c in servico.previsao.cobertura_do_historico()
    )


def test_a_tela_mostra_os_anos_que_embasam_a_conta(cliente):
    este_ano = date.today().year
    _semear(
        _concurso(f"{este_ano - 8} - Prefeitura de Tijucas", "Tijucas"),
        _concurso(f"{este_ano - 4} - Prefeitura de Tijucas", "Tijucas"),
    )

    texto = cliente.get("/previsao").text

    assert f"{este_ano - 8}, {este_ano - 4}" in texto


def test_o_selo_da_cobertura_sai_do_dado(cliente, monkeypatch):
    """O "o que isto nao sabe" mostra a cobertura, contada no banco: o selo
    dela le a origem da Cobertura (Etapa 7A)."""
    from radar.servico import previsao

    _semear(_concurso("2018 - Prefeitura de Tijucas", "Tijucas"))
    monkeypatch.setattr(previsao.Cobertura, "origem", "acervo")

    texto = cliente.get("/previsao").text

    assert "🔵</span> Estatística do acervo</span> O que isto" in texto


def test_os_concursos_coletados_da_tela_mais_leem_a_mesma_origem(cliente, monkeypatch):
    """A tela Mais mostra a mesma cobertura, com o selo dela (Etapa 7A)."""
    from radar.servico import previsao

    def cabeca_do_cartao():
        # A legenda do topo da tela tem todos os selos: o que vale e o selo
        # na cabeca do cartao, entre o titulo e o fim dela.
        texto = cliente.get("/mais").text
        inicio = texto.index("Concursos coletados</h3>")
        return texto[inicio:texto.index("</div>", inicio)]

    _semear(_concurso("2018 - Prefeitura de Tijucas", "Tijucas"))
    assert "ds-selo--automatico" in cabeca_do_cartao()

    monkeypatch.setattr(previsao.Cobertura, "origem", "acervo")
    assert "ds-selo--acervo" in cabeca_do_cartao()


def test_sem_historico_a_tela_explica_o_que_fazer(cliente):
    assert "radar coletar" in cliente.get("/previsao").text


def test_o_radar_tem_link_para_a_previsao(cliente):
    assert 'href="/previsao"' in cliente.get("/concursos").text


# --- como a previsao aparece (etapa 1B, pendencia A3) -----------------------
#
# Data fingida: o "ano de hoje" e trocado para 2026, entao os anos abaixo sao
# fixos e o teste nao muda de resultado conforme o calendario anda. A conta
# nao mudou - so a frase e a ordem dentro da janela.

@pytest.fixture
def em_2026(monkeypatch):
    from radar.servico import previsao

    monkeypatch.setattr(previsao, "_este_ano", lambda: 2026)


def test_ano_previsto_que_ja_passou_vira_atrasado(banco_temporario, em_2026):
    """Um concurso so em 2021: previsto 2025, que em 2026 ainda esta na folga
    ("esperado"), mas ja passou. A tela dizia "Previsto para 2025"."""
    _semear(_concurso("2021 - Prefeitura de Tijucas", "Tijucas"))

    previsao = _por_municipio(servico.previsao_de_abertura())["Tijucas"]

    assert previsao.situacao == "esperado"          # a conta nao mudou
    assert previsao.proximo_previsto == 2025
    assert previsao.vencido
    assert previsao.quando == "Atrasado: era esperado em 2025"


def test_o_atrasado_da_janela_vem_no_topo(banco_temporario, em_2026):
    """Biguacu (2021, 2023: previsto 2025, ja passou) esta parado ha menos
    tempo que Palhoca (2022: previsto 2026). Pela ordem antiga, Palhoca vinha
    antes; o que ja passou do ano tem que vir primeiro."""
    _semear(
        _concurso("2022 - Prefeitura de Palhoca", "Palhoca"),
        _concurso("2021 - Prefeitura de Biguacu", "Biguacu"),
        _concurso("2023 - Prefeitura de Biguacu", "Biguacu"),
    )

    janela = [p for p in servico.previsao_de_abertura() if p.situacao == "esperado"]

    assert [p.municipio for p in janela] == ["Biguacu", "Palhoca"]
    assert janela[1].quando == "Previsto para 2026"


@pytest.mark.parametrize("ultimo, frase", [
    (2026, "O último foi este ano"),
    (2025, "O último foi há 1 ano"),
    (2023, "O último foi há 3 anos"),
])
def test_ha_quanto_tempo_foi_o_ultimo(banco_temporario, em_2026, ultimo, frase):
    _semear(_concurso(f"{ultimo} - Prefeitura de Tijucas", "Tijucas"))

    motivo = _por_municipio(servico.previsao_de_abertura())["Tijucas"].motivo

    assert frase in motivo
    assert "ano(s)" not in motivo


def test_em_dia_diz_so_com_acento(banco_temporario, em_2026):
    _semear(_concurso("2026 - Prefeitura de Tijucas", "Tijucas"))

    previsao = _por_municipio(servico.previsao_de_abertura())["Tijucas"]

    assert previsao.situacao == "em_dia"
    assert previsao.motivo.endswith("O último foi este ano, o próximo só em 2030.")
    assert previsao.quando == "Próximo por volta de 2030"


def test_atrasado_de_verdade_diz_quantos_anos_passaram(banco_temporario, em_2026):
    _semear(
        _concurso("2015 - Prefeitura de Tijucas", "Tijucas"),
        _concurso("2018 - Prefeitura de Tijucas", "Tijucas"),
    )

    previsao = _por_municipio(servico.previsao_de_abertura())["Tijucas"]

    assert previsao.situacao == "atrasado"
    assert "passaram 5 anos do previsto" in previsao.motivo
    assert previsao.quando == "Atrasado: era esperado em 2021"


def test_a_tela_mostra_o_atraso_em_vez_do_ano_passado(cliente, em_2026):
    _semear(_concurso("2021 - Prefeitura de Tijucas", "Tijucas"))

    texto = cliente.get("/previsao").text

    assert "Atrasado: era esperado em 2025" in texto
    assert "Previsto para 2025" not in texto
    assert "ano(s)" not in texto
