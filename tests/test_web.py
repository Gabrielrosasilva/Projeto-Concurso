"""A pagina web renderiza?

Erro em template Jinja so aparece quando a pagina e pedida de verdade - nao
no import. Como a web e a unica interface visual do projeto, vale um teste
que realmente monte o HTML.
"""
import pytest
from fastapi.testclient import TestClient

from radar.db import sessao
from radar.models import Concurso
from radar.web.app import app


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_pagina_abre_vazia(cliente):
    resposta = cliente.get("/concursos")
    assert resposta.status_code == 200
    assert "Radar de Concursos" in resposta.text
    assert "Nada coletado ainda" in resposta.text


def test_pagina_mostra_concurso(cliente):
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/ascurra",
                fonte="concursosnobrasil",
                titulo="Edital Prefeitura de Ascurra (SC) oferta salarios",
                uf="SC",
                situacao="edital_publicado",
                relevancia="nucleo",   # o padrao da pagina so mostra o que e perto
            )
        )

    texto = cliente.get("/concursos").text
    assert "Ascurra" in texto
    assert "https://exemplo.test/ascurra" in texto   # o link original aparece
    # A linha do cartao responde onde, quanto e ate quando. A cidade perdeu o
    # rotulo "Cidade:" porque na linha ela e o primeiro item e se explica
    # sozinha; o resto continua rotulado - "FEPESE" solto nao diz nada.
    assert "Salário:" in texto
    assert "Status:" in texto
    # banca e tipo vivem dentro de "detalhes", que nasce fechado. O conteudo
    # continua no HTML, entao o Ctrl+F do navegador continua achando.
    assert "Banca:" in texto
    assert "detalhes" in texto


def test_aba_estadual_sc(cliente):
    """"estadual" e jargao do banco; na tela vale o que eu entendo. A aba e
    propria porque concurso do estado nao e "perto" nem "longe"."""
    with sessao() as s:
        s.add(
            Concurso(
                url="https://exemplo.test/sap",
                fonte="fepese",
                titulo="2019 - Secretaria de Estado da Administracao Prisional",
                uf="SC",
                tipo="concurso",
                relevancia="estadual",
                motivo_relevancia=(
                    "Orgao estadual de SC; polos de prova a confirmar no edital."
                ),
            )
        )

    inicio = cliente.get("/concursos").text
    assert "Estadual SC" in inicio          # a aba, com a contagem

    texto = cliente.get("/concursos?relevancia=estadual").text
    assert "Administracao Prisional" in texto
    assert "polos de prova a confirmar no edital" in texto


def test_filtro_por_uf(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="De SC",
                       uf="SC", relevancia="nucleo"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="De Sao Paulo",
                       uf="SP", relevancia="nucleo"))

    texto = cliente.get("/concursos?uf=SC").text
    assert "De SC" in texto
    assert "De Sao Paulo" not in texto


def test_contagem_mostra_o_total_quando_filtra(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="De SC",
                       uf="SC", relevancia="nucleo"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="De SP",
                       uf="SP", relevancia="nucleo"))

    assert "1 de 2 concurso(s)" in cliente.get("/concursos?uf=SC").text


def test_atalhos_mostram_a_contagem_de_cada_anel(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="Perto",
                       uf="SC", relevancia="nucleo"))
        s.add(Concurso(url="https://a.test/2", fonte="f", titulo="Longe 1",
                       uf="SP", relevancia="remoto"))
        s.add(Concurso(url="https://a.test/3", fonte="f", titulo="Longe 2",
                       uf="SP", relevancia="remoto"))

    texto = cliente.get("/concursos").text
    # "Perto" e atalho de primeira linha; "Longe" desceu para "mais filtros",
    # mas continua a um clique - nada de anel sumiu da navegacao.
    assert "Perto" in texto and "Longe" in texto
    assert 'href="/concursos?relevancia=remoto"' in texto


def test_pagina_vazia_explica_em_vez_de_parecer_quebrada(cliente):
    """O caso real: tudo coletado esta longe. A pagina precisa dizer isso."""
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="Capinzal",
                       uf="SC", relevancia="remoto"))

    texto = cliente.get("/concursos").text
    assert "Nenhum concurso perto de você agora" in texto
    assert "Ver todos" in texto          # oferece a saida
    assert "Nada coletado ainda" not in texto   # nao confunde com banco vazio


def test_noticia_nao_aparece(cliente):
    """O "Bolsa Familia" que veio no feed nao pode poluir a lista."""
    with sessao() as s:
        s.add(Concurso(url="https://a.test/bolsa", fonte="f", tipo="noticia",
                       titulo="Bolsa Familia passa a ter novo valor",
                       relevancia="nucleo"))

    assert "Bolsa Familia" not in cliente.get("/concursos?todos=true").text


