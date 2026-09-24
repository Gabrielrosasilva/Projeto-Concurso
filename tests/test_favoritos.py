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

def test_o_recorte_padrao_nao_esconde_favorito(cliente):
    """A promessa que era do mural lateral, agora feita pela consulta.

    O mural mostrava os favoritos em qualquer aba, e era isso que garantia que
    um favorito de Itajai nao sumisse na tela de Concursos. Ele saiu na etapa
    8; sem este escape, a promessa passaria a valer so dentro de Acompanhando.
    """
    (id_,) = _semear(_concurso(
        "https://a.test/1", titulo="Guarda Municipal de Capinzal",
        municipio="Capinzal", relevancia="remoto",
    ))
    servico.favoritar(id_)

    # O anel padrao da tela e nucleo+proximo: sem a estrela, "remoto" nao entra.
    titulos = [c.titulo for c in servico.listar()]
    assert "Guarda Municipal de Capinzal" in titulos
    assert "Guarda Municipal de Capinzal" in cliente.get("/concursos").text


def test_filtro_de_salario_nao_esconde_favorito(cliente):
    """Nem o salario baixo, nem o salario desconhecido."""
    ids = _semear(
        _concurso("https://a.test/1", titulo="Favorito que ganha pouco",
                  salario=2500.0),
        _concurso("https://a.test/2", titulo="Favorito sem salario conhecido",
                  salario=None),
        _concurso("https://a.test/3", titulo="Concurso qualquer", salario=2400.0),
    )
    servico.favoritar(ids[0])
    servico.favoritar(ids[1])

    titulos = [c.titulo for c in servico.listar(salario_min=5000)]
    assert "Favorito que ganha pouco" in titulos
    assert "Favorito sem salario conhecido" in titulos
    assert "Concurso qualquer" not in titulos


def test_pergunta_explicita_continua_sendo_pergunta(cliente):
    """Escolher um anel a dedo e uma pergunta, e a resposta nao pode vir com
    um favorito de outro anel no meio - senao o filtro deixa de responder."""
    (id_,) = _semear(_concurso("https://a.test/1", titulo="Favorito do nucleo"))
    servico.favoritar(id_)

    titulos = [c.titulo for c in servico.listar(relevancia="remoto")]
    assert titulos == []


