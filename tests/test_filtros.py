"""Os filtros da pagina.

Este arquivo nasceu de um relato de que "nenhum filtro esta funcionando, todos
deram erro e estao quebrando a pagina". A causa era uma so, e derrubava todos:
o formulario HTML manda TODO campo, inclusive o vazio, e a rota declarava
`salario_min` como numero. Filtrar so pela banca enviava `salario_min=`, o
FastAPI tentava converter "" para float e devolvia 422.
"""
import pytest
from datetime import timedelta

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
        titulo="Concurso Prefeitura de Palhoça (SC) para Guarda Municipal",
        uf="SC",
        municipio="Palhoça",
        tipo="concurso",
        relevancia="nucleo",
        banca="FEPESE",
        salario=5200.0,
    )
    base.update(mudancas)
    return Concurso(**base)


def _dias(n: int):
    """Uma data daqui a n dias; negativo e no passado."""
    return agora() + timedelta(days=n)


def _semear(*concursos):
    with sessao() as s:
        for c in concursos:
            s.add(c)


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


# --- o que quebrava a pagina inteira ----------------------------------------

@pytest.mark.parametrize("consulta", [
    "?banca=FEPESE&salario_min=",
    "?banca=FEPESE&salario_min=&salario_max=",
    "?uf=SC&banca=&termo=&salario_min=&salario_max=",
    "?termo=guarda&salario_min=",
    "?todos=true&salario_min=&salario_max=",
    "?abertas=true&salario_min=",
    "?favoritos=true&salario_min=",
    "?editar=&salario_min=",
])
def test_campo_vazio_no_formulario_nao_derruba_a_pagina(cliente, consulta):
    """Formulario HTML manda todo campo, inclusive o vazio."""
    _semear(_concurso("https://a.test/1"))
    assert cliente.get("/concursos" + consulta).status_code == 200


@pytest.mark.parametrize("entrada", ["abc", "R$", "-", "1,2,3", "   "])
def test_texto_invalido_no_campo_de_salario_e_ignorado(cliente, entrada):
    """Quem digita errado ve a lista sem filtro, nao uma pagina de erro."""
    _semear(_concurso("https://a.test/1"))

    resposta = cliente.get(f"/concursos?salario_min={entrada}")
    assert resposta.status_code == 200
    assert "Guarda Municipal" in resposta.text


def test_editar_vazio_nao_derruba(cliente):
    _semear(_concurso("https://a.test/1"))
    assert cliente.get("/concursos?editar=").status_code == 200


# --- faixa de remuneracao ---------------------------------------------------

def _tres_faixas():
    return (
        _concurso("https://a.test/baixo", titulo="Ganha pouco", salario=1500),
        _concurso("https://a.test/medio", titulo="Ganha medio", salario=3000),
        _concurso("https://a.test/alto", titulo="Ganha bem", salario=7000),
        _concurso("https://a.test/altissimo", titulo="Ganha muito", salario=25000),
    )


@pytest.mark.parametrize("minimo,maximo,esperados", [
    (None, 2000, ["Ganha pouco"]),
    (2100, 5000, ["Ganha medio"]),
    (5000, 10000, ["Ganha bem"]),
    (10000, None, ["Ganha muito"]),
])
def test_faixas_de_remuneracao(banco_temporario, minimo, maximo, esperados):
    _semear(*_tres_faixas())

    titulos = [
        c.titulo for c in servico.listar(salario_min=minimo, salario_max=maximo)
    ]
    assert titulos == esperados


def test_so_o_teto_tambem_filtra(banco_temporario):
    """A faixa "até R$ 2.000" nao tem minimo."""
    _semear(*_tres_faixas())
    assert len(servico.listar(salario_max=2000)) == 1


def test_sem_salario_fica_de_fora_de_qualquer_faixa(banco_temporario):
    _semear(_concurso("https://a.test/1", salario=None))
    assert servico.listar(salario_min=None, salario_max=2000) == []


def test_os_atalhos_de_faixa_aparecem_na_tela(cliente):
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/concursos").text
    for rotulo in ("até R$ 2.000", "R$ 2.100 a R$ 5.000",
                   "R$ 5.000 a R$ 10.000", "acima de R$ 10.000"):
        assert rotulo in texto


def test_o_atalho_preserva_a_aba(cliente):
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/concursos?todos=true").text
    assert "todos=true&amp;salario_min=" in texto