def test_motivo_da_classificacao_aparece_na_tela(cliente):
    """Preciso poder auditar por que o radar decidiu o que decidiu."""
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="Palhoca",
                       uf="SC", relevancia="nucleo",
                       motivo_relevancia="Palhoca (SC) esta no anel nucleo."))

    assert "esta no anel nucleo" in cliente.get("/concursos").text


def test_os_grids_declaram_coluna_que_encolhe(cliente):
    """Grid sem coluna declarada usa uma implicita de tamanho `auto`, que pode
    chegar a max-content e furar a largura da tela com um titulo longo.

    Isto e prevencao, nao conserto: o corte que eu achei ter visto no celular
    era artefato do print (o Chrome no Windows tem largura minima de janela de
    500px, entao um screenshot pedido com 400px e so um recorte). Declarar
    minmax(0,1fr) continua sendo o certo e custa nada.

    Eram tres grids quando o mural lateral existia. Ele saiu na etapa 8 e
    levou dois junto; o que sobrou e o da grade de filtros."""
    texto = cliente.get("/concursos").text
    assert texto.count("grid-template-columns:minmax(0,1fr)") >= 1


# --- a navegacao do topo ---------------------------------------------------
# Os seis destinos do sitemap da especificacao. A barra e a mesma em toda
# pagina: antes cada uma tinha so um "voltar ao radar", e nao dava para pular
# de Macetes para Calendario sem passar pela home.

def test_a_barra_do_topo_tem_os_seis_destinos(cliente):
    texto = cliente.get("/concursos").text
    for rotulo, destino in (("Meu foco", "/"), ("Estudar", "/estudar"),
                            ("Revisão", "/revisao"), ("Análises", "/analises"),
                            ("Concursos", "/concursos"), ("Mais", "/mais")):
        assert rotulo in texto, rotulo
        assert f'href="{destino}"' in texto, destino


def test_previsao_e_calendario_ficam_dentro_de_concursos(cliente):
    """Como a especificacao manda: Concursos junta a lista, Acompanhando,
    Calendario e Previsao, em sub-abas."""
    texto = cliente.get("/previsao").text
    for destino in ("/concursos", "/acompanhando", "/calendario", "/previsao"):
        assert f'href="{destino}"' in texto


@pytest.mark.parametrize("caminho", ["/", "/analises", "/macetes", "/simulado",
                                     "/previsao", "/calendario", "/foco",
                                     "/acompanhando", "/mais"])
def test_a_barra_aparece_em_toda_pagina(cliente, caminho):
    assert "topo-barra" in cliente.get(caminho).text


def test_nenhuma_aba_esta_mais_em_construcao(cliente):
    for caminho in ("/", "/acompanhando", "/analises", "/mais"):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200
        assert "Em construcao" not in resposta.text