def test_botao_favoritar_liga_e_desliga(cliente):
    (id_,) = _semear(_concurso("https://a.test/1"))

    resposta = cliente.post(
        "/favoritar",
        data={"concurso_id": id_, "voltar": "/concursos"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303
    assert servico.contar_favoritos() == 1

    cliente.post("/favoritar", data={"concurso_id": id_, "voltar": "/concursos"},
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

    texto = cliente.get("/concursos?favoritos=true").text
    for etapa in ("previsto", "autorizado", "banca contratada",
                  "edital publicado", "inscrições abertas", "encerrado"):
        assert etapa in texto


def test_filtro_de_salario_na_tela(cliente):
    _semear(
        _concurso("https://a.test/1", titulo="Ganha bem", salario=8000),
        _concurso("https://a.test/2", titulo="Ganha pouco", salario=2500),
    )

    texto = cliente.get("/concursos?salario_min=5000").text
    assert "Ganha bem" in texto
    assert "Ganha pouco" not in texto


def test_a_tela_avisa_quantos_ficaram_de_fora_por_falta_de_salario(cliente):
    """Nao basta filtrar certo: eu preciso saber o tamanho do ponto cego."""
    _semear(
        _concurso("https://a.test/1", titulo="Ganha bem", salario=8000),
        _concurso("https://a.test/2", titulo="Sem valor", salario=None),
    )

    texto = cliente.get("/concursos?salario_min=5000").text
    assert "não informam salário no título" in texto
    assert "Ver sem esse filtro" in texto


def test_a_estrela_aparece_como_simbolo_e_nao_como_texto(cliente):
    """Entidade HTML no template vira texto: o Jinja escapa por padrao."""
    (id_,) = _semear(_concurso("https://a.test/1"))

    texto = cliente.get("/concursos").text
    assert "&amp;#9733;" not in texto and "&amp;#9734;" not in texto
    assert "☆" in texto                      # estrela vazia

    servico.favoritar(id_)
    assert "★" in cliente.get("/concursos").text      # estrela cheia


def test_o_campo_de_salario_nao_mostra_casa_decimal_a_toa(cliente):
    """20000.0 no campo fica feio; o valor volta inteiro."""
    _semear(_concurso("https://a.test/1", salario=8000))

    texto = cliente.get("/concursos?salario_min=5000").text
    assert 'value="5000"' in texto
    assert 'value="5000.0"' not in texto


# --- salario que eu digito --------------------------------------------------

def test_gravar_salario_na_mao(banco_temporario):
    """1.115 dos 2.185 nao trazem valor no titulo. Sem isto, ficariam sem
    remuneracao para sempre e fora do filtro."""
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))

    concurso = servico.definir_salario(id_, 5200)
    assert concurso.salario == 5200
    assert concurso.salario_manual is True


def test_a_coleta_nao_sobrescreve_o_salario_que_eu_digitei(banco_temporario):
    """O titulo traz o teto, e mal. O valor do edital vale mais."""
    from radar.collectors.base import ItemColetado

    (id_,) = _semear(_concurso("https://a.test/1", salario=None))
    servico.definir_salario(id_, 5200)

    with sessao() as s:
        servico._gravar(s, ItemColetado(
            titulo="Concurso Prefeitura de Palhoca (SC) oferece ate R$ 2 mil",
            url="https://a.test/1",
            uf="SC",
        ), fonte="teste")

    with sessao() as s:
        assert s.get(Concurso, id_).salario == 5200


def test_reclassificar_tambem_respeita_o_valor_digitado(banco_temporario):
    (id_,) = _semear(_concurso(
        "https://a.test/1",
        titulo="Concurso Prefeitura de Palhoca (SC) oferece ate R$ 2 mil",
    ))
    servico.definir_salario(id_, 9000)
    servico.reclassificar()

    with sessao() as s:
        assert s.get(Concurso, id_).salario == 9000


def test_limpar_devolve_o_campo_ao_classificador(banco_temporario):
    (id_,) = _semear(_concurso("https://a.test/1"))
    servico.definir_salario(id_, 5200)

    concurso = servico.definir_salario(id_, None)
    assert concurso.salario is None
    assert concurso.salario_manual is False


def test_salario_digitado_entra_no_filtro(banco_temporario):
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))
    assert servico.listar(salario_min=5000) == []

    servico.definir_salario(id_, 7000)
    assert len(servico.listar(salario_min=5000)) == 1


# --- a tela do salario ------------------------------------------------------

def test_sem_salario_a_linha_principal_nao_mostra_nada(cliente):
    """"R$ ??" ocupava o mesmo espaco de um dado e nao dizia nada - e mais da
    metade dos concursos nao informa valor no titulo, entao a linha vinha
    cheia de interrogacao."""
    _semear(_concurso("https://a.test/1", salario=None))

    assert "R$ ??" not in cliente.get("/concursos").text


def test_sem_salario_o_lapis_continua_em_detalhes(cliente):
    """Esconder o valor desconhecido nao pode esconder o jeito de preenche-lo."""
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))

    texto = cliente.get("/concursos").text
    assert "não informado" in texto
    assert f"editar={id_}" in texto          # o link do lapis


def test_com_salario_a_linha_principal_mostra(cliente):
    _semear(_concurso("https://a.test/1", salario=5200.0))

    texto = cliente.get("/concursos").text
    assert "R$ 5.200" in texto
    assert "não informado" not in texto


