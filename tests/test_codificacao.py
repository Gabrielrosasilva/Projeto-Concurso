"""Pagina que declara uma codificacao e serve outra.

O caso real: o hotsite de 2016 da FEPESE manda `charset=iso-8859-1` no
cabecalho e escreve os dois no mesmo arquivo - "PROVISORIO" em latin-1 e
"Seguranca" em UTF-8. Lido so como latin-1, o cargo chegava ao manifesto
versionado como "Agente de SeguranÃ§a Socioeducativo".

Os bytes daqui sao os mesmos que o site serve. Nenhum teste vai a internet.
"""
import requests

from radar.collectors import base

# "Agente de Segurança" com o cedilha em UTF-8 (c3 a7) e "PROVISÓRIO" com o
# O acentuado em latin-1 (d3), exatamente como a pagina de 2016 os mistura.
CEDILHA_UTF8 = b"\xc3\xa7"
O_ACENTUADO_LATIN1 = b"\xd3"

PAGINA_MISTURADA = (
    b"<html><body><b>PROVIS" + O_ACENTUADO_LATIN1 + b"RIO</b>"
    b"<a href='?arquivo=AS.pdf'>Agente de Seguran" + CEDILHA_UTF8 + b"a "
    b"Socioeducativo (AS)</a></body></html>"
)

# A mesma pagina, latin-1 honesto do comeco ao fim - como as de 2013 e 2019.
PAGINA_LATIN1 = (
    "<html><body><b>PROVISÓRIO</b>"
    "<a href='?arquivo=AP.pdf'>Agente Penitenciário</a></body></html>"
).encode("latin-1")


def _resposta(corpo: bytes, charset: str) -> requests.Response:
    resposta = requests.Response()
    resposta._content = corpo
    resposta.status_code = 200
    resposta.headers["Content-Type"] = f"text/html; charset={charset}"
    # o requests preenche isso a partir do cabecalho ao montar a resposta de
    # verdade; construindo a mao, o passo precisa ser feito aqui
    resposta.encoding = requests.utils.get_encoding_from_headers(resposta.headers)
    return resposta


# --- o caso que motivou o conserto ------------------------------------------

def test_le_o_utf8_escondido_dentro_da_pagina_latin1():
    resposta = _resposta(PAGINA_MISTURADA, "iso-8859-1")
    base.corrigir_codificacao(resposta)

    assert "Agente de Segurança Socioeducativo (AS)" in resposta.text
    assert "SeguranÃ§a" not in resposta.text


def test_o_acento_latin1_da_mesma_pagina_continua_certo():
    """A pagina tem os dois: consertar um nao pode quebrar o outro."""
    resposta = _resposta(PAGINA_MISTURADA, "iso-8859-1")
    base.corrigir_codificacao(resposta)

    assert "PROVISÓRIO" in resposta.text


# --- o que nao pode mudar ---------------------------------------------------

def test_pagina_latin1_honesta_sai_igual():
    """As de 2013 e 2019 sao latin-1 de verdade e tem que sair como antes."""
    antes = _resposta(PAGINA_LATIN1, "iso-8859-1")
    esperado = antes.text

    depois = _resposta(PAGINA_LATIN1, "iso-8859-1")
    base.corrigir_codificacao(depois)

    assert depois.text == esperado
    assert "Agente Penitenciário" in depois.text


def test_servidor_que_declara_utf8_e_respeitado():
    """So mexemos onde ha ambiguidade. Quem diz UTF-8 nao precisa de ajuda."""
    corpo = "Agente de Segurança".encode("utf-8")
    resposta = _resposta(corpo, "utf-8")
    base.corrigir_codificacao(resposta)

    assert resposta.text == "Agente de Segurança"


def test_resposta_sem_charset_nao_e_tocada():
    """PDF e JSON chegam sem charset no cabecalho: nao sao texto para ler."""
    resposta = requests.Response()
    resposta._content = b"%PDF-1.4 \xd3\xc3\xa7"
    resposta.status_code = 200
    resposta.headers["Content-Type"] = "application/pdf"

    base.corrigir_codificacao(resposta)

    # o corpo binario tem que continuar byte a byte igual
    assert resposta.content == b"%PDF-1.4 \xd3\xc3\xa7"