def test_a_faixa_escolhida_fica_destacada(cliente):
    _semear(*_tres_faixas())

    texto = cliente.get("/concursos?salario_min=5000&salario_max=10000").text
    assert 'class="ativa"' in texto


def test_o_botao_mostra_a_faixa_escolhida(cliente):
    """Fechada, a caixinha diz qual faixa esta valendo - senao nao da para
    saber sem abrir."""
    _semear(*_tres_faixas())

    aberto = cliente.get("/concursos").text
    assert "Remuneração" in aberto

    escolhido = cliente.get("/concursos?salario_min=5000&salario_max=10000").text
    # A caixinha de faixas e procurada pela classe dela: desde a barra do topo,
    # o primeiro <summary> da pagina e o menu "Mais", e nao este.
    caixinha = escolhido[escolhido.index('<details class="menu-faixa">'):]
    assert "R$ 5.000 a R$ 10.000" in caixinha.split("<summary")[1][:200]


def test_o_campo_de_salario_maximo_saiu_do_formulario(cliente):
    """Quem digita quer dizer "a partir de X". As faixas fechadas continuam
    existindo, mas pela caixinha."""
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/concursos").text
    assert 'name="salario_min"' in texto
    assert 'name="salario_max"' not in texto


def test_digitar_um_minimo_desfaz_a_faixa_fechada(banco_temporario):
    """O formulario nao manda mais o maximo, entao filtrar por 6000 depois de
    ter escolhido "2.100 a 5.000" passa a valer "de 6000 para cima"."""
    _semear(*_tres_faixas())

    titulos = [c.titulo for c in servico.listar(salario_min=6000)]
    assert titulos == ["Ganha muito", "Ganha bem"]


# --- banca por abreviacao ---------------------------------------------------

@pytest.mark.parametrize("digitado", [
    "FCC", "fcc", "Fundação Carlos Chagas", "fundacao carlos chagas",
])
def test_banca_pelo_nome_curto_ou_por_extenso(banco_temporario, digitado):
    """Quem digita "Fundacao Carlos Chagas" quer o mesmo de quem digita FCC."""
    _semear(
        _concurso("https://a.test/1", titulo="Da FCC", banca="FCC"),
        _concurso("https://a.test/2", titulo="Da FEPESE", banca="FEPESE"),
    )

    titulos = [c.titulo for c in servico.listar(banca=digitado)]
    assert titulos == ["Da FCC"]


@pytest.mark.parametrize("digitado,esperado", [
    ("fepese", "FEPESE"),
    ("fundacao de estudos e pesquisas socioeconomicos", "FEPESE"),
    ("getulio vargas", "FGV"),
    ("cespe", "Cebraspe"),
    ("barriga verde", "Instituto o Barriga Verde"),
])
def test_apelidos_conhecidos(digitado, esperado):
    assert esperado in servico.expandir_banca(digitado)


def test_banca_desconhecida_cai_na_busca_por_pedaco(banco_temporario):
    """Banca que nao esta na tabela de apelidos ainda precisa ser encontrada."""
    _semear(_concurso("https://a.test/1", banca="Instituto Novo Qualquer"))

    assert servico.expandir_banca("Novo Qualquer") == []
    assert len(servico.listar(banca="Novo Qualquer")) == 1


# --- busca por palavra ------------------------------------------------------

@pytest.mark.parametrize("digitado", ["Palhoça", "Palhoca", "PALHOCA", "palhoça"])
def test_busca_ignora_acento_e_caixa(banco_temporario, digitado):
    """Quem digita no campo raramente poe cedilha."""
    _semear(_concurso("https://a.test/1"))
    assert len(servico.listar(termo=digitado)) == 1


def test_busca_tambem_olha_o_municipio(banco_temporario):
    _semear(_concurso(
        "https://a.test/1", titulo="Concurso sem cidade no titulo",
        municipio="Biguaçu",
    ))
    assert len(servico.listar(termo="biguacu")) == 1


def test_busca_sem_resultado_devolve_pagina_vazia_e_nao_erro(cliente):
    _semear(_concurso("https://a.test/1"))

    resposta = cliente.get("/concursos?termo=coisaquenaoexiste")
    assert resposta.status_code == 200
    assert "Nenhum resultado" in resposta.text