def test_salvar_salario_pela_tela(cliente):
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))

    resposta = cliente.post(
        "/salario",
        data={"concurso_id": id_, "salario": "5200", "voltar": "/concursos"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303

    with sessao() as s:
        assert s.get(Concurso, id_).salario == 5200


@pytest.mark.parametrize("digitado,esperado", [
    ("5200", 5200.0),
    ("R$ 5200", 5200.0),
    ("5.200", 5200.0),
    ("5.200,50", 5200.5),
    ("5200.50", 5200.5),
    (" 5200 ", 5200.0),
])
def test_aceita_o_jeito_que_a_pessoa_digita(cliente, digitado, esperado):
    """Quem digita nao tem que lembrar do formato."""
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))

    cliente.post("/salario",
                 data={"concurso_id": id_, "salario": digitado, "voltar": "/concursos"},
                 follow_redirects=False)

    with sessao() as s:
        assert s.get(Concurso, id_).salario == esperado


def test_campo_vazio_limpa(cliente):
    (id_,) = _semear(_concurso("https://a.test/1", salario=8000))

    cliente.post("/salario", data={"concurso_id": id_, "salario": "", "voltar": "/concursos"},
                 follow_redirects=False)

    with sessao() as s:
        assert s.get(Concurso, id_).salario is None


