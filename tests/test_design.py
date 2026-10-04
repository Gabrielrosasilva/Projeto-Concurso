"""O design system: um arquivo de estilo, os selos de origem, modo escuro, e nada de JS.

A tela de Macetes e a primeira a usar. Estes testes seguram o contrato que as
proximas telas vao herdar - se alguem renomear uma variavel ou tirar um selo,
estoura aqui, e nao numa tela que eu so abro de vez em quando.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from radar.web.app import app, templates

CSS = Path(__file__).resolve().parent.parent / "src" / "radar" / "web" / "static" / "design.css"


@pytest.fixture
def cliente(banco_temporario):
    return TestClient(app)


def test_o_arquivo_de_estilo_e_servido(cliente):
    resposta = cliente.get("/estatico/design.css")
    assert resposta.status_code == 200
    assert "text/css" in resposta.headers["content-type"]


@pytest.mark.parametrize("variavel", [
    # cor, espaco, tipografia - as tres familias que a especificacao pede
    "--cor-fundo", "--cor-superficie", "--cor-texto", "--cor-acao",
    "--esp-1", "--esp-4", "--esp-7",
    "--fonte", "--tam-base", "--peso-forte", "--linha",
    "--raio", "--cor-aviso",
    # as quatro origens da secao 20 do novo.md, e o plano (Etapa 7A)
    "--selo-oficial", "--selo-acervo", "--selo-automatico", "--selo-ia", "--selo-plano",
    # a meta do dia, com token proprio desde a 7A
    "--meta-ideal", "--meta-reduzida", "--meta-minima", "--meta-nao-fiz",
])
def test_as_variaveis_existem(variavel):
    assert re.search(rf"{variavel}\s*:", CSS.read_text(encoding="utf-8"))


def test_o_escuro_e_o_padrao_e_nao_segue_o_sistema():
    css = CSS.read_text(encoding="utf-8")
    # O escuro vale sempre que a pagina nao disser claro...
    assert ':root:not([data-tema="claro"])' in css
    # ...e o tema do Windows deixou de mandar.
    assert "prefers-color-scheme" not in css


def test_os_selos_da_especificacao():
    """As quatro origens do novo.md, com o emoji, o texto e a cor da tabela."""
    modulo = templates.env.get_template("_componentes.html").module
    esperados = {
        "oficial": ("🟢", "Fonte oficial", "oficial"),
        "prova": ("🟢", "Extraída da prova", "oficial"),
        "acervo": ("🔵", "Estatística do acervo", "acervo"),
        "automatico": ("🟡", "Análise automática", "automatico"),
        "classificacao": ("🟡", "Análise automática (classificação)", "automatico"),
        "tendencia": ("🟡", "Análise automática (tendência)", "automatico"),
        "ia": ("🟣", "Gerado por IA", "ia"),
        "plano": ("📌", "Seleção do plano (cronograma)", "plano"),
    }
    for tipo, (emoji, texto, cor) in esperados.items():
        html = str(modulo.selo(tipo))
        assert emoji in html and texto in html, tipo
        assert f"ds-selo--{cor}" in html, tipo


def test_o_selo_calculado_saiu():
    """O verde quer dizer oficial: o "calculado" virou acervo ou automatico."""
    from radar import origem

    assert "calculado" not in origem.SELOS
    assert "--selo-calculado" not in CSS.read_text(encoding="utf-8")


def test_o_selo_curto_e_o_mesmo_selo():
    """A ficha usa o mesmo componente, so com o emoji: o texto vai no title."""
    modulo = templates.env.get_template("_componentes.html").module
    html = str(modulo.selo("acervo", curto=True))
    assert "ds-selo--acervo" in html and "🔵" in html
    assert 'aria-label="Estatística do acervo"' in html


def _bloco(css: str, marca: str) -> str:
    """O corpo da primeira regra depois da marca (um seletor, ou o titulo de
    uma secao do design.css), para conferir para onde cada token aponta."""
    inicio = css.index("{", css.index(marca))
    return css[inicio:css.index("}", inicio)]


def test_os_selos_tem_as_cores_do_novo_md():
    """Verde oficial, azul acervo, amarelo automatico, roxo IA - nos dois temas,
    porque o selo aponta para a cor com nome e o escuro troca a cor com nome."""
    css = CSS.read_text(encoding="utf-8")
    origens = _bloco(css, "--- os selos de origem")
    assert "--selo-oficial:          var(--cor-verde)" in origens
    assert "--selo-acervo:           var(--cor-azul)" in origens
    assert "--selo-automatico:       var(--cor-ambar)" in origens
    assert "--selo-ia:               var(--cor-roxo)" in origens
    escuro = _bloco(css, ':root:not([data-tema="claro"])')
    for cor in ("--cor-verde:", "--cor-azul:", "--cor-ambar:", "--cor-roxo:", "--cor-roxo-fundo:"):
        assert cor in escuro, cor


def test_a_meta_do_dia_nao_usa_a_cor_dos_selos():
    """Ideal verde, Reduzida azul, Minima amarela, Nao fiz vermelha: as cores de
    antes da 7A, com token proprio - trocar um selo nao pinta a meta."""
    css = CSS.read_text(encoding="utf-8")
    assert "--meta-ideal:          var(--cor-verde)" in css
    assert "--meta-reduzida:       var(--cor-azul)" in css
    assert "--meta-minima:         var(--cor-ambar)" in css
    assert "--meta-nao-fiz:        var(--cor-vermelho)" in css
    pasta = CSS.parent.parent / "templates"
    for arquivo in ("hoje.html", "semanas.html"):
        texto = (pasta / arquivo).read_text(encoding="utf-8")
        for meta in ("ideal", "reduzida", "minima", "nao-fiz"):
            assert f"var(--meta-{meta})" in texto, (arquivo, meta)


def test_so_o_selo_e_o_bloco_usam_a_cor_dos_selos():
    """Fora do design.css, ninguem pinta com --selo-*: a cor de origem e do
    selo e do bloco. Bom e ruim usam --cor-verde e --cor-vermelho."""
    pasta = CSS.parent.parent / "templates"
    for arquivo in sorted(pasta.glob("*.html")):
        assert "--selo-" not in arquivo.read_text(encoding="utf-8"), arquivo.name


def test_a_tela_de_macetes_usa_o_design_system(cliente):
    pagina = cliente.get("/macetes").text
    assert '/estatico/design.css' in pagina
    assert 'class="ds-pagina"' in pagina


def test_tema_escuro_pela_url(cliente):
    assert 'data-tema="escuro"' in cliente.get("/macetes?cor=escuro").text


def test_o_tema_do_filtro_dos_macetes_nao_mexe_na_cor(cliente):
    """O `tema` da URL e o filtro "Materia ou tema" dos Macetes, e so ele: ate
    04/10 o mesmo nome forcava a cor, e `?tema=claro` pintava a tela E
    procurava "claro". A cor forcada e o `?cor=`."""
    assert 'data-tema="escuro"' in cliente.get("/macetes?tema=claro").text
    assert 'data-tema="claro"' in cliente.get("/macetes?tema=crase&cor=claro").text


# --- o tema: escuro por padrao, claro por escolha (cookie) ------------------

@pytest.mark.parametrize("endereco", ["/", "/hoje", "/mais", "/macetes", "/concursos"])
def test_sem_cookie_a_pagina_sai_escura(cliente, endereco):
    assert 'data-tema="escuro"' in cliente.get(endereco).text


def test_com_cookie_claro_a_pagina_sai_clara(cliente):
    cliente.cookies.set("tema", "claro")
    assert 'data-tema="claro"' in cliente.get("/macetes").text


def test_o_tema_da_url_vence_o_cookie(cliente):
    cliente.cookies.set("tema", "claro")
    assert 'data-tema="escuro"' in cliente.get("/macetes?cor=escuro").text


def test_cookie_com_valor_estranho_cai_no_escuro(cliente):
    cliente.cookies.set("tema", "roxo")
    assert 'data-tema="escuro"' in cliente.get("/macetes").text


def test_trocar_tema_grava_o_cookie_e_volta(cliente):
    resposta = cliente.get("/tema?valor=claro&volta=/hoje", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/hoje"
    assert "tema=claro" in resposta.headers["set-cookie"]


def test_a_escolha_fica_lembrada_entre_as_paginas(cliente):
    cliente.get("/tema?valor=claro&volta=/hoje")
    assert 'data-tema="claro"' in cliente.get("/mais").text
    assert 'data-tema="claro"' in cliente.get("/macetes").text


@pytest.mark.parametrize("volta", [
    "http://exemplo.com/", "https://exemplo.com", "//exemplo.com", "/\\exemplo.com", "hoje",
])
def test_volta_externa_e_recusada(cliente, volta):
    resposta = cliente.get("/tema", params={"valor": "claro", "volta": volta},
                           follow_redirects=False)
    assert resposta.headers["location"] == "/"


def test_o_botao_do_tema_esta_na_barra(cliente):
    escuro = cliente.get("/macetes?banca=FEPESE").text
    # No escuro o botao oferece o claro, e volta para a mesma pagina.
    assert "☀️" in escuro
    assert "/tema?valor=claro&amp;volta=%2Fmacetes%3Fbanca%3DFEPESE" in escuro


def test_o_botao_mantem_o_filtro_dos_macetes_na_volta(cliente):
    """Antes do `?cor=`, o botao tirava o `tema` da volta - e com ele o filtro."""
    pagina = cliente.get("/macetes?banca=FEPESE&tema=crase").text
    assert "volta=%2Fmacetes%3Fbanca%3DFEPESE%26tema%3Dcrase" in pagina


def test_o_botao_tira_a_cor_da_url_na_volta(cliente):
    """Se o ?cor= ficasse na volta, ele venceria o cookie recem-gravado."""
    pagina = cliente.get("/hoje?cor=claro").text
    assert "🌙" in pagina
    assert "/tema?valor=escuro&amp;volta=%2Fhoje\"" in pagina


def test_sem_javascript(cliente):
    """O CLAUDE.md pede sem JavaScript pesado; esta tela nao tem nenhum."""
    assert "<script" not in cliente.get("/macetes").text.lower()


# --- nenhum numero sem fonte, nas outras telas ------------------------------

def test_a_questao_real_do_simulado_leva_o_selo_da_prova(cliente):
    from radar import servico
    from radar.db import sessao
    from radar.models import QuestaoDeProva

    with sessao() as s:
        s.add(QuestaoDeProva(
            prova_url="https://fepese.test/x.pdf", banca="FEPESE", ano=2019,
            numero=1, materia="Direito Penal", enunciado="Questao real?",
            alternativas={"a": "x", "b": "y"}, resposta="a", impressao="r1",
        ))
    simulado = servico.criar_simulado(quantidade=1, materia="Direito Penal")

    texto = cliente.get(f"/simulado/{simulado.id}").text

    assert "ds-selo--oficial" in texto and "🟢 Extraída da prova" in texto.replace(
        '<span aria-hidden="true">🟢</span>', "🟢")


def test_o_custo_em_reais_diz_que_o_cambio_e_fixo(cliente):
    texto = cliente.get("/geradas").text
    if "US$" in texto:                       # so aparece com base para gerar
        assert "câmbio fixo" in texto