def test_o_formulario_nao_deixa_o_navegador_preencher_sozinho(cliente):
    """O navegador restaura o que foi digitado antes ao recarregar, e o campo
    aparecia com um valor que ninguem pediu - o servidor manda vazio."""
    _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/concursos").text
    assert 'autocomplete="off"' in texto
    assert 'name="salario_min" type="number" step="100" min="0"\n               placeholder="Salário min" value=""' in texto


# --- aba de noticias e andamento --------------------------------------------

def _mundo_variado():
    """Um concurso em cada fase, e um deles longe de casa."""
    from radar.models import agora

    return (
        _concurso("https://a.test/pm-sp", titulo="Concurso PM SP autorizado",
                  situacao="autorizado", relevancia="remoto", uf="SP",
                  municipio="Sao Paulo", publicado_em=agora()),
        _concurso("https://a.test/pm-mg", titulo="Concurso PM MG abre vagas",
                  situacao="edital_publicado", relevancia="remoto", uf="MG"),
        _concurso("https://a.test/pm-velho", titulo="Concurso PM RS encerrado",
                  situacao="encerrado", relevancia="remoto", uf="RS"),
        _concurso("https://a.test/banca", titulo="Concurso PM BA define banca",
                  situacao="banca_definida", relevancia="indefinida"),
        _concurso("https://a.test/outro", titulo="Concurso de Enfermeiro",
                  situacao="edital_publicado"),
    )


def test_a_busca_de_noticias_nao_filtra_por_distancia(banco_temporario):
    """As outras abas escondem o que e longe. Aqui e o contrario: quem procura
    "PM" quer saber de qualquer policia militar, esteja onde estiver."""
    _semear(*_mundo_variado())

    achados = servico.buscar_noticias(termo="PM")
    assert len(achados) == 4
    assert {c.relevancia for c in achados} == {"remoto", "indefinida"}


def test_a_busca_de_noticias_traz_o_que_ja_encerrou(banco_temporario):
    """Concurso que ja passou e o que diz se o orgao costuma abrir."""
    _semear(*_mundo_variado())

    titulos = [c.titulo for c in servico.buscar_noticias(termo="PM")]
    assert "Concurso PM RS encerrado" in titulos


def test_ordena_pelo_andamento_e_nao_pela_data(banco_temporario):
    """O que esta mais perto de acontecer vem primeiro; o encerrado por ultimo."""
    _semear(*_mundo_variado())

    situacoes = [c.situacao for c in servico.buscar_noticias(termo="PM")]
    assert situacoes.index("banca_definida") < situacoes.index("autorizado")
    assert situacoes[-1] == "encerrado"


def test_busca_de_noticias_sem_termo_traz_tudo(banco_temporario):
    _semear(*_mundo_variado())
    assert len(servico.buscar_noticias()) == 5


def test_a_aba_aparece_na_navegacao(cliente):
    _semear(_concurso("https://a.test/1"))
    assert 'href="/concursos?noticias=true"' in cliente.get("/concursos").text


def test_a_aba_tem_campo_de_busca_proprio(cliente):
    _semear(*_mundo_variado())

    texto = cliente.get("/concursos?noticias=true").text
    assert "busca-noticia" in texto
    assert "polícia científica" in texto      # o exemplo do campo


def test_a_aba_resume_quantos_em_cada_fase(cliente):
    _semear(*_mundo_variado())

    texto = cliente.get("/concursos?noticias=true&termo=PM").text
    assert "banca contratada" in texto
    assert "autorizado" in texto


def test_sem_termo_a_aba_explica_para_que_serve(cliente):
    _semear(_concurso("https://a.test/1", titulo="Qualquer coisa"))

    texto = cliente.get("/concursos?noticias=true&termo=naoexistenada").text
    assert "Nada encontrado" in texto


# --- deteccao da fase pelo titulo -------------------------------------------

@pytest.mark.parametrize("titulo,esperado", [
    ("Policia Militar de Sao Paulo tem novo concurso autorizado", "autorizado"),
    ("Concurso DPE SP define FCC como banca para proximo edital", "banca_definida"),
    ("PGE BA vai contratar banca para novo concurso", "banca_definida"),
    ("Concurso Coren SP tem edital previsto para 76 vagas", "prevista"),
    ("Concurso PM SC deve sair em 2027", "prevista"),
])
def test_fase_lida_no_titulo(titulo, esperado):
    """Antes disto, tudo virava "edital publicado" e as fases anteriores - que
    sao as que dao tempo de estudar - se perdiam."""
    from radar.classificador import detectar_fase

    assert detectar_fase(titulo) == esperado