def test_texto_invalido_nao_quebra(cliente):
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))

    resposta = cliente.post(
        "/salario",
        data={"concurso_id": id_, "salario": "nao sei", "voltar": "/concursos"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303


# --- rotulos e nomes --------------------------------------------------------

def test_cada_informacao_vem_com_rotulo(cliente):
    """"FEPESE" sozinho nao diz nada; "Banca: FEPESE" diz.

    A cidade e a excecao, e de proposito: ela abre a linha do cartao, onde e
    o unico item que pode ser um nome de lugar. Rotular ali seria repetir o
    obvio numa linha que precisa caber inteira.
    """
    _semear(_concurso("https://a.test/1", banca="FEPESE", salario=5200))

    texto = cliente.get("/concursos").text
    for rotulo in ("Salário:", "Banca:", "Status:", "Tipo:"):
        assert rotulo in texto


def test_nucleo_aparece_como_perto(cliente):
    """"nucleo" e jargao do codigo; na tela vale o que se entende."""
    _semear(_concurso("https://a.test/1", relevancia="nucleo"))

    texto = cliente.get("/concursos").text
    assert ">Perto<" in texto


def test_cidade_e_estado_aparecem(cliente):
    _semear(_concurso("https://a.test/1", municipio="Palhoca", uf="SC"))
    assert "Palhoca/SC" in cliente.get("/concursos").text


def test_sem_cidade_a_tela_diz_isso_em_vez_de_ficar_em_branco(cliente):
    _semear(_concurso("https://a.test/1", municipio=None, uf=None))
    assert "não identificada" in cliente.get("/concursos").text


def test_status_aberta_e_fechada(cliente):
    _semear(
        _concurso("https://a.test/1", titulo="Aberto", inscricoes_ate=dias(10)),
        _concurso("https://a.test/2", titulo="Fechado", inscricoes_ate=dias(-10)),
    )

    texto = cliente.get("/concursos?todos=true").text
    # O par virou "Inscrição: aberta" dentro de "detalhes". Quem esta aberto
    # continua dizendo o prazo na linha principal, que e o que decide.
    assert "Inscrição:" in texto
    assert "aberta" in texto
    assert "fechada" in texto


def test_sem_prazo_o_status_diz_que_nao_sabe(cliente):
    _semear(_concurso("https://a.test/1", inscricoes_ate=None))
    assert "prazo não confirmado" in cliente.get("/concursos").text


def test_o_campo_de_salario_so_aparece_no_cartao_que_eu_pedi(cliente):
    """Primeiro tentei <details>: dentro do selo ele crescia para uns 90px e
    deixava uma caixa vazia na tela. Um link ?editar=<id> e previsivel, nao
    depende de CSS esperto e da para testar."""
    ids = _semear(
        _concurso("https://a.test/1", titulo="Primeiro", salario=None),
        _concurso("https://a.test/2", titulo="Segundo", salario=None),
    )

    # sem o parametro, nenhum campo aberto
    assert 'name="salario"' not in cliente.get("/concursos").text

    texto = cliente.get(f"/concursos?editar={ids[0]}").text
    assert texto.count('name="salario"') == 1      # so um cartao abriu
    assert "cancelar" in texto


def test_o_lapis_leva_para_o_proprio_cartao(cliente):
    # precisa ter prazo aberto para aparecer nessa aba
    (id_,) = _semear(_concurso(
        "https://a.test/1", salario=None, inscricoes_ate=dias(10)
    ))

    texto = cliente.get("/concursos?abertas=true").text
    # mantem a aba em que estou e acrescenta o id.
    # O & sai como &amp; porque e HTML - e assim que deve ser.
    assert f"abertas=true&amp;editar={id_}" in texto


def test_cancelar_volta_sem_o_parametro(cliente):
    (id_,) = _semear(_concurso("https://a.test/1", salario=None))

    texto = cliente.get(f"/concursos?todos=true&editar={id_}").text
    assert 'href="/concursos?todos=true"' in texto
    assert f"editar={id_}" not in texto.split("cancelar")[0][-200:]


def test_o_selo_de_salario_nao_usa_a_classe_do_estado_vazio(cliente):
    """Colisao de nome de classe: `.vazio` e a caixa de "nada aqui", com
    padding de 2.5rem. Reusar o nome no selo fazia ele virar um retangulo de
    90px de altura no meio da linha de selos."""
    _semear(_concurso("https://a.test/1", salario=None))

    # Sem valor, o salario saiu da linha principal na etapa 12 - o que esta
    # protegido aqui e o nome da classe: onde ele aparecer, nao pode ser
    # `vazio`. Com o campo de edicao aberto ele reaparece na linha.
    texto = cliente.get("/concursos?editar=" + str(_id_do_unico())).text
    assert "dinheiro sem-valor" in texto
    assert "dinheiro vazio" not in texto


def _id_do_unico() -> int:
    with sessao() as s:
        return s.scalar(select(Concurso)).id


# --- minha anotacao sobre o concurso ----------------------------------------

def test_gravar_e_ler_a_anotacao(banco_temporario):
    (ident,) = _semear(_concurso("https://a.test/nota"))

    servico.definir_notas(ident, "conferir se aceita Sistemas de Informacao")

    with sessao() as s:
        assert "Sistemas" in s.get(Concurso, ident).notas


def test_anotacao_vazia_apaga(banco_temporario):
    (ident,) = _semear(_concurso("https://a.test/nota"))
    servico.definir_notas(ident, "alguma coisa")

    servico.definir_notas(ident, "   ")

    with sessao() as s:
        assert s.get(Concurso, ident).notas is None


def test_anotar_concurso_que_nao_existe_nao_quebra(banco_temporario):
    assert servico.definir_notas(99999, "oi") is None


def test_a_coleta_nao_sobrescreve_a_minha_anotacao(banco_temporario):
    """Este campo e meu, como o favorito."""
    from radar.collectors.base import ItemColetado

    (ident,) = _semear(_concurso("https://a.test/nota"))
    servico.definir_notas(ident, "minha nota")

    with sessao() as s:
        servico._gravar(s, ItemColetado(
            titulo="Titulo corrigido pela fonte", url="https://a.test/nota", uf="SC",
        ), fonte="teste")

    with sessao() as s:
        concurso = s.get(Concurso, ident)
        assert concurso.titulo == "Titulo corrigido pela fonte"
        assert concurso.notas == "minha nota"


def test_a_caixa_de_anotacao_abre_na_tela(cliente):
    (ident,) = _semear(_concurso("https://a.test/nota"))

    assert "+ anotar" in cliente.get("/concursos").text
    assert 'name="notas"' in cliente.get(f"/concursos?anotar={ident}").text


def test_gravar_a_anotacao_pela_tela(cliente):
    (ident,) = _semear(_concurso("https://a.test/nota"))

    resposta = cliente.post(
        "/notas",
        data={"concurso_id": ident, "notas": "prova no mesmo dia da outra",
              "voltar": "/concursos"},
        follow_redirects=False,
    )

    assert resposta.status_code == 303
    assert "prova no mesmo dia da outra" in cliente.get("/concursos").text