def test_o_endereco_antigo_do_foco_leva_para_a_home(cliente):
    resposta = cliente.get("/foco", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/"


def test_estudar_abre_no_simulado_e_revisao_nos_macetes(cliente):
    """Estudar e treinar; Macetes e revisao, como no sitemap."""
    assert cliente.get("/estudar", follow_redirects=False).headers["location"] == "/simulado"
    assert cliente.get("/revisao", follow_redirects=False).headers["location"] == "/macetes"


def test_estudar_junta_simulado_e_gerar(cliente):
    """De dentro de uma da para ir na outra, sem voltar para a home."""
    assert 'href="/geradas"' in cliente.get("/simulado").text
    assert 'href="/simulado"' in cliente.get("/geradas").text


# --- os atalhos e o "mais filtros" ------------------------------------------

def test_a_barra_de_atalhos_tem_quatro(cliente):
    """Perto, Estadual SC, Abertos e Todos. Os outros aneis desceram para
    "mais filtros" - continuam a um clique, mas nao competem por espaco com
    os que eu abro todo dia."""
    texto = cliente.get("/concursos").text
    inicio = texto.index('<div class="atalhos">')
    fim = texto.index("</div>", inicio)
    atalhos = texto[inicio:fim]

    assert atalhos.count("<a ") == 4
    for rotulo in ("Perto", "Estadual SC", "Abertos", "Todos"):
        assert rotulo in atalhos, rotulo


def test_mais_filtros_nasce_fechado(cliente):
    """Sao seis campos que eu uso de vez em quando; abertos, empurravam a
    lista para baixo da dobra."""
    texto = cliente.get("/concursos").text
    assert '<details class="mais-filtros" >' in texto


def test_mais_filtros_abre_sozinho_quando_ha_filtro_ligado(cliente):
    """Filtro escondido e ligado seria a pior combinacao: a lista viria curta
    e a tela nao diria por que."""
    texto = cliente.get("/concursos?banca=FEPESE").text
    assert '<details class="mais-filtros" open>' in texto
    assert "ligado" in texto


def test_a_busca_fica_antes_dos_atalhos(cliente):
    """E o que resolve o caso que nenhum atalho resolve."""
    texto = cliente.get("/concursos").text
    assert texto.index('class="busca"') < texto.index('class="atalhos"')


# --- 30 cartoes por vez -----------------------------------------------------

def _semear_muitos(quantos: int) -> None:
    with sessao() as s:
        for i in range(quantos):
            s.add(Concurso(
                url=f"https://a.test/{i}", fonte="f", titulo=f"Concurso {i}",
                uf="SC", municipio="Palhoca", relevancia="nucleo",
                tipo="concurso", situacao="edital_publicado",
            ))


def test_mostra_trinta_cartoes_por_vez(cliente):
    _semear_muitos(45)
    texto = cliente.get("/concursos").text

    assert texto.count('<li class="nucleo">') == 30
    assert "Ver mais" in texto


def test_ver_mais_cresce_de_trinta_em_trinta(cliente):
    _semear_muitos(45)
    texto = cliente.get("/concursos?mostrar=60").text

    assert texto.count('<li class="nucleo">') == 45
    assert "Ver mais" not in texto       # acabou a lista, o botao some


def test_lista_curta_nao_mostra_o_ver_mais(cliente):
    _semear_muitos(5)
    assert "Ver mais" not in cliente.get("/concursos").text


def test_mostrar_menor_que_o_minimo_nao_encolhe_a_lista(cliente):
    """URL editada a mao nao pode deixar a pagina com um cartao so."""
    _semear_muitos(45)
    assert cliente.get("/concursos?mostrar=1").text.count('<li class="nucleo">') == 30


# --- o cartao enxuto --------------------------------------------------------

def test_o_cartao_mostra_titulo_e_a_linha_de_sempre(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f",
                       titulo="Concurso Prefeitura de Palhoca",
                       uf="SC", municipio="Palhoca", relevancia="nucleo",
                       tipo="concurso", banca="FEPESE", salario=5200.0))

    texto = cliente.get("/concursos").text
    assert "linha-chave" in texto
    assert "Palhoça" in texto            # onde
    assert "R$ 5.200" in texto           # salario
    assert "prazo não confirmado" in texto   # prazo


def test_banca_tipo_e_motivo_ficam_dentro_de_detalhes(cliente):
    with sessao() as s:
        s.add(Concurso(url="https://a.test/1", fonte="f", titulo="Palhoca",
                       uf="SC", relevancia="nucleo", tipo="concurso",
                       banca="FEPESE",
                       motivo_relevancia="Palhoca (SC) esta no anel nucleo."))

    texto = cliente.get("/concursos").text
    abre = texto.index('<details class="detalhes">')
    fecha = texto.index("</details>", abre)
    dentro = texto[abre:fecha]

    assert "FEPESE" in dentro
    assert "esta no anel nucleo" in dentro
    assert "+ anotar" in dentro


def test_a_barra_do_topo_nao_e_estilizada_por_pagina(cliente):
    """A barra e a mesma em todo lugar, e o estilo dela vem de
    _topo_estilo.html. Em Concursos havia um bloco `nav {...}` de uma
    navegacao antiga: o seletor pegava a barra compartilhada - que e um <nav> -
    e so ali os quatro destinos apareciam com borda e fundo de botao."""
    import re

    for caminho in ("/", "/concursos", "/acompanhando", "/simulado"):
        html = cliente.get(caminho).text
        estilos = "\n".join(re.findall(r"<style>(.*?)</style>", html, re.DOTALL))
        assert not re.search(r"^\s*nav\s*[{,]", estilos, re.MULTILINE), caminho


# --- o icone da aba (etapa 12) ----------------------------------------------

def test_o_icone_da_aba_existe(cliente):
    resposta = cliente.get("/favicon.svg")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in resposta.text


def test_favicon_ico_nao_devolve_404(cliente):
    """O navegador pede este endereco por conta propria, mesmo com o <link>
    do SVG na pagina. Sem resposta, era um 404 no console a cada visita."""
    assert cliente.get("/favicon.ico").status_code == 204


@pytest.mark.parametrize("caminho", ["/", "/concursos", "/acompanhando",
                                     "/simulado", "/macetes", "/previsao",
                                     "/calendario"])
def test_toda_pagina_declara_o_icone(cliente, caminho):
    assert 'rel="icon" href="/favicon.svg"' in cliente.get(caminho).text
