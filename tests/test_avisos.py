"""Avisos no Telegram.

Nenhum teste aqui vai a internet: o envio e substituido por uma funcao falsa
que so guarda o que teria sido mandado.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from radar import avisos, servico
from radar.db import sessao
from radar.models import Concurso


@pytest.fixture
def telegram(monkeypatch):
    """Finge que o Telegram esta configurado e captura o que seria enviado."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")

    enviadas: list[str] = []

    def falso_enviar(texto: str) -> bool:
        enviadas.append(texto)
        return True

    monkeypatch.setattr(avisos, "enviar", falso_enviar)
    monkeypatch.setattr(avisos, "PAUSA_ENTRE_MENSAGENS", 0)  # teste nao espera
    return enviadas


def _concurso(**mudancas) -> Concurso:
    base = dict(
        url="https://exemplo.test/palhoca",
        fonte="concursosnobrasil",
        titulo="Prefeitura de Palhoca (SC) abre concurso para Guarda Municipal",
        uf="SC",
        municipio="Palhoca",
        situacao="edital_publicado",
        tipo="concurso",
        relevancia="nucleo",
        motivo_relevancia="Palhoca (SC) esta no anel nucleo.",
        salario=5200.0,
        publicado_em=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos):
    with sessao() as s:
        for c in concursos:
            s.add(c)


# --- a mensagem -------------------------------------------------------------

def test_mensagem_traz_o_link_da_fonte(banco_temporario):
    """O motivo de existir do aviso: nao ter que abrir o computador."""
    texto = avisos.formatar(_concurso())
    assert "https://exemplo.test/palhoca" in texto


def test_mensagem_traz_titulo_salario_local_e_motivo(banco_temporario):
    texto = avisos.formatar(_concurso())
    assert "Guarda Municipal" in texto
    assert "R$ 5.200" in texto
    assert "Palhoca/SC" in texto
    assert "esta no anel nucleo" in texto


def test_emoji_muda_conforme_o_anel(banco_temporario):
    verde = avisos.formatar(_concurso(relevancia="nucleo"))
    amarelo = avisos.formatar(_concurso(relevancia="proximo"))
    azul = avisos.formatar(_concurso(relevancia="indefinida"))
    assert verde[0] != amarelo[0] != azul[0]


def test_titulo_com_caractere_especial_nao_quebra_o_html(banco_temporario):
    """Titulo vem de site de terceiro: < e & precisam virar entidade."""
    texto = avisos.formatar(_concurso(titulo="Concurso <b>P&D</b> & Seguranca"))
    assert "&lt;b&gt;" in texto
    assert "P&amp;D" in texto


def test_concurso_sem_salario_nao_mostra_valor_vazio(banco_temporario):
    texto = avisos.formatar(_concurso(salario=None))
    assert "R$" not in texto


# --- quem e avisado ---------------------------------------------------------

def test_avisa_o_que_esta_perto(banco_temporario, telegram):
    _semear(_concurso())
    resultado = servico.avisar()

    assert resultado.enviados == 1
    assert "Guarda Municipal" in telegram[0]


def test_avisa_indefinida(banco_temporario, telegram):
    """Federal sem UF pode aplicar prova em Floripa: melhor avisar a toa."""
    _semear(_concurso(relevancia="indefinida", uf=None, municipio=None))
    assert servico.avisar().enviados == 1


def test_nao_avisa_o_que_e_longe(banco_temporario, telegram):
    _semear(_concurso(relevancia="remoto", municipio="Capinzal"))
    assert servico.avisar().enviados == 0
    assert telegram == []


def test_nao_avisa_noticia(banco_temporario, telegram):
    """O "Bolsa Familia" do feed nao pode virar notificacao no celular."""
    _semear(_concurso(tipo="noticia", titulo="Bolsa Familia tem novo valor"))
    assert servico.avisar().enviados == 0


def test_nao_avisa_duas_vezes_o_mesmo_concurso(banco_temporario, telegram):
    """A coleta de amanha nao pode repetir o aviso de hoje."""
    _semear(_concurso())

    assert servico.avisar().enviados == 1
    assert servico.avisar().enviados == 0
    assert len(telegram) == 1


def test_marca_a_data_do_aviso(banco_temporario, telegram):
    _semear(_concurso())
    servico.avisar()

    with sessao() as s:
        concurso = s.scalar(select(Concurso))
    assert concurso.avisado_em is not None


# --- o limite de seguranca --------------------------------------------------

def test_limite_por_coleta(banco_temporario, telegram):
    """Regra quebrada nao pode virar 200 notificacoes as 6h da manha."""
    _semear(*[
        _concurso(url=f"https://exemplo.test/{i}", titulo=f"Concurso {i}")
        for i in range(25)
    ])

    resultado = servico.avisar(limite=10)

    assert resultado.enviados == 10
    assert resultado.pendentes == 15
    # 10 avisos + 1 mensagem dizendo quantos ficaram de fora
    assert len(telegram) == 11
    assert "Mais 15" in telegram[-1]


def test_sem_excesso_nao_manda_mensagem_de_alerta(banco_temporario, telegram):
    _semear(_concurso())
    servico.avisar(limite=10)
    assert len(telegram) == 1


def test_o_que_passou_do_limite_fica_para_a_proxima(banco_temporario, telegram):
    _semear(*[
        _concurso(url=f"https://exemplo.test/{i}", titulo=f"Concurso {i}")
        for i in range(12)
    ])

    servico.avisar(limite=10)
    telegram.clear()

    # os 2 que sobraram continuam pendentes
    assert servico.avisar(limite=10).enviados == 2


# --- quando da errado -------------------------------------------------------

def test_sem_configuracao_nao_quebra(banco_temporario, monkeypatch):
    """Coleta sem aviso e melhor que coleta quebrada."""
    monkeypatch.delenv("RADAR_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("RADAR_TELEGRAM_CHAT_ID", raising=False)
    _semear(_concurso())

    resultado = servico.avisar()

    assert resultado.configurado is False
    assert resultado.enviados == 0


def test_telegram_fora_do_ar_mantem_o_concurso_pendente(banco_temporario, monkeypatch):
    """Se a mensagem nao saiu, a proxima coleta precisa tentar de novo."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")
    monkeypatch.setattr(avisos, "enviar", lambda texto: False)
    monkeypatch.setattr(avisos, "PAUSA_ENTRE_MENSAGENS", 0)

    _semear(_concurso())
    assert servico.avisar().enviados == 0

    with sessao() as s:
        assert s.scalar(select(Concurso)).avisado_em is None


def test_erro_de_rede_nao_sobe(banco_temporario, monkeypatch):
    """requests.post estourando nao pode derrubar a coleta diaria."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")

    def explode(*args, **kwargs):
        raise ConnectionError("sem rede")

    monkeypatch.setattr(avisos.requests, "post", explode)

    assert avisos.enviar("teste") is False


def test_o_token_nunca_aparece_no_log(banco_temporario, monkeypatch, caplog):
    """A URL da API carrega o token. Ela nao pode vazar para o log."""
    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-secreto-123")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123456")

    def explode(*args, **kwargs):
        raise ConnectionError("falhou em https://api.telegram.org/bottoken-secreto-123/x")

    monkeypatch.setattr(avisos.requests, "post", explode)

    with caplog.at_level("DEBUG"):
        avisos.enviar("teste")

    assert "token-secreto-123" not in caplog.text
