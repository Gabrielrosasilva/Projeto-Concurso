"""Filtro de inscricoes abertas e a ordem de quem tem a pagina lida.

O pedido que originou isto: "quero que traga todos os concursos que estao com
a inscricao aberta tambem, ou seja, nao so na data de hoje. Caso postaram 1
mes atras mas ainda esta aberta a inscricao, eu quero saber".
"""
from datetime import timedelta

from sqlalchemy import select

from radar import servico
from radar.db import sessao
from radar.models import Concurso, agora


def _concurso(url: str, **mudancas) -> Concurso:
    base = dict(
        url=url,
        fonte="teste",
        titulo="Concurso Prefeitura de Palhoca (SC) abre vagas",
        uf="SC",
        municipio="Palhoca",
        tipo="concurso",
        relevancia="nucleo",
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos):
    with sessao() as s:
        for c in concursos:
            s.add(c)


def dias(n: int):
    return agora() + timedelta(days=n)


# --- o que conta como aberto ------------------------------------------------

def test_publicado_ha_um_mes_mas_ainda_aberto_aparece(banco_temporario):
    """O caso do pedido: data de publicacao velha, prazo ainda em pe."""
    _semear(_concurso(
        "https://a.test/1",
        publicado_em=dias(-30),
        inscricoes_de=dias(-25),
        inscricoes_ate=dias(+10),
    ))

    assert len(servico.listar(abertas=True)) == 1


def test_publicado_hoje_mas_ja_encerrado_nao_aparece(banco_temporario):
    """O inverso tambem vale: recente nao quer dizer aberto."""
    _semear(_concurso(
        "https://a.test/2",
        publicado_em=agora(),
        inscricoes_de=dias(-40),
        inscricoes_ate=dias(-2),
    ))

    assert servico.listar(abertas=True) == []


def test_inscricao_que_ainda_vai_abrir_nao_conta(banco_temporario):
    _semear(_concurso(
        "https://a.test/3", inscricoes_de=dias(+5), inscricoes_ate=dias(+30)
    ))

    assert servico.listar(abertas=True) == []


def test_sem_prazo_conhecido_nao_conta(banco_temporario):
    """Sem data nao da para afirmar que esta aberto. Melhor calar."""
    _semear(_concurso("https://a.test/4", inscricoes_ate=None))

    assert servico.listar(abertas=True) == []


def test_so_com_data_de_fim_ainda_conta(banco_temporario):
    """Se sei que fecha dia 30, vale mostrar mesmo sem saber quando abriu."""
    _semear(_concurso(
        "https://a.test/5", inscricoes_de=None, inscricoes_ate=dias(+10)
    ))

    assert len(servico.listar(abertas=True)) == 1


def test_noticia_nunca_entra(banco_temporario):
    _semear(_concurso("https://a.test/6", tipo="noticia", inscricoes_ate=dias(+10)))

    assert servico.listar(abertas=True) == []


def test_aberto_mas_longe_nao_aparece_por_padrao(banco_temporario):
    """`--abertas` soma ao filtro de distancia, nao substitui ele.

    Mostrar as 1.400 inscricoes abertas do Brasil inteiro afogaria as que eu
    posso fazer. Quem quiser ve tudo com --todos.

    O concurso estadual tipo SEFAZ SC nao se perde por causa disto: depois de
    `radar detalhar` ele deixa de ser indefinida e vira nucleo, porque a
    pagina diz que a lotacao e em Florianopolis.
    """
    _semear(_concurso(
        "https://a.test/7", relevancia="remoto", municipio="Capinzal",
        inscricoes_ate=dias(+5),
    ))

    assert servico.listar(abertas=True) == []
    assert len(servico.listar(abertas=True, todas_relevancias=True)) == 1


# --- ordem e contagem -------------------------------------------------------

def test_ordena_pelo_que_fecha_primeiro(banco_temporario):
    """Aqui o que importa e o prazo, nao a data de publicacao."""
    _semear(
        _concurso("https://a.test/a", titulo="Fecha depois", inscricoes_ate=dias(+20)),
        _concurso("https://a.test/b", titulo="Fecha logo", inscricoes_ate=dias(+2)),
        _concurso("https://a.test/c", titulo="Fecha no meio", inscricoes_ate=dias(+9)),
    )

    titulos = [c.titulo for c in servico.listar(abertas=True)]
    assert titulos == ["Fecha logo", "Fecha no meio", "Fecha depois"]


def test_contagem_de_abertas(banco_temporario):
    _semear(
        _concurso("https://a.test/1", inscricoes_ate=dias(+5)),
        _concurso("https://a.test/2", inscricoes_ate=dias(+5)),
        _concurso("https://a.test/3", inscricoes_ate=dias(-5)),   # fechado
    )

    assert servico.contar_abertas() == 2


# --- prioridade de quem tem a pagina lida -----------------------------------

def test_prioridade_comeca_pelo_que_esta_perto(banco_temporario):
    _semear(
        _concurso("https://a.test/longe", relevancia="remoto", uf="SP"),
        _concurso("https://a.test/perto", relevancia="nucleo"),
    )

    escolhidos = servico._pendentes_de_detalhe(limite=10)
    assert [c.url for c in escolhidos] == ["https://a.test/perto"]


def test_concurso_estadual_de_sc_entra_na_fila(banco_temporario):
    """O caso da SEFAZ SC: indefinida por falta de municipio no titulo."""
    _semear(_concurso(
        "https://a.test/sefaz",
        titulo="Concurso SEFAZ (SC) abre 50 vagas",
        relevancia="indefinida",
        municipio=None,
        uf="SC",
    ))

    assert len(servico._pendentes_de_detalhe(limite=10)) == 1


def test_indefinida_de_outro_estado_fica_de_fora(banco_temporario):
    """Concurso de SP que ficou indefinido nao merece uma requisicao."""
    _semear(_concurso(
        "https://a.test/sp", relevancia="indefinida", uf="SP", municipio=None
    ))

    assert servico._pendentes_de_detalhe(limite=10) == []


def test_federal_sem_uf_entra(banco_temporario):
    """Pode aplicar prova em Florianopolis; vale a requisicao."""
    _semear(_concurso(
        "https://a.test/inss",
        titulo="Concurso INSS abre vagas em todo o pais",
        relevancia="indefinida", uf=None, municipio=None,
    ))

    assert len(servico._pendentes_de_detalhe(limite=10)) == 1


def test_nao_le_a_mesma_pagina_duas_vezes(banco_temporario):
    _semear(_concurso("https://a.test/ja", detalhado_em=agora()))

    assert servico._pendentes_de_detalhe(limite=10) == []


def test_respeita_o_limite(banco_temporario):
    _semear(*[_concurso(f"https://a.test/{i}") for i in range(20)])

    assert len(servico._pendentes_de_detalhe(limite=5)) == 5
