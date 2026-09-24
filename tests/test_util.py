"""Conversao de fuso horario.

Estes testes existem por causa de um bug real: a CLI inteira quebrava no
Windows porque o fuso era carregado na importacao do modulo e o Windows nao
tem base de fusos no sistema. Os 18 testes da epoca passaram assim mesmo,
porque nenhum deles encostava neste arquivo.
"""
from datetime import datetime, timedelta, timezone

import pytest

from radar.util import (
    formatar_data,
    fuso_local,
    para_local,
    separar_campos_grudados,
)


def test_o_fuso_carrega():
    assert fuso_local() is not None


def test_utc_vira_horario_de_florianopolis():
    utc = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    local = para_local(utc)

    # o Brasil nao tem mais horario de verao: UTC-3 o ano inteiro
    assert local.utcoffset() == timedelta(hours=-3)
    assert local.hour == 9


def test_data_sem_fuso_e_tratada_como_utc():
    local = para_local(datetime(2026, 9, 17, 12, 0))
    assert local.hour == 9


def test_virada_de_dia_usa_a_data_local():
    """Um concurso publicado 01:00 UTC saiu dia 16 aqui, nao dia 17."""
    assert formatar_data(datetime(2026, 9, 17, 1, 0, tzinfo=timezone.utc)) == "16/09/2026"


def test_sem_data():
    assert para_local(None) is None
    assert formatar_data(None) == "--"
    assert formatar_data(None, vazio="sem data") == "sem data"


# --- valor em reais do jeito que a pessoa digita -----------------------------

@pytest.mark.parametrize("digitado,esperado", [
    ("5200", 5200.0),
    ("R$ 5200", 5200.0),
    ("R$5200", 5200.0),
    (" 5200 ", 5200.0),
    ("5.200", 5200.0),          # ponto de milhar, o jeito brasileiro
    ("1.234.567", 1234567.0),
    ("5.200,50", 5200.5),       # virgula decide: ela e o decimal
    ("5200.50", 5200.5),        # ponto decimal tambem vale
    ("0", 0.0),
])
def test_converter_valor(digitado, esperado):
    from radar.util import converter_valor
    assert converter_valor(digitado) == esperado


@pytest.mark.parametrize("digitado", ["", "   ", None, "nao sei", "abc", "-100"])
def test_valor_invalido_vira_none(digitado):
    """Quem digitou errado nao pode derrubar a pagina."""
    from radar.util import converter_valor
    assert converter_valor(digitado) is None


# --- porta ocupada ----------------------------------------------------------

def test_porta_livre_e_porta_ocupada():
    """O uvicorn estoura com "[winerror 10048] normalmente e permitida apenas
    uma utilizacao de cada endereco", que nao diz o que fazer. Perguntar antes
    permite explicar em uma linha."""
    import socket

    from radar.util import porta_ocupada

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind(("127.0.0.1", 0))      # o sistema escolhe uma livre
        servidor.listen(1)
        porta = servidor.getsockname()[1]

        assert porta_ocupada("127.0.0.1", porta) is True

    # fora do bloco a tomada ja fechou
    assert porta_ocupada("127.0.0.1", porta) is False


def test_primeira_porta_livre_pula_a_ocupada():
    import socket

    from radar.util import primeira_porta_livre

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen(1)
        porta = servidor.getsockname()[1]

        assert primeira_porta_livre("127.0.0.1", porta) != porta


def test_host_aberto_e_testado_no_local():
    """0.0.0.0 significa "todas as interfaces"; para TESTAR vale o 127.0.0.1."""
    from radar.util import porta_ocupada

    assert porta_ocupada("0.0.0.0", 1) is False


# --- titulo com os campos colados (etapa 12) --------------------------------
#
# A FEPESE monta o titulo juntando campos do sistema dela, as vezes sem
# separador nenhum. Os exemplos abaixo sao titulos REAIS do banco.

def test_separa_dois_campos_colados():
    titulo = ("2019 – Secretaria de Estado da Administração Prisional – "
              "Concurso PúblicoConcurso Público – Edital 001/2019")

    assert "PúblicoConcurso" not in separar_campos_grudados(titulo)
    assert "Público – Concurso" in separar_campos_grudados(titulo)


def test_separa_orgao_colado_na_secretaria():
    titulo = "2017 – Prefeitura Municipal de FlorianópolisSecretaria Municipal"

    assert ("Florianópolis – Secretaria"
            in separar_campos_grudados(titulo))


@pytest.mark.parametrize("titulo", [
    "2020 – IçaraPrev – Concurso Público – Edital nº 001/2020",
    "RioSaúde (RJ) abre edital com 23 vagas para Médicos",
    "AM: Concurso ManausPrev anuncia remunerações de até R$ 9,1 mil",
    "AgSUS anuncia novo edital de seletivo",
    "Concurso CaraguaPrev (SP) abre vagas",
])
def test_nome_proprio_em_CamelCase_nao_e_separado(titulo):
    """Os cinco sao reais e nenhum pode ser cortado: e assim que a instituicao
    se chama. E por isso que a regra exige palavra longa dos DOIS lados."""
    assert separar_campos_grudados(titulo) == titulo


def test_titulo_vazio_nao_quebra():
    assert separar_campos_grudados(None) == ""
    assert separar_campos_grudados("") == ""
