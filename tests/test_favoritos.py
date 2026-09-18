"""Favoritos, filtro de remuneracao e status derivado das datas.

O pedido: "quero uma aba Meus favoritos, poder favoritar o concurso da Guarda
Municipal e ver o status completo dele, e um filtro de remuneracao acima de
5 mil".
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from radar import servico
from radar.db import sessao
from radar.models import Concurso, agora
from radar.web.app import app


def _concurso(url: str, **mudancas) -> Concurso:
    base = dict(
        url=url,
        fonte="teste",
        titulo="Concurso Prefeitura de Palhoca (SC) para Guarda Municipal",
        uf="SC",
        municipio="Palhoca",
        tipo="concurso",
        relevancia="nucleo",
        situacao="edital_publicado",
    )
    base.update(mudancas)
    return Concurso(**base)


def _semear(*concursos) -> list[int]:
    with sessao() as s:
        for c in concursos:
            s.add(c)
    with sessao() as s:
        return [c.id for c in s.scalars(select(Concurso).order_by(Concurso.id))]


def dias(n: int):
    return agora() + timedelta(days=n)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- marcar e desmarcar -----------------------------------------------------

def test_favoritar_e_desfavoritar(banco_temporario):
    (id_,) = _semear(_concurso("https://a.test/1"))

    assert servico.favoritar(id_).interesse == servico.FAVORITO
    assert servico.contar_favoritos() == 1

    assert servico.favoritar(id_, favorito=False).interesse is None
    assert servico.contar_favoritos() == 0


def test_alternar_liga_e_desliga(banco_temporario):
    """E o que o botao de estrela da tela faz."""
    (id_,) = _semear(_concurso("https://a.test/1"))

    assert servico.alternar_favorito(id_).interesse == servico.FAVORITO
    assert servico.alternar_favorito(id_).interesse is None


def test_favoritar_id_que_nao_existe_nao_quebra(banco_temporario):
    assert servico.favoritar(99999) is None


def test_a_coleta_nunca_desmarca_um_favorito(banco_temporario):
    """Favorito e escolha minha; a fonte nao manda nele."""
    from radar.collectors.base import ItemColetado

    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)

    with sessao() as s:
        servico._gravar(s, ItemColetado(
            titulo="Titulo corrigido pela fonte",
            url="https://a.test/1",
            uf="SC",
        ), fonte="teste")

    with sessao() as s:
        concurso = s.get(Concurso, id_)
    assert concurso.titulo == "Titulo corrigido pela fonte"
    assert concurso.interesse == servico.FAVORITO


# --- nenhum filtro esconde um favorito --------------------------------------

def test_favorito_longe_continua_aparecendo(banco_temporario):
    """Se eu marquei, eu quero ver - nem que seja em Roraima."""
    (id_,) = _semear(_concurso(
        "https://a.test/1", relevancia="remoto", municipio="Boa Vista", uf="RR"
    ))
    servico.favoritar(id_)

    assert len(servico.listar(favoritos=True)) == 1


def test_favorito_com_inscricao_encerrada_continua_aparecendo(banco_temporario):
    """Quero acompanhar ate o fim, inclusive depois de fechar."""
    (id_,) = _semear(_concurso("https://a.test/1", inscricoes_ate=dias(-30)))
    servico.favoritar(id_)

    assert len(servico.listar(favoritos=True)) == 1


def test_favorito_sem_salario_continua_aparecendo(banco_temporario):
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))
    servico.favoritar(id_)

    assert len(servico.listar(favoritos=True, salario_min=5000)) == 1


def test_quem_nao_e_favorito_nao_entra(banco_temporario):
    _semear(
        _concurso("https://a.test/1"),
        _concurso("https://a.test/2"),
    )
    assert servico.listar(favoritos=True) == []


def test_favoritos_ordenam_por_quem_fecha_primeiro(banco_temporario):
    ids = _semear(
        _concurso("https://a.test/a", titulo="Fecha depois", inscricoes_ate=dias(20)),
        _concurso("https://a.test/b", titulo="Sem prazo", inscricoes_ate=None),
        _concurso("https://a.test/c", titulo="Fecha logo", inscricoes_ate=dias(3)),
    )
    for id_ in ids:
        servico.favoritar(id_)

    titulos = [c.titulo for c in servico.listar(favoritos=True)]
    assert titulos == ["Fecha logo", "Fecha depois", "Sem prazo"]


# --- filtro de remuneracao --------------------------------------------------

def test_filtra_acima_do_valor(banco_temporario):
    _semear(
        _concurso("https://a.test/1", titulo="Ganha bem", salario=8000),
        _concurso("https://a.test/2", titulo="Ganha pouco", salario=2500),
    )

    titulos = [c.titulo for c in servico.listar(salario_min=5000)]
    assert titulos == ["Ganha bem"]


def test_o_valor_exato_entra(banco_temporario):
    _semear(_concurso("https://a.test/1", salario=5000))
    assert len(servico.listar(salario_min=5000)) == 1


def test_sem_salario_fica_de_fora_do_filtro(banco_temporario):
    """Filtro filtra. A primeira versao deixava os sem valor passarem para nao
    esconder concurso bom, mas 1.115 dos 2.185 nao trazem salario no titulo -
    o filtro nao filtrava nada. O ponto cego agora e avisado na tela, via
    contar_sem_salario()."""
    _semear(
        _concurso("https://a.test/1", titulo="Sem valor no titulo", salario=None),
        _concurso("https://a.test/2", titulo="Ganha bem", salario=8000),
    )

    titulos = [c.titulo for c in servico.listar(salario_min=5000)]
    assert titulos == ["Ganha bem"]
    assert servico.contar_sem_salario() == 1


def test_ordena_do_maior_salario_para_o_menor(banco_temporario):
    _semear(
        _concurso("https://a.test/1", titulo="Medio", salario=7000),
        _concurso("https://a.test/2", titulo="Alto", salario=25300),
        _concurso("https://a.test/3", titulo="Baixo", salario=5100),
    )

    titulos = [c.titulo for c in servico.listar(salario_min=5000)]
    assert titulos == ["Alto", "Medio", "Baixo"]


# --- status derivado das datas ----------------------------------------------

def test_dentro_do_prazo_vira_inscricoes_abertas(banco_temporario):
    _semear(_concurso(
        "https://a.test/1", inscricoes_de=dias(-5), inscricoes_ate=dias(10)
    ))
    servico.atualizar_situacoes()

    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "inscricoes_abertas"


def test_prazo_vencido_vira_encerrado(banco_temporario):
    _semear(_concurso(
        "https://a.test/1", inscricoes_de=dias(-40), inscricoes_ate=dias(-2)
    ))
    servico.atualizar_situacoes()

    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "encerrado"


def test_antes_de_abrir_segue_como_edital_publicado(banco_temporario):
    _semear(_concurso(
        "https://a.test/1", inscricoes_de=dias(5), inscricoes_ate=dias(30)
    ))
    servico.atualizar_situacoes()

    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "edital_publicado"


def test_sem_prazo_o_status_nao_e_inventado(banco_temporario):
    """Sem data nao da para afirmar nada. Nunca chutar."""
    _semear(_concurso("https://a.test/1", situacao="prevista", inscricoes_ate=None))
    servico.atualizar_situacoes()

    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "prevista"


# --- a tela -----------------------------------------------------------------

def test_aba_de_favoritos_aparece_com_a_contagem(cliente):
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.favoritar(id_)

    texto = cliente.get("/").text
    assert "Meus favoritos" in texto
    assert 'href="/?favoritos=true"' in texto


def test_aba_vazia_explica_como_favoritar(cliente):
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/?favoritos=true").text
    assert "ainda nao favoritou" in texto
    assert "estrela" in texto


def test_botao_favoritar_liga_e_desliga(cliente):
    (id_,) = _semear(_concurso("https://a.test/1"))

    resposta = cliente.post(
        "/favoritar",
        data={"concurso_id": id_, "voltar": "/"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303
    assert servico.contar_favoritos() == 1

    cliente.post("/favoritar", data={"concurso_id": id_, "voltar": "/"},
                 follow_redirects=False)
    assert servico.contar_favoritos() == 0


def test_favoritar_devolve_para_a_pagina_de_onde_veio(cliente):
    (id_,) = _semear(_concurso("https://a.test/1"))

    resposta = cliente.post(
        "/favoritar",
        data={"concurso_id": id_, "voltar": "/?abertas=true"},
        follow_redirects=False,
    )
    assert resposta.headers["location"] == "/?abertas=true"


def test_nao_redireciona_para_fora_do_site(cliente):
    """`voltar` vem do formulario; nao pode virar redirecionador aberto."""
    (id_,) = _semear(_concurso("https://a.test/1"))

    resposta = cliente.post(
        "/favoritar",
        data={"concurso_id": id_, "voltar": "https://exemplo-malicioso.test/"},
        follow_redirects=False,
    )
    assert resposta.headers["location"] == "/"


def test_linha_do_tempo_do_status_aparece_nos_favoritos(cliente):
    (id_,) = _semear(_concurso(
        "https://a.test/1", inscricoes_de=dias(-5), inscricoes_ate=dias(10)
    ))
    servico.favoritar(id_)
    servico.atualizar_situacoes()

    texto = cliente.get("/?favoritos=true").text
    for etapa in ("previsto", "autorizado", "banca contratada",
                  "edital publicado", "inscricoes abertas", "encerrado"):
        assert etapa in texto


def test_filtro_de_salario_na_tela(cliente):
    _semear(
        _concurso("https://a.test/1", titulo="Ganha bem", salario=8000),
        _concurso("https://a.test/2", titulo="Ganha pouco", salario=2500),
    )

    texto = cliente.get("/?salario_min=5000").text
    assert "Ganha bem" in texto
    assert "Ganha pouco" not in texto


def test_a_tela_avisa_quantos_ficaram_de_fora_por_falta_de_salario(cliente):
    """Nao basta filtrar certo: eu preciso saber o tamanho do ponto cego."""
    _semear(
        _concurso("https://a.test/1", titulo="Ganha bem", salario=8000),
        _concurso("https://a.test/2", titulo="Sem valor", salario=None),
    )

    texto = cliente.get("/?salario_min=5000").text
    assert "nao informam salario no titulo" in texto
    assert "Ver sem esse filtro" in texto


def test_a_estrela_aparece_como_simbolo_e_nao_como_texto(cliente):
    """Entidade HTML no template vira texto: o Jinja escapa por padrao."""
    (id_,) = _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/").text
    assert "&amp;#9733;" not in texto and "&amp;#9734;" not in texto
    assert "☆" in texto                      # estrela vazia

    servico.favoritar(id_)
    assert "★" in cliente.get("/").text      # estrela cheia


def test_o_campo_de_salario_nao_mostra_casa_decimal_a_toa(cliente):
    """20000.0 no campo fica feio; o valor volta inteiro."""
    _semear(_concurso("https://a.test/1", salario=8000))

    texto = cliente.get("/?salario_min=5000").text
    assert 'value="5000"' in texto
    assert 'value="5000.0"' not in texto
