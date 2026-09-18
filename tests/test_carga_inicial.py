"""Carga inicial: andar para tras no feed para buscar o historico.

O RSS e um fluxo, nao um arquivo: quem liga o radar hoje ve os concursos de
hoje e nada do que veio antes. Foi a primeira pergunta depois da fase 2 -
"por que so aparecem 14 concursos?". Estes testes cobrem a resposta.

Nenhum vai a internet: as paginas do feed sao montadas aqui.
"""
from datetime import datetime, timedelta, timezone

import pytest

from radar.collectors.concursos_no_brasil import MAXIMO_DE_PAGINAS, ConcursosNoBrasil

HOJE = datetime(2026, 9, 17, tzinfo=timezone.utc)


def _pagina(numero: int, dias_atras: int, quantos: int = 15) -> str:
    """Monta um feed igual ao do site real, com datas controladas."""
    data = (HOJE - timedelta(days=dias_atras)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    itens = "".join(
        f"""<item>
             <title>Concurso Prefeitura de Cidade{numero}x{i} (SC) abre vagas</title>
             <link>https://concursosnobrasil.com/concursos/sc/2026/09/{numero}-{i}/</link>
             <pubDate>{data}</pubDate>
             <category>Santa Catarina</category>
             <description>Teste.</description>
           </item>"""
        for i in range(quantos)
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{itens}</channel></rss>'


class RespostaFalsa:
    def __init__(self, texto: str):
        self.text = texto


@pytest.fixture
def feed_falso(monkeypatch):
    """Substitui o acesso a rede. Registra quais URLs foram pedidas."""
    pedidas: list[str] = []

    def responder(self, url: str):
        pedidas.append(url)
        numero = 1
        if "paged=" in url:
            numero = int(url.split("paged=")[1])
        if numero > 10:                       # o feed acaba na pagina 10
            return RespostaFalsa(_pagina(numero, 0, quantos=0))
        # cada pagina recua 3 dias
        return RespostaFalsa(_pagina(numero, dias_atras=(numero - 1) * 3))

    monkeypatch.setattr(ConcursosNoBrasil, "get", responder)
    monkeypatch.setattr(
        "radar.config.ATRASO_ENTRE_REQUISICOES", 0
    )                                          # teste nao espera
    return pedidas


# --- paginacao --------------------------------------------------------------

def test_coleta_diaria_le_so_a_primeira_pagina(feed_falso):
    """O dia a dia nao pode virar varredura: sao 15 itens e acabou."""
    itens = ConcursosNoBrasil().coletar()

    assert len(itens) == 15
    assert feed_falso == ["https://www.concursosnobrasil.com.br/feed/"]


def test_carga_inicial_le_varias_paginas(feed_falso):
    itens = ConcursosNoBrasil(paginas=4).coletar()

    assert len(itens) == 60                    # 4 paginas x 15
    assert len(feed_falso) == 4
    assert "paged=2" in feed_falso[1]
    assert "paged=4" in feed_falso[3]


def test_primeira_pagina_nao_leva_paged(feed_falso):
    """paged=1 e a mesma coisa que sem parametro; nao poluir a URL."""
    ConcursosNoBrasil(paginas=2).coletar()
    assert feed_falso[0] == "https://www.concursosnobrasil.com.br/feed/"


def test_para_quando_o_feed_acaba(feed_falso):
    """Pedir 50 paginas de um feed com 10 nao vira 50 requisicoes."""
    ConcursosNoBrasil(paginas=50).coletar()
    assert len(feed_falso) == 11               # 10 com conteudo + 1 vazia


def test_teto_de_paginas(feed_falso):
    """Protecao contra digitar um numero enorme sem querer."""
    assert ConcursosNoBrasil(paginas=99999).paginas == MAXIMO_DE_PAGINAS
    assert ConcursosNoBrasil(paginas=0).paginas == 1
    assert ConcursosNoBrasil(paginas=-5).paginas == 1


# --- parada por data --------------------------------------------------------

def test_para_ao_passar_do_periodo_pedido(feed_falso):
    """Pedir 10 dias nao pode varrer o feed inteiro para descobrir o fim."""
    # cada pagina recua 3 dias, entao a pagina 5 ja esta a 12 dias
    ConcursosNoBrasil(paginas=50, desde=HOJE - timedelta(days=10)).coletar()

    assert len(feed_falso) == 5


def test_sem_data_limite_le_tudo_que_foi_pedido(feed_falso):
    ConcursosNoBrasil(paginas=6, desde=None).coletar()
    assert len(feed_falso) == 6


def test_pagina_parcialmente_dentro_do_periodo_nao_para(feed_falso, monkeypatch):
    """Se um item da pagina ainda esta no periodo, a pagina nao encerra a busca."""
    def meia_pagina(self, url: str):
        if "paged=" not in url:
            # um item de hoje e um de 100 dias atras, na mesma pagina
            nova = _pagina(1, 0, quantos=1)
            velha = _pagina(1, 100, quantos=1)
            miolo = nova.split("<channel>")[1].split("</channel>")[0]
            miolo += velha.split("<channel>")[1].split("</channel>")[0]
            return RespostaFalsa(
                f'<?xml version="1.0"?><rss version="2.0"><channel>{miolo}</channel></rss>'
            )
        return RespostaFalsa(_pagina(2, 0, quantos=0))

    monkeypatch.setattr(ConcursosNoBrasil, "get", meia_pagina)
    coletor = ConcursosNoBrasil(paginas=5, desde=HOJE - timedelta(days=10))
    coletor.coletar()
    # nao parou na pagina 1: foi para a 2, que veio vazia
    assert coletor.paginas == 5


# --- o que a carga inicial traz ---------------------------------------------

def test_itens_saem_classificaveis(feed_falso):
    """A carga inicial usa o mesmo parser, entao vem com titulo e UF de sempre."""
    item = ConcursosNoBrasil(paginas=2).coletar()[0]

    assert item.uf == "SC"
    assert item.publicado_em is not None
    assert "Prefeitura" in item.titulo
    assert item.url.startswith("https://")


# --- a carga inicial nao pode virar enxurrada de notificacao -----------------

def _feed_de_uma_pagina(monkeypatch, quantos=3):
    def responder(self, url):
        if "paged=" in url:
            return RespostaFalsa(_pagina(2, 0, quantos=0))
        return RespostaFalsa(_pagina(1, dias_atras=60, quantos=quantos))

    monkeypatch.setattr(ConcursosNoBrasil, "get", responder)
    monkeypatch.setattr("radar.config.ATRASO_ENTRE_REQUISICOES", 0)


def test_historico_nao_entra_na_fila_de_avisos(banco_temporario, monkeypatch):
    """Trazer 90 dias nao pode render 10 mensagens sobre editais de junho."""
    from sqlalchemy import select

    from radar import servico
    from radar.db import sessao
    from radar.models import Concurso

    _feed_de_uma_pagina(monkeypatch)
    servico.carga_inicial(dias=90)

    with sessao() as s:
        pendentes = list(s.scalars(
            select(Concurso).where(Concurso.avisado_em.is_(None))
        ))
    assert pendentes == []


def test_depois_da_carga_a_coleta_diaria_volta_a_avisar(banco_temporario, monkeypatch):
    """Encerrar a fila e so para o historico: o que chegar depois avisa."""
    from radar import avisos, servico
    from radar.collectors.base import ItemColetado
    from radar.db import sessao

    _feed_de_uma_pagina(monkeypatch)
    servico.carga_inicial(dias=90)

    monkeypatch.setenv("RADAR_TELEGRAM_TOKEN", "token-de-teste")
    monkeypatch.setenv("RADAR_TELEGRAM_CHAT_ID", "123")
    enviadas = []
    monkeypatch.setattr(avisos, "enviar", lambda t: enviadas.append(t) or True)
    monkeypatch.setattr(avisos, "PAUSA_ENTRE_MENSAGENS", 0)

    assert servico.avisar().enviados == 0       # o historico ficou quieto

    # agora chega um concurso novo, como chegaria na coleta de amanha
    with sessao() as s:
        servico._gravar(s, ItemColetado(
            titulo="Concurso Prefeitura de Palhoca (SC) abre 50 vagas",
            url="https://concursosnobrasil.com/concursos/sc/2026/09/18/palhoca/",
            uf="SC",
        ), fonte="teste")

    assert servico.avisar().enviados == 1
    assert "Palhoca" in enviadas[0]