def test_edital_publicado_vence_a_pista_de_fase_anterior():
    """Se o edital saiu, nao interessa que a noticia lembre da autorizacao."""
    from radar.classificador import detectar_fase

    assert detectar_fase("Prefeitura publica edital do concurso autorizado") is None


def test_titulo_sem_pista_nao_inventa_fase():
    from radar.classificador import detectar_fase

    assert detectar_fase("Camara de Capinzal oferece ate R$ 4,5 mil") is None


def test_a_fase_do_titulo_so_vale_sem_prazo_conhecido(banco_temporario):
    """Data de inscricao e fato; titulo e interpretacao."""
    from datetime import timedelta

    from radar.collectors.base import ItemColetado
    from radar.models import agora

    _semear(_concurso(
        "https://a.test/1",
        titulo="Concurso PM SC autorizado",
        inscricoes_ate=agora() + timedelta(days=10),
        situacao="inscricoes_abertas",
    ))

    with sessao() as s:
        servico._gravar(s, ItemColetado(
            titulo="Concurso PM SC autorizado",
            url="https://a.test/1", uf="SC",
        ), fonte="teste")

    with sessao() as s:
        assert s.scalar(select(Concurso)).situacao == "inscricoes_abertas"


def test_a_aba_de_noticias_nao_mostra_o_filtro_das_outras(cliente):
    """Dois campos de busca na mesma tela confunde. E UF/banca/salario nao
    fazem sentido quando o objetivo e achar o andamento de um concurso em
    qualquer lugar do pais."""
    _semear(_concurso("https://a.test/1"))

    noticias = cliente.get("/concursos?noticias=true").text
    assert 'class="filtros"' not in noticias
    assert "busca-noticia" in noticias

    normal = cliente.get("/concursos").text
    assert 'class="filtros"' in normal


# --- a ordem da lista (etapa 12) --------------------------------------------

def test_inscricao_aberta_vem_primeiro_e_encerrado_por_ultimo(banco_temporario):
    """A lista responde "o que eu ainda posso fazer?". Antes disto o primeiro
    cartao da tela era, em geral, um concurso vencido: ordenar so por data de
    publicacao poe o mais novo na frente, e o mais novo muitas vezes e o que
    acabou de fechar."""
    _semear(
        _concurso("https://a.test/1", titulo="Ja encerrou",
                  inscricoes_de=_dias(-40), inscricoes_ate=_dias(-1),
                  publicado_em=agora()),
        _concurso("https://a.test/2", titulo="Sem prazo conhecido",
                  inscricoes_ate=None, publicado_em=agora() - timedelta(days=5)),
        _concurso("https://a.test/3", titulo="Esta aberta",
                  inscricoes_de=_dias(-2), inscricoes_ate=_dias(10),
                  publicado_em=agora() - timedelta(days=10)),
    )

    assert [c.titulo for c in servico.listar()] == [
        "Esta aberta", "Sem prazo conhecido", "Ja encerrou",
    ]


def test_dentro_do_grupo_o_mais_recente_vem_antes(banco_temporario):
    _semear(
        _concurso("https://a.test/1", titulo="Aberta, publicada ontem",
                  inscricoes_de=_dias(-1), inscricoes_ate=_dias(10),
                  publicado_em=agora() - timedelta(days=1)),
        _concurso("https://a.test/2", titulo="Aberta, publicada mes passado",
                  inscricoes_de=_dias(-30), inscricoes_ate=_dias(20),
                  publicado_em=agora() - timedelta(days=30)),
    )

    assert [c.titulo for c in servico.listar()][0] == "Aberta, publicada ontem"


def test_a_ordem_vem_da_data_e_nao_do_campo_situacao(banco_temporario):
    """Data e fato; `situacao` pode estar velha - e justamente por isso ela
    nao decide onde o cartao aparece."""
    _semear(
        _concurso("https://a.test/1", titulo="Diz aberta, prazo vencido",
                  situacao="inscricoes_abertas",
                  inscricoes_de=_dias(-40), inscricoes_ate=_dias(-2)),
        _concurso("https://a.test/2", titulo="Diz encerrado, prazo correndo",
                  situacao="encerrado",
                  inscricoes_de=_dias(-2), inscricoes_ate=_dias(10)),
    )

    assert [c.titulo for c in servico.listar()] == [
        "Diz encerrado, prazo correndo", "Diz aberta, prazo vencido",
    ]
